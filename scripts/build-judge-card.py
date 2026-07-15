#!/usr/bin/env python3
"""Judge-card builder (B2). Runs at gate-approval time as a pure script.

Re-checks tier-1 machine facts, compares them with the gate report's recorded
`claims:`, compares recorded 1st/2nd review verdicts, and emits a judge card
with a tri-state verdict. Exit 0=🟢 / 1=🔴 (block) / 2=🟡 (needs ack).
Never dispatches an LLM (the second opinion is recorded by the LLM beforehand).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


class JudgeError(Exception):
    """Unexpected internal failure. Surfaced as 🟡 (ack-able), not 🔴: a judge
    that cannot RUN is 'unverified', not a proven contradiction. Hard-blocking on
    it would brick every gate (review/qa/security/deploy) with no ack path."""


_DRILL = None


def _drill():
    """Lazy-load B1's drill module (reuse added_lines_by_file/resolve_diff_ref/
    _execute). The filename has hyphens, so load by path."""
    global _DRILL
    if _DRILL is None:
        import importlib.util
        path = Path(__file__).resolve().parent / "run-test-strength-drill.py"
        spec = importlib.util.spec_from_file_location("drill_mod", path)
        _DRILL = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_DRILL)
    return _DRILL


# Non-code path prefixes excluded from CODE checks. B1's added_lines_by_file
# already drops docs/qa-reports artifacts; we additionally drop all of docs/
# (STATUS.md, design docs, notes) and .claude/ (harness control-plane, e.g. the
# .gate-snapshot written at the first gate approval) so documentation and harness
# state never perturb the code fingerprint or trip the stub/secret scanners.
NONCODE_PREFIXES = ("docs/", ".claude/")

# STUB scan only: the harness control-plane CODE (hooks/scripts/templates) is not
# the project's reviewed product code. OBS-017: a fresh install diffs the WHOLE
# framework as added, so the stub scanner would read build-judge-card.py's own
# STUB_PATTERN literal ("TODO|FIXME|...") and self-match into a framework-origin
# false 🔴. These dirs are deliberately NOT added to the secret-scan exclusion:
# a secret committed into a framework script must still be caught at the security
# gate (no security backsliding — scan_secrets keeps full coverage).
STUB_NONCODE_PREFIXES = NONCODE_PREFIXES + ("hooks/", "scripts/", "templates/")


def _changed_code_files(root: Path, exclude: tuple = NONCODE_PREFIXES) -> dict:
    """Map changed CODE files -> set of added line numbers, dropping paths whose
    rel-path starts with any prefix in `exclude` (default: docs/ + .claude/)."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    added = drill.added_lines_by_file(root, ref)
    return {rel: lines for rel, lines in added.items()
            if not rel.startswith(exclude)}


def current_fingerprint(root: Path) -> str:
    """Delegate to hooks/lib/fingerprint.sh — the SINGLE OWNER of the
    fingerprint definition (a python reimplementation would drift). Returns the
    token verbatim; callers must require 64-hex before trusting equality."""
    fp_lib = root / "hooks" / "lib" / "fingerprint.sh"
    if not fp_lib.is_file():
        return "nolib"
    try:
        proc = subprocess.run(["bash", str(fp_lib), str(root)],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "error"
    if proc.returncode != 0:
        return "error"
    return proc.stdout.strip()


# Conventional unfinished-code markers. Case-SENSITIVE with word boundaries so
# legitimate identifiers (todos, todoStore) and HTML attributes (placeholder=)
# are NOT flagged — a stub false positive here is a non-ack-able 🔴 hard block.
STUB_PATTERN = re.compile(
    r"\b(TODO|FIXME|XXX|HACK|WIP)\b"   # uppercase markers (convention)
    r"|NotImplementedError"            # python not-implemented
    r"|pass\s*#\s*stub")              # explicit stub body


def scan_stubs(root: Path) -> list[str]:
    """Scan ONLY changed (added) CODE lines for stub markers. Returns a list of
    'file:line' hits (empty = clean)."""
    hits: list[str] = []
    for rel, lines in _changed_code_files(root, STUB_NONCODE_PREFIXES).items():
        try:
            content = (root / rel).read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        for ln in sorted(lines):
            if 1 <= ln <= len(content) and STUB_PATTERN.search(content[ln - 1]):
                hits.append(f"{rel}:{ln}")
    return hits


EVIDENCE_LOG_REL = Path(".claude") / "evidence-log.jsonl"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _test_runner_patterns(root: Path) -> list:
    """Load AEGIS_TEST_RUNNER_REGEX from patterns.sh (single source). The
    patterns are contract-bound to the grep-E/python-re common subset
    (tests/test_patterns_parity.py)."""
    lib = root / "hooks" / "lib" / "patterns.sh"
    if not lib.is_file():
        return []
    try:
        out = subprocess.run(
            ["bash", "-c",
             'source "$1"; printf "%s\\n" "${AEGIS_TEST_RUNNER_REGEX[@]}"',
             "_", str(lib)],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    pats = []
    for raw in out.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pats.append(re.compile(raw))
        except re.error:
            continue
    return pats


def _tr_strip_patterns(root: Path) -> list:
    """Load AEGIS_TR_STRIP_DQ/SQ from patterns.sh (single source; same
    bash-source printf route as _test_runner_patterns). DQ-then-SQ order is
    the convention pinned by tests/test_patterns_parity.py. Anything short of
    exactly two compilable patterns makes the caller degrade to 'unverified'
    (fail-closed)."""
    lib = root / "hooks" / "lib" / "patterns.sh"
    if not lib.is_file():
        return []
    try:
        out = subprocess.run(
            ["bash", "-c",
             'source "$1"; printf "%s\\n%s\\n" '
             '"$AEGIS_TR_STRIP_DQ" "$AEGIS_TR_STRIP_SQ"',
             "_", str(lib)],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    pats = []
    for raw in out.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            pats.append(re.compile(raw))
        except re.error:
            continue
    return pats


def _norm_cmd_match(cmd: str, pats: list, strips: list) -> bool:
    """Normalize a cmd (newlines→';', quoted spans masked to the inert token
    Q via `strips`) then test it against the runner patterns `pats`. This is
    the single-source normalize+match used by BOTH read_test_result's scan and
    record-test-result.py's pre-validation — so the checker (record) and the
    consumer (judge) can never drift in how they normalize a command."""
    cmd = (cmd or "").replace("\n", ";")
    for sp in strips:
        cmd = sp.sub("Q", cmd)
    return any(p.search(cmd) for p in pats)


def runner_cmd_matches(root: Path, cmd: str) -> bool | None:
    """Is `cmd` a recognized test-runner command, per the SAME normalization
    and patterns the judge uses to scan the evidence log? Returns None when the
    check cannot run (patterns.sh unreadable → no runner patterns, or the strip
    patterns are not exactly two) — a fail-closed 'cannot verify' distinct from
    a definite False. record-test-result.py consumes this so a command the
    judge could never recognize is never recorded (checker == consumer)."""
    pats = _test_runner_patterns(root)
    if not pats:
        return None
    strips = _tr_strip_patterns(root)
    if len(strips) != 2:
        return None
    return _norm_cmd_match(cmd, pats, strips)


def _evidence_entries(root: Path) -> list:
    """Parse evidence-log (rotated .1 first, then current = oldest->newest).
    Broken lines are skipped — the judge must degrade to 'unverified', never
    crash (silent-green is the only forbidden failure mode)."""
    entries = []
    for name in (str(EVIDENCE_LOG_REL) + ".1", str(EVIDENCE_LOG_REL)):
        p = root / name
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict):
                entries.append(d)
    return entries


def read_test_result(root: Path) -> str:
    """'green' / 'red' / 'unverified' from the OBSERVED evidence log (E1).
    Compat wrapper — for the deciding entry's cmd/src/ts see
    read_test_result_detail."""
    return read_test_result_detail(root)["tests"]


def read_test_result_detail(root: Path) -> dict:
    """Deciding test-runner entry as a dict: {"tests": <'green'|'red'|
    'unverified'>, "cmd": <str|None>, "src": <str|None>, "ts": <str|None>}.
    Judgment and card display share this single scan so they can never drift
    on WHICH entry decided. cmd/src/ts are the raw values from the deciding
    entry (green/red); sanitization is the display layer's responsibility.
    Every 'unverified' terminus returns cmd/src/ts all None.

    The newest **decidable** test-runner entry decides; its fp must equal
    the CURRENT worktree fingerprint (both 64-hex). Anything else — no log,
    no decidable entry, stale/oversize/nogit fingerprint, unreadable
    patterns — is 'unverified' (🟡 ack-able), never silent-green.

    Undecidable = src:'observed' with marker_verified NOT true; every other
    entry is decidable (src:'manual' from the trusted runner, observed with
    marker_verified:true — the real writers emit only those two src values;
    an unknown/missing src falling to decidable is pre-existing, whitelist
    hardening tracked as a follow-up). An undecidable entry certifies
    nothing, so the trust-scan (iter67) treats it by status:
      - undecidable-ok  → TRANSPARENT: pure no-run noise (--collect-only
        counts, piped/truncated output), skipped so the scan continues to
        the newest decidable entry. It cannot demote a trusted green nor
        launder a decidable red into a 🟡 (this demotion bit three gate
        approvals in iter64-66 — see docs/LEARNINGS.md, judge test-fact).
      - undecidable-fail → TERMINAL 'unverified': something runner-shaped
        failed, keep the re-record signal (fail-closed unchanged).
    The transparency skip precedes the fp check, so a stale undecidable-ok
    is skipped too (it is decidable-nothing; fp is irrelevant to noise).

    C-2 (v1.6.1): runner-name match alone is insufficient. An entry from an
    OBSERVED source (post-bash-observe.sh) is treated as 'green' / 'red'
    ONLY when it carries marker_verified:true (meaning the observer saw an
    actual final-summary line in tool_response.output — `== N passed in`,
    `Tests: N passed`, etc.). Without marker_verified:true an OBSERVED entry
    is undecidable: with status 'ok' it is transparent (skipped), with
    status 'fail' it is terminal 'unverified' (fail-closed). Manual entries
    (src='manual', via record-test-result.py with the trusted-runner
    contract) keep the old behavior — they bypass marker_verified because
    the human attested.
    Schema: entries written by v1.6.0 lack the field, so an OBSERVED v1.6.0
    'ok' entry is transparent (skipped) in the sequence and a v1.6.0 'fail'
    entry is terminal 'unverified' — re-run the test to upgrade the log.
    """
    unverified = {"tests": "unverified", "cmd": None, "src": None, "ts": None}
    pats = _test_runner_patterns(root)
    if not pats:
        return unverified
    strips = _tr_strip_patterns(root)
    if len(strips) != 2:
        return unverified
    current = current_fingerprint(root)
    if not _HEX64.match(current):
        return unverified
    for d in reversed(_evidence_entries(root)):
        if d.get("status") not in ("ok", "fail"):
            continue
        # Newlines normalized to ';' and quoted spans masked to the inert token
        # Q before matching — the same pipeline as the grep consumer
        # (T1 v1.5.1 + v1.5.2, tests/test_patterns_parity.py). Single-sourced
        # via _norm_cmd_match so record-test-result.py's pre-validation cannot
        # drift from this scan's normalization.
        if not _norm_cmd_match(d.get("cmd"), pats, strips):
            continue
        # trust-scan (iter67): an observed entry whose marker was NOT
        # verified can certify neither green nor red (C-2) — with status
        # "ok" it is pure noise (--collect-only counts, piped/truncated
        # output), so it is TRANSPARENT: skip it and keep scanning for the
        # newest decidable entry. A fail-status undecidable stays terminal
        # (something runner-shaped failed — keep the 🟡 re-record signal).
        # Without this, one noise entry after a trusted green demotes the
        # gate to unverified (iter64/65/66), and one --collect-only after a
        # decidable red launders red into an ack-able 🟡.
        undecidable = (d.get("src") == "observed"
                       and d.get("marker_verified") is not True)
        if undecidable and d.get("status") == "ok":
            continue
        if (d.get("fp") or "") != current:
            return unverified
        # C-2: marker_verified gate for observed entries.
        if undecidable:
            return unverified
        return {"tests": "green" if d.get("status") == "ok" else "red",
                "cmd": d.get("cmd"), "src": d.get("src"), "ts": d.get("ts")}
    return unverified


SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]))")


def scan_secrets(root: Path) -> list[str]:
    """Scan ONLY changed (added) CODE lines for secret-like patterns. Returns
    'file:line' hits. Scanning added lines (not whole files) avoids hard-blocking
    on a pre-existing secret in a file touched for an unrelated reason."""
    hits: list[str] = []
    for rel, lines in _changed_code_files(root).items():
        try:
            content = (root / rel).read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        for ln in sorted(lines):
            if 1 <= ln <= len(content) and SECRET_PATTERN.search(content[ln - 1]):
                hits.append(f"{rel}:{ln}")
    return hits


# Files whose presence proves DEPENDENCIES ARE DECLARED even though we do not
# (yet) have an audit path for that ecosystem. Their presence must keep
# audit_deps at the fail-visible 'unverified' (🟡, ack-able) — NOT the info
# 'no-manifest' (which is a positive claim that the repo has zero dependencies
# and nothing to audit). iter70 review 敵対2次 caught that the first cut of
# this list was too short: real dependency declarations for Node lockfiles,
# .NET, conda, Deno, CocoaPods, etc. fell through to 'no-manifest', silently
# weakening the security signal (a fail-visible→fail-silent regression).
#
# This list is still a denylist and therefore inherently incomplete — an
# unknown ecosystem's manifest can still be mis-read as 'no-manifest'. The root
# fix (a POSITIVE proof of zero dependencies rather than "no known manifest
# matched") is tracked in docs/security-followups.md (SF-014 class). Until
# then: keep this broad, and prefer 'unverified' whenever anything looks like a
# dependency declaration.
UNAUDITABLE_MANIFESTS = (
    # Python
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock",
    "poetry.lock", "uv.lock", "requirements.in",
    # Node / JS / TS (lockfile alone = deps declared even without package.json)
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lockb", "deno.json", "deno.jsonc", "deno.lock",
    # Go / Rust / PHP / Ruby
    "go.mod", "Cargo.toml", "Cargo.lock", "composer.json", "Gemfile",
    "Gemfile.lock",
    # JVM / BEAM / Flutter / Swift (grill-code F-2)
    "pom.xml", "build.gradle", "build.gradle.kts", "mix.exs",
    "pubspec.yaml", "Package.swift",
    # .NET / conda / Nix / Crystal / Erlang / CocoaPods (iter70 敵対2次)
    "packages.config", "paket.dependencies", "environment.yml",
    "environment.yaml", "conda.yaml", "flake.nix", "shard.yml",
    "rebar.config", "Podfile", "Podfile.lock",
    # Haskell / Scala / Clojure / Julia / R / Perl / Dart-lock / C++ / build
    # systems (iter70 security 盲検2次 finding ③ — empirically enumerated).
    "cabal.project", "stack.yaml", "build.sbt", "deps.edn", "project.clj",
    "Project.toml", "renv.lock", "cpanfile", "cpanfile.snapshot",
    "pubspec.lock", "vcpkg.json", "conanfile.txt", "conanfile.py",
    "meson.build", "WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel")

# Dependency manifests named by EXTENSION rather than a fixed filename
# (.NET project files, Ruby gemspecs, CocoaPods podspecs, Haskell cabal).
# Matched by glob so a repo declaring deps this way also stays 'unverified'
# (iter70 敵対2次 / 盲検2次).
UNAUDITABLE_MANIFEST_GLOBS = (
    "*.csproj", "*.fsproj", "*.vbproj", "*.gemspec", "*.podspec", "*.cabal")


def audit_deps(root: Path) -> str:
    """Audit the PROJECT's declared dependencies. Returns 'clean'/'vuln'/
    'unverified'/'no-manifest'.

    Two failure modes the naive version got wrong:
    - `pip-audit` with no args audits the *ambient* interpreter env, not the
      project, so it is run with `-r <requirements>` and only when that file
      exists.
    - `npm audit` with no lockfile errors out (non-zero), which must NOT be read
      as 'vuln'. npm runs only when a lockfile is present.
    When an auditable manifest exists but the tool is absent/times out, the
    result is 'unverified' (advisory 🟡) — never a fabricated 'vuln'.

    'no-manifest' is the proof of a zero-dependency repo (nothing to audit), not
    an exemption for the un-auditable: if even one known dependency manifest
    exists (package.json without a lockfile, or any UNAUDITABLE_MANIFESTS entry)
    we fall to 'unverified' — dependencies are present but the audit path is not
    wired, so we fail-visible rather than claim no manifest."""
    for req in ("requirements.txt", "requirements.lock"):
        if (root / req).is_file():
            try:
                proc = subprocess.run(
                    ["pip-audit", "-q", "-r", str(root / req)],
                    cwd=str(root), capture_output=True, timeout=120)
            except (OSError, subprocess.TimeoutExpired):
                return "unverified"
            return "clean" if proc.returncode == 0 else "vuln"
    has_lock = any((root / lk).is_file()
                   for lk in ("package-lock.json", "npm-shrinkwrap.json"))
    if (root / "package.json").is_file() and has_lock:
        try:
            proc = subprocess.run(
                ["npm", "audit", "--audit-level=high"],
                cwd=str(root), capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return "unverified"
        return "clean" if proc.returncode == 0 else "vuln"
    # package.json without a lockfile: a real manifest we could not audit.
    if (root / "package.json").is_file():
        return "unverified"
    # A known dependency manifest exists but no audit path is wired for it —
    # dependencies are present (not zero), so fail-visible as 'unverified'.
    if any((root / m).is_file() for m in UNAUDITABLE_MANIFESTS):
        return "unverified"
    # Extension-named manifests (.csproj / .gemspec / .podspec) — same rule.
    if any(next(root.glob(pat), None) is not None
           for pat in UNAUDITABLE_MANIFEST_GLOBS):
        return "unverified"
    # No dependency manifest of any kind → proof of a zero-dependency repo.
    return "no-manifest"


GATE_REF_KEY = {"review": "review", "qa": "qa", "security": "security",
                "deploy": "deploy"}


def resolve_gate_report(root: Path, gate: str) -> Path | None:
    """Read current_refs.<ref_key> from STATUS.md; return the report path or
    None when the ref is null/absent (=> 🟡 evidence-not-submitted upstream).

    iter68 atomic approve: `update-gate.sh <gate> approve --ref <path>` exports
    AEGIS_PENDING_REF (existence-validated) BEFORE this pre-approve judge runs
    and commits it to current_refs in the same single write as the approval.
    Honor it as the claims source so the atomic golden path stays judgeable —
    otherwise every judge gate would land a routine 🟡 (claims-absent) and ack
    would stop signalling real deviations. Tier-1 facts (fp/tests) untouched."""
    ref_key = GATE_REF_KEY.get(gate)
    if not ref_key:
        return None
    pending = os.environ.get("AEGIS_PENDING_REF")
    if pending:
        return root / pending
    status = root / "docs" / "STATUS.md"
    if not status.is_file():
        return None
    in_refs = False
    for line in status.read_text(encoding="utf-8").splitlines():
        if re.match(r"^current_refs:\s*$", line):
            in_refs = True
            continue
        if in_refs and re.match(r"^[A-Za-z_]", line):  # next top-level key
            break
        if in_refs:
            m = re.match(rf"^\s+{ref_key}:\s*(.+)$", line)
            if m:
                val = m.group(1).strip().strip('"')
                if val in ("null", "", "[]"):
                    return None
                return root / val
    return None


# gates that require a self-attested second opinion (tier-2)
SECOND_OPINION_GATES = ("review", "security")

# iter56 ③: verdict severity classes. approve × approve_with_notes is a nominal
# difference, not a divergence (M2: 3 consecutive gates needed a meaningless
# ack). Values OUTSIDE the known set are never treated as ok (fail-visible:
# an unfilled template placeholder must not sail through silently).
OK_VERDICTS = frozenset({"approve", "approve_with_notes"})
KNOWN_VERDICTS = OK_VERDICTS | frozenset({"reject", "blocked"})


class Verdict:
    # Plain class (not a dataclass): with `from __future__ import annotations`
    # a dataclass resolves field annotations via sys.modules[__module__], which
    # is absent when this file is loaded via importlib (record-test-result.py,
    # tests) and raises. A plain class is load-mechanism agnostic.
    def __init__(self, overall: int, red=None, yellow=None, info=None):
        self.overall = overall          # 0=🟢 / 1=🔴 / 2=🟡
        self.red = red if red is not None else []
        self.yellow = yellow if yellow is not None else []
        # iter56 ③: non-blocking notes surfaced on the card — never counted
        # in overall (visibility without an ack treadmill).
        self.info = info if info is not None else []


def compute_verdict(gate: str, claims: dict | None, facts: dict,
                    second_opinion: dict | None) -> Verdict:
    """Harness-computed verdict. Tier-1 facts BLOCK (🔴); claims-absent and
    tier-1-unverified and tier-2 divergence are advisory (🟡). Tier-2 NEVER
    blocks (assurance is self-attested)."""
    red: list[str] = []
    yellow: list[str] = []
    info: list[str] = []

    # tier-1 facts run unconditionally (independent of what was claimed)
    if facts["stubs"]:
        red.append(f"変更コードに未完成マーカー: {', '.join(facts['stubs'])}")
    if facts["secrets"]:
        red.append(f"シークレットの疑い: {', '.join(facts['secrets'])}")
    if facts["tests"] == "red":
        red.append("テストが赤")
    elif facts["tests"] == "unverified":
        # iter56 ⑦a: the deny/ack text must carry its own remediation (M2:
        # the bare message forced a docs dig every time).
        yellow.append(
            "テスト結果が未検証（記録なし/コード変更後）— 全編集後に "
            "`python3 scripts/record-test-result.py \"python3 -m pytest\"` で再記録")
    if facts["deps"] == "unverified":
        yellow.append("依存監査が未検証")
    elif facts["deps"] == "vuln":
        # Dependency audits are environment/network sensitive and prone to false
        # positives, so a vuln advises (🟡) but never hard-blocks (🔴) — even if
        # a claim says deps_clean. Blocking on a flaky signal would let a network
        # hiccup veto a release.
        yellow.append("依存監査で脆弱性の可能性（要確認・ack で承認可）")
    elif facts["deps"] == "no-manifest":
        # no-manifest is an info demotion that removes the meaningless per-
        # iteration ack (treadmill) for zero-dependency repos — full-review F6.
        info.append("依存 manifest なし（依存ゼロ repo）— 監査対象なし")
    # At the qa GATE the B1 drill runs first and already blocks on FAIL, so this
    # is usually redundant there; it still matters for the read-only /judge
    # PREVIEW (which does not run the drill) reading a recorded FAIL verdict.
    if facts.get("b1_verdict") == "FAIL":
        red.append("テスト強度ドリル(B1)が FAIL")

    # claims sanity (advisory; missing claims must not hard-block — §1.5)
    if claims is None:
        yellow.append("claims 未提出（要確認）")
    else:
        # 盲検2次 Major (iter56): 1次 verdict の値検証は claims があれば全ゲートで
        # 実施する。second-opinion 分岐内だけだと qa ゲートで未記入プレースホルダが
        # 🟢 沈黙通過し、「claims 未提出 🟡」より後退する（fail-visible 違反）。
        v1 = claims.get("verdict")
        if v1 is None:
            # security 2nd-opinion Low: a claims block missing the verdict key
            # was silent (v1=None skipped the value check). fail-visible.
            yellow.append("claims に verdict キーがありません（要確認）")
        elif v1 not in KNOWN_VERDICTS:
            yellow.append(f"1次 verdict 値が不正/未記入: {v1}")

    # tier-2: self-attested second opinion (advisory only, never blocks)
    if gate in SECOND_OPINION_GATES:
        if second_opinion is None:
            yellow.append("第2意見なし（self-attested・要確認）")
        elif claims:
            v1, v2 = claims.get("verdict"), second_opinion.get("verdict")
            # iter56 ③: approve × approve_with_notes は名目差 — 🟡 にしない。
            # 未知値は ok 扱いしない（fail-visible）。
            both_ok = v1 in OK_VERDICTS and v2 in OK_VERDICTS
            if v1 != v2 and not both_ok:
                yellow.append(
                    f"1次/2次レビューの相違（self-attested）: 1次={v1} / 2次={v2}")
            # grill 致命2: 既知集合外の値（テンプレ未記入プレースホルダ含む）は
            # 同値でも沈黙させない。1次は上の claims 常時検査が担当済み＝ここは2次のみ。
            if v2 is not None and v2 not in KNOWN_VERDICTS:
                yellow.append(f"2次 verdict 値が不正/未記入: {v2}")
            if "approve_with_notes" in (v1, v2):
                notes = second_opinion.get("notes")
                info.append(f"approve_with_notes の notes: {notes}" if notes
                            else "approve_with_notes — notes の解消状況を確認")

    overall = 1 if red else (2 if yellow else 0)
    return Verdict(overall=overall, red=red, yellow=yellow, info=info)


def collect_facts(root: Path, gate: str) -> dict:
    b1 = None
    if gate == "qa":
        ts = root / "docs" / "qa-reports" / "test-strength.md"
        if ts.is_file():
            m = re.search(r"verdict:\s*(\w+)", ts.read_text(encoding="utf-8"))
            b1 = m.group(1) if m else None
    secrets = scan_secrets(root) if gate == "security" else []
    deps = audit_deps(root) if gate == "security" else "clean"
    tr = read_test_result_detail(root)
    return {
        "tests": tr["tests"],
        "tests_cmd": tr["cmd"],
        "tests_src": tr["src"],
        "tests_ts": tr["ts"],
        "stubs": scan_stubs(root),
        "secrets": secrets,
        "b1_verdict": b1,
        "deps": deps,
    }


def _sanitize_card_field(s, limit: int = 120) -> str:
    """Neutralize a raw evidence field for single-line card display: CR/LF are
    collapsed to ';' (a forged header cannot land on its own line to inject a
    second card section or a second '- テスト:' line), backticks to "'" (no
    stray code spans), and a leading markdown '#' run to fullwidth '＃' so the
    field can never reproduce the genuine '## 総合' header substring (design
    line 77: '## 見出し注入不能'); over-limit is truncated to limit-1 + '…'."""
    out = str(s).replace("\r", ";").replace("\n", ";")
    # grill-code F-1: CR/LF alone is a denylist — Unicode line separators
    # (U+2028/U+2029/NEL/\v/\f) survive it and str.splitlines()/some renderers
    # break on them, so a hostile cmd could spoof a second card line. Collapse
    # ALL remaining whitespace positively via str.split() (which splits on
    # every Unicode whitespace) instead of enumerating break characters.
    out = " ".join(out.split())
    out = out.replace("`", "'").replace("#", "＃")
    if len(out) > limit:
        out = out[:limit - 1] + "…"
    return out


def render_card(report_out: Path, *, gate: str, v: Verdict, claims: dict | None,
                facts: dict, second_opinion: dict | None) -> None:
    sym = {0: "🟢 承認可", 1: "🔴 ブロック", 2: "🟡 要確認"}[v.overall]
    # tests line: when the deciding entry's cmd is known, name the judgment
    # source (src/cmd/ts) so a reader can trace the verdict; all three fields go
    # through _sanitize_card_field so a hostile recorded cmd cannot inject card
    # structure. build()'s except path passes facts without the new keys, so
    # .get keeps missing keys benign (compat pin test_card_tolerates_missing).
    if facts.get("tests_cmd"):
        _src = _sanitize_card_field(facts.get("tests_src") or "?")
        _cmd = _sanitize_card_field(facts["tests_cmd"])
        _ts = _sanitize_card_field(facts.get("tests_ts") or "?")
        tests_line = (f"- テスト: {facts['tests']}"
                      f"（判定源: src={_src} / cmd={_cmd} / ts={_ts}）")
    else:
        tests_line = f"- テスト: {facts['tests']}"
    lines = [f"# Judge カード: {gate} ゲート（機械生成）", "",
             f"## 総合: {sym}", "",
             "## ティア1: 機械事実（✅検証済・高信頼）",
             tests_line,
             f"- 未完成マーカー(変更行): {facts['stubs'] or 'なし'}"]
    if gate == "security":
        lines.append(f"- シークレット: {facts['secrets'] or 'なし'}")
        lines.append(f"- 依存監査: {facts['deps']}")
    if gate == "qa":
        lines.append(f"- テスト強度ドリル(B1): {facts['b1_verdict'] or '未実施'}")
    if gate in SECOND_OPINION_GATES:
        lines += ["", "## ティア2: 🔍 第2意見（self-attested・自己申告・低信頼）",
                  f"- {('あり: ' + str(second_opinion.get('verdict'))) if second_opinion else 'なし'}"]
    if v.red:
        lines += ["", "## 🔴 ブロック要因"] + [f"- {r}" for r in v.red]
    if v.yellow:
        lines += ["", "## 🟡 要確認"] + [f"- {y}" for y in v.yellow]
    if v.info:
        lines += ["", "## 💬 情報（非ブロッキング）"] + [f"- {i}" for i in v.info]
    lines += ["", "## あなたが取るアクション", "（LLM が平易日本語で記述）", ""]
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text("\n".join(lines), encoding="utf-8")


def build(root: Path, gate: str, report_out: Path) -> int:
    try:
        report = resolve_gate_report(root, gate)
        claims = read_claims(report) if report else None
        second = claims.get("second_opinion") if claims else None
        facts = collect_facts(root, gate)
        v = compute_verdict(gate, claims, facts, second)
        render_card(report_out, gate=gate, v=v, claims=claims, facts=facts,
                    second_opinion=second)
        for r in v.red:
            print(f"🔴 {r}")
        for y in v.yellow:
            print(f"🟡 {y}")
        for i in v.info:
            print(f"💬 {i}")
        return v.overall
    except Exception as exc:
        # The judge could not complete (e.g. not a git repo, transient git
        # failure, internal bug). Treat as 🟡 unverified — ack-able with a
        # recorded reason — rather than 🔴, so one judge fault cannot lock every
        # gate. The reviewer/QA/security agents remain the substantive check.
        print(f"🟡 judge を実行できませんでした（要手動確認・ack で承認可）: {exc}")
        try:
            render_card(report_out, gate=gate,
                        v=Verdict(overall=2, yellow=[f"judge 実行不可: {exc}"]),
                        claims=None, facts={"tests": "unverified", "stubs": [],
                                            "secrets": [], "b1_verdict": None,
                                            "deps": "unverified"},
                        second_opinion=None)
        except Exception:
            pass
        return 2


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Judge-card builder (B2)")
    p.add_argument("--gate", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--report-out", default=None)
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.report_out) if args.report_out else (
        root / "docs" / "qa-reports" / f"judge-{args.gate}.md")
    return build(root, args.gate, out)


def _parse_scalar(v: str):
    s = v.strip()
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    return s.strip('"')


def read_claims(report_path: Path) -> dict | None:
    """Read the single fenced ```claims YAML block from a gate report. Returns a
    flat dict (nested second_opinion captured as a sub-dict) or None if the file
    or block is absent. Intentionally a narrow YAML subset (key: value lines and
    one nested `second_opinion:` map) to stay dependency-free."""
    if not report_path.is_file():
        return None
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"```claims\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None
    claims: dict = {}
    cur_map: dict | None = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z_]+:\s*$", line):  # "second_opinion:" map start
            key = line.split(":")[0].strip()
            cur_map = {}
            claims[key] = cur_map
            continue
        indented = line.startswith("  ")
        kv = line.strip().split(":", 1)
        if len(kv) != 2:
            continue
        key, val = kv[0].strip(), kv[1].strip()
        if indented and cur_map is not None:
            cur_map[key] = _parse_scalar(val)
        else:
            cur_map = None
            claims[key] = _parse_scalar(val)
    return claims


if __name__ == "__main__":
    sys.exit(main())

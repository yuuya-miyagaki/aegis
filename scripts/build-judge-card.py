#!/usr/bin/env python3
"""Judge-card builder (B2). Runs at gate-approval time as a pure script.

Re-checks tier-1 machine facts, compares them with the gate report's recorded
`claims:`, compares recorded 1st/2nd review verdicts, and emits a judge card
with a tri-state verdict. Exit 0=🟢 / 1=🔴 (block) / 2=🟡 (needs ack).
Never dispatches an LLM (the second opinion is recorded by the LLM beforehand).
"""
from __future__ import annotations

import json
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

    The newest test-runner entry decides; its fp must equal the CURRENT
    worktree fingerprint (both 64-hex). Anything else — no log, no matching
    entry, stale/oversize/nogit fingerprint, unreadable patterns — is
    'unverified' (🟡 ack-able), never silent-green.

    C-2 (v1.6.1): runner-name match alone is insufficient. An entry from an
    OBSERVED source (post-bash-observe.sh) is treated as 'green' / 'red'
    ONLY when it carries marker_verified:true (meaning the observer saw an
    actual final-summary line in tool_response.output — `== N passed in`,
    `Tests: N passed`, etc.). Without marker_verified:true the entry
    degrades to 'unverified' (fail-closed). Manual entries (src='manual',
    via record-test-result.py with the trusted-runner contract) keep the
    old behavior — they bypass marker_verified because the human attested.
    Schema: entries written by v1.6.0 lack the field, so they all degrade
    to 'unverified' on first load — re-run the test to upgrade the log.
    """
    pats = _test_runner_patterns(root)
    if not pats:
        return "unverified"
    strips = _tr_strip_patterns(root)
    if len(strips) != 2:
        return "unverified"
    current = current_fingerprint(root)
    if not _HEX64.match(current):
        return "unverified"
    for d in reversed(_evidence_entries(root)):
        if d.get("status") not in ("ok", "fail"):
            continue
        # Newlines normalized to ';' and quoted spans masked to the inert token
        # Q before matching — the same pipeline as the grep consumer
        # (T1 v1.5.1 + v1.5.2, tests/test_patterns_parity.py).
        cmd = (d.get("cmd") or "").replace("\n", ";")
        for sp in strips:
            cmd = sp.sub("Q", cmd)
        if not any(p.search(cmd) for p in pats):
            continue
        if (d.get("fp") or "") != current:
            return "unverified"
        # C-2: marker_verified gate for observed entries.
        if d.get("src") == "observed" and d.get("marker_verified") is not True:
            return "unverified"
        return "green" if d.get("status") == "ok" else "red"
    return "unverified"


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


def audit_deps(root: Path) -> str:
    """Audit the PROJECT's declared dependencies. Returns 'clean'/'vuln'/
    'unverified'.

    Two failure modes the naive version got wrong:
    - `pip-audit` with no args audits the *ambient* interpreter env, not the
      project, so it is run with `-r <requirements>` and only when that file
      exists.
    - `npm audit` with no lockfile errors out (non-zero), which must NOT be read
      as 'vuln'. npm runs only when a lockfile is present.
    When no matching manifest exists, or the tool is absent/times out, the result
    is 'unverified' (advisory 🟡) — never a fabricated 'vuln'."""
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
    return "unverified"


GATE_REF_KEY = {"review": "review", "qa": "qa", "security": "security",
                "deploy": "deploy"}


def resolve_gate_report(root: Path, gate: str) -> Path | None:
    """Read current_refs.<ref_key> from STATUS.md; return the report path or
    None when the ref is null/absent (=> 🟡 evidence-not-submitted upstream)."""
    ref_key = GATE_REF_KEY.get(gate)
    if not ref_key:
        return None
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
            "`python3 scripts/record-test-result.py \"python3 -m pytest -q\"` で再記録")
    if facts["deps"] == "unverified":
        yellow.append("依存監査が未検証")
    elif facts["deps"] == "vuln":
        # Dependency audits are environment/network sensitive and prone to false
        # positives, so a vuln advises (🟡) but never hard-blocks (🔴) — even if
        # a claim says deps_clean. Blocking on a flaky signal would let a network
        # hiccup veto a release.
        yellow.append("依存監査で脆弱性の可能性（要確認・ack で承認可）")
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
    return {
        "tests": read_test_result(root),
        "stubs": scan_stubs(root),
        "secrets": secrets,
        "b1_verdict": b1,
        "deps": deps,
    }


def render_card(report_out: Path, *, gate: str, v: Verdict, claims: dict | None,
                facts: dict, second_opinion: dict | None) -> None:
    sym = {0: "🟢 承認可", 1: "🔴 ブロック", 2: "🟡 要確認"}[v.overall]
    lines = [f"# Judge カード: {gate} ゲート（機械生成）", "",
             f"## 総合: {sym}", "",
             "## ティア1: 機械事実（✅検証済・高信頼）",
             f"- テスト: {facts['tests']}",
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

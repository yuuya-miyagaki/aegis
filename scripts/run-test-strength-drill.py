#!/usr/bin/env python3
"""Test-strength drill runner (B1). Runs at qa-gate approval time.

Reads a .drill input spec (mutants + scoped test command), applies each mutant
with byte-exact save/restore, runs the test command, and emits a machine
verdict. Exit 0 = PASS (all mutants caught), 1 = FAIL/inconclusive. The verdict
is computed live at approval, so it cannot be forged or go stale.
"""
from __future__ import annotations

import ast
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_SPEC_KEYS = ("test_command", "timeout_seconds", "mutants")
MAX_MUTANTS = 25  # bound approval wall-time; keep ~one mutant per changed hunk
# The harness writes its own input/output here; never treat these as task code.
DRILL_ARTIFACT_PREFIX = "docs/qa-reports/"
# B1 permanent fix (evolution review 2026-06-10): bookkeeping hunks under docs/
# are not task code — they pollute both mutant generation and the coverage
# floor on framework-mixed diffs (38-hunk case, LEARNINGS:37).
DRILL_EXCLUDED_PREFIXES = ("docs/",)  # superset of DRILL_ARTIFACT_PREFIX
# OBS-023 (behavioral review 2026-06-12): vendor/build output swamped the
# drill scope (node_modules hunks demanded mutants). Directory-segment match
# at any depth; src/dist/ collateral is an accepted residual (v160-security 1).
VENDOR_SEGMENTS = frozenset({
    "node_modules", "vendor", "dist", "build", "out", "coverage",
    ".git", ".venv", "venv", ".next", ".nuxt", ".astro",
})


def vendor_excluded(rel: str) -> bool:
    return any(seg in VENDOR_SEGMENTS for seg in rel.split("/")[:-1])


def _drill_excluded(rel: str) -> bool:
    return rel.startswith(DRILL_EXCLUDED_PREFIXES) or vendor_excluded(rel)
# git's well-known empty-tree object; diffing against it makes a not-yet-
# committed project treat all its current code as added.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
BASELINE_OUTPUT_TAIL = 20  # lines of failing baseline output to surface

# R4 (full-review 2026-07-06): evidence.sh は no-run コマンド（--collect-only /
# --dry-run 等）を AEGIS_TEST_NO_RUN_FLAG_REGEX で拒否するが、drill 側が未消費
# だった — collect-only ＋構文破壊 mutant で「1件もテストを実行しない DRILL
# PASS」が成立していた。同じ regex を同じエンジン（bash grep -E）で消費する:
# regex は [[:space:]] POSIX クラスを含み、python re に直接食わせると文字集合
# として誤解釈され silent mis-match になる。
# patterns.sh は --root でなく本スクリプト位置相対で解決する: --root は
# patterns.sh を持たない scratch clone / temp repo を指しうる（root 相対だと
# 全 drill block か fail-open の二択になる）。framework install では scripts/
# と hooks/ が兄弟（update-task.sh の ROOT 解決と同型）。
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_LIB = FRAMEWORK_ROOT / "hooks" / "lib" / "patterns.sh"


def check_no_run_command(cmd: str, patterns_lib: Path | None = None) -> None:
    """Reject a test_command matching AEGIS_TEST_NO_RUN_FLAG_REGEX (single
    source: patterns.sh). Any condition that prevents the check — missing
    patterns.sh, unset regex, grep/subprocess failure — is fail-closed."""
    lib = Path(patterns_lib) if patterns_lib is not None else PATTERNS_LIB
    if not lib.is_file():
        raise DrillError(
            f"patterns.sh not found: {lib} — NO_RUN 検査を実行できないため "
            f"fail-closed（framework install が壊れています）")
    # grep -e: dash 始まり regex がオプションと誤解釈される余地を機構的に排除
    # （マッチ意味論は evidence.sh:128 の grep -qE と同一）
    script = ('source "$1" >/dev/null 2>&1 || exit 3; '
              '[ -n "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || exit 3; '
              'printf %s "$2" | grep -qE -e "$AEGIS_TEST_NO_RUN_FLAG_REGEX"')
    try:
        proc = subprocess.run(
            ["bash", "-c", script, "_", str(lib), cmd],
            capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DrillError(f"NO_RUN 検査の実行に失敗（fail-closed）: {exc}")
    if proc.returncode == 0:
        raise DrillError(
            "test_command が no-run フラグ（--collect-only / --dry-run / "
            "--version 等）を含みます — テストを1件も実行しないコマンドは"
            "テスト強度を証明しません")
    if proc.returncode != 1:
        raise DrillError(
            f"NO_RUN regex を patterns.sh から読み込めません "
            f"(rc={proc.returncode}) — fail-closed")


_SYNTAX_CHECKED_SUFFIXES = (".py", ".sh", ".bash")


def _parses(rel: str, text: str) -> bool | None:
    """Parse verdict for the file type: True/False, or None when no checker
    exists for this extension (unknown types are not judged)."""
    suffix = Path(rel).suffix
    if suffix == ".py":
        try:
            compile(text, rel, "exec")
            return True
        except (SyntaxError, ValueError):
            return False
    if suffix in (".sh", ".bash"):
        try:
            proc = subprocess.run(["bash", "-n"], input=text.encode("utf-8"),
                                  capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0
    return None


def syntax_check_mutants(root: Path, mutants: list[dict]) -> None:
    """R4 併発: 構文破壊 mutant は「テストが assert で捕まえた」ことを証明しない
    （import/収集エラーでも red になる）。適用前 pre-pass で mutant 適用後の全文
    が構文検査（.py→compile() builtin／.sh→bash -n）を通ることを要求する。
    元ファイルが parse 不能なファイルは帰責不能として skip（baseline red が別途
    受け止める）。ファイル不在・行範囲外・original 不一致も skip — それらは
    apply_mutant の既存エラー経路が正本（メッセージを二重化しない）。"""
    broken: list[str] = []
    originals: dict[str, str | None] = {}
    for m in mutants:
        rel = m["file"]
        if Path(rel).suffix not in _SYNTAX_CHECKED_SUFFIXES:
            continue
        if rel not in originals:
            try:
                text = (root / rel).read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                originals[rel] = None
            else:
                originals[rel] = text if _parses(rel, text) else None
        text = originals[rel]
        if text is None:
            continue
        line_no = int(m["line"])
        parts = text.split("\n")
        if line_no < 1 or line_no > len(parts):
            continue
        if parts[line_no - 1] != m["original"]:
            continue
        mutated = parts.copy()
        mutated[line_no - 1] = m["mutated"]
        if _parses(rel, "\n".join(mutated)) is False:
            broken.append(f"{rel}:{line_no}")
    if broken:
        raise DrillError(
            "構文破壊 mutant は assert の強さを証明しません（parse エラーでも"
            "テストは red になるため）。意味を変え構文を保つ mutant に"
            "書き換えてください: " + ", ".join(broken))


class DrillError(Exception):
    """Any condition that makes the drill inconclusive => fail-closed."""


class ConcurrentEditError(DrillError):
    """A third party modified the target file mid-drill; we refuse to overwrite
    their work (the core 'never destroy uncommitted work' promise)."""


def parse_spec(path: Path) -> dict:
    if not path.is_file():
        raise DrillError(f"drill spec not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise DrillError(f"drill spec is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise DrillError("drill spec must be a JSON object")
    for key in REQUIRED_SPEC_KEYS:
        if key not in data:
            raise DrillError(f"drill spec missing required key: {key}")
    if not isinstance(data["mutants"], list) or not data["mutants"]:
        raise DrillError("drill spec 'mutants' must be a non-empty list")
    if len(data["mutants"]) > MAX_MUTANTS:
        raise DrillError(
            f"too many mutants ({len(data['mutants'])} > {MAX_MUTANTS}); "
            f"keep ~one per changed hunk to bound approval time")
    if not isinstance(data["test_command"], str) or not data["test_command"].strip():
        raise DrillError("'test_command' must be a non-empty string")
    # bool is a subclass of int in Python; reject it explicitly
    if (isinstance(data["timeout_seconds"], bool)
            or not isinstance(data["timeout_seconds"], int)
            or data["timeout_seconds"] <= 0):
        raise DrillError("'timeout_seconds' must be a positive integer")
    for m in data["mutants"]:
        if not isinstance(m, dict):
            raise DrillError(f"each mutant must be an object: {m}")
        for k in ("file", "line", "original", "mutated"):
            if k not in m:
                raise DrillError(f"mutant missing key '{k}': {m}")
        if isinstance(m["line"], bool) or not isinstance(m["line"], int):
            raise DrillError(f"mutant 'line' must be an integer: {m}")
        for k in ("file", "original", "mutated"):
            if not isinstance(m[k], str):
                raise DrillError(f"mutant '{k}' must be a string: {m}")
    return data


def _quoted_residual(path: str) -> bool:
    """True when a git-emitted path is still quoted/garbled after
    core.quotepath=off — i.e. it contains control characters (git quotes those
    unconditionally) or failed to decode (errors="replace" marker). Such a path
    does not exist on disk under that spelling, so downstream reads would
    silently skip it — the exact silent-green C-4 closed."""
    return path.startswith('"') or "�" in path


def _tracked_added_lines(root: Path, ref: str) -> dict[str, set[int]]:
    try:
        out = subprocess.run(
            # C-4 (iter54): core.quotepath defaults to ON, mangling non-ASCII
            # paths (テスト.py) into quoted octal escapes; the garbled name then
            # missed every disk read and the file silently vanished from the
            # drill scope AND the judge's secret/stub scans (false-green).
            # Same hardening as hooks/lib/fingerprint.sh:54.
            ["git", "-C", str(root), "-c", "core.quotepath=off",
             "diff", "--unified=0", ref],
            capture_output=True, text=True, check=True,
            errors="replace",  # binary-ish diffs must not crash scope discovery
        ).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        raise DrillError(f"git diff failed: {exc}")
    result: dict[str, set[int]] = {}
    cur_file: str | None = None
    new_lineno: int | None = None
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            # C-4: a path that is STILL quoted (control chars) cannot be read
            # back under this spelling. Excluded prefixes (docs/, vendor) are
            # out of drill scope anyway; anything else fails CLOSED — a silent
            # `continue` here would recreate the same false-green class.
            if _quoted_residual(path):
                probe = path.strip('"')
                probe = probe[2:] if probe.startswith("b/") else probe
                if _drill_excluded(probe):
                    cur_file = None
                    new_lineno = None
                    continue
                raise DrillError(
                    f"git emitted a quoted path even with core.quotepath=off "
                    f"(control characters in the name?): {path!r} — "
                    f"fail-closed; rename the file to a scannable name")
            cur_file = path[2:] if path.startswith("b/") else (
                None if path == "/dev/null" else path)
            new_lineno = None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            new_lineno = int(m.group(1)) if m else None
        elif line.startswith("+") and not line.startswith("+++"):
            if cur_file is not None and new_lineno is not None:
                result.setdefault(cur_file, set()).add(new_lineno)
                new_lineno += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass  # deletions do not advance the new-file line number
    return result


def _untracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            # C-4 (iter54): quotepath=off + errors="replace" — see
            # _tracked_added_lines for the rationale.
            ["git", "-C", str(root), "-c", "core.quotepath=off",
             "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True, errors="replace",
        ).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        raise DrillError(f"git ls-files failed: {exc}")
    files: list[str] = []
    for p in out.splitlines():
        if not p:
            continue
        # C-4: still-quoted names fail closed unless the path is outside drill
        # scope anyway (docs/, vendor) — mirrors _tracked_added_lines.
        if _quoted_residual(p):
            probe = p.strip('"')
            if _drill_excluded(probe):
                continue
            raise DrillError(
                f"git emitted a quoted path even with core.quotepath=off "
                f"(control characters in the name?): {p!r} — "
                f"fail-closed; rename the file to a scannable name")
        files.append(p)
    return files


def resolve_diff_ref(root: Path) -> str:
    """Return the ref to diff the working tree against: 'HEAD' when commits
    exist, else git's empty-tree hash (so a not-yet-committed project treats all
    its code as added). Raises DrillError with actionable guidance when `root` is
    not a git repository — the drill's anti-gaming check fundamentally needs git.
    """
    try:
        inside = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True,
        )
    except OSError as exc:
        raise DrillError(f"git is not available: {exc}")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise DrillError(
            "このドリルは git リポジトリが必要です（変更差分で反ガミングを判定するため）。"
            " 次を実行してください: git init && git add -A && git commit -m init")
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
        capture_output=True, text=True,
    )
    return "HEAD" if head.returncode == 0 else EMPTY_TREE


def added_lines_by_file(root: Path, ref: str = "HEAD",
                        tracked: dict[str, set[int]] | None = None) -> dict[str, set[int]]:
    """Map each changed file to its set of ADDED (+) line numbers. Includes both
    tracked changes (git diff) AND brand-new untracked files (every line of a new
    file counts as added) so 'add a new module' tasks are drillable. The harness'
    own artifacts under docs/qa-reports/ are excluded (they are not task code).
    `tracked` may be a precomputed _tracked_added_lines map to avoid a second
    git diff."""
    result = dict(_tracked_added_lines(root, ref) if tracked is None else tracked)
    for rel in _untracked_files(root):
        if _drill_excluded(rel):
            continue
        f = root / rel
        try:
            data = f.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary/unreadable: cannot mutate as text
        parts = text.split("\n")
        line_count = len(parts) - 1 if data.endswith(b"\n") else len(parts)
        if line_count >= 1:
            result.setdefault(rel, set()).update(range(1, line_count + 1))
    return {f: lines for f, lines in result.items()
            if lines and not _drill_excluded(f)}


def _contiguous_runs(sorted_lines: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for n in sorted_lines:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return runs


# 罠 l (full-review R6 / LEARNINGS:136): コメント/空行/docstring だけの連続ラン
# には behavior-catching mutant を置けない（そこに置いた mutant は必ず
# survived→FAIL）。floor がそれを要求すると sanctioned skip 強制になるため
# 除外する。除外は「充足不可能な要求の削除」のみ: コード行を含む混在ランは
# subset 判定を満たさず floor 維持＝偽造面積は増えない。
# 実需（LEARNINGS の実痛点）は py/sh。js 系トークンは配布先ユーザープロジェクト
# （feature/refactor タスク）向けの安価な拡張。
LINE_COMMENT_TOKENS = {
    ".py": "#", ".sh": "#", ".bash": "#",
    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".mjs": "//", ".cjs": "//",
}


def _docstring_lines(text: str) -> set[int]:
    """Module/class/function docstring line ranges via AST. A file that does
    not parse yields the empty set — no exemption (stricter = safe)."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)
                    and body[0].end_lineno is not None):
                lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def non_coverable_lines(root: Path, rel: str) -> set[int]:
    """Lines of the on-disk file that cannot host a catchable mutant: blank
    lines, line comments (by extension; shebang included), and python
    docstrings. Read/decode failures degrade to 'no exemption'."""
    try:
        text = (root / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    token = LINE_COMMENT_TOKENS.get(Path(rel).suffix)
    exempt: set[int] = set()
    for i, raw in enumerate(text.split("\n"), 1):
        stripped = raw.strip()
        if not stripped or (token and stripped.startswith(token)):
            exempt.add(i)
    if Path(rel).suffix == ".py":
        exempt |= _docstring_lines(text)
    return exempt


def anti_gaming_violations(
    added_by_file: dict[str, set[int]],
    mutants: list[dict],
    coverage_files: set[str] | None = None,
    exempt_lines: dict[str, set[int]] | None = None,
) -> list[str]:
    """(a) each mutant must sit on an added (+) line of SOME changed file; (b)
    every contiguous run of added lines in a covered file must contain >=1 mutant
    (per-hunk coverage floor). Runs made solely of blank/comment/docstring lines
    (see exempt_lines) are exempt — they cannot host a catchable mutant.

    `added_by_file` is the full membership map (tracked + untracked) used for (a).
    `coverage_files` limits the floor (b) to files that are genuinely task code
    (tracked changes, plus untracked files the agent chose to mutate). When None,
    the floor applies to every file (used by unit tests)."""
    violations: list[str] = []
    mutant_lines: dict[str, set[int]] = {}
    for m in mutants:
        mutant_lines.setdefault(m["file"], set()).add(int(m["line"]))

    for m in mutants:
        f, ln = m["file"], int(m["line"])
        if ln not in added_by_file.get(f, set()):
            violations.append(
                f"{f}:{ln} is not an added (+) line in the diff "
                f"(anti-gaming: mutants must sit on changed code)")

    for f, lines in added_by_file.items():
        if coverage_files is not None and f not in coverage_files:
            continue  # untouched untracked/noise file: do not force coverage
        exempt = (exempt_lines or {}).get(f, set())
        for run in _contiguous_runs(sorted(lines)):
            if set(run) <= exempt:
                continue  # comment/blank/docstring-only run: no catchable mutant
            if not (mutant_lines.get(f, set()) & set(run)):
                violations.append(
                    f"{f}: added lines {run[0]}-{run[-1]} have no mutant "
                    f"(coverage floor: every changed hunk needs one)")
    return violations


def _execute(command: str, cwd: Path, timeout_seconds: int) -> tuple[str, str]:
    """Run the scoped test command WITHOUT a shell (no metachar interpretation,
    no command chaining/redirection => the approval-time drill cannot be turned
    into an arbitrary-shell vector). Returns (status, combined_output) where
    status is 'passed' (exit 0), 'failed' (non-zero), 'timeout', or 'error'."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return "error", "command could not be parsed (check quoting)"
    if not argv:
        return "error", "empty command"
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return "timeout", ""
    except OSError as exc:
        return "error", str(exc)
    output = (proc.stdout or b"") + (proc.stderr or b"")
    text = output.decode("utf-8", errors="replace")
    return ("passed" if proc.returncode == 0 else "failed"), text


def run_test(command: str, cwd: Path, timeout_seconds: int) -> str:
    """Status-only wrapper around _execute (used during mutant runs)."""
    return _execute(command, cwd, timeout_seconds)[0]


def check_baseline(command: str, cwd: Path, timeout_seconds: int) -> tuple[str, str]:
    """Run the test command twice on the UNMODIFIED code. Returns
    (status, failure_output) where status is 'green' (both passed), 'red' (a run
    failed), 'flaky' (passed then failed or vice versa), or 'inconclusive'
    (timeout/error). A non-green baseline is fail-closed; failure_output is the
    captured test output so a non-engineer can see WHY it is not green.
    NOTE: assumes an idempotent test command (cleanly runnable twice); a
    deterministic-but-non-idempotent suite may be reported as flaky."""
    first, out1 = _execute(command, cwd, timeout_seconds)
    if first in ("timeout", "error"):
        return "inconclusive", out1
    second, out2 = _execute(command, cwd, timeout_seconds)
    if second in ("timeout", "error"):
        return "inconclusive", out2
    if first == "passed" and second == "passed":
        return "green", ""
    if first == "failed" and second == "failed":
        return "red", out1
    return "flaky", (out1 or out2)


def _current_line(data: bytes, line_no: int) -> str:
    parts = data.decode("utf-8").split("\n")  # \n only, to match git line numbers
    if line_no < 1 or line_no > len(parts):
        raise DrillError(f"line {line_no} out of range (1..{len(parts)})")
    return parts[line_no - 1]


def _replace_line(data: bytes, line_no: int, new_line: str) -> bytes:
    parts = data.decode("utf-8").split("\n")
    if line_no < 1 or line_no > len(parts):
        raise DrillError(f"line {line_no} out of range (1..{len(parts)})")
    parts[line_no - 1] = new_line
    return "\n".join(parts).encode("utf-8")


def apply_mutant_and_test(root: Path, mutant: dict, command: str,
                          timeout_seconds: int) -> str:
    """Apply ONE mutant with byte-exact save/restore, run the test, restore.
    Returns 'caught' (test went red) or 'survived' (test stayed green). Raises
    DrillError on any inconclusive/abort condition (fail-closed). Restore runs in
    finally; if a third party changed the file mid-run we do NOT overwrite
    (ConcurrentEditError), and on restore-verification failure the backup is
    KEPT so the user can recover."""
    target = root / mutant["file"]
    if not target.is_file():
        raise DrillError(f"mutant target not found: {target}")
    original_bytes = target.read_bytes()

    if _current_line(original_bytes, int(mutant["line"])) != mutant["original"]:
        raise DrillError(
            f"line {mutant['line']} of {mutant['file']} does not match "
            f"'original'; refusing to mutate (line drift)")

    backup = tempfile.NamedTemporaryFile(delete=False)
    backup.write(original_bytes)
    backup.close()
    backup_path = Path(backup.name)

    mutant_bytes: bytes | None = None
    try:
        mutant_bytes = _replace_line(
            original_bytes, int(mutant["line"]), mutant["mutated"])
        target.write_bytes(mutant_bytes)
        outcome = run_test(command, root, timeout_seconds)
        if outcome == "failed":
            return "caught"
        if outcome == "passed":
            return "survived"
        raise DrillError(f"test command was inconclusive ({outcome})")
    finally:
        current = target.read_bytes() if target.is_file() else b""
        if mutant_bytes is not None and current == mutant_bytes:
            target.write_bytes(backup_path.read_bytes())
            if target.read_bytes() != original_bytes:
                # keep the backup: it is the user's recovery copy
                raise DrillError(
                    f"restore verification failed for {target}; "
                    f"original bytes preserved at {backup_path}")
            backup_path.unlink(missing_ok=True)
        elif current == original_bytes:
            backup_path.unlink(missing_ok=True)  # nothing written / already clean
        else:
            # third party (editor/watcher/other session) changed the file mid-run
            raise ConcurrentEditError(
                f"{target} was modified during the drill; refusing to overwrite. "
                f"Original bytes preserved at {backup_path}")


def write_report(report_path: Path, *, verdict: str, total: int, caught: int,
                 baseline: str, survived: list[str]) -> None:
    """Write the machine block (harness-authored, not LLM prose). The qa agent
    appends a plain-Japanese explanation block below this when presenting."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    survived_repr = "[]" if not survived else "[" + ", ".join(survived) + "]"
    report_path.write_text(
        "# テスト強度ドリル結果（機械ブロック・ハーネス生成）\n\n"
        "```\n"
        f"verdict: {verdict}\n"
        f"mutants_total: {total}\n"
        f"mutants_caught: {caught}\n"
        f"baseline: {baseline}\n"
        f"survived: {survived_repr}\n"
        "```\n",
        encoding="utf-8",
    )


def run_drill(root: Path, spec_path: Path, report_path: Path) -> int:
    """Orchestrate. Returns 0 (PASS) or 1 (FAIL/inconclusive). Never raises:
    every DrillError becomes a fail-closed verdict + non-zero exit."""
    try:
        spec = parse_spec(spec_path)
        cmd = spec["test_command"]
        timeout = int(spec["timeout_seconds"])
        check_no_run_command(cmd)
        # transparency: surface what will actually be executed at approval time
        print(f"test command (executed at approval): {cmd}")

        ref = resolve_diff_ref(root)  # 'HEAD', or empty-tree when no commits yet
        tracked_map = _tracked_added_lines(root, ref)
        added = added_lines_by_file(root, ref, tracked=tracked_map)
        # coverage floor applies to tracked changes (clearly task code) plus any
        # untracked file the agent actually mutated; untouched untracked files
        # (scratch/noise) are not force-covered.
        tracked = {f for f in tracked_map
                   if not _drill_excluded(f)}
        mutant_files = {m["file"] for m in spec["mutants"]}
        coverage_files = tracked | (mutant_files & set(added))
        # 罠 l: コメント/空行/docstring だけのランは floor 免除（透明化のため
        # 免除ランを承認ログに明示する）
        exempt = {f: non_coverable_lines(root, f) for f in coverage_files}
        for f in sorted(coverage_files & set(added)):
            for run in _contiguous_runs(sorted(added[f])):
                if set(run) <= exempt.get(f, set()):
                    print(f"coverage floor exempt (comment/blank/docstring "
                          f"only): {f}:{run[0]}-{run[-1]}")
        ag = anti_gaming_violations(added, spec["mutants"],
                                    coverage_files=coverage_files,
                                    exempt_lines=exempt)
        if ag:
            print("DRILL BLOCKED (anti-gaming):")
            for v in ag:
                print(f"  - {v}")
            write_report(report_path, verdict="FAIL", total=len(spec["mutants"]),
                         caught=0, baseline="n/a", survived=[])
            return 1

        syntax_check_mutants(root, spec["mutants"])

        base, base_output = check_baseline(cmd, root, timeout)
        if base != "green":
            print(f"DRILL BLOCKED (baseline {base}): tests must be green and "
                  f"stable before drilling.")
            if base_output.strip():
                print("---- test output (last lines) ----")
                tail = base_output.strip().splitlines()[-BASELINE_OUTPUT_TAIL:]
                print("\n".join(tail))
            write_report(report_path, verdict="FAIL", total=len(spec["mutants"]),
                         caught=0, baseline=base, survived=[])
            return 1

        survived: list[str] = []
        caught = 0
        for m in spec["mutants"]:
            outcome = apply_mutant_and_test(root, m, cmd, timeout)
            if outcome == "caught":
                caught += 1
            else:
                survived.append(f"{m['file']}:{m['line']}")

        verdict = "PASS" if not survived else "FAIL"
        write_report(report_path, verdict=verdict, total=len(spec["mutants"]),
                     caught=caught, baseline="green", survived=survived)
        if survived:
            print("DRILL FAIL — these mutants survived (tests have a hole):")
            for s in survived:
                print(f"  - {s}")
            return 1
        print("DRILL PASS — all mutants caught.")
        return 0
    except ConcurrentEditError as exc:
        print(f"DRILL ABORTED (concurrent edit): {exc}")
        return 1
    except DrillError as exc:
        print(f"DRILL BLOCKED (fail-closed): {exc}")
        try:
            write_report(report_path, verdict="FAIL", total=0, caught=0,
                         baseline="inconclusive", survived=[])
        except OSError:
            pass
        return 1


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Test-strength drill runner (B1)")
    p.add_argument("--root", default=".")
    p.add_argument("--spec", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args(argv)
    return run_drill(Path(args.root).resolve(), Path(args.spec), Path(args.report))


if __name__ == "__main__":
    sys.exit(main())

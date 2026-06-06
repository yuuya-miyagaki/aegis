#!/usr/bin/env python3
"""Test-strength drill runner (B1). Runs at qa-gate approval time.

Reads a .drill input spec (mutants + scoped test command), applies each mutant
with byte-exact save/restore, runs the test command, and emits a machine
verdict. Exit 0 = PASS (all mutants caught), 1 = FAIL/inconclusive. The verdict
is computed live at approval, so it cannot be forged or go stale.
"""
from __future__ import annotations

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
    for m in data["mutants"]:
        for k in ("file", "line", "original", "mutated"):
            if k not in m:
                raise DrillError(f"mutant missing key '{k}': {m}")
    return data


def _tracked_added_lines(root: Path, ref: str) -> dict[str, set[int]]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--unified=0", ref],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        raise DrillError(f"git diff failed: {exc}")
    result: dict[str, set[int]] = {}
    cur_file: str | None = None
    new_lineno: int | None = None
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
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
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError) as exc:
        raise DrillError(f"git ls-files failed: {exc}")
    return [p for p in out.splitlines() if p]


def added_lines_by_file(root: Path, ref: str = "HEAD") -> dict[str, set[int]]:
    """Map each changed file to its set of ADDED (+) line numbers. Includes both
    tracked changes (git diff) AND brand-new untracked files (every line of a new
    file counts as added) so 'add a new module' tasks are drillable. The harness'
    own artifacts under docs/qa-reports/ are excluded (they are not task code)."""
    result = _tracked_added_lines(root, ref)
    for rel in _untracked_files(root):
        if rel.startswith(DRILL_ARTIFACT_PREFIX):
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
            if lines and not f.startswith(DRILL_ARTIFACT_PREFIX)}


def _contiguous_runs(sorted_lines: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for n in sorted_lines:
        if runs and n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return runs


def anti_gaming_violations(
    added_by_file: dict[str, set[int]],
    mutants: list[dict],
    coverage_files: set[str] | None = None,
) -> list[str]:
    """(a) each mutant must sit on an added (+) line of SOME changed file; (b)
    every contiguous run of added lines in a covered file must contain >=1 mutant
    (per-hunk coverage floor).

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
        for run in _contiguous_runs(sorted(lines)):
            if not (mutant_lines.get(f, set()) & set(run)):
                violations.append(
                    f"{f}: added lines {run[0]}-{run[-1]} have no mutant "
                    f"(coverage floor: every changed hunk needs one)")
    return violations


def run_test(command: str, cwd: Path, timeout_seconds: int) -> str:
    """Run the scoped test command WITHOUT a shell (no metachar interpretation,
    no command chaining/redirection => the approval-time drill cannot be turned
    into an arbitrary-shell vector). Returns 'passed' (exit 0), 'failed'
    (non-zero), 'timeout', or 'error' (unparseable/could not start)."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return "error"
    if not argv:
        return "error"
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except OSError:
        return "error"
    return "passed" if proc.returncode == 0 else "failed"


def check_baseline(command: str, cwd: Path, timeout_seconds: int) -> str:
    """Run the test command twice on the UNMODIFIED code. Returns 'green' (both
    passed), 'red' (a run failed), 'flaky' (passed then failed or vice versa),
    or 'inconclusive' (timeout/error). A non-green baseline is fail-closed.
    NOTE: assumes an idempotent test command (cleanly runnable twice); a
    deterministic-but-non-idempotent suite may be reported as flaky."""
    first = run_test(command, cwd, timeout_seconds)
    if first in ("timeout", "error"):
        return "inconclusive"
    second = run_test(command, cwd, timeout_seconds)
    if second in ("timeout", "error"):
        return "inconclusive"
    if first == "passed" and second == "passed":
        return "green"
    if first == "failed" and second == "failed":
        return "red"
    return "flaky"


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
        # transparency: surface what will actually be executed at approval time
        print(f"test command (executed at approval): {cmd}")

        added = added_lines_by_file(root, "HEAD")
        # coverage floor applies to tracked changes (clearly task code) plus any
        # untracked file the agent actually mutated; untouched untracked files
        # (scratch/noise) are not force-covered.
        tracked = {f for f in _tracked_added_lines(root, "HEAD")
                   if not f.startswith(DRILL_ARTIFACT_PREFIX)}
        mutant_files = {m["file"] for m in spec["mutants"]}
        coverage_files = tracked | (mutant_files & set(added))
        ag = anti_gaming_violations(added, spec["mutants"],
                                    coverage_files=coverage_files)
        if ag:
            print("DRILL BLOCKED (anti-gaming):")
            for v in ag:
                print(f"  - {v}")
            write_report(report_path, verdict="FAIL", total=len(spec["mutants"]),
                         caught=0, baseline="n/a", survived=[])
            return 1

        base = check_baseline(cmd, root, timeout)
        if base != "green":
            print(f"DRILL BLOCKED (baseline {base}): tests must be green and "
                  f"stable before drilling.")
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

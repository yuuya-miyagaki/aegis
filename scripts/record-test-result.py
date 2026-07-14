#!/usr/bin/env python3
"""Manual fallback writer for the E1 evidence log: run the (trusted, scoped)
test command itself and append the result with src:"manual". Used when tests
were run OUTSIDE Claude Code (no hook observation). Same schema as
hooks/lib/evidence.sh; the judge treats manual and observed alike because this
script executed the command itself (trusted runner, not self-report).

Validation contract (iter70): the command is validated BEFORE execution and
BEFORE any record — runner match (judge.runner_cmd_matches, judge-identical
normalization), non-shell-compat (env-assign prefix / bare shell-operator
argv tokens, which this shell-less exec would pass through as red-recording
arguments), and NO_RUN (drill.check_no_run_command). A non-matching command
is a usage error (rc2, stderr guidance, no log write, no execution). The
accepted set is single-sourced with the judge's visible set, so a command the
judge could never recognize is never recorded."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import shlex
import sys
import time
from pathlib import Path

# argv tokens that a shell would interpret as operators; passed to a shell-less
# exec they become literal red-recording arguments. Conservative exact-match
# set only — e.g. -k "a and b" is untouched.
_SHELL_OP_TOKENS = frozenset({"&&", "||", ";", "|", "&"})


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Record test result (E1 manual)")
    p.add_argument("--root", default=".")
    p.add_argument("command")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    drill = _load("drill_mod", "run-test-strength-drill.py")
    judge = _load("judge_mod", "build-judge-card.py")

    usage = ('正しい例: python3 scripts/record-test-result.py '
             '"python3 -m pytest -q"')

    def _reject(reason: str) -> int:
        print(f"record-test-result: {reason}\n{usage}", file=sys.stderr)
        return 2

    # 1) runner match — [:500] matches the cmd that would be persisted / that
    # the judge reads, so the checker and the consumer see the same input.
    match = judge.runner_cmd_matches(root, args.command[:500])
    if match is None:
        return _reject("patterns.sh を読み込めません — runner 照合を実行できない"
                       "ため fail-closed（framework install が壊れています）")
    if match is False:
        return _reject(
            "テストランナーコマンドではありません（AEGIS_TEST_RUNNER_REGEX "
            "非該当）— judge が読めないエントリは記録しません")

    # 2) non-shell-compat — this script runs the command WITHOUT a shell, so
    # env-assignment prefixes and shell-operator tokens are not interpreted;
    # they would be passed as arguments and produce a spurious red record.
    try:
        argv = shlex.split(args.command)
    except ValueError as exc:
        return _reject(f"コマンドを解析できません（クォート不整合）: {exc}")
    if not argv:
        return _reject("コマンドが空です")
    if "=" in argv[0]:
        return _reject(
            f"argv[0] に env 代入 prefix が含まれます（{argv[0]!r}）— shell なし"
            "実行では解釈されず引数事故になります")
    if any(tok in _SHELL_OP_TOKENS for tok in argv):
        return _reject(
            "シェル演算子トークン（&& || ; | &）が含まれます — shell なし実行"
            "では引数として渡り red 記録になります")

    # 3) NO_RUN — reuse drill's check against the TARGET root's patterns.sh
    # (same file the judge reads), so a zero-test command cannot be recorded.
    try:
        drill.check_no_run_command(
            args.command, patterns_lib=root / "hooks" / "lib" / "patterns.sh")
    except drill.DrillError as exc:
        return _reject(str(exc))

    status_code, output = drill._execute(args.command, root, 600)
    status = "ok" if status_code == "passed" else "fail"
    out_bytes = (output or "")[:65536].encode("utf-8", errors="replace")
    entry = {
        "v": 1,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "src": "manual",
        "cmd": args.command[:500],
        "status": status,
        "payload_sha": hashlib.sha256(out_bytes).hexdigest(),
        "fp": judge.current_fingerprint(root),
    }
    log = root / ".claude" / "evidence-log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"recorded: {'green' if status == 'ok' else 'red'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

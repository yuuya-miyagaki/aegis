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
judge could never recognize is never recorded.

Zero-run forgery — CLOSED (SF-014 iter71): a command that MATCHES a runner yet
executes ZERO tests and exits 0 (e.g. `unittest discover -p <no-match>`, which
exits 0 unlike pytest's exit 5, or `npm test` bound to a `"test":"true"`
script) is now rejected. A green (exit 0) record additionally requires the
POSITIVE marker verdict (hooks/lib/marker.sh — the same 4-stage proof the hook
observer consumes: N>=1 tests actually ran). No marker -> rc2, no log write. A
red run keeps recording as-is (failure is fail-visible, not a forge vector).

Residual (intentionally NOT closed): the marker is an OUTPUT-based proof, so two
classes it cannot distinguish remain, both in the SF-014 bucket:
  (a) arbitrary-script output — e.g. an `npm test` script that echoes a
      marker-shaped line (`Tests: 3 passed` etc.).
  (b) all-skip suites — a unittest suite where every test is @skip'd still
      prints `Ran N tests ... OK (skipped=N)` (unittest counts a skipped test as
      "run"), and go prints `ok pkg dur` when every test t.Skip()s; both satisfy
      the marker with ZERO bodies executed. (pytest `N skipped in` and cargo
      `0 passed` are correctly rejected — see tests/test_marker_lib.py
      TestSkipSuiteResidual.)
We do NOT chase either by enumeration (a denylist regression = reproducing
SF-014). Contained by defence-in-depth: fingerprint / judge / human preview /
drill (a skip/echo baseline kills no mutant -> the drill FAILs). The permanent
fix is a passed/failed-COUNT positive proof (not just a pass-marker match).
Handed off to the SF-014 docs update (iter71 docs phase) and the audit_deps
positive-proof track (iter72).

The accepted green entry's optional `"marker": true` is an additive audit-
transparency field; the judge does not consume it."""
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
             '"python3 -m pytest"')

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
        # Defensive guard (iter70 review Finding 1): step 1's runner match
        # already rejects an empty/whitespace-only command (it matches no
        # runner regex), so this is not reachable via the current step order.
        # Kept so a future reordering of the checks stays fail-closed.
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
    # 4) positive proof (SF-014 iter71): a GREEN record additionally requires
    # the shared 4-stage marker verdict (hooks/lib/marker.sh — the same
    # implementation the hook observer consumes) over the FULL output.
    # payload_sha keeps its 64 KiB cap below, but runners print their summary
    # at the TAIL — never pass the capped prefix to the verdict.
    # red (exit != 0) is recorded as-is: failure is fail-visible, not a
    # gaming vector.
    # verdict uses the TARGET root's marker.sh (--root-resolved) — same
    # "judge reads the co-located install" basis as check_no_run_command's
    # patterns_lib. marker.sh sources its own dir's patterns.sh, so a
    # patterns/marker mismatch is structurally impossible. exit_code stays 0
    # (the default): the green path is defined by _execute's returncode==0, so
    # the constant 0 is correct (pytest exit 5 falls to the red path and is
    # recorded as red, as before).
    marker_proven = False
    if status == "ok":
        try:
            marker_proven = drill.marker_verdict(
                output or "", args.command[:500],
                marker_lib=root / "hooks" / "lib" / "marker.sh")
        except drill.DrillError as exc:
            return _reject(f"marker 検査を実行できません — fail-closed: {exc}")
        if not marker_proven:
            return _reject(
                "exit 0 ですが、テスト実行の positive proof（ランナーのサマリ "
                "marker）が出力にありません — 0 件実行の green（例: unittest "
                "discover のパターン不一致 / `npm test` が `true` に束縛）は"
                "記録しません。pytest は `-q` を外して実行してください（marker "
                "はデフォルト出力の `===== N passed =====` 行）。対応ランナー: "
                "pytest（デフォルト出力）/ jest / vitest / go test / cargo test "
                "/ unittest。未収載ランナーは hooks/lib/patterns.sh の marker "
                "追加を検討してください")
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
    if marker_proven:
        entry["marker"] = True  # additive 監査フィールド（judge 非消費）
    log = root / ".claude" / "evidence-log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"recorded: {'green' if status == 'ok' else 'red'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

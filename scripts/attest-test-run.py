#!/usr/bin/env python3
"""Execution attestation for pytest (iter78, SF-014/SF-022 root fix).

Runs the given pytest command WITHOUT a shell (argv spawn — exit laundering
like `; true` is impossible by construction), injects the event plugin
(scripts/aegis_attest_plugin.py), and reconciles the structured event stream
against the child's REAL exit code (waitpid). The child's stdout/stderr are
inherited, NEVER parsed — fake output cannot produce events. A green record
requires exit==0 AND executed>=1 AND failed==errors==collection_errors==0,
where executed = passed+failed+xfailed+xpassed from call-phase events (skips
excluded; an all-xfail suite IS executed — closes the SF-015 false negative
on this path). Any evaluation gap (missing sessionfinish, exitstatus !=
returncode, corrupt event JSON, timeout) is rc2: no record, no green —
fail-closed. Residual ceiling (documented, pre-existing class): in-process
sabotage (conftest unregistering the plugin / forging events) and
hand-written log entries — deliberate self-deception, contained by
defence-in-depth (drill, human preview, fingerprint). Plugin suppression via
PYTEST_ADDOPTS / ini addopts (`-p no:aegis_attest_plugin`) collapses to the
same rc2 (missing events) — it cannot mint a green."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_SHELL_OP_TOKENS = frozenset({"&&", "||", ";", "|", "&"})


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Attest pytest execution (iter78)")
    p.add_argument("--root", default=".")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("command")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    judge = _load("judge_mod", "build-judge-card.py")

    usage = ('正しい例: python3 scripts/attest-test-run.py '
             '"python3 -m pytest"')

    def _reject(reason: str) -> int:
        print(f"attest-test-run: {reason}\n{usage}", file=sys.stderr)
        return 2

    # 1) pytest family — [:500] matches the cmd that would be persisted / that
    # the judge reads, so the checker and the consumer see the same input.
    fam = judge.is_pytest_family_cmd(root, args.command[:500])
    if fam is None:
        return _reject("patterns.sh を読み込めません — fail-closed"
                       "（framework install が壊れています）")
    if fam is False:
        return _reject(
            "pytest family ではありません。非 pytest ランナーは "
            "scripts/record-test-result.py を使ってください")

    # 2) non-shell-compat — this spawns argv WITHOUT a shell, so env-assignment
    # prefixes and shell-operator tokens are not interpreted; they would be
    # passed as arguments (spurious red) or, worse, mask exit laundering.
    try:
        cmd_argv = shlex.split(args.command)
    except ValueError as exc:
        return _reject(f"コマンドを解析できません（クォート不整合）: {exc}")
    if not cmd_argv:
        return _reject("コマンドが空です")
    if "=" in cmd_argv[0]:
        return _reject(
            f"argv[0] に env 代入 prefix が含まれます（{cmd_argv[0]!r}）— shell "
            "なし実行では解釈されず引数事故になります")
    if any(tok in _SHELL_OP_TOKENS for tok in cmd_argv):
        return _reject(
            "シェル演算子トークン（&& || ; | &）が含まれます — shell なし実行"
            "では引数として渡り exit 洗浄の温床になります")

    # 3) plugin suppression / override — the attestation is only valid if OUR
    # plugin is the one loaded. Any `-p` targeting aegis_attest_plugin (bare
    # `-p no:aegis_attest_plugin`, joined `-pno:aegis_attest_plugin`, or even a
    # redundant re-register) can neutralize positive proof, so reject it.
    for i, tok in enumerate(cmd_argv):
        val = None
        if tok == "-p":
            if i + 1 < len(cmd_argv):
                val = cmd_argv[i + 1]
        elif tok.startswith("-p"):
            val = tok[2:]
        if val is not None and "aegis_attest_plugin" in val:
            return _reject(
                "attestation プラグインの指定/打ち消しは禁止です"
                "（-p ... aegis_attest_plugin）")

    # 4) event file — a per-run temp JSONL in <root>/.claude/tmp. Deleted in
    # the finally below on EVERY path (green / red / rc2 / timeout).
    tmp_dir = root / ".claude" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, event_path = tempfile.mkstemp(prefix="attest-", suffix=".jsonl",
                                      dir=str(tmp_dir))
    os.close(fd)
    event_path = Path(event_path)

    try:
        # 5) spawn WITHOUT a shell. stdout/stderr inherited (NOT captured / NOT
        # parsed). PYTHONPATH front-prepends scripts/ so `-p aegis_attest_plugin`
        # resolves to our plugin; AEGIS_ATTEST_EVENT_PATH points the plugin at
        # the event file.
        child_env = os.environ.copy()
        scripts_dir = str(Path(__file__).resolve().parent)
        prev_pp = child_env.get("PYTHONPATH", "")
        child_env["PYTHONPATH"] = (
            scripts_dir + (os.pathsep + prev_pp if prev_pp else ""))
        child_env["AEGIS_ATTEST_EVENT_PATH"] = str(event_path.resolve())
        try:
            proc = subprocess.run(
                cmd_argv + ["-p", "aegis_attest_plugin"],
                cwd=str(root), timeout=args.timeout, env=child_env,
                shell=False)
        except subprocess.TimeoutExpired:
            return _reject("timeout — attest 不成立")

        # 6) read + aggregate events. A single corrupt line fails CLOSED.
        raw_bytes = event_path.read_bytes()
        # strict decode: the plugin only ever writes valid UTF-8 (json.dumps),
        # so a non-UTF-8 byte in the stream IS corruption (in-process
        # sabotage / partial write) — rc2 like any other corrupt line, not a
        # bare UnicodeDecodeError traceback (grill-code iter78: rc1 would
        # falsely signal "red recorded").
        try:
            raw_text = raw_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return _reject("イベントストリーム破損（不正バイト）— attest 不成立")
        calls: dict[str, tuple] = {}
        setup_teardown_errors = 0
        setup_skipped = 0
        call_skipped_nonxfail = 0
        collection_errors = 0
        sessionfinish = None
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except (ValueError, TypeError):
                return _reject("イベント JSON 破損 — attest 不成立")
            kind = ev.get("e")
            if kind == "sessionfinish":
                sessionfinish = ev.get("exitstatus")
            elif kind == "collect_error":
                collection_errors += 1
            elif kind == "test":
                when = ev.get("when")
                outcome = ev.get("outcome")
                wasxfail = bool(ev.get("wasxfail"))
                if when == "call":
                    calls[ev.get("nodeid")] = (outcome, wasxfail)
                    if outcome == "skipped" and not wasxfail:
                        call_skipped_nonxfail += 1
                elif when in ("setup", "teardown"):
                    if outcome == "failed":
                        setup_teardown_errors += 1
                    if when == "setup" and outcome == "skipped":
                        setup_skipped += 1

        passed = failed = xfailed = xpassed = 0
        for outcome, wasxfail in calls.values():
            if outcome == "passed":
                if wasxfail:
                    xpassed += 1
                else:
                    passed += 1
            elif outcome == "failed":
                failed += 1
            elif outcome == "skipped" and wasxfail:
                xfailed += 1
        executed = passed + failed + xfailed + xpassed
        errors = setup_teardown_errors
        skipped = setup_skipped + call_skipped_nonxfail

        rc = proc.returncode

        # 7) reconciliation (order matters — every gap is rc2, no record).
        if sessionfinish is None:
            return _reject(
                "イベント欠落＝attest 不成立（プラグインが妨害された可能性）")
        if sessionfinish != rc:
            return _reject("exit 突合不一致")
        if rc == 0 and (failed or errors or collection_errors):
            return _reject("exit 0 なのに失敗イベント＝不整合")
        if rc == 0 and executed == 0:
            return _reject("実行 0 件（all-skip / collect-only）は green 不成立")

        # 8) record. rc==0 -> green (ok); any rc!=0 -> red (fail, fail-visible;
        # pytest exit 5 = collected 0 is red too).
        status = "ok" if rc == 0 else "fail"
        payload_sha = hashlib.sha256(raw_bytes).hexdigest()
        entry = {
            "v": 1,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "src": "attested",
            "cmd": args.command[:500],
            "status": status,
            "payload_sha": payload_sha,
            "fp": judge.current_fingerprint(root),
            "counts": {
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "errors": errors,
                "xfailed": xfailed,
                "xpassed": xpassed,
                "collection_errors": collection_errors,
            },
            "exit": rc,
        }
        log = root / ".claude" / "evidence-log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"attested: {'green' if status == 'ok' else 'red'}")
        return 0 if status == "ok" else 1
    finally:
        try:
            event_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())

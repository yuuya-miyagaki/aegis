#!/usr/bin/env python3
"""Manual fallback writer for the E1 evidence log: run the (trusted, scoped)
test command itself and append the result with src:"manual". Used when tests
were run OUTSIDE Claude Code (no hook observation). Same schema as
hooks/lib/evidence.sh; the judge treats manual and observed alike because this
script executed the command itself (trusted runner, not self-report)."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path


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

#!/usr/bin/env python3
"""Record a test result for the B2 judge card: run the (trusted, scoped) test
command and write docs/qa-reports/test-result.json with {status, fingerprint}.
Kept separate from the judge builder so the builder stays a pure reader."""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Record test result (B2)")
    p.add_argument("--root", default=".")
    p.add_argument("command")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    drill = _load("drill_mod", "run-test-strength-drill.py")
    judge = _load("judge_mod", "build-judge-card.py")
    status_code = drill._execute(args.command, root, 600)[0]
    status = "green" if status_code == "passed" else "red"
    out = root / "docs" / "qa-reports" / "test-result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"status": status, "code_fingerprint": judge.code_fingerprint(root)}),
        encoding="utf-8")
    print(f"recorded: {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

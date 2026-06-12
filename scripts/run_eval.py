#!/usr/bin/env python3
"""Tiered evaluation runner for framework root."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

TIER1_VALIDATORS = [
    {"name": "check_status", "script": "check_status.py", "args": ["--root"]},
    {"name": "status_doctor", "script": "status_doctor.py", "args": ["--root"]},
    {"name": "check_framework_contract", "script": "check_framework_contract.py", "args": ["--root"]},
    {"name": "check_reference_drift", "script": "check_reference_drift.py", "args": ["--root"]},
]


def run_tier1(root: Path) -> int:
    """Run all tier 1 validators and print summary."""
    results: list[dict[str, str]] = []
    any_fail = False
    any_warning = False

    for v in TIER1_VALIDATORS:
        script_path = SCRIPTS_DIR / v["script"]
        cmd = ["python3", str(script_path)] + v["args"] + [str(root)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            output = stdout or stderr

            if proc.returncode != 0:
                status = "FAIL"
                any_fail = True
            elif "WARNING" in (stdout + stderr).upper():
                status = "WARNING"
                any_warning = True
            else:
                status = "PASS"

            results.append({"name": v["name"], "status": status, "output": output})
        except subprocess.TimeoutExpired:
            results.append({"name": v["name"], "status": "FAIL", "output": "timeout"})
            any_fail = True
        except FileNotFoundError:
            results.append({"name": v["name"], "status": "FAIL", "output": "script not found"})
            any_fail = True

    # Print summary table
    print("=== Tier 1 Evaluation ===")
    print("")
    print(f"  {'Validator':<30} {'Status':<10}")
    print(f"  {'-' * 30} {'-' * 10}")
    for r in results:
        print(f"  {r['name']:<30} {r['status']:<10}")

    # Print details for non-PASS
    for r in results:
        if r["status"] != "PASS" and r["output"]:
            print(f"\n--- {r['name']} ({r['status']}) ---")
            for line in r["output"].splitlines():
                print(f"  {line}")

    print("")
    if any_fail:
        print("Result: FAIL")
        return 1
    elif any_warning:
        print("Result: PASS (with warnings)")
        return 0
    else:
        print("Result: PASS")
        return 0


def run_tier(tier_num: int, script_name: str, label: str) -> int:
    """Run a single-script tier evaluation."""
    script_path = SCRIPTS_DIR / script_name
    try:
        proc = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="")
        return proc.returncode
    except subprocess.TimeoutExpired:
        print(f"=== {label} ===\n\nResult: FAIL (timeout)\n")
        return 1
    except FileNotFoundError:
        print(f"=== {label} ===\n\nResult: FAIL (script not found: {script_name})\n")
        return 1


def run_tier0(root: Path) -> int:
    """Tier 0: unittest discovery. Runs all tests in tests/ directory."""
    print("=== Tier 0: Unit Tests ===\n")
    try:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"],
            capture_output=True,
            text=True,
            # 507 subprocess-heavy tests run ~135s; 120s silently failed the
            # whole tier on suite growth (v1.6.0).
            timeout=300,
            cwd=str(root),
        )
        print(proc.stderr, end="")  # unittest writes to stderr
        if proc.stdout:
            print(proc.stdout, end="")
        print("")
        if proc.returncode != 0:
            print("Result: FAIL")
        else:
            print("Result: PASS")
        return proc.returncode
    except subprocess.TimeoutExpired:
        print("Result: FAIL (timeout)\n")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run tiered evaluation")
    parser.add_argument("--root", default=None, help="Project root (default: script parent dir)")
    parser.add_argument("--tier", type=int, default=1, choices=[0, 1, 2, 3], help="Evaluation tier")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root)
    else:
        root = Path(__file__).resolve().parent.parent

    if args.tier == 0:
        return run_tier0(root)
    elif args.tier == 1:
        return run_tier1(root)
    elif args.tier == 2:
        return run_tier(2, "eval_scaffold_smoke.py", "Tier 2: Scaffold Smoke Tests")
    elif args.tier == 3:
        return run_tier(3, "eval_scenario.py", "Tier 3: Scenario Contract Checks")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Tier 2 evaluation: scaffold smoke tests.

Runs setup.sh for each profile, validates the file manifest with
check_framework_contract.py, AND fires representative installed hooks to prove
the scaffold's PaC enforcement layer actually RUNS (not just that files exist).

The hook-execution check exists because file-existence alone is blind to a
source-time break: every hook `source`s hooks/lib/emit.sh, so if setup.sh fails
to copy that lib the hooks die with "No such file" and the moat silently
fails open. Firing a hook is the only way to catch that (audit F6, 2026-06-07).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
SETUP_SH = REPO_ROOT / "bin" / "setup.sh"
CONTRACT_PY = SCRIPTS_DIR / "check_framework_contract.py"

# Single source of truth for the intentionally-divergent scaffold-safe command
# variants. Importing it (rather than hardcoding the list) makes the
# command-surface check self-extending: adding a command to MIRROR_ALLOWLIST
# automatically requires it to be wired into setup.sh resolve_source.
sys.path.insert(0, str(SCRIPTS_DIR))
from check_reference_drift import MIRROR_ALLOWLIST  # noqa: E402

# Profiles validated by file manifest (contract). full --profile validates the
# framework repo itself (ignores --root), so it cannot be contract-validated as a
# scaffold; it is exercised by the hook-execution check below instead.
PROFILES = ["minimal", "standard"]

# Every profile that installs ANY hook installs session-start.sh, which sources
# hooks/lib/emit.sh. So even `minimal` is in scope for the lib-presence check —
# do not assume minimal ships no hooks.
REQUIRED_HOOK_LIBS = ["emit.sh", "patterns.sh"]


def _scaffold(profile: str, target: Path) -> tuple[bool, str]:
    """Run setup.sh for *profile* into *target*. Returns (ok, detail)."""
    result = subprocess.run(
        ["bash", str(SETUP_SH), f"--profile={profile}", f"--target={target}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return False, f"setup.sh --profile={profile} failed: {detail}"
    return True, "scaffolded"


def _fire_hook(target: Path, hook_rel: str, stdin: str) -> subprocess.CompletedProcess:
    """Fire an installed hook from the scaffold root with *stdin* on its stdin."""
    return subprocess.run(
        ["bash", hook_rel],
        cwd=str(target),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
    )


def verify_hooks_runnable(target: Path, profile: str) -> tuple[bool, str]:
    """Prove the scaffold's installed hooks actually RUN (not just exist).

    Judged by exit code + fixed stdout, never by matching an OS/locale-dependent
    stderr string like "No such file": a source-time break yields exit 1 with
    empty stdout, which both assertions below catch deterministically.
    """
    hooks_dir = target / "hooks"
    if not hooks_dir.is_dir():
        # A profile that installs no hooks at all has no moat to verify.
        return True, f"{profile}: no hooks installed"

    # (B-3) lib presence: every installed hook sources emit.sh; check-destructive
    # also sources patterns.sh. Both must be delivered by setup.sh.
    for lib in REQUIRED_HOOK_LIBS:
        if not (hooks_dir / "lib" / lib).exists():
            return False, (
                f"{profile}: hooks/lib/{lib} missing — installed hooks cannot "
                f"source it (moat fails open at install)"
            )

    # (B-1) check-gate.sh execution (installed by standard/full). A docs path hits
    # check-gate's early allowlist, so it returns emit_allow ({}) without depending
    # on STATUS contents or git — proving emit.sh sourced cleanly.
    if (hooks_dir / "check-gate.sh").exists():
        r = _fire_hook(target, "hooks/check-gate.sh",
                       '{"tool_input":{"file_path":"docs/notes.md"}}')
        if r.returncode != 0 or r.stdout.strip() != "{}":
            return False, (
                f"{profile}: check-gate.sh did not run cleanly "
                f"(exit={r.returncode}, stdout={r.stdout.strip()!r}, "
                f"stderr={r.stderr.strip()[:200]!r})"
            )

    # (B-2) check-destructive.sh execution (installed by full). Proves patterns.sh
    # sourced cleanly. check-destructive falls back to pwd when not in a git repo.
    if (hooks_dir / "check-destructive.sh").exists():
        r = _fire_hook(target, "hooks/check-destructive.sh",
                       '{"tool_input":{"command":"rm -rf /"}}')
        ask = False
        try:
            ask = json.loads(r.stdout or "{}").get(
                "hookSpecificOutput", {}
            ).get("permissionDecision") == "ask"
        except json.JSONDecodeError:
            ask = False
        if r.returncode != 0 or not ask:
            return False, (
                f"{profile}: check-destructive.sh did not run cleanly "
                f"(exit={r.returncode}, stdout={r.stdout.strip()!r}, "
                f"stderr={r.stderr.strip()[:200]!r})"
            )

    return True, f"{profile}: hooks runnable"


def verify_command_surface(target: Path, profile: str) -> tuple[bool, str]:
    """Prove setup.sh delivered the right command surface (audit F2, F3).

    Two invariants:
      - Every MIRROR_ALLOWLIST command the scaffold installs must be the EXAMPLE
        (scaffold-safe) variant, not the framework variant — i.e. resolve_source
        must map it. retro must additionally keep its graceful-degradation guard.
      - full must ship /judge (its backing build-judge-card.py is delivered there).
    Failures are collected so a single run surfaces every gap.
    """
    failures: list[str] = []
    example_root = REPO_ROOT / "examples" / "minimal-project"

    for rel in sorted(MIRROR_ALLOWLIST):
        installed = target / rel
        if not installed.is_file():
            continue  # this profile does not install this command
        example = example_root / rel
        if not example.is_file():
            failures.append(f"example variant missing for {rel}")
            continue
        if installed.read_bytes() != example.read_bytes():
            failures.append(
                f"{rel} is not the scaffold-safe example variant "
                f"(setup.sh resolve_source must map it)"
            )

    # retro must degrade gracefully when retro_report.py is absent (no profile
    # ships it). Match the specific guard line, not a generic word, so this stays
    # meaningful insurance if the example variant ever silently loses the guard
    # (byte-identity above would still pass in that case).
    retro = target / ".claude" / "commands" / "retro.md"
    retro_guard = "`scripts/retro_report.py` is available"
    if retro.is_file() and retro_guard not in retro.read_text(encoding="utf-8"):
        failures.append(
            "installed retro.md lacks its graceful guard "
            "(must degrade when scripts/retro_report.py is absent)"
        )

    # full delivers build-judge-card.py, so it must also deliver /judge.
    if profile == "full" and not (target / ".claude" / "commands" / "judge.md").is_file():
        failures.append("/judge command not installed though build-judge-card.py is")

    if failures:
        return False, f"{profile}: " + "; ".join(failures)
    return True, f"{profile}: command surface ok"


def run_scaffold_test(profile: str, target: Path) -> tuple[str, str]:
    """Scaffold with profile, validate manifest, then verify hooks + commands."""
    ok, detail = _scaffold(profile, target)
    if not ok:
        return "FAIL", detail

    # File manifest validation.
    result = subprocess.run(
        ["python3", str(CONTRACT_PY), f"--profile={profile}", f"--root={target}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        return "FAIL", f"contract check failed for {profile}: {output}"

    # Execution validation (audit F6).
    ok, detail = verify_hooks_runnable(target, profile)
    if not ok:
        return "FAIL", detail

    # Command-surface validation (audit F2, F3).
    ok, detail = verify_command_surface(target, profile)
    if not ok:
        return "FAIL", detail

    return "PASS", f"{profile} scaffold validated + hooks runnable + command surface ok"


def run_full_hook_exec_test(target: Path) -> tuple[str, str]:
    """full cannot be contract-validated as a scaffold (--profile=full ignores
    --root), so exercise it via hook execution only — this also proves
    patterns.sh delivery via check-destructive, which only full installs."""
    ok, detail = _scaffold("full", target)
    if not ok:
        return "FAIL", detail
    ok, detail = verify_hooks_runnable(target, "full")
    if not ok:
        return "FAIL", detail
    ok, detail = verify_command_surface(target, "full")
    if not ok:
        return "FAIL", detail
    return "PASS", "full scaffold hooks runnable + command surface ok"


def main() -> int:
    results: list[dict[str, str]] = []
    any_fail = False

    def record(label: str, fn) -> None:
        nonlocal any_fail
        tmpdir = tempfile.mkdtemp(prefix=f"ultra-eval-{label}-")
        try:
            status, detail = fn(Path(tmpdir))
        except subprocess.TimeoutExpired:
            status, detail = "FAIL", "timeout"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        results.append({"profile": label, "status": status, "detail": detail})
        if status != "PASS":
            any_fail = True

    for profile in PROFILES:
        record(profile, lambda t, p=profile: run_scaffold_test(p, t))
    record("full (hooks)", run_full_hook_exec_test)

    # Print summary
    print("=== Tier 2: Scaffold Smoke Tests ===")
    print("")
    print(f"  {'Profile':<20} {'Status':<10}")
    print(f"  {'-' * 20} {'-' * 10}")
    for r in results:
        print(f"  {r['profile']:<20} {r['status']:<10}")

    for r in results:
        if r["status"] != "PASS":
            print(f"\n--- {r['profile']} ({r['status']}) ---")
            print(f"  {r['detail']}")

    print("")
    if any_fail:
        print("Result: FAIL")
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

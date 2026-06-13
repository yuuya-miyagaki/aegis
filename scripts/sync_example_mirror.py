#!/usr/bin/env python3
"""Sync the example mirror from the framework root (P3-A / M1).

Control files under MIRROR_DIRS + MIRROR_FILES are byte-identical copies of the
framework root (enforced by check_reference_drift.check_mirror_identity). This
regenerates them so editing a root control file no longer needs manual cp.

Single manifest: MIRROR_DIRS/MIRROR_FILES/MIRROR_ALLOWLIST are imported from
check_reference_drift so generation and verification cannot diverge.

Writes ONLY the mirror portion. Example-specific divergent files (CLAUDE.md,
docs/STATUS.md, docs/requirements/*, etc.) live outside MIRROR_DIRS and are
never touched. Allowlisted scaffold-safe variants (validate.md/retro.md) are
skipped. shutil.copy2 also copies the source mtime onto the example file each
run; git ignores mtime, so this produces no diff when content+mode are unchanged.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from check_reference_drift import (  # noqa: E402
    MIRROR_ALLOWLIST,
    MIRROR_DIRS,
    MIRROR_FILES,
)


def sync_mirror(root: Path) -> list[str]:
    """Copy mirror control files root -> examples/minimal-project, skipping the
    allowlist and removing stale files (under MIRROR_DIRS and the explicit
    MIRROR_FILES). Returns the actions taken (for logging/idempotency checks)."""
    example_root = root / "examples" / "minimal-project"
    actions: list[str] = []

    # 1. Copy: every file under MIRROR_DIRS + the explicit MIRROR_FILES.
    candidates: list[Path] = []
    for d in MIRROR_DIRS:
        root_dir = root / d
        if not root_dir.is_dir():
            continue
        for p in sorted(root_dir.rglob("*")):
            if p.is_file():
                candidates.append(p.relative_to(root))
    candidates.extend(MIRROR_FILES)

    for rel in candidates:
        if rel in MIRROR_ALLOWLIST:
            continue
        src = root / rel
        if not src.is_file():
            continue
        dst = example_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)  # copy2 preserves mode (executable bits)
        actions.append(f"copy {rel.as_posix()}")

    # 2. Remove stale MIRROR_DIRS files: present in the example but no longer in
    #    root (e.g. a hook removed upstream). Allowlist preserved. Divergent
    #    files live outside MIRROR_DIRS, so they are never considered.
    for d in MIRROR_DIRS:
        ex_dir = example_root / d
        if not ex_dir.is_dir():
            continue
        for p in sorted(ex_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(example_root)
            if rel in MIRROR_ALLOWLIST:
                continue
            if not (root / rel).is_file():
                p.unlink()
                actions.append(f"remove {rel.as_posix()}")

    # 3. Remove stale MIRROR_FILES: symmetric with the dir sweep above. The list
    #    is explicit, so this can only ever remove a named script's example copy
    #    when root no longer ships it — never a divergent file.
    for rel in MIRROR_FILES:
        if rel in MIRROR_ALLOWLIST:
            continue
        if not (root / rel).is_file() and (example_root / rel).is_file():
            (example_root / rel).unlink()
            actions.append(f"remove {rel.as_posix()}")

    return actions


def main() -> int:
    actions = sync_mirror(ROOT)
    for a in actions:
        print(a)
    print(f"example mirror synced ({len(actions)} action(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

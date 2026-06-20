---
description: Generate retrospective summary from learnings and session history
allowed-tools: Read, Bash
---

# /retro

Generate a retrospective report from current project state.

If `scripts/retro_report.py` is available:

1. Run `python3 scripts/retro_report.py --root .`
2. Display the report to the user

If it is not present (minimal/standard scaffold does not ship it), summarize
manually instead from `docs/STATUS.md` session history and `docs/LEARNINGS.md`.

# Minimal Project Example

This example shows the intended happy path for a small Claude Code project
using Aegis.

## Included

- root `CLAUDE.md`
- `docs/STATUS.md`
- canonical requirement documents
- one design note
- one implementation plan
- review, QA, and security evidence
- handover documents
- `.claude/agents/` — bounded specialist roles (12 agents)
- `.claude/commands/` — slash commands (`/status`, `/gate`, `/next`, `/recover`, `/validate`, `/retro`, `/tutorial`)
- `.claude/rules/` — always-loaded state machine and routing rules
- `.claude/skills/` — pull-based skill documents (18 skills)
- `.claude/settings.json` — hooks configuration
- `hooks/` — runtime enforcement hooks (including `hooks/lib/`)
- `scripts/update-gate.sh` (required by `/gate` command for gate approvals)
- `scripts/check_status.py` (required by `/validate` command for status validation)

## Validate

Run from the framework repository root:

```bash
python3 scripts/check_status.py --root examples/minimal-project
```

Profile-based contract validation (optional, from framework root):

```bash
python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project
```

If `.claude/settings.json` is present, required hooks registration is verified.
If absent, a WARNING is shown (not FAIL).

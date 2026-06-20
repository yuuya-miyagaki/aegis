---
description: Run project validator (status check)
allowed-tools: Bash, Read
---

# /validate

Run the project status validator.

```bash
python3 scripts/check_status.py --root .
```

Report the validator result (PASS/FAIL) and list any failures.

## Profile-based validation (optional)

If `scripts/check_framework_contract.py` is available, run a profile check:
```bash
python3 scripts/check_framework_contract.py --profile=standard --root .
```

Available profiles: `minimal`, `standard`. (`full` is framework repo root only.)
- `minimal`: core files only (CLAUDE.md, STATUS.md, LEARNINGS.md, check_status.py)
- `standard`: core + rules + commands + key hooks (required=FAIL, recommended=WARNING)

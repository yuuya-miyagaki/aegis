---
description: Show gate approvals and manage gates via the authorized script
allowed-tools: Read, Bash
---

# /gate

Show current gate approvals and manage gates (approve, set n/a, or reset).

Usage: `/gate`, `/gate approve <gate>`, `/gate na <gate>`, `/gate reset <gate>`

## Display mode (no arguments)

1. Read `docs/STATUS.md`
2. Display all gate_approvals with status
3. Show which gate is the next expected approval based on current phase

## Approve mode (`$ARGUMENTS` contains "approve")

1. Read `docs/STATUS.md`
2. Parse the gate name from arguments
3. **Pre-validation check**: For gates with ref mappings (plan, review, qa, security, deploy), verify `current_refs.<gate>` is set. If empty, display the ref status and warn the user before proceeding.
4. **Judge preview (review/qa/security/deploy のみ)**: 承認を求める**前に**カードを提示する:
   - Run: `python3 scripts/build-judge-card.py --gate <gate-name> --root .`
   - Read `docs/qa-reports/judge-<gate-name>.md` and present it to the user in plain Japanese, filling the「次のアクション」section from context. The user decides by looking at the card — never summarize it away.
5. Confirm with the user: "Approve {gate} gate? This advances the workflow."
6. On confirmation, run:

```bash
bash scripts/update-gate.sh <gate-name> approve
```

If the result is 🟡, relay the card's 🟡 items and ask the user for an explicit reason, then run:

```bash
bash scripts/update-gate.sh <gate-name> approve --ack "<user-stated reason>"
```

The reason must come from the user's reply — never invent one.

## N/A mode (`$ARGUMENTS` contains "na")

Set a gate to n/a (not applicable). Only brainstorm and plan gates support n/a (used by bugfix/hotfix flows).

1. Parse the gate name from arguments
2. Confirm with the user: "Set {gate} gate to n/a?"
3. On confirmation, run:

```bash
bash scripts/update-gate.sh <gate-name> na
```

## Reset mode (`$ARGUMENTS` contains "reset")

Reset a gate from approved or n/a back to pending.

1. Parse the gate name from arguments
2. Confirm with the user: "Reset {gate} gate to pending?"
3. On confirmation, run:

```bash
bash scripts/update-gate.sh <gate-name> reset
```

## Important

This script is the ONLY authorized way to change gate values. It updates STATUS.md and .gate-snapshot atomically.

**Do NOT edit STATUS.md gate fields directly with Edit/Write.** Direct edits will be denied by the gate tamper detection hook (any value change, not just →approved).

Valid gates: client_ready_for_dev, brainstorm, plan, review, qa, security, deploy, dev_ready_for_client

Do not change gates without explicit user confirmation.

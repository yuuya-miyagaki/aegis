# Aegis

## Operating Contract

- Thin Claude Code operating model. Claude orchestrates routing.
- Hard gates require explicit user approval.
- Completion requires evidence, not chat confidence.
- Load only docs required for the current task.
- Use framework phases, not `EnterPlanMode`.
- Persist lessons in `docs/LEARNINGS.md`. Auto-memory may store personal preferences only; it must not duplicate LEARNINGS.
- Stop after 3 failures toward the same goal: write `docs/second-opinion.md`,
  update STATUS.md blockers, recommend IDE chat, then wait.
  Count by goal, not method. TDD red-to-green cycles excluded.
  Record each failure in STATUS.md `failure_tracking` (goal/count/last_attempt).
  Reset to null when the goal is achieved or changed.
- Destructive commands require explicit user approval. Enforce via hooks (PaC).
- Hook enforcement level is set at install via `bin/setup.sh --profile` — TDD backstop is on in `full`, off in `minimal`/`standard`. In `full`, `AEGIS_TDD_MODE=off` disables it for the session (session-start warns).
- Phase HINT nudges follow the profile: `full` shows them; `minimal`/`standard` default `AEGIS_NUDGE=off` (written to settings `env` at install). `AEGIS_NUDGE=off` suppresses the phase-HINT sermon for the session; gates, skill boot-paths, blockers, the unknown-phase diagnostic, and warnings are unaffected. Lowercase `off` only; session-start does NOT warn (off is benign).

## Session Start

1. Read `docs/STATUS.md`.
2. Read only `current_refs` relevant to the task.
3. Pull extra docs only when a dependency appears.
4. Invoke subagents only when isolation reduces risk or context.
5. Update `docs/STATUS.md` when phase, refs, blockers, or next step change.

## State Machine

Modes: `Client`, `Dev`. Hard gates control transitions.
Client: onboard→discovery→requirements→scope→acceptance→handover
Dev: brainstorm→plan→implement→review→qa→security→deploy→ship→docs
Details in `.claude/rules/state-machine.md`.

## Routing

Subagents only when they make work clearer, safer, or smaller.
Details in `.claude/rules/routing.md`.

## Model Policy

Agent `model`/`effort` is pinned by role tier (enforced by `scripts/check_framework_contract.py`):

- Quality-pin (`opus`): `planner`=max, `security`=max, `reviewer`=xhigh, `qa`=high.
- Cost-pin (`sonnet`, effort high): `reviewer-testing`/`reviewer-performance`/`reviewer-maintainability`, `translation-specialist`.
- Default (`inherit`, effort high): `implementer`, `qa-browser`, `ui`, `integration-specialist`.

Rules: lineage aliases or `inherit` only (no version-pinned ids); `xhigh`/`max` only on `opus` roles; `haiku` is not used. A pin sets the role default and survives a session `--model` downgrade (frontmatter outranks the session model); it is overridden only by `CLAUDE_CODE_SUBAGENT_MODEL`, which globally downgrades ALL pins (including security). Session-start emits an advisory when that env var is set.

## Context Budget Policy

L0 `CLAUDE.md`+`STATUS.md` (always-on), L1 phase refs, L2 task files, L3 on-demand.

- Prefer repo files over chat history. Pull-based.
- Summarize at phase transitions. Update `docs/STATUS.md` before pauses.

## Skills

Skills live in `.claude/skills/`. Load for the current phase only.

- aegis-brainstorm, bug-diagnosis, tdd, subagent-dev
- deploy, client-workflow, session-recovery, ship-and-docs, user-manual, maintenance, uat
- aegis-review-gate, aegis-security-gate, qa-verification, docs-sync, translation-mapping
- integration-assist, browser-assist

## Source of Truth

- Operating rules: `CLAUDE.md`
- Current phase and next action: `docs/STATUS.md`
- Requirements: `docs/requirements/*`
- Design and plans: `docs/specs/*`, `docs/plans/*`
- Review, QA, and security evidence: `docs/qa-reports/*`
- Skills: named skills
- Actual behavior: code, tests, and command output
- Optional addons: `extensions/` (manual opt-in, not in core contract)

## Completion Rule

A task is only complete when:

- the relevant artifact exists
- zero-tool-call completions are invalid
- the relevant checks have been run or explicitly skipped with reason
- `docs/STATUS.md` points to the active refs
- blockers and residual risks are recorded
- the completion summary is evidence-based
- approved `review`/`qa`/`security`/`deploy`/`plan` gates declare their `current_refs` entry (and `pending`/`n/a` gates leave it null); every declared ref points to an existing file. Enforced at completion by the TaskCompleted hook (same invariant as `check_framework_contract`).

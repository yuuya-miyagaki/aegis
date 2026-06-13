# Ultra Framework Claude Code Design

Date: 2026-04-10
Status: Approved design
Scope: Claude Code native distribution derived from Ultra Framework v7 principles

## Goal

Create a Claude Code specific framework distribution that preserves the strongest
parts of Ultra Framework v7 while removing host-agnostic overhead.

Primary success criteria:

- Keep working context thin by default
- Maintain explicit, logical phase control
- Reduce unnecessary token usage
- Use Claude Code native entry points and subagents instead of `.agents/`
  first-class routing

## Decision Summary

Recommended direction: build a separate distribution named
`ultra-framework-claude-code` and keep `ultra-framework-v7` intact.

Reasoning:

- Rewriting v7 directly would mix stable framework rules with Claude specific
  runtime assumptions.
- A full fork would create long-term drift and duplicate maintenance.
- A dedicated Claude Code distribution allows a thin, optimized execution model
  while still inheriting v7's phase, gate, evidence, and handover discipline.

## Core Design Principles

1. `CLAUDE.md` is the thin control kernel, not a full manual.
2. `docs/STATUS.md` is the operational state index and phase router.
3. Detailed documents are pull-based and read only when required.
4. Claude remains the orchestrator; subagents handle bounded specialist work.
5. Evidence determines completion, not conversational confidence.

## What Carries Over from Ultra Framework v7

- Explicit phase and gate discipline
- User approval for hard gates
- Evidence-first completion criteria
- Canonical document families:
  - `docs/requirements/`
  - `docs/plans/`
  - `docs/specs/`
  - `docs/qa-reports/`
  - `docs/handover/`
- `docs/LEARNINGS.md` for durable operational lessons
- `docs/STATUS.md` as the restart and handoff index

## What Changes for Claude Code

- Replace `.agents/AGENTS.md` as the primary entrypoint with root `CLAUDE.md`
- Replace broad host-neutral instruction loading with Claude native routing
- Move specialist roles into `.claude/agents/*.md`
- Keep always-on context minimal
- Prefer current repo files over long conversation history
- Remove unnecessary abstraction intended for non-Claude runtimes

## Repository Shape

```text
ultra-framework-claude-code/
├── CLAUDE.md
├── .claude/
│   └── agents/
├── docs/
│   ├── STATUS.md
│   ├── requirements/
│   ├── plans/
│   ├── specs/
│   ├── qa-reports/
│   ├── handover/
│   └── LEARNINGS.md
├── templates/
└── docs/MIGRATION-FROM-v7.md
```

## CLAUDE.md Responsibilities

`CLAUDE.md` should stay around 800-1200 tokens, with a hard preference to keep
it below 1500.

It should contain only:

- Operating contract
- Session start order
- State machine summary
- Subagent routing rules
- Context budget policy
- Source-of-truth mapping
- Completion rule

It should not contain:

- Long skill catalogs
- Full review, QA, or security procedures
- Large design rule sets
- Full learnings history
- Repeated content that already lives in canonical docs

## Session Start Contract

Claude should start work in this order:

1. Read `docs/STATUS.md`
2. Read only the `current_refs` relevant to the current task
3. Invoke a subagent only if the task requires specialist isolation
4. Pull additional docs only when a real dependency appears

Default rule: do not preload all requirements, plans, specs, and reports.

## State Machine

This framework uses a two-layer model:

- Modes: `Client`, `Dev`
- Client phases: `onboard -> discovery -> requirements -> scope -> acceptance -> handover`
- Dev phases: `brainstorm -> plan -> implement -> review -> qa -> security -> ship -> docs`

Mode transitions are controlled by gate approvals:

- `client_ready_for_dev`: required before entering `Dev`
- `dev_ready_for_client`: required before handing back to `Client`

Phase progression is controlled by gate approvals in `docs/STATUS.md`:

- Do not enter `plan` before `brainstorm` approval
- Do not enter `implement` before `plan` approval
- Do not enter `qa` before `review` approval
- Do not enter `security` before `qa` approval
- Do not claim completion before required evidence exists

There is no separate `implement` approval key. Entry into `implement` is
controlled by `plan` approval.

Approval is explicit and user-controlled.

## Subagent Topology

Use a small specialist set instead of a large persona catalog.

Required agents:

- `planner.md`
- `implementer.md`
- `reviewer.md`
- `qa.md`
- `security.md`

Optional agent:

- `ui.md`

Role boundaries:

- `planner`: requirements, design, plan, no code edits
- `implementer`: implementation only
- `reviewer`: review and findings with fresh context
- `qa`: reproduction, validation, QA evidence
- `security`: security-focused review and evidence
- `ui`: visual and UX work only when the task demands it

Default orchestration rule: do not invoke subagents unless specialization
reduces risk or context size.

## STATUS.md Schema

`docs/STATUS.md` should behave like a lightweight operational state file.

Recommended frontmatter:

```yaml
---
framework: ultra-framework-claude-code
framework_version: "0.1.0"
mode: Dev
phase: brainstorm
task_type: feature
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: pending
  plan: pending
  review: pending
  qa: pending
  security: pending
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/requirements/PRD.md
    - docs/requirements/SCOPE.md
  plan: null
  spec: null
  review: null
  qa: null
  security: null
next_action: "Finalize design note and request brainstorm approval."
blockers: []
---
```

Recommended body sections:

- `Summary`
- `Recent Decisions`
- `Session History`

This file should remain an index, not a full narrative log.

## Token Budget Rules

Token efficiency is a first-class design target.

Operational rules:

- Always-on context is limited to `CLAUDE.md` and `docs/STATUS.md`
- Detailed docs are loaded on demand from `current_refs`
- Summarize at phase transitions, not after every micro-step
- Use file references as memory; do not restate large docs in chat
- Prefer diff-based review and validation over full-project rereads
- Use only one subagent by default; parallelize only when boundaries are clear
- Keep `session_history` short
- Put durable lessons in `docs/LEARNINGS.md`; keep transient chatter out

## Source of Truth Map

- Operating contract: `CLAUDE.md`
- Current phase and next step: `docs/STATUS.md`
- Requirements: `docs/requirements/*`
- Design and planning artifacts: `docs/specs/*`, `docs/plans/*`
- Review, QA, and security evidence: `docs/qa-reports/*` and `current_refs`
- Actual behavior: code, tests, commands, and runtime output

## Migration Strategy

Migration should be additive, not destructive.

1. Keep `ultra-framework-v7` unchanged
2. Create `ultra-framework-claude-code` as a new distribution
3. Reuse v7 concepts, not v7 file loading behavior
4. Rebuild templates for Claude Code native operation
5. Add `docs/MIGRATION-FROM-v7.md` with a concept mapping table
6. Validate the new distribution with a minimal example project

## Initial Implementation Sequence

1. Create repository skeleton
2. Write root `CLAUDE.md`
3. Add `docs/STATUS.md` template
4. Add `.claude/agents/` with the 5+1 topology
5. Recreate canonical templates for requirements, plans, specs, QA, and handover
6. Add migration guide from v7
7. Add one example project and validate actual Claude Code usage

## Risks

- If `CLAUDE.md` becomes a dumping ground, token costs will regress quickly
- If subagents proliferate, orchestration overhead will erase clarity gains
- If `STATUS.md` becomes verbose narrative, restart quality will degrade
- If v7 and the Claude distribution diverge conceptually, maintenance cost rises

## Guardrails

- Keep the control kernel thin
- Keep the state explicit
- Keep the evidence concrete
- Keep specialist count low
- Keep completed phases compressed

## Outcome

The target system is not a Claude-themed copy of v7. It is a Claude Code native
distribution that preserves v7's operational rigor while optimizing for:

- lighter context
- cleaner routing
- stronger logical state transitions
- lower token waste

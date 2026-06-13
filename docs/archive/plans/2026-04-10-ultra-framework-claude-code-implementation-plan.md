# Ultra Framework Claude Code Implementation Plan

Date: 2026-04-10
Status: Drafted from approved design
Depends on: `docs/plans/2026-04-10-ultra-framework-claude-code-design.md`

## Objective

Bootstrap `ultra-framework-claude-code` as a Claude Code native framework
distribution that preserves Ultra Framework v7's operational discipline while
optimizing for thin context, explicit state control, and lower token usage.

## Delivery Outcome

The first usable version should include:

- root `CLAUDE.md`
- `.claude/agents/` with the agreed 5+1 topology
- `docs/STATUS.md` template with explicit operational schema
- canonical templates for requirements, plans, specs, QA, and handover
- `docs/MIGRATION-FROM-v7.md`
- one minimal example project

## Non-Goals for V0

- broad host compatibility
- large specialist catalogs
- complex automation or external integrations
- full parity with every v7 helper file on day one

## Workstreams

### 1. Repository Skeleton

Create the base layout:

```text
ultra-framework-claude-code/
├── CLAUDE.md
├── .claude/agents/
├── docs/
│   ├── STATUS.md
│   ├── requirements/
│   ├── plans/
│   ├── specs/
│   ├── qa-reports/
│   ├── handover/
│   ├── LEARNINGS.md
│   └── MIGRATION-FROM-v7.md
├── templates/
└── examples/minimal-project/
```

Acceptance:

- directory structure exists
- naming is consistent with the approved design
- no `.agents/` first-entry dependency remains

### 2. Control Kernel

Write root `CLAUDE.md` with these sections only:

- Operating Contract
- Session Start
- State Machine
- Routing
- Context Budget Policy
- Source of Truth
- Completion Rule

Acceptance:

- file stays within the target token budget
- no duplicated long procedures
- references point to canonical docs instead of inlining them

### 3. Operational State Template

Create `docs/STATUS.md` template with:

- frontmatter schema for mode, phase, gate approvals, current refs, blockers, next action
- compact body sections for summary and recent decisions
- explicit rule that the file is an index, not a full log

Acceptance:

- phase transitions are machine-legible
- current refs clearly identify active plan/spec/review/qa/security files
- restart quality does not depend on chat history

### 4. Subagent Layer

Create `.claude/agents/`:

- `planner.md`
- `implementer.md`
- `reviewer.md`
- `qa.md`
- `security.md`
- `ui.md`

Each file should define:

- when the agent is used
- what it must read first
- what it must not do
- what artifact or output it is expected to produce

Acceptance:

- responsibilities do not overlap excessively
- agents remain small and bounded
- default path still works without subagents

### 5. Canonical Templates

Recreate templates for:

- `docs/requirements/PRD.md`
- `docs/requirements/SCOPE.md`
- `docs/requirements/NFR.md`
- `docs/requirements/ACCEPTANCE.md`
- `docs/plans/`
- `docs/specs/`
- `docs/qa-reports/`
- `docs/handover/TO-CLIENT.md`
- `docs/handover/TO-DEV.md`
- `docs/LEARNINGS.md`

Acceptance:

- templates match Claude native flow
- templates avoid repeated boilerplate that should live in `CLAUDE.md`
- fields align with the new `STATUS.md` schema

### 6. Migration Guide

Create `docs/MIGRATION-FROM-v7.md` with:

- v7 concept to Claude Code concept mapping
- what carries over unchanged
- what is intentionally removed
- suggested migration sequence for existing users

Acceptance:

- a v7 user can understand the new mental model quickly
- the guide makes clear that this is a separate distribution, not a silent rewrite

### 7. Example Project

Add `examples/minimal-project/` demonstrating:

- root `CLAUDE.md`
- initialized `docs/STATUS.md`
- at least one requirement doc
- one design/plan/spec chain
- one QA or review evidence artifact

Acceptance:

- example shows the intended happy path
- example stays small enough to inspect quickly
- example can be used to validate startup behavior manually

## Implementation Order

Recommended order:

1. repository skeleton
2. `CLAUDE.md`
3. `docs/STATUS.md`
4. `.claude/agents/`
5. canonical templates
6. migration guide
7. example project

## Gate Strategy

Planned gate sequence:

1. approve design
2. approve implementation plan
3. build repository skeleton and core control files
4. review generated structure
5. validate example project flow

## Verification Strategy

Verification for V0 should stay lightweight.

Checks:

- `CLAUDE.md` remains thin and does not accrete procedural bulk
- `docs/STATUS.md` supports restart without relying on prior chat
- subagent files are scoped and non-overlapping
- example project proves the intended reading order and phase flow

## Risks and Countermeasures

- Risk: `CLAUDE.md` grows into a second manual
  Countermeasure: reject long embedded procedures and push detail back into docs

- Risk: subagent count expands too quickly
  Countermeasure: require a concrete token or logic benefit before adding one

- Risk: v7 and Claude Code edition drift conceptually
  Countermeasure: keep migration mapping explicit and review shared concepts

- Risk: templates become verbose and duplicate each other
  Countermeasure: keep templates role-specific and index through `STATUS.md`

## First Build Milestone

Milestone definition:

- a new repo can be initialized
- Claude can start from `CLAUDE.md`
- `STATUS.md` drives the next action correctly
- at least one end-to-end path from design to review is demonstrable in the example

## Suggested Next Action

Begin implementation with the repository skeleton, root `CLAUDE.md`, and
`docs/STATUS.md` template. Those three pieces establish the control plane that
all later templates and agents depend on.

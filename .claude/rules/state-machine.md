# State Machine

- Modes: `Client`, `Dev`
- Client phases: `onboard -> discovery -> requirements -> scope -> acceptance -> handover`
- Dev phases: `brainstorm -> plan -> implement -> review -> qa -> security -> deploy -> ship -> docs`

Mode gates:

- `client_ready_for_dev`: required before entering `Dev`
- `dev_ready_for_client`: required before handing back to `Client`

Client mode purpose: structure client information, translate client
language into functional specs and implementation hints, and produce
a verified handover package for Dev mode.

In `Client`, load the `client-workflow` skill.
Only `client_ready_for_dev` moves work to `Dev`.

Before `brainstorm`, reread `docs/STATUS.md`, confirm refs, and restate
objective, blockers, and next action. Required; not a phase.

`deploy`/`ship`/`docs` details live in their respective skills.

Iteration: after `dev_ready_for_client`, new task resets to `brainstorm`,
clears dev gates to `pending`, sets non-requirements refs to null,
increments `iteration`, keeps `current_refs.requirements`. Change
`task_type`/`task_size` only via `scripts/update-task.sh` (raw edits = tamper).
Archive external_evidence beyond the latest 3 to `docs/evidence-archive.md`.

When re-entering `Client` to revise requirements, `reset`
`client_ready_for_dev` first; an approved gate skips
re-approval and the spec-delta check (`docs/handover/CHANGES.md`).

Phase transition: get approval -> update gates/refs -> update phase/next_action -> invoke next route.

Phase gates:

- Do not enter a phase before its prior gate is approved.
  Task size routing overrides: skipped phases exempt their gates.
- Do not write production code before a failing test exists.
- Do not claim completion before the required evidence exists.

| type | required gates | S (1 file) | M (2-5) | L (6+) |
|------|---------------|------------|---------|--------|
| feature/refactor/framework | review+qa+security+deploy | impl->review->ship->docs | skip deploy | all |
| bugfix | review; brainstorm+plan=n/a (bug-diagnosis) | same | same | same |
| hotfix | review preferred; brainstorm+plan=n/a (bug-diagnosis simplified) | same | same | same |

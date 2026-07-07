# Routing

## Principle

Subagents only when they make work clearer/safer/smaller; else keep in session context.

## Agents

<!-- aegis:budget-exclude-start -->
Subagents: `planner`, `implementer`, `reviewer`, `qa`, `security`, `ui`,
`qa-browser`, `integration-specialist`, `translation-specialist`,
`reviewer-testing`, `reviewer-performance`, `reviewer-maintainability`.
Each agent's own file defines its domain.
<!-- aegis:budget-exclude-end -->

`brainstorm` runs in session context (live user dialogue), not as a subagent.
`browser-assist` skill (`.claude/skills/browser-assist/SKILL.md`) is available to any agent needing browser automation.

## Subagent continuation

Resume a stalled subagent via SendMessage (same agent, context preserved), not a fresh re-dispatch.
Guidance, not harness-enforced; bounded by each agent's `maxTurns` and the 3-failure rule.

## Verification delegation

Standard constraints for every verification dispatch (review first and
blind-second, security, qa, qa-browser, specialist reviewers). Carry them in
the delegation prompt. 1-5 apply as written to itemized work; 6 is unconditional.

1. Split: bounded batch, numbered items.
2. Completion: no final report until every item has evidence; partial is never final.
3. Resume: continue the same agent (see Subagent continuation).
4. Progress: report per item.
5. Evidence: per item {action, expected, observed, verdict}.
6. Read-only: MUST NOT modify existing files, MUST NOT run
   git checkout/restore/reset/clean/stash; the only allowed writes are new
   evidence artifacts on the assigned path. If the tree gets dirty:
   stop, report, do not touch it.

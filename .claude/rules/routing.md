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

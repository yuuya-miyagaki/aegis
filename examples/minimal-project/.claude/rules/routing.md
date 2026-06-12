# Routing

## Principle

Subagents only when they make work clearer, safer, or smaller.
When in doubt, keep work in the session context.

## Agents

Subagents: `planner`, `implementer`, `reviewer`, `qa`, `security`, `ui`,
`qa-browser`, `integration-specialist`, `translation-specialist`,
`reviewer-testing`, `reviewer-performance`, `reviewer-maintainability`.
Each agent's own file defines its domain.

`brainstorm` runs in session context (live user dialogue), not as a subagent.
`browser-assist` skill (`.claude/skills/browser-assist/SKILL.md`) is available to any agent needing browser automation.

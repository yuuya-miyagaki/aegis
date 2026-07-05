#!/usr/bin/env python3
"""Single source of truth for platform-coupled (volatile) values.

Isolates values that shift when the Claude Code platform or the Claude model
lineup evolves, so a platform change is a one-place edit. Consumed by import:
  - check_framework_contract.py -> model/effort validity (FAIL)
  - check_reference_drift.py     -> hook-event drift (FAIL) / tool registry (WARN) / staleness (WARN)

emit.sh is intentionally NOT a consumer: the hook output schema stays defined in
pure-bash there (the deny path must have zero external deps). This module only
records WHEN that schema was last verified against the platform contract.

The harness cannot introspect the live platform, so reality drift is tracked by
human-maintained verification dates (PLATFORM_VERIFIED), surfaced as a
non-blocking staleness advisory. This is what keeps the manifest from becoming a
silent declarative mirror: every value either has a real importing consumer or a
dated human re-verification trigger.
"""

from __future__ import annotations

from datetime import date

# --- Models / effort: validated against agent frontmatter + MODEL_EFFORT_POLICY
#     by check_framework_contract.py. `inherit` is not a model id but the
#     "follow the session model" directive; it is an allowed frontmatter value. ---
ALLOWED_MODELS = frozenset({"opus", "sonnet", "inherit"})  # lineage alias + inherit
FORBIDDEN_MODELS = frozenset({"haiku"})                    # explicitly not used
EFFORT_LEVELS = frozenset({"high", "xhigh", "max"})
OPUS_ONLY_EFFORTS = frozenset({"xhigh", "max"})

# --- Hook lifecycle events: template events must be a subset of this. ---
KNOWN_HOOK_EVENTS = frozenset({
    "SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "PreCompact", "Stop", "SubagentStop", "UserPromptSubmit", "Notification",
    "TaskCreated", "TaskCompleted",
})

# Events whose `matcher` field holds TOOL names. Others (e.g. SessionStart holds
# session sources like startup|resume|clear|compact) must NOT be checked here.
TOOL_MATCHING_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure"})

# --- Tool / MCP-tool tokens referenced by template matchers today. Extend ONLY
#     when a new tool-matching matcher is added (best-effort registry; do not pad
#     with tools no matcher references, or the registry silently rots). ---
KNOWN_TOOL_NAMES = frozenset({
    "Bash", "Edit", "Write", "NotebookEdit",
    "Skill", "CronCreate",
    "mcp__claude_ai_Vercel__deploy_to_vercel",
})

# --- Human verification dates (YYYY-MM-DD): last time each class was checked
#     against the live Claude Code platform. Bump on re-verification. ---
PLATFORM_VERIFIED = {
    "models": "2026-06-14",
    "hook_events": "2026-06-14",
    "tool_names": "2026-06-14",
    "hook_output_schema": "2026-06-14",
    # iter57: PostToolUseFailure envelope carries tool_response.stderr (string)
    # and tool_input.command — verified against code.claude.com/docs/en/hooks.md
    # (2026-07-05). explain-oslock-eacces.sh pattern-matches stderr for
    # permission-denied AND command for a locked-CP mention (both required, so
    # a benign non-zero exit like grep-no-match does not fire the advisory).
    "posttoolfailure_stderr": "2026-07-05",
}
STALENESS_DAYS = 180


def stale_keys(today: date | None = None) -> list[str]:
    """Verification keys whose last-verified date is older than STALENESS_DAYS.
    Pure function; `today` is injectable for tests."""
    if today is None:
        today = date.today()
    stale: list[str] = []
    for key, iso in PLATFORM_VERIFIED.items():
        if (today - date.fromisoformat(iso)).days > STALENESS_DAYS:
            stale.append(key)
    return sorted(stale)

#!/usr/bin/env bash
# Single source of truth for Aegis hook OUTPUT JSON schemas.
#
# No external interpreter, no external dependency. Escaping uses a bash
# command substitution (a subshell, not an external program), so the
# security-critical deny/block output path NEVER depends on an external
# runtime and can never fail open when one is missing.
# When Claude Code changes a hook output schema, update ONLY this file.
#
# Escaping scope: _aegis_json_escape handles the structural JSON characters
# (backslash, double-quote, newline, tab, CR) found in developer-authored
# reason strings. Call sites that embed EXTERNAL fragments (cron prompts,
# task subjects, file paths, command fragments) into a reason MUST sanitize
# them to printable text first; raw control bytes (0x01-0x08 etc.) are out of
# scope here.
#
# Schema reference (verified 2026-06-05):
#   PreToolUse:            hookSpecificOutput.{permissionDecision, permissionDecisionReason}
#   PostToolUse / PreCompact(block) / Stop / SubagentStop: top-level {decision:"block", reason}
#   PostToolUseFailure / SessionStart / PreCompact(allow) / UserPromptSubmit:
#                          hookSpecificOutput.{hookEventName, additionalContext}
#   TaskCreated (hard stop): top-level {continue:false, stopReason}
#
# Source: source "$(dirname "$0")/lib/emit.sh"

# JSON-escape a string for a double-quoted JSON value. Pure bash parameter
# expansion (works in bash 3.2). Handles the characters that occur in
# developer-authored reason strings: backslash, double-quote, newline, tab, CR.
_aegis_json_escape() {
  local s=$1
  s=${s//\\/\\\\}     # backslash FIRST
  s=${s//\"/\\\"}     # double quote
  s=${s//$'\n'/\\n}   # newline
  s=${s//$'\t'/\\t}   # tab
  s=${s//$'\r'/\\r}   # carriage return
  printf '%s' "$s"
}

# Allow / passthrough.
emit_allow() { printf '{}\n'; }

# PreToolUse decision. $1=decision(deny|ask) $2=reason
emit_pretool() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' \
    "$1" "$(_aegis_json_escape "$2")"
}
emit_deny() { emit_pretool deny "$1"; }
emit_ask()  { emit_pretool ask  "$1"; }

# Top-level block (PostToolUse, PreCompact-block, Stop, SubagentStop). $1=reason
emit_block() {
  printf '{"decision":"block","reason":"%s"}\n' "$(_aegis_json_escape "$1")"
}

# hookSpecificOutput.additionalContext. $1=hookEventName $2=additionalContext
emit_context() {
  printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' \
    "$1" "$(_aegis_json_escape "$2")"
}

# TaskCreated hard stop. $1=stopReason
emit_continue_false() {
  printf '{"continue":false,"stopReason":"%s"}\n' "$(_aegis_json_escape "$1")"
}

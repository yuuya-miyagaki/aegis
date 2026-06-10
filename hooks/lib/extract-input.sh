#!/usr/bin/env bash
# Shared input extraction library for Aegis hooks.
# Source this file: source "$(dirname "$0")/lib/extract-input.sh"

# Extract file_path from Edit/Write/NotebookEdit tool_input JSON.
extract_file_path() {
  local input="$1"
  local result
  # Embedded escaped quote (\") makes the grep `"[^"]*"` capture truncate at the
  # first internal quote. Use python3 for fidelity in that case (rare). Plain
  # paths keep the grep fast-path (no python3 spawn on the hot path).
  if printf '%s' "$input" | grep -q '\\"'; then
    result=$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()).get("tool_input",{}); print(d.get("file_path","") or d.get("notebook_path",""))' 2>/dev/null || true)
    if [ -n "$result" ]; then
      printf '%s' "$result"
      return
    fi
  fi
  # Try file_path first (Edit/Write).
  result=$(printf '%s' "$input" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//;s/"$//' || true)
  # Fallback: try notebook_path (NotebookEdit).
  if [ -z "$result" ]; then
    result=$(printf '%s' "$input" | grep -o '"notebook_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//;s/"$//' || true)
  fi
  if [ -z "$result" ]; then
    result=$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()).get("tool_input",{}); print(d.get("file_path","") or d.get("notebook_path",""))' 2>/dev/null || true)
  fi
  printf '%s' "$result"
}

# Extract command from Bash tool_input JSON.
extract_command() {
  local input="$1"
  local result
  # Embedded escaped quote (\") truncates the grep `"[^"]*"` capture at the first
  # internal quote, which previously hid a dangerous token placed after it
  # (destructive/secrets bypass). Use python3 for fidelity when an escaped quote
  # is present; otherwise keep the grep fast-path (no python3 on the hot path).
  # Same fidelity routing for backslash escapes (\n, \t, ...): the grep path
  # returns them as literal two-char sequences, so a multiline command would
  # never re-gain its real newlines — breaking the ';' normalization contract
  # of the test-runner classifier (T1 v1.5.1) for both the evidence log and
  # post-bash.sh. python3 failure still falls through to the grep path
  # (degraded text beats no text for the downstream fail-closed checks).
  if printf '%s' "$input" | grep -q '\\[\\nrtbfu"]'; then
    result=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
    if [ -n "$result" ]; then
      printf '%s' "$result"
      return
    fi
  fi
  result=$(printf '%s' "$input" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:[[:space:]]*"//;s/"$//' || true)
  if [ -z "$result" ]; then
    result=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.loads(sys.stdin.read()).get("tool_input",{}).get("command",""))' 2>/dev/null || true)
  fi
  printf '%s' "$result"
}

# Extract exit_code from PostToolUse / PostToolUseFailure tool result JSON.
#
# v0.13.0 Phase 0b: support both key schemas to bridge implementation drift.
# The official Claude Code Hooks docs do not explicitly document the
# PostToolUse result key name. We probe in priority order:
#   1. tool_response.exitCode (camelCase, current Claude Code 2.x suspected)
#   2. tool_response.exit_code (snake_case under tool_response, defensive)
#   3. tool_result.exit_code   (legacy / aegis pre-v0.12.2 wire format)
#   4. tool_result.exitCode    (defensive)
# Returns the first non-null value found, or 0 if none.
extract_exit_code() {
  local input="$1"
  printf '%s' "$input" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
except Exception:
    print(0)
    sys.exit(0)
tr = data.get("tool_response") or {}
tl = data.get("tool_result") or {}
for v in (tr.get("exitCode"), tr.get("exit_code"), tl.get("exit_code"), tl.get("exitCode")):
    if v is not None:
        print(v)
        sys.exit(0)
print(0)
' 2>/dev/null || echo "0"
}

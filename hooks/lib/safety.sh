#!/usr/bin/env bash
# safety.sh — fail-closed integrity helpers for deny hooks.
#
# K-5 (v1.6.2): source FIRST in every deny hook so that even when
# emit.sh / extract-input.sh / patterns.sh fail to source, the hook still
# emits a structured `permissionDecision:deny` (fail-closed) instead of
# empty stdout + exit 1 (fail-open under Claude Code spec).
#
# DESIGN (grill 致命 5):
#   - The fallback inline block in each deny hook MUST be byte-identical
#     across all 6 deny hooks (enforced by
#     tests/test_safety_fallback_identity.py via SHA256).
#   - The reason string is STATIC — no %s / $VAR substitution — to
#     eliminate JSON-injection risk and to remove drift surface. The
#     specific failure (which lib failed) is logged to stderr only.
#   - The fallback runs BEFORE safety.sh itself is sourced, because
#     safety.sh's own absence is the worst case the system must survive.
#
# AEGIS_SAFETY_FALLBACK_BEGIN / END markers in each deny hook delimit the
# block; the contract test reads the file, extracts the block, and
# compares hashes.

# Emit an explicit deny that does not depend on emit.sh.
# Argument: short hint logged to stderr (e.g. which lib failed).
# Reason in JSON is fixed; do not parameterize.
_aegis_emit_fail_closed_deny() {
  local stderr_hint="${1:-unspecified}"
  printf '[aegis-safety] fail-closed: %s\n' "$stderr_hint" >&2
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}}'
  exit 0
}

# Source a lib file; on failure, fail-closed via emit above.
# bash gotcha: under `set -e`, `source missing_file 2>/dev/null || fallback`
# does NOT fall through — bash exits at the source call. We must:
#   (1) check existence first, and
#   (2) temporarily disable errexit around the source so its rc reaches
#       our explicit check.
aegis_require_lib() {
  local lib="$1"
  if [ ! -r "$lib" ]; then
    _aegis_emit_fail_closed_deny "lib not readable: $(basename "$lib")"
  fi
  set +e
  # shellcheck disable=SC1090
  source "$lib" 2>/dev/null
  local _rc=$?
  set -e
  if [ "$_rc" -ne 0 ]; then
    _aegis_emit_fail_closed_deny "lib source failed (rc=$_rc): $(basename "$lib")"
  fi
}

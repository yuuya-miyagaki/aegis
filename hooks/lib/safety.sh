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

# --- FS case-sensitivity probe (C-1, iter54) ---
# aegis_fs_case_insensitive <root> — returns 0 when <root> sits on a
# case-insensitive filesystem (macOS/Windows defaults), 1 otherwise.
#
# Probe: the framework root always carries a lowercase `hooks/` dir (the deny
# hooks themselves live there); if the UPPERCASE spelling resolves AND is the
# SAME directory entry (device+inode via `-ef`), the FS folds case. The `-ef`
# check is load-bearing: a case-SENSITIVE FS can host a genuinely separate
# user-owned `HOOKS/` dir — `-d` alone would misdetect that as case-insensitive
# and drag the user's dir into the moat (false deny).
#
# AEGIS_CASE_FOLD_FORCE=1 forces case-folding ON regardless of the probe. The
# override is STRENGTHEN-ONLY (it can only widen deny coverage); there is
# deliberately NO off-switch env var, so session-env pollution cannot weaken
# the moat. Consumers must pass their own probe result to child processes
# explicitly (e.g. AEGIS_CASE_INSENSITIVE=<result> python3 ...), never inherit
# it from the session environment.
aegis_fs_case_insensitive() {
  local root="$1"
  if [ "${AEGIS_CASE_FOLD_FORCE:-}" = "1" ]; then
    return 0
  fi
  [ -d "${root}/HOOKS" ] && [ "${root}/HOOKS" -ef "${root}/hooks" ]
}

# --- PostToolUse variant (I1, iter41) ---
# post-status-audit.sh is a PostToolUse blocker; its fail-closed signal is the
# top-level {"decision":"block"} schema, NOT PreToolUse deny. Same static-reason
# discipline (no %s / $VAR) for the JSON-injection / drift reasons above. This
# is why post-status-audit is NOT part of the 12-hook byte-identity set — its
# fallback emits a different (PostToolUse) schema.
_aegis_emit_fail_closed_block() {
  local stderr_hint="${1:-unspecified}"
  printf '[aegis-safety] fail-closed: %s\n' "$stderr_hint" >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
}

# Source a lib file; on failure, fail-closed via PostToolUse block above.
aegis_require_lib_block() {
  local lib="$1"
  if [ ! -r "$lib" ]; then
    _aegis_emit_fail_closed_block "lib not readable: $(basename "$lib")"
  fi
  set +e
  # shellcheck disable=SC1090
  source "$lib" 2>/dev/null
  local _rc=$?
  set -e
  if [ "$_rc" -ne 0 ]; then
    _aegis_emit_fail_closed_block "lib source failed (rc=$_rc): $(basename "$lib")"
  fi
}

#!/usr/bin/env bash
# PostToolUse hook for Bash (success path): record the execution into the
# evidence log (E1 activity verification). Observation only — ALWAYS allows.
# Failed executions are recorded by post-bash.sh (PostToolUseFailure).
#
# Failure policy: advisory / fail-open at record time. The missing-record case
# fail-closes at gate time (judge card 🟡 unverified) — see
# docs/hook-failure-policy.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib/emit.sh"
source "${SCRIPT_DIR}/lib/evidence.sh"

DEFAULT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# Test fixtures isolate via AEGIS_ROOT_OVERRIDE (same as check-task-completed).
ROOT="${AEGIS_ROOT_OVERRIDE:-${DEFAULT_ROOT}}"

INPUT=$(cat || true)
append_evidence "$ROOT" ok "$INPUT" || true
emit_allow
exit 0

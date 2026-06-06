#!/usr/bin/env bash
# SessionStart hook: reads STATUS.md and injects session context.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"

source "${SCRIPT_DIR}/lib/emit.sh"

# If STATUS.md doesn't exist, allow silently.
if [ ! -f "$STATUS_FILE" ]; then
  emit_allow
  exit 0
fi

# Initialize gate snapshot for tamper detection (used by post-status-audit.sh).
SNAPSHOT_DIR="${ROOT}/.claude"
SNAPSHOT_FILE="${SNAPSHOT_DIR}/.gate-snapshot"
mkdir -p "$SNAPSHOT_DIR"
sed -n '/^gate_approvals:/,/^[a-z]/{ /^gate_approvals:/p; /^  /p; }' "$STATUS_FILE" > "$SNAPSHOT_FILE" 2>/dev/null || true
# Save phase to snapshot (used by post-status-audit.sh for phase transition monitoring).
grep -m1 "^phase:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true
# Save mode to snapshot (used by post-status-audit.sh for mode change monitoring).
grep -m1 "^mode:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true

# Extract a scalar value from YAML frontmatter.
extract_value() {
  local key="$1"
  grep -m1 "^${key}:" "$STATUS_FILE" | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}

MODE=$(extract_value "mode")
PHASE=$(extract_value "phase")
TASK_TYPE=$(extract_value "task_type")
NEXT_ACTION=$(extract_value "next_action")

# Extract blockers (all list items, stop at next top-level key).
BLOCKERS=""
if grep -q "^blockers:[[:space:]]*\[\]" "$STATUS_FILE"; then
  BLOCKERS=""
elif grep -q "^blockers:" "$STATUS_FILE"; then
  BLOCKERS=$(sed -n '/^blockers:/,/^[a-z]/{/^blockers:/d;/^[a-z]/d;s/^[[:space:]]*- //p;}' "$STATUS_FILE" | awk 'BEGIN{ORS=""} {if(NR>1) printf "; "; printf "%s",$0}' || true)
fi

# Extract gate approvals.
GATES=""
GATE_SECTION=$(grep -A20 "^gate_approvals:" "$STATUS_FILE" || true)
if [ -n "$GATE_SECTION" ]; then
  for gate_key in client_ready_for_dev brainstorm plan review qa security deploy dev_ready_for_client; do
    gate_val=$(printf '%s' "$GATE_SECTION" | grep -m1 "${gate_key}:" | sed "s/.*${gate_key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
    if [ -n "$gate_val" ] && [ "$gate_val" != "null" ]; then
      GATES="${GATES} ${gate_key}=${gate_val}"
    fi
  done
fi

# Extract task_size for hook profile hint.
TASK_SIZE=$(extract_value "task_size")

# Build context message.
CONTEXT="[Aegis] mode=${MODE} phase=${PHASE}"
if [ -n "$TASK_SIZE" ]; then
  CONTEXT="${CONTEXT} size=${TASK_SIZE}"
fi
if [ -n "$NEXT_ACTION" ] && [ "$NEXT_ACTION" != '""' ]; then
  CONTEXT="${CONTEXT} | next: ${NEXT_ACTION}"
fi
if [ -n "$BLOCKERS" ]; then
  CONTEXT="${CONTEXT} | BLOCKERS: ${BLOCKERS}"
fi
if [ -n "$GATES" ]; then
  CONTEXT="${CONTEXT} | gates:${GATES}"
fi

# Second-opinion file detection (PaC: enforced by check_framework_contract.py).
SECOND_OPINION_FILE="${ROOT}/docs/second-opinion.md"
if [ -f "$SECOND_OPINION_FILE" ]; then
  CONTEXT="${CONTEXT} | [BLOCKER] docs/second-opinion.md exists — read before proceeding"
fi

# Failure tracking detection with escalation.
FT_COUNT=$(grep -A3 "^failure_tracking:" "$STATUS_FILE" | grep -m1 "count:" | sed 's/.*count:[[:space:]]*//' | sed 's/^"//;s/"$//' || true)
if [ -n "$FT_COUNT" ] && [ "$FT_COUNT" != "null" ] && [ "$FT_COUNT" -ge 1 ] 2>/dev/null; then
  FT_GOAL=$(grep -A3 "^failure_tracking:" "$STATUS_FILE" | grep -m1 "goal:" | sed 's/.*goal:[[:space:]]*//' | sed 's/^"//;s/"$//' || true)
  if [ "$FT_COUNT" -ge 3 ]; then
    if [ -f "${ROOT}/docs/second-opinion.md" ]; then
      CONTEXT="${CONTEXT} | [BLOCKER] second-opinion.md に基づいて対応してください"
    else
      CONTEXT="${CONTEXT} | [BLOCKER] 3回失敗ルール発動: ${FT_GOAL} → second-opinion.md を作成し、STATUS.md blockers に記録し、IDE chat を推奨してから停止してください"
    fi
  elif [ "$FT_COUNT" -ge 2 ]; then
    CONTEXT="${CONTEXT} | [BLOCKER] failure tracking: ${FT_GOAL} (${FT_COUNT}/3) → 次の失敗で3回ルール発動。second-opinion.md 準備を検討してください"
  else
    CONTEXT="${CONTEXT} | [WARNING] failure tracking active: ${FT_GOAL} (${FT_COUNT}/3)"
  fi
fi

# Stuck detection: phase stagnation (all session_history entries in same phase).
HISTORY_PHASES=$(
  sed -n '/^session_history:/,/^[a-z]/{/phase:/p;}' "$STATUS_FILE" \
    | sed 's/.*phase:[[:space:]]*//' \
    | sed 's/^"//;s/"$//'
)
HISTORY_COUNT=$(printf '%s\n' "$HISTORY_PHASES" | grep -c . || true)
if [ "$HISTORY_COUNT" -ge 2 ]; then
  UNIQUE_PHASES=$(printf '%s\n' "$HISTORY_PHASES" | sort -u | wc -l | tr -d ' ')
  if [ "$UNIQUE_PHASES" -eq 1 ]; then
    STUCK_PHASE=$(printf '%s\n' "$HISTORY_PHASES" | head -1)
    CONTEXT="${CONTEXT} | [WARNING] stuck: ${HISTORY_COUNT} sessions in '${STUCK_PHASE}' phase — consider changing approach or escalating"
  fi
fi

# Phase-aware skill and rule hints.
HINT=""
case "$PHASE" in
  onboard|discovery|requirements|scope|acceptance)
    HINT="skill: client-workflow"
    ;;
  handover)
    HINT="skill: client-workflow / mapping.md必須(translation-mapping skill)"
    ;;
  brainstorm)
    if [ "$TASK_TYPE" = "bugfix" ] || [ "$TASK_TYPE" = "hotfix" ]; then
      HINT="skill: bug-diagnosis / TDD必須 / brainstorm+plan=n/a"
    else
      HINT="skill: aegis-brainstorm / TDD必須 / エビデンスなき完了なし"
    fi
    ;;
  plan)
    HINT="skill: subagent-dev(計画) / Boundary Map必須 / TDD必須"
    ;;
  implement)
    HINT="skill: subagent-dev / TDD必須: テストを先に書け / エビデンスなき完了なし"
    ;;
  review)
    HINT="skill: subagent-dev(レビュー) / Review Army: diff-scope分析でspecialist起動"
    ;;
  qa)
    HINT="skill: qa-verification / エビデンスなき完了なし / 再現・検証を実行せよ"
    ;;
  security)
    HINT="skill: aegis-security-gate / エビデンスなき完了なし / 残留リスクを記録せよ"
    ;;
  deploy)
    HINT="skill: deploy / Security Blockers確認必須 / 3回失敗=ゴールベースカウント"
    ;;
  ship|docs)
    HINT="skill: ship-and-docs / LEARNINGS更新必須(confidence付き)"
    ;;
  *)
    if [ -n "$PHASE" ]; then
      HINT="unknown phase: ${PHASE} — docs/STATUS.md を確認"
    fi
    ;;
esac
if [ -n "$HINT" ]; then
  CONTEXT="${CONTEXT} | ${HINT}"
fi

# Extract high-confidence learnings with phase-aware priority.
# Format: "- [confidence:N] [phase:X] content" or "- [confidence:N] content".
# Phase-matching entries (confidence >= 8) are shown first, then general (confidence >= 9).
LEARNINGS_FILE="${ROOT}/docs/LEARNINGS.md"
if [ -f "$LEARNINGS_FILE" ]; then
  # Phase-aware: current phase matching entries (confidence >= 8), max 2.
  PHASE_LEARNINGS=""
  if [ -n "$PHASE" ]; then
    PHASE_LEARNINGS=$(
      grep -E "^[[:space:]]*-[[:space:]]*\[confidence:(8|9|10)\].*\[phase:${PHASE}\]" "$LEARNINGS_FILE" \
        | head -2 \
        | sed -E 's/^[[:space:]]*-[[:space:]]*\[confidence:[0-9]+\][[:space:]]*/- /' \
        | sed -E 's/\[phase:[a-z]+\][[:space:]]*//' \
        || true
    )
  fi
  # Fallback: phase-tagless entries (confidence >= 9), max 1.
  GENERAL_LEARNINGS=$(
    grep -E '^[[:space:]]*-[[:space:]]*\[confidence:(9|10)\][[:space:]]+' "$LEARNINGS_FILE" \
      | grep -v '\[phase:' \
      | head -1 \
      | sed -E 's/^[[:space:]]*-[[:space:]]*\[confidence:[0-9]+\][[:space:]]+/- /' \
      || true
  )
  LEARNINGS="${PHASE_LEARNINGS}${GENERAL_LEARNINGS:+ ${GENERAL_LEARNINGS}}"
  LEARNINGS=$(printf '%s' "$LEARNINGS" | tr '\n' ' ' | sed 's/  */ /g')
  if [ -n "$LEARNINGS" ]; then
    CONTEXT="${CONTEXT} | learnings: ${LEARNINGS}"
  fi
fi

# STATUS.md health check (maintenance warnings).
HEALTH_WARNINGS=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-status-health 2>&1 || true)
if [ -n "$HEALTH_WARNINGS" ]; then
  HEALTH_SHORT=$(printf '%s' "$HEALTH_WARNINGS" | head -2 | tr '\n' '; ')
  CONTEXT="${CONTEXT} | [MAINTENANCE] ${HEALTH_SHORT}"
fi

# Locale hint.
CONTEXT="${CONTEXT} / ドキュメントは日本語"

# AEGIS_TDD_MODE=off のとき TDD backstop 無効を毎セッション可視化する（off 形骸化の防止）。
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
  CONTEXT="${CONTEXT} | [WARNING] AEGIS_TDD_MODE=off — TDD backstop はこのセッション無効（テスト無しの本番編集でも確認なし）"
fi

emit_context SessionStart "$CONTEXT"
exit 0

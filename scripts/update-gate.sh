#!/usr/bin/env bash
# Gate update script — the ONLY authorized way to change gate values.
# Called by /gate command via Bash tool. Updates STATUS.md and .gate-snapshot atomically.
# Because this runs via Bash (not Edit/Write), it naturally bypasses post-status-audit.sh.
#
# Usage: bash scripts/update-gate.sh <gate-name> [approve|na|reset] [--ack "reason"]
#   approve (default): pending → approved
#   na:                pending → n/a (only brainstorm/plan)
#   reset:             approved/n/a → pending
#   --ack "reason":    acknowledge a 🟡 (tri-state) judge result when approving
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATUS_FILE="${ROOT}/docs/STATUS.md"
SNAPSHOT_DIR="${ROOT}/.claude"
SNAPSHOT_FILE="${SNAPSHOT_DIR}/.gate-snapshot"

GATE_NAME="${1:-}"
ACTION="${2:-approve}"
ACK_FLAG="${3:-}"
ACK_REASON="${4:-}"

VALID_GATES="client_ready_for_dev brainstorm plan review qa security deploy dev_ready_for_client"
VALID_ACTIONS="approve na reset"

# --- Argument validation ---

if [ -z "$GATE_NAME" ]; then
  echo "Usage: bash scripts/update-gate.sh <gate-name> [approve|na|reset]"
  echo ""
  echo "Valid gates: $VALID_GATES"
  echo "Actions: approve (default), na, reset"
  echo ""
  # Show current gate status if STATUS.md exists.
  if [ -f "$STATUS_FILE" ]; then
    echo "Current gate status:"
    grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep "^  " | sed 's/^  /  /' || true
  fi
  exit 1
fi

VALID=false
for g in $VALID_GATES; do
  if [ "$g" = "$GATE_NAME" ]; then
    VALID=true
    break
  fi
done

if [ "$VALID" = "false" ]; then
  echo "ERROR: Invalid gate name '$GATE_NAME'"
  echo "Valid gates: $VALID_GATES"
  exit 1
fi

VALID_ACTION=false
for a in $VALID_ACTIONS; do
  if [ "$a" = "$ACTION" ]; then
    VALID_ACTION=true
    break
  fi
done

if [ "$VALID_ACTION" = "false" ]; then
  echo "ERROR: Invalid action '$ACTION'"
  echo "Valid actions: $VALID_ACTIONS"
  exit 1
fi

if [ ! -f "$STATUS_FILE" ]; then
  echo "ERROR: docs/STATUS.md not found"
  exit 1
fi

# --- Read current value ---
# Escape GATE_NAME for use in sed/grep patterns (defensive; current valid gates
# are all [a-z_] but this guards against future additions).
GATE_NAME_SED=$(printf '%s\n' "$GATE_NAME" | sed 's/[.[\/*^$&]/\\&/g')

CURRENT=$(grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep -m1 "  ${GATE_NAME}:" | sed "s/.*${GATE_NAME_SED}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

if [ -z "$CURRENT" ]; then
  echo "ERROR: Gate '$GATE_NAME' not found in STATUS.md gate_approvals"
  exit 1
fi

# --- Action-specific validation and target value ---

TARGET_VALUE=""
ACTION_TAG=""

case "$ACTION" in
  approve)
    if [ "$CURRENT" = "approved" ]; then
      echo "Gate '$GATE_NAME' is already approved. No change needed."
      exit 0
    fi
    if [ "$CURRENT" = "n/a" ]; then
      echo "ERROR: Gate '$GATE_NAME' is marked n/a (not applicable). Cannot approve."
      echo "If this gate should be active, first reset it to 'pending' via: bash scripts/update-gate.sh $GATE_NAME reset"
      exit 1
    fi
    # Context validation: delegate to check_status.py (tri-state 0/1/2).
    # set +e: python returning non-zero is expected (deny/ack) — must not abort
    # before echoing.
    set +e
    GATE_CHECK=$(python3 "${SCRIPT_DIR}/check_status.py" --root "$ROOT" --pre-approve-gate "$GATE_NAME" 2>&1)
    GATE_CHECK_RC=$?
    set -e
    if [ -n "$GATE_CHECK" ]; then
      echo "$GATE_CHECK"
    fi
    if [ "$GATE_CHECK_RC" -eq 0 ]; then
      : # 🟢 approvable — fall through
    elif [ "$GATE_CHECK_RC" -eq 2 ]; then
      # 🟡 needs ack: approve only when an explicit reason is supplied.
      if [ "$ACK_FLAG" != "--ack" ] || [ -z "$ACK_REASON" ]; then
        echo ""
        echo "🟡 要確認の項目があります（上記）。承認するには理由を添えてください:"
        echo "  bash scripts/update-gate.sh $GATE_NAME approve --ack \"確認した理由\""
        exit 1
      fi
      CARD="${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md"
      if [ -f "$CARD" ]; then
        printf '\n## ACK\n- %s （%s）\n' "$ACK_REASON" "$(date '+%Y-%m-%d %H:%M')" >> "$CARD"
      fi
      # Brace-delimit ${CARD}: bash 3.2 (macOS default) mis-parses a bare $CARD
      # immediately followed by a multibyte char like ）, yielding "unbound var".
      echo "[gate-ack] ${GATE_NAME}: 🟡 を ack で承認（理由記録: ${CARD}）"
    else
      # 🔴 (1) or any unexpected code: hard block.
      exit 1
    fi
    TARGET_VALUE="approved"
    ACTION_TAG="gate-approve"
    ;;
  na)
    if [ "$CURRENT" = "approved" ]; then
      echo "ERROR: Gate '$GATE_NAME' is already approved. Cannot set to n/a."
      echo "If this gate should be skipped, first reset it to 'pending' via: bash scripts/update-gate.sh $GATE_NAME reset"
      exit 1
    fi
    if [ "$CURRENT" = "n/a" ]; then
      echo "Gate '$GATE_NAME' is already n/a. No change needed."
      exit 0
    fi
    # Validate which gates can be set to n/a.
    # set +e: python returning non-zero is expected (deny) — must not abort before echoing.
    set +e
    NA_CHECK=$(python3 "${SCRIPT_DIR}/check_status.py" --root "$ROOT" --pre-na-gate "$GATE_NAME" 2>&1)
    NA_CHECK_RC=$?
    set -e
    if [ $NA_CHECK_RC -ne 0 ]; then
      echo "$NA_CHECK"
      exit 1
    fi
    TARGET_VALUE="n/a"
    ACTION_TAG="gate-na"
    ;;
  reset)
    if [ "$CURRENT" = "pending" ]; then
      echo "ERROR: Gate '$GATE_NAME' is already pending. No reset needed."
      exit 1
    fi
    TARGET_VALUE="pending"
    ACTION_TAG="gate-reset"
    ;;
esac

# --- Gate → ref mapping (mirrors check_status.py gate_ref_mapping) ---
get_ref_key() {
  case "$1" in
    plan) echo "plan" ;;
    review) echo "review" ;;
    qa) echo "qa" ;;
    security) echo "security" ;;
    deploy) echo "deploy" ;;
    client_ready_for_dev) echo "translation" ;;
    *) echo "" ;;
  esac
}

# --- Update STATUS.md ---

echo "[${ACTION_TAG}] $GATE_NAME: $CURRENT → $TARGET_VALUE"

TMP="${STATUS_FILE}.tmp.$$"
# Scope sed to gate_approvals section only — prevents matching same key names
# in other sections (e.g., current_refs also has review, qa, security, deploy).
# Use | delimiter in substitution to avoid conflict with n/a value containing /.
sed "/^gate_approvals:/,/^[a-z]/ s|\(  ${GATE_NAME_SED}:\).*|\1 ${TARGET_VALUE}|" "$STATUS_FILE" > "$TMP" && mv "$TMP" "$STATUS_FILE"

# --- Reset: also null the corresponding ref ---
if [ "$ACTION" = "reset" ]; then
  REF_KEY=$(get_ref_key "$GATE_NAME")
  if [ -n "$REF_KEY" ]; then
    REF_KEY_SED=$(printf '%s\n' "$REF_KEY" | sed 's/[.[\/*^$&]/\\&/g')
    TMP2="${STATUS_FILE}.tmp2.$$"
    sed "/^current_refs:/,/^[a-z]/ s|\(  ${REF_KEY_SED}:\).*|\1 null|" "$STATUS_FILE" > "$TMP2" && mv "$TMP2" "$STATUS_FILE"
    echo "[${ACTION_TAG}] current_refs.${REF_KEY} → null"
  fi
fi

# --- Update snapshot atomically ---

mkdir -p "$SNAPSHOT_DIR"
sed -n '/^gate_approvals:/,/^[a-z]/{ /^gate_approvals:/p; /^  /p; }' "$STATUS_FILE" > "$SNAPSHOT_FILE" 2>/dev/null || true
# Preserve phase in snapshot (used by post-status-audit.sh for phase transition monitoring).
grep -m1 "^phase:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true
# Preserve mode in snapshot (used by post-status-audit.sh for mode change monitoring).
grep -m1 "^mode:" "$STATUS_FILE" >> "$SNAPSHOT_FILE" 2>/dev/null || true

echo "[${ACTION_TAG}] STATUS.md and .gate-snapshot updated."

# --- Show result ---

echo ""
echo "Current gate status:"
grep -A20 "^gate_approvals:" "$STATUS_FILE" | grep "^  " | sed 's/^  /  /' || true

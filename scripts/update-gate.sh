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

source "${ROOT}/hooks/lib/frontmatter.sh"

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
    frontmatter_section "$STATUS_FILE" gate_approvals | grep "^  " | sed 's/^  /  /' || true
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

# --- Exclusive lock (P3-3): mkdir is atomic on POSIX; flock(1) absent on macOS ---
# Acquired BEFORE reading CURRENT (T3 v1.5.1): read→validate→write all happen
# inside the lock, so a concurrent update cannot invalidate the read (TOCTOU).
LOCK_DIR="${SNAPSHOT_DIR}/.gate-update.lock.d"
mkdir -p "$SNAPSHOT_DIR"
LOCK_OK=false
LOCK_HOLDER_PID=""
for _ in {1..50}; do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OK=true
    # rm pid first: rmdir alone would always fail once the pid file exists.
    trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    printf '%s' "$$" > "$LOCK_DIR/pid"
    break
  fi
  # Orphan-claim restore (T4a v1.5.2): per the claim protocol below, pid and
  # pid.claim.* never coexist (a claim is created only by atomically mv-ing the
  # pid file away). A lingering claim whose claimer is DEAD therefore means the
  # claimer crashed between mv and rm/undo — restore it to pid and let the
  # dead-pid reclaim below decide on the ORIGINAL holder pid it contains.
  # Live claimer or non-numeric suffix: leave alone (fail-closed). mv failure
  # is ignored — a concurrent restorer winning the race is equivalent.
  for _claim in "$LOCK_DIR"/pid.claim.*; do
    [ -e "$_claim" ] || continue
    _claimer="${_claim##*.}"
    case "$_claimer" in
      ''|*[!0-9]*) continue ;;
    esac
    if ! kill -0 "$_claimer" 2>/dev/null && [ ! -e "$LOCK_DIR/pid" ]; then
      mv "$_claim" "$LOCK_DIR/pid" 2>/dev/null || true
    fi
  done
  # Stale-lock reclaim (T4 v1.5.1): atomic-mv claim protocol. Only a purely
  # numeric pid of a DEAD process is reclaimed; missing/empty/garbage pid or a
  # live holder falls through to wait (fail-closed). mv of the pid file is an
  # atomic rename, so at most one contender wins the claim — a slow loser can
  # never delete a lock that a faster winner has already re-acquired.
  pid1=$(cat "$LOCK_DIR/pid" 2>/dev/null || true)
  case "$pid1" in
    ''|*[!0-9]*) ;;  # no/garbage pid → do not reclaim
    *)
      LOCK_HOLDER_PID="$pid1"
      if ! kill -0 "$pid1" 2>/dev/null; then
        CLAIM="$LOCK_DIR/pid.claim.$$"
        if mv "$LOCK_DIR/pid" "$CLAIM" 2>/dev/null; then
          pid2=$(cat "$CLAIM" 2>/dev/null || true)
          if [ "$pid2" = "$pid1" ]; then
            rm -f "$CLAIM" 2>/dev/null || true
            rmdir "$LOCK_DIR" 2>/dev/null || true
          else
            # A faster reclaimer re-acquired between our read and mv — undo.
            mv "$CLAIM" "$LOCK_DIR/pid" 2>/dev/null || true
          fi
        fi
      fi
      ;;
  esac
  # Pid-less adoption (T4b v1.5.2): a crash between mkdir and the pid write
  # (kill -9, trap not yet installed) leaves a pid-less dir forever. NEVER
  # delete it — an age check followed by rm/rmdir is check-then-act and can
  # destroy a NEW live winner's lock (grill-plan A red-2, reproduced). Instead
  # ADOPT it: atomically create our pid via O_EXCL (noclobber) — the kernel
  # picks at most one winner in a single syscall; losers observe a live pid
  # and wait. Age gate: POSIX -mmin +1 compares floor(age/60) > 1, i.e.
  # effectively >2 min (BSD/GNU common; avoids a stat -f/-c fork). Dir mtime
  # refreshes on any entry add/remove — mkdir itself, the pid write, and every
  # claim create/remove each reset it — so a freshly acquired or actively
  # contested lock is always young and never passes the age gate (tests fake
  # age via touch -t AFTER adding entries). Find of a vanished dir is silenced. An
  # EXISTING empty/garbage pid structurally defeats O_EXCL and stays
  # manual-removal (fail-closed). SIGSTOP >2 min inside the original holder's
  # mkdir->write window can still cross with an adopter — accepted residual
  # (single-user operation), recorded in v152-security.md.
  if [ ! -e "$LOCK_DIR/pid" ]; then
    _has_claim=false
    for _claim in "$LOCK_DIR"/pid.claim.*; do
      [ -e "$_claim" ] && _has_claim=true && break
    done
    if [ "$_has_claim" = "false" ] \
       && [ -n "$(find "$LOCK_DIR" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
      if ( set -C; printf '%s' "$$" > "$LOCK_DIR/pid" ) 2>/dev/null; then
        LOCK_OK=true
        trap 'rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
        break
      fi
    fi
  fi
  sleep 0.2
done
if [ "$LOCK_OK" != "true" ]; then
  if [ -n "$LOCK_HOLDER_PID" ] && kill -0 "$LOCK_HOLDER_PID" 2>/dev/null; then
    echo "ERROR: another live gate update (pid ${LOCK_HOLDER_PID}) holds the lock (${LOCK_DIR})."
    echo "Retry shortly."
  else
    echo "ERROR: a stale gate-update lock blocks this run (${LOCK_DIR})."
    echo "Retry shortly. If no other session is running, remove the stale directory."
  fi
  exit 1
fi

# --- Read current value ---
# Escape GATE_NAME for use in sed/grep patterns (defensive; current valid gates
# are all [a-z_] but this guards against future additions).
GATE_NAME_SED=$(printf '%s\n' "$GATE_NAME" | sed 's/[.[\/*^$&]/\\&/g')

CURRENT=$(frontmatter_section "$STATUS_FILE" gate_approvals | grep -m1 "  ${GATE_NAME}:" | sed "s/.*${GATE_NAME_SED}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)

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
    # B2 judge-card push (P1-C2, OBS-019): print the full card into the
    # transcript so the LLM relays it to the client. Pull-only cards (/judge)
    # never reached non-engineer clients in the behavioral review.
    # Gate list duplicates check_status.py JUDGE_GATES (bash cannot import it).
    case "$GATE_NAME" in
      review|qa|security|deploy)
        CARD_FILE="${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md"
        if [ -f "$CARD_FILE" ]; then
          echo ""
          echo "===== JUDGE CARD (${GATE_NAME}) ====="
          cat "$CARD_FILE"
          echo "===== END JUDGE CARD ====="
          echo "[judge-card] 上のカードを平易な日本語で依頼者に提示してください（「次のアクション」欄は文脈に合わせて補完）。"
        fi
        ;;
    esac
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
# Single pass: gate value and (for reset) ref null-ing land in one write so a
# concurrent reader never observes the intermediate state.
SED_ARGS=(-e "/^gate_approvals:/,/^[a-z]/ s|\(  ${GATE_NAME_SED}:\).*|\1 ${TARGET_VALUE}|")
if [ "$ACTION" = "reset" ]; then
  REF_KEY=$(get_ref_key "$GATE_NAME")
  if [ -n "$REF_KEY" ]; then
    REF_KEY_SED=$(printf '%s\n' "$REF_KEY" | sed 's/[.[\/*^$&]/\\&/g')
    SED_ARGS+=(-e "/^current_refs:/,/^[a-z]/ s|\(  ${REF_KEY_SED}:\).*|\1 null|")
  fi
fi
sed "${SED_ARGS[@]}" "$STATUS_FILE" > "$TMP" && mv "$TMP" "$STATUS_FILE"
if [ "$ACTION" = "reset" ] && [ -n "${REF_KEY:-}" ]; then
  echo "[${ACTION_TAG}] current_refs.${REF_KEY} → null"
fi

# --- Update snapshot atomically ---

mkdir -p "$SNAPSHOT_DIR"
# K-7 (v1.6.2): atomic write — see post-status-audit.sh for rationale.
_AEGIS_SNAP_TMP="${SNAPSHOT_FILE}.tmp.$$"
{
  sed -n '/^gate_approvals:/,/^[a-z]/{ /^gate_approvals:/p; /^  /p; }' "$STATUS_FILE" 2>/dev/null
  grep -m1 "^phase:" "$STATUS_FILE" 2>/dev/null
  grep -m1 "^mode:" "$STATUS_FILE" 2>/dev/null
} > "$_AEGIS_SNAP_TMP" 2>/dev/null && \
  mv "$_AEGIS_SNAP_TMP" "$SNAPSHOT_FILE" 2>/dev/null || \
  rm -f "$_AEGIS_SNAP_TMP" 2>/dev/null || true

echo "[${ACTION_TAG}] STATUS.md and .gate-snapshot updated."

# --- Show result ---

echo ""
echo "Current gate status:"
frontmatter_section "$STATUS_FILE" gate_approvals | grep "^  " | sed 's/^  /  /' || true

#!/usr/bin/env bash
# Neutralize untrusted, project-authored free text (STATUS.md blockers/next_action,
# LEARNINGS.md content) before it is injected into a hook's additionalContext.
#
# Why: session-start.sh concatenates these values — which originate from client
# requirements / upstream artifacts / failure logs — into the model's context
# alongside trusted framework signals (gate state). Without neutralization a
# crafted blocker can read like an instruction (prompt injection) and an
# unbounded value silently grows the per-session context budget.
#
# Pure bash 3.2 (parameter expansion only); no external interpreter.
#
# Source: source "$(dirname "$0")/lib/sanitize.sh"

# Truncate a UTF-8 string to at most MAX *bytes* WITHOUT splitting a multibyte
# character. `local LC_ALL=C` forces byte semantics for ${#s} / ${s:o:l};
# `printf '%d' "'X"` returns a SIGNED char so byte values are normalized with
# +256. Appends an ellipsis when truncation occurs. (Verified across all byte
# boundaries on bash 3.2; valid UTF-8 in every case, set -euo pipefail safe.)
_aegis_utf8_trunc() {
  local s=$1 max=$2
  local LC_ALL=C
  if [ "${#s}" -le "$max" ]; then printf '%s' "$s"; return; fi
  s=${s:0:max}
  local cont=0 i b ord
  for ((i=0; i<3; i++)); do
    b=${s: -1-i:1}
    [ -z "$b" ] && break
    ord=$(printf '%d' "'$b")
    [ "$ord" -lt 0 ] && ord=$((ord+256))
    if [ "$ord" -ge 128 ] && [ "$ord" -le 191 ]; then cont=$((cont+1)); else break; fi
  done
  local lead_idx=$(( ${#s} - 1 - cont ))
  if [ "$lead_idx" -ge 0 ]; then
    local lead=${s:$lead_idx:1} lord need=0
    lord=$(printf '%d' "'$lead")
    [ "$lord" -lt 0 ] && lord=$((lord+256))
    if   [ "$lord" -ge 240 ]; then need=3
    elif [ "$lord" -ge 224 ]; then need=2
    elif [ "$lord" -ge 192 ]; then need=1
    else need=0
    fi
    if [ "$lord" -ge 128 ] && [ "$need" -ne "$cont" ]; then
      s=${s:0:lead_idx}
    fi
  fi
  printf '%s…' "$s"
}

# aegis_sanitize_field VALUE [MAXLEN]
#   - collapses newlines/tabs/CR to single spaces
#   - strips C0 control bytes (0x01-0x1F minus the whitespace handled above)
#   - removes [ ] < > so untrusted text cannot forge a data fence or pseudo-tag
#   - squeezes repeated spaces, trims ends
#   - UTF-8-safely truncates to MAXLEN bytes (default 200) with an ellipsis
aegis_sanitize_field() {
  local s=$1 max=${2:-200}
  s=${s//$'\n'/ }
  s=${s//$'\t'/ }
  s=${s//$'\r'/ }
  # NOTE: this C0 set is duplicated in hooks/lib/emit.sh::_aegis_json_escape on
  # purpose — emit.sh must stay free of any inter-lib dependency (fail-closed
  # contract), so it cannot source this file. Keep both sets in sync if changed.
  local _aegis_ctl=$'\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
  s=${s//[$_aegis_ctl]/ }
  s=${s//[<>]/}
  s=${s//\[/}
  s=${s//\]/}
  while [[ $s == *"  "* ]]; do s=${s//  / }; done
  s=${s#"${s%%[![:space:]]*}"}
  s=${s%"${s##*[![:space:]]}"}
  if [ -n "$s" ]; then
    s=$(_aegis_utf8_trunc "$s" "$max")
  fi
  printf '%s' "$s"
}

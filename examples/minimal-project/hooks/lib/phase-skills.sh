#!/usr/bin/env bash
# Single owner of the phase -> required-skill map (P1-A, OBS-004/020/031/035).
#
# Every Aegis skill ships with disable-model-invocation:true and (except
# session-recovery) user-invocable:false, so the ONLY way a skill can boot is
# an explicit instruction to Read its file. This lib turns the current phase
# into that instruction. Consumers: hooks/session-start.sh (session entry) and
# hooks/post-status-audit.sh (phase transition).
#
# Contract: scripts/check_reference_drift.py (check_skill_reachability) parses
# the `names="..."` assignments below as reachability roots. Keep the literal
# `names="` syntax when editing.

# aegis_phase_skill_paths <root> <phase> [task_type]
# Prints one skill path per line. Existence-filtered: partial installs
# (minimal/standard profiles) must never be told to Read an undistributed file.
aegis_phase_skill_paths() {
  local root="$1" phase="$2" task_type="${3:-}"
  local names=""
  case "$phase" in
    onboard|discovery|requirements|scope|acceptance)
      names="client-workflow" ;;
    handover)
      names="client-workflow translation-mapping" ;;
    brainstorm)
      if [ "$task_type" = "bugfix" ] || [ "$task_type" = "hotfix" ]; then
        names="bug-diagnosis tdd"
      else
        names="aegis-brainstorm"
      fi ;;
    plan)
      names="subagent-dev" ;;
    implement)
      names="subagent-dev tdd" ;;
    review)
      names="aegis-review-gate subagent-dev" ;;
    qa)
      names="qa-verification" ;;
    security)
      names="aegis-security-gate" ;;
    deploy)
      names="deploy" ;;
    ship|docs)
      names="ship-and-docs user-manual uat maintenance docs-sync" ;;
    *)
      names="" ;;
  esac
  local n
  for n in $names; do
    if [ -f "${root}/.claude/skills/${n}/SKILL.md" ]; then
      printf '.claude/skills/%s/SKILL.md\n' "$n"
    fi
  done
}

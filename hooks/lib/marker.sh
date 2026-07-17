#!/usr/bin/env bash
# Marker positive-proof core (SF-014 / iter71). Single implementation of the
# 4-stage "did >=1 test actually execute" verdict, consumed by THREE callers:
#   - hooks/lib/evidence.sh              (source; hook-observed entries)
#   - scripts/record-test-result.py      (subprocess; green-record gate)
#   - scripts/run-test-strength-drill.py (subprocess; baseline proof gate)
# Stage logic MOVED VERBATIM from evidence.sh _check_test_marker (C-2 v1.6.1 /
# K-1 v1.6.2); pattern data stays single-sourced in patterns.sh.
#
# Pipeline (moved verbatim from evidence.sh):
#   (1) No-run flag check — if the command itself contains a no-run flag
#       like `--version`, `--collect-only`, `-h`, `--dry-run`, no test ran
#       regardless of output → "false". (Closes the
#       `echo "===== 1 passed in 0.01s =====" && pytest --collect-only`
#       grill-code A-Crit-2 / B-Critical forge.)
#   (2) Strong markers (AEGIS_TEST_PASS_MARKER_REGEX) — single-line
#       sufficient candidate. pytest === summary, jest "Tests:",
#       go "ok pkg X.Xs", etc. Any hit → proceed to zero-run gate.
#   (3) Weak markers (AEGIS_TEST_PASS_MARKER_PAIRS) — each entry is
#       "ANCHOR|||COMPANION"; BOTH halves must hit the output. unittest
#       and cargo: `Ran N tests in` + `OK`/`FAILED`, `running N tests`
#       + `test result: ok./FAILED.`. Any hit → proceed to zero-run gate.
#   (4) K-1 (v1.6.2) Zero-run gate — after a marker candidate, run three
#       independent axes:
#         Axis 1 (universal): output contains a zero-run regex
#         (`collected 0 items`, `no tests ran`, `Ran 0 tests`,
#         `test result: ok. 0 passed`, etc.) → "false".
#         Axis 2 (pytest only): exitCode == 5 (no tests collected) → "false".
#         Axis 3 (pytest only): strong marker hit but ZERO prologue lines
#         (platform/rootdir/collected/cachedir/plugins) → "false".
#       Axis 2 and 3 require the command to match
#       AEGIS_TEST_IS_PYTEST_REGEX. The gate ensures REDTEAM-01 and its
#       grill-derived variants (output filter / stderr suppression /
#       prologue-less forge) all fail-closed.
#   (5) iter72 (SF-014 count proof) — for each count-capable family whose
#       summary is DETECTed in the output (AEGIS_TEST_COUNT_FAMILIES), compute
#       executed = passed+failed (skips excluded) and require >=1 in at least
#       one detected family. No family detected (bare `go test`) keeps the
#       stage-1-4 verdict — the documented SF-014 residual.
#
# aegis_marker_verdict <exit_code> <command>
#   stdin : test output text (the CALLER decides windowing; record/drill pass
#           the FULL text, evidence.sh passes its head+tail window)
#   stdout: "true" | "false" with rc 0
#   rc 3  : evaluation impossible (patterns.sh not loaded / pattern data
#           missing) — every caller must treat this as NOT verified.
# NOTE: the rc3 guard below requires ALL SEVEN pattern sources non-empty.
# If a future patterns.sh edit legitimately empties one (e.g. every runner
# gains a STRONG marker and PAIRS goes away), update the guard in the SAME
# change — otherwise every consumer hard-fails with rc3.

_AEGIS_MARKER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=patterns.sh
source "${_AEGIS_MARKER_LIB_DIR}/patterns.sh" 2>/dev/null || true

aegis_marker_verdict() {
  local exit_code="$1" cmd="$2" out pat split anchor companion
  # rc3 guard: the verdict is meaningless without the full pattern data.
  # ${arr[*]:-} keeps this bash-3.2 / set-u safe when patterns.sh is absent.
  if [ -z "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PASS_MARKER_PAIRS[*]:-}" ] || \
     [ -z "${AEGIS_TEST_ZERO_RUN_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_PROLOGUE_REGEX[*]:-}" ] || \
     [ -z "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ] || \
     [ -z "${AEGIS_TEST_COUNT_FAMILIES[*]:-}" ]; then
    return 3
  fi
  out="$(cat)"
  if [ -z "$out" ]; then
    printf 'false'
    return 0
  fi
  # Stage 1: no-run flag in the command disqualifies regardless of output.
  if [ -n "${AEGIS_TEST_NO_RUN_FLAG_REGEX:-}" ] && \
     printf '%s' "$cmd" | grep -qE "$AEGIS_TEST_NO_RUN_FLAG_REGEX"; then
    printf 'false'
    return 0
  fi
  # Stage 2 / 3: did any marker hit?
  local marker_hit=0
  if [ "${#AEGIS_TEST_PASS_MARKER_REGEX[@]}" -gt 0 ]; then
    for pat in "${AEGIS_TEST_PASS_MARKER_REGEX[@]}"; do
      if printf '%s' "$out" | grep -qE "$pat"; then
        marker_hit=1
        break
      fi
    done
  fi
  if [ $marker_hit -eq 0 ] && [ "${#AEGIS_TEST_PASS_MARKER_PAIRS[@]}" -gt 0 ]; then
    for split in "${AEGIS_TEST_PASS_MARKER_PAIRS[@]}"; do
      anchor="${split%%\|\|\|*}"
      companion="${split##*\|\|\|}"
      if [ -z "$anchor" ] || [ -z "$companion" ] || [ "$anchor" = "$split" ]; then
        continue
      fi
      if printf '%s' "$out" | grep -qE "$anchor" && \
         printf '%s' "$out" | grep -qE "$companion"; then
        marker_hit=1
        break
      fi
    done
  fi
  if [ $marker_hit -eq 0 ]; then
    printf 'false'
    return 0
  fi
  # Stage 4: zero-run gate (K-1 v1.6.2). The marker hit is necessary but
  # not sufficient — any axis below downgrades to false.
  # Axis 1: universal output zero-run regex.
  if [ "${#AEGIS_TEST_ZERO_RUN_REGEX[@]}" -gt 0 ]; then
    for pat in "${AEGIS_TEST_ZERO_RUN_REGEX[@]}"; do
      if printf '%s' "$out" | grep -qE "$pat"; then
        printf 'false'
        return 0
      fi
    done
  fi
  # Axes 2 & 3: only apply when the command is in the pytest family.
  local is_pytest=0
  if [ -n "${AEGIS_TEST_IS_PYTEST_REGEX:-}" ] && \
     printf '%s' "$cmd" | grep -qE "$AEGIS_TEST_IS_PYTEST_REGEX"; then
    is_pytest=1
  fi
  if [ $is_pytest -eq 1 ]; then
    # Axis 2: pytest exit 5 = no tests collected.
    if [ -n "$exit_code" ] && \
       [ "$exit_code" = "${AEGIS_TEST_ZERO_RUN_EXIT_PYTEST:-5}" ]; then
      printf 'false'
      return 0
    fi
    # Axis 3: strong marker hit but ZERO prologue lines.
    if [ "${#AEGIS_TEST_PROLOGUE_REGEX[@]}" -gt 0 ]; then
      local prologue_hit=0 ppat
      for ppat in "${AEGIS_TEST_PROLOGUE_REGEX[@]}"; do
        if printf '%s' "$out" | grep -qE "$ppat"; then
          prologue_hit=1
          break
        fi
      done
      if [ $prologue_hit -eq 0 ]; then
        printf 'false'
        return 0
      fi
    fi
  fi
  # Stage 5 (iter72 SF-014): count proof. Stages 2-4 prove a summary LINE
  # exists; they do not prove any test BODY ran (all-skip suites: unittest
  # counts skipped tests inside `Ran N`; go -v prints only `--- SKIP:`).
  # ANY rule: multiple families in one real run's output only occur under
  # attacker-controlled output (the echo residual (b), out of scope), while
  # an ALL rule would misreject a real run that happens to quote a nested
  # runner's output. Arithmetic errors fail CLOSED (true->false only).
  local entry seg t nsep fam_detect fam_exec fam_mode fam_minus rest
  local lines grc n m num
  local family_detected=0 count_ok=0
  # -a on every Stage-5 grep: in a UTF-8 locale GNU grep treats a stray
  # non-UTF-8 byte (which out="$(cat)" does not strip, unlike NUL) as "binary"
  # and prints "Binary file (standard input) matches" INSTEAD of the matching
  # lines — the digit extraction would then sum to 0 and flip a real green run
  # to false (iter72 review F4). -a forces text mode (no-op on BSD grep, which
  # never triggered this) and restores BSD/GNU parity per the file header.
  for entry in "${AEGIS_TEST_COUNT_FAMILIES[@]}"; do
    # iter72 review (F6): strict 5-field parse — a stale/hand-edited entry
    # (typo'd `||` separator, emptied field) is a CORRUPT install, not a
    # skippable family. Silently `continue`-ing would fail OPEN (reopen the
    # all-skip veto hole with no signal), so malformation returns rc3 =
    # "evaluation impossible", which every caller treats as NOT verified.
    seg="$entry"; nsep=0
    while :; do
      t="${seg#*\|\|\|}"
      [ "$t" = "$seg" ] && break
      nsep=$((nsep + 1)); seg="$t"
    done
    [ "$nsep" -eq 4 ] || return 3
    fam_detect="${entry#*\|\|\|}"
    rest="${fam_detect#*\|\|\|}"
    fam_detect="${fam_detect%%\|\|\|*}"
    fam_exec="${rest%%\|\|\|*}"; rest="${rest#*\|\|\|}"
    fam_mode="${rest%%\|\|\|*}"; fam_minus="${rest#*\|\|\|}"
    if [ -z "$fam_detect" ] || [ -z "$fam_exec" ] || \
       { [ "$fam_mode" != "sum" ] && [ "$fam_mode" != "lines" ]; }; then
      return 3
    fi
    # iter72 review (F5): distinguish grep rc1 (no match = family absent) from
    # rc>1 (the host grep REJECTED the DETECT regex). Swallowing the latter as
    # "absent" would silently disable this family's veto on that install —
    # exactly the all-skip forgery class Stage 5 closes — so a regex the host
    # grep cannot compile fails CLOSED to rc3, not open.
    lines="$(printf '%s' "$out" | grep -aE "$fam_detect")"; grc=$?
    [ "$grc" -gt 1 ] && return 3
    [ "$grc" -eq 0 ] || continue    # rc1: family not present in this output
    family_detected=1
    if [ "$fam_mode" = "lines" ]; then
      n="$(printf '%s' "$out" | grep -acE "$fam_exec")"; grc=$?
      [ "$grc" -gt 1 ] && return 3
    else
      n=0
      # digit tokens only after the final grep -oE '[0-9]+' — unquoted word
      # splitting is glob-safe; 10# blocks octal on zero-padded counts; the
      # 9-char cap keeps a FORGED astronomic count inside bash arithmetic
      # (overflow would crash out of the normal "false" path) — >=1
      # semantics only need magnitude, not precision.
      for num in $(printf '%s' "$lines" | grep -aoE "$fam_exec" | grep -aoE '[0-9]+' || true); do
        num="${num:0:9}"
        n=$((n + 10#$num))
      done
      if [ -n "$fam_minus" ]; then
        m=0
        for num in $(printf '%s' "$out" | grep -aoE "$fam_minus" | grep -aoE '[0-9]+' || true); do
          num="${num:0:9}"
          m=$((m + 10#$num))
        done
        n=$((n - m))
        if [ "$n" -lt 0 ]; then
          n=0
        fi
      fi
    fi
    if [ "$n" -ge 1 ]; then
      count_ok=1
      break
    fi
  done
  if [ "$family_detected" -eq 1 ] && [ "$count_ok" -eq 0 ]; then
    printf 'false'
    return 0
  fi
  printf 'true'
}

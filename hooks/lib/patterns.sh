#!/usr/bin/env bash
# Detection PATTERN DATA for Aegis hooks. Single source of truth for the
# destructive-command patterns consumed by check-destructive.sh.
# Source: source "$(dirname "$0")/lib/patterns.sh"
#
# NOTE: secret-file patterns intentionally live in check-secrets.sh, NOT here.
# That hook matches the same credential files in four context-specific forms
# (command-text regex, find -name globs, basename case, staged-path regex) whose
# nuances (anchors, id_rsa* vs id_rsa\b vs id_rsa.pub) do not reduce to a single
# glob array without losing coverage. Centralizing them is deferred until a real
# second consumer (e.g. a drift check) needs the list — see the Foundation plan.

# Destructive patterns matched against the LOWER-cased command ($CMD_LOWER).
AEGIS_DESTRUCTIVE_LOWER_REGEX=('drop\s+(table|database)' '\btruncate\b')
AEGIS_DESTRUCTIVE_LOWER_WARN=(
  "Destructive: SQL DROP detected."
  "Destructive: SQL TRUNCATE detected."
)

# Destructive patterns matched against the RAW command ($CMD).
# (rm -r has a safe-targets exception and is handled directly in the hook.)
AEGIS_DESTRUCTIVE_CMD_REGEX=(
  'git\s+push\s+.*(-f\b|--force)'
  'git\s+reset\s+--hard'
  'git\s+(checkout|restore)\s+\.'
  'git\s+branch\s+(-[a-zA-Z]*[dD]\b|--delete)'
  'git\s+(checkout|restore)\s+--\s+'
  'git\s+clean\s+.*-f'
  'git\s+filter-branch'
  'git\s+update-ref\s+-d'
  'git\s+reflog\s+expire.*--expire=now'
  'npx\s+rimraf'
  'find\s+.+\s+-delete'
)
AEGIS_DESTRUCTIVE_CMD_WARN=(
  "Destructive: git force-push rewrites remote history."
  "Destructive: git reset --hard discards uncommitted changes."
  "Destructive: discards all uncommitted working tree changes."
  "Destructive: branch deletion."
  "Destructive: discards changes to specific files."
  "Destructive: git clean removes untracked files."
  "Destructive: git filter-branch rewrites repository history (irreversible)."
  "Destructive: git update-ref -d deletes a ref permanently."
  "Destructive: git reflog expire --expire=now wipes reflog (no recovery)."
  "Destructive: npx rimraf bulk-deletes files recursively."
  "Destructive: find -delete bulk-deletes matching files."
)

# Test-runner classification patterns (E1 activity verification).
# Consumed by post-bash.sh (grep -E) and build-judge-card.py (python re).
# CONSTRAINT: stay within the regex subset that behaves identically in BSD/GNU
# `grep -E` AND Python `re` — no [[:space:]], no \b. Use ( |^|$) style
# boundaries instead. tests/test_patterns_parity.py enforces parity with
# shared fixtures; add a fixture line whenever you add a pattern.
#
# Command-position anchor (v1.5.1, nested-subshell extension v1.5.2): a runner
# name matches only at the start of a (sub)command — string start, after ; & |,
# through any run of subshell '(' at that position, across env assignments
# (FOO=bar ), or through known wrappers (npx/bunx, uv/poetry/pipenv run).
# Mentions as arguments (grep vitest package.json) do not match. Quoted spans
# are masked to Q before this anchor applies (T1 above), so quoted regex groups
# (grep -E "(pytest|...)") never reach it; the anchor stays as defense-in-depth
# for unmaskable malformed input (e.g. an unclosed quote). Consumers also
# normalize newlines to ';' BEFORE matching (grep '^' is per-line, python re
# '^' is string-start — normalization keeps the two engines in parity).
# Quote-span mask (T1 v1.5.2): consumers replace "…"/'…' spans with the inert
# token Q BEFORE matching, so quoted runner mentions — grep -E "(unittest|pytest)" f,
# grep "foo; pytest" f — never reach the classifier (quote-blind false-RED root
# fix). Substitution, NOT deletion: deletion would promote trailing arguments to
# command position ('"echo" pytest' -> ' pytest' = green forgery, grill A red-1).
# Apply DQ then SQ — the order is a convention pinned by the parity fixtures.
# Both patterns stay in the grep-E/python-re common subset and contain no '/'
# (safe as sed s/// payloads). Masking is CLASSIFICATION-ONLY: deny-side hooks
# (check-destructive / check-control-plane / check-secrets) must never mask —
# there it would be a quote-wrapping bypass (fail-open). The evidence log keeps
# the raw command (fidelity / payload_sha unchanged). If the number of STRIP
# patterns ever changes, update the `len(strips) != 2` guard in
# scripts/build-judge-card.py (and its pinning tests) in the same change.
AEGIS_TR_STRIP_DQ='"(\\.|[^"\\])*"'
AEGIS_TR_STRIP_SQ="'[^']*'"

_AEGIS_TR_PRE='(^|[;&|]) *(\( *)*([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*((npx|bunx) +|(uv|poetry|pipenv) +run +)?'
AEGIS_TEST_RUNNER_REGEX=(
  "${_AEGIS_TR_PRE}vitest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}jest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}pytest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}python3? +-m +pytest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}python3? +-m +unittest($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}cargo +test($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}go +test($|[^a-zA-Z0-9_])"
  "${_AEGIS_TR_PRE}(npm|pnpm|bun|yarn) +(run +)?test(:[-a-zA-Z0-9_]+)?($|[^a-zA-Z0-9_])"
)

# C-2 (v1.6.1): pass-MARKER regex. Matching AEGIS_TEST_RUNNER_REGEX above only
# proves the COMMAND was a test runner — not that any test ran. `pytest --version`,
# `pytest --collect-only`, `pytest -k __NEVER_MATCH__` all match runner regex
# yet execute zero tests. The marker array below matches each runner's
# FINAL SUMMARY LINE so the consumer can distinguish "real test execution"
# from "runner-named-but-no-tests-ran". post-bash-observe.sh and
# build-judge-card.py both consume this single source.
#
# CONSTRAINT (same as runner regex): grep-E ∩ python-re common subset — no
# [[:space:]], no \b. Use ( |^|$) style boundaries.
#
# Each entry is anchored to a separator before the marker so a free-text
# "1 passed" in a previous line cannot satisfy the regex; we require the
# runner's actual final summary form (== N passed in / Tests: N passed /
# test result: ok / Ran N tests in / OK at line start / ok pkg X.Xs).
AEGIS_TEST_PASS_MARKER_REGEX=(
  # pytest: "============ 3 passed in 0.42s ============" or "1 failed, 2 passed in"
  '={3,} [0-9]+ (passed|failed)'
  # jest / vitest: "Tests:       5 passed, 5 total"
  '(^|\n)Tests:[ \t]+([0-9]+ failed,[ \t]+)?[0-9]+ passed'
  '(^|\n)Test Files[ \t]+[0-9]+ passed'
  # cargo: "test result: ok. 12 passed; 0 failed; ..."
  '(^|\n)test result: (ok|FAILED)\.'
  # go: "ok      example/pkg     0.123s"  or  "FAIL    example/pkg     [build failed]"
  '(^|\n)(ok|FAIL)[ \t]+[A-Za-z0-9_./-]+[ \t]+[0-9]+\.[0-9]+s'
  # python -m unittest: "Ran 17 tests in 89.6s" plus the OK / FAILED line
  '(^|\n)Ran [0-9]+ tests? in [0-9]+(\.[0-9]+)?s'
  '(^|\n)OK( \(.+\))?( |$)'
  '(^|\n)FAILED \('
)

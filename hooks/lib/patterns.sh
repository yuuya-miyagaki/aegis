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
  '(^|[^[:alnum:]_])dd\s+.*\bof='
  '(^|[^[:alnum:]_])chmod\s+(-[a-zA-Z]*R[a-zA-Z]*\b|--recursive\b)'
  '(^|[^[:alnum:]_])mkfs(\.|[[:space:]]|$)'
  '(^|[^[:alnum:]_])shred([[:space:]]|$)'
  '(^|[^0-9>])>\s*/(etc|usr|bin|sbin|boot|sys|lib)(/|[[:space:]]|$)'
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
  "Destructive: dd writes directly to a device/file (overwrites raw blocks)."
  "Destructive: recursive chmod (-R) changes permissions across a whole tree."
  "Destructive: mkfs formats a filesystem (destroys all data on it)."
  "Destructive: shred securely wipes files (unrecoverable)."
  "Destructive: redirect truncates a system path."
)

# Deploy-command detection. Single source of truth (G3, iter42): consumed by
# check-deploy-gate.sh (gates actual deploy execution) AND check-cron-gate.sh
# (asks when a scheduled prompt contains a deploy command). Keeping it here
# stops the two hooks from drifting. NOTE: git-push-as-deploy (heroku/dokku) and
# variable-indirected deploys ($V deploy) are intentionally NOT matched — a git
# push is indistinguishable from a normal remote update (same rationale as the
# MCP push exclusion), and var-indirection is the accepted SF-004 class.
AEGIS_DEPLOY_REGEX='(^|[[:space:];&|])(vercel +deploy|vercel( +--[A-Za-z][A-Za-z0-9-]*(=[^[:space:];&|]*)?)*[[:space:]]*($|[;&|>])|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy|wrangler +(deploy|publish))'

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
# v1.6.1 grill-code Critical: an output containing JUST "OK" or just
# "test result: ok." is forgeable in 1 line — `pytest --version && echo OK`.
# We split markers into STRONG (single-line sufficient) and WEAK (pair
# required). The consumer (evidence.sh) requires BOTH halves of any pair to
# be present in the output for marker_verified=true. Also see the no-run-flag
# guard in evidence.sh that disqualifies `pytest --collect-only` etc.
#
# STRONG markers: each line includes runner-specific structural anchors
# (===== prefix for pytest, "Tests:" prefix for jest, package-path+time
# for go) that are not trivially echoed. These verify on their own.
AEGIS_TEST_PASS_MARKER_REGEX=(
  # pytest: "============ 3 passed in 0.42s ============" or "1 failed, 2 passed in"
  '={3,} [0-9]+ (passed|failed)'
  # jest / vitest: "Tests:       5 passed, 5 total"
  '(^|\n)Tests:[ \t]+([0-9]+ failed,[ \t]+)?[0-9]+ passed'
  '(^|\n)Test Files[ \t]+[0-9]+ passed'
  # go: "ok      example/pkg     0.123s"  or  "FAIL    example/pkg     [build failed]"
  '(^|\n)(ok|FAIL)[ \t]+[A-Za-z0-9_./-]+[ \t]+[0-9]+\.[0-9]+s'
)

# WEAK markers: each individual line is too easy to forge with `echo`.
# Each entry is "ANCHOR_REGEX|COMPANION_REGEX" — BOTH must hit the output.
# Format: anchor and companion are separated by `|||` (a token that never
# appears in regex). evidence.sh splits on this token before grep-ing.
# - unittest:    `Ran N tests in X.Xs`  AND  `OK` / `FAILED (...)`
# - cargo test:  `running N tests`      AND  `test result: ok./FAILED.`
AEGIS_TEST_PASS_MARKER_PAIRS=(
  '(^|\n)Ran [0-9]+ tests? in [0-9]+(\.[0-9]+)?s|||(^|\n)(OK( \(|$)|FAILED \()'
  '(^|\n)running [0-9]+ tests?|||(^|\n)test result: (ok|FAILED)\.'
)

# No-run flags — when present in the COMMAND, the run produced no tests
# regardless of output content. Used to disqualify forged-output cases
# where a runner-name match is paired with a non-running flag.
# Each pattern is anchored on word boundaries via ( |^|$).
AEGIS_TEST_NO_RUN_FLAG_REGEX='(^|[[:space:]])(-{1,2}(version|help|collect-only|co|dry-run|no-run|fixtures|markers|listTests|list-tests|listFiles|listAllFiles)|-h)($|[[:space:]])'

# K-1 (v1.6.2): zero-run output signals. After strong/weak marker has hit,
# scan the output for runner-emitted "no tests actually ran" lines. This
# closes the REDTEAM-01 forge:
#   echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__
# where the echo provides the strong marker and pytest writes `collected 0
# items` / `no tests ran` to stdout. Each pattern targets a specific
# runner's zero-execution finalizer line.
#
# CONSTRAINT (same as runner regex): grep-E ∩ python-re common subset — no
# [[:space:]], no \b. Use ( |^|$) style boundaries.
AEGIS_TEST_ZERO_RUN_REGEX=(
  '(^|\n)collected 0 items'                     # pytest
  '(^|\n)no tests ran'                          # pytest -k <NOMATCH>
  '(^|\n)Ran 0 tests'                           # unittest
  '(^|\n)No tests (found|ran)'                  # pytest/jest variant
  '(^|\n)test result: (ok|FAILED)\. 0 passed'   # cargo
  '(^|\n)Tests:[ \t]+0 passed[ \t]*,[ \t]*0 total' # jest "0 passed, 0 total"
  '(^|\n)Test Files[ \t]+0 passed'              # vitest
  '(^|\n)0 passing(\b|$)'                       # mocha
  '(^|\n)PASS[ \t]+\([ \t]*0 tests'             # go test -v: "PASS\t(0 tests"
)

# K-1 (v1.6.2): pytest prologue regex. When a pytest-family command runs,
# pytest prints a multi-line prologue (platform/Python version, rootdir,
# collected N items) BEFORE the strong summary. A forged `echo "== 3 passed
# in 0.42s ====="` produces ONLY the summary line with no prologue. If a
# pytest-classified command yields a strong-marker hit but the output has
# NONE of the prologue lines, treat as zero-run (axis 3). This is
# pytest-only — jest/vitest/cargo/go have less stable prologues and
# applying this check there would produce false positives.
AEGIS_TEST_PROLOGUE_REGEX=(
  '(^|\n)platform [A-Za-z0-9_]+ -- Python'      # pytest header
  '(^|\n)rootdir: '                              # pytest rootdir
  '(^|\n)collected [0-9]+ item'                  # pytest collection
  '(^|\n)cachedir: '                             # pytest cachedir
  '(^|\n)plugins: '                              # pytest plugins line
)

# K-1 (v1.6.2): command-side classifier — "is this command in the pytest
# family?". Axes 2 (exit code) and 3 (prologue) apply ONLY to pytest, since
# other runners' exit codes and prologues are inconsistent. Matches the
# pytest entries in AEGIS_TEST_RUNNER_REGEX above.
AEGIS_TEST_IS_PYTEST_REGEX='(^|[;&|]| |\()(npx +|bunx +|(uv|poetry|pipenv) +run +)?(pytest|python3? +-m +pytest)($|[^a-zA-Z0-9_])'

# K-1 (v1.6.2): pytest-only zero-run exit code. Other runners' exit codes
# do not uniquely encode "no tests ran" (e.g. unittest returns 0 on `Ran 0
# tests in 0.001s OK`). pytest exit 5 = "no tests collected" is the only
# reliable cross-version signal.
# Reference: https://docs.pytest.org/en/stable/reference/exit-codes.html
AEGIS_TEST_ZERO_RUN_EXIT_PYTEST=5

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
  "破壊的: SQL DROP を検出（テーブル/データベースを削除します・復元不可）。"
  "破壊的: SQL TRUNCATE を検出（テーブルの全行を削除します・復元不可）。"
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
  # iter61 (full-review R1): tree-revert forms a verification subagent used in
  # the iter60 incident. Only shapes a branch name cannot take are matched
  # (glob / trailing slash / multi-arg / ' -- '); a single bare pathspec is
  # indistinguishable from a branch switch and stays allowed (accepted residue).
  'git\s+(-C\s+\S+\s+)?restore\s+[^-[:space:]]'
  'git\s+(-C\s+\S+\s+)?checkout\s+([^-][^;&|[:space:]]*)?([*?]|/($|[[:space:];&|]))'
  'git\s+(-C\s+\S+\s+)?checkout\s+[^-][^;&|[:space:]]*\s+([^-;&|#>[:space:]0-9]|[0-9]+[^>;&|[:space:]])'
  'git\s+(-C\s+\S+\s+)?(checkout|restore)\s+[^;&|]*\s--\s'
  'git\s+(-C\s+\S+\s+)?stash(\s*$|\s+(push|save)($|[^a-zA-Z])|\s*[0-9]*[;&|)#<>]|\s+-)'
  'git\s+(-C\s+\S+\s+)?stash\s+(drop|clear)($|[^a-zA-Z])'
  'git\s+(-C\s+\S+\s+)?checkout\s+(--?[a-zA-Z][a-zA-Z=-]*\s+)*(-[a-zA-Z]*f[a-zA-Z]*($|[[:space:]])|--force($|[^-a-zA-Z]))'
  'git\s+(-C\s+\S+\s+)?restore\s+(.*--(worktree|source)|-[a-zA-Z]*W)'
  'npx\s+rimraf'
  'find\s+.+\s+-delete'
  '(^|[^[:alnum:]_])dd\s+.*\bof='
  '(^|[^[:alnum:]_])chmod\s+(-[a-zA-Z]*R[a-zA-Z]*\b|--recursive\b)'
  '(^|[^[:alnum:]_])mkfs(\.|[[:space:]]|$)'
  '(^|[^[:alnum:]_])shred([[:space:]]|$)'
  '(^|[^0-9>])>\s*/(etc|usr|bin|sbin|boot|sys|lib)(/|[[:space:]]|$)'
)
AEGIS_DESTRUCTIVE_CMD_WARN=(
  "破壊的: git force-push はリモートの履歴を書き換えます（元に戻せません）。"
  "破壊的: git reset --hard は未コミットの変更を破棄します（復元できません）。"
  "破壊的: 作業ツリーの未コミット変更をすべて破棄します（復元できません）。"
  "破壊的: ブランチを削除します（未マージのコミットが失われる可能性があります）。"
  "破壊的: 指定ファイルの変更を破棄します（復元できません）。"
  "破壊的: git clean は未追跡ファイルを削除します（復元できません）。"
  "破壊的: git filter-branch はリポジトリ履歴を書き換えます（元に戻せません）。"
  "破壊的: git update-ref -d は参照(ref)を完全に削除します（復元不可）。"
  "破壊的: git reflog expire --expire=now は reflog を消去します（復旧手段が失われます）。"
  "破壊的: git restore <パス> は指定ファイルの未コミット変更を破棄します（復元できません）。"
  "破壊的: グロブ/ディレクトリ指定の git checkout はパスとして扱われ、該当ファイルの未コミット変更を一括破棄します（復元できません）。"
  "破壊的: 複数引数の git checkout はパス指定として扱われ、未コミット変更を破棄します（復元できません）。"
  "破壊的: -- 付きの git checkout/restore は指定パスの未コミット変更を破棄します（復元できません）。"
  "破壊的: git stash は未コミット変更を作業ツリーから退避・除去します（並走セッション/親セッションの進行中作業が消えたように見えます）。"
  "破壊的: git stash drop/clear は退避済みの変更を削除します（復元できません）。"
  "破壊的: git checkout -f/--force は競合する未コミット変更を黙って破棄します（復元できません）。"
  "破壊的: --source/--worktree 付きの git restore は指定パスの未コミット変更を破棄します（復元できません）。"
  "破壊的: npx rimraf はファイルを再帰的に一括削除します（復元できません）。"
  "破壊的: find -delete は該当ファイルを一括削除します（復元できません）。"
  "破壊的: dd はデバイス/ファイルに直接書き込みます（生ブロックを上書き・復元不可）。"
  "破壊的: 再帰的な chmod (-R) はツリー全体の権限を変更します（元の権限を控えていないと戻せません）。"
  "破壊的: mkfs はファイルシステムを初期化します（その上の全データを破壊・復元不可）。"
  "破壊的: shred はファイルを完全消去します（復元不可）。"
  "破壊的: リダイレクトがシステムパスを上書き(truncate)します（元の内容は失われます）。"
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
  # iter71 (M10): bracket classes use a LITERAL TAB character (0x09), not \t —
  # BSD grep -E does not expand \t inside brackets (it matches literal
  # backslash + "t", which broke the go marker on macOS), and [[:space:]] is
  # banned by the grep-E/python-re parity constraint above. A literal TAB
  # behaves identically in BSD grep -E, GNU grep -E, and python re. Beware
  # editors converting the embedded tab to spaces.
  # jest / vitest: "Tests:       5 passed, 5 total". iter72: real jest orders
  # segments failed, skipped, todo, passed — any skipped/todo test broke the
  # old `(N failed,)? N passed` adjacency (empirically a false negative for
  # every suite with a skipped test). `([0-9]+ [a-z]+,[ 	]+)*` accepts the
  # intermediate segments; forge value is unchanged (the strict form was
  # already echoable) and Stage 5 still requires passed+failed >= 1.
  '(^|\n)Tests:[ 	]+([0-9]+ [a-z]+,[ 	]+)*[0-9]+ passed'
  # vitest: real output indents its summary (" Test Files  1 passed (1)") —
  # iter72 allows leading blanks (accept-side only; forge value unchanged).
  '(^|\n)[ 	]*Test Files[ 	]+[0-9]+ passed'
  # go: "ok      example/pkg     0.123s"  or  "FAIL    example/pkg     [build failed]"
  '(^|\n)(ok|FAIL)[ 	]+[A-Za-z0-9_./-]+[ 	]+[0-9]+\.[0-9]+s'
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
# iter69 grill-code + blind-2nd (2026-07-14): `collectonly` (pytest's no-dash
# alias for --collect-only), `setup-plan`, `setup-only`, `fixtures-per-test`
# were empirically verified to run ZERO test bodies (`pytest --X -s` prints no
# body marker), so paired with an import-crash mutant they reconstruct the R4
# forge (no-run command → fake DRILL PASS with zero assertions). The denylist
# had missed them. Verified NON-matches that DO run bodies and must stay out:
# `--setup-show` (runs tests, shows fixture setup). NOTE: an enumerated denylist
# is inherently incomplete — the robust long-term fix is a positive "N tests
# actually executed" proof (follow-up candidate). This regex is the single
# source consumed by both evidence.sh (marker realness) and the B1 drill; the
# drill also shlex-normalizes the command first so quoting can't smuggle a flag.
AEGIS_TEST_NO_RUN_FLAG_REGEX='(^|[[:space:]])(-{1,2}(version|help|collect-only|collectonly|co|dry-run|no-run|setup-plan|setup-only|fixtures-per-test|fixtures|markers|listTests|list-tests|listFiles|listAllFiles)|-h)($|[[:space:]])'

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
# iter72: the cargo line-deny (`test result: ... 0 passed`) was REMOVED — an
# empty doc-tests section emits exactly that line on every real run of a
# doc-test-less crate (empirically: verdict false = false negative), while
# the attack it guarded (echoed pair + a REAL zero-run cargo alongside) is
# strictly dominated by pure echo with no cargo run at all (already true
# today; cargo has no prologue/exit-code second axis). The all-ignored case
# stays rejected by the Stage 5 count sum in marker.sh (moat pin unchanged:
# tests/test_marker_lib.py test_cargo_all_ignored_false_moat_pin).
AEGIS_TEST_ZERO_RUN_REGEX=(
  '(^|\n)collected 0 items'                     # pytest
  '(^|\n)no tests ran'                          # pytest -k <NOMATCH>
  '(^|\n)Ran 0 tests'                           # unittest
  '(^|\n)No tests (found|ran)'                  # pytest/jest variant
  # iter71 (M10): literal TAB (0x09) in brackets, not \t — same BSD grep -E
  # rationale as AEGIS_TEST_PASS_MARKER_REGEX above.
  '(^|\n)Tests:[ 	]+0 passed[ 	]*,[ 	]*0 total' # jest "0 passed, 0 total"
  '(^|\n)[ 	]*Test Files[ 	]+0 passed'         # vitest（iter72: インデント許容）
  '(^|\n)0 passing($|[^a-zA-Z])'               # mocha (iter71: \b -> common subset; BSD grep -E does not honor \b)
  '(^|\n)PASS[ 	]+\([ 	]*0 tests'             # go test -v: "PASS\t(0 tests"
)

# iter72 (SF-014 count proof): count-family data for marker.sh Stage 5. A
# STRONG/WEAK marker hit proves a summary LINE exists; the count stage
# additionally requires the summary's arithmetic to show >=1 test body
# actually executed (skips excluded). Entry format (`|||`-separated, the
# AEGIS_TEST_PASS_MARKER_PAIRS convention): NAME|||DETECT|||EXEC|||MODE|||MINUS
#   DETECT: family is present when any output line matches.
#   EXEC  : MODE=sum   -> sum every digit-run inside each EXEC match found on
#                         DETECT-matching lines (unittest MINUS scans the whole
#                         output — see the entry comment).
#           MODE=lines -> count EXEC-matching lines over the whole output.
#   MINUS : (sum only, may be empty) digit-run sum over the WHOLE output,
#           subtracted from the EXEC sum (floored at 0).
# Families NOT listed (bare `go test`: non-verbose output carries no counts)
# fall back to the Stage 1-4 verdict; that residual is pinned in
# tests/test_marker_lib.py and tracked in docs/security-followups.md SF-014.
# Extraction is heuristic text-mining over untrusted-ish output: mis-detection
# and over-subtraction fail CLOSED (false); over-addition needs attacker-
# controlled output = the echo residual (b), out of scope.
# CONSTRAINT (same as above): grep-E ∩ python-re common subset — no
# [[:space:]], no \b, literal TAB (0x09) inside brackets.
AEGIS_TEST_COUNT_FAMILIES=(
  # unittest: `Ran 5 tests in 0.010s` + `OK (skipped=2)` -> 5-2=3. MINUS scans
  # the WHOLE output. iter72 review (F0): the MINUS is ANCHORED to `[(,] ?` so
  # it only matches unittest's own `(skipped=N)` / `, skipped=N` summary tokens.
  # Without the anchor, incidental `skipped=N` text a test body prints (config
  # dumps, captured child output) over-subtracted and flipped a genuinely green
  # `python3 -m unittest` run to false (empirically confirmed). `unskipped=3`
  # substring hits are excluded by the same anchor. review M-2 (accepted
  # fail-closed residual, SF-014): an incidental `(skipped=N)` printed by a test
  # BODY still matches the `[(` half and over-subtracts -> the real run reads
  # false. Safe direction (never a false GREEN), rare, drill-subsumed; a
  # body-vs-summary split is not expressible in the grep-E∩python-re subset.
  'unittest|||(^|\n)Ran [0-9]+ tests? in|||Ran [0-9]+ tests?|||sum|||[(,] ?skipped=[0-9]+'
  # pytest: `===== 2 failed, 3 passed in 1.20s =====` -> 2+3. iter72 review (F1):
  # DETECT now REQUIRES a `N passed|failed` token, so a decorative wrapper/CI
  # banner (`===== build finished in 3.21s =====`) no longer false-detects the
  # pytest family and cross-family-vetoes a real green run of another runner.
  # (`3 skipped in` still has no passed/failed token -> not detected -> Stage
  # 1-4 verdict, which for pytest already rejects all-skip via the STRONG gate.)
  'pytest|||={3,} .*[0-9]+ (passed|failed).* in [0-9.]+s|||[0-9]+ (passed|failed)|||sum|||'
  # jest: `Tests:       1 failed, 2 skipped, 3 passed, 6 total` -> 1+3
  # (skipped/todo segments carry no passed|failed token).
  'jest|||(^|\n)Tests:[ 	]|||[0-9]+ (passed|failed)|||sum|||'
  # vitest: `      Tests  2 passed (2)` (indented) -> 2. iter72 review (F-2):
  # DETECT includes skipped|failed|todo so an all-skip vitest file (which still
  # prints `Test Files 1 passed` at file level, matching the relaxed STRONG
  # anchor) is DETECTed here and count(passed+failed)=0 -> vetoed to false.
  # Without this, the STRONG relaxation flipped a real all-skip vitest run from
  # false (iter71) to true (a false GREEN — the dangerous direction). Older
  # vitest with no `Tests` line at all still falls back to Stage 1-4.
  'vitest|||(^|\n)[ 	]*Tests[ 	]+[0-9]+ (passed|failed|skipped|todo)|||[0-9]+ (passed|failed)|||sum|||'
  # cargo: sum across ALL `test result:` lines (unit + doc-tests sections) —
  # fixes the empty-doc-tests false negative; all-ignored sums to 0 -> false.
  'cargo|||(^|\n)test result: (ok|FAILED)\.|||[0-9]+ (passed|failed)|||sum|||'
  # go -v: count `--- PASS:`/`--- FAIL:` lines; an all-skip -v run has only
  # `--- SKIP:` -> 0 -> false. Bare `go test` emits no counts -> family not
  # detected -> Stage 1-4 verdict (known residual, see array comment).
  'go-verbose|||(^|\n)--- (PASS|FAIL|SKIP):|||(^|\n)--- (PASS|FAIL):|||lines|||'
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

# --- iter75 SF-017: quote/backslash/${IFS}/行継続・改行 正規化（純 bash・parser なし） ---
# _obfuscated_unlock_on_cp（check-runtime-state.sh）と同一手法の拡張。呼び出し側は
# LC_ALL=C を export 済み前提。backslash-newline（行継続）と裸改行/タブも畳んで
# 行指向 grep の分割バイパス（iter75 fix-forward F2）を塞ぐ。brace/param-default/
# cmdsub は解決しない（SF-019 残余・構造化 argv 待ち）。
aegis_dequote_normalize() {
  local c=$1
  c=${c//\\$'\n'/}         # backslash-newline（行継続）除去 ← 最初（後段の裸BS除去より前）
  c=${c//\\/}              # 残り backslash 除去
  c=${c//\"/}              # 二重クォート除去
  c=${c//\'/}              # 単一クォート除去
  c=${c//$'\n'/ }          # 残る改行 → 空白（複数行の単一行化・行指向 grep 対策）
  c=${c//$'\t'/ }          # 残るタブ → 空白（改行と対称・raw でも \s カバー済みだが一貫のため）
  # ${IFS...} parameter-expansion family（${IFS}/${IFS:0:1}/${IFS: -1}/${IFS/x/y}/
  # ${IFS#}/${IFS:-x} 等）＋裸 $IFS → 空白。IFS 由来の展開値は常に空白の部分集合
  # （shell 仕様: IFS 既定 = space/tab/newline）ゆえ空白畳みが保守側 — 実 word-split
  # バイパスは捕捉し、:+/+ 等の非バイパス変種は無害な false-ASK に倒れる（MISS なし）。
  # 単一 sed で O(n)・非貪欲（[^}]* が } を跨がず a${IFS}b${IFS}c を a b c に保つ）。
  # bash の ${c//…} 全置換は多数一致で O(n²)・秒オーダー（grill-code G9 実測 5000 件で
  # ~21s）だが sed 全置換は同ケース ~40ms。呼び出し側 export の LC_ALL=C 下で sed は
  # 不正バイトでも crash しない（iter73 実証・両フックとも既に C locale で sed 使用）。
  # 改行/タブは上で畳み済みゆえ command-sub の trailing-NL strip は無害。
  # iter75 SEC-1（security 盲検2次・bash runtime 実証）。
  c=$(printf '%s' "$c" | sed -E 's/\$\{IFS[^}]*\}/ /g; s/\$IFS/ /g')
  printf '%s' "$c"
}

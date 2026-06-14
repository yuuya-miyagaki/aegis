# Migration History

aegis のバージョン間アップグレード注記。v1.6.0 までは README から移設（2026-06-14・docs-only。各版見出しを h2 に昇格した以外、本文は無改変）。v1.6.1〜v1.8.0 は事後に git 履歴から再構成した（2026-06-14）。

> 収録範囲: v0.5.0 → v1.8.0。以降の版は `git log` と `docs/STATUS.md` を参照のこと。

## From v1.7.2 to v1.8.0

**Non-breaking — P2 volatile-truth マニフェスト（プラットフォーム結合値の単一所有）。**

プラットフォーム依存の揮発値（モデル id/effort・hook event 名・tool 名・schema 検証日）を新規 `scripts/platform_manifest.py`（framework root 専用・example へは非ミラー）に集約し、生成と検証が同一マニフェストを import する構造にした。

- **モデル/effort ポリシーの値源が platform_manifest に移動。** `check_framework_contract.py` が許容モデル・禁止集合（haiku）・effort・opus-only ルールを manifest から import 照合する。`CLAUDE.md` の Model Policy は「モデル系統の更新は `platform_manifest.py` で行う」と明記（インラインで増やさない）。
- **drift lint にチェック追加（ALL_CHECKS 12→14）**: template の hook event が既知集合の部分か（FAIL）、tool-matcher トークンが既知レジストリ内か（WARN）、`platform_manifest.py` を持つ root の検証日 staleness（advisory）。
- 下流プロジェクトへの作業は基本不要（framework 内部の契約・drift 強化）。framework を保守する場合のみ、モデル系統や event/tool を増やすときは manifest を更新する。

## From v1.7.1 to v1.7.2

**Non-breaking（framework 開発者向け）— M1 example ミラー自動生成。**

- 新規 `scripts/sync_example_mirror.py` と `make example` ターゲットを追加。root の制御ファイルから `examples/minimal-project/` ミラーを再生成する。
- 制御ファイル（`hooks/`・`scripts/`・`.claude/` 等）編集後の `make example` 忘れは `check_reference_drift.py` のミラー同一性チェックが検出する。
- 下流プロジェクトへの作業は不要（framework リポジトリの開発フロー専用）。

## From v1.7.0 to v1.7.1

**Non-breaking — M3 STATUS パーサの bash 一本化。**

- `hooks/lib/frontmatter.sh` に `frontmatter_value`/`gate_value` アクセサを追加し、`session-start`・`pre-compact`・`post-status-audit` ほかの STATUS スカラ/ゲート読み取りをこれに統一した（実装ばらつきの解消）。
- **`frontmatter.sh` が全プロファイルの required に昇格。** 既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行して `frontmatter.sh` を配布すること。
- 挙動の変更はなし（内部リファクタ）。`examples/minimal-project/` ミラーも byte-identical に更新。

## From v1.6.3 to v1.7.0

**Non-breaking — P2-a 段階 HINT（phase nudge）のオプトアウト。**

- **`minimal`/`standard` プロファイルは phase HINT nudge を既定オフ**にした（インストール時に `AEGIS_NUDGE=off` を settings の `env` に書き込む）。`full` は従来どおり表示。
- 任意のプロファイルで `AEGIS_NUDGE=off`（小文字のみ）によりセッション単位で抑止可。抑止されるのは phase HINT の sermon のみで、ゲート・skill 起動経路・blockers・failure-tracking・unknown-phase 診断・安全警告は常に残る。
- unknown-phase 診断は nudge ゲートの外へ移動（nudge オフでも診断は出る）。setup は既存の `AEGIS_NUDGE` 値を保持（key-level setdefault）。
- 既存インストールで nudge を戻すには `.claude/settings.local.json` の `env.AEGIS_NUDGE` キーを削除する。

## From v1.6.2 to v1.6.3

**Non-breaking — 第7回全力レビュー由来の fail-closed 強化（R1–R4）。**

- `emit.sh` の JSON エスケープが C0 制御バイトを squash（fail-open な deny 経路を封鎖, R1）。
- session-start が信頼できない STATUS/LEARNINGS テキストを fence＋上限 cap してコンテキストに載せる（注入対策, R2/C1）。
- 入力抽出失敗時は fail-closed（R3）、再帰削除の検出が大文字小文字非依存に（R4）。
- 既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行して `emit.sh`・session-start を更新する。挙動はセキュリティ強化方向のみ。

## From v1.6.1 to v1.6.2

**Non-breaking — K シリーズ（配布完全性・安全性・原子性）。**

- **新規 `hooks/lib/safety.sh`**、各 hook の timeout 宣言、`.gate-snapshot` の原子的書き込み（K-5/6/7）。
- secrets deny の回避経路を追加封鎖: コマンド置換・クォート変数形（K-2/3/4）。
- 配布経路（install 出力）の堅牢化と setup の前提チェック（K-8〜11）。
- handover 成果物→テンプレートのマッピング、`full` プロファイル整備、早見表（K-12/13）。
- zero-run テストマーカー gate を 3 軸化（K-1）。
- 既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行（新 lib・timeout・原子的 snapshot を反映）。

## From v1.6.0 to v1.6.1

**Non-breaking — 機能整合／フルレビュー fix バッチ（C/S シリーズ）。**

- **新規 `hooks/lib/secrets-patterns.sh`（secrets パターンの単一所有）** を追加し `check-secrets.sh` をこれ経由に（C-9）。`lib/phase-skills.sh`・`lib/secrets-patterns.sh` を REQUIRED に登録（S-11）。
- 変数で組み立てた control-plane 書き込み・git stage ファイル名の deny（C-1 / grill-code A-Crit）、`.env` の `--git-dir`/`-C`/`stage`/`update-index` 経由ステージングの deny（S-3）、WRITE_OP regex の bypass 封鎖。
- **`client_ready_for_dev` が handover 成果物 6 点の内容を機械検査**（sentinel＋≥200 bytes, C-3）。
- **green テスト判定に `AEGIS_TEST_PASS_MARKER` を要求**（C-2）＋ zero-run flag guard。
- SessionStart matcher に `resume` を追加（C-4）、arch-overview の drift 是正と counts 固定（C-5/C-6）。
- 既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行（新 lib・更新 hook を反映）。

## From v1.5.2 to v1.6.0

**Non-breaking — 行動レビュー（2026-06-12）P1×4 の fix-forward バッチ（構造起動・配布完全性・可視化・対称検査）。**

- **skill が構造的に起動するようになった（P1-A）。** phase ごとの必読 skill が
  SessionStart と正当な phase 遷移時に additionalContext（advisory）で
  「`.claude/skills/<name>/SKILL.md` を Read」形式で注入される。
  phase→skill map は `hooks/lib/phase-skills.sh` が単一所有。
  additionalContext 未対応クライアントでは注入が消えるだけで deny/block 系は不変（fail-safe）。
  制御ファイル内の skill 参照は path 形式が起動形となり、起動経路のない skill は
  drift チェック（repo）と scaffold smoke（install 先）の両方で機械検出される。
- **full プロファイルが skill 参照テンプレート 6 件を配布する（P1-B）。**
  skill が参照するテンプレートの実在は drift＋install 先 smoke で契約化。
- **judge card がゲート承認時に transcript へ全文 push される（P1-C）。**
  pull 専用カードが非エンジニア依頼者に届かない問題の是正。/gate はカード提示→
  承認確認の順序。judge/drill の scanner はバイナリ混在 repo でも crash せず
  該当ファイルを skip（判定は unverified 方向＝green 偽装不能）。
- **client_ready_for_dev が handover 成果物 6 点を機械検査する（P1-D）。**
  承認側（pre-approve）と完了側（evidence integrity）の対称検査。
- drill の scope から vendor/build 区画（`node_modules`/`dist`/`build`/`out`/`coverage` 等)
  が恒久除外され、第三者コードによる scope 汚染がなくなった。

## From v1.5.1 to v1.5.2

**Non-breaking — v1.5.1 記録残余の全消化バッチ（誤判定根治・可用性向上）。**

- **テストランナー分類にクォートマスク正規化が入った（T1）。** 照合前に
  `"…"`/`'…'` span を不活性トークン `Q` に置換するため、
  `grep -E "(unittest|pytest)" f` や `grep "foo; pytest" f` のような
  クォート内ランナー言及の失敗が judge の 🔴 を誘発しない（false-RED 根治）。
  逆方向の変化として、`npx "vitest"`・`"pytest" -x` などクォートで包んだ
  ランナー起動は分類されず unverified（🟡 ack 可）に倒れる。マスクは分類専用で、
  deny 系 hook と evidence-log の記録（raw コマンド・payload_sha）には適用されない。
- 入れ子サブシェル `((pytest))` がコマンド位置として分類されるようになった（T2）。
- `\/` エスケープを含むペイロードも python3 fidelity 経路で抽出される（T3）。
- `update-gate.sh` のロックが自己修復するようになった（T4）: クラッシュで残った
  孤児 claim（claimer 死亡）は pid に復元して回収し、pid なしロック（実効 2 分超）
  は O_EXCL（noclobber）で原子的に採用する。空/garbage pid は従来どおり
  手動削除案内（fail-closed）。
- ロック待機窓が 2s → 10s に拡大した（T5）。軽量ゲート（reset・brainstorm approve
  等）の実競合は敗者も勝者完了後に自力取得できる。qa/security の pre-approve
  （B1 ドリル・audit_deps をロック内で実行、分オーダー）の競合は引き続き
  rc=1 → 再実行を案内する。

## From v1.5.0 to v1.5.1

**Non-breaking — grill 残余修正バッチ（防御強化・誤判定緩和）。**

- **テストランナー分類がコマンド位置アンカーになった（T1）。**
  `grep vitest package.json` や `echo pytest` のような「引数・文字列としての
  言及」はテスト実行と分類されなくなり、その失敗が judge の 🔴 を誘発しない。
  分類から外れたコマンドは unverified 方向に倒れる（fail-open しない）。
  `time pytest`・`bash -c "pytest"`・`if ...; then pytest; fi` 等のラッパー/
  制御構文形は分類されないため、ゲート承認前は実テストを
  直接実行（または `scripts/record-test-result.py` で手動記録）すること。
- deploy ゲートの ask/deny 文面に python の警告や traceback が混入しなくなった（T2）。
- `update-gate.sh` の排他ロックが読み取り前に取得され（T3）、kill 等で残った
  stale lock は保持プロセスの死亡を確認して自動回収される（T4）。生きた並行
  実行がある場合は pid 付きのエラーで待機を案内する。
- `check-control-plane.sh` が `find ... -exec/-delete` 系の書込形を deny する
  ようになり、`grep "confirm " hooks/x.sh` 等の正当読取りの誤 deny が解消（T5）。

## From v1.4.0 to v1.5.0

**Non-breaking — E1 activity verification (観測ベースのテスト検証).**

ゲート承認時のテスト判定は、エージェントの自己申告ではなく hook が観測した
実行記録（`.claude/evidence-log.jsonl`）に基づく。PostToolUse/PostToolUseFailure
(Bash) が全実行のメタ（コマンド・成否・worktree fingerprint）を記録し、judge card
が現在のコードと一致する最新のテスト実行を照合する。記録が無い・コード変更後の
場合は 🟡 unverified（`--ack` で承認可）、観測された red は 🔴 ブロック。
Claude Code 外でテストを実行した場合は `scripts/record-test-result.py` で
手動記録できる（同一スキーマ・`src:"manual"`）。

- **`docs/qa-reports/test-result.json`（自己申告ファイル）は廃止。**
  `record-test-result.py` は evidence-log への手動フォールバック書き手に変わった。
- **新規配布物**: `hooks/post-bash-observe.sh`（PostToolUse Bash 観測）、
  `hooks/lib/evidence.sh` / `hooks/lib/fingerprint.sh`（記録・指紋の単一所有）。
  既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行して
  hooks と settings を更新する。
- **完了時の生存チェック**: evidence-log ファイル不在（観測系が一度も発火して
  いない）を TaskCompleted が差し戻す。session-start がログを touch/ローテーション
  する（空ファイルは正常）。

## From v1.3.3 to v1.4.0

**Mostly non-breaking — evolution-review fix batch** (P2-1 … P3-6, B1, K-2;
review 2026-06-10). What changes for existing projects:

- **`standard` now ships the Bash guard moat (P2-1).** `check-destructive.sh`,
  `check-secrets.sh`, `check-deploy-gate.sh`, and `check-control-plane.sh` are
  registered in the `standard` profile's generated settings. Existing
  `standard` installs: re-run `bash bin/setup.sh --profile=standard` (or add
  the four PreToolUse Bash entries to `.claude/settings.local.json` by hand).
- **Deploy gate widened + size-skip now asks (P2-2, P2-3).** Flag-form
  `vercel --prod` and `wrangler deploy|publish` are now gated. S/M tasks
  (which skip the deploy phase) no longer deploy silently: the gate emits an
  `ask` so a human confirms the ungated deploy. RC contract:
  0=allow / 2 with a leading `ASK:`=ask / anything else=deny.
- **`ULTRA_PRECOMPACT_INTERVAL` renamed to `AEGIS_PRECOMPACT_INTERVAL`
  (P3-2).** The old name still works as a fallback for THIS release only and
  will be removed in the next one.
- **Generated settings reference hooks via `$CLAUDE_PROJECT_DIR` (P3-6).**
  cwd-relative `bash hooks/x.sh` silently disabled every hook when Claude Code
  was launched from a subdirectory. Existing installs: regenerate settings by
  re-running setup.sh, or rewrite each command to
  `bash "${CLAUDE_PROJECT_DIR:-.}"/hooks/<name>.sh` (the `:-.` fallback keeps
  hooks alive even where the variable is unset).
- **New: `docs/hook-failure-policy.md`** — the declared fail-open/fail-closed
  policy per hook, with a table-driven test keeping it honest. Read it before
  changing any hook's error handling.

## From v1.3.2 to v1.3.3

**Non-breaking — integrity-hook availability fixes** (evolution review
2026-06-10). The operating contract is unchanged and defense strength is
preserved (every probed bypass form stays denied); these fixes remove two
over-blocking defects that crippled scaffolded projects:

- **`check-control-plane` denied nearly every Bash command during project
  work.** The hook matched control-plane patterns against the RAW hook input,
  and real input always carries `transcript_path` under `~/.claude/projects/`
  (which contains `.claude/`), so the early-allow never fired. The hook now
  extracts the command (python3 first, bash fast-path, raw fallback stays
  fail-closed) and matches patterns against the command only, with root-anchored
  directory boundaries plus fixed-string absolute-path checks (logical and
  physical root forms).
- **`check-gate` blocked ordinary project paths.** Its `*/hooks/*`,
  `*/scripts/*`, `*CLAUDE.md` globs collided with project-owned paths such as
  `src/hooks/`, `src/templates/`, vendored `.claude/`, and nested `CLAUDE.md`.
  Protected paths are now anchored to the project root, dot-segments are
  lexically normalized, and root-escaping relative paths stay conservatively
  denied.
- **Hardening.** The scaffold smoke now drives hooks with a realistic input
  envelope (`transcript_path` included) and seals both fixes with live-fire
  checks, closing the same blind-spot family as v1.3.2's F6 (inspection inputs
  must match the real runtime schema).

**Action for existing projects**: replace the two hooks —
`hooks/check-control-plane.sh` and `hooks/check-gate.sh` — with the v1.3.3
versions (copy by hand, or re-run `bash bin/setup.sh` with `--force`; `--force`
overwrites all managed files, so review local edits first). Without this,
project-work sessions remain heavily over-blocked.

## From v1.3.1 to v1.3.2

**Non-breaking — install-delivery bug fixes** (functional-integrity audit
2026-06-07). The operating contract is unchanged; these fixes make scaffolded
projects actually ship and run what they were designed to. The audit found that
static checks (contract/eval/drift/mirror) only validated the framework repo and
the hand-maintained example — the `setup.sh` install path was never executed — so
several install-only breaks went unnoticed.

- **Hook libraries now ship (the big one).** `setup.sh` copied only
  `hooks/lib/extract-input.sh`, omitting `hooks/lib/emit.sh` (sourced by every
  hook) and `hooks/lib/patterns.sh`. Every hook died at `source lib/emit.sh` in
  `standard`/`full` installs, so the deterministic PaC moat silently failed open.
  `copy_hooks` now copies the whole `hooks/lib/*.sh`.
- **`/judge`, graceful `/retro`, `status_doctor` now ship in `full`.** `/judge`
  was in no profile; `/retro` shipped the non-graceful framework variant that
  hard-runs a script no profile ships; `session-recovery`'s `status_doctor.py`
  call had no installed script. All three are delivered now.
- **Hardening.** The scaffold smoke now *executes* installed hooks/scripts (not
  just checks files exist), and the contract manifest tracks all registered
  hooks. Plus two doc/comment polish items.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full`. The
previously-missing files (`hooks/lib/emit.sh`, `hooks/lib/patterns.sh`,
`.claude/commands/judge.md`, `scripts/status_doctor.py`) copy in automatically
(setup skips only files that already exist). To also replace the older
non-graceful `.claude/commands/retro.md`, pass `--force` or update that one file
by hand (`--force` overwrites all managed files, so review local edits first).

## From v1.3.0 to v1.3.1

**Docs-only — no action required.** Audit 2026-06-06 §4 priority-4 follow-up B4
(native-redundancy inventory). Adds the native delegation map to the
[Native Feature Mapping](../README.md#native-feature-mapping) table (what aegis keeps,
complements, or delegates vs. Checkpoints/`/rewind`, `/resume`, Auto Mode,
routines, and why) and a note in the `session-recovery` skill clarifying its
relationship to native `/resume`. No operating-contract, template, or behavior
changes; existing projects are unaffected. This completes the post-audit
B-series (B1–B4).

## From v1.2.0 to v1.3.0

**Non-breaking — additive lifecycle-completion features** (audit 2026-06-06 §4
priority-4 follow-ups B3c and B3b). With B3a (v1.2.0) these complete the
post-delivery lifecycle: ⑨ manual, ⑩ UAT, ⑫ maintenance. Existing projects keep
working; the one behavior change (UAT gate coupling) is conditional on having
defined acceptance criteria.

- **B3c — maintenance lifecycle (⑫).** A new `RUNBOOK.template.md` plus a single
  `maintenance` skill: Part A generates `docs/handover/RUNBOOK.md` (monitoring,
  triage, escalation, incident history) at ship; Part B runs the
  monitor→triage→route→record loop for production incidents, reusing
  `bug-diagnosis` + bugfix/hotfix for the actual fix. `ship-and-docs` (Step 2.6),
  `docs-sync`, and `bug-diagnosis` reference it; no new mode/phase/gate.
- **B3b — UAT execution (⑩).** A new `UAT-RESULTS.template.md` plus a `uat` skill:
  at ship, the client verifies the built product against `ACCEPTANCE.md`, records
  pass/fail + evidence per criterion, and signs off into
  `docs/handover/UAT-RESULTS.md` (`ship-and-docs` Step 2.7).
- **Gate change — `dev_ready_for_client` requires recorded UAT.** When
  `docs/requirements/ACCEPTANCE.md` exists, approving `dev_ready_for_client` is
  blocked unless `docs/handover/UAT-RESULTS.md` exists. Pass/fail is the client's
  sign-off; the machine only checks the artifact exists. Projects without
  ACCEPTANCE are unaffected (legacy behavior).

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full` to
pick up the new `maintenance`/`uat` skills and `RUNBOOK`/`UAT-RESULTS` templates.
Projects on `minimal`/`standard` get the updated `check_status.py` (the UAT gate
check) but not the new skills (those ship only in `full`).

## From v1.1.0 to v1.2.0

**Non-breaking — additive end-user manual generation** (audit 2026-06-06 §4
priority-4 follow-up B3a). No public operating-contract changes; existing
projects keep working.

- **B3a — audience-parameterized operation manual at the docs phase.** A new
  `user-manual` skill (`.claude/skills/user-manual/`) plus
  `templates/MANUAL.template.md` generate a task-oriented operation guide for the
  people who *use* or *operate* the delivered product, written so non-engineers
  can follow it.
- **`ship-and-docs` Step 2.5.** After the TO-CLIENT package is drafted,
  `ship-and-docs` reads `user-manual` and, when the product has users/operators,
  writes `docs/handover/MANUAL.md` (one procedure section per audience) and links
  it from the TO-CLIENT delivery summary. When no one uses or operates the
  product, no manual is generated and the reason is recorded in that slot.
- **`docs-sync` parity check.** For projects that warrant a manual, `docs-sync`
  verifies `docs/handover/MANUAL.md` exists and that its declared audiences
  (front-matter) map one-to-one to its procedure sections — no missing sections,
  no orphan sections — otherwise the "not applicable" reason must be recorded.
- **Registration.** The `user-manual` skill is registered in the `full` profile
  and the framework mirror; `templates/HANDOVER-TO-CLIENT.template.md` gains a
  manual slot.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full` to
pick up the new `user-manual` skill and `MANUAL.template.md`. Projects on
`minimal`/`standard` are unaffected — the skill ships only in `full`.

## From v1.0.0 to v1.1.0

**Non-breaking — additive deterministic-assurance features** (audit 2026-06-06 §4
priority-4 follow-ups B1/B2, plus the priority 1-3 fix-forwards). No public
operating-contract changes; existing projects keep working.

- **B1 — test-strength drill at the qa gate.** `pre_approve_gate` runs
  `scripts/run-test-strength-drill.py` live at qa approval: tests must catch the
  mutants seeded into changed code, or approval is refused. Tasks with no testable
  code declare an auditable skip (`{"skip": true, "reason": "..."}`) in
  `docs/qa-reports/test-strength.drill`.
- **B2 — judge card (tri-state) at review/qa/security/deploy.** `build-judge-card.py`
  runs at approval and emits 🟢/🔴/🟡: tier-1 machine facts (changed-line stub scan,
  secret scan, fingerprint-verified test result, B1 verdict) that contradict the
  report's recorded `claims:` block hard-block (🔴); a missing/divergent
  self-attested second opinion, absent claims, or a dependency-audit concern are
  advisory (🟡), approvable via `update-gate.sh <gate> approve --ack "reason"`
  (the reason is recorded into the card). `scripts/record-test-result.py` records
  the test result the judge reads; `/judge` previews the card read-only.
- **Gate exit codes are now tri-state.** `pre_approve_gate` / `update-gate.sh`
  return 0/1/2 (was 0/1). A judge that cannot run (e.g. non-git project) yields an
  ack-able 🟡, never a hard block, so one fault cannot lock every gate.
- **Hardening (priority 1-3):** gate fail-closed behavior, deploy boundary, and
  mirror-drift detection. New scripts are registered in the mirror and `full`
  profile; agents/skills document the `claims:` convention and blind second opinion.

## From v0.12.2 to v1.0.0

**Future-proof re-architecture (F→R→A→D).** Everything since the `v0.12.2` tag,
consolidated into the v1.0.0 milestone. The old "v0.13.0" line was reframed onto
the `0.12.x` series and lands here.

**Breaking — skill renames** (Phase 0b, official-name collision avoidance). Update
any external references (e.g. uccc) to the new names:

| Old skill | New skill |
|-----------|-----------|
| `brainstorming` | `aegis-brainstorm` |
| `review` | `aegis-review-gate` |
| `security-review` | `aegis-security-gate` |

**New enforcement / behavior:**

1. **New gate hooks**: `check-skill-gate.sh` (Skill), `check-cron-gate.sh` (CronCreate),
   and Task event hooks — `check-task-created.sh` (TaskCreated → `continue:false` hard
   stop when a gate blocks a new task) and `check-task-completed.sh` (TaskCompleted →
   `exit 2` push-back).
2. **Evidence-completion enforcement** (v0.12.6): TaskCompleted pushes back when an
   approved `review`/`qa`/`security`/`deploy`/`plan` gate has no `current_refs` entry,
   or a declared ref points to a missing file. Same invariant as `check_framework_contract`.
3. **Model/effort policy**: agent frontmatter is now pinned by role tier (quality
   roles on `opus`, cost roles on `sonnet`, default `inherit`); `haiku` removed.
4. **TDD profile**: the `check-tdd.sh` backstop ships only in `full`; within `full`,
   `AEGIS_TDD_MODE=off` disables it for a session (session-start warns).
5. **Leaner rules**: `routing.md` reduced to principles + agent manifest; `CLAUDE.md`
   dropped the hard context-doc count (pull-based).
6. **Internal (behavior-unchanged)**: hook output schemas unified in `hooks/lib/emit.sh`,
   destructive patterns in `hooks/lib/patterns.sh`.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=<your-profile>`
to refresh `.claude/settings.local.json` and hooks, then update any external skill
references to the renamed `aegis-*` skills above.

## From v0.12.1 to v0.12.2

**Hot-fix release**: Hook output schemas migrated to current Claude Code spec.
The old form (top-level `permissionDecision`/`message`) is silently ignored
by Claude Code 2.x — `deny` / `block` were not actually enforced before this fix.

1. **PreToolUse 8 hooks**: top-level `permissionDecision`/`message` → `hookSpecificOutput.permissionDecision`/`permissionDecisionReason`. Affects `check-gate.sh`, `check-control-plane.sh`, `check-secrets.sh`, `check-destructive.sh`, `check-deploy-gate.sh`, `check-deploy-mcp-gate.sh`, `check-tdd.sh`, `check-client-info.sh`.
2. **PostToolUse hook** (`post-status-audit.sh`): top-level `permissionDecision`/`message` → top-level `decision: "block"`/`reason`. Restores gate-tamper / phase-skip / mode-tamper detection.
3. **post-bash.sh**: migrated from `PostToolUse` to **`PostToolUseFailure`** event. Output uses `hookSpecificOutput.additionalContext` (informational; never blocks). The internal exit-code check is removed — the event itself fires only on failures.
4. **pre-compact.sh**: block path → top-level `decision`/`reason`; allow path → `hookSpecificOutput.additionalContext` + `hookEventName`.
5. **`if` filter removed** from `templates/hooks.template.json` for `post-status-audit.sh`. The official spec restricts `if` to a single permission rule (no `||`). Replaced by the existing `case TARGET_FILE in *STATUS.md` filter inside the hook script (covers Edit/Write/NotebookEdit fully).
6. **New event registration**: `PostToolUseFailure` section added to `templates/hooks.template.json` for `post-bash.sh`.
7. **Contract tests**: new `tests/test_hook_output_schema.py` (12 cases) covers all hook output schemas. Reference: `hooks/session-start.sh` was already conformant.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=<your-profile>` to refresh `.claude/settings.local.json` with the new `templates/hooks.template.json`. The old schema was already non-functional in Claude Code 2.x, so this is a strict improvement (no functional regression).

Driven by a 5-round external review (Round 1〜5, 25 issues raised, all reflected). See `docs/plans/v0130-modernization-plan.md` Rev.5 for full context. The follow-on work (Skill/Cron gates, Task event hooks, the re-architecture) shipped on the `0.12.x` line — see *From v0.12.2 to v1.0.0* above.

## From v0.9.0 to v0.10.0

1. **browser-assist skill added**: new `.claude/skills/browser-assist/SKILL.md`
   provides shared browser automation foundation (gstack `$B` + Playwright MCP
   fallback); any agent can load it via `skills:` frontmatter array
2. **integration-assist refactored**: `$B` resolution logic and bash code blocks
   moved to browser-assist; integration-assist now references browser-assist for
   browser operations and focuses on service connection workflow
3. **qa-browser agent updated**: now loads `browser-assist` skill; `$B` preferred
   for navigation/interaction, Playwright MCP for console/network diagnostics;
   `Bash` removed from `disallowedTools` (needed for `$B` commands)
4. **integration-specialist agent updated**: `skills:` expanded to
   `[browser-assist, integration-assist]` (first multi-skill agent)
5. **routing.md updated**: browser-assist availability note added
6. **CLAUDE.md Skills list**: `browser-assist` added to the skill listing
7. **extensions/qa-browser/WORKFLOW.md updated**: browser-assist priority
   (`$B` preferred, Playwright MCP as fallback/diagnostics)
8. **Skill count**: 14 → 15 skills

## From v0.8.0 to v0.9.0

1. **integration-specialist agent added**: new `.claude/agents/integration-specialist.md`
   handles external service integration (API setup, OAuth, webhooks) with browser
   automation via gstack `$B`; copy to your project's `.claude/agents/`
2. **integration-assist skill added**: new `.claude/skills/integration-assist/SKILL.md`
   guides service connection with 6-step workflow (identify → research → automate →
   handoff → configure → test); copy to your project's `.claude/skills/`
3. **routing.md updated**: `integration-specialist` route added
4. **CLAUDE.md Skills list**: `integration-assist` added to the skill listing
5. **Optional dependency**: gstack browse (`$B`) enables browser automation with
   handoff/resume; skill falls back to guided text instructions when not installed
6. **Agent count**: 11 → 12 agents; Skill count: 13 → 14 skills

## From v0.7.3 to v0.8.0

1. **translation-specialist agent added**: new `.claude/agents/translation-specialist.md`
   supports Client→Dev handover translation; copy to your project's `.claude/agents/`
2. **translation-mapping skill added**: new `.claude/skills/translation-mapping/SKILL.md`
   guides creation of `docs/translation/mapping.md`; copy to your project's `.claude/skills/`
3. **check-client-info.sh hook added**: new `hooks/check-client-info.sh` denies
   requirements edits in Client mode when `docs/client/context.md` is absent;
   copy to `hooks/` and register in PreToolUse `Edit|Write|NotebookEdit` matcher
4. **Client directories added**: create `docs/client/`, `docs/translation/`,
   `docs/decisions/` in your project; scaffold with `bin/setup.sh --profile=full`
5. **Client templates added**: 5 new templates in `templates/`:
   `CLIENT-CONTEXT.template.md`, `CLIENT-GLOSSARY.template.md`,
   `CLIENT-OPEN-QUESTIONS.template.md`, `TRANSLATION-MAPPING.template.md`,
   `HANDOVER-TO-DEV.template.md` (updated)
6. **state-machine.md updated**: Client mode purpose statement added
7. **client-workflow SKILL.md updated**: Translation Artifact section added
   with `docs/translation/mapping.md` handover prerequisite
8. **session-start.sh updated**: handover phase hint split from acceptance;
   includes mapping.md requirement note
9. **STATUS.md schema**: add `translation: null` to `current_refs`
10. **Gate contract expanded**: `client_ready_for_dev` gate now checks
    `docs/translation/mapping.md` existence via `check_status.py`
11. **CLAUDE.md Skills list**: `translation-mapping` added to the skill listing
12. **Agent count**: 10 → 11 agents; Skill count: 12 → 13 skills

## From v0.7.2 to v0.7.3

1. **qa-verification skill added**: new `.claude/skills/qa-verification/SKILL.md`
   provides QA phase verification process (test execution, evidence collection,
   reproduction templates); copy to your project's `.claude/skills/`
2. **Agent skills preload unified**: `reviewer.md` now preloads `review`,
   `security.md` preloads `security-review`, `qa.md` preloads `qa-verification`;
   add `skills:` frontmatter to your agent files
3. **MCP catalog added**: `extensions/mcp/` provides configuration templates
   for 5 recommended MCP servers (Playwright, GitHub, Context7, Vercel, Figma);
   copy needed `.json` files and merge into your `.mcp.json`
4. **session-start.sh updated**: qa and security phase hints now include
   skill references (`skill: qa-verification`, `skill: security-review`)
5. **CLAUDE.md Skills list**: `qa-verification` added to the skill listing
6. **Skill count**: 11 → 12 skills

## From v0.7.1 to v0.7.2

1. **check-control-plane.sh added**: new Bash PreToolUse hook that denies
   control plane file writes (STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/)
   during non-framework tasks; register in Bash PreToolUse before check-destructive.sh
2. **NotebookEdit added to matchers**: PreToolUse and PostToolUse matchers
   expanded from `Edit|Write` to `Edit|Write|NotebookEdit` (defense-in-depth)
3. **extract\_file\_path notebook\_path fallback**: `hooks/lib/extract-input.sh`
   now falls back to `notebook_path` when `file_path` is empty (NotebookEdit support)
4. **Template reference drift fixed**: corrected stale skill/agent names in
   PLAN, VERIFICATION, DEPLOY-CHECKLIST templates and session-start.sh
5. **`/validate` scaffold-safe**: example project's `/validate` now runs
   `check_status.py` only (not `check_framework_contract.py`)
6. **check\_status.py in Quick Start**: step 11 added for copying the script
   into scaffolded projects

## From v0.7.0 to v0.7.1

1. **PreCompact hook added**: `hooks/pre-compact.sh` blocks compaction when
   STATUS.md is stale (not updated within 5 min during active phase);
   register `PreCompact` in your hooks settings
2. **qa-browser agent added**: `.claude/agents/qa-browser.md` provides safe
   Playwright MCP access via `disallowedTools` (Edit/Write/NotebookEdit/Bash denied);
   update routing rules to include `qa-browser`
3. **QA agent updated**: browser QA section now delegates to qa-browser
   instead of the "Orchestrator Action Required" handoff
4. **Auto-memory policy relaxed**: CLAUDE.md now permits auto-memory for
   personal preferences (LEARNINGS.md remains primary for technical lessons)
5. **external\_evidence.type lint**: validator now warns on non-kebab-case type values
6. **`/next` enhanced**: suggests trimming body Session History when entries exceed 10
7. **subagent-dev TaskCreate clarified**: TaskCreate usage scoped to
   session-local subtask management only

## From v0.6.0 to v0.7.0

1. **STATUS.md schema expanded**: add `failure_tracking: null` and
   `task_size_rationale` fields to frontmatter
2. **Archive limits enforced**: `session_history` and `external_evidence` capped
   at 3 entries each; older entries archived to body or `docs/evidence-archive.md`
3. **Archive file**: create `docs/evidence-archive.md` for overflow evidence
4. **CLAUDE.md updated**: 3-failure rule now requires writing to
   `failure_tracking` (goal/count/last_attempt); reset to null on resolution
5. **Iteration reset**: `state-machine.md` updated — archive external_evidence
   older than latest 3 on iteration reset
6. **Skills updated**: brainstorming and bug-diagnosis skills now include
   `task_size_rationale` recording step

## From v0.5.0 to v0.6.0

1. **Skills moved**: `docs/skills/` → `.claude/skills/*/SKILL.md`
2. **Rules extracted**: State Machine and Routing moved from CLAUDE.md to `.claude/rules/`
3. **Commands added**: 5 slash commands in `.claude/commands/`
4. **Trust boundary hardened**: `check-gate.sh` blocks framework file edits;
   `post-status-audit.sh` detects gate tampering
5. **Hook library**: shared `hooks/lib/extract-input.sh` for input parsing
6. **Agent frontmatter enriched**: `model`, `permissionMode`, `effort`, `color` fields
7. **Agent language unified**: all agent files now in English
8. **CLAUDE.md slimmed**: 583 → 320 words

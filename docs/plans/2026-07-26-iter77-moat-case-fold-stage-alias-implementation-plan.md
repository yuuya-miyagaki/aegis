# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: SF-020（`check-destructive.sh` raw 経路の大文字 silent allow）と SF-021（`_STAGE_BROAD_RE` の `git stage` エイリアス欠落による silent allow）の封鎖。両 High・OPEN を TDD（旧赤→新緑）でクローズし、moat 非弱体化を機械的に確認する。

## 入力

- 参照要件: なし（framework 自己改善・正本は `docs/security-followups.md` SF-020/SF-021）
- 参照設計: `docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md`

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（Claude Code hooks・ローカル実行）
- Database: n/a
- CI/CD: n/a（M size routing で deploy skip）

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: n/a（web アプリ非該当）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

Project Overrides 未定義・既存慣行に従い main 直接・per-task commit（iter75/76 と同一）。

## ファイル構造（変更マップ）

- 変更: `hooks/check-destructive.sh` — raw 経路 grep 4 サイトの `-i` 化
  - :67-68 fallback（CMD 空）の `AEGIS_DESTRUCTIVE_CMD_REGEX` on `$INPUT` → `grep -iqE`
  - :71 fallback の rm 再帰 grep on `$INPUT` → `grep -iqE`
  - :128 rm 再帰 grep on `$CMD` → `grep -iqE`
  - :144-145 `AEGIS_DESTRUCTIVE_CMD_REGEX` ループ on `$CMD` → `grep -iqE`
  - 非変更（既 fold 済み）: :61-64 `RAW_LOWER`＋LOWER_REGEX／:79 `CMD_LOWER`＋:134-135 LOWER_REGEX
  - 非変更（意図的）: :88 `SAFE_TARGETS` sed（小文字 `^rm` のみ）— allow 例外を大文字へ**拡張しない**（allow 経路の拡張＝弱体化のため）。帰結: `RM -rf node_modules` → ask（保守的側・D-6 で pin）
- 変更: `hooks/check-secrets.sh` — :169 `_STAGE_BROAD_RE` の `add` → `(add|stage)`＋:290 付近の事実誤認コメント訂正（`git stage` は add の完全エイリアスで `-A/--all/.` の broad 綴りを持つ。`update-index` は broad 綴りなし＝除外は正しい＝`${GIT_STAGE_VERB}` 流用はしない）
- 非変更: `hooks/lib/patterns.sh`（regex SSOT 不変更。redirect システムパス :50 は呼び出し側 `-i` で自動封鎖）
- テスト: `tests/test_moat_case_fold_stage_alias.py`（新規）— 下記 D-*/S-* pin
- テスト: 既存 `tests/test_case_insensitive_fs.py`・`test_destructive_recursive.py`・`test_moat_quote_split.py`・`test_secrets_broad_dot_token.py`・`test_hook_locale_byte.py` — 全 green 維持（回帰）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `tests/test_moat_case_fold_stage_alias.py`（RED 実測記録） | なし |
| Task 2 | `check-destructive.sh` grep -i 化（D-* green） | Task 1 の RED pin |
| Task 3 | `check-secrets.sh` (add\|stage) 拡張（S-* green） | Task 1 の RED pin |
| Task 4 | full suite green＋moat 非弱体化 evidence | Task 2, 3 |

循環なし。Task 2/3 は別ファイル・依存なしだが、テスト実行の衝突回避のため直列実行（並列不要な規模）。

## タスク分解

### タスク 1: RED — 失敗 pin の新設と実測

**blockedBy:** なし | **モデル:** `opus`（dispatch）
**ファイル:** テスト `tests/test_moat_case_fold_stage_alias.py`（新規）
**意図:** 既存テストの慣行（hook を subprocess 起動し stdin JSON → 出力 JSON の decision を検証）に合わせ、以下の pin を書き、**旧実装での赤/緑を1件ずつ実測記録**する。
**pin 一覧:**

| ID | 入力 | 期待（新） | 旧実装 |
|----|------|-----------|--------|
| D-1 | `RM -rf /tmp/x` | ask | allow（赤） |
| D-2 | `RM -RF /tmp/x` | ask（コマンド名×flag の大文字合成） | allow（赤） |
| D-3 | `echo x > /ETC/passwd` | ask（小文字 `/etc` 形と同一判定。redirect パターンは patterns.sh:50＝raw `AEGIS_DESTRUCTIVE_CMD_REGEX` 配列内と 2026-07-26 実列挙で確認済み） | allow（赤） |
| D-4a | `GIT RESET --HARD` | ask（小文字リテラル regex `git\s+reset\s+--hard` の大文字 miss 代表） | allow（赤） |
| D-4b | `CHMOD -R 777 /tmp/x` | ask（regex 内大文字リテラル `R` が `-i` 下でも機能する検証を兼ねる） | allow（赤） |
| D-5 | `rm -rf node_modules` | allow（回帰・不変） | allow（緑） |
| D-6 | `RM -rf node_modules` | ask（safe-artifact 例外は大文字へ拡張しない設計判断の pin） | allow |
| D-7 | fallback 経路（CMD 抽出不能入力）＋大文字 `RM -rf` | ask（**条件付き**・下記） | RED 時に実測 |
| S-1 | `git stage -A`（実 .env 存在） | deny | allow（赤） |
| S-2 | `git stage .`（実 .env 存在） | deny | allow（赤） |
| S-3 | `git${IFS}stage -A`（実 .env 存在） | ask（NORM 経路） | allow（赤） |
| S-4 | `git stagearea xyz` | allow（誤マッチ回避） | allow（緑） |
| S-5 | `GIT STAGE -A`（実 .env 存在） | deny（SF-020×021 合成・CMD_LC 照合） | allow（赤） |
| S-6 | `git add -A`（実 .env 存在） | deny（回帰・不変） | deny（緑） |
| S-7 | `git stage .env`（実 .env 存在） | deny（回帰: targeted 系は `GIT_STAGE_VERB` :111 で既捕捉のはず＝「targeted=既存/broad=本修正」の境界 pin） | deny（緑・RED 時に要実証） |

**D-7 の条件:** iter73 修正後、invalid-byte による extraction drop は main 経路化済み（`tests/test_hook_locale_byte.py:105` コメント）＝旧誘発法は使えない。truncated/不整形 JSON（`command` フィールド非抽出形）で `CMD` 空を hook 直接呼び出しで実証できた場合のみ pin 化。誘発不能なら D-7 を**記録付きで削除**（fallback は defense-in-depth であり大文字対応は bonus。:67-71 の `-i` 化自体は D-7 なしでも実施）。
**停止条項（グリル 4 反映）:** 赤 pin が旧実装で**赤にならなかった場合は実装（Task 2/3）に入らず親へ報告**する。pin の前提（台帳実測 2026-07-20）が崩れた＝設計判断のやり直し。緑 pin（D-5/S-4/S-6/S-7）が旧実装で FAIL した場合も同様に停止。
**TDD:** テスト → FAIL 確認（赤 pin 全件の実測ログを記録） → コミット（RED コミット）
**RED evidence の置き場:** RED コミットメッセージに pin 別の赤/緑実測サマリを記載（iter76 慣行）。生出力は `docs/qa-reports/iter77-review.md` 作成時に review evidence として転記。
**受入条件:** 赤 pin が旧実装で全件 FAIL・緑 pin（D-5/S-4/S-6/S-7）が PASS、実測が記録されている
**Deliverable:** [ ] テストファイル存在 [ ] RED 実測記録

### タスク 2: SF-020 — check-destructive.sh raw 経路 grep -i 化

**blockedBy:** タスク 1 | **モデル:** `opus`（dispatch）
**ファイル:** 対象 `hooks/check-destructive.sh` / テスト `tests/test_moat_case_fold_stage_alias.py`
**意図:** 変更マップ記載の 4 サイトを `grep -qE` → `grep -iqE` に変更。SAFE_TARGETS sed・LOWER 系・NORM 経路は不変更。:158 コメントに raw 経路も `-i` 化した旨を追記（NORM 経路との対称性）。
**TDD:** D-1〜D-4/D-6/D-7 が green・D-5 が green 維持 → PASS 確認 → コミット
**受入条件:** D-* 全 green・`test_destructive_recursive.py`／`test_moat_quote_split.py`／`test_hook_locale_byte.py` green 維持
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 3: SF-021 — _STAGE_BROAD_RE (add|stage) 拡張

**blockedBy:** タスク 1 | **モデル:** `opus`（dispatch）
**ファイル:** 対象 `hooks/check-secrets.sh` / テスト `tests/test_moat_case_fold_stage_alias.py`
**意図:** :169 の `add` を `(add|stage)` に拡張（`${GIT_STAGE_VERB}` は `update-index` を含むため流用しない）。:290 付近の「Only `add` … has the broad-stage spellings」コメントを訂正。
**TDD:** S-1〜S-3/S-5 が green・S-4/S-6/S-7 が green 維持 → PASS 確認 → コミット
**受入条件:** S-* 全 green・`test_secrets_broad_dot_token.py`／`test_secrets_git_variants.py`／`test_case_insensitive_fs.py` green 維持・**broad deny のユーザー向け文言が動詞非依存であることを確認**（`git add` 直書き文面なら staging 系へ汎化。文言変更時は `test_destructive_warning_language.py` 系の文言 pin 有無を確認して同期）
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 4: 統合検証 — full suite・moat 非弱体化・contract

**blockedBy:** タスク 2, 3 | **モデル:** `opus`（dispatch・read-only 検証＋evidence 記録のみ）
**ファイル:** なし（検証のみ・新規 evidence 記録は可）
**意図:** full pytest green・deny 系 moat pin 非弱体化（**iter76 時点 174 本が green 維持＋本 iter 新規 N 本を加えた総数を記録**する形式）・`check_framework_contract.py`／`check_reference_drift.py`／`status_doctor.py` PASS を実測記録。
**TDD:** n/a（検証タスク）
**受入条件:** full suite green（passed/skipped 実数を記録）・moat 非弱体化（174 維持＋新規数明記）・contract/drift/doctor PASS・**`scripts/record-test-result.py` 経由（trusted runner）の記録が green**（グリル 2 反映: 素の pytest だけでは judge card の test-fact が undecidable になり qa/security ゲートで詰まる）
**Deliverable:** [ ] 検証ログが evidence として記録済み [ ] record green

## External Integrations

なし。

## 事前準備

- [x] ベースブランチ main・tree clean（rollover コミット c140fd1 済み）
- [x] pytest 実行環境（iter76 で full 1395 passed 実績）
- [ ] 実 .env fixture の作成方式は既存テスト（`test_secrets_git_variants.py` 等）の tmp repo 慣行に従う

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| SF-020（raw 大文字 destructive） | D-1,2,4a,4b（＋条件付き D-7）赤→緑 | Task 1,2 | `tests/test_moat_case_fold_stage_alias.py` |
| SF-020 範囲（redirect システムパス） | D-3 赤→緑 | Task 1,2 | 同上 |
| SF-020 安全側判断（safe-artifact 非拡張） | D-5 不変・D-6 pin | Task 1,2 | 同上 |
| SF-021（stage エイリアス broad） | S-1,2,3,5 赤→緑・S-4 誤マッチなし・S-7 境界 pin | Task 1,3 | 同上 |
| 非弱体化（moat 174・既存 pin） | 全既存テスト green | Task 4 | full suite |

## 自己レビュー

- 仕様カバレッジ: SF-020 残存分（コマンド名＋redirect パス＋fallback 経路）と SF-021（broad 綴り・raw/norm 二経路・合成形）を pin で網羅
- 曖昧さ検出: 「safe-artifact 大文字」の扱いを ask と確定（設計未解決 → 本計画で解消。理由: allow 例外の拡張は弱体化方向）
- 型の整合性: n/a（bash・JSON decision のみ）
- 境界整合性: Task 2/3 は Task 1 の pin を consume・Task 4 は両者の green を consume

## リスク

- リスク: raw grep `-i` 化の widening で正常形が過剰 ask になる（例: コミットメッセージ内の大文字 `RM -RF` 言及）。
- 対策: 同クラスの小文字形（メッセージ内 `rm -rf` 言及）は**現行でも ask**＝新カテゴリの誤検知ではなく既存クラスの case 拡張のみ。NORM 経路は iter75 から `-i` 運用済みで誤検知実績なし。正常形回帰は D-5/S-4/S-6＋full suite で pin。
- リスク: `-i` が `AEGIS_DESTRUCTIVE_CMD_REGEX` 内の大文字リテラル（`[dD]`・`W`・`R`）の意図（大小の区別）を消す。
- 対策: これらのリテラルは「両ケース捕捉」意図（`[rR]`/`[dD]`）か片側表記であり、`-i` は捕捉集合を広げる方向のみ＝deny/ask 側 moat では安全。既存 pin green 維持（Task 4）で機械確認。

## 完了条件

- [ ] 全テスト pass（full suite・passed/skipped 実数記録）
- [ ] moat 非弱体化（deny 系 174 pin green）
- [ ] contract/drift/doctor PASS
- [ ] レビュー完了（review gate は次フェーズ）
- [ ] SF-020/SF-021 台帳更新は ship/docs フェーズで実施（CLOSED-in-review 化）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

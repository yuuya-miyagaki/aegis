# v1.6.1 review エビデンス（2026-06-13）

## レビュー実施

第5回全力レビュー（`docs/full-review-2026-06-12.md`、軸 A〜F 並列 6 サブエージェント）の結果と grill-plan + grill-code 独立 2 本を経て、v1.6.1 にすべての Critical を反映済み。本ファイルは review-gate の根拠を集約する。

## レビュー履歴

### 1. 全力レビュー（5 軸 + 比較）

- charter: `docs/full-review-charter-2026-06-12.md`
- レポート: `docs/full-review-2026-06-12.md`
- 軸 A〜F 6 サブエージェント並列実行で **Critical 9 件 + Should fix 19 件** を抽出
- 結論: 「**修正後マージ → v1.7 で構造強化**」

### 2. plan 作成

- 計画書: `docs/plans/v1.6.1-fix-forward-plan.md`
- 対象: Critical 7 件（C-1〜C-6, C-9） + S-3 + S-11。C-7/C-8 は v1.7 へ
- 10 commit プラン（Task 0→6, 7→ 1/2/3/4/5/8→ release）

### 3. grill-plan

- 5 致命的（Task 1 ヒューリスティクス、Task 2 schema migration、Task 3 sentinel、Task 7 stash 受容、Phase 進行表）を抽出
- すべて plan 本体に反映済（5 章追加：Phase 進行表 / Schema Migration / Commit プラン / 受容済みリスク / Release Checklist）

### 4. 実装（TDD）

- ブランチ: `fix/v1.6.1-critical-bypasses`
- Plan の Commit プランどおりに 9 commit + grill-code 修正 3 commit + 本 release commit
- 既存 508 → 新規 98 テスト追加 = 606 全 PASS

### 5. grill-code 独立 2 本

#### grill-code A（攻撃面再走）

PoC 駆動で moat 突破を試行。Critical 4 件指摘：

- **A-Crit-1**: cmd_var_built_write WRITE_OP 不完全（ln/curl/wget/rsync/chmod/rm 等）→ 修正済（commit `2001a6a`）
- **A-Crit-2**: marker_verified が `pytest --version && echo OK` で forge 可能 → 修正済（commit `4a27b09`、3 段ゲート peephole）
- **A-Crit-3**: A-Crit-1 と A-Crit-2 の合成 → A-Crit-1 修正で連鎖封鎖
- **A-Crit-4**: `F=.env; git add $F` 変数構築バイパス → 修正済（commit `f0eb9ac`）

Should fix（A-S1〜A-S4）は受容済み（v161-security.md §受容済みリスクに記録）または修正済（A-S4: git commit GIT_PRE_OPTS 適用）

#### grill-code B（仕様乖離・保守性）

計画 AC tick で 9 Task すべて充足を確認。Critical 1 件指摘：

- **B-Critical**: A-Crit-2 と同一指摘（marker_verified 偽装）→ 修正済

Should fix（B-S1〜B-S6）は v161-security.md §受容済みリスクに記録 or B-S2（secrets-patterns.sh REQUIRED test pin）を修正済（commit `f0eb9ac`）

## 設計判断の評価（grill-code B より）

- **schema migration の fail-closed 設計**: v1.6.0 ログを silent green できない構造
- **bilateral check の対称性**: pre-approve と completion-time で同じ integrity check
- **patterns.sh の単一所有 + parity test**: marker regex も含めて bash/python 両 consumer から source
- **F6 教訓の継承**: 新規 lib（phase-skills, secrets-patterns）は REQUIRED 登録で覚醒
- **mirror byte-identity の徹底**: 12 commit すべてで本体↔example の diff ゼロ

## マージ判定

**マージ可**。Critical 9 件すべて修正済み、grill-code A/B の Critical 4 件も追加修正済み、回帰テスト 606 PASS、contract / drift / scaffold smoke 全 PASS。受容済み Should fix は v161-security.md に明示。

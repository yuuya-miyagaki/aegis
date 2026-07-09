# 納品サマリー — iteration 64（v1.25.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.25.0（iter64・MINOR＝fp 定義変更で record 再取得を要する運用意味変更）
- 日付: 2026-07-09
- 担当者: aegis dev フロー（security 1次は in-session・盲検2次は多エージェント）
- 操作マニュアル: 不要（保守者の操作手順に新規ステップなし。挙動変化＝下記「運用上の注意」に記載）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲

- **1. fingerprint tree-hash 化**（full-review 2026-07-06 **§2 R6 根1・§4 Phase 1「1-1」**＝罠 r,b,c,d の根切り）。
  `hooks/lib/fingerprint.sh`（E1 evidence moat の単一所有者）のハッシュ入力先頭 `head:<HEAD-sha>` 行を、
  「**非 docs/.claude の committed tree-hash**」`tree:<sha>`（`git ls-tree -r HEAD` の各行から docs/・.claude/
  パスを除外→sha256）に置換。
  - **効果**: docs-only／.claude-only コミットは非除外行が不変＝fp 不変＝green の record が無効化しない
    （罠 r 根絶）。コード変更コミットは blob sha が動く＝tree-hash が動く＝**silent-green 防止を完全保存**。
  - **除外はスラッシュ末尾＋char-class `[.]claude/`**（リテラルドット固定）。素の `.claude/` だと bash が
    バックスラッシュを剥がし bare-dot（正規表現 any-char）化し `aclaude/` 等を誤除外する silent-green 穴になる
    ため char-class で封鎖。ルート直下の `docs` という名の *ファイル* は非除外（スラッシュ要件）。
  - **token 契約不変**（64-hex|oversize|nogit|error・rc0）・**consumer 無改修**（build-judge-card.py /
    evidence.sh は 64-hex を不透明比較のみ＝`head:`/`tree:` 内部表現非依存）。
- **2. setup.sh OR marker 厳格化**（iter63 security 盲検2次 **LOW-1** の解消）。
  `selfheal_unlock_target` の身元判定を `.aegis-install-version` **OR** `hooks/lib/cp-lock.sh` から
  **install stamp 単独要求**へ。stamp（K-11・2026-06-13）は cp-lock（2026-06-21）より先行導入のため
  OS-lock され得る install は必ず stamp を持つ＝正規 self-heal を失わず、self-heal（`chmod a-w` 解除）の
  発火面を authoritative 1本に縮小。第2防御（`aegis_cp_verify` 実 lock 検出）・opt-out fail-closed は不変。
- **テスト**: 新規4本（`test_docs_only_commit_does_not_change_fp`／`test_committed_dir_resembling_dotclaude_is_not_excluded`／
  `test_root_file_named_docs_is_not_excluded`／`test_cplock_present_without_stamp_does_not_self_heal`）を
  RED-first で実証。full suite **1080 passed / 2 skipped**。

## 証拠

- 実装計画: docs/plans/2026-07-08-iter64-fingerprint-tree-hash-plan.md（grill-plan 致命1〔escaping over-exclusion〕反映・実 git 実証簿記）
- 設計: docs/specs/2026-07-08-iter64-fingerprint-tree-hash-design.md（＋brainstorm-record 併設・tree-hash と OR marker 安全性を実 git 実証）
- レビュー: docs/qa-reports/iter64-review.md（1次 in-session＋テスト強度〔23 passed 無回帰〕＋盲検2次 approve_with_notes・Critical/Major 0・mutant flip で歯を実証）
- QA: docs/qa-reports/iter64-qa.md（B1 drill=**skip**〔実装コミット済・diff 空／純コメントハンクは floor 除外の既知限界=§1-5〕＋代替実証: 4新規テスト RED-first＋4種一時変異 RED＋coverage 空白3件を実 git で安全確認・full 1080 recorded green）
- セキュリティ: docs/qa-reports/iter64-security.md（1次 in-session＋盲検2次 security〔動的実証: injection 6種・clean→clean pin・移行 fail-closed・OR marker 発火面縮小〕・**Findings HIGH/MEDIUM/LOW 0**・両者 approve 収束・docs/qa-reports/iter64-security-2nd.md）
- 動機の正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R6 根1・§4 Phase 1「1-1」／ iter63 LOW-1

## 既知のギャップ・運用上の注意

- **【重要・移行】既存 record は初回のみ unverified 化**: fp 定義変更（head:sha→tree-hash）で、
  `.claude/evidence-log.jsonl` の**既存 record は新 fp と不一致になり初回ロードで unverified（🟡）に降格**する。
  これは **fail-closed**（silent-green にならない）で安全。**該当タスクのテストを一度再実行すれば新 fp で
  record が上書きされ解消**する（marker_verified〔v1.6.1〕導入時と同型の安全な移行）。
- **committed 成分に oversize 上限なし**（盲検2次 divergence #1・🟢 residual）: working 成分は
  MAX_FILES/BYTES でガードされるが committed tree-hash は ls-tree 全行を処理。ただし内容 cat なし・
  行あたり定数長メタデータのみ（459 files で +25ms・hot-path 外）＝brick リスクなし・受容。
- **ゲート運用の罠（本 iter で遭遇）**: review ref を gate 承認**前**に置くと、pending gate は null ref という
  contract 不変条件に違反し `check_framework_contract` が一過性 red 化する。正しい順序は
  「record green → ref 設定 → 直後に承認（間に pytest を挟まない）」。full-review 1-3「approve --ref 原子化」で
  将来機械化予定。

## 配備と運用

- 環境: Claude Code ネイティブ。変更は `hooks/lib/fingerprint.sh`（moat コア）＋`bin/setup.sh`（installer）＝
  新規 script/hook なし・公開契約（token 契約 / scripts-manifest / hook 集合）変更なし。
- アクセス: 変更なし。
- 監視: なし。fp 移行に伴う一過性 unverified はテスト再実行で解消（上記）。

## 次の推奨アクション

- 実装 + docs + STATUS を 1 コミット（version bump 込み amend）→ **push 手前で停止しユーザー確認**
  （push = gh auth switch --user yuuya-miyagaki）。
- 以降: full-review §4 **Phase 1 の残り**: judge read_test_result **skip-and-continue**（1-2・R6 根2＝罠 e,m）／
  update-gate **approve --ref 原子化＋SIGPIPE**（1-3・本 iter で遭遇した罠）／S サイズ修復（1-4）／
  drill **NO_RUN 拒否＋コメントラン floor 除外**（1-5・本 iter で skip 経路を採らせた限界）／
  record 引数事前検証（1-6）。→ Phase 2 純化 → Phase 3 plugin/CI。

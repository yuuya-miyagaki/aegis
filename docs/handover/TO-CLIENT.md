# 納品サマリー — iteration 60（v1.21.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者
> （次に aegis を使う自分自身）。外部クライアントへの製品納品ではない。

## 納品サマリー

- リリース / ビルド: **v1.20.0 → v1.21.0（MINOR）**
- 日付: 2026-07-06
- 担当者: Dev（Aegis 自己改修イテレーション）
- 操作マニュアル: **生成せず** — フレームワーク（利用者＝保守者自身）。
- 運用 RUNBOOK: **生成せず** — 運用者なし（CI 相当は contract/drift/context-budget の機械検査）。
- UAT 結果: **生成せず** — `docs/requirements/ACCEPTANCE.md` なし。

## 実装範囲

- **完了**: budget ratchet policy 見直し＝**語数予算の計数から drift 支配の圧縮不能構造を除外**。
  - `scripts/context_budget.py`: `<!-- aegis:budget-exclude-start/end -->` マーカー領域を計数前 strip する
    `_strip_excluded`／`_budget_word_count` を追加し、`check`/`tighten`/`seed` の**3経路を統一**（乖離不能）。
  - `.claude/rules/routing.md`: agent roster（`check_reference_drift #1` が agents/ と mirror＝drift-pin＝圧縮不能）を
    マーカーで囲み、budget を **90→70**（prose のみを計数）。以後 agent 追加（roster 成長）は budget を食わず drift が支配、
    prose 追加だけが ratchet 対象＝**計数が本来の anti-bloat を意味あるものに**。
  - **濫用ガード（3重）**: (1) 行単位 ==roster（除外領域の各行が backtick agent 名 or scaffold＝自由 prose 行を検知）／
    (2) `len==1`（多領域で prose を包む濫用を検知）／(3) allowlist トリップワイヤ（除外マーカーは routing.md のみ・
    新 excluder は機械 FAIL）。
  - `CLAUDE.md`「Context Budget Policy」節に terse policy（1行）＋fail-graceful（unmatched は全計数＝bloat を隠さない）。

## 主要な設計判断

- **方向＝「計数の意味を正す」**（headroom 再導入でなく）: budget は bloat しうる自由 prose のみを測り、別 invariant（drift）が
  支配する構造は除外＝tighten-only ラチェットの anti-bloat 趣旨を保持。iter59 の headroom-0 問題の**根本原因**（roster が
  floor を人為的に押し上げる）を源から解消。
- **濫用ガードを drift invariant に接地**: 「除外してよいのは別 invariant で pin 済の内容だけ」を policy 化し、
  routing.md では除外領域 ⊇ `.claude/agents/*.md` 全 stem をテスト固定（roster 成長に自動追従）。
- **残余 floor（state-machine/bug-diagnosis）は機構追加せず**: 除外対象の構造を持たない密な必須 prose＝floor-0 は正しい
  anti-bloat signal＝co-bump（iter59 規則）で足りる（CLAUDE.md policy に明記）。

## 変更ファイル

- `scripts/context_budget.py`（除外ロジック・3経路統一）
- `.claude/rules/routing.md`（roster をマーカー囲み＝68→prose 70 計数）
- `scripts/context-budgets.json`（routing.md 90→70）
- `tests/test_context_budget.py`（除外2＋濫用ガード2＝行単位==roster・allowlist）
- `CLAUDE.md`（Context Budget Policy terse 追記）
- version bump: `scripts/check_framework_contract.py`・`templates/STATUS.template.md`・`docs/STATUS.md`
- コミット: 実装 `acc2ad4`・grill-code fix-forward `c971894`・review fix-forward `f8974f1`

## 証拠

- 仕様: `docs/specs/2026-07-06-iter60-budget-exclusion-design.md`（＋`-brainstorm-record.md`）
- 計画: `docs/plans/2026-07-06-iter60-budget-exclusion-plan.md`（grill-plan 致命ゼロ・要検討3点反映）
- レビュー: `docs/qa-reports/iter60-review.md`（1次 approve・盲検2次 approve_with_notes・note1/2 fix-forward 解消）
- QA: `docs/qa-reports/iter60-qa.md`（B1 SKIP＋実 mutation demo M1/M2・full 1056 passed）
- セキュリティ: `docs/qa-reports/iter60-security.md`（1次 approve・盲検2次 approve_with_notes・Minor2件 residual・moat 不変・secrets 0）

## 既知のギャップ（residual）

- **行ガードは「行形」強制で「語完全一致」でない**（security 盲検2次 Minor-1）: `Subagents:` 行の延伸や backtick 名を持つ行への
  自由 prose 混入で語を密輸する余地が残る。**評価＝許容**（budget は anti-bloat の衛生ラチェットでセキュリティ境界でない・
  routing.md 編集は trusted commit＋review＋drift を通る）。将来 word-exact 強化 or コメント精確化は別 slice（post-qa のコード
  再編集は review/qa を無効化するため見送り）。
- **`_EXCLUDE_RE` は unmatched start に O(k²)**（Minor-2）: repo 内入力限定＝ReDoS 非該当・対応不要。
- **CLAUDE.md は kernel budget 650 制約**（実装時判明・当初「対象外」は誤り）: policy は terse 1行（641/650）に収めた。

## 配備と運用

- 環境: フレームワーク本体（`aegis/`）。install 先は `bin/setup.sh` 経由。
- アクセス: GitHub `yuuya-miyagaki/aegis`（push は `gh auth switch --user yuuya-miyagaki` 後）。
- 影響: 計数ロジック＋rule/guidance の後方互換な変更（除外は opt-in・マーカー無しファイルは従来どおり全計数）。
  **公開/運用契約は不変**（SemVer MINOR）。既存 install への破壊的変更なし。moat/enforcement 不変。
- 監視: `check_framework_contract` / `check_reference_drift` / `context_budget` の機械検査で回帰検出。

## 運用インシデント（本 iter 中に発生・復旧済）

- **盲検2次 security サブエージェントが検証中に `git checkout docs/STATUS.md docs/qa-reports/*` を実行**し、未コミットの
  gate 承認簿記（STATUS の review/qa approved・phase）＋test-strength.drill を revert した。`.claude/.gate-snapshot` は
  `docs/` 外ゆえ revert されず earned 状態を保持していたため、**STATUS を snapshot に一致させて復旧**（実装コミット f8974f1 は無傷）。
  → 教訓＝**サブエージェントに `git checkout`/`git reset` 等の tree 変更コマンドを許さない**（read-only 検証に限定する委譲文言へ）。LEARNINGS 予約。

## 次の推奨アクション

- 次: push（`gh auth switch --user yuuya-miyagaki` 後）＝**ユーザー確認待ちで停止中**。
- **その後の予定＝v1.21.0 で aegis 全体レビュー**（6 dimension: moat/gate-flow/context-budget/skill-guidance/distribution/test-strength・多エージェント fan-out）。

## 承認

- 作成者: Dev（Aegis iter60）
- 日付: 2026-07-06

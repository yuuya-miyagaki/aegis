# iter59 レビューレポート（review ゲート）

- 対象: 実装 commit `b2c2851`＋review fix-forward `89fb52f`（iter59・サブエージェント継続 SendMessage の SoT 定義）
- 仕様正本: `docs/specs/2026-07-06-iter59-subagent-continuation-sot-design.md`
- 実装計画: `docs/plans/2026-07-06-iter59-subagent-continuation-sot-plan.md`
- 一次情報: iter58 review 盲検2次 note1（`SendMessage` が qa.md/qa-verification にのみ出現・機構定義が正本ファイルに無い＝dangling）
- 1次レビュー方式: セッション内フルコンテキスト実読＋grill-code（実装後に完走・Critical/Major 0）＋決定論検査（token pin RED→GREEN／full suite／contract／drift／budget）。盲検2次は fresh context の general-purpose エージェントで独立実施（1次結論非開示・diff/spec/plan のみ）。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | 継続定義の token pin 追加（RED-first・単一コミット方針で未コミット→Task2 と一括） | `tests/test_skill_guidance_tokens.py`（`ROUTING` 読込＋`TestSubagentContinuationSoT`） | ✅ 完了 | 短核 `SendMessage`＋`harness-enforced` の2 assertion。RED（2 failed）を実装前に実証済 |
| 2 | routing.md 継続節追加＋principle 1文化＋budget 75→90 | `.claude/rules/routing.md`＋`scripts/context-budgets.json` | ✅ 完了 | 「## Subagent continuation」節＝設計 §確定文言A とバイト一致（実測 90 words）。budget 90（境界 PASS） |

未着手タスクなし。仕様 §コンポーネント分解の3ファイルすべて実装済。

## Findings（1次・実測検証済みのみ）

### Critical — 該当なし
### Major — 該当なし

### Minor / Nice-to-have（grill-code 由来・任意・据置）

- **`.claude/rules/routing.md:5`（confidence 8）** — Principle 圧縮の意味微差：旧 "When in doubt"（不確実性のタイブレーカ）→ 新 "else"（論理的補集合）。「明確に clearer/safer/smaller でない」は doubt を含むため `else` は旧文を包摂＝意味欠落なし・むしろ論理的にタイト。据置。
- **`.claude/rules/routing.md:20`（confidence 7）** — pin トークン `harness-enforced`（ハイフン複合語）は "not enforced by the harness" 等へ言い換えると false RED。ただし**意図した決定論トリップワイヤ**（load-bearing 文言の書換えはテスト同時更新を強制）＝grill-plan 要検討3 で受容済。本文が pin 複合語と厳密一致していることを確認。
- **`scripts/context-budgets.json:21`（confidence 8・監視項目）** — headroom-0（content 90 / budget 90）。grill-plan 要検討1 で受容＋co-bump ルールを plan/LEARNINGS に予約済＝**設計選択でありコードバグではない**。残リスク＝後続ゲートの fix-forward が routing.md に加筆した場合の context_budget FAIL（→ 同一 diff で budget 共 bump で自己修復）。security へ引き継ぐ。
- **`.claude/rules/routing.md:20`（confidence 8）** — 新節が参照する `maxTurns`（Claude Code agent frontmatter のプラットフォーム primitive）・`the 3-failure rule`（CLAUDE.md Operating Contract に定義済）はいずれも実在参照＝**新規 dangling を持ち込んでいない**（本 iter の目的が dangling 解消ゆえ自己整合を確認）。

## Evidence Checklist

- [x] diff を実読した（`git show b2c2851`・chat summary ではなく実 diff）
- [x] plan/spec の受入条件と突合（§確定文言A とバイト一致・スコープ境界遵守）
- [x] 未カバーのエッジケース列挙（token 一意性・drift 誤抽出・principle 意味差＝上記 Findings）
- [x] 全 finding に severity と confidence（1-10）付与

### 決定論検査の実測

| 検査 | コマンド | 結果 |
|------|---------|------|
| token pin RED→GREEN | `pytest ...::TestSubagentContinuationSoT` | RED=2 failed（実装前）→ GREEN=2 passed（実装後） |
| 予算 | `python3 scripts/context_budget.py` | exit 0（90≤90 境界 PASS） |
| 参照ドリフト（roster） | `python3 scripts/check_reference_drift.py` | exit 0（`maxTurns` 大文字T・`SendMessage` 非バッククォートで agent 誤抽出なし） |
| フレームワーク契約 | `python3 scripts/check_framework_contract.py` | exit 0（budget 更新反映・aligned） |
| フルスイート | `python3 -m pytest -q` | 1052 passed, 2 skipped, 0 failed（iter58 baseline 1050 +2） |

## PASS/FAIL 判定

**PASS（1次）。** Critical/Major 0・仕様 §確定文言A とバイト一致・全 harness チェック緑・新規 dangling なし。Minor は全て記録済の設計選択（headroom-0）か意図した挙動（pin tripwire）で据置妥当。

## 盲検 第2意見（self-attested）

fresh context の general-purpose エージェントに diff（commit b2c2851）＋spec＋plan のみを渡し、1次結論を非開示で独立2次レビューを1回ディスパッチ。5論点（dangling 解消の妥当性／予算 bump の健全性／token pin 設計／回帰リスク／仕様乖離）について独立判定を求めた。実走検証済（word count=90／token count 各1／context_budget exit0／drift PASS／contract PASS／pytest 11 passed／full 1052 passed）。

**2次 verdict = approve_with_notes。** 論点1-5 すべて「妥当／健全／適切／回帰なし／乖離なし」。1点の divergence（非ブロッカー）＝**presence-pin の意味反転 false-PASS**を提起：`harness-enforced` 単トークン pin は "not" 脱落による反転（`Guidance, not harness-enforced` → `Guidance, harness-enforced`）を検知できない。plan 要検討3 は「言い換えによる false-RED」を扱うが「反転による false-PASS」は未カバー。

### divergence への対応（fix-forward・commit 89fb52f）

**採用して fix-forward 済。** pin を `"harness-enforced"` → `"not harness-enforced"`（否定語 "not" を含む句）へ強化。この節で最も load-bearing な "not" を含めることで、節削除**と** "not" 反転の両方を捕捉。実測で確認済：

| 入力 | 旧 pin `"harness-enforced"` | 新 pin `"not harness-enforced"` |
|------|------|------|
| 実 routing.md | True（pass） | True（pass） |
| 反転版 `Guidance, harness-enforced` | **True（false-PASS＝反転を見逃す）** | **False（RED＝反転を捕捉）** |

false-RED プロファイルは不変（"harness-enforced"→"enforced by harness" 等の言い換えは旧 pin でも同様に RED＝リスク増なし）。routing.md は無変更＝budget/word-count 不変。強化後 pin GREEN・contract exit0・full suite 緑を再確認。

```claims
verdict: approve
tests_green: true
no_stubs: true
second_opinion:
  verdict: approve_with_notes
  notes: 論点1-5 すべて妥当（dangling 解消・予算 bump 健全・pin 適切・回帰なし・仕様乖離なし）を実走検証で確認。1件の divergence（presence-pin の意味反転 false-PASS）は非ブロッカーだが安価かつ strictly-better のため fix-forward 採用（commit 89fb52f・pin を 'not harness-enforced' 句へ強化＝反転を RED で捕捉・実測確認済）。headroom-0 は 2次も「ラチェット自然状態・tighten-only と整合・過剰でない」と評価＝監視項目のまま security へ引継ぎ。
  divergence_points: ["tests/test_skill_guidance_tokens.py:120 — harness-enforced 単トークン pin は 'not' 脱落の意味反転を見逃す false-PASS（→ fix-forward 89fb52f で 'not harness-enforced' 句へ強化し解消）"]
```

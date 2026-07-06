# BRAINSTORM-RECORD — iter60 budget ratchet policy 見直し（drift 支配構造の計数除外）
<!-- 正本: brainstorming skill -->

## 入力

- iter59 の headroom-0 問題（routing.md content 90/budget 90）＋ LEARNINGS line18/122 の緊張（raise vs 圧縮）。
- 全体レビュー前の「決定済だが未完」領域を1つ片付ける方針（ユーザー選択・その後 v1.20.0 で全体レビュー）。

## 実測（設計の起点）

- budget floor 一覧（headroom = budget − 実語数）: routing.md=0・state-machine.md=0・bug-diagnosis=2（floor）／
  qa-verification=6・client-workflow=7（tight）／残り15は 13-37（余裕）。
  → floor は**局所的**（最頻編集の数ファイルが tighten で 0 に張り付いた）。
- routing.md 90語の内訳: agent roster = **20語**（drift-pin＝圧縮不能）／自由 prose = **70語**。

## 合意した設計（ユーザー承認 2026-07-06）

- **方向1「計数の意味を正す」**: budget は bloat しうる自由 prose のみを測り、drift 等**別 invariant が支配する
  圧縮不能構造（roster）を計数から除外**する。
- **除外機構 = in-file マーカー**（`<!-- aegis:budget-exclude-start/end -->`）を `context_budget.py` の計数前 strip で処理。
- **濫用ガード（必須）**: 「除外してよいのは別 invariant で pin 済の内容だけ」を policy 化し、routing.md では
  「除外領域 == check_reference_drift が支配する roster」をテストで固定（任意 prose を包んで budget 回避＝不可）。
- **残余 floor**（state-machine/bug-diagnosis）: 除外対象を持たない密な必須 prose ＝ floor-0 は正しい signal。
  co-bump（iter59 規則）を CLAUDE.md policy に明記するのみ（機構追加なし）。
- routing.md budget 90→70（prose のみ）。SemVer v1.20.0→v1.21.0（MINOR・opt-in 追加）。規模 M（5ファイル）。

## 却下・descope した案

- **方向2（既存ルールの明文化のみ）**: iter59 判断規則＋co-bump を first-class 化するが計数は現状維持＝
  「構造が floor を人為的に押し上げる」根本は残る。→ 却下（ユーザーは根本原因を選択）。ただし policy 明文化の要素は方向1 に内包。
- **方向3（headroom 再導入）**: floor に content×1.1 等のマージン再シード。tighten-only の anti-bloat 趣旨を弱める。→ 却下。
- **除外機構の代替**: (b) drift backtick 名だけ自動除外＝roster 周辺の構造語（"Subagents:" 等）が残り部分的・
  context_budget↔drift の結合増／(c) budgets.json に per-file 除外 regex＝config-content drift（行ズレ）。→ マーカーが最も汎用・
  自己文書化・低結合ゆえ採用。
- **濫用ガードの一般化**（任意ファイルの除外領域が別 invariant pin 済かを汎用検査）: YAGNI で先送り。現状 routing.md が
  唯一の除外利用＝特化テストで十分。policy doc は一般形で記述。

## 未解決事項（plan / grill-plan で詰める）

- `_strip_excluded` の正規表現（複数マーカー対・unmatched/nested の fail-graceful 挙動の具体）。
- routing.md の除外境界（roster の「Each agent's own file defines its domain.」まで含めるか＝実測 70語との整合）。
- prose budget の正確値（除外後 70 ちょうどか・tighten 流儀）。
- B1 drill の mutant 選定（context_budget.py の strip 境界・fail-graceful 分岐）。
- CLAUDE.md policy 文言（budget=自由prose／除外=別invariant pin済のみ／floor co-bump）。

## スコープ境界

- 対象 = context_budget.py の除外ロジック＋routing.md マーカー＋budget 付替＋濫用ガードテスト＋CLAUDE.md policy。
- 非対象 = tighten-only ラチェット本体（不変）・drift 機構（不変）・roster 内容/agents（不変）・
  他 floor ファイル（state-machine/bug-diagnosis）の機構変更（co-bump 文書化のみ）・headroom 再導入（却下）。

# iter67 review レポート — judge test-fact 判定堅牢化（trust-scan）

- **対象**: `d2c4dd6..HEAD`（実装 `7c0829d`〜`6a4c0ef`＋fix-forward `70ace79`/`0739a79`）
- **task_type/size**: framework / M（control-plane＝gate 判定ロジックにつき review+qa+security 必須・deploy skip）
- **仕様正本**: `docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md`
- **計画**: `docs/plans/2026-07-12-iter67-judge-test-fact-robustness-implementation-plan.md`
- **動機正本**: retro 合意 改善#1（LEARNINGS conf9 line137＝iter64/65/66 で3回顕在化した unverified 降格罠）
- **判定**: **PASS**（1次4角度＋親 verify＋盲検2次が approve 系に収束・Minor は fix-forward 2コミットで解消/起票済み）

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | コミット | 状態 |
|---|------------|------------|---------|------|
| 1 | 系列テスト10件（TDD RED） | tests/test_test_runner_realness.py（TestReadTestResultTrustScan） | 7c0829d | 済（RED 実測 6 failed/27 passed＝計画分布と厳密一致） |
| 2 | trust-scan 実装＋docstring 同期＋既存ピンコメント限定子 | scripts/build-judge-card.py・tests/test_judge_card.py | 2f5eaaa | 済（GREEN 33 passed・full 1148 passed/2 skipped） |
| 3 | guidance 1文同期 | docs/architecture-overview.md | 6a4c0ef | 済（budget green） |
| FF-1次 | 3段系列ピン追加（角度C Minor）＋docstring に iter64-66/LEARNINGS 導線（角度D D-1） | tests/test_test_runner_realness.py・scripts/build-judge-card.py | 70ace79 | 済（99 passed） |
| FF-2次 | docstring Decidable 定義の実挙動化（盲検 F1）＋guidance に und-fail 終端補記（盲検 F3） | scripts/build-judge-card.py・docs/architecture-overview.md | 0739a79 | 済（99 passed・budget green） |

全タスク実装済み・未着手ゼロ・スコープ超過なし（候補#2/#3 の混入なし・grill-code でも確認済み）。

## 1次レビュー（4角度・finder=opus/sonnet-pin・親 verify=fable）

### 角度A: 仕様準拠・判定ロジック — **approve**（findings 0）
設計判定マトリクス全7行×実装分岐を独立ハーネスで base/head 両実測。head 10/10 が設計期待値・base 6/10 DIFF＝計画「現行」列と完全一致。docstring 3箇所（冒頭/C-2/v1.6.0 注記）と実装の意味一致・`C-2 (v1.6.1)` タグ不変・transparency-precedes-fp をコード順とケース10で確認。残差 R1（exit-0 洗浄・設計受容済）/R2（full suite は qa で締め）。

### 角度B: 敵対的 gate-bypass — **approve**（FB-1 は pre-existing 実証・Low）
実 writer（append_evidence）実発火＋合成系列 26 種を実走。**silent-green 新経路ゼロ**（透明化悪用 A1-A6b・fp backstop B1-B7・red 可視性 C1-C7 全 pass）。red はむしろ厳格化（旧: decidable red + noise → unverified に洗浄可／新: red 維持を実測）。C-2/K-1 は evidence.sh/patterns.sh/fingerprint.sh 完全不変更で無緩和。
- **FB-1（Low・pre-existing 実証済み）**: `pytest -q; true`（exit 洗浄）＋failed summary は marker regex（`N passed|failed` 一致）＋status=exit-code 由来で **washed decidable-green** になる — baseline d2c4dd6 で同一挙動（OLD=NEW=green）＝**本 diff の回帰でない**。本 diff の影響は到達性のみ（W2: washed-green 上の noise が旧は 🟡 に隠し新は表面化）＝green の新規製造なし。→ **SF-012 として security フェーズで起票**（marker/status 整合 hardening・iter68 候補）。
- unknown-src decidable-by-default も pre-existing（実 writer は observed/manual のみ発行・任意 log 書込みは脅威モデル外）→ SF-012 に同梱で allowlist 化を follow-up。

### 角度C: テスト強度 — **approve_with_notes** → note は fix-forward 済
trust-scan 分岐の全構成要素（src/marker/status 判定・continue 位置・fp 検査位置・und-fail 終端・green/red・noise-only・rotated 境界）に kill テスト対応を机上トレース＋実測で確認。カバレッジ空白なし。Minor（3段系列 green←und-fail←und-ok の未ピン・conf6）→ 親 verify が HEAD で unverified を実測後、`test_transparency_does_not_skip_undecidable_fail` を追加（70ace79）。

### 角度D: 保守性・ドキュメント整合 — **approve_with_notes** → D-1 は fix-forward 済
decidable/undecidable/透明の用語が design/実装/テスト/guidance の5箇所で完全一致・旧意味論の残骸ゼロ（plan 内の対比引用と 6/20 スナップショットは非該当）。D-1（docstring に LEARNINGS 導線なし・conf6）→ 70ace79 で補記。D-2（ハーネス重複・conf7）/D-3（`_write_entry` vs `_write_entries` 命名近接・conf5）は実害なしの将来 note＝据置（本 iter で統合しない判断は plan 時に合意済み）。

### 親 verify（fable）
- grill-code 時に変異2種（status 限定除去→#4 単独 kill／fp 順序退行→#10 単独 kill）を scratch clone で実証。
- 3段系列の期待値（unverified）を HEAD 実測してから角度C の追加テストを確定。
- 盲検 F1 の docstring 乖離を確認し実挙動記述へ是正（0739a79・挙動変更なし＝テスト99 passed 不変）。

## Evidence Checklist
- [x] diff を Read/Grep で実読（chat summary ではなく実ファイル・実 writer 発火・base/head 差分実走）
- [x] plan/spec の受入条件と突合（対照表・RED/GREEN 分布・既存系列ピン生存）
- [x] エッジケース列挙（stale noise/3段系列/rotated 跨ぎ/noise-only/v1.6.0 キー欠如/truthy-not-True/unknown-src/exit 洗浄）
- [x] 全 finding に severity と confidence 付与

## テスト実測
- 対象2ファイル（realness＋judge_card）: **99 passed**（fix-forward 後）
- full suite: 実装時点 **1148 passed / 2 skipped / 0 failed**（2f5eaaa・角度B/2次も独立再実測）・fix-forward 後の full 締めは record-test-result で本承認直前に実施
- 既知 flaky `test_update_gate_lock` は全 run で顕在化せず（本 diff 不接触＝回帰外）

## 盲検 第2意見（self-attested）

盲検2次（fable・fresh context・1次結論未参照・検査12項目全消化）は **approve_with_notes**。RED 分布を旧コード実走で独立再現（6 fail/5 pass）・設計整合 7/7・新規 silent-green なし・full suite 緑を独立実測。F1（docstring 定義乖離）/F3（guidance 省略）は fix-forward 0739a79 で解消、F2 は設計受容済み残余の明示（divergence でなく同意）、F4（cmd 非文字列で例外→build() が 🟡 fail-closed・pre-existing・diff 範囲外）は情報提供。1次との結論割れなし。

```claims
tests_pass: true
no_stubs: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: []
  evidence: "盲検12項目・M1-M10 実走・旧コードで RED 分布再現（6f/5p）・fp=byte同一tree の attestation 確認・rotation 連続 suffix 構造で red 先行消失なし・full 1132 passed（flaky lock 除外実行）・F1/F3 は fix-forward 済・F2=設計受容の明示・F4=pre-existing info。新規 silent-green 経路なし・red 可視性は厳格化。"
```

## 結論
**review PASS**。trust-scan は「証明能力ゼロのエントリから終端拒否権を剥奪する」1分岐に閉じ、C-2/K-1/fp backstop 無緩和・red 洗浄経路の封鎖（厳格化）を4角度＋盲検で実証。pre-existing 2件（washed-green・unknown-src）は SF-012 起票へ。qa フェーズへ。

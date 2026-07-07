# QA レポート — iteration 62（委譲拘束 SoT 標準化・R1 文言層）

- date: 2026-07-07
- task: framework / L / v1.23.0 予定
- plan: docs/plans/2026-07-07-iter62-delegation-constraints-sot-plan.md

## 機能対照表

| # | 要件/plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|
| 1 | routing.md 単一正本（6拘束・見出し一意） | .claude/rules/routing.md:23-38 | pin テスト（count==1）＋確定文言 A 逐語 grep | PASS |
| 2 | 6点目 read-only（2否定・コマンド列挙・汚染時プロトコル・無条件宣言） | routing.md:34-38 | pin 5本（否定句×2・連結token・protocol・unconditional） | PASS |
| 3 | qa-verification 6点目追加 | qa-verification/SKILL.md:65 | pin（参照名＋tree 変更禁止）＋逐語 grep | PASS |
| 4 | review/security 盲検2次への拘束参照 | review-gate:81・security-gate:72 | pin（両ファイル・subTest） | PASS |
| 5 | subagent-dev コアルール5点目 | subagent-dev/SKILL.md:25 | pin（参照名＋核） | PASS |
| 6 | token-pin drift 封鎖（RED-first） | tests/test_skill_guidance_tokens.py:140-210 | 計画7本 RED 実証→GREEN。fix-forward 2本（SendMessage count==1・第2否定）は一時変異で RED 実証 | PASS |
| 7 | budget 簿記（追加分ちょうど raise） | scripts/context-budgets.json:13,21 | 実測一致（181/459）＋`context_budget.py` rc=0 | PASS |
| 8 | 既存 pin・既存挙動の無退行 | full suite | 1071 passed / 2 skipped（既存 skip は環境条件つき by-design） | PASS |

実装漏れなし（「検証対象なし」の行はゼロ）。

## エビデンス収集チェックリスト

- [x] テストスイート実行・記録: `record-test-result.py "python3 -m pytest -q"` → **recorded: green**（1071 passed / 2 skipped・全編集後・drill 後に実行＝manual entry が newest）
- [x] lint/type-check/build: 該当なし（md/json/テストのみ）。契約検査 `check_framework_contract.py` PASS・`check_status.py` PASS で代替
- [x] plan の受入条件と突合: 上記対照表＋plan「QA チェックリスト」全項目消化（下記）
- [x] 各検証項目に PASS/FAIL 付与済み
- [x] FAIL 項目: なし

## plan QA チェックリスト消化

- [x] pin 7テストが md 未編集状態で RED だった証跡（implement Task 1: `7 failed, 11 passed`）
- [x] 全 pin GREEN＋既存 pin 退行なし（19 passed → full 1071 passed）
- [x] budget: routing=181・qa-verification=459 実測一致・check rc=0
- [x] 確定文言 A-D の逐語存在（盲検2次が byte 一致を独立確認）
- [x] 既存 SendMessage pin の一意性維持（routing.md 内 1 回＝count==1 ガードで機械化）
- [x] contract PASS・STATUS 整合
- [x] plan 外追加: fix-forward テスト2本（review 1次 verify／盲検2次 Minor-1 由来。review レポートで追認済み）

## テスト強度ドリル（B1・実 mutant）

**DRILL PASS — 11/11 mutants caught**（skip なしの実 drill。iter59/60 の同クラス diff は skip＋手動実証だったが、grill-code 🟡 の指摘どおり全ハンク実 mutant が成立）。

わかったことを平易に:

- ✅ わざと「MUST NOT run」を「may run」に書き換えたら（＝git コマンド実行を許可する改悪）、テストが赤くなった＝**iter60 事故の許可文への変異は機械検知される**
- ✅ 4つの消費側ファイルの「tree 変更禁止」を1つずつ改悪（変更可/許可/自由）・参照名を1字削り → すべて赤化＝**どの経路の核が消えても検知される**
- ✅ budget を実態より小さく偽装（459→100・181→100）→ 実リポジトリ検査テストが赤化＝**簿記の改竄も検知される**
- ✅ テスト自身の読込先・assert 向き・count 期待値を改悪 → すべて赤化＝**ガード自体の破壊も検知される**
- mutant は全11変更ハンク（docs/ 除外後）に1個ずつ＝coverage floor 充足

```claims
verdict: approve
tests:
  full_suite: "1071 passed / 2 skipped (recorded green, manual newest)"
  drill: "B1 DRILL PASS 11/11 caught (real mutants, no skip)"
  budget_check: "rc=0 (routing 181/181, qa-verification 459/459)"
  contract: "PASS"
```

## ブロッカー

なし。

## 禁止事項の遵守

- エビデンスなき PASS なし（全行に実測根拠）／テスト実行省略なし（record 実走）／FAIL 隠蔽なし（FAIL ゼロ）／検証範囲の縮小なし（plan チェックリスト全消化＋plan 外2本を追認記録）

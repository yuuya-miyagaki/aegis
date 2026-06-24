# iter44 QA Report — C5 ROOT-external plan-gate false-positive

- 日付: 2026-06-25
- task_type/size: framework / M（qa 必須）
- qa 証拠（gate ref）: `docs/qa-reports/test-strength.md`（B1 ドリル結果）／本ファイルは可読 QA ドキュメント

## 機能対照表（要件 → 検証）

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | Dev・ROOT 外絶対 → allow | `tests/...::test_a` | pytest（RED-first 実測済） | PASS |
| 2 | Dev・ROOT 内 → deny（ROOT/ROOT_REAL 両形） | `::test_b` | pytest | PASS |
| 3 | control file → deny | `::test_c` | pytest | PASS |
| 4 | docs → allow | `::test_d` | pytest | PASS |
| 5 | Client・ROOT 外 → allow | `::test_e` | pytest | PASS |
| 6 | Client・ROOT 内 → deny | `::test_f` | pytest | PASS |
| 7 | 相対 → gate 維持 | `::test_g` | pytest | PASS |
| 8 | templates → deny | `::test_h` | pytest | PASS |
| 9 | plan 承認時に内部 allow（positive control） | `::test_i` | pytest | PASS |
| 10 | sibling prefix → external/allow | `::test_j` | pytest | PASS |

実装漏れなし（全機能に検証対象が存在）。

## エビデンス

- テストスイート: full suite green（`record-test-result.py` で記録・fingerprint bound）。新規 C5 test: **10 passed**（`pytest tests/test_check_gate_root_external.py`）。
- `bash -n hooks/check-gate.sh` → OK。
- lint/type-check/build: 該当なし（bash hook + python test）。

## テスト強度ドリル（B1・mutation）

`docs/qa-reports/test-strength.drill` に 2 mutant を定義し実走（`run-test-strength-drill.py`）:

| # | 変異対象（追加行） | 変異 | 壊す振る舞い | 捕捉テスト |
|---|------------------|------|------------|-----------|
| 1 | `hooks/check-gate.sh:156` 第1アーム pattern | `"$ROOT"/*` → `"$ROOT"/nomatch/*` | ROOT 内 gate 維持 | test_b / test_f が RED |
| 2 | `hooks/check-gate.sh:158` `emit_allow` | → `emit_deny mutant` | ROOT 外 allow | test_a / test_e / test_j が RED |

結果: **DRILL PASS — all mutants caught**（プレビュー実走で確認・承認時にハーネスが再実走）。
iter43 の skip-drill（framework 混在 diff で coverage floor 不成立）と異なり、本 iter は
未コミットの追加実行行が明確で、テストが hook を copy 実走するため**本物の mutation drill が成立**。

## 判定

**PASS。** 全 10 検証 PASS・B1 ドリル PASS（2 mutant caught）・full suite green。ブロッカーなし。

```claims
verdict: pass
b1_drill: PASS (2 mutants caught)
tests: green
notes: ["framework・M・依存追加ゼロ（deps 監査 N/A）", "qa は mechanical-evidence gate（2nd-opinion 非対象 SECOND_OPINION_GATES=review/security）"]
```

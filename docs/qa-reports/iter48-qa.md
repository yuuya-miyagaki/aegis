# iter48 QA Report — profile 参照整合性チェック＋JNY-07 実修正

- 日付: 2026-06-26
- task_type/size: framework / M（review+qa+security 必須・deploy size-exempt）
- qa 証拠: 本ファイル（claims 付き）／B1 ドリル結果は `docs/qa-reports/test-strength.md`
- 参照: requirements `docs/requirements/iter48-distribution-self-containment.md` / plan `docs/plans/2026-06-26-distribution-self-containment-implementation-plan.md` / review `docs/qa-reports/iter48-review.md`

## 機能対照表（要件/plan の機能 → 検証）

| # | 機能 | 検証対象 | 検証方法 | 判定 |
|---|------|---------|---------|------|
| 1 | 横断参照整合性検査の存在 | `tests/test_profile_referential_integrity.py::test_every_profile_is_referentially_self_contained` | pytest | PASS |
| 2 | 2 穴を RED 捕捉（D5/JNY-07） | full.json から map 除去で整合性テスト＋e2e の両方が RED | 一時 mutation 実測 | PASS |
| 3 | JNY-07 実修正（full install で実出力） | `tests/test_profile_checker_parity.py::TestFullInstallSurfacesTemplateHints` | pytest（setup.sh full install→client-gate deny grep） | PASS |
| 4 | D5 by-design allow-list 理由付き | `INTENTIONAL_UNSHIPPED['full']['scripts/check_framework_contract.py']` | reason 非空テスト | PASS |
| 5 | 依存辺抽出ヘルパの teeth | `_deps_from_source` 5 ケース（static/string/stdlib/try/docstring）＋`_violations` 3 負例 | pytest | PASS |
| 6 | allow-list rot 検知 | `test_no_stale_or_redundant_allowlist_entries` | pytest | PASS |

実装漏れ=なし。

## 検証項目

### 検証項目: 3 点検証（LEARNINGS conf9）
- 操作: `python3 -m pytest -q` / `python3 scripts/check_framework_contract.py` / `python3 scripts/eval_scaffold_smoke.py`
- 期待: 全緑（pytest 単独では framework-root 専用 contract に未到達のため 3 点必須）
- 実際: pytest **1131 passed/1 skip**（record-test-result src:manual で green 記録・本 qa 直前の追加 3 テストで現 1134 系）、contract **PASS**、scaffold smoke **PASS（minimal/standard/full）**
- 判定: PASS

### 検証項目: JNY-07 install e2e
- 前提: tmp に `setup.sh --profile=full` install
- 操作: install の `check_status.py --root <install> --pre-approve-gate client_ready_for_dev`
- 期待: deny 出力に `templates/PRD.template.md` 等のテンプレ位置ヒントが出る
- 実際: PRD/SCOPE/NFR/ACCEPTANCE/HANDOVER-TO-DEV のテンプレパスが出力（修正前は空 degrade）
- 判定: PASS

### 検証項目: B1 テスト強度ドリル（mutation・3 mutant）
- 操作: `run-test-strength-drill.py`（fixed spec `docs/qa-reports/test-strength.drill`）
- mutant: (1) full.json の map 行を偽名化（→整合性＋e2e RED）/ (2) e2e の `--profile=full`→`minimal`（→map 不在で assert RED）/ (3) `_violations` の `and`→`or`（→空 reason 検知が RED）
- 期待: 全 mutant が caught（テスト赤化）
- 実際: **DRILL PASS — all mutants caught**（承認時にハーネスが再実走して合否判定）
- 判定: PASS

## Evidence Checklist

- [x] テストスイートを実行し結果を記録（record-test-result src:manual = green）
- [x] 3 点検証（pytest + contract + scaffold smoke）を実行
- [x] plan/requirements の受入条件と突合（機能対照表）
- [x] 各検証項目に PASS 判定・B1 は本物 mutation で 3 mutant caught
- [x] FAIL 項目なし

## 判定

**PASS**。Critical/Major=0。3 点検証緑・JNY-07 install e2e で実出力確認・B1 ドリル 3 mutant 全 caught。スタブ無し（実コード＝full.json データ追加＋テスト logic、grill-code/2次レビュー指摘も全反映）。

```claims
tests_pass: true
no_stubs: true
verdict: approve
b1_drill: 3_mutants_caught
```

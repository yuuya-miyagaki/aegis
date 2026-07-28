# iter78 review — pytest execution attestation

- 対象: `git diff a5ef438..HEAD`（実装 dd06cca..c55761e ＋ review fix-forward）
- 正本: `docs/specs/2026-07-28-iter78-pytest-execution-attestation-design.md` / `docs/plans/2026-07-28-iter78-pytest-execution-attestation-implementation-plan.md`
- 手法: 1次＝4角度 finder（opus・仕様準拠/敵対/テスト強度/保守性）＋盲検2次（fable）。finder は plan-mode stall が多発したため、critical 候補は**親が in-session 実走裁定**（LEARNINGS line40）。

## 対照表（plan 全タスク → 実装状態）

| Task | 実装 | 状態 |
|---|---|---|
| Task1 RED バッテリ | tests/test_attest_execution.py（28→33 pin） | 完 |
| Task2 plugin | scripts/aegis_attest_plugin.py（import-only） | 完 |
| Task3 attestor | scripts/attest-test-run.py（ask） | 完 |
| Task4 judge 契約＋pin17 | scripts/build-judge-card.py＋test3ファイル | 完 |
| Task5 record 誘導＋pin7 | scripts/record-test-result.py | 完 |
| Task6 統合＋文書 | full green・dogfood attest・skill/evidence.sh | 完 |

## 角度別サマリ

### 角度A（仕様準拠・opus 1次＋fable 盲検2次）
- design/plan 全節に対応実装・verdict 規則（green=exit0∧executed>=1∧failed=errors=collection_errors=0）・executed=passed+failed+xfailed+xpassed・pytest exit5=red を実走確認。
- 逸脱0・勝手な追加0（`templates/profiles/full.json` の2行は contract checker が ask スクリプトに要求する随伴・scope 内）。
- Finding F-1（Minor・conf8）: plan の A/B 表に表外3+2 pin 名が未追記＝doc-sync。→ **fix-forward で plan に追記済み**。
- 判定: **approve_with_notes**。

### 角度B（敵対・opus 2体＋親 in-session 実走）
finder 2体とも plan-mode stall。静的解析で 2 綴りを摘発→**親が tmp repo で全攻撃を実走裁定**:

| 攻撃 | コマンド | 観測 | 判定 |
|---|---|---|---|
| 出力偽造 | 実 pass が "999 failed" print | rc0 status ok・executed1 | 封鎖（出力非パース） |
| exit 洗浄 | `pytest; true` 等 | rc2 実行前拒否 | 封鎖 |
| plugin 抑止(cmd) | `-p no:aegis_attest_plugin` | rc2 | 封鎖 |
| plugin 抑止(env) | `PYTEST_ADDOPTS=-p no:...` | rc0（明示 cmdline -p が勝ち・実 green） | 封鎖 |
| **event 偽造(5b)** | conftest が偽 call passed 追記＋all-skip | **rc0 attested green 捏造** | **バイパス（残余）** |
| event 偽造(5a/5c) | 実失敗 suite に偽 sessionfinish/pass | **rc1 red 記録**（real exit 勝ち） | 封鎖（real red は green 化不能） |
| attested 手書き | evidence-log 直書き `attested,ok,fp一致`・counts皆無 | green（fp のみ moat） | 残余（既存 manual 天井同クラス） |

- **load-bearing 不変は保持**: 本物の red は偽イベントでも green にできない（5a/5c 実走確認）。作れるのは all-skip/all-pass の偽陽性のみ＝**drill が subsume**（all-skip→marker false→BLOCKED・親実走確認）。
- 2残余は**同一ユーザー OS-limit**（SF-004 同型・roadmap §6 対象外）＝**SF-024 起票**。iter78 は accidental 偽 green を全封鎖した net 改善で残るは故意偽造のみ（pre-iter78 echo-class と同クラス・非拡大）。
- 判定: **approve_with_notes**（新規 Critical/Major バイパス 0・残余は文書化＋緩和）。

### 角度C（テスト強度・mutation・親 in-session）
finder stall（"stays green under mutant" 断片）→ **親が mutation バッテリ実走**:

| mutant | 検知 | 検知者 |
|---|---|---|
| judge green制限 continue→pass | ✓2 | test_observed/manual_pytest_ok_no_longer_decides |
| src allowlist attested 除去 | ✓4 | test_attested_decides_* |
| **sessionfinish!=rc 突合削除（M3）** | **✗0→修正後✓1** | **検知者不在を摘発→pin 追加** |
| rc==0∧executed==0 削除 | ✓3 | test_zero_run_* |
| executed から xfailed+xpassed 除外 | ✓1 | test_all_xfail_green（SF-015） |
| attested counts 検証削除（新規） | ✓2 | test_handwritten_attested_*_fails_closed |
| record redirect `if fam:` 削除 | ✓1 | test_record_rejects_pytest_family |

- **Finding C-M3（Major・テスト強度 gap）**: `sessionfinish != rc` 突合（real-red-can't-go-green の要）に検知者が無かった。→ **fix-forward で `test_forged_sessionfinish_mismatch_rejected` 追加**（削除で RED を確認）。
- 判定: **修正後 approve**。

### 角度D（保守性・sonnet）
- Finding D-1（Major・conf6）: rc2 文言の一部が jargon。→ qa 文脈では十分 actionable＋新 pin が部分文字列依存のため据え置き（accepted）。
- Finding D-2（Minor・drift risk）: cmd 正規化が3+箇所コピー。→ **fix-forward で `_mask_cmd` ヘルパーに単一ソース化**（is_pytest_family_cmd/_norm_cmd_match/_cmd_has_shell_operators/scan inline の4箇所）。
- 他 Minor（event schema 暗黙契約・loader 3関数類似）は accepted（pre-existing パターンの踏襲・非拡大）。
- 判定: **approve_with_notes**。

## review fix-forward（本 review 内で実施・削除0）
1. **judge read-time counts 検証**（build-judge-card.py）: attested green は `counts.executed>=1` 必須・欠如/0 は unverified（B2 の「counts 皆無で green」非対称を除去）。
2. **M3 検知者 pin**（test_attest_execution.py）: `test_forged_sessionfinish_mismatch_rejected`＋`test_forged_pass_events_cannot_green_a_real_red`（load-bearing 不変の pin）。
3. **`_mask_cmd` 単一ソース化**（D-2）。
4. **SF-024 起票**＋design 残余節精密化＋plan A/B 表追記（F-1）。
- pin 数: 28→33（+5 review・+1 grill-code B11＝実装後 34）。契約強化: C12 リネーム（counts 皆無→unverified）。

## Evidence
- 影響スイート: test_attest_execution/test_judge_card/test_test_runner_realness/test_record_test_result/test_patterns_parity = **200 passed**（fix-forward 後）。
- full suite: **1442 passed / 2 skipped**（実装完了時）→ review fix 後も全 green（再実測）。
- `check_framework_contract.py` PASS・`check_reference_drift.py` PASS・`context_budget.py` PASS。
- mutation: 7 判断点に検知者確立（M3 gap を摘発→封鎖）。
- 敵対: 7 攻撃クラス実走・新規 Critical/Major バイパス 0・残余2は SF-024 で文書化＋緩和。

## 盲検2次（独立）

盲検2次エージェント（fable・fresh context）を dispatch したが**ハード stall**（37分ツール活動なし・SendMessage 再開も無応答＝他5 finder の plan-mode stall より重い死亡）。LEARNINGS line40「再開1回で駄目なら即親 in-session」に従い、**独立2次の実質を親が in-session で実走**（iter77 の残 mutation 親回収と同じ運用）。1次・角度B の battery が触れていない角度を新たに検証:

| 独立2次の観点 | 試行 | 観測 | 判定 |
|---|---|---|---|
| record↔judge drift | glued `python3 -mpytest`・quoted `"pytest"`・`PYTHONPATH=x pytest`・`poetry run pytest` の is_pytest 判定 | 両者同一 regex 共有・glued/quoted は非 runner fail-closed・env-prefix は両者 rc2 | 非対称なし |
| counts 壊れ耐性 | attested ok の counts=`"forged"`/`null`/`{executed:"1"}` | 全て unverified（isinstance dict+int ガード） | fail-closed 堅牢 |
| log rotation | .1 log の attested green | 正しく green 判定 | 正常 |
| plugin 例外妨害 | conftest が `pytest_runtest_logreport` で raise | run 壊れ → **red 記録**（rc1・green 化不能） | 封鎖（fail-visible） |
| load-bearing 不変 | 実失敗 suite に偽 sessionfinish/pass 注入 | real exit 勝ち red 記録 | 封鎖（本物の red は green 化不能） |

- 独立2次の**新規 finding 0**。SF-024 残余記述は**正直**（過小/過大なし）と独立確認: load-bearing 不変「本物の red は偽イベントでも green にできない」を独立実走で再現、drill subsume（all-skip→marker false）を実測、attested 手書き天井が fp-moat 同クラスであることを確認。
- 分岐点: 1次仕様準拠が見落とした attested read-time counts 非検証を敵対2次が摘発→counts 検証で緩和（親裁定）。M3 突合の検知者不在をテスト強度が摘発→pin 追加。いずれも fix-forward 済み。

## 総合判定: **approve_with_notes**

全 Critical/Major は review 内で fix-forward 済み（M3 検知者・counts 検証・drift なし独立確認）。残る notes は accepted residual（SF-024 の OS-limit・drill subsume・load-bearing 不変は pin 保証）＋ D-1 jargon（qa 文脈で actionable）。

```claims
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["敵対2次が attested read-time counts 非検証を摘発（1次仕様準拠は見落とし）→ 親裁定で counts 検証を追加", "テスト強度が M3 突合の検知者不在を摘発 → pin 追加", "5b event 偽造は design が名指し済み残余だが severity 較正を SF-024 で精密化（Low・OS-limit・非拡大）", "盲検2次エージェントがハード stall→親 in-session 独立検証で回収（drift/counts 堅牢/rotation/plugin 例外 全安全・新規 finding 0）"]
```

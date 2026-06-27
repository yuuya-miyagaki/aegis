# iter50 QA レポート — doc(CLAUDE.md/rules)→script 参照整合性 guard
<!-- 正本: qa agent -->

## 対象

- 変更内容: `tests/test_profile_referential_integrity.py` に iter50 セクション追加（install 実体の doc→script 参照整合性 guard）。production code 無改変・guard-only。
- 環境: ローカル（python3 / pytest）。internal framework iteration（ui_surface=false・ブラウザ QA 非該当）。
- 参照: plan=`docs/plans/2026-06-27-doc-script-ref-integrity-implementation-plan.md`／spec=同日 design／review=`docs/qa-reports/iter50-review.md`（approve_with_notes）。

## 機能対照表（plan 機能 → 検証）

| # | plan 機能 | 検証対象 | 検証方法 | 判定 |
|---|----------|---------|---------|------|
| T1 | doc resolver（install 実体解決） | `_doc_install_source`/`_DOC_TEMPLATE_REMAP` | 単体2（CLAUDE.md→template／rules→verbatim） | PASS |
| T2 | アンカー（setup.sh 同期・コメント耐性） | `test_doc_resolver_matches_setup_sh`/`_setup_resolve_remap` | 単体4＋実 setup.sh 一致＋3 mutation 手動実証 | PASS |
| T3 | doc edge 抽出（再利用） | `_doc_script_edges` alias | 単体1 | PASS |
| T4 | doc surface 選別 | `_shipped_doc_surfaces` | 単体2（選別／除外） | PASS |
| T5 | allow-list＋rot | `INTENTIONAL_UNSHIPPED_DOC` | 単体2（reason 非空／rot） | PASS |
| T6 | 本体 cross-check | `test_every_profile_doc_script_ref_is_self_contained` | install 実体読込＋allow-list トグル RED→GREEN | PASS |

検証対象なしの plan 機能は無し（実装漏れなし）。

## 実施した確認

- [x] テストファイル実行（36 passed）
- [x] フルスイート実行（回帰確認）
- [x] B1 mutation drill（テスト強度）
- [x] guard 本体の歯を allow-list トグルで実測（install 実体から3 profile 違反検出）
- [x] アンカーの歯を3 mutation で実測（drift／dead-key／parse 失敗 全 caught）
- [x] contract / status_doctor（review フェーズで PASS 確認済・gate 承認時に再評価）

## 実行コマンド

```bash
python3 -m pytest tests/test_profile_referential_integrity.py -q          # 36 passed
python3 -m pytest -q                                                      # 1157 passed, 1 skipped
python3 scripts/run-test-strength-drill.py --root . \
  --spec docs/qa-reports/test-strength.drill --report docs/qa-reports/test-strength.md
```

## 結果

- Pass: テストファイル **36 passed**／フルスイート **1157 passed, 1 skipped**（回帰ゼロ）。
- B1 mutation drill: **verdict PASS・mutants 3/3 caught・baseline green**（`docs/qa-reports/test-strength.md`）。
  - mutant1: `_doc_install_source` の remap を verbatim へ（line 453）→ `test_doc_source_claude_is_template` が RED で捕捉。
  - mutant2: `_shipped_doc_surfaces` の `CLAUDE.md` 判定を改竄（line 467）→ `test_shipped_doc_surfaces_selects_claude_and_rules` が RED。
  - mutant3: `_setup_resolve_remap` のコメント除去を no-op 化（line 518）→ `test_setup_parse_tolerates_quoted_comment_in_case` が RED。
- coverage-floor: iter50 は全行を末尾1連続ブロックで追記（既存行 無改変）＝単一ランのため3 mutant で floor 充足（iter49 の docstring 別ラン衝突は非該当）。
- Fail: なし。
- Skip: フルスイートの 1 skip は既存の record green skip（iter50 と無関係）。

## guard の歯の追加実証（手動）

- 本体: `INTENTIONAL_UNSHIPPED_DOC` を空にすると本体 cross-check が full/standard/minimal の3 profile で `CLAUDE.md（install 実体 templates/CLAUDE.template.md）→ scripts/check_framework_contract.py` を違反検出（restore で PASS）。dogfood CLAUDE.md を読むなら update-gate/update-task/platform_manifest も出るはずが出ない＝**install 実体を読んでいる証拠**。
- アンカー: resolver の template パス改竄／dead-key 追加／parse 空化の3 mutation を全て明示 fail で捕捉。

## Blockers

- なし。

```claims
verdict: pass
notes:
  - "guard-only（実穴ゼロ）の本イテレーションでも、B1 drill は単一ラン追記により 3 mutant で coverage-floor を充足し PASS（3/3 caught・baseline green）。iter49 の docstring 別ラン衝突は今回未改変のため非該当。"
  - "install 実体読込の正しさを二重実証＝allow-list トグルで template の check_framework_contract.py のみ検出（dogfood の4参照は出ない）。"
  - "フルスイート 1157 passed/1 skip・回帰ゼロ。tests=verified。"
```
<!-- exit-check: 全チェック実施・結果記入済み → security へ -->

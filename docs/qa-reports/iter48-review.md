# iteration 48 review — profile 参照整合性チェック＋JNY-07 実修正

- 日付: 2026-06-26
- task_type/size: framework / M（review+qa+security 必須・deploy は M で size-exempt）
- 対象 diff（code）:
  - `tests/test_profile_referential_integrity.py`（新規・横断検査＋ast 依存辺抽出＋`_violations` 純関数＋allow-list＋単体/負例/rot/docstring 境界テスト）
  - `templates/profiles/full.json`（+1 行・`scripts/_artifact_template_map.py` を recommended に同梱＝JNY-07 実修正）
  - `tests/test_profile_checker_parity.py`（`TestFullInstallSurfacesTemplateHints` 追加・full install の client-gate deny にテンプレヒントが出る e2e）
- 参照: requirements=`docs/requirements/iter48-distribution-self-containment.md` / spec=`docs/specs/2026-06-26-distribution-self-containment-design.md` / plan=`docs/plans/2026-06-26-distribution-self-containment-implementation-plan.md`

## 対照表（plan タスク → 実装）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| 1 | `_script_deps`（static import + string scan）＋`_violations` 純関数＋単体/負例テスト | `tests/test_profile_referential_integrity.py` | 完了 | 13 テスト（helper 5＋negative-control 3＋rot 1＋docstring 2＋本体 1＋reason 非空 1） |
| 2 | 横断検査本体＋`INTENTIONAL_UNSHIPPED` allow-list | 同上 | 完了 | full の JNY-07 辺を RED 実証→GREEN |
| 3 | JNY-07 実修正（full に map 同梱）＋install 実証 | `templates/profiles/full.json` ＋ `tests/test_profile_checker_parity.py` | 完了 | e2e で deny にテンプレパス出力を assert |
| 4 | ~~README 件数同期~~ | — | 不要と判明 | full 件数は README 記載・count テストとも無し（reconcile 済） |

未着手タスク=なし。

## findings（severity / confidence）— 1次（self/grill-code）＋盲検2次（`reviewer-maintainability`）統合

**1次（grill-code）— 全反映済**:
- **Should fix / conf 8** — 計画と実装の乖離（README no-op／e2e を parity test に追加）。→ **反映済**: plan のファイルマップ＋トレーサビリティを実態へ更新。
- **Should fix / conf 7** — `_deps_from_source` の検出境界（f-string/連結は非検出）が未明記。→ **反映済**: docstring コメントに既知境界を明記。
- **Nice / conf 7** — allow-list の rot 検知が無い。→ **反映済**: `test_no_stale_or_redundant_allowlist_entries` 追加（stale＝未参照／redundant＝実は同梱 を検知）。

**盲検2次（`reviewer-maintainability`・fresh context・verdict=approve_with_notes）— 反映/裁定済**:
- **Minor / conf 7** — docstring 中の `.py` を string scan が過検出しうる（境界テスト不在）。→ **反映済**: bare-expression（docstring・単独文字列文）を scan から除外し、`test_deps_ignores_docstring_mentions`＋`test_deps_picks_up_string_literal_in_real_statement` で境界を固定。
- **Minor / conf 6** — rot テストはハードコード allow-list のみ検査（逆方向は本体テストが担保）。→ **裁定**: by-design（前方向＝新規未同梱辺は `test_every_profile_is_referentially_self_contained` が捕捉）。追加対応なし。
- **Minor / conf 6** — `import scripts.foo` のドット付きは未解決。→ **反映済**: 現状 scripts は flat import のみ＝境界をコメント明記。

**検証（issue なし）**: 2 穴の RED→GREEN を full.json から map 除去で実測（整合性テスト＋e2e の両方が RED）。3点検証緑（pytest 1131→[本 review 後再走] / contract PASS / scaffold smoke PASS）。スコープ逸脱なし（command→script・skill 散文・severity 次元は明示的に対象外）。

Critical=0 / Major=0。

## Evidence Checklist

- [x] diff を Read で実読（chat summary でなく実ファイル）
- [x] requirements/spec/plan の受入条件と突合（対照表）
- [x] 未カバーのエッジケースを列挙（docstring/f-string/dotted import の検出境界を明記＋テスト固定）
- [x] 全 finding に severity と confidence 付与・全反映 or 裁定

## 判定

**PASS（approve_with_notes）**。Critical/Major=0。1次（grill-code）3 件＋盲検2次 3 件のうち、反映 5 件・by-design 裁定 1 件。JNY-07 は full 同梱で install 実出力を e2e 固定、D5 は maintainer 専用 by-design として理由付き allow-list、両穴の RED→GREEN を実測。自動検出（ast import＋string scan・bare-expression 除外）で再発クラスを恒久封鎖。

tests は本 review 直後に full suite を実走し record-test-result で green 記録（qa で B1 drill により強度も確認）。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "1次/2次に実質的相違なし。盲検2次の Minor 3 件のうち docstring 境界（F1）と dotted-import 境界（F3）を反映、rot 逆方向（F2）は本体テストが担保で by-design 裁定。両者とも『2 穴の RED→GREEN 実証・自動検出による再発封鎖・スコープ bound』に同意。"
```

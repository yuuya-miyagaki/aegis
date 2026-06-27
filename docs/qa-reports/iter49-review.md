# iter49 レビュー — 配布 self-containment 射程拡大（skill→script 検査＋update-task.sh 同梱）

- 対象 diff（uncommitted・production 相当）:
  - `tests/test_profile_referential_integrity.py`（+154）: skill(.md)→script 参照整合性検査を追加
  - `templates/profiles/full.json`・`templates/profiles/standard.json`: `required` に `scripts/update-task.sh` 追加
  - `README.md`: standard 件数 20→21
- 参照: spec=`docs/specs/2026-06-27-command-skill-ref-integrity-design.md`（訂正注記付き）／
  plan=`docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md`
- 検証: TDD RED（full の aegis-brainstorm/bug-diagnosis→update-task.sh）→ GREEN・
  test file 22 passed・full suite 1142 passed/1 skip・contract PASS。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| T0 | `_skill_script_edges` 抽出 | test:284＋単体5 | ✅ | code-fence/inline 抽出・散文/hooks/lib 除外・空 |
| T1 | 結合検査（RED 実証） | `test_every_profile_skill_script_ref_is_self_contained` | ✅ | RED=full→update-task.sh 文言一致→GREEN |
| T2 | manifest 修正 | full/standard.json `required`＋update-task.sh | ✅ | sibling=update-gate.sh |
| T3 | README 同期 | README:184（20→21） | ✅ | `test_readme_profile_counts` green |
| T4 | regression | 全 suite | ✅ | 1142 passed/1 skip・contract PASS |

未着手タスクなし。

## Findings（severity＋confidence）

### Critical
- 該当なし。

### Major
- 該当なし。

### Minor
- **M1（conf 7）** `tests/...:307` `_shipped_skill_docs` は plan 旧名 `_shipped_skills`（SKILL.md 限定）から
  改名・全 skill `.md` へ拡張（grill-code 🟡#1 反映）。意図的かつ正（deploy/platforms.md を検査対象化）。
  → **裁定**: plan 文言を `_shipped_skill_docs`/全 .md に同期済（doc↔impl 整合）。docstring に根拠あり。
- **M2（conf 8）** `tests/...:366` `test_skill_allowlist_no_stale_entries` は allow-list 空のため vacuous pass。
  → **裁定**: by-design（将来 guarded-optional ref 用の受け皿）。rot 判定の中核 `_violations` は単体実証済
  （iter48 `test_violations_*`）。entry 追加で活性化。容認。
- **M3（conf 6）** `tests/...:277` `_SKILL_SCRIPT_RE` はコメント/URL/散文中の `scripts/x.py` も拾う（過検出）。
  → **裁定**: fail-closed（過検出は allow-list[理由必須]で明示解消）。Markdown 文脈解析は surface 比で過剰。
  検出境界は docstring に固定済。容認。

### Confirmed OK
- README は full 件数を記載せず（既存仕様・本変更で不変）＝full required 件数は未検査だが**既存ギャップ**で
  本 iteration 由来でない（plan 射程外明記）。
- `update-task.sh` を standard+full の required に同梱（required `update-gate.sh` の sibling）。minimal は
  skill 非同梱で skill→script 露出ゼロ＝不変で正。

## Evidence Checklist

- [x] diff を実読（test 全体・manifest・README・spec/plan）
- [x] plan/spec の受入条件と突合（対照表）
- [x] 未カバーのエッジケース列挙（agents サーフェス＝穴ゼロ実証で射程外明記／platforms.md＝拡張で包含）
- [x] 全 finding に severity＋confidence 付与（confidence<7 は M3 のみ＝過検出許容の判断注記付き）

## 盲検 第2意見（`reviewer-maintainability`・fresh context・diff＋spec/plan のみ・verdict=approve_with_notes）

1次 verdict/コメント非開示で独立ディスパッチ。結果: approve_with_notes。findings: F1=`_shipped_skill_docs`
命名/スコープ拡張（Minor c7・docstring で緩和）／F2=allow-list 空で rot 検査 vacuous（Minor c8・by-design）／
F3=README full 件数未検査（Minor c9・既存ギャップ）／F4=regex 過検出 fail-closed 容認（OK c9）／
F5=update-task.sh sibling 整合・minimal 不変（OK c10）。**commands 免除の論拠（resolve_source が
templates/commands の scaffold-safe 版へ remap）を一次資料で独立確認**。1次の M1/M2/M3 と実質一致。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "1次/2次に実質的相違なし。両者 approve_with_notes。2次 F1(_shipped_skill_docs 命名)を plan 同期で解消、F2(vacuous rot)/F3(README full 未検査)は by-design/既存ギャップとして裁定一致、F4(regex fail-closed)/F5(sibling 整合)は OK。2次が commands 免除の resolve_source 論拠を一次資料で独立確認した点を補強として採用。"
```

## 判定

**PASS（approve_with_notes）**。Critical/Major ゼロ。Minor 3 件は裁定済（M1=plan 同期で解消・M2/M3=by-design 容認）。
tests は qa フェーズで full suite 実走＋B1 mutation drill により強度確認する。

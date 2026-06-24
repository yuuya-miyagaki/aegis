# iter44 Review Report — C5 ROOT-external plan-gate false-positive

- 日付: 2026-06-25
- 対象: full-review C5（`hooks/check-gate.sh` が ROOT 外絶対パスにも plan-gate / Client-mode deny を適用する false-positive の修正）
- task_type/size: framework / M（review+qa+security 必須・deploy は size routing で exempt）
- 参照: spec `docs/specs/2026-06-25-iter44-root-external-plan-gate-design.md` / plan `docs/plans/2026-06-25-iter44-root-external-plan-gate-implementation-plan.md`

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | ROOT 外絶対パス short-circuit ＋ RED-first テスト | `hooks/check-gate.sh`（+16 行 case ブロック）／`tests/test_check_gate_root_external.py`（新規・10 ケース） | 実装済 | RED（test_a/test_e）実測→GREEN。full suite 1103→（+test）green |

`git diff --name-only`: `hooks/check-gate.sh`（変更）／`tests/test_check_gate_root_external.py`（新規・untracked）。plan の Task は 1 件のみで全て実装済。未着手なし。

## Evidence Checklist

- [x] diff を実読（hooks/check-gate.sh の case ブロック・テスト全体）
- [x] plan/spec の受入条件と突合（ROOT 外 allow／ROOT 内 gate／control・templates・docs 不変／Client-mode 相互作用）
- [x] 未カバーのエッジ列挙（下記 findings 参照）
- [x] 全 finding に severity ＋ confidence 付与

## Findings（severity / confidence）

### Critical
該当なし。bypass 不成立を確認: short-circuit は docs/templates/control 判定の後に置かれ、ROOT 内は第1アームで gate 維持、`/*` allow は外部絶対のみ。`is_control_file` の絶対パターンは全て ROOT-anchored で外部絶対は構造的に非マッチ＝順序が逆でも穴は開かない（盲検 maintainability が独立確認）。

### Major
- **[testing, conf 8] false-green 耐性（positive control 不在）** — 解消済。test STATUS のスキーマがドリフトしても deny テストが気付けない懸念に対し、`test_i`（Dev・plan=approved・内部→allow）を追加。gate 値が正しく parse されなければ deny に転び FAIL するため、drift を捕捉する positive control になった。

### Minor
- **[testing/maintainability, conf 8] sibling prefix collision** — 解消済。`test_j`（`{root}-backup/...` → external/allow）追加＋hook コメントに「`/` 区切りが boundary を固定し sibling を誤って内部判定しない」旨を明記。
- **[testing, conf 7] test_b の ROOT_REAL アームが Linux で vacuous** — 受容。本開発プラットフォームは darwin（`/var`→`/private/var`）で ROOT≠ROOT_REAL となり両アームを実踏。Linux では論理=物理で 1 回に縮退するが挙動は同じ（hook も degrade gracefully）。残留として記録。

## 盲検 第2意見（self-attested）

1次（本セッションの構造化レビュー＋grill-code）確定後、verdict 非共有・fresh context（diff＋spec/plan のみ）で 2 エージェントを独立ディスパッチ:

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["reviewer-testing(approve_with_notes): Major=false-green 懸念→test_i で解消／Minor=sibling→test_j／Minor=test_b Linux vacuity 受容", "reviewer-maintainability(approve_with_notes): `/` delimiter コメント反映済／placement・bypass・normalize_target の ../ 封鎖を独立 approve"]
```

- **1次**（本セッション構造化レビュー＋grill-code）: approve_with_notes（Critical 0・notes 全解消）。
- **2次**（盲検 reviewer-testing / reviewer-maintainability・verdict 非共有・fresh context）: 両 approve_with_notes・Critical 0・bypass 0。
- 1次/2次とも approve_with_notes で一致。指摘は全て承認前に反映または受容記録。

## 判定

**PASS。** Critical 0。Major 1（解消済）・Minor 2（1 解消・1 受容記録）。実装は spec/plan の受入条件を満たし、緩和系変更にもかかわらず保護対象（project code・control file・templates・docs）は不変。test は RED 真正・10 ケース・positive control つき。

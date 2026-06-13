# 過程 docs アーカイブ Implementation Plan (P3・docs-only・版据え置き)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** root `docs/` の過程成果物（plans/qa-reports の履歴＋top-level 審査レポート 16）を `docs/archive/{plans,qa-reports,reviews}/` へ `git mv` で隔離し、空 scaffold dir 3 を削除する。コード挙動ゼロ変更・版据え置き。

**Architecture:** ファイル移動のみ。新規ロジック・テストなし。受け入れ条件は「移動前に緑だった契約（contract 全 profile / drift / full suite / make example）が移動後も緑」。`git mv` で履歴保全。current_refs が指す active（v162 qa-reports 4・requirements 1）は移動しない＝breakage ゼロ。plan/spec は本タスク（P3）docs へ通常ローテーション（移動する被参照ファイルは無し）。

**Tech Stack:** git, bash, python3（既存 checker）, pytest。

**設計書:** `docs/plans/2026-06-14-docs-archive-design.md`

---

## File Structure

| 操作 | 対象 | 行き先 |
|---|---|---|
| git mv | `docs/plans/*.md`（active 4 を除く 60） | `docs/archive/plans/` |
| git mv | `docs/qa-reports/*.md`（v162 4 を除く 55） | `docs/archive/qa-reports/` |
| git mv | top-level historical 16 | `docs/archive/reviews/` |
| git rm | `docs/{handover,requirements,decisions}/.gitkeep`（空 scaffold dir） | 削除 |
| edit | `docs/STATUS.md`（iteration 29・plan/spec ローテ・next_action・session_history） | — |
| edit | ワークスペース `MEMORY.md`（history パス → docs/archive/reviews/） | — |

**root 維持（keep-list）**:
- docs/plans/: `2026-06-14-volatile-truth-manifest-design.md`, `2026-06-14-v180-volatile-truth-manifest-implementation.md`, `2026-06-14-docs-archive-design.md`, `2026-06-14-docs-archive-implementation.md`
- docs/qa-reports/: `v162-review.md`, `v162-qa.md`, `v162-security.md`, `v162-deploy-checklist.md` ＋ **`test-strength.drill`（LIVE artifact＝run-test-strength-drill.py/test_test_strength_drill.py が参照）** ＋ `.gitkeep`
- top-level load-bearing 8: STATUS.md, LEARNINGS.md, MIGRATION-FROM-v7.md, architecture-overview.md, evidence-archive.md, hook-failure-policy.md, perf-baseline.md, full-review-2026-06-13-context-futureproof.md

---

## Task 1: 移動前ベースライン（緑を確認）

**Files:** なし（検証のみ）

- [ ] **Step 1: contract / drift が緑であることを確認**

Run:
```bash
python3 scripts/check_framework_contract.py && python3 scripts/check_reference_drift.py
```
Expected: `PASS: aegis contract is aligned` ／ `PASS: no reference drift detected`

- [ ] **Step 2: 既知 flake を除き full suite が緑であることを確認**

Run: `python3 -m pytest tests/ -q`
Expected: `1 failed, 750 passed, 1 skipped`（唯一の失敗は既知の順序依存 flake `test_python3_absent_advisory_hooks_do_not_crash`＝単独実行で緑。これが移動後も「これ1件のみ」であることを最終確認の基準にする）

---

## Task 2: docs/plans 履歴をアーカイブ

**Files:** Move `docs/plans/*.md`（keep-list 4 を除く 60）→ `docs/archive/plans/`

- [ ] **Step 1: archive dir 作成＋移動（keep-list を case で除外）**

Run:
```bash
mkdir -p docs/archive/plans
for f in docs/plans/*.md; do
  case "$(basename "$f")" in
    2026-06-14-volatile-truth-manifest-design.md|\
    2026-06-14-v180-volatile-truth-manifest-implementation.md|\
    2026-06-14-docs-archive-design.md|\
    2026-06-14-docs-archive-implementation.md) ;;
    *) git mv "$f" docs/archive/plans/ ;;
  esac
done
```

- [ ] **Step 2: root に keep-list 4 件だけが残ったことを確認**

Run: `ls docs/plans/`
Expected: 上記 4 ファイルのみ（design 2 件＝v180/P3、implementation 2 件＝v180/P3）

- [ ] **Step 3: contract / drift が緑のままであることを確認**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_reference_drift.py`
Expected: 両方 PASS（current_refs.plan/spec＝v180 はまだ root にあり解決可）

- [ ] **Step 4: コミット**

```bash
git add -A docs/plans docs/archive/plans
git commit -m "docs(P3): archive historical plans to docs/archive/plans (60 files)"
```

---

## Task 3: docs/qa-reports 履歴をアーカイブ

**Files:** Move `docs/qa-reports/*.md`（v162 4 を除く 55）→ `docs/archive/qa-reports/`。`test-strength.drill`・`.gitkeep` は `*.md` glob 対象外で自動的に残る。

- [ ] **Step 1: 移動（v162 を case で除外）**

Run:
```bash
mkdir -p docs/archive/qa-reports
for f in docs/qa-reports/*.md; do
  case "$(basename "$f")" in
    v162-review.md|v162-qa.md|v162-security.md|v162-deploy-checklist.md) ;;
    *) git mv "$f" docs/archive/qa-reports/ ;;
  esac
done
```

- [ ] **Step 2: root に v162 4 件＋test-strength.drill が残ったことを確認**

Run: `ls -A docs/qa-reports/`
Expected: `v162-review.md v162-qa.md v162-security.md v162-deploy-checklist.md test-strength.drill .gitkeep`（.md は v162 の 4 件のみ）

- [ ] **Step 3: contract / drift が緑のままであることを確認**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_reference_drift.py`
Expected: 両方 PASS（current_refs.review/qa/security/deploy＝v162 が解決可）

- [ ] **Step 4: コミット**

```bash
git add -A docs/qa-reports docs/archive/qa-reports
git commit -m "docs(P3): archive historical qa-reports to docs/archive/qa-reports (55 files)"
```

---

## Task 4: top-level 審査履歴 16 をアーカイブ＋空 scaffold dir 削除

**Files:** Move 16 top-level docs → `docs/archive/reviews/`；`git rm` 3 つの `.gitkeep`

- [ ] **Step 1: 16 ファイルを移動**

Run:
```bash
mkdir -p docs/archive/reviews
git mv docs/audit-charter-2026-06-06.md docs/archive/reviews/
git mv docs/audit-report-2026-06-06.md docs/archive/reviews/
git mv docs/evolution-review-2026-06-10.md docs/archive/reviews/
git mv docs/functional-integrity-audit-charter-2026-06-07.md docs/archive/reviews/
git mv docs/functional-integrity-audit-report-2026-06-07.md docs/archive/reviews/
git mv docs/behavioral-review-charter-2026-06-11.md docs/archive/reviews/
git mv docs/behavioral-review-report-2026-06-12.md docs/archive/reviews/
git mv docs/full-review-2026-06-12.md docs/archive/reviews/
git mv docs/full-review-charter-2026-06-12.md docs/archive/reviews/
git mv docs/full-review-2026-06-13.md docs/archive/reviews/
git mv docs/full-review-charter-2026-06-13.md docs/archive/reviews/
git mv docs/v060-improvement-report.md docs/archive/reviews/
git mv docs/v070-improvement-report.md docs/archive/reviews/
git mv docs/v071-improvement-report.md docs/archive/reviews/
git mv docs/v072-improvement-report.md docs/archive/reviews/
git mv docs/v073-implementation-summary.md docs/archive/reviews/
```

- [ ] **Step 2: 空 scaffold dir 3 を削除**

Run:
```bash
git rm docs/handover/.gitkeep docs/requirements/.gitkeep docs/decisions/.gitkeep
```

- [ ] **Step 3: keep-list 8（load-bearing）が root に残り、context-futureproof が健在であることを確認**

Run: `ls docs/*.md`
Expected（8 件のみ）: STATUS.md, LEARNINGS.md, MIGRATION-FROM-v7.md, architecture-overview.md, evidence-archive.md, hook-failure-policy.md, perf-baseline.md, full-review-2026-06-13-context-futureproof.md

- [ ] **Step 4: contract / drift が緑のままであることを確認**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_reference_drift.py`
Expected: 両方 PASS（requirements ref＝context-futureproof は root 維持で解決可）

- [ ] **Step 5: コミット**

```bash
git add -A docs
git commit -m "docs(P3): archive top-level review history + remove empty scaffold dirs"
```

---

## Task 5: STATUS 更新・メモリ更新・全回帰・最終確認

**Files:** Modify `docs/STATUS.md`；Modify workspace `MEMORY.md`

- [ ] **Step 1: STATUS.md frontmatter を更新**

`docs/STATUS.md` の以下を編集（**版は据え置き＝framework_version は触らない**）:
- `iteration: 28` → `iteration: 29`
- `phase: deploy`（据え置き）
- `task_size_rationale`: P3 docs アーカイブの記述に更新
- `last_updated`: 実行時刻（ISO8601）
- `current_refs.plan`: `docs/plans/2026-06-14-docs-archive-implementation.md`（P3 へローテ・root 維持で解決可）
- `current_refs.spec`: `docs/plans/2026-06-14-docs-archive-design.md`（同上）
- `current_refs.requirements`: `docs/full-review-2026-06-13-context-futureproof.md`（据え置き）
- `current_refs.review/qa/security/deploy`: v162 据え置き（移動していない）
- `next_action`: P3 完了の要約（archive 構造・移動数・backlog 完済）
- `session_history`: 2026-06-14 の P3 エントリを prepend し、**最古エントリを 1 件削除して 3 件以内**に保つ（contract が max 3 を enforce）

- [ ] **Step 2: STATUS が contract を通ることを確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS: aegis contract is aligned`（session_history ≤ 3・current_refs 全解決）

- [ ] **Step 3: example ミラー差分ゼロを確認**

Run: `make example && git status --short`
Expected: docs/archive は root のみ＝`examples/minimal-project/` に差分が出ない（archive 系の変更が example に波及しない）

- [ ] **Step 4: 全回帰**

Run:
```bash
python3 scripts/check_framework_contract.py
python3 scripts/check_reference_drift.py
python3 -m pytest tests/ -q
bash tests/poc/v162-redteam-rerun.sh
bash tests/poc/v163-redteam.sh
```
Expected: contract PASS / drift PASS / pytest `1 failed, 750 passed, 1 skipped`（既知 flake のみ・Task 1 と同一＝新規回帰ゼロ）/ PoC 18/18・5/5。

- [ ] **Step 5: ワークスペース MEMORY.md の history パスを更新**

ワークスペース `/Users/miyagakiyuuya/.claude/projects/-Users-miyagakiyuuya-Desktop-personal-superpowers-gstack-antigravitykit-urtorapowers/memory/MEMORY.md` 内で、移動した history docs を参照している箇所を `docs/archive/reviews/...` に置換:
- `aegis/docs/behavioral-review-report-2026-06-12.md` → `aegis/docs/archive/reviews/behavioral-review-report-2026-06-12.md`
- `aegis/docs/evolution-review-2026-06-10.md` → `aegis/docs/archive/reviews/evolution-review-2026-06-10.md`
- `aegis/docs/audit-charter-2026-06-06.md` / `audit-report-2026-06-06.md` → `docs/archive/reviews/...`
- `aegis/docs/functional-integrity-audit-charter-2026-06-07.md` / `report` → `docs/archive/reviews/...`
- `aegis/docs/full-review-charter-2026-06-12.md` / `full-review-2026-06-12.md` → `docs/archive/reviews/...`
- 据え置き（root のまま）: `docs/full-review-2026-06-13-context-futureproof.md`（requirements ref）, `docs/architecture-overview.md` 等 load-bearing 8

（MEMORY.md は aegis repo 外＝git コミット対象外。ファイル編集のみ。）

- [ ] **Step 6: STATUS をコミット**

```bash
git add docs/STATUS.md
git commit -m "chore(STATUS): record P3 docs archive landing (iteration 29, version held)"
```

---

## Self-Review

**1. Spec coverage（設計書 §1-8 との照合）:**
- §2 アーキ（docs/archive/{plans,qa-reports,reviews}・git mv・root=active）→ Task 2/3/4 ✓
- §3 移動・削除リスト（plans 60・qa-reports 55・top-level 16・空dir 3）→ Task 2/3/4 ✓
  - 注: 設計 §3-1 は「61」と記載だが、本タスクで P3 implementation 計画自身も keep に加わるため実移動は 60（design 計画と本計画の 2 つが新 active）。test-strength.drill は LIVE artifact として除外（設計 §5 の趣旨＝契約を壊さない）。
- §4 keep-list（load-bearing 8）→ Task 4 Step 3 で確認 ✓
- §5 検証（contract 全 profile / drift / full suite / make example / メモリ更新）→ Task 1/各 Step3-4/Task 5 ✓
- §6 テスト追加不要（移動のみ・移動前後緑）→ Task 1 ベースライン＋各タスク検証 ✓
- §7 版据え置き＋STATUS → Task 5（framework_version 不変）✓
- §8 スコープガード（README 非縮約・specs/reviews 据え置き・archive index 無し・example 非改変）→ 全タスクで遵守 ✓

**2. Placeholder scan:** TBD/TODO 等なし。move コマンドは実行可能な実コード。✓

**3. 整合性チェック:**
- keep-list は Task 2（plans 4）/ Task 3（qa-reports v162 4＋drill）/ Task 4（top-level 8）で一貫。`test-strength.drill` を qa-reports keep に含め、`*.md` glob で自動除外＝二重に安全。✓
- current_refs ローテ（plan/spec→P3）で移動するファイルは無い（P3 docs は元から root・移動対象外）＝breakage ゼロ。review/qa/security/deploy/requirements は不変。✓
- 設計 §1「current_refs 無編集」と §7「plan/spec を P3 へ」の不整合は、本計画で「plan/spec は通常の per-iteration ローテーション（被参照ファイルを移動しない＝breakage ゼロ）」として解決。grill-plan の確認対象。

**留意（grill-plan へ渡す論点）:**
- `git mv` のワイルドカード移動が大量（131）＝1 ファイルでも typo すると検出しにくい。各タスク Step3-4 の contract/drift と Task5 の full suite が安全網。
- v180 plans（P2・shipped）を root に残す判断（設計の keep-list 準拠）。今や current_refs 非参照だが設計合意通り据え置き。archive に倒すべきか要確認。
- session_history max 3 の維持（Task 5 Step1 で最古 1 件削除）。

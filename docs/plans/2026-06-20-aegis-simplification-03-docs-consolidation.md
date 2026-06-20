# docs 整理（archive 撤去・bookkeeping 整理）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans（小規模・git rm 中心）。Steps はチェックボックス。
>
> 正典設計: `docs/plans/2026-06-20-aegis-simplification-design.md`（判定#5）。簡素化5ワークストリームの**第3**。低リスク・高削減（作業ツリー約33k行減）。

**Goal:** `docs/` の作者向け履歴・簿記（git 履歴で保全）を作業ツリーから撤去。ユーザーを導く doc と load-bearing は残す。

**Architecture:** 撤去は純粋な `git rm`（履歴は git に残る）＋少数の prose 参照掃除。**load-bearing / active を一切触らない**ことが唯一のリスクなので、撤去対象は「ランタイム/コントラクト/テスト参照ゼロ かつ current_refs 非参照 かつ active backlog でない」もののみ。

**Tech Stack:** git / Python 3・pytest。

**前提:** カレント＝framework root。M3・examples cut 完了済み。

## 検証で確定した KEEP / REMOVE（manifest＋STATUS current_refs＋active 判定）

**REMOVE（参照ゼロ・current_refs 非参照・履歴 only）:**
- `docs/archive/`（132ファイル・約29,363行）— ランタイム参照ゼロ。STATUS は note prose のみ、test は comment cite のみ。
- `docs/reviews/`（4ファイル・927行）— second-opinion 旧 phase スナップショット。参照ゼロ。
- `docs/qa-reports/{iter31-batch1-,v1100-,v162-}*`（12ファイル）— 旧版審査。現 current_refs（qa/review/security/deploy=null）非参照。
- `docs/MIGRATION-HISTORY.md`（527行）— 移行履歴。コード参照なし（README/旧 plan/spec の prose link のみ）。

**KEEP（load-bearing または active — 撤去禁止）:**
- `docs/full-review-2026-06-13-context-futureproof.md` ← **current_refs.requirements が指す**（contract 必須）。
- `docs/security-followups.md` ← **OPEN セキュリティ課題の active backlog**＋LEARNINGS 参照。
- load-bearing: `MIGRATION-FROM-v7.md`(contract)・`second-opinion.md`(doctor/session-start/contract)・`evidence-archive.md`(check_status target)・`hook-failure-policy.md`(test)・`architecture-overview.md`(test)・`perf-baseline.md`(test bounds)。
- `docs/qa-reports/{judge-*.md, test-strength.drill, test-strength.md, .gitkeep}`（ランタイム）。
- `docs/specs/`（決定記録）・`docs/plans/`（active）・`docs/client/`・`docs/handover/TO-CLIENT.md`・`docs/onboarding/`・`docs/translation/`・`STATUS.md`・`LEARNINGS.md`。

**やらない（投資過剰/設計通り）:**
- dangling skill パス（`docs/requirements/`・`docs/decisions/`・`docs/handover/{MANUAL,RUNBOOK,UAT-RESULTS,TO-DEV,CHANGES}.md`）への stub 作成 — 全てランタイム生成のプロジェクト成果物＝設計通り。`templates/` にテンプレあり。
- `docs/specs/` のブラッシュ（決定記録・churn 不要）。
- 完了 plan の archive 移動（archive 自体を撤去するので無意味）。

---

### Task 1: ベースライン

- [ ] **Step 1: 全層緑を確認**

Run: `python3 -m pytest -q` → 全 PASS（総数メモ）。
Run: `python3 scripts/check_framework_contract.py` → `PASS: aegis contract is aligned`。
Run: `python3 scripts/run_eval.py` → `Result: PASS`。

- [ ] **Step 2: current_refs.requirements が full-review を指すことを再確認（撤去禁止の確認）**

Run: `grep -n "full-review-2026-06-13" docs/STATUS.md`
Expected: current_refs.requirements に存在＝この file は KEEP。

---

### Task 2: 履歴・簿記を撤去し prose 参照を掃除

- [ ] **Step 1: 撤去（git rm・パスはクォート）**

Run:
```bash
git rm -r "docs/archive" "docs/reviews"
git rm "docs/MIGRATION-HISTORY.md"
git rm "docs/qa-reports/iter31-batch1-deploy-checklist.md" "docs/qa-reports/iter31-batch1-qa.md" "docs/qa-reports/iter31-batch1-review.md" "docs/qa-reports/iter31-batch1-security.md"
git rm "docs/qa-reports/v1100-deploy-checklist.md" "docs/qa-reports/v1100-qa.md" "docs/qa-reports/v1100-review.md" "docs/qa-reports/v1100-security.md"
git rm "docs/qa-reports/v162-deploy-checklist.md" "docs/qa-reports/v162-qa.md" "docs/qa-reports/v162-review.md" "docs/qa-reports/v162-security.md"
```
Expected: 132＋4＋1＋12＝149ファイルが staged for deletion。

- [ ] **Step 2: README から MIGRATION-HISTORY リンクを除去**

`README.md` の `docs/MIGRATION-HISTORY.md` への言及行を削除（リンク/箇条書き1行）。他の README 構造は維持。

- [ ] **Step 3: test の stale comment cite を掃除**

`tests/test_hook_output_schema.py:1264-1265` の `# ... See docs/archive/reviews/... and docs/archive/plans/...` を、archive パスを含まない説明コメントに置換（テストロジックは不変＝コメントのみ）。

- [ ] **Step 4: 全層緑を確認（load-bearing 無傷の証明）**

Run: `python3 -m pytest -q`
Expected: 全 PASS。Task1 から**テスト数の減少なし**（削除は docs のみ＝テスト非依存）。
Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS`（full-review・load-bearing 群を残したので current_refs/REQUIRED_FILES 健全）。
Run: `python3 scripts/run_eval.py`
Expected: `Result: PASS`。

- [ ] **Step 5: コード内 dangling 参照ゼロを確認（prose 履歴は対象外）**

Run:
```bash
grep -rn "docs/archive\|docs/reviews/\|MIGRATION-HISTORY" --include='*.py' --include='*.sh' --include='*.json' . | grep -v ".git/"
```
Expected: 出力なし（test comment 掃除後）。docs 内の prose（STATUS note・旧 plan/spec）は履歴として残置可。

- [ ] **Step 6: ステージ確認 → コミット**

Run: `git status --short`
Expected: 149 `D`＋`README.md`/`tests/test_hook_output_schema.py` の `M`。想定外 path が無いか目視。

`git commit -F <msgfile>`（パスはクォート）:
`refactor(simplification): consolidate docs — drop archive/history bookkeeping (docs cut)`

その後 `docs/STATUS.md` 更新は本 workstream では任意（structured ref は触らない）。

---

## Self-Review
- **load-bearing 保全の二重確認**: manifest（コード参照）＋STATUS current_refs（structured）＋active backlog 判定の3観点で KEEP を確定。manifest が見落とした `full-review`（current_ref）と `security-followups`（active）を KEEP に是正済み。
- **green-between-tasks**: docs 撤去はテスト非依存＝Task2 後も件数不変・全緑のはず。pytest だけでなく **contract＋run_eval（Tier1）** も回す（examples cut の教訓: contract は CLI 専用検証あり）。
- **Placeholder**: 撤去対象は全列挙。prose 掃除は2箇所明示。
- **YAGNI**: dangling stub・specs ブラッシュ・plan archive 移動は不要と判断（設計通り/churn 回避）。

## 注記
- 最大リスクは「load-bearing 誤削除」のみ。current_refs.requirements=full-review・active security-followups を KEEP で回避。
- 撤去は git 履歴で完全に復元可能（reversible・低 stakes）。

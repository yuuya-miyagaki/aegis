# 設計確定：過程 docs アーカイブ（P3・docs-only）

- 日付: 2026-06-14
- 対象: aegis（HEAD `c18fd85` / v1.8.0）
- 出典: 第7回全力レビュー `docs/full-review-2026-06-13-context-futureproof.md` §2 P3「過程 docs の archive 化・空 scaffold 削除」（M2）
- 種別: docs-only 再編（コード挙動ゼロ変更）。**版は据え置き（v1.8.0 のまま）**＝SemVer 的にコード不変に版を消費しない。
- task_type: framework / task_size: L（~134 ファイル移動）
- フロー: brainstorm（本書）→ writing-plans → grill-plan → 実装 → grill-code

---

## 0. 目的と非目的

root `docs/` の過程成果物（qa-reports/plans の履歴＋top-level の審査レポート履歴）を `docs/archive/` に隔離し、「**root = 運用ドキュ＋現イテレーションの active ref／archive = 履歴**」の不変条件を確立する。ソロ運用の持続性（root の見通し）を上げる。

**非目的（YAGNI ガード）**:
- README 44KB の縮約（フレームワークの玄関口＝内容品質の別タスク）。
- `docs/specs/`(9) ・`docs/reviews/`(4) サブツリーの移動（合意範囲外。必要なら後追いで安全に移動可）。
- `docs/archive/` への index README 作成（git log で履歴追跡可）。
- example（`examples/minimal-project/docs/`）の改変（別物＝scaffold 見本・REQUIRED_FILES・別 current_refs）。

---

## 1. 設計判断（確定事項）

### 判断 A：active は root 維持＝current_refs 無編集
root `docs/STATUS.md` の current_refs が指す 6 ファイル（plans 2＝v180、qa-reports 4＝v162）と requirements ref（top-level `full-review-2026-06-13-context-futureproof.md`）は **root に残す**。「契約（every declared ref points to an existing file）」を編集せずに満たす。

### 判断 B：履歴は git mv で移動（履歴保全）
`git mv` でファイル履歴を保持しつつ `docs/archive/{plans,qa-reports,reviews}/` へ。

### 判断 C：空 scaffold dir 削除
framework repo では常に空の `docs/{handover,requirements,decisions}/.gitkeep` を `git rm`。root REQUIRED_FILES 非対象・runtime の client モードは scaffold 側で別途生成するため安全。

---

## 2. アーキテクチャ

```
docs/
├── STATUS.md, LEARNINGS.md, MIGRATION-FROM-v7.md   ← 運用（REQUIRED）
├── architecture-overview.md, evidence-archive.md   ← 運用（test/参照）
├── hook-failure-policy.md, perf-baseline.md         ← 運用（参照）
├── full-review-2026-06-13-context-futureproof.md    ← current_refs.requirements（維持）
├── plans/         ← active 2（v180 design + implementation）のみ
├── qa-reports/    ← active 4（v162 review/qa/security/deploy-checklist）のみ
├── specs/(9), reviews/(4), client/(3), onboarding/(4), translation/(1)  ← 据え置き
└── archive/
    ├── plans/      ← 履歴 61
    ├── qa-reports/ ← 履歴 57
    └── reviews/    ← top-level 履歴 16
```

---

## 3. 移動・削除リスト

### 3-1. `docs/plans/*` → `docs/archive/plans/`（active 2 を除く 61）
- 除外（root 維持）: `2026-06-14-volatile-truth-manifest-design.md`, `2026-06-14-v180-volatile-truth-manifest-implementation.md`, **本設計書 `2026-06-14-docs-archive-design.md` と後続の実装計画**（P3 の active ref）

### 3-2. `docs/qa-reports/*` → `docs/archive/qa-reports/`（active 4 を除く 57）
- 除外（root 維持）: `v162-review.md`, `v162-qa.md`, `v162-security.md`, `v162-deploy-checklist.md`

### 3-3. top-level historical 16 → `docs/archive/reviews/`
audit-charter-2026-06-06, audit-report-2026-06-06, evolution-review-2026-06-10, functional-integrity-audit-charter-2026-06-07, functional-integrity-audit-report-2026-06-07, behavioral-review-charter-2026-06-11, behavioral-review-report-2026-06-12, full-review-2026-06-12, full-review-charter-2026-06-12, full-review-2026-06-13, full-review-charter-2026-06-13, v060-improvement-report, v070-improvement-report, v071-improvement-report, v072-improvement-report, v073-implementation-summary

### 3-4. 空 dir 削除
`docs/handover/.gitkeep`, `docs/requirements/.gitkeep`, `docs/decisions/.gitkeep`（dir ごと消える）

---

## 4. root に残す keep-list（load-bearing）
STATUS.md / LEARNINGS.md / MIGRATION-FROM-v7.md（REQUIRED_FILES）/ architecture-overview.md（test_arch_overview_currency）/ evidence-archive.md / hook-failure-policy.md / perf-baseline.md / full-review-2026-06-13-context-futureproof.md（current_refs.requirements）

---

## 5. 壊さない検証（テスト戦略）
移動は契約・テスト・README から個別参照されない 134 ファイルが対象（参照監査で実証済み）。実装後に以下で回帰確認:
- `python3 scripts/check_framework_contract.py`（全 profile）= current_refs 6 active が解決＋REQUIRED_FILES 健在。
- `python3 scripts/check_reference_drift.py` = 緑。
- full pytest suite = 既存 + 新規ゼロ（docs 移動はテスト追加不要だが、回帰ゼロを確認）。既知の順序依存 flake は単独緑として扱う。
- `make example` 差分ゼロ（archive は root のみ）。
- メモリ `MEMORY.md` の history パス参照（behavioral-review/evolution-review/audit-report/full-review charter 等）を `docs/archive/reviews/...` に更新。

## 6. テスト追加の要否
本タスクはファイル移動でロジック変更なし＝新規ユニットテストは不要。代わりに「移動後に既存契約（contract/drift/full suite）が緑」を受け入れ条件とする。**TDD の red は『契約が active ref を解決できること』を移動前後で確認する形**（移動前緑→移動実行→移動後緑）。

## 7. 版・STATUS
- 版: **据え置き（v1.8.0）**。版 stamp 4 箇所は触らない。
- STATUS: iteration 29、phase deploy、current_refs.plan/spec を P3 docs に、requirements は据え置き、review/qa/security/deploy は v162 据え置き、next_action/session_history 更新。

## 8. スコープガード（YAGNI 再掲）
README 縮約せず ／ specs・reviews サブツリー据え置き ／ archive index 作らず ／ example 非改変 ／ 版据え置き。

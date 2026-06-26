# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- 各 profile の「shipped .py が実行時に参照する兄弟スクリプト依存が、同梱 ∨ 理由付き
  allow-list」を恒久検査するテストを追加し、現存 2 穴（D5 / JNY-07）を解消する。
  JNY-07 は実修正（full に `_artifact_template_map.py` 同梱）、D5 は by-design allow-list。

## 入力

- 参照要件: `docs/requirements/iter48-distribution-self-containment.md`
- 参照設計: `docs/specs/2026-06-26-distribution-self-containment-design.md`

## Deploy Target

### プラットフォーム

- Hosting: n/a（framework 内部の配布契約テスト。デプロイ対象なし）
- Database: n/a
- CI/CD: n/a（ローカル pytest + contract + scaffold smoke で検証）

### 互換性確認

- next.config `output` 設定: n/a（Node/Web アプリではない）
- デプロイ先互換: n/a（size=M は deploy gate を size-exempt）

### 認証方式

- 認証プロバイダ: None（n/a）
- DEMO_MODE 予定: n/a

## Git 戦略

- 現行 main で作業（iter45-47 と同じ単一ブランチ運用）。push は最後にユーザー承認の上
  `gh auth switch --user yuuya-miyagaki` で実施。

## grill-plan 反映（2026-06-26）

致命的 3 件を反映:
- **F1（自動検出に置換）**: 手動 `KNOWN_EXTRA_EDGES` を廃止。`_script_deps` は ast の
  static import（Import/ImportFrom→兄弟 `scripts/<mod>.py`）＋ **ast 文字列定数走査**
  （`ast.Constant(str)` で `*.py` かつ 兄弟 `scripts/<basename>` 実在 → 動的辺）の二段。
  status_doctor→check_framework_contract（string read）も build-judge-card→importlib も
  **自動検出**。過検出（docstring 等）は fail-closed＝allow-list で明示解消。ハイフン名
  （build-judge-card.py 等）は import 不可視だが string scan で拾える。
- **F2（negative control）**: 判定を純関数 `_violations(shipped, edges, allowlist)->list` に
  切り出し、合成入力で歯を証明（未同梱＋未 allow-list→違反 / allow-list 済→無違反 /
  reason 空→違反）。vacuous（false-green）封鎖。
- **F3（install 実証の assertion 具体化）**: tmp full install で check_status を client-gate
  pre-approve 実行し、deny 出力にテンプレパス（例 `templates/PRD.template.md`）が含まれることを assert。

対象外（明示・bound）: required-vs-recommended の severity 次元（conf8 line84）。現状 gate-blocking 依存は
既に required のため実害なし。本スライスは「同梱されるか」に限定し、severity は将来スライス。

## ファイル構造（変更マップ）

**実装後 reconcile（grill-code 🟡）**: README は no-op と判明（`test_readme_profile_counts.py` は
minimal/standard のみ検査し full 件数を追跡せず、README にも full 件数の記載なし）。代わりに
e2e install テストを JNY-07 ファミリ（`test_profile_checker_parity.py`）へ追加した。実際の変更 3 ファイル:

- 新規: `tests/test_profile_referential_integrity.py` — profile 横断の参照整合性検査＋
  ast ベース依存辺抽出（static import + string-literal sibling scan）＋純関数 `_violations`＋
  `INTENTIONAL_UNSHIPPED` allow-list＋ヘルパ/負例/rot 検知 単体テスト。
- 変更: `templates/profiles/full.json:recommended` — `scripts/_artifact_template_map.py`
  を 1 行追加（JNY-07 実修正）。
- 変更: `tests/test_profile_checker_parity.py` — `TestFullInstallSurfacesTemplateHints` 追加
  （full install を実施し client-gate deny にテンプレ位置ヒントが出ることを e2e で固定＝
  grill-plan F3 の install 実証 assertion の恒久テスト化）。
- **不要と判明**: `README.md`（full 件数の記載・テストとも無し）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `_script_deps()`（static+string）＋`_violations()` 純関数＋単体/負例テスト | なし |
| Task 2 | 横断検査本体＋`INTENTIONAL_UNSHIPPED` | Task 1 の `_script_deps()`/`_violations()` |
| Task 3 | full.json に map 追加（GREEN 化）＋install 実証 | Task 2（RED を GREEN に） |
| Task 4 | README 件数同期 | Task 3 |

循環なし。Consumes は各前タスクの Produces に一致。

## タスク分解

### タスク 1: 依存辺抽出 `_script_deps` ＋判定純関数 `_violations`

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `tests/test_profile_referential_integrity.py`（新規・ヘルパ部）
**意図（F1）:** `_script_deps(py_path) -> set[str]` は二段:
1. static import: `ast` の Import/ImportFrom を走査し、module 名が `scripts/<mod>.py` に実在する
   兄弟なら `{"scripts/<mod>.py"}`。try/except 内も**辺として数える**（degrade は壊れないだけで
   機能は依存同梱で初めて働く）。
2. dynamic/string: `ast.Constant(str)` を走査し、値が `*.py` かつ basename が兄弟 `scripts/<basename>`
   に実在 → 動的辺（importlib/subprocess/string-read を自動捕捉）。
**意図（F2）:** `_violations(shipped:set, edges:set, allowlist:dict)->list[str]` を純関数化。
`dep ∉ shipped ∧ (dep ∉ allowlist ∨ allowlist[dep] が空)` を違反として返す。
**TDD:** テスト → FAIL → 最小実装 → PASS。
**受入条件（単体テスト＝test has teeth）:**
- `_script_deps` 正例: `from _artifact_template_map import X` → `{"scripts/_artifact_template_map.py"}`。
- `_script_deps` 正例（string）: `"check_framework_contract.py"` リテラル → 兄弟実在で辺に含む。
- `_script_deps` 負例: `import json`（兄弟不在）→ 含まない。
- `_script_deps` 正例（try/except）: try 内 import も拾う。
- `_violations` 負例制御: `shipped={}, edges={"scripts/x.py"}, allowlist={}` → 違反 1 件
  （未同梱＋未 allow-list）。
- `_violations`: allow-list 済（非空 reason）→ 違反 0。reason 空文字 → 違反 1。
**Deliverable:** [ ] `_script_deps` 二段動作 [ ] `_violations` 純関数 [ ] 6 ケースカバー

### タスク 2: 横断検査本体＋allow-list

**blockedBy:** Task 1 | **モデル:** `inherit`
**ファイル:** `tests/test_profile_referential_integrity.py`
**意図:** 各 profile JSON で shipped = (required ∪ recommended) ∩ `scripts/*.py`。各 shipped .py の
依存辺 = `_script_deps()`（static+string・**自動検出**）。`_violations(shipped, edges, INTENTIONAL_UNSHIPPED[profile])`
が非空なら FAIL（remediation テキスト付き＝「`<profile>.json` に同梱 OR `INTENTIONAL_UNSHIPPED['<profile>']` に
reason 付き追記」）。allow-list reason 非空テストも追加。
**INTENTIONAL_UNSHIPPED 初期値（自動検出が surface した辺を実装時に確定）:**
- `minimal`/`standard`: `scripts/_artifact_template_map.py` → 「Dev-lean/core-only。Client workflow 不在で
  client-gate テンプレヒント未使用（conf8 line61）」
- `minimal`: check_status が判定経路で参照する judge 系（build-judge-card.py / run-test-strength-drill.py
  等）が string scan で surface した場合 → 「minimal は judge toolchain 非同梱。run_judge_card 経路は
  minimal 利用で未到達」。**実装時に自動検出結果を見て確定**（投機で先回り登録しない）。
- `full`: `scripts/check_framework_contract.py` → 「contract/version ツールチェーンは maintainer 専用。
  D5 ドリフトは maintainer→install 方向の検査で install 単体は新版を観測不能＝field no-op は
  by-design。依存閉包 platform_manifest+context_budget を install に同梱しない」
  **※ full に `_artifact_template_map` は allow-list しない（Task 3 で同梱する＝RED の駆動源）**
**TDD（RED-first）:** Task 2 を書いた時点で full の `check_status → _artifact_template_map` 辺が
未同梱（full.json 未更新）かつ未 allow-list → **RED**。
**受入条件:** 検査本体が RED（full の JNY-07 辺）になることを実測。負例制御（F2）が別途 GREEN。
**Deliverable:** [ ] 検査本体 [ ] reason 非空テスト [ ] RED 実測

### タスク 3: JNY-07 実修正（full に map 同梱）＋install 実証

**blockedBy:** Task 2 | **モデル:** `inherit`
**ファイル:** `templates/profiles/full.json`
**意図:** `recommended` に `scripts/_artifact_template_map.py` を追加 → full install で
check_status のテンプレヒントが働く。Task 2 の RED が GREEN に。
**TDD:** Task 2 の RED → この修正で GREEN 確認。
**受入条件（F3・install 実証 assertion）:** tmp full install を実施し
`python3 scripts/check_status.py --root <install> --pre-approve-gate client_ready_for_dev` を実行、
出力に `templates/PRD.template.md`（および `templates/HANDOVER-TO-DEV.template.md`）が**含まれること**を
assert。`_artifact_template_map.py` が install に同梱されていることも確認。Task 2 GREEN。
**Deliverable:** [ ] full.json 更新 [ ] 横断検査 GREEN [ ] install deny にテンプレパス出力を assert

### タスク 4: README 件数同期

**blockedBy:** Task 3 | **モデル:** `inherit`
**ファイル:** `README.md`
**意図:** full profile のファイル件数 +1 を README に反映。
**TDD:** `test_readme_profile_counts.py` が RED（JSON +1 で不一致）→ README 修正で GREEN。
**受入条件:** `test_readme_profile_counts.py` GREEN。
**Deliverable:** [ ] README 更新 [ ] count テスト GREEN

## 事前準備

- [ ] ベースは現行 main（origin/main=2c81192）。rollover+brainstorm 成果物は未コミット（同一作業ツリー）。
- [ ] 依存追加なし（標準ライブラリ ast/json のみ）。

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| 横断検査の存在 | 各 profile で依存=同梱∨allow-list | Task 1+2 | `tests/test_profile_referential_integrity.py` |
| 2 穴を RED 捕捉 | 修正前 RED | Task 2 | 同上（full.json から map 除去で実証済み） |
| JNY-07 実修正 | full 同梱で GREEN・install で実出力 | Task 3 | 同上＋`tests/test_profile_checker_parity.py`（e2e） |
| D5 by-design 明示 | allow-list 理由付き | Task 2 | 同上（reason 非空＋rot 検知テスト） |
| ~~README 同期~~ | 不要（full 件数の記載・テストとも無し） | — | — |

## 自己レビュー

- 仕様カバレッジ: 要件の AC 全件に Task を割当済み。
- 曖昧さ: KNOWN_EXTRA_EDGES の build-judge-card→record-test-result は「実 importlib ロード時のみ
  登録」と明記（実装時 grep で確定）。
- 型整合: `_script_deps` 出力 = `set[str]`（rel-path `scripts/X.py`）で統一。
- 境界整合: Task 2 は Task 1 の `_script_deps` を Consumes、一致。

## リスク

- リスク1: ast 抽出が動的 import（importlib）を見逃す → KNOWN_EXTRA_EDGES で明示補完。fail-closed
  方針（判定不能辺は過検出側＝allow-list で明示解消）。
- リスク2: full に map を足すと README count がズレる → Task 4 で同期（count テストが番人）。
- リスク3: 3 点検証の片落ち（pytest 緑でも contract/scaffold で別 FAIL・conf9） → 完了条件で 3 点必須化。
- リスク4: allow-list が「サイレント許容」に堕する → reason 非空テストで明示性を強制。

## 完了条件

- [ ] 全テスト pass（新テスト含む）
- [ ] 3 点検証緑: `python3 -m pytest -q` ＋ `python3 scripts/check_framework_contract.py` ＋
  `python3 scripts/eval_scaffold_smoke.py`
- [ ] full install（tmp）で JNY-07 ヒント実出力・D5 は意図通り field no-op
- [ ] grill-plan / grill-code の全指摘を解消
- [ ] review + qa（本物 B1 drill）+ security ゲート通過（deploy は M で size-exempt）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-28-permission-allowlist-completeness-brainstorm-record.md`
- 要件: なし（internal framework iteration・requirements=[]）

## 問題整理

- 背景: iter51 で安全 read/record 系 10 件を `permissions.allow` に同梱（全プロファイル一律・generate_settings が template の allow を全 profile に配布）。だが読み取り専用 framework スクリプトの一部（`check_reference_drift`/`learnings_search`/`lint_names`）と安全 git-read（`git show`）が漏れ、author は毎イテレーション無意味な確認を浴びる。さらに今後スクリプトが増えても allow に追従する仕組みが無く drift する。
- 判断が必要な論点: 「どのコマンドが auto-allow して安全か」の境界を、安全側に倒しつつ drift しない契約にする。
- 制約条件: (1) **moat 不変** — allow はプロンプト抑制のみ・hook は独立発火（iter51 LEARNINGS conf8）。(2) auto-allow は **read-only（mutate しない／exec sink を持たない）コマンド限定**。(3) **状態変更系・exec gadget・destructive 副形を持つコマンドは allow に入れない**（`record-test-result` は引数コマンドを実行＝iter51 で除外済の exec gadget／`git branch -D` 等）。(4) 全プロファイル一律（profile 別 allow は本 iteration の非スコープ）。

## 推奨アプローチ

- 採用方針: **read-only 完全性ガード＋拡張**。scripts を 3 分類（read_only_cli / mutating_cli / not_cli）した**監査可能な分類表**を持ち、テストで「read_only_cli ⊆ allow ∧ mutating_cli ∩ allow = ∅ ∧ 全 scripts が分類済（未分類＝drift trip）」を強制。併せて allow に read-only スクリプト 3 件＋`git show` を追加。
- 採用理由: read-only は moat 無関係で全員に安全、profile 分け不要、author が今すぐ分類・検証可能、commit oversight の論争を避ける。iter49/50 の参照整合性ガードと同型で durable。
- 検討した代替案と不採用理由: A=平易化（非実在ユーザー・検証不能）。B=profile 別 reversible-write（価値薄・commit oversight と衝突・infra 時期尚早＝延期）。

## コンポーネント分解

- 分割方針: データ（分類表）＋ガード（テスト）＋配布物（allow エントリ）に分ける。production code（hook/scripts ロジック）は無改変。
- 各ユニットの責務:
  - ユニット A（分類表）: `tests/` 内に `scripts/*.py` → `{read_only_cli, mutating_cli, not_cli}` の dict（各エントリに 1 行根拠）。`update-gate.sh`/`update-task.sh` も mutating として明記。
  - ユニット B（完全性ガード）: 分類表と「shipped allow（`templates/hooks.template.json` の `permissions.allow`）」を突き合わせるテスト群。
  - ユニット C（allow 拡張）: `templates/hooks.template.json` の `permissions.allow` に 5 エントリ追加。
  - ユニット D（ドキュメント）: README の allow-list 節（件数・完全性ガードの存在）。

## インターフェース定義

- ユニット間の契約:
  - A → B: 分類表 dict（key=スクリプトのパス名、value=分類 enum）。B は `scripts/` 実体を列挙し A と照合。
  - C → B: allow エントリ列（`Bash(python3 scripts/<name>.py:*)` / `Bash(git <sub>:*)` 形）。B が membership を検証。
- 公開 API: 新規 production API なし。テスト内 helper のみ（例: `_classify_scripts()`, `_shipped_allow()`, `_allow_script_entries(allow)`）。

## データフロー / 構造

- 入力: `scripts/` のファイル一覧＋分類表＋`hooks.template.json` の allow。
- 処理: (1) 全 `scripts/*.py` が分類表に在るか（未分類→FAIL）。(2) read_only_cli の各スクリプトに対応する allow エントリが在るか。(3) mutating_cli のスクリプトが allow に**無い**か。(4) 安全 git-read 固定集合（`git status`/`git log`/`git diff`/`git show`）⊆ allow。(5) rot: allow の各 script エントリが read_only_cli に対応（orphan→FAIL）。
- 出力: テスト pass/fail（drift を赤で検出）。

### 分類（初版・根拠は実装時に静的確認）

- **read_only_cli（allow 必須）**: `check_status.py`, `check_framework_contract.py`, `status_doctor.py`, `retro_report.py`, `build-judge-card.py`（以上 iter51 済）, `check_reference_drift.py`, `learnings_search.py`, `lint_names.py`（**今回追加**）。
- **mutating_cli（allow 禁止）**: `record-test-result.py`（引数コマンドを実行＝exec gadget）, `run-test-strength-drill.py`（mutation 実行）, `run_eval.py` / `eval_scaffold_smoke.py` / `eval_scenario.py`（scaffold/install/exec）, `update-gate.sh`, `update-task.sh`（STATUS 変更）。
- **not_cli（無視＝CLI entrypoint でない）**: `_artifact_template_map.py`, `platform_manifest.py`（import 専用モジュール）。
- **安全 git-read（固定集合）**: `git status`, `git log`, `git diff`, `git show`。`git branch`/`git remote`/`git checkout` は destructive 副形（`-D`/`remove`/`checkout .`）を含むため broad allow から除外。

## 依存関係

- 依存方向: テスト → (分類表データ, `scripts/` 実体, `templates/hooks.template.json`)。循環なし。
- 外部依存: なし（標準ライブラリ・pytest のみ）。

## エラーハンドリング

- 想定失敗: (1) 新スクリプト追加で未分類 → ガードが FAIL し追加者に分類を強制。(2) read-only スクリプトを allow に入れ忘れ → FAIL。(3) mutating/exec スクリプトを誤って allow に入れる → FAIL（安全側 fail-closed）。
- 対応: いずれもテスト赤で検出し、分類表 or allow を直す。
- エラー伝播の方針: 静的テストなので即時赤。fail-closed（疑わしきは mutating 扱いで allow から外す）。

## テスト戦略

- 単体: 分類 helper（列挙・membership・orphan 検出）。
- 結合: 完全性ガード 6 アサーション（上記 (1)〜(5)）。既存 `tests/test_permission_allowlist_install.py` の install e2e がグリーン継続。
- エッジケース: 未分類スクリプト（mutation で 1 件落として赤を確認）、mutating を allow に混入（赤を確認）、orphan allow エントリ（赤を確認）。**B1 drill** 対象（tracked task code の追加ハンクごとに mutant）。
- 手動確認: 本リポ install／local settings に拡張 allow が反映され、対象 read-only スクリプトが無プロンプト化するか（dogfood）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-28-permission-allowlist-completeness-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

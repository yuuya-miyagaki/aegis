# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-25-iter45-setup-arg-version-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（C2 / C3）

## 問題整理

- 背景: `bin/setup.sh` のインストール初期化領域に 2 件の欠陥。
  - **C2**: 引数パーサ（`for arg in "$@"` + `--profile=*` / `--target=*`）が `=` 形式のみ受理。`--profile full`（空白形式）は `*)` に落ちて `ERROR: Unknown argument` で即死。`--target` も同じ穴（H2 実測）。`CLAUDE.md` 散文は `--profile` と書くため doc/impl 不整合。
  - **C3**: FRAMEWORK_VERSION 取得の `python3 - <<'PY' ... PY` がクォート付き heredoc のため `$FRAMEWORK_ROOT` を展開せず、python は常に `FileNotFoundError`（H1b 実測）→ `echo unknown`。直後の grep フォールバックが実値 `1.14.0` を救出（H1 実測）するため**機能影響は現状ゼロ**＝dead first path。
- 判断が必要な論点: パーサを両形式対応にする範囲（profile だけか target も含むか）、C3 を dead path 解消（heredoc 生存）にするか削除にするか。
- 制約条件:
  - 既存 `=` 形式・既存テスト（`test_setup_*`）を壊さない（回帰禁止）。
  - クォート heredoc のインジェクション安全性（外部入力をコードとして評価しない）を維持。
  - bash 3.2 互換（macOS 既定）。`set -euo pipefail` 下で安全。
  - profile 値検証（allowlist）は不変＝攻撃面を増やさない。

## 推奨アプローチ

- 採用方針:
  - **C2**: 引数パーサを `while [ $# -gt 0 ]` + `shift` ループに置換し、各フラグに `--flag=*`（= 形式）と `--flag`（空白形式・次引数を値に取る）の 2 アームを与える。対象は `--profile` と `--target`。`--force` / `-h|--help` / 不明引数は現状維持。値欠落（`--profile` が最終引数）は明示エラー。リポジトリ内の既存実装 `scripts/update-task.sh` と同一スタイルにそろえる（保守一貫性）。
  - **C3**: heredoc を `python3 - "$FRAMEWORK_ROOT/scripts/check_framework_contract.py" <<'PY'` の **argv 渡し**に変更し、body は `sys.argv[1]` を読む。クォート heredoc を維持（インジェクション安全）したまま dead path を解消。grep フォールバックは python3 不在・file/regex miss 用の defense-in-depth として存置。コメントの「heredoc cannot interpolate」記述を実態に更新。
- 採用理由: C2 は実ユーザー価値・North Star 直結・testable。target も直して構造的非一貫を残さない。C3 は argv 渡しなら安全に主経路を生かせ、positive-control test で「python が実際に version を返す」ことを実証でき qa の守った挙動が成立する。
- 検討した代替案と不採用理由:
  - C2 エラーメッセージ親切化のみ → 「ただ動く」より不親切（習慣的に空白形式を打つ層に無力）。
  - C3 heredoc 削除＋grep 正本化 → python 正規表現の頑健性を失う（grep+sed は greedy `.*` で複数クォート行を誤抽出しうる）。

## コンポーネント分解

- 分割方針: 単一ファイル `bin/setup.sh` の 2 つの独立ブロック。相互依存なし。
- 各ユニットの責務:
  - ユニット A（C2 引数パーサ）: `$@` を解釈し `PROFILE` / `TARGET` / `FORCE` を確定。両形式受理。値欠落・不明引数で fail-closed。
  - ユニット B（C3 version 解決）: `FRAMEWORK_ROOT` から FRAMEWORK_VERSION を解決。python 主経路（argv）＋grep フォールバック＋最終 `unknown`。

## インターフェース定義

- ユニット A: 入力 `"$@"` → 出力 環境変数 `PROFILE`(str) / `TARGET`(str) / `FORCE`(bool)。エラー: 不明引数・値欠落で stderr＋`exit 1`。
- ユニット B: 入力 `FRAMEWORK_ROOT`(path) → 出力 `FRAMEWORK_VERSION`(str, 非空。最終 `unknown` 保証)。
- 公開 CLI 契約（不変）: `bin/setup.sh --profile=<p> --target=<d> [--force]` は引き続き有効。**追加**で `bin/setup.sh --profile <p> --target <d>` も有効。

## データフロー / 構造

- 入力: コマンドライン引数。
- 処理: A でパース → profile allowlist 検証（不変）→ B で version 解決 → 各種 copy → stamp 書込み。
- 出力: install 先ファイル群＋`.claude/.aegis-install-version`（実 version）。

## 依存関係

- 依存方向: A → （profile 検証）→ B → copy/stamp。循環なし。
- 外部依存: `python3`（既に prereq 検査済み・K-10）、`bash`、`git`（baseline は best-effort）。新規依存なし。

## エラーハンドリング

- 想定失敗:
  - `--profile` 値欠落（最終引数）→ `ERROR: --profile requires a value`（または既存の `--profile is required`）で `exit 1`。
  - 不明引数 → 既存どおり `ERROR: Unknown argument: <arg>` で `exit 1`。
  - python3 不在/壊れ → K-10 が冒頭で abort（B には到達しない）。B 内の python miss は grep フォールバック。
- エラー伝播の方針: fail-closed（不正引数で install を始めない）。version は最悪 `unknown`（status_doctor が後で警告）。

## テスト戦略（RED-first）

新規テストファイル: `tests/test_setup_arg_version.py`

- 単体/結合（C2・実 `bin/setup.sh` を temp `--target` で実行）:
  - 回帰: `--profile=minimal --target=<tmp>` → rc 0（既存 `=` 形式）。
  - **新規 RED**: `--profile minimal --target <tmp>`（両空白形式）→ rc 0・stamp 生成。修正前は `Unknown argument` で rc≠0。
  - 新規 RED: 混在 `--profile minimal --target=<tmp>` → rc 0。
  - 新規: `--profile`（値なし・最終引数）→ rc≠0・「value/required」を含むメッセージ。
  - 回帰: `--bogus` → rc≠0・`Unknown argument`。
- 単体（C3）:
  - **静的 RED**: `bin/setup.sh` の version heredoc が `sys.argv` を参照し、クォート heredoc body 内に `$FRAMEWORK_ROOT` を含まない（dead path 除去の直接証明）。修正前は body に `$FRAMEWORK_ROOT` を含むため RED。
  - 回帰: install 後 `.claude/.aegis-install-version` が実 version（既存 `test_install_writes_version_stamp` と重複しない範囲で）。
  - **positive-control RED**（python が主経路として実値を返すことの実証）: temp に framework root を複製し、`scripts/check_framework_contract.py` の `FRAMEWORK_VERSION` 行を **grep フォールバックが取りこぼす形**（例: 行頭非アンカー＝先頭インデント）に改変。複製 setup.sh を実行し stamp を確認。修正前: python dead → grep も miss → stamp=`unknown`（RED）。修正後: python が `re.search`（非アンカー）で実値抽出 → stamp=実値（GREEN）。複製範囲は plan で確定（bin/hooks/scripts/templates/.claude の framework-owned 最小集合・minimal profile）。
- エッジケース: `--profile ""`（明示空値）→ 既存 `-z PROFILE` 検査で `required` エラー。`--profile --target=/x`（値取り違え）→ profile allowlist で `Invalid profile`。
- 手動確認: `bash -n bin/setup.sh`、`bin/setup.sh --profile full --target /tmp/aegis-smoke` の実走（空白形式 smoke）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-25-iter45-setup-arg-version-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- `bin/setup.sh` の C2（引数パーサが `=` 形式のみ）と C3（FRAMEWORK_VERSION heredoc の dead first path）を修正し、(a) `--profile`/`--target` を `=` と空白の両形式対応にし、(b) version 解決の python 主経路を argv 渡しで実際に機能させる。

## 入力

- 参照要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（C2 / C3）
- 参照設計: `docs/specs/2026-06-25-iter45-setup-arg-version-design.md`

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（ローカル installer スクリプトの修正。デプロイ先なし）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a（Node/Next アプリではない）
- 上記がデプロイ先と互換であることを確認: Yes（該当なし）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

> 補足: task_type=framework・task_size=M。M は deploy gate を size-exempt（SIZE_ALLOWED_PHASES）。本変更は installer のローカル挙動のみで deploy 相互作用なし。

## Git 戦略

- 未定義のため既定: main へ直接コミット（過去 iteration と同様の単一コミット運用）。push は `gh auth switch --user yuuya-miyagaki` 後に origin/main へ。

## ファイル構造（変更マップ）

- 変更: `bin/setup.sh:44-58`（引数パーサ）— `for arg in "$@"` を `while [ $# -gt 0 ]` + `shift` に置換し、`--profile`/`--target` に `=*` と空白の 2 アームを付与。`--force`/`-h|--help`/不明引数は挙動維持。値欠落は決定的メッセージ `ERROR: --profile requires a value` / `ERROR: --target requires a value` で `exit 1`。**parser に意図コメント必須**（grill-plan 致命2）: `# C2: accept both --flag=val and --flag val forms (CLAUDE.md prose uses the space form). Do not collapse back to =-only.` ——3 年後に dead arm と誤認され `=`-only へ戻される回帰を防ぐ。
- 変更: `bin/setup.sh:100-112`（version 解決）— heredoc を `python3 - "$FRAMEWORK_ROOT/scripts/check_framework_contract.py" <<'PY'` の argv 渡しにし body は `sys.argv[1]` を read。コメント（107-108）を実態に更新。grep フォールバックは存置。
- 新規テスト: `tests/test_setup_arg_version.py` — C2（両形式・回帰・値欠落・不明引数）と C3（静的 dead-path 除去・positive-control・回帰 stamp）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 (C2) | 両形式対応パーサ（PROFILE/TARGET/FORCE 確定） | なし |
| Task 2 (C3) | argv 渡し version 解決（FRAMEWORK_VERSION 非空） | なし |

循環なし。両タスクとも `bin/setup.sh` の独立ブロックを変更（同一ファイル＝逐次実行・並列禁止）。テストファイルは共有（新規）。

## タスク分解

> 同一ファイルを変更するため逐次。各タスク RED-first TDD。サイズが小さく文脈共有が有利なため**親セッションで実装**（subagent 分離は不要・routing 原則「subagents only when clearer/safer/smaller」）。

### タスク 1: C2 引数パーサ両形式対応

**blockedBy:** なし | **モデル:** in-session
**ファイル:** 対象 `bin/setup.sh:44-58` / テスト `tests/test_setup_arg_version.py`
**意図:** `--profile full` / `--target /dir`（空白形式）を `=` 形式と同様に受理。値欠落・不明引数は fail-closed。
**TDD:**
1. テスト先行（RED）: `--profile minimal --target <tmp>` → rc 0; 混在 `--profile minimal --target=<tmp>` → rc 0; `--profile`（値なし最終）→ rc≠0 + value/required; `--bogus` → rc≠0 + Unknown argument; 回帰 `--profile=minimal --target=<tmp>` → rc 0。修正前は空白形式が "Unknown argument" で RED。
2. FAIL 確認 → `while`+`shift`+2 アーム実装 → PASS 確認。
**受入条件:** 上記全ケース緑。既存 `test_setup_*.py` 全緑（回帰なし）。
**Deliverable:** [ ] 両形式受理 [ ] 値欠落/不明引数 fail-closed [ ] テストカバー

### タスク 2: C3 version heredoc argv 渡し

**blockedBy:** Task 1（同一ファイル＝逐次） | **モデル:** in-session
**ファイル:** 対象 `bin/setup.sh:100-112` / テスト `tests/test_setup_arg_version.py`
**意図:** dead first path（クォート heredoc 内 `$FRAMEWORK_ROOT` 非展開）を argv 渡しで解消し、python 主経路を実際に機能させる。grep フォールバックは存置。
**TDD:**
1. テスト先行（RED）:
   - 静的: `bin/setup.sh` の唯一の `<<'PY' ... PY` ブロックが `sys.argv` を含み `$FRAMEWORK_ROOT` を含まない。修正前は body に `$FRAMEWORK_ROOT` で RED。
   - positive-control: 最小 fake framework root（`bin/setup.sh` コピー＋`templates/profiles/minimal.json` コピー＋`scripts/check_framework_contract.py` を**先頭インデント版** `    FRAMEWORK_VERSION = "9.9.9-pytest"` に改変＝grep `^` アンカーが取りこぼし python 非アンカー `re.search` は拾う）を組み、コピー setup.sh を `--profile=minimal --target=<proj>` で実行。**判定は 3 点 assert（grill-plan 致命1）**: `rc == 0` ∧ stamp ファイル存在 ∧ 内容（修正前 `unknown`／修正後 `9.9.9-pytest`）。3 点にするのは「setup が別要因で途中 abort→stamp 不在」という別経路の赤を「unknown による赤」と取り違えないため。**テスト docstring に brittle 結合を明記（grill-plan 要検討1）**: 先頭インデントは `grep -E '^FRAMEWORK_VERSION'` の `^` アンカーを外して python の非アンカー `re.search` だけに値を拾わせる仕掛けであり、fallback の実装に意図的に結合している旨を残す。修正前: python dead→grep miss→`unknown`（RED）。修正後: python が argv で拾う→`9.9.9-pytest`（GREEN）。
   - 回帰: 実 `bin/setup.sh` で install 後 stamp == 実 version（`1.14.0`）。
2. FAIL 確認 → argv 渡し実装＋コメント更新 → PASS 確認。
**受入条件:** 静的・positive-control・回帰すべて緑。
**Deliverable:** [ ] heredoc argv 化 [ ] python 主経路が実証可能 [ ] grep フォールバック存置

## 事前準備

- [x] python3 / bash あり（既存環境）
- [x] ベースブランチ最新（origin/main=77383ff、working tree clean）
- [x] 外部サービス・API キー不要

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| C2（空白形式即死） | 両形式受理・fail-closed 維持 | Task 1 | `tests/test_setup_arg_version.py` |
| C3（dead first path） | python 主経路が実値を返す・回帰なし | Task 2 | `tests/test_setup_arg_version.py` |

## 自己レビュー

- 仕様カバレッジ: C2/C3 とも Task とテストあり。
- 曖昧さ: 「両形式」= `--flag=val` と `--flag val` の両方。`--force` は値なしフラグのまま。
- 型整合性: PROFILE/TARGET/FORCE のシェル変数名は既存と一致。
- 境界整合性: 両タスク Consumes なし。

## リスク

- リスク R1: パーサ書き換えで既存 `=` 形式が回帰。→ 対策: 回帰テスト（`--profile=minimal`）＋既存 `test_setup_*` 全実行。
- リスク R2: `shift 2` が値欠落（最終引数 `--profile`）で `set -e` 下に意図せず abort。→ 対策: `${2:-}` で先に空取得し `shift 2 || { err; exit 1; }` で明示処理（update-task.sh と同型）。
- リスク R3: positive-control の fake root が minimal profile の必須ソース欠落で setup を abort させる。→ 対策: 欠落ソースは copy_file が SKIP するだけで setup は rc 0 完走（K-10 は python3 破損時のみ abort）。profile JSON と check_framework_contract.py のみ用意すれば stamp は書かれる。実装時に rc を assert して確認。
- リスク R4: 静的テストが `<<'PY'` ブロック境界を誤抽出。→ 対策: setup.sh の `<<'PY'` は version 解決の 1 箇所のみ（他は `python3 -c`）。一意抽出可。実装時に grep で一意性を確認。

## 完了条件

- [ ] 新規テスト（C2/C3）緑 + 既存 `test_setup_*` 回帰なし
- [ ] **full pytest 実行 → `record-test-result`**（grill-plan 要検討3: qa judge は newest test-runner entry の marker_verified を読むため、record で `marker_verified` を残す。罠 e）
- [ ] `bash -n bin/setup.sh` OK
- [ ] 空白形式 smoke: `mktemp -d` 配下を `--target` に `bin/setup.sh --profile full --target <tmpdir>` で実走し、終了後 `rm -rf`（grill-plan 要検討4: /tmp 残骸を残さない）
- [ ] レビュー完了（review/qa/security gate）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

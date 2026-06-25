# iter45 Review Report — C2 setup arg parser / C3 version heredoc

- 日付: 2026-06-25
- 対象: full-review C2（`bin/setup.sh` 引数パーサを `=`/空白の両形式対応）＋ C3（FRAMEWORK_VERSION heredoc の dead first path を argv 渡しで解消）
- task_type/size: framework / M（review+qa+security 必須・deploy は size routing で exempt）
- 参照: spec `docs/specs/2026-06-25-iter45-setup-arg-version-design.md` / plan `docs/plans/2026-06-25-iter45-setup-arg-version-implementation-plan.md`

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | C2 引数パーサ両形式対応 ＋ RED-first テスト | `bin/setup.sh`（parser を while+shift・`[ $# -ge 2 ]` guard 化）／`tests/test_setup_arg_version.py`（新規） | 実装済 | RED 実測（5 fail）→GREEN |
| 2 | C3 version heredoc argv 渡し ＋ static/positive-control/回帰テスト | `bin/setup.sh`（version block）／同テスト | 実装済 | positive-control RED（`0.0.0-grepwrong`）→GREEN（`9.9.9-real`） |

`git diff --name-only`: `bin/setup.sh`（変更）／`tests/test_setup_arg_version.py`（新規・untracked）。plan の全 Task 実装済・未着手なし。

## Evidence Checklist

- [x] diff 実読（parser ループ・version block・テスト全体）
- [x] plan/spec 受入条件と突合（両形式・fail-closed・injection 安全・grep フォールバック存置・dead path 解消）
- [x] RED-first 実測（13 tests・full suite 1115 passed/1 skip）
- [x] 全 finding に severity ＋ confidence 付与・解消/受容を記録

## 盲検 第2意見（self-attested）

1次（本セッション構造化レビュー＋grill-code）確定後、verdict 非共有・fresh context（変更概要＋spec/plan のみ）で 2 エージェントを独立ディスパッチ。両者は **fix 前 diff** をレビューし、findings を全て fix に反映（その後 phase-level で再検証）。

### reviewer-testing（approve_with_notes 相当）

- **[F1, critical, conf 8] C3 positive-control の false-green 耐性** — 解消済。「python 成功時は grep アームが skip されるため、grep が誤値を返すという discriminator が steady-state で実行されず、将来 fixture が変質すると false-green 化しうる」。→ テストに **grep+sed パイプライン単独実行**を追加し、doctored fixture で必ず `0.0.0-grepwrong`（誤値）を返すことを self-validate。discriminator が live であることを証明。
- **[F3, major, conf 8] value-mistake（`--profile --force`）未テスト** — 解消済。`test_profile_consumes_flag_lookalike_then_fails_validation` 追加（allowlist で `Invalid profile` ＝fail-closed を担保）。
- **[F2, major→minor, conf 7] `--profile ""`（明示空値）未テスト** — 解消済。`test_profile_explicit_empty_value_fails_closed` 追加（fail-closed）。
- **[F5, minor, conf 7] `--help` の空白形式ヒント未担保** — 解消済。`test_help_exits_zero_with_usage` に `space form` の assert 追加。
- **[F4, minor, conf 7] `--force` テストが再 install 効果を未検証** — 受容。本テストの目的は parse/no-hang guard（grill-code 🟡）であり、FORCE の上書き意味論は C2 スコープ外（既存挙動・変更なし）。

### reviewer-maintainability（approve_with_notes 相当）

- **[M2/m2, major, conf 8] `shift 2` 終了コードの bash 版依存** — 解消済。「`shift N>$#` の終了コードは bash 版で差がありうる（4+ で 0 の主張）。`|| {...}` guard が inert 化すると `--profile` 値欠落時のメッセージが非決定的」。→ **shift 終了コード依存を撤廃**し、明示 `[ $# -ge 2 ]` guard に置換。bash 3.2/4/5 で「requires a value」を決定的に保証（実測未確認の版差に依存しない堅牢化）。コメントも更新。
- **[M1, major, conf 9] flag-lookalike（`--profile --force`）を値に取る** — 受容＋テスト化。getopt 慣行・spec 許容挙動（`Invalid profile` で fail-closed）。F3 のテストで担保。
- **[m1, info, conf 9] C3 injection 安全性** — 独立確認。`<<'PY'`（quoted heredoc）で body は非展開、path は `sys.argv[1]` の data として渡り `pathlib.Path.read_text` で評価されない。injection ベクタなし。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["reviewer-testing(approve_with_notes): F1 false-green→grep-discriminator self-validation 追加／F3 value-mistake・F2 empty・F5 help-hint テスト追加／F4 受容(scope)", "reviewer-maintainability(approve_with_notes): M2 shift 版依存→明示 [ $# -ge 2 ] guard 化／M1 flag-lookalike 受容+テスト／m1 injection 安全を独立確認"]
```

## 判定

**PASS。** Critical 0。盲検 2 次（reviewer-testing / reviewer-maintainability）とも approve_with_notes・verdict 一致。全 finding を承認前に反映（F1 self-validation／M2 portability guard／F2-F5 テスト追加）または scope 受容（F4）。実装は spec/plan の受入条件を満たし、C3 は injection 安全・grep フォールバック存置、C2 は両形式 fail-closed・決定的メッセージ。13 tests・full suite 1115 passed/1 skip。

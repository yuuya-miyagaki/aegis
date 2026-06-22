# iteration 39 plan — check-gate.sh テスト分離バグ修正（framework・M・test-only）

## 背景・根本原因（bug-diagnosis 済）

`tests/test_failure_policy.py::test_python3_absent_behavior` の `check-gate.sh` シナリオが
潜在的なテスト分離バグを持つ。`check-gate.sh:24` は
`ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"` で root をハードコード解決し、
`AEGIS_ROOT_OVERRIDE` も `cwd` も見ない。よって python3 不在フォールバックは
**実リポの STATUS** を読む。テストは scratch に `FEATURE_STATUS`（plan:approved）を
書くが使われず、実 STATUS の plan が approved/n/a の間だけ「運頼みに pass」する。
iter38 rollover で実 plan=pending になった瞬間に deny→fail で露出した。iter36 Bug-B
（hook ごとに root 解決が違う／その hook が実際に使う変数で分離せよ）と同クラス。

## スコープ

- **test-only**。本番 hook（`check-gate.sh`）は変更しない。
- `check-gate.sh` シナリオを `_scenarios()` ループ（実 hook 発火）から外し、
  `check-control-plane.sh` の専用メソッド（`test_failure_policy.py:196-212`）と同型に、
  hook を temp-root へ **copy**（lib も copy。symlink は os.chmod 追従＝iter36 Bug A 回避）
  して発火する専用メソッドを追加する（`ROOT=scratch` になり scratch STATUS を読む）。

## サイズ判定（M の理由）

実質 1 ファイル（`tests/test_failure_policy.py`）。ただし framework 内部の `tests/` 編集は
`check-gate` の plan ゲート承認を要し（`tests/` は control-file allowlist 外）、S には
plan フェーズが無い。plan フェーズを持つ M とする（bugfix は plan=n/a で編集可だが moat
施錠でスイートが壊れる＝framework が正分類）。framework につき review+qa+security 必須
（M は deploy skip／qa は test-only で skip-drill・security は無サーフェス）。

## タスク

| # | タスク | ファイル |
|---|--------|---------|
| 1 | `check-gate.sh` を `_scenarios()` から外し、理由コメントを残す | `tests/test_failure_policy.py` |
| 2 | 専用メソッド `test_python3_absent_check_gate_reads_scratch_status` を追加（temp-root copy・lib copy・両極 approved→allow／pending→deny で scratch 追従を実証） | `tests/test_failure_policy.py` |

## 検証

- `test_failure_policy.py` 単体 green（新メソッド含む）。
- full suite green（moat 解錠下）。
- 強度: 両極アサート（pending→deny）が「scratch を読む」ことを直接固定＝実 STATUS 非依存。
  旧方式（実 hook・実 STATUS 読み）なら pending 極で実 plan に依存し FAIL ＝バグを捕捉。

## ゲート

framework・M: review + qa（test-only につき skip-drill＋本プランの両極実証で代替）+ security
（無サーフェス）必須。deploy は M で size-skip。

# iteration 36 — テスト分離バグ修正（bugfix・S）

> iteration 35 で発見した follow-up。task_type=framework（framework 自体の修正＝moat が
> framework 編集を許す型。bugfix 型は moat が framework コード編集をブロックするため使えない＝
> 本件自体が framework の知見）。size=S・review のみ必須（qa/security/deploy は短絡可）。

## 根本原因（systematic-debugging で特定）

- **症状**: full suite 実行後、実リポの `scripts/check_status.py` がモード 644→700 に変化し、
  fingerprint（scripts/ を含む）が揺れて iteration 35 のゲート運用を繰り返し妨げた。
- **conftest 計測で特定**: `tests/test_phase_skills_lib.py::TestSessionStartInjection`
  （`_scaffold` 行94）が実 `scripts/check_status.py` を scratch `d/scripts/` に **symlink**。
- **当初の仮説（誤り）**: 「cp-lock の `chmod -R` が symlink を辿る」と推測したが、
  **直接プローブで反証**——`chmod -R` は symlink を辿らない（BSD -P 既定）。`cp-lock.sh` は無罪。
- **実際の機序（直接プローブで確証）**: `task_type: feature` の scratch で session-start が
  `aegis_cp_lock` を起動 → scratch を `chmod -R a-w`（**正しい lock 動作**）→ テストの
  `with TemporaryDirectory()` 終了時の `rmtree` が locked dir で `PermissionError` →
  **Python の `resetperms` onerror ハンドラが `os.chmod(path, 0o700)` を実行し、`os.chmod` は
  symlink を辿る** → symlink `d/scripts/check_status.py` 経由で**実ファイルを 0o700 に変更**。
  （単発 _run では再現せず：私の repro は cleanup 前に unlock していたため。クラス実行で
  unlock せず cleanup→resetperms が発火して再現。）

## 修正

**テスト側の分離違反を正す**（cp-lock は変更しない）:
`tests/test_phase_skills_lib.py::_scaffold` 行94 の **symlink → copy**（`shutil.copy2`）。
これで lock された scratch の cleanup（resetperms）が chmod するのは**コピー**であり、実ファイルは
不変。session-start の lock 動作自体は正しいので変更しない。

- 他の symlink 利用テスト（test_check_status:359 が scripts/ 丸ごと・test_control_plane_* が
  hooks/lib）は **session-start/cp_lock を起動しない**＝scratch が lock されない＝resetperms が
  発火しない＝漏れない。本件は「symlink＋scratch lock＋cleanup 前 unlock 無し」の3条件が揃う
  test_phase_skills のみ。

## テスト（TDD）

- `test_scaffold_check_status_is_regular_file_not_symlink`（新規・回帰ガード）:
  `_scaffold` が `scripts/check_status.py` を **symlink でなく実ファイル**として置くことを固定。
  RED（symlink→is_symlink True）→ GREEN（copy）。
- 検証: `test_phase_skills_lib.py` 実行後・full suite 実行後に実 `scripts/check_status.py` の
  モードが**不変（644）**になること。

## ゲート

S・framework 型: **review 必須**。qa/security/deploy は tiny fix のためユーザー判断で短絡可。
push は yuuya-miyagaki。

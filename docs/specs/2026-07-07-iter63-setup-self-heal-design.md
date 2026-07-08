# 設計ノート — iter63: setup.sh self-heal unlock（R3）

## 入力

- 要件: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R3・§4 Phase 0-3
- 実再現（2026-07-07 本セッション）: standard install → framework-owned hook を stale 化 →
  `aegis_cp_lock` → `bin/setup.sh` 再実行 = **rc=1・`cp: hooks/check-gate.sh: Permission denied`・
  原因説明ゼロ・stale hook 残置（mixed-version）**。
- 追加の発見（設計・テスト両方に効く）: **同一内容の再 install は死なない**。
  `copy_file_force` の `cmp -s` が cp 前に no-op return するため、故障は
  「配布物に差分がある実 upgrade」でのみ顕在化する。既存 upgrade テスト
  （test_setup_upgrade_overwrite.py）が未 lock target でしか走らないことと合わせ、
  回帰テストは **stale 化→lock→再実行** の順で組む必要がある。

## 問題整理

- 背景: cp-lock（moat layer-2）は session-start で非 framework task_type の install を
  `chmod a-w`（永続）する。`bin/setup.sh` は `set -e`＋`cp -f` で、locked target への
  正規 upgrade が必ず途中 abort する。status_doctor 自身が「Re-run bin/setup.sh」と
  案内するのに、その手順が「一度でも使った install」全てで失敗する。
- 死に方の内訳（いずれも unlock で解ける）:
  1. 既存 framework-owned ファイルへの `cp -f`（a-w ファイル）→ Permission denied
  2. 新規配布ファイルの `mkdir -p`／cp（a-w ディレクトリ）→ 新規作成不可
  3. `.bak` 退避の cp（a-w ディレクトリ内への新規作成）→ `|| true` で黙殺され退避なし
- 制約条件:
  - unlock 実装は `hooks/lib/cp-lock.sh` が単一正本（第2実装を生やさない）。
  - `set -euo pipefail` 下で `aegis_cp_verify`（findings=rc1）と `aegis_cp_unlock`
    （部分失敗=rc1）が abort を誘発しない受け方にする。
  - `--target` は任意のディレクトリを指せる。**aegis install でない**ディレクトリの
    perms を installer が勝手に書き換えてはならない（hooks/ や scripts/ は一般的な
    ディレクトリ名で、ユーザーが意図して read-only にした無関係ファイルがあり得る）。
  - explain-oslock-eacces.sh の在世界観「エージェントは chmod で self-repair しない」と
    整合させる: unlock は *sanctioned flow*（installer 内部）に限定し、出力で可視化する。

## 推奨アプローチ（A: 冒頭 self-heal＋帰属エラー＋opt-out seam）

- 採用方針:
  1. **self-heal unlock**: setup.sh 本処理前に、(a) target が aegis install
     （`.claude/.aegis-install-version` または `hooks/lib/cp-lock.sh` が存在）かつ
     (b) `aegis_cp_verify <target> framework` が non-writable CP path を検出したときのみ、
     framework 側 `hooks/lib/cp-lock.sh` を source して `aegis_cp_unlock <target>`。
     実施時は NOTE を出力（「unlock した・再 lock は次回 session start」）。
  2. **再 lock はしない**（次回 session-start の `aegis_cp_apply` 任せ）。
     NOTE で明示するので silent ではない。
  3. **lock 帰属エラーメッセージ**: `copy_file` / `copy_file_force` の
     `mkdir -p`・`cp` 失敗時に、dst（または親 dir）が non-writable なら
     「aegis OS-lock（cp-lock）由来の可能性・self-heal の再実行/手動 unlock 手順」を
     stderr に出して exit 1（従来は cp の生 stderr のみで即死）。
  4. **`AEGIS_SETUP_SELFHEAL=off` seam**（既定 on・lowercase off のみ、AEGIS_NUDGE と
     同慣習）: off なら unlock せず従来挙動＝locked target では帰属エラーで fail-closed。
     テストの決定論的経路にもなる。
- 採用理由: unlock の正本再利用（SoT）・発火条件を「aegis install かつ実際に locked」に
  絞ることで無関係ディレクトリへの副作用ゼロ・失敗時も必ず説明つき fail-closed。
  status_doctor の「Re-run bin/setup.sh」案内が全 install で真になる。
- 検討した代替案と不採用理由:
  - **B: setup.sh 末尾で re-lock まで行う**: target の STATUS.md/frontmatter 読解が
    installer に入る（結合増）。lock 窓は「次回 session-start まで」だが、layer-2 の
    脅威モデルは偶発書込み防御であり、窓の残余リスクは小。full-review の修正方向も
    「再 lock は次回 session-start 任せ」。→ 不採用（YAGNI）。
  - **C: unlock せず帰属エラーのみ（手動 unlock 誘導）**: 正規 upgrade が手動2ステップの
    ままで、R3 の核（正規手順が死ぬ）が残る。→ 不採用。
  - **D: cp 失敗時に per-file `chmod u+w` リトライ**: locked ディレクトリでの新規ファイル
    作成（死に方2）を解けず、cp-lock と別の第2 unlock 実装が生える（SoT 違反）。→ 不採用。

## コンポーネント分解

- ユニット1（self-heal）: `bin/setup.sh` に `selfheal_unlock_target()` を追加し、
  main の「--- Required files ---」前に呼ぶ。
  - ガード順: env off → return（黙）／ aegis マーカーなし → return（黙）／
    framework 側 cp-lock.sh 不在 → WARNING して return（後段の帰属エラーが安全網）／
    `locked=$(aegis_cp_verify "$TARGET" framework)`（`set -e` 対策で `|| true` 受け）が
    空 → return（黙）。
  - 実施: `aegis_cp_unlock "$TARGET"` 成功 → NOTE 2行（unlock 済・次回 session start で
    再 lock）。失敗（rc1）→ WARNING（以降の copy が失敗し得る旨）で続行
    （cp-lock ヘッダの「failure is NON-fatal」慣習に一致。実害は帰属エラーで顕在化）。
- ユニット2（帰属エラー）: `bin/setup.sh` に `explain_unwritable_dst()` を追加。
  `copy_file` / `copy_file_force` の `mkdir -p` と `cp` を `if ! …; then explain; exit 1; fi`
  型に変更（`set -e` の即死を説明つき abort に置換。cp 自身の stderr は残す）。
  メッセージ核: 対象 path／non-writable の帰属（dst or 親 dir）／「aegis OS-lock
  （cp-lock）の可能性」／self-heal が skip された場合の再実行（env を外す）／
  手動 unlock（`source hooks/lib/cp-lock.sh; aegis_cp_unlock <target>`）。
- ユニット3（回帰テスト）: `tests/test_setup_locked_target_upgrade.py`（新規）。
  - T1 locked-upgrade self-heal: install → framework hook を stale 化 → lock →
    再 install = rc0・hook がソースと一致（mixed-version 解消）・`.bak` 生成・
    NOTE token 出力・target は unlock のまま（再 lock しない設計の pin）。
  - T2 fresh install: NOTE 非出力・rc0（無関係経路に副作用なし）。
  - T3 opt-out fail-closed: stale 化＋lock＋`AEGIS_SETUP_SELFHEAL=off` → rc≠0・
    stderr に帰属 token（`cp-lock` / `AEGIS_SETUP_SELFHEAL`）。
  - T4 non-aegis 不介入: aegis マーカーのない dir に read-only `hooks/` を置いて
    install → rc≠0（帰属エラー）・**dir の perms は不変**（unlock されていない）。
  - 各テストは teardown で `chmod -R u+w` 復旧（pytest tmp_path の後始末を壊さない）。
- ユニット4（簿記）: CHANGELOG/README 等の bump は ship フェーズ（従来どおり）。

## エラー処理・エッジケース

- `aegis_cp_verify` は findings 時 rc1: 代入は `|| true` で受け、判定は出力の非空で行う。
- symlink: cp-lock 側で `! -type l` 済み（verify/unlock とも）— setup 側に追加考慮なし。
- 部分 lock（iter40 の half-locked 状態）: verify は全列挙なので検出・unlock は全走査で復旧。
- `--force` 経路（user-owned CLAUDE.md = CP-locked かつ user-owned）: unlock 後は
  `.bak` → cp とも成功。unlock 前に死ぬ場合も帰属エラーで説明される。
- ジェネリック cp 失敗（dst がディレクトリ等・writable）: 帰属句なしの ERROR のみ
  （誤帰属しない）。

## セキュリティ考慮（先出し）

- unlock は「aegis install マーカー＋実 lock 検出」の AND でのみ発火し、対象は
  cp-lock 正本の CP path 集合に限定（任意 path を触らない）。
- エージェントが target セッション内で framework clone の setup.sh を実行して moat を
  外す経路は**残余として受容**: layer-2 の脅威モデルは偶発書込み防御であり、意図的
  多段バイパス（任意スクリプト実行）は元々 scope 外。owner の `chmod u+w` が常に可能な
  ことと等価。NOTE 出力で可視・監査可能。explain-oslock-eacces の「chmod するな」文言は
  エージェントの self-repair 抑止であり、installer 内部の sanctioned unlock とは別物。
- `AEGIS_SETUP_SELFHEAL=off` は機能を**減らす**方向（locked で fail-closed）のみで、
  バイパス lever にならない。

## 互換性・バージョン

- 既存挙動の互換: 未 lock target への install/upgrade は出力含め不変（NOTE は lock 検出時
  のみ）。fresh install 不変。既存テスト（setup 系 8 ファイル）は無改変で green を維持する。
- バージョン: v1.23.0 → **v1.24.0（MINOR）**。効果は「パッチ級」だが、env seam と
  新出力（NOTE/帰属エラー）という運用面の追加があるため MINOR を採る。

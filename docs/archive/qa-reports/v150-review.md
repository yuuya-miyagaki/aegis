# v1.5.0 E1 activity verification — review エビデンス（2026-06-11）

対象: E1 activity verification 全 13 タスク＋grill-code 修正 4 件（v1.4.0..HEAD、19 commits）
出典: docs/specs/2026-06-10-e1-activity-verification-design.md、docs/plans/2026-06-10-e1-activity-verification-implementation-plan.md
方式: 2段グリル実装段（grill-code）。独立サブエージェント 2 本（①正当性・セキュリティ視点／②テスト強度・配布経路視点）で差分全体（42 files, +3188/−224 時点）を file:line 裏取り付きで精査。

## レビュー結果

判定: **マージ可**（修正後 Critical ゼロ）。🔴1件・🟡4件は同セッションで全て修正済み:

| ID | 指摘 | 対応 |
|----|------|------|
| 🔴-1 | `core.quotepath`（既定 on）で非ASCIIファイル名が octal-quote され `cat` 失敗→定数をハッシュ→**内容を変更しても fp 不変＝silent green**（temp repo で FP1==FP2 を実証）。日本語圏が対象の本ハーネスでは自然発生 | **修正済み**（c523894）。全 git 呼出しに `-c core.quotepath=off`。なお quote されたままの名前（制御文字等）・読取不能ファイルは `error` トークンへ fail-closed。非ASCII名の内容変更で fp 変化・docs 除外維持をテストで固定 |
| 🟡-1 | fingerprint のハッシュ入力が rel＋content の無区切り連結で、異なるツリーが同一入力に衝突（`{B:"bfoo"}`=={B:"b",f:"oo"} を実証）。記録時と承認時のツリー細工で green 持ち越しが可能 | **修正済み**（c523894）。`f:<bytes>:<rel>\n<content>\n`（削除は `d::<rel>\n`）の長さプレフィックス framing 化。境界衝突耐性・削除検知をテストで固定 |
| 🟡-2 | 参照インストール（examples/minimal-project）の settings.json に observer 未登録＝観測系が永久に死に判定が常時 🟡。さらに E1 の 3 ファイルが REQUIRED_EXAMPLE_FILES 外で、example 側を削除しても contract/drift が通過 | **修正済み**（82992a1）。observer 登録＋contract presence 3 件追加＋template==example 配線パリティの恒久テスト新設 |
| 🟡-3 | scaffold smoke が成功側 observer のみ実発火。失敗記録（post-bash.sh）が install 先で死ぬと「最新 fail 未記録→同一 fp の古い ok が green」＝**偽 green 方向**で F6 教訓（実発火検証）に反する | **修正済み**（03e047d）。smoke が post-bash.sh を実発火し `"status":"fail"` 追記を assert（standard/full） |
| 🟡-4 | 「観測した ok が green になる」主契約の結合テスト不在。書き手（evidence.sh）が誤った root の fp を計算する変異が全テストを生存し、本番で恒久 🟡＝green 認証の静かな無力化 | **修正済み**（4518012）。hook 実発火→judge 判定の e2e（green/red/コード変更後 unverified）。fire() の cwd≠記録 root のため誤 root 変異はここで落ちる |

🟢（任意・未対応で記録、詳細は v150-security.md）:

- 失敗側の false-RED: 非テスト目的の `grep vitest package.json`（rc=1）等が分類一致で fail 記録→judge 🔴。実テスト再実行で回復可・fail-closed 方向
- 観測 hook が毎 Bash 実行で git diff＋変更ファイル読込（AEGIS_FP_MAX_FILES=200 / MAX_BYTES=10MB で有界）— ホットパスコスト
- cmd 500 字切詰め・制御文字混入・python3 不在時の `\"` 含むコマンドは いずれも unverified 方向（fail-closed、偽装には使えない）
- `read_test_result` の newest-stale 優先（古い fresh ok へ遡らない）は 4518012 でピン留め済み
- judge の stale-fp `return` を `continue` に変異しても落ちないケースは同コミットの順序ピンで封鎖

## 仕様との整合性

設計ノート・実装計画の全 13 タスクに対応実装を確認。設計逸脱 2 件（out_sha→payload_sha／fingerprint の HEAD 比＋HEAD sha 混入）はユーザー承認済みで spec に注記同期済み（9bd0a76）。`echo pytest` 型の cmd 文字列偽装は計画 §552 で明示許容（記録経路の防御は check-control-plane の責務）＝所見対象外。

## よく書けている点

- 記録=fail-open／判定=fail-closed の二段構えが全経路で一貫（append/rotate は常に rc=0・`|| true`、読み手は 64-hex 必須・token==token 認証不能）
- HEAD sha 混入（grill-plan 🔴1）が `test_new_commit_changes_fp_even_when_tree_clean` で恒久固定
- bash/python 二重実装の排除: judge の `current_fingerprint` は fingerprint.sh サブプロセス委譲（ハッシュ drift が構造的に不可能）
- ミラー契約: 変更 9 ファイル全て byte-identical（cmp 実測）

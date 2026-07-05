# 納品サマリー — iteration 57（v1.18.0）

> 本タスクは Aegis フレームワーク自身の構造リアーキ。「client」＝フレームワーク保守者
> （次に aegis を使う自分自身）。外部クライアントへの製品納品ではない。

## 何を作ったか

**主 moat の交代**: 安定 control-plane（`hooks/` `scripts/` `templates/` `CLAUDE.md`
`.claude/{rules,skills,commands,agents}`）への誤書込み防御を、バイパス実績のある文字列静的解析
`check-control-plane.sh`（979行）から **OS-lock（`hooks/lib/cp-lock.sh`・chmod a-w・syscall 強制・
形非依存）へ昇格**。静的層は「lock が物理的に守れない残余領域」だけの `check-runtime-state.sh` に縮退。

| # | コンポーネント | 主な変更 |
|---|--------------|---------|
| 1 | `aegis_cp_verify` | lock 期待状態と実 FS 状態の全数照合（half-locked を可視化）・symlink 除外 |
| 2 | `session-start.sh` | apply 後 verify で不一致を強警告＋是正手順（fail-visible）・Windows は非サポート1行 |
| 3 | `check-runtime-state.sh`（新規） | 残余静的ガード＝runtime-state 書込み deny・unlock 形 deny・broad chmod ask・fail-closed |
| 4 | `explain-oslock-eacces.sh`（新規） | PostToolUseFailure advisory＝EACCES×CP で chmod 自己修復を抑止（純 advisory） |
| 5 | `check-control-plane.sh` | **退役（削除）**・配線/profile/contract/テストを 1対1 置換マッピングで移送 |

## 主要な設計判断

- 「syscall で守れるものは syscall へ、守れないものだけ静的判定に残す」。unlock 形（chmod 自体）と
  runtime-state 書込み（lock 対象外の docs/STATUS.md・.claude 設定）だけが残余静的層の担当。
- 脅威モデルは**事故防止**を維持（敵対 sandbox 化しない）。os.chmod 解錠は従来どおり脅威モデル外。
- 公式サポート = macOS/Linux/WSL（Windows ネイティブは chmod no-op＝OS-lock 無効・毎セッション明示）。
- 退役は「黙った削除」をせず、旧テストを lock 下 EACCES カタログ等へ 1対1 で移送（受け皿明示）。

## 変更ファイル一覧

- hook: `hooks/check-runtime-state.sh`（新規）・`hooks/explain-oslock-eacces.sh`（新規）・
  `hooks/lib/cp-lock.sh`（verify 追加）・`hooks/session-start.sh`・`hooks/check-control-plane.sh`（削除）
- scripts: `scripts/check_framework_contract.py`・`scripts/eval_scaffold_smoke.py`・`scripts/platform_manifest.py`
- 配布: `templates/hooks.template.json`・`templates/profiles/{full,standard}.json`・`templates/STATUS.template.md`
- テスト: 新規3（runtime_state_hook・cp_lock_verify・explain_oslock_eacces）＋sf_catalog 拡張＋退役群の置換
- docs: `docs/security-followups.md`・`README.md`・`docs/architecture-overview.md`
- version: v1.17.0 → **v1.18.0**（minor: 公開/運用契約は不変・保護実装の内部交代＋サポート表明の明確化）

## テスト・QA・セキュリティ結果の要約（証拠参照）

- テスト: full suite **1048 passed / 2 skipped**・`docs/qa-reports/iter57-qa.md`（B1 SKIP＋RED-first 代替実証）
- レビュー: セッション内フルコンテキスト実読＋盲検2次（approve_with_notes → 指摘全解消）・`docs/qa-reports/iter57-review.md`
- セキュリティ: 1次バイパス試行24形＋盲検2次が**難読化 unlock の silent 保護回帰（Major）を検出**→
  `_obfuscated_unlock_on_cp` で ASK 化・SF-009 記録・`docs/qa-reports/iter57-security.md`
- deploy: install 契約検証＝scaffold smoke 全3プロファイル PASS（installed tree で OS-lock apply+verify）・
  `docs/qa-reports/iter57-deploy.md`
- 決定論検査: contract/reference-drift/context-budget/status_doctor すべて PASS

## 残留リスク・既知の制限事項

- **難読化 unlock の残余**: 深い `$()` 構築・変数間接（`D=hooks; chmod +w $D`）はヒューリスティックを
  すり抜けうるが、意図的難読化＝事故防止の脅威モデル外（SF-004 と同じ静的判定の原理的限界・SF-009 記録）。
- 敵対的 `os.chmod`/`chflags` 解錠は従来どおり脅威モデル外（決定論的敵対防御ではない）。
- `mv hooks hooks_bak`（root 非 lock ゆえ rename 成功しうる）は rev.2 既定の accepted residual・hooks/ 内 INTACT。
- **Windows ネイティブは OS-lock 無効**（公式サポート外）＝chmod が no-op。WSL を使用のこと。

## 運用上の注意点

- **既存 install は `bin/setup.sh` 再実行で新配線に更新**（旧 check-control-plane 配線は template 書換で消滅・
  退役 hook file は copy_hooks が prune）。
- **framework 更新（git pull 等）で EACCES が出たら chmod で解錠しない** — `scripts/update-task.sh --type framework`
  で task_type を切替え、セッション再開で自動 unlock（advisory が案内）。
- エディタからも control-plane は read-only に見える（現行 layer-2 と同一挙動）。
- ロールバック: iter57 コミット群の revert で完全復元（状態移行なし）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- **MANUAL: 生成せず** — エンドユーザー製品ではなくフレームワーク（利用者＝保守者自身）。
- **RUNBOOK: 生成せず** — 運用者なし（CI 相当は contract/drift/scaffold-smoke の機械検査）。
- **UAT: 生成せず** — `docs/requirements/ACCEPTANCE.md` なし（受入基準を要する外部案件ではない）。

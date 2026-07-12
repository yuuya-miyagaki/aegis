---
name: deploy
description: "Deployment orchestration with security gates. Used in deploy phase."
disable-model-invocation: true
user-invocable: false
---

# Deploy Skill

## Overview

deploy フェーズはセキュリティレビュー完了後、ship の前に実行する。
デプロイ先の確認、環境構築、ステージング検証、本番投入、事後確認を
構造的に行うことで、場当たり的なデプロイ試行を防止する。

## デプロイ前ゲート確認（必須）

deploy フェーズ開始時に STATUS.md で以下を確認:

1. [ ] review ゲートが approved
2. [ ] qa ゲートが approved
3. [ ] security ゲートが approved（CONDITIONAL PASS の残留リスクは blockers に記録済み）
4. [ ] 環境変数の設定確認（LEARNINGS のデプロイ注意事項を参照）
5. [ ] git config user.email が正しいアカウントと一致

いずれかが未完了の場合、デプロイを実行しない。

## Deploy Substeps

```
deploy-prep   → デプロイ先確認、環境変数リスト、インフラセットアップ
staging       → ステージング環境での検証
uat           → ユーザー受入テスト
production    → 本番デプロイ + ヘルスチェック
post-deploy   → 外部連携テスト、モニタリング設定
```

## deploy-prep チェックリスト

PLAN の Deploy Target セクションを再読し、以下を確認する:

- [ ] デプロイ先プラットフォームが Plan と一致している
- [ ] 環境変数の一覧と設定状態を確認
- [ ] DB マイグレーションが準備されている
- [ ] インフラ（DNS、SSL 等）がセットアップ済み

## Mandatory Security Blockers

以下のいずれかが true の場合、production デプロイをブロック:

- [ ] 認証が無効（DEMO_MODE, auth bypass 等）
- [ ] デフォルト管理者パスワードが変更されていない
- [ ] HTTPS が未設定
- [ ] 環境変数にシークレットのハードコードがある

該当する場合:
1. STATUS.md に blocker として記録
2. ユーザーに明示的にリスクを説明
3. ユーザーが「リスクを受容する」と明言した場合のみ続行可能

## プラットフォーム別チェックリスト

プラットフォーム固有の手順は `.claude/skills/deploy/platforms.md` を参照。

## staging / uat

- ステージング環境で E2E テスト（または手動テスト）を実行する
- PLAN の External Integrations セクションがある場合、外部連携テストを実施する
- UAT の結果をユーザーに報告し、本番投入の承認を得る

## production

- 本番デプロイを実行する
- ヘルスチェックエンドポイントの応答を確認する
- 主要画面のスモークテストを実施する

## post-deploy

- 外部連携（Slack 通知、Webhook 等）の動作確認
- モニタリング / アラート設定の確認
- デプロイ完了を STATUS.md に記録する

## トラブルシューティング

トラブルシューティングの詳細は `.claude/skills/deploy/platforms.md` を参照。

## Deploy と Failure Rule の関係

deploy フェーズのゴール単位:

- deploy-prep → staging → uat → production → post-deploy は別ゴール
- 同一サブステップ内の再試行が3回失敗 → second-opinion 発動
- サブステップ間の移動はカウントをリセット

例:
- production デプロイが3回失敗 → second-opinion（ゴール = "production デプロイ成功"）
- staging 成功 → production 失敗1回 → staging に戻って修正 → production 再挑戦
  → これは production の2回目（staging の修正はカウント外）

## Completion

deploy フェーズ完了時に `DEPLOY-CHECKLIST.template.md` をベースにした
チェックリストを `docs/qa-reports/` に保存し、deploy ゲートを承認する:

```bash
bash scripts/update-gate.sh deploy approve --ref docs/qa-reports/iterNN-deploy.md
```

STATUS.md の直接編集は禁止（`update-gate.sh` が gate snapshot を含めて原子的に更新する唯一の経路）。

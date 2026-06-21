# iteration 35 deploy gate — デプロイ チェックリスト（layer-2 immutable moat）

> framework 改修＝実デプロイ先なし。deploy = `origin` への push（iteration 32/34 同様）。
> staging/uat/production は非該当（デプロイ対象プラットフォーム無し）。

## デプロイ前ゲート確認

- [x] review ゲート approved（証拠 docs/qa-reports/iter35-review.md）
- [x] qa ゲート approved（証拠 docs/qa-reports/test-strength.md・skip-drill＋手動 mutation 同等実証）
- [x] security ゲート approved（証拠 docs/qa-reports/iter35-security.md・adversarial 9 ベクタ遮断・ack deps N/A）
- [x] git config user.email を push 前に確認（yuuya-miyagaki アカウント）

## Mandatory Security Blockers（deploy skill）

- [ ] 認証無効（DEMO_MODE/auth bypass） → **非該当**（認証機構なし）
- [ ] デフォルト管理者パスワード未変更 → **非該当**
- [ ] HTTPS 未設定 → **非該当**（ネットワークサービスなし）
- [ ] 環境変数にシークレット ハードコード → **非該当**（secrets scan 0・新規依存 0）

→ **deploy-blocker なし**。

## デプロイ内容

- バージョン: 1.13.0（MINOR・追加のみ後方互換）
- 変更: layer-2 OS write-lock（`hooks/lib/cp-lock.sh` ＋ session-start 連動）追加。layer-1 存置。
- 検証: full suite 1025 passed/1 skip・contract PASS・版 3 箇所同期・arch-overview currency PASS。
- コミット: 1e46e4d〜（実装7）＋ゲート証拠コミット。

## post-deploy

- 外部連携なし（Slack/Webhook なし）。
- モニタリングなし（framework・solo）。
- push 完了を STATUS.md / session_history に記録。

## 判定: **READY（push 可）**

全ゲート approved・deploy-blocker なし・多層緑。push は yuuya-miyagaki アカウント。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["なし（review/security で独立レビュー済・deploy は framework の push 締めで実デプロイ検証対象なし）"]
  note: framework のため staging/uat/production 実機検証は非該当。deploy=push。deps N/A（pure-bash・stdlib）。
```

# v0.10.0 デプロイチェックリスト

## 対象

- プロジェクト: Ultra Framework Claude Code
- デプロイ先: GitHub (git push — フレームワークリポジトリ)
- 日付: 2026-04-18

## deploy-prep

- [x] デプロイ先が PLAN の Deploy Target と一致している — git push to origin/main
- [x] 環境変数の一覧と設定状態を確認した — 該当なし（フレームワークリポジトリ）
- [x] DB マイグレーションが準備されている — 該当なし
- [x] インフラ（DNS、SSL 等）がセットアップ済み — 該当なし

## Security Blockers

- [x] 認証が有効である — 該当なし（フレームワークテンプレート）
- [x] デフォルト管理者パスワードが変更済み — 該当なし
- [x] HTTPS が設定済み — GitHub 標準
- [x] 環境変数にシークレットのハードコードがない — grep 確認済み

**ブロッカー該当:** なし

## フレームワーク固有チェック

- [x] `python3 scripts/check_status.py --root .` → PASS
- [x] `python3 scripts/check_framework_contract.py` → PASS
- [x] `python3 scripts/check_status.py --root examples/minimal-project` → PASS
- [x] CLAUDE.md 語数 < 650（root=377, template=379, example=382）

## 総合判定

- 判定: completed
- 次のアクション: commit + git push to origin/main

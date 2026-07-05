# デプロイチェックリスト（iter56）

## デプロイ対象の性質

- iter56 は **aegis framework 自体の内部変更**（hook 判定・judge・contract・配布
  プロファイル・skill 文言）であり、外部サービスへのデプロイ（本番サーバ・DB・
  DNS 等）は伴わない。「デプロイ」＝**install 契約（setup.sh による対象プロジェクトへの
  配布）が壊れていないことの検証**をもって充足する。

## デプロイ前ゲート確認

- [x] review ゲート approved（docs/qa-reports/iter56-review.md）
- [x] qa ゲート approved（docs/qa-reports/iter56-qa.md）
- [x] security ゲート approved（docs/qa-reports/iter56-security.md・moat 回帰は修正済）
- [x] git config user.email = 正しいアカウント（push は yuuya-miyagaki・ユーザー確認待ち）

## install 契約の検証（本イテレーションの deploy 実体）

- [x] `test_full_profile_runnable_scripts.py`: setup.sh --profile=full を tmp へ実走し、
      manifest 実行可（allow|ask）全スクリプトの install 先実在を検証（⑥の再発防止）
- [x] contract 方向4: 実行可スクリプト ⊆ full 配布（intentional_unshipped 除外・理由必須）
      が PASS
- [x] `test_permission_allowlist_install.py` / `test_profile_referential_integrity.py` /
      `test_readme_profile_counts.py` すべて PASS（プロファイル増加後も整合）
- [x] full プロファイルに追加した5本（retro_report・check_reference_drift・
      learnings_search・lint_names・platform_manifest）が install 先に配布されることを確認

## Mandatory Security Blockers

- 該当なし（認証・HTTPS・シークレットハードコード等の本番要素なし・純フレームワーク変更）

## Blockers

- なし

## 判定

- deploy: **approve**（install 契約検証済み・外部デプロイなし）

## Claims（judge が機械読取する）

```claims
verdict: approve
```

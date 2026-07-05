# デプロイチェックリスト（iter57）

## デプロイ対象の性質

- iter57 は **aegis framework 自体の内部変更**（主 moat 交代＝OS-lock 昇格・
  check-control-plane 退役・残余ガード/advisory 新設）であり、外部サービスへの
  デプロイ（本番サーバ・DB・DNS 等）は伴わない。「デプロイ」＝**install 契約
  （setup.sh による対象プロジェクトへの配布）が壊れていないことの検証**をもって充足する。
  主 moat が install 経路に依存する（F6 教訓）ため、本イテレーションでは install 契約の
  検証が特に重要。

## デプロイ前ゲート確認

- [x] review ゲート approved（docs/qa-reports/iter57-review.md）
- [x] qa ゲート approved（docs/qa-reports/iter57-qa.md・B1 SKIP＋RED-first 代替実証）
- [x] security ゲート approved（docs/qa-reports/iter57-security.md・盲検2次 Major=難読化 unlock
      回帰は ASK 化で修正済・deps 🟡 は依存ゼロで ack）
- [x] git config user.email = 正しいアカウント（push は yuuya-miyagaki・ユーザー確認待ち）

## install 契約の検証（本イテレーションの deploy 実体）

- [x] **scaffold smoke 全3プロファイル PASS**（`python3 scripts/eval_scaffold_smoke.py`）:
      minimal / standard / full(hooks) いずれも PASS。
- [x] full(hooks) プロファイルで **installed tree の実発火を検証**（iter57 で更新した eval）:
      check-runtime-state が STATUS 書込みを deny ＋ **installed tree で cp-lock apply→verify rc0**
      （OS-lock が install 先で機能することを契約化）。
- [x] **退役 hook の install prune**: setup.sh copy_hooks が旧 `check-control-plane.sh` を
      install 先から除去（アップグレード時に配線外れの残骸を残さない）。
- [x] **新配線の配布**: templates/hooks.template.json（PreToolUse=check-runtime-state・
      PostToolUseFailure=explain-oslock-eacces）と profiles が install 先に配布される。
- [x] contract（REQUIRED_HOOK_FILES に advisory も追加・F6 教訓の silent 配布欠落防止）PASS。

## Mandatory Security Blockers

- 該当なし（認証・HTTPS・シークレットハードコード等の本番要素なし・純フレームワーク変更）

## Blockers

- なし

## 判定

- deploy: **approve**（install 契約検証済み＝scaffold smoke 全3プロファイル PASS・
  installed tree で OS-lock apply+verify・退役 hook prune・外部デプロイなし）

## Claims（judge が機械読取する）

```claims
verdict: approve
tests_green: true
```

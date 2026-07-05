# QA レポート
<!-- 正本: qa agent -->

> QA agent が実行した確認と証拠を要約する。VERIFICATION は自己検証用であり、
> 本レポートとは別物。

## 対象

- 変更内容: <記入>
- 環境: <記入>

## 実施した確認

- [ ] <記入>
- [ ] <記入>

## 実行コマンド

```bash
# <記入>
```

## 結果

- Pass: <記入>
- Fail: <記入>
- Skip: <記入>

## ブラウザ QA（ui_surface: true の場合）

- [ ] ページ表示
  - URL: <検証した URL>
  - snapshot: <docs/qa-reports/ のパス or "取得不可 + 理由">
  - 判定: 正常 / 異常
- [ ] コンソールエラー
  - エラー要約: <主要エラー or "なし">
- [ ] ネットワーク 4xx/5xx
  - エラー要約: <ステータスコード + エンドポイント or "なし">
- [ ] 主要操作
  - 操作: <実行した操作>
  - 判定: 正常 / 異常

## Blockers

- なし / あれば記入
## Claims（judge が機械読取する）

```claims
verdict: <記入: approve / approve_with_notes / reject / blocked>
```

<!-- exit-check: 全チェック実施・結果記入済み → security へ -->

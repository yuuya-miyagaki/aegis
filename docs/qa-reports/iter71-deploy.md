# iter71 デプロイチェックリスト — marker positive proof

- 対象: HEAD=8886715（実装 9dc77b1＋review/qa/security docs）
- デプロイ形態: **ローカル CLI framework 自体**（実ホスティング先なし・plan Deploy Target=n/a）。「デプロイ」＝`bin/setup.sh` による install 先への配布経路。

## デプロイ前ゲート確認

- [x] review ゲート approved（ref=docs/qa-reports/iter71-review.md）
- [x] qa ゲート approved（ref=docs/qa-reports/iter71-qa.md）
- [x] security ゲート approved（ref=docs/qa-reports/iter71-security.md・新規脆弱性0）
- [x] 環境変数: 該当なし（CLI・secrets なし）
- [x] git config user.email: 既存運用どおり

## Mandatory Security Blockers（全て非該当）

| blocker | 該当 |
|---------|------|
| 認証が無効（DEMO_MODE/auth bypass） | 非該当（認証機構なし） |
| デフォルト管理者パスワード未変更 | 非該当（パスワードなし） |
| HTTPS 未設定 | 非該当（ネットワークサービスなし） |
| 環境変数にシークレットのハードコード | 非該当（secrets なし・security gate で確認済み） |

→ production ブロッカーなし。

## 配布経路検証（deploy 実体）

新規 `hooks/lib/marker.sh` が install 先へ配布され、install 先で反ガミング moat が動作することを実測。

| # | 検証 | 期待 | 実測 | 判定 |
|---|------|------|------|------|
| 1 | 配布テスト（setup distribution） | green | **16 passed** | PASS |
| 2 | scaffold smoke（install 先で hook 実発火） | 全プロファイル PASS | minimal/standard/full 全 PASS | PASS |
| 3 | `bin/setup.sh --profile full <tmp>` 後の marker.sh 存在 | 配布される | `hooks/lib/marker.sh` present | PASS |
| 4 | install 先 marker.sh の正規入力判定 | true | **true** | PASS |
| 5 | install 先 marker.sh の zero-run 判定（moat 動作） | false | **false** | PASS |

検証4/5 が正しく true/false を返す＝marker.sh が自 dir の patterns.sh を隣接 source して機能している（両ファイル配布・fail-closed 退行なし）決定的証拠。setup.sh は `hooks/lib/*.sh` を glob 無条件配布（setup.sh:510）のため marker.sh は追加作業なしで全プロファイルに配布される。

## 判定

**deploy verdict: PASS**。実ホスティング先なし・Mandatory Security Blockers 全非該当・配布経路（新規 marker.sh の install 先配布＋moat 動作）を実測確認。

```claims
verdict: approve
```

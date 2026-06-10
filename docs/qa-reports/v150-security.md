# v1.5.0 E1 activity verification — security エビデンス（2026-06-11）

## 脅威モデル

E1 の敵対者は「検証したと偽るエージェント」（Fable 5 世代で顕在化した失敗モード）。防御目標は (1) 自己申告を信頼チェーンから排除し、green 認証を hook 観測の実行記録に限定する、(2) 観測系の死を silent fail-open にしない（F6 教訓）、の 2 軸。

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| judge テスト判定の唯一ソースを evidence-log 化（自己申告 test-result.json 廃止） | 強化 | エージェントが Write で偽の test-result.json を置く経路を構造的に排除。evidence-log への Bash 直接追記は check-control-plane が deny ✅ |
| fingerprint.sh 単一所有＋HEAD sha 混入 | 強化 | クリーンツリー同士の fp 一致で未テスト新コミットが green 認証される穴を封鎖（grill-plan 🔴1）✅ |
| quotepath=off＋quoted/unreadable→error（grill-code 🔴1） | 強化 | 非ASCII名で fp が内容変更に不感になる silent-green を封鎖。判別不能は error トークンで fail-closed ✅ |
| 長さプレフィックス framing（grill-code 🟡1） | 強化 | 異なるツリーの同一ハッシュ入力衝突（境界曖昧）を排除 ✅ |
| 記録=fail-open／判定=fail-closed の二段構え | 設計通り | 記録欠落は隠れず gate で 🟡 unverified に表面化（silent-green なし）。token==token 認証は `_HEX64` 検証で不能 ✅ |
| observer 生存チェック（TaskCompleted で evidence-log 不在＝差し戻し） | 強化 | 観測系死亡の silent fail-open 同族（CLAUDE_PROJECT_DIR 未設定系）対策 ✅ |
| scaffold smoke の観測系実発火（成功側＋失敗側） | 強化 | install 経路の死角なし。失敗記録の死＝偽 green 方向も実発火で検証（grill-code 🟡3）✅ |
| docs/hook-failure-policy.md に observer 行追加＋実発火突合 | 可視化 | 「宣言なき fail-open」の構造的排除を維持 ✅ |

## 受容済みリスク（設計上の明示トレードオフ）

- **cmd 文字列偽装**（`echo pytest` で ok 記録を作る）: 計画 §552 で明示許容。記録は「実行があった」ことの観測であり、コマンドの意味解析は reviewer（LLM）の責務。偽装はチャット履歴・evidence-log に痕跡が残り、非エンジニア judge の可視面では fp 鮮度照合が同時に要求される
- **payload_sha は生ペイロードのハッシュ**（出力本文抽出なし）: pure-bash 制約による承認済み逸脱。読み手は未検証のため攻撃面なし

## 残余リスク（記録、いずれも fail-closed 方向）

- 失敗側 false-RED: テストランナー名を含む非テストコマンドの失敗（例 `grep vitest package.json` rc=1）が red 化。実テスト再実行で回復可・ハードブロックは現行踏襲
- 観測 hook のホットパスコスト: 毎 Bash 実行で git diff＋変更ファイル読込。AEGIS_FP_MAX_FILES=200 / AEGIS_FP_MAX_BYTES=10MB で有界、超過は oversize（unverified 方向）
- cmd 500 字切詰め・制御文字混入・python3 不在時の `\"` 含む cmd: いずれも分類漏れ→unverified（green 偽装には使えない）
- `${input:0:65536}` は文字数スライスでスキーマ注記「64KB」と微差（payload_sha は読み手未検証のため実害なし）
- 既存残穴（v1.4.0 から継続、v140-security.md 記録済み）: WRITE_INDICATORS 左境界なし・`truncate`/`dd` シェル形・stale lock 自動回収なし・check-deploy-gate stderr 混入・update-gate CURRENT 表示 TOCTOU

## 検証

- 観測→判定 e2e（実発火）で green/red/unverified の 3 値が設計どおり（test_evidence_hooks.py）
- fingerprint の fail-closed 経路（nogit/error/oversize/nolib）が全て unverified に倒れることをテストで固定
- 436 tests OK / contract PASS / drift PASS / scaffold smoke 3 プロファイル PASS（v150-qa.md 参照）

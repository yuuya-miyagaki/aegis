# v1.5.1 grill 残余修正バッチ — security エビデンス（2026-06-11）

## 位置づけ

v140-security.md / v150-security.md に記録した既知残余（grill 🟢）の解消バッチ。
**v140/v150 記録の残余 5 系統は本バッチで全て対処済み**: WRITE_INDICATORS 左境界（T5a）、
find 経由の truncate/dd 書込形（T5b）、stale lock 自動回収なし（T4）、check-deploy-gate
stderr 混入（T2）、update-gate CURRENT 表示 TOCTOU（T3）。

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| T5b: `find ... -exec/-execdir/-ok/-okdir/-delete/-fprint0?/-fprintf/-fls` を deny | **強化（実バイパス封鎖）** | `find hooks/ -exec dd of={} +` は READ_ONLY_STARTS（find 先頭）と CHAIN_OPS（`;` なし形）を共に通過する実書込経路だった。左境界付き列挙で封鎖、`cat hooks/pre-exec.log` 等のファイル名言及は allow 維持 ✅ |
| T5a: 語形 WRITE_INDICATORS に左境界 | 誤 deny 解消（可用性） | `grep "confirm " hooks/x.sh` の "confirm " 内 `rm ` 誤一致を解消。`|` 後連結で先頭 `-` パターンを回避（BSD grep が option と誤parse→rc=2→`!` 反転で fail-open になる事故の予防を維持）✅ |
| T1: テストランナー分類のコマンド位置アンカー＋改行正規化 | 誤判定緩和（fail-closed 維持） | 分類の縮小は unverified 方向（green 偽装には使えない）。false-RED（引数言及の rc≠0 が実 green を覆す）を解消 ✅ |
| T1 逸脱: extract-input.sh の python3 fidelity ルーティング拡張（`\\[\\nrtbfu"]`） | 強化（分類経路の忠実度） | 改行入りコマンドが実改行で記録され正規化契約に到達。python3 失敗時の grep フォールバックは記録系 fail-open として設計どおり。deny 系（check-control-plane）は python3-first で独立・影響なし ✅ |
| T2: check_status.py の stderr を判定テキストから分離 | 強化（判定文面の完全性） | python 警告/traceback が ask/deny 文面に混入する経路を排除。RESULT 空のときのみ診断として deny 理由に併合（fail-closed 維持）✅ |
| T3: ロック取得を CURRENT 読取前に移動 | 強化（TOCTOU 封鎖） | 表示値と書込値の不一致窓を排除。構造テストで順序をピン留め ✅ |
| T4: stale lock の dead-pid 限定自動回収（atomic-mv claim） | 強化＋可用性 | kill 等で残ったロックを保持プロセス死亡確認後にのみ回収。garbage/live/pid なしは不回収＝fail-closed、live は pid 付き案内。15 回レース実証で単独勝者・torn write ゼロ ✅ |

## 受容済みリスク（設計上の明示トレードオフ）

- `grep -e "-exec" hooks/x.sh` 型の false-deny（設計 §T5 記載済み。読み取りは Read ツールで代替可）
- `time pytest`・`bash -c "pytest"`・`if ...; then pytest; fi` 等のラッパー/制御構文形は分類不一致＝unverified 方向（README Migration に記載、直接実行か record-test-result.py で回復）
- `kill -0` の EPERM で他ユーザー所有 live プロセスを dead 誤判定し得る（設計 §T4 受容済み。単一ユーザー運用が前提）

## 残余リスク（今回記録、いずれも fail-closed／可用性方向）

- クォート内の `;&|` 区切り quote-blindness は残存: `grep -E "(unittest|pytest)" f` のような**グループ内 2 番目以降**のランナー名は `|` 経由で一致し得る（rc≠0 時 false-RED）。先頭位置の `(` 衝突（高頻度形）は grill A 🟡-1 で封鎖済み。回復手段は実テスト再実行/手動記録で同一
- 入れ子サブシェル `((pytest))` は分類不一致（unverified 方向、稀形）
- `\/` エスケープは fast-path 非ルーティング（標準エンコーダ非生成・deny 系は独立、コメントで明文化）
- claim-mv 後 undo 前のクラッシュで pid なしロックが残留し回収対象外（極小窓・手動削除案内が受け皿）
- ロック待機 2s は実競合では常に敗者 rc=1（「Retry shortly」案内どおり。自動リトライは非目標）

## 検証

- バイパス回帰: v1.3.3 で deny を確認した 13 形は test_check_status.py の既存テストで維持（461 tests OK に包含）
- T5 の deny/allow 実機確認・T3/T4 レース実証・T1 judge e2e は v151-qa.md「実地検証」参照
- 461 tests OK / contract full+standard PASS / drift PASS / scaffold smoke 3 プロファイル PASS / check_status --strict PASS

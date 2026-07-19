# ブレインストーミング記録

## 日付
2026-07-20

## テーマ
iter75 P0：SF-017 MOAT-BYPASS の修正。`check-destructive.sh`／`check-secrets.sh` が空クォート トークン分割（`g""it a""dd .e""nv` → bash では `git add .env`）で回避され、**secret DENY が silent ALLOW に落ちる**（Critical）。SF-001 で control-plane 側には防御があるが、この2フックの生 regex 判定に未伝播。

## コンテキスト
- 正本＝`docs/full-review-2026-07-19-dual-codex-fable.md` §4.1／SF-017（`docs/security-followups.md`）。親再現済み。
- **重要な既存事実**: フレームワークは**フル shlex tokenizer を意図的に退役**させ（`check-runtime-state.sh:188` "A full tokenizer is what the moat handover deliberately retired"）、`_obfuscated_unlock_on_cp` が「クォート/バックスラッシュを param 展開で除去 → 正規化形を grep → 難読化があれば ASK 格上げ（silent allow → visible confirm）」という軽量パターンを採用済み。iter75 はこの既存哲学に一貫させる。

## 検討したアプローチ
### A: 共有 helper で正規化（採用）
`patterns.sh` に `aegis_dequote_normalize`（純 bash・クォート/バックスラッシュ除去）を1つ新設し、check-destructive/secrets が生形＋正規化形の両方で既存検出を実行。CP コードは触らない。既存哲学と一貫・DRY・低複雑・SF-001 退行リスクゼロ。
### B: 各フックにインライン移植（却下）
`_obfuscated_unlock_on_cp` を各フックにコピー。共有 helper を作らずロジック重複。3本目の同型が出たら再重複。
### C: 厳密トークナイザ新設（却下）
argv＋演算子位置を解釈。最も精密（OBS-006 誤検知を原理排除）だが最も新規コード＝フレームワークが退役させた方針に逆行・保守負担増（North Star 非整合）。

## 決定
1. **アプローチ A 採用**（AskUserQuestion Q1）。
2. **難読化形でのみ一致した secret は ASK に格上げ**（Q2）。生形一致は従来通り（destructive=ASK／secrets=DENY）。理由: command 位置を見ない方針では `g""it a""dd .e""nv` と `git commit -m "git add .env"` を正規化後に区別不能。ASK なら Critical（silent 漏洩）を閉じつつ誤 DENY（作業ブロック）を避け、CP の `_obfuscated_unlock_on_cp` 哲学と一貫。「DENY 復元でない＝弱化」批判はあるが、閾値上げ＋事故防止という脅威モデルに整合。
3. 正規化は**純 bash param 展開**（python 不要＝fail-open 経路を増やさない）。

## スコープ境界
- **含む**: クォート（`"`/`'`）＋バックスラッシュ除去（レビュー実証の bypass）。既存の安全形除外（`.env.example`）・git-add 系認識・`LC_ALL=C`・SQL 小文字畳み込みを再利用。
- **含まない**: `$(...)`/バックティックのコマンド置換・runtime 構築（SF-004 原理的限界・文書化済み）、フル argv トークナイザ、CP コードの改修。

## 未解決事項
- check-secrets の正規化照合は既存検出関数の再利用で実装するが、`RAW_LC`（小文字畳み込み）との合成順序は実装時に確定（正規化→畳み込み）。
- 誤 ASK の実頻度（`echo "r""m"` 等の contrived case）は許容だが、回帰 pin で正常クォート形の非 ASK を固定する。

## 次のステップ
plan（writing-plans で実装計画）→ **grill-plan で穴出し・全潰し** → implement（TDD RED→GREEN・実装は opus dispatch）→ grill-code → review+qa+security。

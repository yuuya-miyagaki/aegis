# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-18（iteration 32）

## テーマ

- SF-001: control-plane フックのクォート/エスケープ/bare-dir トークン分割バイパス（Critical・pre-existing）を潰す

## コンテキスト

- 現在の状況: `hooks/check-control-plane.sh` の control-plane 判定は「正規表現＋`mask_quoted` のクォート span マスク」で、シェルのクォート除去＋隣接トークン連結＋パス解決（word splitting）を再現していない。リテラル `hooks/`|`scripts/`|`templates/`|`STATUS.md`… 部分文字列に一致するだけ。
- きっかけ: iteration 31 / Batch1 review の盲検 break-attempt（reviewer ＋ reviewer-maintainability が独立検出）。security 1次＋盲検2次が orig(8f8eb2d) vs new HEAD で全 repro を実走し「両者 allow＝完全に pre-existing」と確認。Batch1 後退ゼロ。deploy blocker 列挙に非該当のため Critical 残存リスクとして繰延承認（ユーザー合意 2026-06-16）。正典＝`docs/security-followups.md` SF-001。

## 検討したアプローチ

### アプローチ A: Augment（token-aware チェックを1本追加）

- 概要: `cmd_mentions_control_plane` 末尾に新関数を1本足し、shlex トークン化＋bare-name 判定で「書込み先の語が CP に解決するか」を検査。既存 (a)(b)(c) は無改変。deny を足すだけ。
- 利点: 既存 moat テスト/REDTEAM(18/18+5/5)/OBS-006 救済が構造的に緑維持。回帰リスク最小。セキュリティ境界として最も安全。
- 欠点: 既存パスと検出が一部重複（同一 deny に収束＝無害）。

### アプローチ B: Replace（mention 検出をトークナイザで作り直す）

- 概要: `cmd_mentions_control_plane` の mention 検出を単一トークナイザモデルに置換。
- 利点: 設計が綺麗・単一モデル。
- 欠点: OBS-006・redirect・cmdsub の全エッジを再導出＝セキュリティ境界で回帰リスク高。盲検レビュー負荷増。

## 決定

- 採用アプローチ: **A（Augment・inline）**。トークナイザ コードは `check-control-plane.sh` に inline（新規 lib を作らず setup.sh 配布面/mirror 面を増やさない＝iter31 F6「lib 未配布で moat 死」類の配布バグを回避）。
- 採用理由: 回帰リスク最小・既存の勝ちを構造的に温存・配布面を増やさない。end-to-end フックテストが主軸なので unit テストのために lib 分離する利得は限定的。
- 不採用理由: B はセキュリティ境界での全エッジ再導出が高リスク。

## スコープ境界

- やること: SF-001 の3クラスを閉じる ①quote分割/隣接連結 ②backslash エスケープ ③trailing-slash 無し bare-dir operand。本体＋mirror 同期。TDD。security 盲検2次。
- やらないこと: 既存 allow/deny 挙動の書き換え。新規 lib 追加。スコープ外のハードニング（YAGNI）。`cd hooks` 等 inert ナビの救済（fail-safe 方向で許容）。

## 未解決事項

- なし（python3 不在時の fail-closed・bare-name の救済規約は SPEC で確定）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-18-sf-001-cp-token-bypass-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-25（iteration 45）

## テーマ

- `bin/setup.sh` の C2（引数パーサが `=` 形式のみ受理）と C3（FRAMEWORK_VERSION 取得 heredoc の dead first path）を直す価値とスコープの確定。

## コンテキスト

- 現在の状況: 2026-06-24 全力レビュー（`docs/full-review-2026-06-24-hooks-gates-distribution.md`）の残課題。C2・C3 はともに `bin/setup.sh` のインストール初期化領域に閉じる。
- きっかけ: full-review C2/C3。grill-premise で「直す価値」を疑い、2 件を再格付けした。

## 検討したアプローチ

### アプローチ A: C2=両形式対応＋C3=heredoc を argv 渡しで生かす（採用）

- 概要: パーサを `--profile=full` と `--profile full` の両形式対応に。`--target` も同様（H2 で同じ穴を確認）。C3 は `python3 - "$ROOT/..." <<'PY'` で `sys.argv[1]` を読み、dead path を解消。grep フォールバックは defense-in-depth として残す。
- 利点: 知識の乏しい層が `--profile full` で詰まらない（North Star 直結）。`--target` の非一貫を残さない。C3 の python 主経路が「実際に version を返す」ことを positive-control test で実証でき、qa の「守った挙動」が成立する。クォート heredoc のインジェクション安全性を維持。
- 欠点: パーサ書き換えで既存 `=` 形式の回帰リスク（テストで担保）。C3 は機能影響ゼロ（後述）なので「掃除」であることを正直に明記する必要。

### アプローチ B: C2=エラーメッセージ親切化のみ／C3=heredoc 削除し grep を正本化

- 概要: 空白形式は非対応のまま「`--profile=full` の形式で指定してください」と案内。C3 は dead heredoc を削除し grep+sed を唯一の経路に。
- 利点: パーサ本体を触らない＝回帰リスク最小。コード行数が減る。
- 欠点: 「ただ動く」より一段不親切（人は習慣的に空白形式を打つ）。grep+sed は python 正規表現より edge case 頑健性が低く、version 行の書式が将来変わると静かに壊れうる。

### アプローチ C: do-nothing（README に「`=` 必須」を 1 行追記のみ）

- 概要: C2 は文書で回避、C3 は放置。
- 利点: 実装ゼロ。
- 欠点: C2 の papercut は残る（文書を読まず打つ層に無力）。C3 の dead code が「動いて見えるが動いていない」保守トラップとして残る。配布 readiness を上げない。

## 決定

- 採用アプローチ: **A**
- 採用理由: C2 は実ユーザー価値（doc/impl 不整合・North Star 直結）かつ testable。`--target` も同時対応で構造的に直す。C3 は機能影響ゼロ（grep が `1.14.0` を返すと実測）だが、honest cleanup として束ねる費用対効果が高く、argv 渡しなら安全に dead path を生かせて positive-control test も成立する。
- 不採用理由: B はエラー親切化のみだと知識の乏しい層に弱く、grep 正本化は頑健性を落とす。C は papercut と保守トラップを温存し配布 readiness を上げない。

## スコープ境界

- やること:
  - C2: `bin/setup.sh` 引数パーサを `--profile` / `--target` の両形式（`=` と空白）対応にする。値検証（profile allowlist）は不変。
  - C3: FRAMEWORK_VERSION heredoc を argv 渡しに変更し dead first path を解消。grep フォールバックは残す。
  - 上記の振る舞いを担保する behavioral test（RED-first）。
- やらないこと:
  - C2 のエラーメッセージ親切化「のみ」案。
  - C3 の heredoc 削除（grep 正本化）案。
  - C4（gate 値パーサ bash↔python 乖離）・G4（.env/curl 再評価）— 別 iteration。
  - `check-control-plane` 再設計。

## 未解決事項

- なし（H1/H1b/H2 を実測で確定済み: grep fallback=`1.14.0`、heredoc=FileNotFoundError、`--target` も `=` 専用）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-25-iter45-setup-arg-version-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

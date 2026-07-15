# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-15

## テーマ

- iter71: SF-014 恒久策 — 反ガミング検証を列挙式 denylist から positive proof（「N≧1 件のテストが実際に実行された」証明）へ置換する

## コンテキスト

- 現在の状況: LEARNINGS line148（conf9）「列挙式 denylist は原理的に不完全＝反ガミング moat は positive proof で作れ」が record / B1 drill / audit_deps の3系統で実証済み。patterns.sh には STRONG/WEAK marker・zero-run 信号・pytest prologue の4段検証が既に存在し、hook 観測経路（`evidence.sh _check_test_marker`）だけが消費している。record-test-result.py は出力を取得済みなのに exit code しか見ておらず（`unittest discover -p <nomatch>` exit0 / `npm test`→`"test":"true"` で green 偽造可）、drill の `check_baseline` も exit code のみ（非ランナー import プローブ＋import-crash mutant で偽 DRILL PASS）。
- きっかけ: iter70 で Phase 1 完遂・SF-014 が唯一の Major-class OPEN。/recover 時にユーザーが iter71 トラックとして選定。

## 検討したアプローチ

（スコープ決定）3系統全部／record+drill のみ／record のみ最小 → **record+drill のみ**を採用。record/drill は同一機構（marker positive proof の共有 lib 化）で1テーマ、audit_deps は「依存ゼロの積極証明」＝attestation 型で機構が別物のため iter72 に分離起票（テーマ純度・iter70 実績に整合）。3系統全部は footprint L 超過で deploy 必須化し周回が重い。

### アプローチ A: bash 単一実装の共有 lib 抽出（marker.sh）

- 概要: evidence.sh の `_check_test_marker` からコア判定（cmd＋exit_code＋output → verdict）を `hooks/lib/marker.sh` に抽出。evidence.sh は source して挙動不変、python 側（record/drill）は subprocess で同一実装を呼ぶ。
- 利点: ロジック単一・言語間 drift ゼロ。`check_no_run_command` の「python から bash+grep を呼び同一エンジン保証」前例に踏襲。iter69 conf8 教訓（検査系と実行系の別経路解釈が Critical を生む）に整合。
- 欠点: subprocess 境界の入出力設計が1点増える（stdin 渡しで解決）。

### アプローチ B: python port（patterns.sh 配列を parity 読込）

- 概要: judge の `_test_runner_patterns` 前例で正規表現を単一ソース読込し、4段ロジックを python に再実装。
- 利点: python 内で完結・単体テスト容易。
- 欠点: **4段ロジック本体が bash/python の2重実装**になる。regex parity 契約はあってもロジック parity は pin できず、SF-014 を生んだ「同じ入力を別経路で解釈」構造を自ら再生産する。

### アプローチ C: evidence.sh に CLI モード追加（抽出なし）

- 概要: evidence.sh に `--check-marker` 引数モードを追加して python から呼ぶ。
- 利点: ファイル増なし。
- 欠点: hook エントリポイント（raw-hook-input JSON 前提）と lib の責務が混在。

## 決定

- 採用アプローチ: A（bash 共有 lib 抽出）
- 採用理由: 同一エンジン・単一実装で drift 構造を作らない。既存前例（check_no_run_command）と設計言語が揃う。
- 不採用理由: B はロジック2重実装＝SF-014 と同型の穴の温床。C は責務混在。
- 偽陽性処理（ユーザー決定）: record 層で「exit 0 だが marker 不成立（未知ランナー含む）」の green は **rc2 拒否・ログ非書込**（stderr で対象ランナー一覧と patterns.sh 拡張を案内）。red（exit≠0）は marker 不要で従来通り記録（fail-visible は gaming 経路でない）。🟡降格記録案は「judge に無視されるエントリを書ける」foot-gun のため不採用。

## スコープ境界

- やること: marker.sh 抽出（挙動不変）／record green 記録の positive proof 必須化（rc2 拒否）／drill `check_baseline` の no-test-proof BLOCKED／TDD RED 先行のテスト
- やらないこと: audit_deps の positive proof（attestation 型・iter72 分離起票）／marker 覆域拡張（mocha/rspec/PHPUnit 等・YAGNI・on-demand）／mutant 実行側の marker 検査（survived→FAIL で fail-visible）／judge 側の検証ロジック変更

## 未解決事項

- なし（64KiB 先頭 cap と末尾 marker の罠は設計ノートで対応を明記）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-15-iter71-marker-positive-proof-design.md`
- テンプレート名: `SPEC.template.md`

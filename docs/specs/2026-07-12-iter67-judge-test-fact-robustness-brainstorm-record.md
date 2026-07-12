# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-12（iteration 67・ユーザー指示＝自走）

## テーマ

- judge tier-1 test-fact 判定の堅牢化 — `build-judge-card.py::read_test_result` の
  「最新 test-runner マッチエントリの終端拒否権」を剥奪する

## コンテキスト

- 現在の状況: `read_test_result` は evidence-log を新しい順に走査し、**最初の**
  test-runner マッチエントリで判定を打ち切る。そのエントリが observed かつ
  `marker_verified≠true`（undecidable）だと、fp 一致の trusted green が直下に
  あっても `unverified`（🟡）を返す。
- きっかけ: iter64/65/66 で3回顕在化（LEARNINGS conf9 line137）。record green 後に
  クォート外の生 pytest（件数確認 `--collect-only`・pipe 切詰め等）を1回走らせる
  だけで judge が 🟡 に降格し、ack 儀式または再 record が毎回必要になった。
  retro で改善 #1 として機構的根切りに合意。
- 根本の不整合: C-2（v1.6.1）は「marker 未検証の observed エントリは green/red を
  **証明できない**」と定めたのに、現行実装はその証明能力ゼロのエントリに
  「trusted green を破壊する終端拒否権」を与えている。信頼できない情報は
  判定を確定できないだけでなく、**判定材料からも透明であるべき**。

## 検討したアプローチ

### アプローチ A: reader-side 透明化（trust-scan）【採用】

- 概要: `read_test_result` の走査で、undecidable（observed かつ
  `marker_verified≠true`）**かつ status=ok** のエントリを「情報ゼロ＝透明」として
  skip し、走査を継続する。最新の **decidable** エントリ（manual、または
  observed+marker_verified=true）が判定を決める。undecidable かつ status=fail は
  従来どおり終端 `unverified`（保守的維持）。fp 不一致の終端 `unverified` も不変。
- 利点:
  - 罠の根切り: 件数確認・pipe 切詰め（いずれも exit 0）が trusted green を
    破壊しなくなる。
  - **fail-visibility の改善**: 現行では decidable red の後に `--collect-only` を
    1回走らせると newest が undecidable-ok になり red→🟡(ack 可) に「洗浄」できる。
    透明化で red が再浮上する＝厳格化。
  - 安全性: 透明化が green を返すのは「fp（committed tree-hash）が現在の worktree と
    一致する trusted green が実在する」場合のみ。C-2/K-1 の forge 防御は不変。
  - 既存ピン（単一エントリ5テスト）と無衝突（変更は複数エントリ系列のみ）。
- 欠点: status=ok に洗浄された marker-less 実失敗（`pytest | tail` で SIGPIPE 等）を
  green が透過する — ただし現行でもそれは red にならず 🟡 なので、red 隠蔽の
  後退はない（fp 一致の trusted green が実在する前提での 🟡→green のみ）。

#### A1 変種: status=fail の undecidable も透明にする【不採用】

- 概要: 全 undecidable を透明化。
- 欠点: marker-less の実失敗（collection error・import error crash＝exit≠0）を
  green が透過し得る。🟡 が「何かが失敗した・再確認せよ」という正しい信号である
  ケースを消す＝fail-visible 後退。罠の実例（件数確認・pipe）は全て exit 0 なので
  fail 透明化は不要（YAGNI）。

### アプローチ B: writer-side 抑制（no-run flag を非 runner 化）【不採用】

- 概要: `is_test_runner_cmd`（evidence.sh）で `--collect-only` 等 no-run flag 付き
  コマンドを非 runner 扱いにし、`fp="skipped"` で記録＝reader が最初から無視。
- 利点: hot-path の fingerprint 計算も節約。
- 欠点: 罠の一部（no-run flag）しか塞げない — pipe 切詰め・prologue 欠け・
  出力 window 溢れ等、undecidable の他経路が全部残る＝根切りにならない。
  観測層は「忠実な記録」に徹し判定意味論は reader の責務（アーキ責務分離）。
  分類器は post-bash.sh の ReAct hint とも共有され、変更の波及が広い。
  過去ログのエントリには効かない。

### アプローチ C: 手続き強制（record 後の生 pytest を hook で警告/deny）【不採用】

- 概要: record-test-result 実行後〜gate 承認までの窓で runner-match コマンドを
  警告またはブロックする hook。
- 欠点: 正当な部分 pytest 実行（デバッグ・単発確認）は普通にあり誤爆面が広い。
  状態（窓の開閉）を持つ hook は複雑で brick リスク。judge が正しく判定すれば
  不要な対症療法。

## 決定

- 採用アプローチ: A（reader-side 透明化・status=ok の undecidable のみ透明）
- 採用理由: 罠3実例の根切り＋red 洗浄経路の封鎖（厳格化）を、trusted 判定
  ロジック（C-2/K-1・fp backstop）を一切緩めず reader 1関数の変更で達成できる。
- 不採用理由: B は網羅性欠如＋責務違反、C は誤爆と複雑さ、A1 は fail-visible 後退。

## スコープ境界

- やること: `read_test_result` の走査意味論変更＋docstring 同期＋系列テスト
  （TDD RED-first）。
- やらないこと:
  - 候補 #2「ref-window 原子化（update-gate approve --ref・full-review 1-3）」—
    別機構（update-gate.sh/contract）の control-plane 変更であり、judge と同一
    反復での2機構同時変更を避ける（iter66 の SF-010 分離と同じ判断）。
    **iter68 第一候補**として繰り越し。
  - 候補 #3「session_history 自動アーカイブ＋doctor 誤検出偏り」— 独立した
    maintenance テーマ。繰り越し。
  - writer 側（evidence.sh）・patterns.sh・record-test-result.py は不変更。

## 未解決事項

- なし

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

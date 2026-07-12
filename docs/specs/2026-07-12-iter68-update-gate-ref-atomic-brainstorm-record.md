# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-12（iteration 68）

## テーマ

- update-gate の `approve --ref` 原子化＋状態変更を出力より先に（SIGPIPE 耐性）＋pending+ref の advisory 降格（全体レビュー §4 Phase 1 項目 1-3・R6 罠 a,b,c の機構的根治）

## コンテキスト

- 現在の状況: ゲート承認の evidence ref（`current_refs.<gate>`）とゲート値（`gate_approvals.<gate>`）は**別ステップで書く**しかなく、どちらの順でも contract が赤くなる窓が開く。
  - ref 先置き→approve: 窓の間は「pending gate に非 null ref」で `evidence_integrity_violations` が stale-ref **FAIL**（LEARNINGS conf9 line137・conf9 line32・conf8 line85 ＝ iter35/43/64/65 で計4回以上被弾）。
  - approve 先→ref 後置き: 窓の間は「approved gate なのに ref 空」で同関数が **FAIL**（pre-approve は ADVISORY を出すのみで完了時 enforcement 前提の設計）。
  - さらに update-gate.sh は approve 時、**状態書込み（sed）より前に** judge カード全文（大量出力）を stdout に流す（241-252 行）。出力先 pipe が先に閉じる（`| head` 等）と SIGPIPE で **状態未変更のまま死ぬ**＝罠 a（「tail 必須」の暗記を operator に強制）。
- きっかけ: docs/full-review-2026-07-06-six-dimensions-evolution.md §R6 が「罠18項目の約6割は設計負債の人間側転嫁」と分類し、§4 Phase 1 表 1-3 に本修正を規定。ユーザー方針＝Phase 1 残り3項目のスイープ（iter68=1-3）。iter67 で test-fact 軸（trust-scan）は根治済み・**ref-window 軸が最後の未解決**。

## 検討したアプローチ

### アプローチ A: writer 原子化＋書込み先行＋advisory 降格（フルセット・レビュー処方どおり）

- 概要: (1) `update-gate.sh <gate> approve --ref <path>` を追加し、ゲート値と ref を**同一 sed 単一パス（TMP+mv）**で書く（reset の ref null 化と同型）。(2) approve 経路を「検証→**状態書込み→ACK 追記→snapshot**→出力（best-effort）」に並べ替え＋`trap '' PIPE`。(3) `evidence_integrity_violations` の「pending/n/a gate に非 null ref」分岐を FAIL→printed WARNING（advisory）へ降格（approved+空 ref・ref 実在検査・client artifact 検査は FAIL 維持）。
- 利点: 赤い窓が**存在自体消える**（正順のワンコマンド化＝record green→`approve --ref` の2手）。SIGPIPE で死んでも「状態変更前＝何も主張しない」「状態変更後＝出力欠けのみ」の fail-safe 不変条件が立つ。降格は共有関数1点で contract テスト（check_framework_contract→validate_status_file）と TaskCompleted hook（--check-completion-evidence）の両方に一貫波及。LEARNINGS の「record→ref→承認を連続」暗記規律を機構で不要化＝北極星（非エンジニアが回せる）に直結。
- 欠点: update-gate.sh の引数解析を positional（$3/$4）から flag loop へ再設計する必要。guidance 同期先が多い（CLAUDE.md 完了規則・/gate command・gate 系 skill 4-5枚）。

### アプローチ B: advisory 降格のみ（--ref なし）

- 概要: contract の pending+ref FAIL を WARNING に落とすだけ。operator は従来どおり ref を raw Edit してから approve。
- 利点: 最小 diff（check_status.py＋テスト1本）。
- 欠点: approved+空 ref の窓（approve 先行順）は FAIL のまま残る＝順序結合が半分生き残る。2ステップ操作自体が残り「正しい操作列の暗記」を解消できない。レビュー処方（原子化＋降格のセット）に未達。

### アプローチ C: SIGPIPE を `trap '' PIPE` だけで対処（並べ替えなし）

- 概要: 罠 a を trap のみで塞ぎ、出力順序は現状維持。
- 利点: 1行変更。
- 欠点: `set -e` 下では SIGPIPE 無視→write() が EPIPE エラーに変わり echo/cat が非ゼロ→**結局書込み前に abort**（罠 a が形を変えて残る）。「状態変更が出力に先行する」不変条件が立たず、テストで固定できる性質にならない。

## 決定

- 採用アプローチ: **A（フルセット）**
- 採用理由: 全体レビュー §4 1-3 の処方そのもの。罠 a,b,c を「注意」でなく機構で消す唯一の案であり、iter67 の trust-scan（test-fact 軸根治）と対になる ref-window 軸の根治。降格単独（B）では順序結合が残り、trap 単独（C）は set -e との相互作用で効かないことを机上で確認済み。
- 不採用理由: B=原子化なしでは operator 体験（ワンコマンド化）と approved+空窓が未解決。C=EPIPE 化するだけで abort 位置が変わらない。

## スコープ境界

- やること: update-gate.sh（--ref・書込み先行・trap '' PIPE・na/reset の --ref 拒否・na の ref null 化〔writer 衛生の対称性〕）／check_status.py（pending/n/a+ref の advisory 降格・pre-approve ADVISORY 文言を --ref 推奨に更新）／テスト（既存ピン更新＋新規: 原子性・--ref 検証・SIGPIPE E2E・出力順序）／guidance 同期（CLAUDE.md 完了規則の文言・.claude/commands/gate.md・gate 系 skill の approve 手順を `approve --ref` に）。
- やらないこと: SF-011（frontmatter 終端デリミタ差）・SF-012（washed-green/unknown-src）は**相乗りしない**（別機構＝frontmatter lib／judge 走査。テーマ純度と M footprint 維持。backlog のまま iter71+ 候補）。approved 済み gate の ref 差し替え機能（raw Edit で可能・現状維持）。rollover の authorized writer 化（Phase 2 の 2-5）。

## 未解決事項

- なし（na の ref null 化を含めるかは plan で最終判断＝含める方向で仮決め。理由: reset と同型1行・writer 衛生の対称性）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-12-iter68-update-gate-ref-atomic-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

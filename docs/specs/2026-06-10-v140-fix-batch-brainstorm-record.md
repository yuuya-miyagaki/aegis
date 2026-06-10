# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-10

## テーマ

- 進化レビュー P2/P3 バッチ修正＋fail-open/closed ポリシー表＋B1 ドリル恒久修正（v1.4.0）

## コンテキスト

- 現在の状況: v1.3.3 で進化レビュー（docs/evolution-review-2026-06-10.md）の P1×2 は解消済み。P2×6・P3×6・K-2 が未着手。調査エージェントで全 finding が現コードで有効と再検証済み。
- きっかけ: STATUS.md next_action の候補①（P2 バッチ）＋②（B1 恒久修正）をユーザーが選択。進化レビュー構造的観察 3（fail-open/closed がアドホック）・4（size-skip の意味論混同）を個別修正と同時に系統ごと締める。

## 検討したアプローチ

### アプローチ A: 一括 fix-forward バッチ＋ポリシー表同時新設（＋B1 同梱）

- 概要: P2-1〜P2-6・P3-1〜P3-6・K-2 を 1 タスクで修正し、fail-open/closed ポリシー表を新設してテストで固定。B1 の docs/** 除外も同梱。
- 利点: 個別 finding は小さいが系統が同根（failure 時挙動のアドホック性）。ポリシー表と同時に直すと再発経路ごと閉じる。リリース 1 回で済む。
- 欠点: 対象ファイルが多く diff が大きい（L サイズ）。

### アプローチ B: ロードマップ通り 2 分割（P2-1+P2-6 先行 → 残りを後続）

- 概要: 進化レビュー §6 の順序のまま、宣言と実態の乖離（P2-1/P2-6）を S サイズで先行リリース。
- 利点: 1 リリースあたりの diff が小さい。
- 欠点: ゲート・リリースのオーバーヘッドが 2 倍。ポリシー表は結局後続バッチで必要になり、先行分の failure 挙動を二度触る。

### アプローチ C: E1（活動検証）brainstorm を優先し fix は後回し

- 概要: 進化の本丸である activity verification の設計に先に着手。
- 利点: 価値の大きいテーマに早く着手できる。
- 欠点: 土台（standard プロファイルの moat 不在等）に既知欠陥を残したまま新機構を設計することになり、brainstorm の前提が不安定。ロードマップ（fix-forward が先）にも反する。

## 決定

- 採用アプローチ: A
- 採用理由: finding の根が共通（failure 時方針の不在）であり、ポリシー表＋テーブル駆動テストを同時に作ることで個別修正が「表の執行」として一貫する。リリースコストも最小。
- 不採用理由: B はオーバーヘッドのみ増え、failure 挙動を二度触る。C は土台清掃前の設計着手で前提が不安定。

## サブ決定（AskUserQuestion で確定）

1. **ポリシー表の形態** = docs 表＋テーブル駆動テスト（テストが docs の Markdown 表をパースし実発火で突合。docs が宣言の単一ソース）。machine-readable ソース化は第 3 同期先になり YAGNI（R1 manifest 指摘と同型）で却下。docs のみは宣言と実態の drift が再発するため却下。
2. **P2-3 の size-skip 意味論** = ask（人間確認）に変更。S/M の deploy コマンドは emit_ask で確認を 1 回挟む。deny は task_size 緩和の意義を消すため却下。現状維持＋文書化は前提逆転（skip＝無検査許可）を温存するため却下。
3. **版数** = v1.4.0 minor。standard プロファイルの hook 構成変更・deploy gate 厳格化・ポリシー表という新契約 artifact を含むため。patch は install 先の体感挙動変更を隠すため却下。

## スコープ境界

- やること: P2-1〜P2-6、P3-1〜P3-6、K-2、docs/hook-failure-policy.md＋tests/test_failure_policy.py 新設、B1（run-test-strength-drill.py の docs/ 除外）、example mirror 同期、README 移行節、v1.4.0 リリース。
- やらないこと: K-1（LEARNINGS 解決済みマーク機構＝ロードマップ 4 番・次回以降）、E1〜E6、check-gate のマニフェスト照合移行（P1-2 恒久案・別タスク）、プロファイル体系の再編。

## 未解決事項

- なし（DEPLOY_RE の具体パターン、mkdir ロックのリトライ回数等の実装詳細は plan で確定）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-10-v140-fix-batch-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

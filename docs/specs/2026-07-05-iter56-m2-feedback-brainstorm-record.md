# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-05

## テーマ

- iter56: ドッグフード二周目（M2）フィードバック反映 — 候補6件＋可視性小玉2件

## コンテキスト

- 現在の状況: iter55 / v1.16.0 完全クローズ・M2 ドッグフード完走（回帰0・チェックリスト6/6）。
  M2 で露出した新種摩擦6件が backlog に根因裏取り付きで起票済み
  （`docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md`）。
- きっかけ: M2 実測データ。全件が「実使用で観測された摩擦」であり内部空想ではない。
- 本セッションでの再裏取り: 候補6件すべての根因引用行（check-secrets.sh:149・
  build-judge-card.py:376/382-385・check_status.py:150/1013・full.json 8本 vs
  manifest 実行可12本・qa-verification SKILL.md 通常/skip 両経路・subagent-dev
  並列規則）を現コードで再確認済み。ドリフトなし。

## 検討したアプローチ

### アプローチ A: 候補6件＋可視性小玉2件を1イテレーション一括（採用）

- 概要: P1（①⑥②）→P2（③⑤④）→P3（⑦=judge 文言の是正手順・テンプレ claims 雛形）を
  一括で TDD 実装。
- 利点: 全件独立・同一ファイル圏の重なりが大きい（build-judge-card.py は②③⑦、
  テンプレは②⑦）。ゲート一周のオーバーヘッドを1回に集約。
- 欠点: L 規模・moat 変更（check-secrets）を含み全ゲート必須。

### アプローチ B: P1 のみ先行（①⑥②）、P2/P3 は iter57

- 概要: moat バグと install 契約の穴だけ先に閉じる。
- 利点: イテレーションが小さい（M 相当）。
- 欠点: P2 は全て数行〜docs のみで分割の節約が小さい。ゲート一周が2回になり
  トータルコストは増える。M2 の ack 形骸化リスク（③）を放置する期間が延びる。

### アプローチ C: ②を judge 側フォールバックで解決（skill は不変更）

- 概要: judge が drill-skip 検出時に `docs/qa-reports/` の claims へフォールバック読取。
- 利点: 配布 skill の文言変更なし。
- 欠点: ref 単一原則（judge は ref 先しか見ない）を壊し、暗黙探索＝第2の証拠経路を
  judge に持ち込む。framework repo 自身が罠(p) で確立した「claims 付き qa レポートを
  ref にする」運用と二重化する。single-owner 教訓に反する。

## 決定

- 採用アプローチ: A（一括・⑦同梱）
- 採用理由: 全件が M2 実測摩擦で YAGNI に反しない。独立6件は backlog が
  「1イテレーション一括が効率的」と評価済み。⑦は②③と同一ファイル圏の数行で、
  M2 で実測された可視性摩擦（judge deny 文面に是正手順なし・テンプレに claims 雛形なし）
  への直接対処。grill-plan で過剰と判定されれば descope 可能。

## スコープ境界

- 対象: backlog 候補①〜⑥＋⑦（judge 文言・テンプレ claims 雛形）
- 対象外（iter56 では見送り・backlog「候補外」に記録済み）:
  grep 交替演算子 deny（頻度待ち）／原因不明 deny 1件（情報不足）／
  repo 直下 prose carve-out の非 *.md 拡張（fail-closed として妥当）／
  qa-browser 途中停止の根治（retro Try#2=委譲プロンプト改善として別トラック）／
  構造リアーキ（iter56 後の最有力テーマとして保持）

## 未解決事項

- ⑤の実装位置（check_status.py のゲート検査出力 vs update-gate.sh）は plan で確定
- ③の notes 要旨表示は `second_opinion.notes` キーが claims に存在する場合のみ
  （narrow YAML subset の制約内で読める形式に限る）

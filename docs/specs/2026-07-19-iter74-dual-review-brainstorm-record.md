# ブレインストーミング記録

## 日付
2026-07-19

## テーマ
Aegis 自己網羅レビューの二重化（Codex＝外部/隔離 clone ＋ Fable＝盲検2次/隔離 clone）と、2出力を突合した改善ロードマップ策定（iter74）。

## コンテキスト
- iter73 完了（HEAD `77566eda7d15cb70d6ca68377fdbd764834d6fe5`・v1.31.1・全 dev ゲート approved・完全クローズ）。
- 73 iterations・1300+ tests まで育ち、**配布前**の段階。North Star＝「知識の乏しい人が AI と堅牢に作り運用できる足場」。
- STATUS next_action に「Fable+Codex 二重網羅レビュー」が iter74+ 残トラックとして起票済み。前回網羅レビュー正本＝`docs/full-review-2026-07-06-six-dimensions-evolution.md`（R1〜R10）。
- ※本 record の brainstorming はセッション内対話で実施済み（公式 brainstorming スキルの Q&A は再走せず、合意済み設計をここに記録）。

## 検討したアプローチ

### アプローチ A: 単一レビュー（前回同型の6次元 fan-out）
- 一貫した観点だが、単一モデルの盲点・anchoring を排除できない。却下（今回は二重化が目的）。

### アプローチ B: 観点分業型の二重レビュー
- Codex と Fable に別々の観点を割り振る。網羅は広がるが、**同一対象での乖離が測れず**、二重化の最大価値（divergence＝バグの在処）を失う。却下。

### アプローチ C: 層1共通＋層2特化ハイブリッド（採用）
- **層1（共通6次元・逐語同一チャーターで盲検並行）**: moat バイパス / SF 再裁定 / locale-byte / test-strength / 前回fix regression / North Star 複雑性収支。ここでの乖離を最重要シグナルとして測る。
- **層2（非重複の特化）**: Codex＝fresh-eyes 配布/オンボーディング実測（外部視点の固有優位）、Fable＝ハーネス結合度/context経済/モデルポリシー（Claude Code 内部知識の固有優位）。

## 決定
1. アプローチ C を採用。
2. **North Star 複雑性収支を層1共通**へ（insider=Fable と outsider=Codex の乖離が「作りすぎか否か」の最重要判定になるため）。
3. **盲検・実証必須・read-only**を両者に課す（iter60 tree 破壊事故を制約に継承＝復元操作も禁止）。
4. **突合は第3文書（親専用）に分離**。ID 規約 `<次元>-<連番>`・severity ルーブリック・生出力逐語貼付・環境/SHA固定・fresh-first・完了規律を両指示文へ反映（grill-plan 指摘の致命5＋要検討5 を全反映済み）。
5. 対象コミットは `77566ed` に固定（rollover でHEADが動いてもレビューは clone を 77566ed に checkout）。

## スコープ境界
- **含む**: レビュー方法論の確定（3文書）・二重レビュー実施・突合裁定・iter74+ 改善ロードマップ策定。
- **含まない**: ロードマップ上の個別 fix の実装（各々が後続 iteration）。SF-014 恒久策（execution attestation）の実装（レビューで pressure-test 後）。

## 未解決事項
1. **iter74 の size / gate モデル**: 成果物が分析ドキュメント（本番コード非変更）で、review/qa/security/deploy ゲートが馴染まない。フレームワークに「research/analysis iteration type」が無い＝これ自体が North Star 次元の指摘候補。→ brainstorm Step D でユーザー判断。
2. **Codex の実行主体**: Codex は外部 CLI で当セッションからは起動不可。ユーザーが hook-free の隔離 clone で実行。
3. **Fable の実行環境**: 当セッションの Aegis moat フックが有効なままだと、破壊文字列テストで permission prompt が割り込む＝盲検/hook-free には別 clone/別セッションが要る。

## 次のステップ
brainstorm gate（size/gate モデルの合意含む）→ plan（実行計画＝merge protocol を正式化）→ implement（2レビュー実行→回収）→ 突合裁定 → ロードマップ正本化。

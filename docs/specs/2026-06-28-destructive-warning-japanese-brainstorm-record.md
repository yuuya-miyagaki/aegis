# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-28（iteration 53）

## テーマ

- 破壊的コマンド警告の日本語化＋ドリフトガード

## コンテキスト

- 現在の状況: hook は破壊的コマンド（rm -r, DROP TABLE, git push --force, dd, mkfs, shred, reset --hard 等）を permission prompt（ask）で止め、reason を `permissionDecisionReason` として確認 UI に表示する（emit.sh:52-56）。framework の CLAUDE.md／skills／他の全 hook プロンプト（control-plane／secrets／skill-gate／cron-gate／tdd／deploy-gate）は日本語だが、**破壊的 WARN 群だけが英語**（patterns.sh:15-57, check-destructive.sh:88）。北極星は日本語話者の知識の乏しい運用者。
- きっかけ: iteration 53 は当初「確認の平易化 slice2（汎用 reason 平易化）」として提案されたが、grill-premise＋実コード調査で premise が falsify された。①技術ゲート＝reason は ask 決定時に UI へ surface される（PASS）、②しかし reason 注入＋平易な日本語化は control-plane/secrets 等で**既に実装済み**＝汎用平易化は YAGNI。代わりに監査で「最高リスクの破壊的コマンド警告だけが英語」という客観的・検証可能・安全関連の欠陥を発見し、テーマを reframe した。

## 検討したアプローチ

### アプローチ A: format「破壊的: <コマンド>。<何が起きるか>（<復元可否>）。」＋日本語文字必須ドリフトガード

- 概要: WARN 本文のみを日本語化（判定 regex 無改変）。コマンドトークン（rm -r 等）は原文保持。ドリフトガードは patterns.sh の WARN 配列を `bash -c 'source'` で読み出し、各要素に日本語文字（ひらがな/カタカナ/漢字）が1つ以上含まれることを assert。
- 利点: 既存 JP プロンプトの「結果＋確認/復元の注記」様式に揃う。コマンドトークン保持で正確。novice の判断に最も効く「元に戻せるか」を全件明示。ASCII 技術トークンを許しつつ将来の英語混入を RED 化（誤検知しない）。
- 欠点: 訳語の品質ばらつきは人手レビュー依存。フォールバック2件は配列外で個別カバーが要る。

### アプローチ B: novice 寄せの冗長版（prefix「危険:」＋噛み砕き）

- 概要: より口語的・冗長な説明。
- 利点: より平易。
- 欠点: 18 件の統一感が緩む。冗長。既存 JP プロンプト様式から外れる。

### アプローチ C: 近似逐語の簡潔版

- 概要: 「破壊的: SQL DROP を検出。」のように現状の簡潔さを維持し日本語化のみ。
- 利点: 最小変更。
- 欠点: 「何が起きるか／復元可否」の判断材料が薄く、novice 支援として弱い。

## 決定

- 採用アプローチ: A
- 採用理由: 既存様式との一貫性・正確性・復元可否の明示（novice の判断材料）・誤検知しないドリフトガード。
- 不採用理由: B は冗長で統一感が緩む。C は判断材料が薄い。

## スコープ境界

- やること: patterns.sh の WARN 配列 18 件＋check-destructive.sh の inline rm -r WARN＋check-destructive.sh / check-secrets.sh の英語フォールバック2件を日本語化。ドリフトガード＋発火テストを新規テストファイルに追加。
- やらないこと: 判定ロジック（正規表現・ask 発火・パターン照合）は無改変＝moat 不変。deploy-gate／skill-gate／cron-gate／control-plane／secrets（変数系）／tdd の ask 文は**既に日本語**＝対象外。`[careful]` 等の英語ブラケットタグは他 hook と統一のため据置。Edit/Write/MCP プロンプトや汎用 reason 平易化は対象外。

## 未解決事項

- 英語フォールバック2件（抽出失敗パス）の発火テストが容易に再現できるか。困難ならソースレベルで当該 emit_ask 行に日本語必須を assert（plan で確定）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-28-destructive-warning-japanese-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

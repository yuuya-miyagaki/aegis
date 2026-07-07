# 納品サマリー — iteration 61（v1.22.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.22.0（iter61）
- 日付: 2026-07-07
- 担当者: aegis dev フロー（多エージェント・盲検2次）
- 操作マニュアル: 不要（内部 enforcement 変更＝エンドユーザー操作面の変化なし。新 ask は事故防止の確認のみ）
- 運用 RUNBOOK: 不要（既存 hook の挙動追加・新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲

- 完了: iter60 で発生した「検証サブエージェントによる親の未コミット作業の破壊」事故クラスへの機械防御（full-review 2026-07-06 R1 の機械層・復旧層）。
  1. **破壊コマンド検知の拡張**（hooks/lib/patterns.sh・9パターン）: `git checkout <パス>`（glob/末尾スラッシュ/複数引数/`--`/`-f`）・`git restore`・`git stash`（fd redirect 含む）を確認プロンプト（ask）対象に追加。ブランチ切替・`git stash pop/list`・`restore --staged` 等の良性形は従来どおり素通り（誤爆ゼロを実証）。
  2. **復旧アンカーの保全**（hooks/lib/snapshot.sh・session-start.sh）: revert 事故後にセッションを再開しても、承認済みゲートを記録した snapshot が上書き消失しないよう、退行を検知したら snapshot を温存し復旧手順を日本語で警告表示する。
- 保留: 委譲文言層（検証サブエージェントへの read-only・tree 変更禁止の明示）は iter62、setup.sh の OS-lock self-heal は iter63（full-review Phase 0 の後続）。

## 証拠

- 仕様: docs/plans/2026-07-07-iter61-incident-class-machine-defense-plan.md（Rev.5）
- レビュー: docs/qa-reports/iter61-review.md（1次 approve＋盲検2次 approve_with_notes・fix-forward 済）
- QA: docs/qa-reports/iter61-qa.md（full 1061 passed＋B1 mutation drill 9/9 caught）
- セキュリティ: docs/qa-reports/iter61-security.md（1次 approve＋盲検2次 approve_with_notes・Major2件は ship 前 fix-forward 済・residual なし）
- 動機の正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1

## 既知のギャップ

- 単一 bare パスの `git checkout`（glob 等なし）はブランチ切替と構文上区別不能ゆえ非対象（iter62 の委譲文言層で被覆）。
- mid-session の Bash revert 後に親自身が gate を再承認する経路は session 境界の外（設計上のスコープ外・plan 残余に明記）。
- いずれも accident-prevention スコープ（ask＝確認）。敵対的バイパスの完全封鎖は OS-lock（主 moat）と委譲文言層の役割。

## 配備と運用

- 環境: Claude Code ネイティブ（hooks PaC）。既存インストールへは通常の upgrade で反映（※現時点の upgrade×OS-lock 衝突は full-review R3・iter63 で解消予定）。
- アクセス: 変更なし。
- 監視: なし（enforcement の挙動追加のみ）。

## 次の推奨アクション

- iter62: 委譲拘束の SoT 標準化（routing.md に検証系委譲雛形＋tree 変更禁止・token-pin）＝R1 文言層。
- iter63: setup.sh の self-heal unlock（R3）。
- 以降: full-review §4 Phase 1（罠の根切り: fingerprint tree-hash 化・judge skip-and-continue 等）。

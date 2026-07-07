# 納品サマリー — iteration 62（v1.23.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.23.0（iter62）
- 日付: 2026-07-07
- 担当者: aegis dev フロー（多エージェント・盲検2次）
- 操作マニュアル: 不要（guidance 層の変更＝エンドユーザー操作面の変化なし）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲

- 完了: 委譲拘束の SoT 標準化（full-review 2026-07-06 R1 の**文言層**＝iter60 事故クラス3層防御の最終層）。
  1. **単一正本の設置**（.claude/rules/routing.md「Verification delegation」節）: 検証系ディスパッチ全種（review 1次/盲検2次・security・qa・qa-browser・specialist reviewers）の標準6拘束を定義。6点目 read-only は無条件＝既存ファイル変更禁止・`git checkout/restore/reset/clean/stash` 実行禁止・書込みは指定パスへの新規 evidence 成果物のみ・tree が汚れたら停止して報告し自己復旧しない。
  2. **4経路からの参照＋核のインライン**: qa-verification（qa-browser 委譲ルールに6点目）・aegis-review-gate／aegis-security-gate（盲検2次の委譲プロンプトへ6拘束を必ず含める）・subagent-dev（コアルール5点目）。iter60 で実際に事故を起こした security 盲検2次経路を含む全経路を被覆。
  3. **drift の機械封鎖**（tests/test_skill_guidance_tokens.py・pin 9本）: 見出し一意（count==1）・否定句2本（MUST NOT modify／MUST NOT run＝反転検知）・禁止コマンド連結列挙（1個脱落で RED）・汚染時プロトコル・無条件宣言・4経路の参照＋核・SendMessage 一意性（iter59 pin の増殖崩壊も封鎖）。
  4. **budget 簿記**: routing 70→181・qa-verification 455→459（実測と厳密一致＝追加分ちょうどの raise・iter59 教訓準拠）。
- 本 iter で dev フロー自体が新拘束を自己適用（レビュー/検証の全11+2エージェント委譲に6拘束を明記）＝ドッグフード済み。

## 証拠

- 仕様: docs/plans/2026-07-07-iter62-delegation-constraints-sot-plan.md（grill-plan 致命3反映）
- レビュー: docs/qa-reports/iter62-review.md（1次 approve〔xhigh 10角度→6検証→sweep〕＋盲検2次 approve_with_notes・fix-forward 2件済）
- QA: docs/qa-reports/iter62-qa.md（full 1071 passed＋**B1 実 drill 11/11 caught・skip なし**）
- セキュリティ: docs/qa-reports/iter62-security.md（1次 approve＋盲検2次 approve_with_notes・Major-1〔drill の pyc キャッシュ汚染＝diff 外の runner 欠陥〕は ship 前解消済）
- デプロイ: docs/qa-reports/iter62-deploy.md（対象なし宣言・全 prior gate 確認）
- 動機の正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1・§4 Phase 0-1

## 既知のギャップ

- 文言層は self-attested（親が拘束を委譲プロンプトへ実際に含めることはハーネス強制不能）＝機械層（iter61 patterns.sh）・復旧層（snapshot 退行ガード）との3層防御で被覆。将来の SubagentStart hook 注入は full-review 将来項目。
- 禁止列挙に `git switch` は含めない（機械層が branch switch を意図的に allow＝誤爆ゼロ方針と整合。破壊形は一般禁止句が防衛線）— 列挙追加は文言・機械の両層セットで別テーマ。
- 「assigned path」の指定責務（委譲時に書込み先パスを必ず明示）は同別テーマで文言化予定。
- **drill runner の pyc キャッシュ汚染**（同バイト長 mutant＋同秒 revert で macOS ミラーキャッシュに変異バイトコードが残留→偽 RED/偽 GREEN）: 恒久対策＝子プロセスへ `PYTHONDONTWRITEBYTECODE=1`＋restore 後 mtime バンプを Phase 1-5（drill 強化）へ起票。

## 配備と運用

- 環境: Claude Code ネイティブ。rules/skills は setup.sh で verbatim 配布（新規 script/hook なし＝contract 変更不要）。
- アクセス: 変更なし。
- 監視: なし。

## 次の推奨アクション

- iter63: setup.sh の self-heal unlock（R3・正規 upgrade が locked install で死ぬ問題）。
- 以降: full-review §4 Phase 1（罠の根切り: fingerprint tree-hash 化・judge skip-and-continue・S サイズ修復・approve --ref 原子化・**drill NO_RUN 拒否＋pyc キャッシュ対策**）。

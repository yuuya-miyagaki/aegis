# 設計ノート

## 入力

- ブレインストーミング記録: docs/specs/2026-07-07-iter62-delegation-constraints-sot-brainstorm-record.md
- 要件: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1 修正方向(1)・§4 Phase 0-1

## 問題整理

- 背景: iter60 事故（検証サブエージェントの `git checkout docs/*` が親セッションの未コミット
  gate 簿記を revert）。iter61 で機械層（destructive patterns）＋復旧層（snapshot 退行ガード）は
  封鎖済み。文言層＝委譲プロンプトに載せる拘束の正本が `.claude/` に存在しない（grep 0 件）。
- 判断が必要な論点: (1) 正本の置き場所と粒度 (2) 消費側の参照形 (3) drift 封鎖方式
  (4) routing.md budget（headroom 0）の扱い。
- 制約条件: thin L0 哲学（routing.md は簡潔英語）／budget ratchet（raise は正当理由必須）／
  budget-exclude 濫用ガード（routing.md は roster 1 領域のみ許可）／
  既存 token-pin（TestQaBrowserDelegation ほか）を壊さない。

## 推奨アプローチ

- 採用方針: routing.md「## Verification delegation」節＝6拘束の単一正本（英語）＋
  4消費側（qa-verification／aegis-review-gate／aegis-security-gate／subagent-dev）参照＋
  token-pin（否定句・一意性）＋budget 追加分ちょうど raise。
- 採用理由: SoT で修正が全経路へ伝播。iter59（SendMessage SoT を routing.md に設置）と同型の先例。
  pin で silent 消失・意味反転を決定論検知。
- 検討した代替案と不採用理由: 全文複製（drift 再発＝R1 構造そのもの）／
  budget-exclude（region==content 完全一致 pin が言い換え false RED・濫用ガード改修増）。
  詳細はブレインストーミング記録。

## コンポーネント分解

- 分割方針: 正本1・消費4・pin 1・簿記1 の7ファイル（L）。

- 各ユニットの責務:
  - ユニット A（正本）: `.claude/rules/routing.md` — 「## Verification delegation」節を
    「## Subagent continuation」の直後に追加。内容（英語・簡潔）:
    - 適用対象: 検証系ディスパッチ全部（review 1次/盲検2次・security・qa・qa-browser・
      specialist reviewers）。委譲プロンプトに拘束を明記させる。
    - 6拘束: 1. Split（有界・連番バッチ） 2. Completion（全項目のエビデンスが揃うまで
      final 報告禁止・partial を final と偽らない） 3. Resume（SendMessage 継続＝上節参照）
      4. Progress（項目ごと報告） 5. Evidence（項目ごと {操作/期待/実測/判定}）
      6. **Read-only（無条件）**: 既存ファイルの変更禁止・
      `git checkout/restore/reset/clean/stash` 実行禁止・許可される書込みは指定パスへの
      新規 evidence 成果物のみ・tree が汚れたら停止して報告し自己復旧しない。
    - 適用規則1文: 「1-5 apply as written to itemized work; 6 is unconditional」
      （確定文言は plan A が正。盲検2次 Info-2 で設計書側の旧ニュアンス文言を追認訂正）。
  - ユニット B（qa 経路）: `qa-verification/SKILL.md` — 「qa-browser 委譲ルール」の5点に
    **6点目**を追加（JP・`tree 変更禁止` 核＋routing.md 正本参照）。既存5点と既存 pin は不変。
  - ユニット C（review 経路）: `aegis-review-gate/SKILL.md` — 「盲検 第2意見」節に
    「委譲プロンプトへ routing.md『Verification delegation』の6拘束（核=read-only・
    tree 変更禁止）を必ず含める」1-2行。
  - ユニット D（security 経路・iter60 事故経路）: `aegis-security-gate/SKILL.md` — C と同形。
  - ユニット E（subagent-dev 経路）: `subagent-dev/SKILL.md` — コアルールに5点目
    「レビュー/検証系サブエージェントの委譲プロンプトには routing.md
    『Verification delegation』の6拘束（核=read-only）を含める」（Step 3/3.5/4 の全
    reviewer ディスパッチをカバー）。
  - ユニット F（drift 封鎖）: `tests/test_skill_guidance_tokens.py` — 新クラスで pin:
    - routing.md: 見出し `## Verification delegation`（一意）／否定句 `MUST NOT`
      を含む read-only 核フレーズ／コマンド列挙 `checkout/restore/reset/clean/stash`
      （1コマンド脱落でも RED になる連結表記）／report-don't-touch 句。
    - 消費側4ファイル: `Verification delegation` 参照 token（各ファイル）＋
      read-only 核（`tree 変更禁止` 等）。
    - 一意性 assert（単一削除で RED・iter59 教訓）。
  - ユニット G（簿記）: `scripts/context-budgets.json` — routing.md 70→実数（追加分ちょうど）。
    qa-verification 449/455 は超過見込み→実数へ。C/D/E は headroom 内（26/24/14）なら据置。

## インターフェース定義

- 正本→消費: 節見出し文字列「Verification delegation」が参照キー（pin が両側を縛る）。
- 正本→Subagent continuation: 拘束3（Resume）は既存節へ言及（重複定義しない）。
- pin テスト→md: 短核 token のみ（長文完全一致は言い換え false RED＝禁止・既存クラス踏襲）。

## エラー処理

- 意味反転: 否定句 pin（`MUST NOT ...` を句ごと）で "NOT" 脱落を捕捉（iter59 教訓）。
- 部分脱落: コマンド列挙は `/` 連結の単一 token として pin → 1個削っても RED。
- 参照切れ: 消費側4ファイルの参照 pin で正本改名・節削除を検知（両側 pin）。
- qa-browser の screenshot 等: 「新規 evidence 成果物の追加のみ可」で read-only と両立。

## テスト戦略

- TDD RED-first: ユニット F の pin テストを先に書き、md 未編集で RED を実証→A-E 編集で GREEN。
- 既存 pin（TestQaBrowserDelegation 等）の GREEN 維持を同時確認。
- B1 drill: 第一候補＝実 mutant（md 追加行の token 削除/否定反転→pin テスト赤化）。
  test/json ハンクが coverage floor を割る場合は iter59/60 前例＝`{"skip":true,...}`＋
  手動 mutation 実証（reason に明記）へ切替。
- full suite green・contract PASS を qa で確認。

## バージョン

- v1.22.0 → v1.23.0（MINOR・guidance 新設）。bump 3箇所（ship 時に grep で特定）。

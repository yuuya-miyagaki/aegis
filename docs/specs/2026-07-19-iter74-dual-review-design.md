# 設計ノート — iter74 二重網羅レビュー方法論

## 入力
- レビュー対象: Aegis フレームワーク全体（HEAD `77566eda7d15cb70d6ca68377fdbd764834d6fe5`＝iter73 完了状態）。
- 既知: `docs/security-followups.md`（SF-001〜016）・`docs/full-review-2026-07-06-six-dimensions-evolution.md`（R1〜R10）・`docs/LEARNINGS.md`・`docs/STATUS.md`。
- 目的: 73 iter/1300+ tests・配布前のフレームワークを、異種2モデルで盲検並行レビューし、乖離を実証裁定して改善ロードマップに落とす。

## 問題整理
- 単一レビューは単一モデルの盲点・anchoring を排除できない。
- iter72 実績: 1次(opus)=approve と盲検2次(fable)=reject の**乖離の場所に High 級バグ**（F-CRIT-1）。→ 「一致＝高確度／乖離＝バグの在処」を設計原理に据える。
- 一般論ベストプラクティスのノイズは突合コストを増やす害。North Star 基準の判定を強制する。

## 推奨アプローチ
2層ハイブリッド盲検レビュー（詳細はアプローチ C＝brainstorm-record 参照）。
- 層1: 共通6次元を逐語同一チャーターで盲検並行（乖離を測る本体）。
- 層2: Codex＝fresh-eyes 配布監査／Fable＝ハーネス結合度・context経済・モデルポリシー（非重複）。
- 実証必須・read-only・出力スキーマ統一。

## コンポーネント分解
本方法論は3文書で構成（いずれも本 spec と同ディレクトリ）:
1. `2026-07-19-iter74-codex-review-instruction.md` — Codex（外部/隔離 clone）向け入力パケット。
2. `2026-07-19-iter74-fable-review-instruction.md` — Fable（盲検2次/隔離 clone）向け入力パケット。
3. `2026-07-19-iter74-merge-adjudication-protocol.md` — 親専用。突合・実走裁定・ロードマップ化の手順（**レビュアーには渡さない**）。

## インターフェース定義
出力スキーマは両レビュアーで統一（突合のため）:
- **ID 規約**: `<次元プレフィックス>-<連番>`。層1の6プレフィックス（MOAT/SF/LOCALE/TEST/REGR/NORTH）は両者逐語一致。層2は Codex=DIST／Fable=HARNESS/CTX/MODEL。白紙 top3=FRESH-1/2/3。
- **severity ルーブリック**: Critical/High/Medium/Low/Info を1行ずつ定義（到達可能性で較正・iter73 教訓）。
- **証拠**: `reproduced` は実行コマンド＋生出力の該当行を逐語貼付（要約不可）。無ければ hypothesis 扱い。
- **各所見**: {ID, 次元, severity, confidence, 新規性, 主張, 証拠(file:line＋生出力), North Star 影響, 修正方向(effort S/M/L)}。

## データフロー / 構造
1. 親が clone ×2 を SHA `77566ed` で用意（read-only）。
2. Codex を隔離 clone で起動（外部 CLI・ユーザー実行）／Fable を clean context で起動（設計文脈を持ち込まない）。
3. 各レビュアーが fresh-first（白紙 top3 → 既知照合）→ 層1 → 層2 の順で走り、成果物を各 clone の `docs/` に出力。
4. 親が両成果物を回収 → 健全性チェック（環境/SHA/生出力/PARTIAL）→ 次元内マッチで3分類（一致/片方のみ/乖離）。
5. 親が乖離・片方のみを**実走裁定**（生出力を再現・環境差の切り分け・到達可能性の較正）。
6. 確定所見を impact×effort でロードマップ化（iter75+ にテーマ分割）。

## 依存関係
- **Codex 実行はユーザー**（外部 CLI・当セッションから起動不可）。
- **Fable は hook-free の隔離 clone/別セッション**が必要（当セッションの moat フックが破壊文字列テストで割り込むため）。
- 対象 SHA 固定（HEAD 不一致なら各レビュアーは中断）。
- 実行環境（OS/grep BSD-GNU/bash/python/locale）の記録が突合の生命線。

## エラーハンドリング
- HEAD ≠ 77566ed → レビュアーは中断・報告（別コミットの突合は無効）。
- 途中終了 → `STATUS: PARTIAL` と未着手次元の明示（partial は final ではない＝routing.md 原則の継承）。
- 環境差起因の乖離 → 「真の乖離」ではなく移植性所見として別枠（それ自体が locale/byte 次元の新規指摘になりうる）。

## テスト戦略
- 本方法論（3文書）自体を `grill-plan` で検証済み。致命5（突合プロトコル/生出力/環境SHA/完了規律/anchoring）＋要検討5（severityルーブリック/複雑性証拠形式/盲検起動条件/層2負荷/脅威モデル）を全反映。

## 次のステップ
brainstorm gate（size/gate モデルの合意）→ plan（merge protocol を実行計画として正式化）→ implement（2レビュー実行）。

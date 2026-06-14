# Aegis 進化ロードマップ（比較レビュー由来）

- 作成日: 2026-06-14
- 出典: 9フレームワーク比較レビュー（`framework-comparison-2026-06-14.md`・workspace 直下）の §5-3「Aegis が学べるネタ」を、北極星で取捨選択した結果。
- 位置づけ: 優先順位付きバックログ。**P1 から順に**、各施策ごとに通常フロー（brainstorm→設計書→grill-plan→TDD→grill-code）で実装する。

## 評価基準

1. **北極星適合**: 非エンジニアが上流〜保守まで非スラップを作れる／harness=構造・段階開示・ゲート・可視化／LLM=判断レビュー。
2. **既存の強みを活かすか**: 決定論的強制（PaC hook）と自己検証（contract/drift/eval＋テスト）。借り物でなく Aegis の土俵に乗るか。
3. **労力・リスク**。
4. **YAGNI**: Aegis のニッチ（Claude Code 専用・非エンジニア・thin）に本当に要るか。大型 OSS の機能を闇雲に真似ない。

## 優先順位

| 優先 | 施策 | 北極星適合 | 労力/リスク | 状態 |
|------|------|-----------|------------|------|
| **P1** | 決定論的コンテキスト予算チェック（サイズ予算＋tighten-only ratchet） | 最高 | 低〜中 / 低 | 次に設計 |
| **P2** | spec delta review（Client モード・非エンジニア向け変更把握） | 高 | 低 / 低 | backlog |
| **P3** | skill 挙動圧力テスト（実エージェントで遵守を adversarial 検証） | 中 | 中〜高 / 中 | backlog |
| **P4** | 実ブラウザ QA 一級市民化 ＋ クロスモデル second-opinion 自動化 | 中〜低 | 高 / 中〜高 | someday |
| **P5** | 決定論強制＋自己検証を差別化として positioning（配布時） | 高（訴求） | 低 / 低 | 配布フェーズ |

## 各施策の詳細

### P1 — 決定論的コンテキスト予算チェック（採用・最優先）
GSD の「バイト予算＋tighten-only ratchet」を Aegis の自己検査機構に転用する。always-on（CLAUDE.md/STATUS.md）と phase ロードされる文脈ファイル（skills/refs）にサイズ上限（予算）を持たせ、超過を contract/drift と同系の**決定論チェックで FAIL** させる。ratchet は「予算は縮小のみ可・拡大は明示的更新が要る」ため、肥大が静かに進むのを機械的に封じる。Aegis の「thin working context」を*ポリシー*から*保証*へ格上げし、決定論 moat と既存自己検査に素直に乗る。**注**: GSD の「フラット skill 列挙を圧縮する2段ルーティング」は Aegis が既に phase スコープ化済みのため**不要**。転用するのは予算＋ratchet の部分のみ。既存にサイズ予算機構は無い（net-new）。

### P2 — spec delta review（Client モード）
spec-kit/OpenSpec の「コードを読まずに変更を高レベルで把握・レビューする」語彙と軽い検査を、Aegis の Client モード（要件→handover）に取り入れる。非エンジニアが「何がどう変わるか」をコード非依存で確認できる＝『LLM=判断・可視化』に合致。既存の Client gate（6成果物＋内容検査）に上乗せする小規模拡張。レバレッジは P1 未満のため P2。

### P3 — skill 挙動圧力テスト
superpowers の writing-skills（skill を「テスト済みコード」として RED-GREEN で鍛える）に倣い、Aegis の skill が実エージェント下で adversarial プロンプトでも遵守されるかを検証する。自己検証（強み）を一段深める。ただし実エージェント実行はコスト/flake が高く、かつ Aegis は hook で強制するため「skill 遵守」依存度が superpowers より低い＝限界価値が中。テスト基盤拡張が前提。

### P4 — 実ブラウザ QA ＋ クロスモデル second-opinion（someday）
gstack の browse/（実 DOM QA）と /codex（クロスモデル second opinion）。重量級ビルド＋外部依存で thin ethos に逆行し、クロスモデルは既に「3失敗→second-opinion.md→IDE チャット」の手動運用で代替済み。Aegis のニッチには過剰のため someday 枠。着手するなら qa-browser 拡張から最小で。

### P5 — positioning（配布フェーズ）
「決定論的強制＋自己契約検査」は人気 OSS（spec-kit/BMAD/GSD/superpowers）が軒並み弱い領域＝Aegis の明確な差別化。機能でなく訴求の問題なので、自分用先行（C ルート）から配布物化に移る段階で README/docs に前面化する。

## 進め方

P1 → P2 → P3 の順に着手。各施策は独立した spec/plan/実装サイクルを持つ。P4 は要否を再評価してから、P5 は配布判断時に。

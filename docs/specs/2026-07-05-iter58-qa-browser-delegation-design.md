# 設計ノート — iter58 qa-browser 委譲プロンプト標準化
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-05-iter58-qa-browser-delegation-brainstorm-record.md`
- 要件: なし（framework 自己改修）。一次情報＝iter56 backlog Try#2・DOGFOOD-M2 観測（qa-browser 途中停止）。

## 問題整理

- 背景: ui_surface QA でメインの qa エージェントが qa-browser サブエージェントにブラウザ検証を委譲するが、
  長尺バッチで qa-browser が**途中停止**し、未完のまま「最終報告」を返すことがある（19項目一括で3回）。
  iter56 で「1委譲5項目分割」は skill に入れたが、「全項目完了まで最終報告を出さない」拘束と
  再開プロトコルが標準化されていない。
- 判断が必要な論点: スコープ（guidance のみ vs 決定論バックストップ）＝**guidance のみに決定**（ユーザー）。
- 制約条件: 委譲プロンプトは本質的にモデル guidance（hook で決定論強制できない）。よって「guidance の
  silent 消失を防ぐ決定論トリップワイヤ（トークン pin）」で aegis の『harness=構造/LLM=判断』に整合させる。

## 推奨アプローチ

- `qa-verification SKILL.md` の「qa-browser 委譲ルール」節を、qa エージェントが qa-browser へ渡す
  **標準委譲プロンプト雛形**に置換（guidance）。加えて load-bearing トークンをテストで pin（決定論トリップワイヤ）。
- 代替案（Option 2 決定論的完了バックストップ・Option 3 browser-assist テンプレ化）は record のとおり descope。

## コンポーネント分解

- **`qa-verification SKILL.md`（改修）**: 「qa-browser 委譲ルール」節を標準委譲プロンプト雛形へ。拘束5点:
  1. **分割**: 1委譲あたり検証項目 ≤5・各項目に連番（`1) … 2) …`）。
  2. **完了拘束**: 委譲した**全項目にエビデンス（PASS/FAIL＋根拠）が揃うまで最終報告を出さない**。
     途中で止まる場合は「完了済/未完の項目番号」を明示し、partial を final と偽らない。
  3. **再開プロトコル**: 途中停止時は**新規委譲でなく SendMessage で同一エージェントを継続**（コンテキスト保持）。
  4. **進捗**: 各項目完了ごとに `[n/N done]` を報告（途中停止の検出・再開のため）。
  5. **エビデンス形式**: 項目ごとに `{項目, 操作, 期待, 実測, PASS/FAIL, screenshot/console 参照}`。
- **`tests/test_skill_guidance_tokens.py`（改修）**: qa-verification の load-bearing トークンに、
  完了拘束フレーズ（例: 「全項目完了まで最終報告」相当）・`SendMessage`・`5`（分割上限）を追加 pin。
  核心命令が消えたら FAIL（silent 消失の機械検出）。進捗形式など軟らかい要素は pin しない（過剰固定回避）。

### アーキテクチャ図

```mermaid
graph TD
    Q[qa エージェント<br>qa-verification skill] -->|標準委譲プロンプト<br>≤5項目・連番| B[qa-browser サブエージェント]
    B -->|項目ごと [n/N done]＋エビデンス| Q
    B -.->|途中停止| R{再開?}
    R -->|SendMessage で同一継続| B
    R -->|再開不能| BL[QA レポート blocker に未完項目記録<br>3-failure ルール]
    T[test_skill_guidance_tokens.py] -.->|load-bearing token pin<br>消失で FAIL| Q
```

## インターフェース定義

- 委譲プロンプト = qa→qa-browser の**自然言語プロンプト雛形**（機械契約ではない）。返却は上記エビデンス形式。
- token pin = テストが qa-verification SKILL.md 本文に必須トークンの存在を assert（部分一致でなく行/文脈で）。

## データフロー / 構造

- qa（ui_surface:true）→ 検証項目を ≤5 に分割 → 標準プロンプトで qa-browser に委譲 →
  qa-browser が項目順に実行・`[n/N done]` 報告 → 全項目エビデンス揃い次第まとめて最終報告 →
  qa がエビデンスを QA レポートに統合。途中停止 → SendMessage 再開 → それも不能なら blocker 記録。

## 依存関係

- `browser-assist` skill（$B/Playwright 操作基盤）: 不変。委譲プロンプトは両モード共通。
- `subagent-dev` / SendMessage: 再開プロトコルが依存（既存機構）。
- `context_budget`: qa-verification の語数予算を割らないこと（表現圧縮）。

## エラー処理

- qa-browser 停止かつ SendMessage 再開不能 → qa が未完項目を QA レポート blocker に記録・3-failure ルール適用。
- token pin テストは RED-first で「トークン削除→FAIL」を確認してから GREEN 化。

## テスト戦略

- `test_skill_guidance_tokens.py` に load-bearing トークン pin を追加（RED-first: 現行 skill から
  対象トークンを一時削除→FAIL 確認→復元→GREEN）。
- `check_reference_drift` / `context_budget check` PASS を維持。
- B1 drill: docs/skill 変更＝mutant 対象コードなしで SKIP＋RED-first 代替実証（token pin の RED 確認）。

## 移行・SemVer

- v1.18.0 → **v1.19.0（MINOR 想定）**: skill guidance の追加（後方互換・公開/運用契約は不変）。plan で最終確定。
- 規模 = **M**（qa-verification SKILL.md ＋ test_skill_guidance_tokens.py の2ファイル・framework・moat 非該当）。
  M framework は review+qa+security 必須・deploy 自動 exempt。

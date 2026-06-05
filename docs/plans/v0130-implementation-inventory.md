# v0.13.0 実装済み / 未済 棚卸し（Foundation F0-1）

> 作成日: 2026-06-05 / 目的: Foundation 着手前に「どこまで実装済みか」を確定し、後続「A: catch-up 吸収」フェーズのスコープ二重計上を防ぐ（Round 1 ⑨ / Round 2 への対応）。

## サマリ

| Phase | 内容 | 状態 | 根拠 |
|---|---|---|---|
| **0a** | hook 出力スキーマ移行 + `if` 削除 | ✅ **shipped** | tag `v0.12.2`（commit 9f672ce） |
| **0b** | 新 PreToolUse/event hook 4本・secrets/destructive 拡張・extract_exit_code 両対応・スキル改名 | ✅ **committed（未 tag/未 merge）** | commit `d6430c1`（2026-06-05、本セッションで確定） |
| **1** | subagent frontmatter（model/effort）・UserPromptSubmit/Stop hook・PreCompact 閾値・routing 拡張 | ⛔ **未着手** | 該当ファイルに変更なし |
| **2** | commands/skills frontmatter 整備・schedule/loop 連携 | ⛔ **未着手** | — |
| **3** | 哲学・README・INTEGRATION・version bump | ⛔ **未着手** | — |

現行テスト: **174 PASS**（`python3 -m unittest discover -s tests`）。

## Phase 0b の中身（commit d6430c1）

旧計画 `v0130-modernization-plan.md` の Phase 0b Task に対する実装状況:

| 旧 Task | 内容 | 状態 |
|---|---|---|
| 0b-1 | `check-skill-gate.sh` / `check-cron-gate.sh`（新 PreToolUse）+ deploy-mcp matcher | ✅ hook 存在・テスト有り（skill-gate/cron-gate）。deploy-mcp matcher 明示化は要確認 |
| 0b-2 | `check-task-created.sh`（continue:false hard stop）/ `check-task-completed.sh`（exit2 差し戻し）+ `.task-event-debug.log` gitignore | ✅ 両 hook 存在・テスト有り・.gitignore 追加済み |
| 0b-3 | secrets（PEM/SSH/credentials/service-account）・destructive（filter-branch/reflog/rimraf/find -delete 等）拡張 + `extract_exit_code` 両キー | ✅ 実装・テスト有り。実機検証ログ `docs/qa-reports/v0130-extract-exit-code.md` あり |
| 0b-4 | スキル改名 3 件（aegis-brainstorm/review-gate/security-gate）+ 全参照更新 | ✅ 改名・参照更新・minimal-project ミラー済み |

## Foundation（再アーキ）との関係

- **Phase 0b の実装スタイルは「旧 inline 方式」**（hook が出力 JSON を手書き・検知パターン inline・手書き escape）。これは Foundation が後で集約する対象であり、思想的矛盾ではない:
  - Foundation **F1（emit.sh）** が Phase 0b hook 含む全 hook の出力を1関数群に集約
  - Foundation **F2（patterns.sh）** が secrets/destructive パターンを単一真実へ
- **Phase 0b は model をハードコードしていない**（reviewer/security は `model: inherit` 維持）→ Foundation/後続フェーズの inherit-first 方針と整合。
- **CLAUDE.md の context 予算（L0–L3）は Phase 0b で未変更** → 新思想の「数値撤廃」は後続 R フェーズの担当。Phase 0b と非干渉。

## 後続「A: catch-up 吸収」フェーズへの含意（二重計上防止）

旧計画では「A フェーズで Phase 0b を新方式で実装」としていたが、**Phase 0b は既に実装・コミット済み**。よって A フェーズは「Phase 0b を*再実装*」ではなく:
1. Phase 0b hook を Foundation の emit.sh / patterns.sh へ**移行（refactor）**（F1/F2 が実施）
2. 残りの真の未実装（Phase 1/2/3）のみを新思想で実装

として再定義する。重複作業なし。

## version 状態（F0-2 で確定予定）

- `scripts/check_framework_contract.py`: `FRAMEWORK_VERSION = "0.12.0"`（**bump 漏れ。最後の ship は v0.12.2**）
- `docs/STATUS.md`: `framework_version: "0.13.0-pre"`（作業中版）
- `templates/STATUS.template.md`: `"0.12.0"`
- → F0-2 で owner=`FRAMEWORK_VERSION` を **0.12.2**（最後の ship）に確定、template を整合、STATUS は作業中版 0.13.0-pre 維持。

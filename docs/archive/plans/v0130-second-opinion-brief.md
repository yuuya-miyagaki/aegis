# Aegis v0.13.0 Modernization — Final Confirmation (Round 5)

> **Round 5 の位置付け**: 最終確認。Round 4 までで本質的な設計判断（hook 出力スキーマ、Plan 条件付き許可、effort 配分、4-C 使い分け、pre-compact.sh の Phase 0a 移管など）はすべて完了。本ブリーフは **Round 4 で受けた P1/P2 指摘 3 件 + 追加意見 2 件が Rev.5 で機械的に反映されたか** の確認のみを求める。
>
> **Round 1〜4 の判定経緯**: すべて GO with conditions、計 25 件の指摘 → 全反映済み
>
> **改訂後の本体プラン**: `docs/plans/v0130-modernization-plan.md`（Revision 5、約 500 行）

---

## 0. レビュアーへの依頼

以下を **確認のみ** お願いします（新たな設計判断は含まれません）：

1. § 1 の Round 4 指摘 3 件（P1×1, P2×2）への対応が反映されているか
2. § 2 の Round 4 追加意見 2 件への対応が反映されているか
3. § 3 の grep で見つかった隠れ残存箇所 6 件の修正が妥当か
4. **Phase 0a (v0.12.2) 即時実装着手 GO 判定**（最終）

---

## 1. Round 4 指摘 3 件への対応（Rev.5）

| # | 指摘 (Round 4) | 旧表現 (Rev.4) | 新表現 (Rev.5) | 該当行 |
|---|---|---|---|---|
| R4-1 (P1) | TaskCompleted が変更マップで `continue:false` のまま | `不整合時 {"continue": false, "stopReason": "..."}` | **`不整合時 exit code 2 + stderr に reason`（task action の差し戻し）** | line 146 |
| R4-2 (P2) | Verification が両 hook とも `continue:false` 前提 | `9. TaskCreated / TaskCompleted event hook が continue:false で制御` | **`9. TaskCreated event hook が {"continue": false, "stopReason": "..."} で hard stop、TaskCompleted event hook が exit code 2 + stderr で task 差し戻し`** | line 387 |
| R4-3 (P2) | TDD「各 hook で両ケース」が曖昧 | `TDD: 各 hook で hard stop / 差し戻しの両ケース` | **`TDD: TaskCreated は hard stop ケース + 通過ケース、TaskCompleted は差し戻しケース + 通過ケース`（hook 別に明示）** | line 285-287 |

---

## 2. Round 4 追加意見 2 件への対応（Rev.5）

| # | 追加意見 | 反映先 | 反映内容 |
|---|---|---|---|
| A1 | `raw_input` ダンプ先は git 管理外 / `.claude/` 配下の ignored path に限定（task_description に機密混入リスク） | Task 0b-2 | **「`.claude/.task-event-debug.log`（gitignore 対象）に限定、リポジトリ内のトラッキング対象には絶対に書かない」と明記。Deliverable に `.gitignore` 追加項目** |
| A2 | TaskCreated/Completed は matcher 非対応で必ず発火 → payload 正規化 + 早期 return テスト | Task 0b-2 TDD / QA / Verification | **「matcher 非対応で必ず発火するため不該当ケースの早期 return も必ずテスト」を明記** |

---

## 3. grep で見つかった隠れ残存箇所 6 件の修正

Round 4 レビュアーが指摘した 3 箇所以外に、私が grep で発見した同根の旧表現を Rev.5 で同時撲滅。すべて「TaskCreated と TaskCompleted を別々に書く」形へ統一：

| 行 | 場所 | Rev.5 修正後 |
|---|---|---|
| 78-79 | Context（出力スキーマ列挙） | TaskCreated（hard stop）と TaskCompleted（差し戻し）を分離 |
| 145 | 変更マップ check-task-created.sh | hard stop 明記、「または exit code 2」削除 |
| 369 | Task 3-5 LEARNINGS 意図 | 用途別使い分けに更新 + raw_input gitignore 注記追加 |
| 446 | 自己レビュー（制御方式の正確性） | TaskCreated=continue:false (hard stop) / TaskCompleted=exit 2 + stderr (差し戻し) |
| 456 | リスク R6 | 両方式の互換テスト + raw_input gitignore 限定 |
| 483 | QA チェックリスト | TaskCreated は hard stop、TaskCompleted は差し戻し動作確認 + 早期 return テスト + ダンプ先確認 |

最終 grep で「実装方針を語る現役記述」からの旧表現残存は **0 件**（残るのは Rev.3 改訂履歴 / R1-3 / R2-3 の回顧文脈のみ）。

---

## 4. 最終確認チェックポイント

レビュアーに最終確認してほしい点：

- [ ] § 1 の 3 件すべて反映済みか
- [ ] § 2 の 2 件すべて反映済みか
- [ ] § 3 の 6 件すべて旧表現撲滅済みか
- [ ] 制御方式マトリクスが公式仕様と一致しているか（Round 4 で是認済み、念のため再確認）：
  - PreToolUse → `hookSpecificOutput.permissionDecision`
  - PostToolUse / Stop / SubagentStop / PreCompact → top-level `decision`/`reason`
  - PostToolUseFailure / UserPromptSubmit / SessionStart → `hookSpecificOutput.additionalContext`
  - **TaskCreated → `{"continue": false, "stopReason": "..."}` (hard stop)**
  - **TaskCompleted → exit code 2 + stderr に reason（差し戻し）**

---

## 5. レビュアーの返答テンプレート

```markdown
## 最終確認判定: [GO / NO-GO]

## § 1 Round 4 指摘 3 件の反映確認
- R4-1 (TaskCompleted 変更マップ): [反映済み / 不足]
- R4-2 (Verification): [反映済み / 不足]
- R4-3 (TDD 明示化): [反映済み / 不足]

## § 2 追加意見 2 件の反映確認
- A1 (raw_input gitignore): [反映済み / 不足]
- A2 (matcher 非対応 + 早期 return): [反映済み / 不足]

## § 3 隠れ残存 6 件の修正確認
[全件 OK / 一部不足] — 不足なら指摘

## Phase 0a (v0.12.2) 即時実装着手 GO 判定
[GO / 条件付き GO / NO-GO]

## その他
<自由記述>
```

---

## 6. 参考資料

- 詳細実装計画: `docs/plans/v0130-modernization-plan.md`（Revision 5）
- Round 1〜4 ブリーフ: 本ファイルの過去版（git log）
- 公式 docs（2026-05-03 確認）:
  - [Skills](https://code.claude.com/docs/en/skills)
  - [Hooks](https://code.claude.com/docs/en/hooks)
  - [Subagents](https://code.claude.com/docs/en/sub-agents)
  - [CLI Reference](https://code.claude.com/docs/en/cli-reference)
- 既存 LEARNINGS / STATUS: `docs/LEARNINGS.md` / `docs/STATUS.md`（v0.12.1, iteration 6, phase=review）

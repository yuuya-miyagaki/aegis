# Design: routing.md 原則化（Phase R 第1手）

> 作成日: 2026-06-06 / 対象モデル: Opus 4.8 / 起点: future-proof 再アーキ §3 DELEGATE「routing 細則 → 原則だけに縮約」

## 1. 背景と狙い

future-proof 再アーキの中核原則は設計思想を3層に分解する（`2026-06-05-v1-future-proof-rearchitecture-design.md` §2）:

- **保証（What/不変）** = hook で決定論的に強制
- **手順（How/揮発）** = 賢いモデルに委ねる
- **揮発値（Platform 固有）** = 1箇所に隔離

model/effort ポリシー（`815b283`）で同じ三層思想を model 割当に適用済み。本作業はその思想を **routing** に適用する。常時ロードの `.claude/rules/routing.md`（root + example、現状バイト一致・30行）から**手順的記述を外し、原則だけに縮約**する。これは再アーキ migration table の **Phase R（再配分・挙動変化あり）の最初の1手**。

## 2. 現状 routing.md の triage

| ブロック | 性質 | 処置 |
|---|---|---|
| ① Agent roles（10役割＋各「Subagent when…」手順文） | 一部 reference / 一部 手順 | agent 名の列挙（reference）は維持、各役割の「Subagent when…」手順文は削除 |
| ② Specialist reviewers（`5+ files` 閾値） | 手順/揮発 | **削除**。下記参照 |
| ③ Browser automation（browser-assist 案内） | reference | 1行に維持 |
| ④ Default rule（clearer/safer/smaller） | **保証＝原則** | 維持（先頭へ） |

### ① を消せない制約

`scripts/check_reference_drift.py::check_agents` が **routing.md ↔ `.claude/agents/*.md` の双方向 drift を FAIL 強制**する（routing.md にバッククォートで全 agent 名が参照されていること／参照名に対応ファイルがあること）。よって agent 名の列挙は **drift の真実源**として維持必須。「原則1行だけ」への単純縮約は12 agent 分の drift FAIL を招く。→ **リーン manifest 化**（名前列挙だけ残し説明文を削る）で両立させる。

加えて routing.md は `check_framework_contract.py` の `REQUIRED_RULES_FILES`（root + example）で**存在必須**。ファイル削除は不可。一方 routing.md の**見出し名・本文は contract も test も検証しない**（contract が見出しを検証するのは CLAUDE.md の `REQUIRED_CLAUDE_HEADINGS` のみ）。よってセクション構成の変更は安全。

### ② を消す根拠（思想だけでなく実在の不整合解消）

specialist 起動トリガは実は**3箇所**に定義されている:

- `routing.md`（常時ロード）= `5+ files`
- `subagent-dev/SKILL.md` Step3.5（phase ロードの表）= `3+ files`
- 各 specialist agent の frontmatter `description: "Trigger: review diff spans 3+ files…"` = `3+ files`（CC が subagent 自動 dispatch 時に参照する signal）

routing.md の `5+` は3者中**唯一の外れ値**。削除は単なる思想転換でなく、トリガを `3+` 合意側に収束させる**実在の不整合解消**でもある。運用上の到達性も保たれる: specialist は manifest に名前が残り（discovery）、frontmatter description と SKILL.md で起動条件が読める（trigger）。

## 3. 決定事項

1. **リーン manifest 化** — agent 名のバッククォート列挙のみ残し、各役割の手順文を削除。
2. **`5+ files` 閾値は routing.md から除去、SKILL.md Step3.5（`3+`）は据え置き** — 運用トリガは phase ロードのスキル＋agent frontmatter に一本化。
3. **原則（clearer/safer/smaller）は routing.md と CLAUDE.md の両方に1行ずつ保持、CLAUDE.md は不変** — 重複は1文のみ、blast radius 最小、`Details in .claude/rules/routing.md` の相互参照も生きる。
4. **バージョン: `0.12.2` → `0.12.3`（patch）** — 挙動変化はあるが range は極小（常時ロードから固定閾値1個を外すのみ、到達性不変）。minor（`0.13.0`）は Phase R 群を束ねて切る方が記録が綺麗。
5. **specialist ポインタ行・原則の言い換え節はトリム**（YAGNI）。副次効果として routing.md から `subagent-dev` 参照が消え、drift 非保護のスキル参照腐敗リスクも解消。

## 4. 新 routing.md（最終形・root と example 同一）

```text
# Routing

## Principle

Subagents only when they make work clearer, safer, or smaller.
When in doubt, keep work in the session context.

## Agents

Subagents: `planner`, `implementer`, `reviewer`, `qa`, `security`, `ui`,
`qa-browser`, `integration-specialist`, `translation-specialist`,
`reviewer-testing`, `reviewer-performance`, `reviewer-maintainability`.
Each agent's own file defines its domain.

`brainstorm` runs in session context (live user dialogue), not as a subagent.
`browser-assist` skill is available to any agent needing browser automation.
```

- 30行 → 14行。原則を先頭固定（保証）、次に 12 agent manifest（drift 真実源）、最後に main-context / skill 注記。
- バッククォート名 = 12 agent（全ファイル参照）＋ `brainstorm`（main_context・drift 除外）＋ `browser-assist`（skill・drift 除外）。agent 誤認なし。

## 5. 変更ファイル

| ファイル | 変更 |
|---|---|
| `.claude/rules/routing.md` | 上記最終形に書き換え |
| `examples/minimal-project/.claude/rules/routing.md` | 同一内容に書き換え（root と byte 一致を維持） |
| `scripts/check_framework_contract.py:17` | `FRAMEWORK_VERSION = "0.12.3"` |
| `templates/STATUS.template.md` | `framework_version:` を `0.12.3` に（contract が version sync を FAIL 強制） |
| `docs/plans/2026-06-06-v1-routing-principle-design.md` | 本書（新規） |

## 6. 挙動変化

- **唯一の挙動変化**: specialist reviewer の起動が常時ロードの固定閾値（`5+ files`）でなく、phase ロードの SKILL.md 表（`3+ files`）＋ agent frontmatter trigger に従う。実体は SKILL.md/frontmatter が `3+` で生きているため、固定閾値を1つ外す以上の意味的変化はない。
- agent の到達性・discovery は不変。原則（保証）も不変。

## 7. Verification（完了条件・全て緑が必須）

```bash
cd aegis
python3 -m unittest discover -s tests -q      # 既存テスト緑維持
python3 scripts/check_reference_drift.py       # routing.md↔agents 双方向 / version #7
python3 scripts/check_framework_contract.py    # 存在・CLAUDE headings・version sync
```

- drift `check_agents`: 12 agent 名が routing.md に残ることを確認（root のみ検証。example の agents は root と12個完全一致のため同一書き換えで安全）。
- contract: routing.md 存在（root+example）、CLAUDE.md `## Routing` 見出し存続、`FRAMEWORK_VERSION` ↔ `STATUS.template.md` version 一致。
- drift #7: `framework_version` in templates ↔ `FRAMEWORK_VERSION` 一致。

## 8. 完了後 bookkeeping（マージ後に実施）

- memory `aegis-rearchitecture-direction.md`: 「routing 原則化＝後続フェーズ未着手」を「完了（2026-06-06・version 0.12.3）」に更新。
- 再アーキ設計 §3 DELEGATE 行「routing 細則 → 原則だけに縮約」と §11 チェックリスト「routing 原則化」を消化済みに反映。
- 未 push の `6df1320`（haiku 仕上げ）と本作業を**まとめて push**。

## 9. リスク

| # | リスク | 対応 |
|---|---|---|
| R1 | 実装で agent 名を落とし drift FAIL | Verification の drift チェックを非スキップゲート化 |
| R2 | example が root と乖離 | 同一内容で書き換え、両方を変更ファイルに明記 |
| R3 | version sync 漏れ（片方だけ bump） | contract version sync が FAIL 強制で捕捉 |
| R4 | specialist 過少起動 | frontmatter trigger + SKILL.md 表（`3+`）が生きており到達性不変 |

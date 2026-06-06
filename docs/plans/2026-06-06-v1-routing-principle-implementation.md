# routing.md 原則化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 常時ロードの `.claude/rules/routing.md`（root + example）を三層 triage に従い「原則＋リーン agent manifest」へ縮約し、framework を `0.12.3` に bump する。

**Architecture:** routing.md から手順的記述（specialist `5+ files` 閾値・各役割の「Subagent when…」文）を除去し、原則（保証）を先頭に固定、12 agent 名の列挙（drift 真実源）と main-context/skill 注記のみ残す。挙動変化は specialist 起動が固定閾値でなく phase ロードの SKILL.md（`3+`）＋agent frontmatter trigger に従う1点のみ。新しい単体テストは無く、既存183テスト＋drift＋contract の3ゲート緑が安全網。

**Tech Stack:** Markdown ルールファイル、Python 検証スクリプト（`unittest` / `check_reference_drift.py` / `check_framework_contract.py`）。

**設計書:** `docs/plans/2026-06-06-v1-routing-principle-design.md`

---

## ベースライン（着手前に確認済み・2026-06-06）

- `python3 -m unittest discover -s tests -q` → `Ran 183 tests ... OK`
- `python3 scripts/check_reference_drift.py` → exit 0
- `python3 scripts/check_framework_contract.py` → exit 0
- `FRAMEWORK_VERSION = "0.12.2"`（`scripts/check_framework_contract.py:17`）/ `framework_version: "0.12.2"`（`templates/STATUS.template.md:3`）

全コマンドは `aegis/` ディレクトリ（`git rev-parse --show-toplevel` が `.../aegis`）で実行する。

---

## Task 1: routing.md 縮約 ＋ version bump 0.12.3

**Files:**
- Modify: `.claude/rules/routing.md`（全置換）
- Modify: `examples/minimal-project/.claude/rules/routing.md`（root と同一内容に全置換）
- Modify: `scripts/check_framework_contract.py:17`
- Modify: `templates/STATUS.template.md:3`

ルール変更とバージョンは1論理単位（version bump はこの routing 変更のために存在する）なので同一コミットにする。

- [ ] **Step 1: root の routing.md を新形へ全置換**

`.claude/rules/routing.md` の全内容を以下に置き換える（14行）:

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

注意: バッククォート名は 12 agent（全 `.claude/agents/*.md` に対応）＋ `brainstorm`（main_context・drift 除外）＋ `browser-assist`（skill・drift 除外）。**12 agent 名を1つも落とさないこと**（落とすと drift FAIL）。

- [ ] **Step 2: example の routing.md を同一内容へ全置換**

`examples/minimal-project/.claude/rules/routing.md` を Step 1 と**バイト単位で同一**の内容に置き換える。

- [ ] **Step 3: root と example が同一であることを確認**

Run: `diff .claude/rules/routing.md examples/minimal-project/.claude/rules/routing.md && echo IDENTICAL`
Expected: `IDENTICAL`（差分なし）

- [ ] **Step 4: FRAMEWORK_VERSION を 0.12.3 へ**

`scripts/check_framework_contract.py:17` を編集:
- old: `FRAMEWORK_VERSION = "0.12.2"`
- new: `FRAMEWORK_VERSION = "0.12.3"`

- [ ] **Step 5: STATUS.template.md の framework_version を 0.12.3 へ**

`templates/STATUS.template.md:3` を編集（contract が version sync を FAIL 強制するため Step 4 と必ず対で行う）:
- old: `framework_version: "0.12.2"`
- new: `framework_version: "0.12.3"`

- [ ] **Step 6: drift チェック（routing↔agents 双方向 / version #7）**

Run: `python3 scripts/check_reference_drift.py; echo "exit=$?"`
Expected: `exit=0`。特に「agent file X exists but not referenced in routing.md」が出ないこと（出たら Step 1 で agent 名を落としている）。`framework_version` ↔ `FRAMEWORK_VERSION` 不一致（#7）も無いこと。

- [ ] **Step 7: contract チェック（存在 / CLAUDE headings / version sync）**

Run: `python3 scripts/check_framework_contract.py; echo "exit=$?"`
Expected: `exit=0`。routing.md（root+example）存在・CLAUDE.md `## Routing` 見出し存続・`FRAMEWORK_VERSION` ↔ `STATUS.template.md` 一致が全て通ること。

- [ ] **Step 8: 既存テスト緑維持**

Run: `python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `Ran 183 tests ... OK`（数が183から増減しないこと。routing 内容を検証する test は無いので 183 のまま緑）。

- [ ] **Step 9: コミット**

```bash
git add .claude/rules/routing.md examples/minimal-project/.claude/rules/routing.md scripts/check_framework_contract.py templates/STATUS.template.md
git commit -m "$(cat <<'EOF'
refactor(rules): principle-ize routing.md, bump 0.12.3

Drop the always-on specialist threshold (5+ files) and per-role
"subagent when" procedure; keep the principle and the 12-agent name
list (drift source of truth). Specialist triggers now live solely in
agent frontmatter and the subagent-dev skill (3+ files). Behavior change
is limited to delegating specialist spin-up; agents stay discoverable.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 再アーキ設計書の bookkeeping

**Files:**
- Modify: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`（§3 DELEGATE 行 / §11 チェックリスト）

設計書 §8 の「完了後 bookkeeping」。再アーキの追従記録を最新化する。

- [ ] **Step 1: §3 DELEGATE テーブルの routing 行を消化済みに**

`docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` の §3 🤖 DELEGATE テーブル内、`routing 細則` の行（現状「`routing.md` 詳細ルール → **原則だけに縮約**（分離が安全/明確/小さくする時のみ subagent）」）の「再設計後」セルに完了注記を追記:
- 追記内容: `→ **完了**（2026-06-06・v0.12.3・`2026-06-06-v1-routing-principle-design.md`）`

- [ ] **Step 2: §11 完了条件チェックリストの routing 項目をチェック**

§11 の `- [ ] CLAUDE.md から固定 context 数値撤廃、routing 原則化` の行を分離・更新:
- old: `- [ ] CLAUDE.md から固定 context 数値撤廃、routing 原則化`
- new: `- [ ] CLAUDE.md から固定 context 数値撤廃 / [x] routing 原則化（2026-06-06・v0.12.3）`

- [ ] **Step 3: コミット**

```bash
git add docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md
git commit -m "$(cat <<'EOF'
docs(plans): mark routing principle-ization done in rearchitecture design

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: memory 更新 ＋ push（要ユーザー確認）

**Files:**
- Modify: `~/.claude/projects/-Users-miyagakiyuuya-Desktop-personal-superpowers-gstack-antigravitykit-urtorapowers/memory/aegis-rearchitecture-direction.md`（git 管理外・memory システム）

- [ ] **Step 1: memory の進捗を更新**

`aegis-rearchitecture-direction.md` の「後続フェーズ未着手」リストから `routing 原則化` を外し、完了記録を追記（例: `routing 原則化 完了（2026-06-06・main・v0.12.3。固定 specialist 閾値を撤廃し原則＋agent manifest へ縮約）`）。これは memory システムへの書き込みで、git コミット対象ではない。

- [ ] **Step 2: push 前の最終状態確認**

Run: `git log --oneline origin/main..HEAD`
Expected: 4コミット — `6df1320`（haiku 仕上げ・既存未push）、`4388c67`（設計書）、Task 1 のコミット、Task 2 のコミット。

- [ ] **Step 3: push（ユーザー確認の上で実行）**

push は共有状態を変える操作。実行直前にユーザーへ「上記4コミットを `origin/main` に push してよいか」を確認してから:

```bash
git push origin main
```

Expected: 4コミットが origin/main へ反映。`docs/architecture-overview.pdf`（untracked・無関係）は push に含めない。

---

## Self-Review

**Spec coverage（設計書の各決定 → タスク対応）:**
- 決定1 リーン manifest 化 → Task 1 Step 1-3
- 決定2 `5+` 除去・SKILL.md 据置 → Task 1 Step 1（routing から閾値削除。SKILL.md は無変更＝据え置きで充足）
- 決定3 原則は両方・CLAUDE.md 不変 → Task 1（routing に原則維持、CLAUDE.md は変更ファイルに含めない）
- 決定4 version 0.12.3 → Task 1 Step 4-5
- 決定5 ポインタ/言い換えトリム → Task 1 Step 1 の最終形に反映済み
- Verification（3ゲート緑）→ Task 1 Step 6-8
- 完了後 bookkeeping → Task 2 ＋ Task 3 Step 1
- 6df1320 同梱 push → Task 3 Step 2-3

**Placeholder scan:** 各 Edit に old/new の厳密文字列、routing.md は全文、コマンドは期待出力付き。プレースホルダなし。

**Type/identifier consistency:** バージョン文字列は全タスクで `0.12.3` 一貫。12 agent 名は `.claude/agents/*.md` の実在 stem と一致（planner, implementer, reviewer, qa, security, ui, qa-browser, integration-specialist, translation-specialist, reviewer-testing, reviewer-performance, reviewer-maintainability）。

ギャップ: CLAUDE.md は意図的に不変（決定3）。SKILL.md Step3.5 と agent frontmatter は意図的に据え置き（決定2）。いずれも設計どおりで欠落ではない。

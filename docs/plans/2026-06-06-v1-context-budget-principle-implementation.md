# context budget 原則化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLAUDE.md の `## Context Budget Policy` から hard 数値「max three docs at once」を撤廃し、aegis-brainstorm の重複数値も整合、L0-L3 語彙と質的原則は維持して読み量をモデルに委ねる。framework を `0.12.4` に bump する。

**Architecture:** routing 原則化（v0.12.3）に続く Phase R の text 変更。固定上限「3」だけを撤廃し、Session Start §2-3 が既に担う「必要なものだけ pull」の意図に委ねる（DRY のため置換句を足さない）。新規機構なし。新しい単体テストは無く、既存183テスト＋drift＋contract の3ゲート緑が安全網。

**Tech Stack:** Markdown 規約ファイル（CLAUDE.md・SKILL.md）、Python 検証スクリプト（`unittest` / `check_reference_drift.py` / `check_framework_contract.py`）。

**設計書:** `docs/plans/2026-06-06-v1-context-budget-principle-design.md`

---

## ベースライン（着手前に確認）

- `python3 -m unittest discover -s tests -q` → `Ran 183 tests ... OK`
- `python3 scripts/check_reference_drift.py` → exit 0
- `python3 scripts/check_framework_contract.py` → exit 0
- 現行 version: `FRAMEWORK_VERSION = "0.12.3"`（`scripts/check_framework_contract.py:17`）/ `framework_version: "0.12.3"`（`templates/STATUS.template.md:3`）

全コマンドは `aegis/`（`git rev-parse --show-toplevel` が `.../aegis`）で実行する。

> **⚠ footgun（grill 致命指摘）**: **example CLAUDE.md は root と全体非同一**（`## Project Overrides` を持つ）。各ファイルは **該当1行のみの Edit** で変更し、**root の全文を example へコピーしない**。対象4行は各ファイル内で一意（grep count=1）。

---

## Task 1: context budget 数値撤廃 ＋ version bump 0.12.4

**Files:**
- Modify: `CLAUDE.md`（1行）
- Modify: `examples/minimal-project/CLAUDE.md`（1行・全文コピー禁止）
- Modify: `.claude/skills/aegis-brainstorm/SKILL.md`（行77）
- Modify: `examples/minimal-project/.claude/skills/aegis-brainstorm/SKILL.md`（行77）
- Modify: `scripts/check_framework_contract.py:17`
- Modify: `templates/STATUS.template.md:3`

ルール変更とバージョンは1論理単位なので同一コミットにする。

- [ ] **Step 1: root CLAUDE.md の数値を撤廃**

`CLAUDE.md` を行単位 Edit:
- old: `- Prefer repo files over chat history. Pull-based; max three docs at once.`
- new: `- Prefer repo files over chat history. Pull-based.`

- [ ] **Step 2: example CLAUDE.md の数値を撤廃（同1行のみ）**

`examples/minimal-project/CLAUDE.md` を**同じ1行だけ** Edit（`## Project Overrides` 等には触れない）:
- old: `- Prefer repo files over chat history. Pull-based; max three docs at once.`
- new: `- Prefer repo files over chat history. Pull-based.`

- [ ] **Step 3: root aegis-brainstorm SKILL.md の数値を撤廃**

`.claude/skills/aegis-brainstorm/SKILL.md` を Edit:
- old: `- L0 の \`docs/STATUS.md\` に加え、同時に開く refs は最大 3 つまで`
- new: `- L0 の \`docs/STATUS.md\` を起点に refs を pull する`

- [ ] **Step 4: example aegis-brainstorm SKILL.md の数値を撤廃**

`examples/minimal-project/.claude/skills/aegis-brainstorm/SKILL.md` を Edit:
- old: `- L0 の \`docs/STATUS.md\` に加え、同時に開く refs は最大 3 つまで`
- new: `- L0 の \`docs/STATUS.md\` を起点に refs を pull する`

- [ ] **Step 5: FRAMEWORK_VERSION を 0.12.4 へ**

`scripts/check_framework_contract.py:17`:
- old: `FRAMEWORK_VERSION = "0.12.3"`
- new: `FRAMEWORK_VERSION = "0.12.4"`

- [ ] **Step 6: STATUS.template.md の framework_version を 0.12.4 へ**

`templates/STATUS.template.md:3`（contract が version sync を FAIL 強制するため Step 5 と必ず対で）:
- old: `framework_version: "0.12.3"`
- new: `framework_version: "0.12.4"`

- [ ] **Step 7: 数値が全 operative 箇所から消えたことを確認**

Run: `grep -rn "max three docs\|最大 3 つまで" CLAUDE.md examples/minimal-project/CLAUDE.md .claude/skills/aegis-brainstorm/SKILL.md examples/minimal-project/.claude/skills/aegis-brainstorm/SKILL.md; echo "exit=$?"`
Expected: マッチ0件・`exit=1`（grep がヒットなしで 1 を返す）。

- [ ] **Step 8: 見出し存続を確認**

Run: `grep -c "## Context Budget Policy" CLAUDE.md examples/minimal-project/CLAUDE.md`
Expected: 各ファイル `1`（`REQUIRED_CLAUDE_HEADINGS` 維持）。

- [ ] **Step 9: contract（見出し / word budget≤650 / version sync）**

Run: `python3 scripts/check_framework_contract.py; echo "exit=$?"`
Expected: `exit=0`。`## Context Budget Policy` 見出し存続・CLAUDE.md word count ≤ 650・`FRAMEWORK_VERSION` ↔ `STATUS.template.md` 一致。

- [ ] **Step 10: drift（version #7）**

Run: `python3 scripts/check_reference_drift.py; echo "exit=$?"`
Expected: `exit=0`。`framework_version` ↔ `FRAMEWORK_VERSION`（#7）一致。

- [ ] **Step 11: 既存テスト緑維持**

Run: `python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `Ran 183 tests ... OK`（test_lint_names は CLAUDE.md の `## Skills` 節のみ解析・budget は非検証なので 183 のまま緑）。

- [ ] **Step 12: コミット**

```bash
git add CLAUDE.md examples/minimal-project/CLAUDE.md .claude/skills/aegis-brainstorm/SKILL.md examples/minimal-project/.claude/skills/aegis-brainstorm/SKILL.md scripts/check_framework_contract.py templates/STATUS.template.md
git commit -m "$(cat <<'EOF'
refactor(rules): drop hard context-budget number, bump 0.12.4

Remove the "max three docs at once" hard limit from CLAUDE.md and the
duplicated "最大 3 つまで" from aegis-brainstorm. Keep the L0-L3
vocabulary and qualitative principles; Session Start already carries the
"pull only what's relevant" intent (DRY, no replacement clause). Read
volume is delegated to the model. Behavior change is limited to lifting
the fixed doc cap.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 再アーキ設計書の bookkeeping

**Files:**
- Modify: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`（§3 DELEGATE context 行 / §11 チェックリスト）

- [ ] **Step 1: §3 DELEGATE の context 行を消化済みに**

`docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` の §3 🤖 DELEGATE テーブル、`context 予算 L0〜L3・同時3doc` の行の「再設計後」セル末尾に追記:
- old 末尾: `何をどれだけ読むかは 1M モデルに委ねる |`
- new 末尾: `何をどれだけ読むかは 1M モデルに委ねる → **完了**（2026-06-06・v0.12.4・「max 3 docs」hard 数値のみ撤廃／L0-L3 語彙維持・`2026-06-06-v1-context-budget-principle-design.md`） |`

> 着手前に `grep -n "context 予算 L0" docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` で正確な行文字列を確認してから Edit すること。

- [ ] **Step 2: §11 チェックリストの context 項目を [x] に**

§11 の行（routing 作業で分割済み）:
- old: `- [ ] CLAUDE.md から固定 context 数値撤廃 / [x] routing 原則化（2026-06-06・v0.12.3）`
- new: `- [x] CLAUDE.md から固定 context 数値撤廃（2026-06-06・v0.12.4） / [x] routing 原則化（2026-06-06・v0.12.3）`

- [ ] **Step 3: コミット**

```bash
git add docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md
git commit -m "$(cat <<'EOF'
docs(plans): mark context-budget principle-ization done in rearchitecture design

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 実装計画 commit ＋ memory 更新 ＋ push（要ユーザー確認）

**Files:**
- Add: `docs/plans/2026-06-06-v1-context-budget-principle-implementation.md`（本書・retention 規約に従い tracked 化）
- Modify: `~/.claude/.../memory/aegis-rearchitecture-direction.md`（git 管理外）

- [ ] **Step 1: 本実装計画をコミット**

```bash
git add docs/plans/2026-06-06-v1-context-budget-principle-implementation.md
git commit -m "$(cat <<'EOF'
docs(plans): track context-budget impl plan as dated snapshot

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: memory の進捗を更新**

`aegis-rearchitecture-direction.md` に context budget 原則化の完了を追記（Phase R 第2手・main・v0.12.4。CLAUDE.md と aegis-brainstorm から「3 docs」hard 数値を撤廃し L0-L3 語彙は維持。observability は YAGNI で見送り）。git コミット対象外。

- [ ] **Step 3: push 前の最終状態確認**

Run: `git log --oneline origin/main..HEAD`
Expected: 4コミット — `21a84c7`（設計書）、Task 1・Task 2・Task 3 Step 1 のコミット。

- [ ] **Step 4: push（ユーザー確認の上で実行）**

実行直前にユーザーへ push 可否を確認してから:

```bash
git push origin main
```

Expected: origin/main へ反映。`docs/architecture-overview.pdf`（untracked・無関係）は含めない。

---

## Self-Review

**Spec coverage（設計書の各決定 → タスク対応）:**
- 決定1 CLAUDE.md 数値撤廃 → Task 1 Step 1-2
- 決定2 aegis-brainstorm 整合 → Task 1 Step 3-4
- 決定3 L0-L3 語彙維持 → 該当行に触れない（L-taxonomy 定義行・スキルの L2 タグは無変更）で充足
- 決定4 version 0.12.4 → Task 1 Step 5-6
- footgun（example 行単位 Edit）→ ベースライン警告＋Task 1 Step 2 に明記
- Verification（3ゲート＋数値消滅＋見出し存続）→ Task 1 Step 7-11
- 完了後 bookkeeping → Task 2 ＋ Task 3
- design/plan retention 規約 → Task 3 Step 1（impl plan を tracked 化）

**Placeholder scan:** 各 Edit に厳密 old/new、コマンドは期待 exit/出力付き。§3 行のみ「着手前に grep 確認」を明記（長い行の取り違え防止）。プレースホルダなし。

**Type/identifier consistency:** version 文字列は全タスク `0.12.4` 一貫、old は `0.12.3`。撤廃対象数値は「max three docs at once」「最大 3 つまで」で一貫。

ギャップ: agent 12本の Context Budget 節・L0-L3 定義行・スキルの L2 タグは意図的に不変（決定3）。欠落ではない。

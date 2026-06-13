# B3b UAT 実行フェーズ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ACCEPTANCE で定義した受入条件を client がビルド済み製品に対し実検証して合否を記録する場（UAT-RESULTS＋uat skill）を作り、既存 `dev_ready_for_client` ゲートに存在チェックで連動させる（監査能力⑩）。

**Architecture:** 新テンプレ `UAT-RESULTS.template.md`＋新 pull-based skill `uat`（ship 段階で ACCEPTANCE を1件ずつ実検証→記録→client サインオフ）。`check_status.py` の `check_gate_prerequisites()` dev_ready_for_client 分岐に「ACCEPTANCE 有り＋UAT-RESULTS 不在ならブロック」を追加（合否は client サインオフが正本、機械は存在のみ）。`ship-and-docs`（Step 2.7）・`docs-sync`・`HANDOVER-TO-CLIENT` も連動。新フェーズ/新ゲート/新 current_refs キーは作らない。

**Tech Stack:** Markdown テンプレ／Claude Code skills（`disable-model-invocation: true`）／Python（`check_status.py` gate チェック＋`unittest`）／`check_framework_contract.py`・`check_reference_drift.py`・`test_mirror_identity.py`・`eval_scaffold_smoke.py` による構造検証。

> **テスト方針:** B3a/B3c と違い B3b は**実コードを持つ**（gate チェック）。`tests/test_check_status.py` にユニットテスト3本を追加。テンプレ/skill は静的 md＝内容レビューで担保。spec `docs/plans/2026-06-07-v1-b3b-uat-execution-design.md`。

> **ミラー注意（grill-plan 反映）:** `scripts/check_status.py` は `examples/minimal-project/scripts/check_status.py` と **byte 同一ミラー**（確認済み）。改修は必ず example へ同期（さもなくば `test_mirror_identity`/`check_reference_drift` が落ちる）。**`tests/` は example 非ミラー**なのでテストは同期しない（スクリプト=ミラー／テスト=非ミラーの非対称）。`.claude/skills/` 配下もミラー。テンプレ（`templates/`）は example 非ミラー。

> **依存順:** `uat` skill（Task 2）→ それを参照する ship-and-docs（Task 4）。lint 双方向（CLAUDE.md↔skill dir）は Task 2 同一コミットに畳む。

---

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `templates/UAT-RESULTS.template.md` | UAT 結果テンプレ（AC ごと 期待/実際/合否/証拠＋サインオフ） | 新規 |
| `.claude/skills/uat/SKILL.md` | UAT 実行手順 | 新規（+example ミラー） |
| `scripts/check_status.py` | dev_ready_for_client に UAT-RESULTS 存在チェック | 改修（+example ミラー） |
| `tests/test_check_status.py` | ユニットテスト3本追加 | 改修（**非ミラー**） |
| `.claude/skills/ship-and-docs/SKILL.md` | Step 2.7 追加 | 改修（+mirror） |
| `.claude/skills/docs-sync/SKILL.md` | 整合チェック1項目 | 改修（+mirror） |
| `templates/HANDOVER-TO-CLIENT.template.md` | UAT 結果リンク行 | 改修 |
| `scripts/check_framework_contract.py` | テンプレ/スキル/example skill dir 登録 | 改修 |
| `templates/profiles/full.json` | `uat` を recommended に登録 | 改修 |
| `CLAUDE.md` / `examples/minimal-project/CLAUDE.md` / `examples/minimal-project/README.md` | Skills 一覧＋スキル数(17→18) | 改修 |

> example の `docs/handover/UAT-RESULTS.md` は**作らない**（B3a/B3c が MANUAL.md/RUNBOOK.md を example に置かないのと同じ。example は ACCEPTANCE 有り・UAT 前の状態を表す。dev_ready_for_client=pending なので contract は通る）。

---

## Task 1: UAT-RESULTS.template.md 作成＋テンプレ登録

**Files:**
- Create: `templates/UAT-RESULTS.template.md`
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_TEMPLATE_FILES`）

- [ ] **Step 1: テンプレを作成**

以下の内容で `templates/UAT-RESULTS.template.md` を作成する:

```markdown
---
product: "<記入>"
release: "<記入>"
date: "<記入>"
tested_by: "<記入: 検証した client 担当者>"
---
# <製品名> UAT（受入）結果
<!-- 正本: uat skill -->
<!-- exit-check: 全 Must-AC に合否・証拠あり・client サインオフ済み -->

> この文書は、ACCEPTANCE で定義した受入条件を、ビルド済み製品に対して client が実検証した結果です。
> 合否の最終判断は client のサインオフが正本です。

## 判定サマリー
- 総合: <合格 / 不合格>
- Must 受入条件: <全通過 / 未通過あり>

## 受入検証
<!-- ACCEPTANCE.md の各 AC を1行ずつ。証拠はテスト結果/スクショ/レビューへのリンク。 -->
| AC | 期待する結果 | 実際の結果 | 合否 | 証拠 | 優先度 |
|----|------------|-----------|------|------|--------|
| AC-001 | <記入> | <記入> | <✅/❌> | <記入> | <Must/Should> |

## 未合格と対応
<!-- ❌ の項目のみ。再修正に回すか、client が理由付きで受容(ack)するか。 -->
- <AC番号>: <対応方針: bugfix/hotfix へ戻す ／ client が ack（理由）>

## サインオフ
- 承認者（client）: <記入>
- 日付: <記入>
```

- [ ] **Step 2: REQUIRED_TEMPLATE_FILES に登録**

`scripts/check_framework_contract.py` の `REQUIRED_TEMPLATE_FILES` で、`ROOT / "templates/RUNBOOK.template.md",` の直後に追加:
```python
    ROOT / "templates/UAT-RESULTS.template.md",
```

- [ ] **Step 3: 構造と contract を確認**

Run: `python3 -c "import pathlib; t=pathlib.Path('templates/UAT-RESULTS.template.md').read_text(encoding='utf-8'); assert '## 受入検証' in t and '## サインオフ' in t and '判定サマリー' in t; print('template OK')"`
Expected: `template OK`

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 4: コミット**

```bash
git add templates/UAT-RESULTS.template.md scripts/check_framework_contract.py
git commit -m "feat(b3b): add UAT-RESULTS template + register"
```

---

## Task 2: uat skill 作成＋lint 必須登録＋example 同期（同一コミット）

**Files:**
- Create: `.claude/skills/uat/SKILL.md`
- Create (mirror): `examples/minimal-project/.claude/skills/uat/SKILL.md`
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_SKILL_FILES`・`REQUIRED_EXAMPLE_SKILL_DIRS`）
- Modify: `CLAUDE.md`・`examples/minimal-project/CLAUDE.md`（`## Skills`）
- Modify: `examples/minimal-project/README.md`（スキル数 17→18）

- [ ] **Step 1: skill を作成**

以下の内容で `.claude/skills/uat/SKILL.md` を作成する:

```markdown
---
name: uat
description: "UAT execution. Client verifies the built product against ACCEPTANCE criteria and records pass/fail with sign-off before handback."
disable-model-invocation: true
user-invocable: false
---
# UAT（受入）実行

> ACCEPTANCE で定義した受入条件を、ビルド済み製品に対して client が実検証し合否を記録する。
> docs フェーズで `ship-and-docs` の ship 段階から、`dev_ready_for_client` 申請の前に参照される。
> 合否の最終判断は client のサインオフが正本（機械は UAT-RESULTS の存在のみ見る）。

## qa-verification との違い
`qa-verification` は Dev 内部 QA（テスト/lint/build を dev が実行）。UAT は client 視点の受入
（製品が ACCEPTANCE を満たすかを client が判定）。qa の結果は証拠として参照してよいが、
client 視点の確認を省略しない。

## いつ使うか
- `ship-and-docs` の ship 段階で、`dev_ready_for_client` 申請の前。
- `docs/requirements/ACCEPTANCE.md` がある案件のとき。ACCEPTANCE が無い案件は UAT 不要（理由記録）。

## 手順

### Step 1: 受入条件を読む
`docs/requirements/ACCEPTANCE.md` の各 AC とトレーサビリティ（検証方法: 自動テスト/手動確認/レビュー）を読む。

### Step 2: 実検証
ビルド済み製品に対し各 AC を検証する。UI は `browser-assist`/`qa-browser` で実画面を確認、自動テストは qa 成果物の結果を参照。各 AC に 期待/実際/合否(✅/❌)/証拠 を記録する。

### Step 3: client サインオフ
結果を client（ユーザー）に提示し合否を確認する。Must の ❌ は bugfix/hotfix へ戻すか、client が理由付きで ack して受容する。

### Step 4: 保存とリンク
`templates/UAT-RESULTS.template.md` をもとに `docs/handover/UAT-RESULTS.md` を作成し、TO-CLIENT の納品サマリーからリンクする。

### Step 5: 整合確認
`docs-sync` skill を読み、UAT-RESULTS の存在と全 Must-AC の合否・サインオフを確認する。

## UAT が不要なとき
ACCEPTANCE が無い（受入条件未定義の内部タスク等）案件は生成せず、TO-CLIENT もしくは STATUS に理由を1行記録する。

## Red Flags（禁止事項）
- ❌ を残したまま理由なくサインオフする。
- 証拠リンク無しで✅にする。
- ACCEPTANCE の AC を UAT-RESULTS から欠落させる。
- qa-verification（内部QA）の結果をそのまま UAT 合否として流用し、client 視点の確認を省く。
- チャット履歴を成果物のソースにする。

## コンテキスト予算
- ACCEPTANCE＋qa 成果物＋UAT テンプレのみ。過去チャットは参照しない。
```

- [ ] **Step 2: example へミラー**

```bash
mkdir -p examples/minimal-project/.claude/skills/uat
cp .claude/skills/uat/SKILL.md examples/minimal-project/.claude/skills/uat/SKILL.md
```

- [ ] **Step 3: REQUIRED_SKILL_FILES に登録**

`scripts/check_framework_contract.py` の `REQUIRED_SKILL_FILES` で、`ROOT / ".claude/skills/maintenance/SKILL.md",` の直後に追加:
```python
    ROOT / ".claude/skills/uat/SKILL.md",
```

- [ ] **Step 4: REQUIRED_EXAMPLE_SKILL_DIRS に登録**

同ファイルの `REQUIRED_EXAMPLE_SKILL_DIRS` で、`"maintenance",` の直後に追加:
```python
    "uat",
```

- [ ] **Step 5: CLAUDE.md ## Skills に登録（本体＋example）**

`CLAUDE.md` と `examples/minimal-project/CLAUDE.md` の両方で、行
```markdown
- deploy, client-workflow, session-recovery, ship-and-docs, user-manual, maintenance
```
を次に変更:
```markdown
- deploy, client-workflow, session-recovery, ship-and-docs, user-manual, maintenance, uat
```

- [ ] **Step 6: example README のスキル数を更新**

`examples/minimal-project/README.md` の
```markdown
- `.claude/skills/` — pull-based skill documents (17 skills)
```
を `(18 skills)` に変更。

- [ ] **Step 7: byte 同一と contract/drift を確認**

```bash
diff -q .claude/skills/uat/SKILL.md examples/minimal-project/.claude/skills/uat/SKILL.md && echo "mirror OK"
python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_reference_drift.py
```
Expected: `mirror OK` ＋ 両方 `PASS`（drift は警告ゼロ）。

- [ ] **Step 8: コミット**

```bash
git add .claude/skills/uat/SKILL.md examples/minimal-project/.claude/skills/uat/SKILL.md scripts/check_framework_contract.py CLAUDE.md examples/minimal-project/CLAUDE.md examples/minimal-project/README.md
git commit -m "feat(b3b): add uat skill + register (contract/example/kernel)"
```

---

## Task 3: dev_ready_for_client に UAT-RESULTS 存在チェック＋テスト＋ミラー

**Files:**
- Modify: `scripts/check_status.py`（`check_gate_prerequisites()` の dev_ready_for_client 分岐）
- Modify (mirror): `examples/minimal-project/scripts/check_status.py`（byte 同一）
- Modify: `tests/test_check_status.py`（**非ミラー**・3テスト追加）

- [ ] **Step 1: failing テストを追加**

`tests/test_check_status.py` の `test_dev_ready_for_client_all_approved_allows` メソッドの直後に、次の3メソッドを同クラス内に追加する:

```python
    def test_dev_ready_for_client_blocks_without_uat_when_acceptance(self):
        """ACCEPTANCE present + UAT-RESULTS missing → block."""
        content = make_status_md(
            phase="ship", task_type="feature", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "approved", "qa": "approved", "security": "approved",
            },
        )
        with TempProject(content) as root:
            req = Path(root) / "docs" / "requirements"
            req.mkdir(parents=True, exist_ok=True)
            (req / "ACCEPTANCE.md").write_text("# 受入条件\n", encoding="utf-8")
            rc, out = run_check(root, "--pre-approve-gate", "dev_ready_for_client")
            self.assertNotEqual(rc, 0, f"Should block without UAT-RESULTS: {out}")
            self.assertIn("UAT-RESULTS", out, f"Error should mention UAT-RESULTS: {out}")

    def test_dev_ready_for_client_allows_with_uat_results(self):
        """ACCEPTANCE + UAT-RESULTS present → allow."""
        content = make_status_md(
            phase="ship", task_type="feature", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "approved", "qa": "approved", "security": "approved",
            },
        )
        with TempProject(content) as root:
            req = Path(root) / "docs" / "requirements"
            req.mkdir(parents=True, exist_ok=True)
            (req / "ACCEPTANCE.md").write_text("# 受入条件\n", encoding="utf-8")
            handover = Path(root) / "docs" / "handover"
            handover.mkdir(parents=True, exist_ok=True)
            (handover / "UAT-RESULTS.md").write_text("# UAT\n", encoding="utf-8")
            rc, out = run_check(root, "--pre-approve-gate", "dev_ready_for_client")
            self.assertEqual(rc, 0, f"Should allow with UAT-RESULTS: {out}")

    def test_dev_ready_for_client_no_acceptance_skips_uat(self):
        """No ACCEPTANCE → UAT not required → allow (legacy behavior)."""
        content = make_status_md(
            phase="ship", task_type="feature", task_size="L",
            approvals={
                "brainstorm": "approved", "plan": "approved",
                "review": "approved", "qa": "approved", "security": "approved",
            },
        )
        with TempProject(content) as root:
            rc, out = run_check(root, "--pre-approve-gate", "dev_ready_for_client")
            self.assertEqual(rc, 0, f"Should allow without ACCEPTANCE: {out}")
```

> `Path` は同ファイルで import 済み（`from pathlib import Path`）。`run_check` は subprocess で `--root` を渡すため、入室後に temp root へ書いたファイルが反映される。

- [ ] **Step 2: テストが赤いことを確認**

Run: `python3 -m unittest tests.test_check_status -v 2>&1 | grep -E 'uat|UAT|blocks_without_uat|FAIL|ERROR' | head`
Expected: `test_dev_ready_for_client_blocks_without_uat...` が FAIL（現状は ACCEPTANCE 有り+UAT 無しでも allow になるため）。allow/skip の2本は PASS でよい。

- [ ] **Step 3: check_status.py に存在チェックを実装**

`scripts/check_status.py` の `check_gate_prerequisites()` 内、dev_ready_for_client 分岐の末尾。次の既存ブロック:
```python
        for req in required:
            val = approvals.get(req, "pending")
            if val not in ("approved", "n/a"):
                print(
                    f"ERROR: Cannot approve 'dev_ready_for_client' — "
                    f"gate '{req}' is '{val}' (must be approved or n/a)."
                )
                return 1
        return 0
```
を次に置き換える:
```python
        for req in required:
            val = approvals.get(req, "pending")
            if val not in ("approved", "n/a"):
                print(
                    f"ERROR: Cannot approve 'dev_ready_for_client' — "
                    f"gate '{req}' is '{val}' (must be approved or n/a)."
                )
                return 1
        # UAT: if acceptance criteria were defined, require recorded UAT results
        # before handback. Pass/fail is the client's sign-off; the machine only
        # checks the artifact exists (content is not parsed).
        acceptance = root / "docs" / "requirements" / "ACCEPTANCE.md"
        uat_results = root / "docs" / "handover" / "UAT-RESULTS.md"
        if acceptance.exists() and not uat_results.exists():
            print(
                "ERROR: docs/requirements/ACCEPTANCE.md があるのに "
                "docs/handover/UAT-RESULTS.md が見つかりません。"
            )
            print("       dev_ready_for_client の前に UAT を実行してください。")
            print("       → uat skill を使用")
            return 1
        return 0
```

- [ ] **Step 4: テストが緑になることを確認**

Run: `python3 -m unittest tests.test_check_status -v 2>&1 | tail -3`
Expected: `OK`（追加3本含め全 PASS）。

- [ ] **Step 5: example へミラー＋byte 同一確認**

```bash
cp scripts/check_status.py examples/minimal-project/scripts/check_status.py
diff -q scripts/check_status.py examples/minimal-project/scripts/check_status.py && echo "mirror OK"
python3 -m unittest tests.test_mirror_identity 2>&1 | tail -2
```
Expected: `mirror OK` ＋ `OK`

- [ ] **Step 6: コミット**

```bash
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "feat(b3b): dev_ready_for_client requires UAT-RESULTS when ACCEPTANCE exists"
```

---

## Task 4: ship-and-docs に Step 2.7 を追加

**Files:**
- Modify: `.claude/skills/ship-and-docs/SKILL.md`（`### Step 3: ユーザー確認` の直前。Step 2.6 の後）
- Modify (mirror): `examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md`

- [ ] **Step 1: Step 2.7 を挿入**

`.claude/skills/ship-and-docs/SKILL.md` の `### Step 3: ユーザー確認` の直前に挿入する:

```markdown
### Step 2.7: UAT 実行（該当時）

`uat` skill を読み、`docs/requirements/ACCEPTANCE.md` がある場合は各 AC をビルド済み製品に対し
実検証し、`docs/handover/UAT-RESULTS.md` を作成して client サインオフを得る。TO-CLIENT の
「納品サマリー」の UAT 結果欄にリンクする。ACCEPTANCE が無い場合は生成せず理由を同欄に記録する。
（ACCEPTANCE があるのに UAT-RESULTS が無いと Step 6 の dev_ready_for_client 申請が機械ブロックされる。）

```

- [ ] **Step 2: example へミラー＋確認**

```bash
cp .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
diff -q .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md && echo "mirror OK"
python3 scripts/check_reference_drift.py 2>&1 | tail -1
```
Expected: `mirror OK` ＋ `PASS`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
git commit -m "feat(b3b): ship-and-docs runs UAT before dev_ready_for_client (Step 2.7)"
```

---

## Task 5: docs-sync に UAT 整合チェックを追加

**Files:**
- Modify: `.claude/skills/docs-sync/SKILL.md`（RUNBOOK 整合行の直後）
- Modify (mirror): `examples/minimal-project/.claude/skills/docs-sync/SKILL.md`

- [ ] **Step 1: チェック項目を追加**

`.claude/skills/docs-sync/SKILL.md` の RUNBOOK 整合行
```markdown
- [ ] 保守が該当する案件なら `docs/handover/RUNBOOK.md` が存在し、front-matter（product/environment/owners）と必須節（監視/インシデント対応（トリアージ）/エスカレーション/インシデント履歴/用語）が埋まっている。該当なしなら理由が記録されている
```
の直後に追加:
```markdown
- [ ] UAT が該当する案件（ACCEPTANCE あり）なら `docs/handover/UAT-RESULTS.md` が存在し、全 Must-AC に合否・証拠・client サインオフがある。該当なしなら理由が記録されている
```

- [ ] **Step 2: example へミラー＋確認**

```bash
cp .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
diff -q .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md && echo "mirror OK"
python3 scripts/check_reference_drift.py 2>&1 | tail -1
```
Expected: `mirror OK` ＋ `PASS`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
git commit -m "feat(b3b): docs-sync verifies UAT-RESULTS sign-off"
```

---

## Task 6: HANDOVER-TO-CLIENT テンプレに UAT 結果行を追加

**Files:**
- Modify: `templates/HANDOVER-TO-CLIENT.template.md`（運用 RUNBOOK 行の直後）

- [ ] **Step 1: UAT 結果リンク行を追加**

`templates/HANDOVER-TO-CLIENT.template.md` の行
```markdown
- 運用 RUNBOOK: <記入: docs/handover/RUNBOOK.md（運用者がいる場合）／不要なら理由>
```
の直後に追加:
```markdown
- UAT 結果: <記入: docs/handover/UAT-RESULTS.md（ACCEPTANCE がある場合）／不要なら理由>
```

- [ ] **Step 2: contract を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 3: コミット**

```bash
git add templates/HANDOVER-TO-CLIENT.template.md
git commit -m "feat(b3b): TO-CLIENT summary links the UAT results"
```

---

## Task 7: full.json に uat を登録

**Files:**
- Modify: `templates/profiles/full.json`（`recommended`）

- [ ] **Step 1: full.json に登録**

`templates/profiles/full.json` の `recommended` 内、`".claude/skills/maintenance/SKILL.md",` の直後に追加:
```json
    ".claude/skills/uat/SKILL.md",
```

- [ ] **Step 2: JSON 妥当性と contract を確認**

```bash
python3 -c "import json; json.load(open('templates/profiles/full.json')); print('full.json valid')"
python3 scripts/check_framework_contract.py --profile=full
```
Expected: `full.json valid` ＋ `PASS`

- [ ] **Step 3: コミット**

```bash
git add templates/profiles/full.json
git commit -m "feat(b3b): add uat skill to full profile"
```

---

## Task 8: 統合検証

- [ ] **Step 1: 全検証を green に**

Run（順に）:
- `python3 scripts/check_framework_contract.py --profile=full` → `PASS`
- `python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project` → `PASS`
- `python3 scripts/check_reference_drift.py` → `PASS`（警告ゼロ）
- `python3 -m unittest tests.test_mirror_identity` → `OK`
- `python3 scripts/run_eval.py --tier 0` → `Ran <N> tests` / `OK`（既存293＋新3＝296 見込み）
- `python3 scripts/run_eval.py --tier 2` → `Result: PASS`
- `python3 scripts/check_status.py --root . --strict` → `PASS`

- [ ] **Step 2: 内容目視レビュー**

`templates/UAT-RESULTS.template.md` が AC ごとの 期待/実際/合否/証拠＋サインオフを持つこと、`uat` SKILL.md が qa-verification との違い・client サインオフ・Red Flags を含むこと、`check_status.py` の存在チェックが ACCEPTANCE 条件付きで日本語エラー＋uat skill 誘導であることを目視。

- [ ] **Step 3: 証拠コミット（変更があれば）**

変更が無ければ空コミットは作らない（検証結果は実行ログが証拠）。

---

## Self-Review（プラン執筆者チェック・実施済み・grill 反映後）

- **spec カバレッジ**: 決定1（advisory+連動）=Task3 既存ゲート連動・新フェーズなし / 決定2（スクリプト強制存在チェック）=Task3 check_gate_prerequisites＋テスト / 決定3（client サインオフ）=Task1 サインオフ節・機械は存在のみ / 決定4（ACCEPTANCE 条件付き）=Task3 acceptance.exists() 分岐。登録=Task1/2/7、結合=Task4/5/6、検証=Task8。**未カバーなし**。
- **grill 反映**: 致命1（check_status.py ミラー必須・tests 非ミラー=Task3 Step5・ファイル構成注記）／致命2（check_gate_prerequisites 配置・日本語エラー=Task3 Step3）／致命3（既存テスト非回帰＝ACCEPTANCE 無し素通り・新3本は入室後ファイル生成=Task3 Step1）／要検討1（example に UAT-RESULTS 置かない＝B3a/B3c 準拠・ファイル構成注記）／要検討2（抜け道は docs-sync＋Red Flags=Task5/Task2）。
- **プレースホルダ**: テンプレの `<記入>` は記入欄。手順に TBD 無し。
- **型/名称整合**: skill 名 `uat`、テンプレ `UAT-RESULTS.template.md`、出力 `docs/handover/UAT-RESULTS.md`、トリガ `docs/requirements/ACCEPTANCE.md`、関数 `check_gate_prerequisites`、参照元 ship-and-docs Step2.7、検証元 docs-sync は全 Task で一致。
- **コミット健全性**: Task3 は failing テスト→実装→緑→ミラーの TDD 順。各 Task 後に contract green。**赤コミットなし**（Task3 は実装とテストを同一コミットにするため、コミット時点で緑）。

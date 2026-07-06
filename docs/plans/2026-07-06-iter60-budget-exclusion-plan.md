# iter60 budget ratchet policy 見直し（drift 支配構造の計数除外）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: implement は Aegis の `tdd` / `subagent-dev` skill に従う（RED-first・per-task commit・赤 HEAD を残さない）。Steps はチェックボックス（`- [ ]`）で追跡する。
> **正本**: 設計 = `docs/specs/2026-07-06-iter60-budget-exclusion-design.md` / brainstorm = 同 `-brainstorm-record.md`。
> **grill-plan 反映済（2026-07-06・致命ゼロ）**: 候補致命（re 未 import／routing.md pin 他テスト／token pin 存続）を実証で全消し。要検討1（B1 は SKIP＋**実** mutation demo＝per-task commit で auto-drill は SKIP＝事実修正）・要検討2（濫用ガードを findall＋`len==1` で多領域封鎖）・要検討3（緑基準を相対表現へ）を反映。

**Goal:** budget の語数計数から「別 invariant（drift）が支配する圧縮不能な構造（routing.md の agent roster）」を除外し、budget が bloat しうる自由 prose のみを測るようにする。除外の濫用（prose を包んで budget 回避）はテストで封じる。

**Architecture:** `context_budget.py` の計数前に `<!-- aegis:budget-exclude-start/end -->` マーカー領域を strip（`check`/`tighten`/`seed` 共通・単一 owner）。`routing.md` の roster をマーカーで囲み budget を 90→70（prose のみ）へ。濫用ガード＝「routing.md の除外領域 == drift 支配の全 agent（`.claude/agents/*.md`）を含み、budget が測るべき prose を含まない」をテスト固定。tighten-only ラチェット・drift・moat は不変。除外は opt-in（マーカー無しファイルは従来どおり全語計数＝後方互換）。

**Tech Stack:** Python（`scripts/context_budget.py`・`re`）、`unittest`（`tests/test_context_budget.py`）、Markdown rule（`.claude/rules/routing.md`）、語数予算レジストリ（`scripts/context-budgets.json`）、`CLAUDE.md`（policy）。

---

## Global Constraints

- **計数の単一 owner を保つ**: `word_count` は純関数のまま。除外は `_strip_excluded` に隔離し、`_budget_word_count = word_count(_strip_excluded(text))` を `check`/`tighten`/`seed` の**3経路すべて**が通す（乖離不能）。`word_count` の外部利用（もしあれば）は不変。
- **fail-graceful（安全側）**: unmatched/nested マーカーは strip せず全語計数（bloat を隠さない）。非貪欲正規表現＝`start` に対応する `end` が無ければ無マッチ＝原文返し。実測: unmatched-start は 93語（全計数）、正常対は 70語。
- **後方互換（opt-in）**: マーカーを持たないファイルは strip 前後で不変＝従来どおり全語計数。既存 budget（他19ファイル）は不変。
- **routing.md の実測値**: マーカー囲み後の raw = 96語、`_strip_excluded` 後 = **70語**（prose のみ）。budget = **70**（`70 > 70 == False` で境界 PASS）。roster に agent を1体足しても除外領域内＝budget 不変（drift が別途 roster↔agents/ を検証）。
- **濫用ガード（最重要）**: 「除外してよいのは別 invariant で pin 済の内容だけ」を policy 化し、routing.md では **除外領域 ⊇ drift 全 agent 名 かつ 除外領域 ⊉ budget 対象 prose** をテスト固定。RED-first: マーカー追加前は除外領域が無く（regex None）テストが FAIL。
- **drift 不変**: マーカーは HTML コメント＝`check_reference_drift #1` の backtick 名抽出に非干渉（roster は引き続き抽出・pin される）。マーカー追加後も drift PASS を回帰確認。
- **B1 drill は SKIP＋実 mutation demo（qa フェーズ・grill-plan 要検討1）**: Task1/2 で **per-task コミット**するため qa 時の `git diff HEAD` は空＝auto-drill は **SKIP**（qa-verification skill の想定内縁ケース）。`.drill` に `{"skip":true,"reason":...}` を置き、reason に**手動 mutation の実証**を明記＝`context_budget.py` は振る舞いコードゆえ**実 mutation**を行う: (1) `_strip_excluded` を恒等（`return text`）に変異→`test_excluded_region_not_counted` が実 RED→revert で GREEN。(2) `_budget_word_count` を `word_count(text)`（strip 抜き）に変異→同テスト RED→revert。(3) 濫用ガードの RED-first（マーカー前は regex None で FAIL→追加で GREEN）。iter59 の token-pin demo より強い実 mutation。qa ref は claims 付き `docs/qa-reports/iter60-qa.md`（罠 g/p）。
- **言語**: 計画・LEARNINGS・CLAUDE.md policy は日本語/英語混在（CLAUDE.md 既存踏襲）。`routing.md`・`context_budget.py` は英語（既存踏襲）。
- **SemVer**: v1.20.0 → **v1.21.0（MINOR）**。除外機構は追加・opt-in・公開/運用契約は不変。ship で3箇所 bump。
- **規模**: **M**（5ファイル: context_budget.py ＋ routing.md ＋ context-budgets.json ＋ test_context_budget.py ＋ CLAUDE.md）。M framework は review+qa+security 必須・**deploy 自動 exempt**。

---

## File Structure

| ファイル | 責務 | 変更 |
|---------|------|------|
| `scripts/context_budget.py` | 語数予算の単一 owner。**除外ロジック追加** | Modify（`re` import＋`_EXCLUDE_RE`/`_strip_excluded`/`_budget_word_count`＋3経路の呼び出し置換） |
| `tests/test_context_budget.py` | context_budget 単体テスト | Modify（`import re`＋除外ロジック 2 テスト＋濫用ガード 1 テスト） |
| `.claude/rules/routing.md` | routing 正本。roster をマーカーで囲む | Modify（roster 前後にマーカー2行＝HTML コメント） |
| `scripts/context-budgets.json` | 語数予算レジストリ | Modify（routing.md `90`→`70`） |
| `CLAUDE.md` | 「## Context Budget Policy」節に除外 policy（terse・kernel budget 650 制約下） | Modify（terse 1行追記＝23語・641/650） |

---

## 確定文言A — context_budget.py 追加コード（実測検証済）

`scripts/context_budget.py` の import 群に `re` を追加し、`word_count` 定義の直後に以下を追加:

```python
import re
```

（`from __future__ import annotations` の下・既存 `import json` 等と並べる。）

`word_count` 関数の直後（現 22行目付近）に追加:

```python
# Budget-exclude markers: content whose growth is governed by ANOTHER invariant
# (e.g. the routing roster, drift-pinned to .claude/agents/) is wrapped in these
# and excluded from the word count, so the budget measures bloat-prone free prose
# only. Unmatched/nested markers strip nothing (fail-graceful = count everything,
# never hide bloat). Non-greedy: a start with no matching end does not match.
_EXCLUDE_RE = re.compile(
    r"<!--\s*aegis:budget-exclude-start\s*-->.*?<!--\s*aegis:budget-exclude-end\s*-->",
    re.DOTALL,
)


def _strip_excluded(text: str) -> str:
    return _EXCLUDE_RE.sub("", text)


def _budget_word_count(text: str) -> int:
    return word_count(_strip_excluded(text))
```

`check`/`tighten`/`seed` の中の **3箇所**（各 `count = word_count(p.read_text(encoding="utf-8"))`）を以下に置換:

```python
        count = _budget_word_count(p.read_text(encoding="utf-8"))
```

（3箇所ともバイト一致の同一行＝replace_all で置換可。）

## 確定文言B — routing.md のマーカー（roster を囲む・strip 後 70語）

`.claude/rules/routing.md` の `## Agents` 節の roster ブロックをマーカーで囲む。改修後の該当部:

```markdown
## Agents

<!-- aegis:budget-exclude-start -->
Subagents: `planner`, `implementer`, `reviewer`, `qa`, `security`, `ui`,
`qa-browser`, `integration-specialist`, `translation-specialist`,
`reviewer-testing`, `reviewer-performance`, `reviewer-maintainability`.
Each agent's own file defines its domain.
<!-- aegis:budget-exclude-end -->

`brainstorm` runs in session context (live user dialogue), not as a subagent.
```

Principle 節・Subagent continuation 節・browser-assist/brainstorm 注記は**不変**（prose＝budget 対象のまま）。

## 確定文言C — CLAUDE.md policy（「## Context Budget Policy」節に追記・terse）

**⚠ 実装時訂正**: CLAUDE.md は `check_framework_contract.py` の `MAX_CLAUDE_WORDS=650` で kernel budget が強制される（baseline 618・headroom 32）＝当初想定の「対象外＝無制約」は誤り。verbose 2項（~90語）は 715>650 で contract FAIL するため、**terse 1行（23語）**に収め、詳細は spec＋`context_budget.py` コメントへ委ねる。floor co-bump 規則は iter59 LEARNINGS 既載ゆえ再掲しない。

既存節末尾に追記（23語・CLAUDE.md 641/650・headroom 9 を実測確認）:

```markdown
- Budget counts bloat-prone prose; invariant-pinned structure may be `<!-- aegis:budget-exclude-start/end -->`-wrapped out of the count when a test pins region==content. See `scripts/context_budget.py`.
```

---

## Task 1: context_budget.py に除外ロジック（RED-first・単一コミット）

**Files:**
- Modify: `scripts/context_budget.py`（除外ロジック＋3経路置換）
- Modify: `tests/test_context_budget.py`（`import re`＋除外 2 テスト）

- [ ] **Step 1: 除外の単体テストを追加（RED）**

`tests/test_context_budget.py` の import 群に `import re` を追加（`import json` の下）。`TestRatchet` クラスの後に追加:

```python
class TestBudgetExclude(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aegis-ctxbudget-x-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_excluded_region_not_counted(self):
        # prose 10語 ＋ 除外領域(マーカー3+100+3=106語) → 計数=10（除外なしなら116）
        body = ("w " * 10 + "\n<!-- aegis:budget-exclude-start -->\n"
                + "x " * 100 + "\n<!-- aegis:budget-exclude-end -->\n")
        p = Path(self.tmp) / ".claude" / "rules" / "r.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        _registry(self.tmp, {"budgets": {".claude/rules/r.md": 20}})
        self.assertEqual(context_budget.check(self.tmp), [])  # 10 ≤ 20

    def test_unmatched_marker_counts_everything(self):
        # start だけ（end 無し）→ strip せず全計数（fail-graceful・bloat を隠さない）
        body = ("w " * 10 + "\n<!-- aegis:budget-exclude-start -->\n" + "x " * 100 + "\n")
        p = Path(self.tmp) / ".claude" / "rules" / "r.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
        _registry(self.tmp, {"budgets": {".claude/rules/r.md": 20}})
        failures = context_budget.check(self.tmp)
        self.assertTrue(any("rules/r.md" in f for f in failures), failures)
```

- [ ] **Step 2: RED を確認**

Run:
```bash
cd aegis && python3 -m pytest tests/test_context_budget.py::TestBudgetExclude -v
```
Expected: `test_excluded_region_not_counted` が **FAIL**（除外未実装＝116語 > 20 で failures 非空＝`assertEqual([], ...)` 不成立）。`test_unmatched_marker_counts_everything` は偶然 PASS しうる（未実装でも全計数）＝除外テストの RED が主眼。

- [ ] **Step 3: 除外ロジックを実装（確定文言A）**

`scripts/context_budget.py` に §確定文言A を適用（`import re`＋`_EXCLUDE_RE`/`_strip_excluded`/`_budget_word_count`＋`check`/`tighten`/`seed` の3経路を `_budget_word_count(...)` に置換）。

- [ ] **Step 4: GREEN を確認**

Run:
```bash
cd aegis && python3 -m pytest tests/test_context_budget.py -v
```
Expected: `TestBudgetExclude` 2件＋既存 `TestCheck`/`TestRatchet`/`TestRealRepo` すべて PASS。

- [ ] **Step 5: コミット**

```bash
cd aegis && git add scripts/context_budget.py tests/test_context_budget.py
git commit -m "feat(iter60): context_budget に budget-exclude マーカー除外ロジック（計数を bloat prose に限定）"
```

---

## Task 2: routing.md に適用＋濫用ガード＋policy（RED-first・単一コミット）

**Files:**
- Modify: `tests/test_context_budget.py`（濫用ガード 1 テスト）
- Modify: `.claude/rules/routing.md`（roster をマーカーで囲む）
- Modify: `scripts/context-budgets.json`（routing.md 90→70）
- Modify: `CLAUDE.md`（policy 追記）

- [ ] **Step 1: 濫用ガードテストを追加（RED）**

`tests/test_context_budget.py` の `TestBudgetExclude` の後に追加:

```python
class TestRoutingExcludeAntiAbuse(unittest.TestCase):
    """濫用ガード: routing.md の除外領域は drift 支配の roster のみ。任意 prose を
    包んで budget を回避できないことを固定（除外領域 ⊇ 全 agent 名 かつ ⊉ 対象 prose）。"""

    def test_excluded_is_drift_roster_not_prose(self):
        routing = (ROOT / ".claude" / "rules" / "routing.md").read_text(encoding="utf-8")
        regions = re.findall(
            r"<!--\s*aegis:budget-exclude-start\s*-->(.*?)<!--\s*aegis:budget-exclude-end\s*-->",
            routing, re.DOTALL)
        # 多領域濫用の封鎖: routing.md の除外は roster ただ1つのみ（2つ目のマーカー対で
        # prose を包む濫用を検知＝grill-plan 要検討2）。
        self.assertEqual(len(regions), 1,
                         f"routing.md の budget-exclude 領域は roster の1つのみであるべき（実際 {len(regions)} 個）")
        excluded = regions[0]
        # (a) drift 支配の全 agent（.claude/agents/*.md）が除外領域内（roster が除外対象）
        agent_stems = sorted(p.stem for p in (ROOT / ".claude" / "agents").glob("*.md"))
        self.assertTrue(agent_stems, "agents/ が空")
        for a in agent_stems:
            self.assertIn(f"`{a}`", excluded,
                          f"drift roster の `{a}` が除外領域外＝除外が roster と不一致")
        # (b) budget が測るべき prose は除外領域に無い（bloat 隠しの濫用防止）
        for prose in ("SendMessage", "harness-enforced", "Principle"):
            self.assertNotIn(prose, excluded,
                             f"prose '{prose}' が除外領域に混入＝budget 回避の濫用")
```

- [ ] **Step 2: RED を確認**

Run:
```bash
cd aegis && python3 -m pytest tests/test_context_budget.py::TestRoutingExcludeAntiAbuse -v
```
Expected: **FAIL**（`assertIsNotNone` 不成立＝routing.md にまだマーカーが無い）。

- [ ] **Step 3: routing.md に マーカー適用（確定文言B）**

`.claude/rules/routing.md` の roster ブロック（`Subagents: …` から `Each agent's own file defines its domain.` まで）の直前に `<!-- aegis:budget-exclude-start -->`、直後に `<!-- aegis:budget-exclude-end -->` を挿入（§確定文言B と一致）。

- [ ] **Step 4: strip 後の語数が 70 であることを実測**

Run:
```bash
cd aegis && python3 -c "import sys; sys.path.insert(0,'scripts'); import context_budget as c; print(c._budget_word_count(open('.claude/rules/routing.md').read()))"
```
Expected: `70`（≠70 なら §確定文言B と差分＝合わせ直す）。

- [ ] **Step 5: budget を 90→70 に付替**

`scripts/context-budgets.json` の該当行を置換:

置換前: `    ".claude/rules/routing.md": 90,`
置換後: `    ".claude/rules/routing.md": 70,`

- [ ] **Step 6: CLAUDE.md policy 追記（確定文言C）**

`CLAUDE.md` の「## Context Budget Policy」節末尾に §確定文言C の2項を追記。

- [ ] **Step 7: 濫用ガード GREEN＋予算＋drift＋契約を確認**

Run:
```bash
cd aegis && python3 -m pytest tests/test_context_budget.py -v 2>&1 | tail -5
python3 scripts/context_budget.py; echo "budget exit=$?"
python3 scripts/check_reference_drift.py >/dev/null 2>&1; echo "drift exit=$?"
python3 scripts/check_framework_contract.py >/dev/null 2>&1; echo "contract exit=$?"
```
Expected: 全 pytest PASS・budget exit 0（routing.md 70/70 境界 PASS）・drift exit 0（マーカーは backtick 抽出に非干渉＝roster 引き続き pin）・contract exit 0。

- [ ] **Step 8: フルスイート緑を確認**

Run:
```bash
cd aegis && python3 -m pytest -q
```
Expected（相対基準・grill-plan 要検討3）: **0 failed**、iter59 baseline（1052 passed）に対し**新規3件増**（除外2＋濫用ガード1）。絶対数は環境差で揺れるため合否は「0 failed ＋ 新規3件 GREEN」で判定。

- [ ] **Step 9: コミット**

```bash
cd aegis && git add tests/test_context_budget.py .claude/rules/routing.md scripts/context-budgets.json CLAUDE.md
git commit -m "feat(iter60): routing roster を budget から除外（マーカー適用・budget 90→70・濫用ガード・policy 明文化）"
```

---

## 後続フェーズ（この plan の範囲外・STATUS next_action に従う）

implement 完了後: grill-code → review（盲検2次・罠 o）→ qa（**B1 SKIP＋実 mutation demo**＝context_budget.py の `_strip_excluded`/`_budget_word_count` を実変異→対象テスト RED→revert・claims 付き iter60-qa.md・罠 d/g/m/n/p/r）→ security（盲検2次・除外＝bloat 隠し濫用面を突く）→ deploy(M exempt・罠 h) → ship（v1.20.0→**v1.21.0**・3箇所 bump・TO-CLIENT・LEARNINGS）→ docs → dev_ready_for_client → **push 手前で停止**。

## Self-Review（spec 突合）

- **spec §コンポーネント分解の5ファイル**: context_budget.py（Task1）／test（Task1,2）／routing.md（Task2）／context-budgets.json（Task2）／CLAUDE.md（Task2）＝全カバー。✓
- **spec §濫用ガード**: Task2 で「除外領域 ⊇ drift 全 agent かつ ⊉ 対象 prose」をテスト固定＝任意 prose 包み込み不可。✓
- **spec §残余 floor（state-machine/bug-diagnosis）**: §確定文言C の policy 2項目に co-bump を明記（機構追加なし）。✓
- **spec §fail-graceful**: Task1 `test_unmatched_marker_counts_everything`＋実測（unmatched=93全計数）でカバー。✓
- **spec §テスト戦略（RED-first・B1 実 drill・drift 回帰）**: Task1/2 が RED-first、後続 qa で本物 drill、Step7 で drift 回帰。✓
- **placeholder スキャン**: TBD/TODO なし・全 step に実コマンド/実コード。✓
- **型/名称整合**: `_EXCLUDE_RE`/`_strip_excluded`/`_budget_word_count`（Task1）とテストの参照が一貫。budget 70・strip 後 70 が確定文言A/B/実測 step と整合。✓

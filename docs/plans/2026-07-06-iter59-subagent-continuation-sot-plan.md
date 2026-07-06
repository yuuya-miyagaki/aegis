# iter59 サブエージェント継続（SendMessage）SoT 定義 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: implement は Aegis の `tdd` / `subagent-dev` skill に従う（RED-first・per-task commit）。Steps はチェックボックス（`- [ ]`）で追跡する。
> **正本**: 設計 = `docs/specs/2026-07-06-iter59-subagent-continuation-sot-design.md` / brainstorm = 同 `-brainstorm-record.md`。
> **一次情報**: iter58 review 盲検2次 note1（`SendMessage` が qa.md/qa-verification にのみ出現・機構定義が正本ファイルに無い＝dangling 用語）。
> **grill-plan 反映済（2026-07-06・致命ゼロ）**: 候補致命4点（旧 principle pin 衝突／template mirror parity／budget tamper-guard／drift #1 誤 FAIL）を実証で全消し。要検討1（headroom-0 の受容＋co-bump ルール文書化）・要検討2（単一コミット化＝赤 HEAD 回避）・要検討4（フル緑を相対基準へ）を織り込み。要検討3（pin `harness-enforced` の言い換え脆さ＝意図した tripwire）は記録のみ。

**Goal:** サブエージェント継続機構 `SendMessage` を `.claude/rules/routing.md` に「## Subagent continuation」節として**単一正本（SoT）**で定義し、iter58 で残った dangling 用語（review 2次 note1）を解消する。継続定義の load-bearing 核（機構名 `SendMessage`＋非強制性 `harness-enforced`）を token pin で決定論的に守る。

**Architecture:** guidance のみ（hook で決定論強制はしない・aegis 哲学の「保証=決定論／手順=モデル委譲」の手順側）。routing.md（サブエージェント機構の正本）に継続節を追加し、qa-verification の既存 `SendMessage` 用法を裏打ちして dangling を解消する。principle を1文に圧縮して bump を最小化し、`context-budgets.json` の routing.md budget を追加分だけ引き上げる（**75→90**・実測に基づく最小値）。判定・ゲート機構（judge / check_status / check_reference_drift）には手を入れない。

**Tech Stack:** Markdown rule（`.claude/rules/routing.md`）、語数予算ラチェット（`scripts/context_budget.py`＋`scripts/context-budgets.json`）、Python `unittest`（`tests/test_skill_guidance_tokens.py`）、参照ドリフト lint（`scripts/check_reference_drift.py`）。

---

## Global Constraints

- **語数予算（最重要・実測根拠）**: budget 単位＝空白区切りトークン `len(text.split())`（`context_budget.py:word_count`・`wc -w` と一致）。現行 routing.md = **68 words**、budget = **75**（headroom 7）。改修後の routing.md 確定文言は**実測 90 words**（下記§確定文言A で検証済）。したがって budget を **75→90** に引き上げ、`context_budget.check()` は `90 > 90 == False` で PASS（境界は strict `>`＝**ちょうど 90 は合格**）。
- **予算引き上げの正当化（この iter の核心的設計判断）**: iter58 は budget-raise を**却下**した（qa-verification に圧縮可能な冗長があった＝tighten-only ラチェットの anti-bloat 趣旨）。**iter59 は状況が質的に異なる**: routing.md は内容が100% load-bearing で**圧縮パスが存在しない**——agent roster（バッククォート列挙）は `check_reference_drift #1` が `.claude/agents/*.md` と双方向 mirror で**drift-pin**（削ると FAIL）、rule 本文・browser-assist 参照・brainstorm 注記も必須。principle 以外に圧縮余地なし。よって本 bump は「圧縮回避のための水増し」ではなく「**圧縮不能な pinned ファイルへの正当な rule 追加の受容**」。bump は追加サイズ分に限定（75→90）。この区別を **LEARNINGS に記録**し、ラチェットの anti-bloat 趣旨は守る。
- **設計見積り 90 vs 生ドラフト 91 の解消（plan で確定）**: 設計ノートの当初文言をそのまま置くと **91 words**（budget 90 を1超過＝FAIL）。principle 圧縮時に冗長な2つ目の "work" を落とす（"keep **work** in session context" → "keep in session context"・意味不変の正当な concision）ことで**ちょうど 90 words**に着地させる。実測済（`python3 -c` で 90 を確認）。
- **headroom-0 の受容と co-bump ルール（grill-plan 要検討1）**: 改修後 routing.md は content 90 / budget 90＝**headroom 0**（現行 75/68 の headroom 7 から低下）。設計承認済の「最小 bump＝90」に忠実であり、かつ headroom 0 はラチェット（tighten=current count）の自然状態でもある。本 iter の期待経路（review/qa/security は diff 審査のみ・ship は routing.md 非対象）では摩擦ゼロ。唯一の残リスク＝**盲検2次の fix-forward が routing.md に加筆した場合**は context_budget FAIL（91>90）＝その diff で **budget も共 bump**して自己修復する（これを LEARNINGS に「以後 routing.md 加筆変更は同一 diff で budget 共 bump 必須」として記録）。budget を 90 超へ引き上げて headroom を作る案は承認パラメータからの逸脱ゆえ**採らない**（沈黙の脆さを文書化された脆さに変える方針）。
- **agent roster を触らない（drift-pin 回帰）**: `check_agents`（drift #1）は正規表現 `` `([a-z][a-z0-9_-]*)` `` でバッククォート小文字トークンを抽出し agents/ と双方向照合する。新節が追加するバッククォート語 `` `maxTurns` `` は大文字 T を含み全体マッチせず、`SendMessage` は非バッククォート＝**どちらも agent 名として抽出されない**（実測: 追加後も `check_reference_drift.py` PASS を確認する）。roster 行そのものは**不変**。
- **token pin は短核・RED-first・一意性（iter58 教訓の反映）**: pin は機構名 `SendMessage` と非強制核 `harness-enforced` の**短核2トークン**。長文完全一致は正当な言い換えで false RED を招くため避ける（設計 §テスト戦略）。両トークンとも**改修後の routing.md 内で一意**（現行 count 0＝RED-first 成立を実測済・追加後は各1）＝iter58 の「重複トークンは単一削除で不発」問題を回避し、単一削除で確実に RED になる。
- **qa-verification は不変**: 既存 `SendMessage` 用法が routing.md 定義で裏打ちされ dangling 解消。qa-verification は編集しない（headroom 6 を守る・iter58 `TestQaBrowserDelegation` の3 pin は緑のまま）。
- **判定・ゲート機構不変**: judge / `check_status.py` / drill / hook は不変。ハーネス強制は追加しない（継続は運用 guidance）。
- **言語**: 計画・LEARNINGS は日本語（既存踏襲）。`routing.md` は英語制御ファイル（既存踏襲）＝追加節も英語。
- **SemVer**: v1.19.0 → **v1.20.0（MINOR）**。routing.md への後方互換な rule 追加・公開/運用契約は不変。ship フェーズで3箇所 bump（contract 定数 `FRAMEWORK_VERSION`＋STATUS テンプレ＋live STATUS）。
- **規模**: **M**（framework・3ファイル: routing.md ＋ context-budgets.json ＋ test_skill_guidance_tokens.py）。M framework は review+qa+security 必須・**deploy 自動 exempt**（`SIZE_ALLOWED_PHASES`・罠 h）。3ファイルは M（2-5）維持＝`update-task.sh` の size 変更不要。
- **qa の B1 drill**: rule/test の変更＝mutant 対象の振る舞いコードなし＝**B1 SKIP**（`test-strength.drill` に `{"skip":true,"reason":...}`）＋RED-first 代替実証（token pin の RED→GREEN）。qa ref は claims 付き `docs/qa-reports/iter59-qa.md`（罠 g/p）。

---

## File Structure

| ファイル | 責務 | 変更 |
|---------|------|------|
| `.claude/rules/routing.md` | サブエージェント機構・routing の正本。継続定義の**単一正本** | Modify（principle 1文化＋末尾に継続節追加＝68→90 words） |
| `scripts/context-budgets.json` | 語数予算レジストリ（単一 owner） | Modify（routing.md budget `75`→`90`） |
| `tests/test_skill_guidance_tokens.py` | rule/skill 本文 load-bearing トークンの drift ガード | Modify（`ROUTING` 読み込み＋継続 pin クラス追加＝2 assertion） |

`.claude/skills/qa-verification/SKILL.md` は**不変**（既存 `SendMessage` 用法が routing.md 定義で裏打ちされる）。`.claude/agents/*.md`（roster）も**不変**。

---

## 確定文言A — routing.md 改修後の全文（実測 90 words）

改修後の `.claude/rules/routing.md` は以下（バイト正本・`len(split())==90` を実測確認済）:

```markdown
# Routing

## Principle

Subagents only when they make work clearer/safer/smaller; else keep in session context.

## Agents

Subagents: `planner`, `implementer`, `reviewer`, `qa`, `security`, `ui`,
`qa-browser`, `integration-specialist`, `translation-specialist`,
`reviewer-testing`, `reviewer-performance`, `reviewer-maintainability`.
Each agent's own file defines its domain.

`brainstorm` runs in session context (live user dialogue), not as a subagent.
`browser-assist` skill (`.claude/skills/browser-assist/SKILL.md`) is available to any agent needing browser automation.

## Subagent continuation

Resume a stalled subagent via SendMessage (same agent, context preserved), not a fresh re-dispatch.
Guidance, not harness-enforced; bounded by each agent's `maxTurns` and the 3-failure rule.
```

変更点は2つのみ:
1. **Principle 節**（5-6行目）を2文→1文に圧縮（冗長な2つ目の "work" を落とす）。
2. **末尾**（16行目の後）に空行＋「## Subagent continuation」節を追加。

Agents 節（roster・browser-assist・brainstorm 注記）は**1バイトも変えない**。

---

## Task 1: 継続定義の token pin を追加（RED-first・**この時点ではコミットしない**）

> **コミット方針（grill-plan 要検討2）**: RED テストと GREEN 実装は**単一コミット**にまとめる（iter58 の implement=単一コミット踏襲・赤 HEAD を残さない）。Task 1 で test を書き RED を実証し、**コミットせずに** Task 2 で実装して GREEN 化、Task 2 末尾で3ファイルを1コミット。RED-first は「実装前に RED run を踏む」ことで担保する（赤 commit は不要）。

**Files:**
- Test: `tests/test_skill_guidance_tokens.py`（Modify: module 冒頭に `ROUTING` 読込＋新クラス追加）

- [ ] **Step 1: RED-first 前提を再確認**

Run:
```bash
cd aegis && grep -c "SendMessage" .claude/rules/routing.md; grep -c "harness-enforced" .claude/rules/routing.md
```
Expected: 両方 `0`（現行 routing.md に継続定義が無い＝pin は追加時 FAIL する）。

- [ ] **Step 2: `ROUTING` 読込を module スコープに追加**

`tests/test_skill_guidance_tokens.py` の `QA = (...).read_text(...)` の直後（18行目付近）に追加:

```python
ROUTING = (ROOT / ".claude" / "rules" / "routing.md").read_text(encoding="utf-8")
```

- [ ] **Step 3: 継続 pin クラスを追加**

`TestSharedMutableResourceRule` クラスの後（117行目付近・`if __name__` の前）に追加:

```python
class TestSubagentContinuationSoT(unittest.TestCase):
    """iter59: routing.md が SendMessage 継続の単一正本（SoT）。iter58 review 2次
    note1 の dangling（機構定義が正本ファイルに無い）を解消。load-bearing 核＝機構名
    SendMessage ＋ 非強制性 harness-enforced を短核 token pin。両トークンとも routing.md
    内で一意ゆえ単一削除で RED（iter58 の presence 保証教訓・重複は不発の反省を反映）。
    長文完全一致は正当な言い換えで false RED を招くため避ける。"""

    def test_continuation_mechanism_present(self):
        self.assertIn("SendMessage", ROUTING,
                      "サブエージェント継続機構（SendMessage）の定義が routing.md から消えている")

    def test_continuation_is_guidance_not_enforced(self):
        self.assertIn("harness-enforced", ROUTING,
                      "継続が guidance（非ハーネス強制・maxTurns/3-failure で有界）である旨が消えている")
```

- [ ] **Step 4: RED を確認（実装前に FAIL すること）**

Run:
```bash
cd aegis && python3 -m pytest tests/test_skill_guidance_tokens.py::TestSubagentContinuationSoT -v
```
Expected: **2 failed**（`AssertionError: ... が routing.md から消えている`）。継続定義が routing.md に未追加のため。**RED を確認したらコミットせず Task 2 へ進む**（単一コミット方針）。

---

## Task 2: routing.md に継続節追加＋principle 圧縮＋budget 引き上げ（GREEN・3ファイル1コミット）

**Files:**
- Modify: `.claude/rules/routing.md`（principle 1文化＋継続節追加）
- Modify: `scripts/context-budgets.json`（routing.md budget `75`→`90`）

- [ ] **Step 1: Principle を1文に圧縮**

`.claude/rules/routing.md` の5-6行目を置換:

置換前（2行）:
```
Subagents only when they make work clearer, safer, or smaller.
When in doubt, keep work in the session context.
```
置換後（1行）:
```
Subagents only when they make work clearer/safer/smaller; else keep in session context.
```

- [ ] **Step 2: 末尾に継続節を追加**

`.claude/rules/routing.md` の最終行（`browser-assist` の行）の後に追加:

```
\n## Subagent continuation\n\nResume a stalled subagent via SendMessage (same agent, context preserved), not a fresh re-dispatch.\nGuidance, not harness-enforced; bounded by each agent's `maxTurns` and the 3-failure rule.\n
```
（＝§確定文言A の 18行目以降。改修後全文が §確定文言A と**バイト一致**すること。）

- [ ] **Step 3: 語数が 90 であることを実測確認**

Run:
```bash
cd aegis && python3 -c "print(len(open('.claude/rules/routing.md').read().split()))"
```
Expected: `90`（≠90 なら §確定文言A と差分がある＝文言を合わせ直す）。

- [ ] **Step 4: budget を 75→90 に引き上げ**

`scripts/context-budgets.json` の該当行を置換:

置換前:
```json
    ".claude/rules/routing.md": 75,
```
置換後:
```json
    ".claude/rules/routing.md": 90,
```

- [ ] **Step 5: token pin が GREEN になることを確認**

Run:
```bash
cd aegis && python3 -m pytest tests/test_skill_guidance_tokens.py::TestSubagentContinuationSoT -v
```
Expected: **2 passed**。

- [ ] **Step 6: 予算チェックが PASS することを確認**

Run:
```bash
cd aegis && python3 scripts/context_budget.py; echo "exit=$?"
```
Expected: FAIL 行なし・`exit=0`（`90 > 90` は False＝境界 PASS）。

- [ ] **Step 7: 参照ドリフト（roster）が PASS を維持することを確認**

Run:
```bash
cd aegis && python3 scripts/check_reference_drift.py; echo "exit=$?"
```
Expected: `exit=0`。`agent '...' referenced/exists` 系 FAIL が**出ない**こと（新節の `maxTurns`/`SendMessage` が agent 名として誤抽出されない回帰）。

- [ ] **Step 8: フレームワーク契約全体が PASS することを確認**

Run:
```bash
cd aegis && python3 scripts/check_framework_contract.py; echo "exit=$?"
```
Expected: `exit=0`（budget 更新反映後・契約違反なし）。

- [ ] **Step 9: フルスイート緑を確認**

Run:
```bash
cd aegis && python3 -m pytest -q
```
Expected（grill-plan 要検討4・相対基準）: **0 failed**、かつ iter58 baseline（実測 1050 passed）に対し**新規2件増**（`TestSubagentContinuationSoT` の2メソッド）。絶対数は環境差で揺れるため合否は「0 failed ＋ 新規2件が GREEN」で判定。

- [ ] **Step 10: コミット（RED テスト＋GREEN 実装＝3ファイル1コミット）**

単一コミット方針（要検討2）に従い、Task 1 で書いた test と Task 2 の実装を**まとめて1コミット**する:

```bash
cd aegis && git add .claude/rules/routing.md scripts/context-budgets.json tests/test_skill_guidance_tokens.py
git commit -m "feat(iter59): routing.md に SendMessage 継続の SoT を定義（dangling 解消）+ 継続 token pin + budget 75→90"
```

---

## 後続フェーズ（この plan の範囲外・STATUS next_action に従う）

implement 完了後は以下を STATUS の罠リスト（a-r）に従って進める（本 plan は plan/implement まで）:

1. **grill-code**（2段グリル2段目・致命反映）。
2. **review**（1次＋盲検2次・`docs/qa-reports/iter59-review.md`・罠 o の verdict 一致）。
3. **qa**（B1 SKIP＋RED-first 代替実証・claims 付き `iter59-qa.md`・罠 g/p/d/m/n/r）。
4. **security**（rule/test guidance のみ＝moat 非該当だが M framework で必須・盲検2次・後退なし確認）。
5. **deploy**（M で自動 exempt・罠 h）。
6. **ship**（v1.19.0→**v1.20.0**・3箇所 bump・TO-CLIENT・LEARNINGS に「圧縮不能 pinned への正当追加＝bump 許容」の区別を蒸留）。
7. **docs → dev_ready_for_client → push 手前で停止**（push=`gh auth switch --user yuuya-miyagaki`）。

---

## Self-Review（spec 突合）

- **spec §コンポーネント分解の3ファイル**: routing.md（Task 2）／context-budgets.json（Task 2）／test（Task 1）＝全カバー。✓
- **spec §予算引き上げの正当化**: Global Constraints に「圧縮不能 pinned への正当追加」区別を明記＋LEARNINGS 記録を後続に予約。✓
- **spec §テスト戦略（RED-first・B1 SKIP・drift 回帰）**: Task 1 で RED-first、Task 2 Step 7 で drift 回帰、B1 SKIP は Global Constraints に明記。✓
- **spec 見積り 90 の妥当性**: 生ドラフト 91 を実測で検出し、principle の冗長 "work" 除去で 90 に確定（設計の committed 90 を保持）＝設計との整合を計画で担保。✓
- **placeholder スキャン**: TBD/TODO/「適切に処理」等なし・全 step に実コマンド/実文言。✓
- **型/名称整合**: 新クラス名 `TestSubagentContinuationSoT`、pin トークン `SendMessage`/`harness-enforced` は Task 1/2・確定文言A・テスト assert で一貫。✓

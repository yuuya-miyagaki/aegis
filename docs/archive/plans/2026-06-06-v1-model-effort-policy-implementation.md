# Model/Effort 継承ポリシー Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AEGIS の 12 サブエージェントの `model`/`effort` を役割階層（品質固定=opus / コスト固定=sonnet / 既定=inherit）に揃え、`check_framework_contract.py` の値検証で逸脱を FAIL にする。

**Architecture:** frontmatter が CC の唯一の読み取り元（実装）。`check_framework_contract.py` を「検証器」として拡張し、役割→(model, effort) 対応表・禁止則（haiku/版番号id）・可用域則（xhigh/max は opus 限定）・網羅性を root と example 両方で検証。TDD は「検証器を先に書く（red）→ frontmatter を揃える（green）」で回す。新規テストファイルは作らず既存スクリプトを拡張（設計 §4.1）。`session-start.sh` に env 一括上書き advisory を追加。

**Tech Stack:** Python 3（`unittest`・標準スクリプト）、Bash（hooks）、Markdown frontmatter。検証コマンドは `python3 scripts/check_framework_contract.py` と `python3 -m unittest discover -s tests`。

> 作業ディレクトリは aegis リポジトリのルート（`.git` がある階層）。全パスはそこからの相対。設計の一次資料: `docs/plans/2026-06-05-v1-model-effort-policy-design.md`。

---

## File Structure

| ファイル | 責務 | 操作 |
| --- | --- | --- |
| `scripts/check_framework_contract.py` | ポリシー検証器（対応表・禁止則・可用域則・網羅性）を追加 | Modify |
| `.claude/agents/{planner,security,reviewer,qa,reviewer-testing,reviewer-performance,reviewer-maintainability}.md` | root agent の model/effort を階層に整合 | Modify ×7 |
| `examples/minimal-project/.claude/agents/{同上7本}` | example ミラーを root と同値に整合 | Modify ×7 |
| `hooks/session-start.sh` | `CLAUDE_CODE_SUBAGENT_MODEL` 検出時の軽量 advisory | Modify |
| `CLAUDE.md` | 「Model Policy」節を追加 | Modify |

**据え置き（変更なし・検証で確認のみ）:** root/example の `implementer.md` `qa-browser.md` `ui.md` `integration-specialist.md`（`inherit`/`high`）、`translation-specialist.md`（`sonnet`/`high`）。

---

## Task 1: ポリシー検証器を `check_framework_contract.py` に追加（失敗するテスト＝red）

**Files:**
- Modify: `scripts/check_framework_contract.py`（モジュール関数を `read_text` 直後 ≈ 248 行目付近に追加、`main()` 末尾の `if failures:` 直前で呼び出し）

検証器が「テスト」。現状 frontmatter（reviewer/security/planner/qa=`inherit`、specialist=`haiku`）に対して**意図的に FAIL する**のがこのタスクの red。

- [ ] **Step 1: モジュール定数と検証関数を追加**

`scripts/check_framework_contract.py` の `def read_text(...)` 定義の直後に、以下を追加する（`ROOT` は 15 行目、`read_text` は 241 行目で定義済み・`re` は既に import 済み）:

```python
# --- Model/Effort policy (design: 2026-06-05-v1-model-effort-policy-design.md) ---
# frontmatter が唯一の真実。ここは検証器（逸脱=FAIL）。値は系統エイリアスか inherit のみ。
MODEL_EFFORT_POLICY = {
    # quality-pin (opus)
    "planner.md": ("opus", "max"),
    "security.md": ("opus", "max"),
    "reviewer.md": ("opus", "xhigh"),
    "qa.md": ("opus", "high"),
    # cost-pin (sonnet floor; no haiku)
    "reviewer-testing.md": ("sonnet", "high"),
    "reviewer-performance.md": ("sonnet", "high"),
    "reviewer-maintainability.md": ("sonnet", "high"),
    "translation-specialist.md": ("sonnet", "high"),
    # default (inherit, follows session)
    "implementer.md": ("inherit", "high"),
    "qa-browser.md": ("inherit", "high"),
    "ui.md": ("inherit", "high"),
    "integration-specialist.md": ("inherit", "high"),
}
_OPUS_ONLY_EFFORTS = {"xhigh", "max"}
_VERSION_ID_RE = re.compile(r"claude-[a-z]+-\d")
# root と example ミラーの両方を同一ポリシーで検証する。
MODEL_POLICY_ROOTS = [ROOT, ROOT / "examples/minimal-project"]


def _frontmatter_section(text: str) -> str:
    m = re.match(r"---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return m.group(1) if m else ""


def check_model_effort_policy(roots) -> list:
    """役割→(model, effort) を root と example の両方で検証して失敗一覧を返す。"""
    failures = []
    for base in roots:
        agents_dir = base / ".claude/agents"
        if not agents_dir.exists():
            failures.append(f"model-policy: missing agents dir {agents_dir}")
            continue
        # 対応表照合 + 禁止則 + 可用域則
        for name, (exp_model, exp_effort) in MODEL_EFFORT_POLICY.items():
            path = agents_dir / name
            if not path.exists():
                failures.append(f"model-policy: missing {path.relative_to(ROOT)}")
                continue
            fm = _frontmatter_section(read_text(path))
            mm = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE)
            em = re.search(r"^effort:\s*(\S+)", fm, re.MULTILINE)
            model = mm.group(1) if mm else None
            effort = em.group(1) if em else None
            rel = path.relative_to(ROOT)
            if model != exp_model:
                failures.append(f"model-policy: {rel} model={model} expected {exp_model}")
            if effort != exp_effort:
                failures.append(f"model-policy: {rel} effort={effort} expected {exp_effort}")
            if model == "haiku":
                failures.append(f"model-policy: {rel} uses haiku (forbidden; floor is sonnet)")
            if model and _VERSION_ID_RE.search(model):
                failures.append(f"model-policy: {rel} uses version-pinned id '{model}' (alias or inherit only)")
            if effort in _OPUS_ONLY_EFFORTS and model != "opus":
                failures.append(f"model-policy: {rel} effort={effort} only allowed on opus-pinned roles")
        # 網羅性: ディレクトリ内の全 agent が対応表に分類済みであること
        for path in sorted(agents_dir.glob("*.md")):
            if path.name not in MODEL_EFFORT_POLICY:
                failures.append(
                    f"model-policy: {path.relative_to(ROOT)} not classified in MODEL_EFFORT_POLICY (assign a tier)"
                )
    return failures
```

- [ ] **Step 2: `main()` から呼び出す**

`scripts/check_framework_contract.py` の `main()` 末尾、`if failures:`（≈ 799 行目）の直前に1行追加する:

```python
    failures.extend(check_model_effort_policy(MODEL_POLICY_ROOTS))

    if failures:
```

- [ ] **Step 3: 検証器を走らせて red を確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: FAIL（exit 1）。出力に少なくとも以下を含む（root と example の両方で）:

```
FAIL: model-policy: .claude/agents/planner.md model=inherit expected opus
FAIL: model-policy: .claude/agents/planner.md effort=high expected max
FAIL: model-policy: .claude/agents/security.md model=inherit expected opus
FAIL: model-policy: .claude/agents/reviewer.md effort=high expected xhigh
FAIL: model-policy: .claude/agents/qa.md model=inherit expected opus
FAIL: model-policy: .claude/agents/reviewer-testing.md model=haiku expected sonnet
FAIL: model-policy: .claude/agents/reviewer-testing.md uses haiku (forbidden; floor is sonnet)
...（example 配下も同様）
```

この red が出れば検証器は正しく機能している。**ここではコミットしない（red 状態）。**

---

## Task 2: root agent frontmatter を整合（green へ前進）

**Files:**
- Modify: `.claude/agents/planner.md`, `security.md`, `reviewer.md`, `qa.md`, `reviewer-testing.md`, `reviewer-performance.md`, `reviewer-maintainability.md`

各ファイルは `model:` 行と `effort:` 行を各1本だけ持つ。以下の文字列置換を行う。

- [ ] **Step 1: opus 固定3本（planner / security）と reviewer / qa を変更**

- `.claude/agents/planner.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: max`
- `.claude/agents/security.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: max`
- `.claude/agents/reviewer.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: xhigh`
- `.claude/agents/qa.md`: `model: inherit` → `model: opus`（`effort: high` は据え置き・変更なし）

- [ ] **Step 2: specialist reviewer 3本を haiku→sonnet**

- `.claude/agents/reviewer-testing.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`
- `.claude/agents/reviewer-performance.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`
- `.claude/agents/reviewer-maintainability.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`

- [ ] **Step 3: 検証器を走らせ、root の失敗が消えたことを確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: まだ FAIL（exit 1）だが、`FAIL: model-policy: .claude/agents/...`（root）は消え、残るのは `examples/minimal-project/.claude/agents/...` の失敗のみ。**まだコミットしない。**

---

## Task 3: example ミラーを整合 → green → コミット

**Files:**
- Modify: `examples/minimal-project/.claude/agents/{planner,security,reviewer,qa,reviewer-testing,reviewer-performance,reviewer-maintainability}.md`

root と同一の値へ。各ファイルの現在値は root と同じ（`inherit`/`high` または `haiku`/`medium`）。

- [ ] **Step 1: example の opus 固定/reviewer/qa を変更**

- `examples/minimal-project/.claude/agents/planner.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: max`
- `examples/minimal-project/.claude/agents/security.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: max`
- `examples/minimal-project/.claude/agents/reviewer.md`: `model: inherit` → `model: opus`、`effort: high` → `effort: xhigh`
- `examples/minimal-project/.claude/agents/qa.md`: `model: inherit` → `model: opus`（`effort` 据え置き）

- [ ] **Step 2: example の specialist reviewer 3本を haiku→sonnet**

- `examples/minimal-project/.claude/agents/reviewer-testing.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`
- `examples/minimal-project/.claude/agents/reviewer-performance.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`
- `examples/minimal-project/.claude/agents/reviewer-maintainability.md`: `model: haiku` → `model: sonnet`、`effort: medium` → `effort: high`

- [ ] **Step 3: 検証器が PASS（green）**

Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS: aegis contract is aligned`（exit 0）。

- [ ] **Step 4: 既存テストスイートが緑のまま**

Run: `python3 -m unittest discover -s tests`
Expected: 全テスト OK（183 緑維持）。

- [ ] **Step 5: コミット（Task 1–3 をまとめて1コミット＝ポリシー＋整合）**

```bash
git add scripts/check_framework_contract.py \
  .claude/agents/planner.md .claude/agents/security.md .claude/agents/reviewer.md .claude/agents/qa.md \
  .claude/agents/reviewer-testing.md .claude/agents/reviewer-performance.md .claude/agents/reviewer-maintainability.md \
  examples/minimal-project/.claude/agents/planner.md examples/minimal-project/.claude/agents/security.md \
  examples/minimal-project/.claude/agents/reviewer.md examples/minimal-project/.claude/agents/qa.md \
  examples/minimal-project/.claude/agents/reviewer-testing.md examples/minimal-project/.claude/agents/reviewer-performance.md \
  examples/minimal-project/.claude/agents/reviewer-maintainability.md
git commit -m "feat(agents): pin model/effort by role tier + enforce in contract check"
```

---

## Task 4: `session-start.sh` に env 一括上書き advisory

**Files:**
- Modify: `hooks/session-start.sh`（Locale hint ≈ 199 行目の直前に挿入）

`CLAUDE_CODE_SUBAGENT_MODEL` が設定されると全 model 固定（security 含む）が一括降格する。block はしない＝警告のみ可視化。

- [ ] **Step 1: advisory ブロックを追加**

`hooks/session-start.sh` の `# Locale hint.`（`CONTEXT="${CONTEXT} / ドキュメントは日本語"` の行）の**直前**に挿入:

```bash
# CLAUDE_CODE_SUBAGENT_MODEL advisory: this env overrides ALL subagent model
# pins (incl. security/reviewer/qa/planner), bypassing the quality guarantee.
# Advisory only (does not block); see model-effort-policy design §10.1.
if [ -n "${CLAUDE_CODE_SUBAGENT_MODEL:-}" ]; then
  CONTEXT="${CONTEXT} | [WARNING] CLAUDE_CODE_SUBAGENT_MODEL=${CLAUDE_CODE_SUBAGENT_MODEL} overrides all model pins (security/reviewer/qa/planner) — quality guarantees globally bypassed"
fi
```

（`set -euo pipefail` 下でも `${CLAUDE_CODE_SUBAGENT_MODEL:-}` の `:-` で unbound エラーを回避している点に注意。）

- [ ] **Step 2: env 未設定時に advisory が出ないことを確認**

Run: `unset CLAUDE_CODE_SUBAGENT_MODEL; echo '{}' | bash hooks/session-start.sh`
Expected: 出力（emit_context の JSON）に `CLAUDE_CODE_SUBAGENT_MODEL` の WARNING を**含まない**。

- [ ] **Step 3: env 設定時に advisory が出ることを確認**

Run: `CLAUDE_CODE_SUBAGENT_MODEL=haiku bash -c "echo '{}' | bash hooks/session-start.sh" | grep -o "CLAUDE_CODE_SUBAGENT_MODEL=haiku overrides all model pins"`
Expected: `CLAUDE_CODE_SUBAGENT_MODEL=haiku overrides all model pins` が表示される（grep ヒット）。

- [ ] **Step 4: hook 出力スキーマテストが緑のまま**

Run: `python3 -m unittest discover -s tests`
Expected: 全テスト OK。

- [ ] **Step 5: コミット**

```bash
git add hooks/session-start.sh
git commit -m "feat(hooks): advise on session-start when CLAUDE_CODE_SUBAGENT_MODEL overrides pins"
```

---

## Task 5: `CLAUDE.md` に Model Policy 節

**Files:**
- Modify: `CLAUDE.md`（`## Routing` 節の直後に新節を追加）

CLAUDE.md はエージェント制御ファイル＝英語。

- [ ] **Step 1: Model Policy 節を追加**

`CLAUDE.md` の `## Routing` 節（`Details in \`.claude/rules/routing.md\`.` の行）の直後に挿入:

```markdown
## Model Policy

Agent `model`/`effort` is pinned by role tier (enforced by `scripts/check_framework_contract.py`):

- Quality-pin (`opus`): `planner`=max, `security`=max, `reviewer`=xhigh, `qa`=high.
- Cost-pin (`sonnet`, effort high): `reviewer-testing`/`reviewer-performance`/`reviewer-maintainability`, `translation-specialist`.
- Default (`inherit`, effort high): `implementer`, `qa-browser`, `ui`, `integration-specialist`.

Rules: lineage aliases or `inherit` only (no version-pinned ids); `xhigh`/`max` only on `opus` roles; `haiku` is not used. A pin sets the role default and survives a session `--model` downgrade (frontmatter outranks the session model); it is overridden only by `CLAUDE_CODE_SUBAGENT_MODEL`, which globally downgrades ALL pins (including security). Session-start emits an advisory when that env var is set.
```

- [ ] **Step 2: routing.md に haiku 文言が無いことを確認（変更不要の確認）**

Run: `grep -n haiku .claude/rules/routing.md || echo "no haiku in routing.md"`
Expected: `no haiku in routing.md`（設計 §7 の routing 整合は no-op）。

- [ ] **Step 3: 契約チェックとテストが緑**

Run: `python3 scripts/check_framework_contract.py && python3 -m unittest discover -s tests`
Expected: `PASS: aegis contract is aligned` ＋ 全テスト OK。

- [ ] **Step 4: コミット**

```bash
git add CLAUDE.md
git commit -m "docs: document agent model/effort policy in CLAUDE.md"
```

---

## Task 6: 全体検証（コミット前の最終確認）

**Files:** なし（検証のみ）

- [ ] **Step 1: 契約チェック・テスト・参照ドリフトを通す**

Run:
```bash
python3 scripts/check_framework_contract.py
python3 -m unittest discover -s tests
python3 scripts/check_reference_drift.py
```
Expected: 契約チェック PASS（exit 0）、unittest 全 OK、reference drift も従来どおり（新たな FAIL を増やさない）。

- [ ] **Step 2: git 状態確認**

Run: `git status --short && git log --oneline -4`
Expected: 作業ツリーがクリーン（未コミットの想定外変更なし）、直近に Task 3/4/5 の3コミット。

---

## Task 7: ship（push）前 smoke checklist（実機確認・手動ゲート）

**Files:** なし（設計 §11。docs だけで確定できない CC 実機挙動を push 前に確認）

> このタスクは**自動テスト化できない実機確認**を含む。各項目を最小再現で確かめ、結果を `docs/STATUS.md` か実装ログに記録する。失敗時は設計 §3 fallback 等の対応を実施してから push する。

- [ ] **Step 1: 固定がセッション降格に勝つか**
`--model haiku`（または安価モデル）でセッションを起こし、`security` か `reviewer` サブエージェントを1回起動して、実際に opus 系で走るかを確認（CC のサブエージェント実行ログ/モデル表示で判定）。Expected: pin が効き opus。

- [ ] **Step 2: env 一括上書きの挙動**
`CLAUDE_CODE_SUBAGENT_MODEL=haiku` を設定したセッションで同上を確認。Expected: 全固定が haiku に降格し、session-start advisory（Task 4）が表示される。

- [ ] **Step 3: effort `max`/`xhigh` の可用性**
`planner`（`effort: max`）/`reviewer`（`effort: xhigh`）を opus セッションで起動。Expected: エラーなく起動。**不可なら**設計 §3 fallback に従い `planner`/`security` を `xhigh`、必要なら `high` へ下げ、対応表（Task 1 の `MODEL_EFFORT_POLICY`）と各 frontmatter を同時に更新して再検証。

- [ ] **Step 4: 存在しない effort 指定時の挙動**
一時的に1つの agent に無効な effort（例 `effort: ultra`）を置いて起動し、CC が fail するか無視/クランプするかを観察（観察後すぐ戻す）。Expected: 挙動を記録。fail 型なら contract の値集合（現状の正規値のみ許可）で十分。

- [ ] **Step 5: `name` 無し agent の公式挙動**
現状 12 agent は `name:` 無しで filename fallback 動作中。CC 公式が name を必須とするか docs/実機で確認。Expected: 許容なら現状維持。**拒否される挙動なら**別パス（frontmatter hygiene）で全 agent に `name:` を付与（本ポリシー外・設計 §10-新A）。

- [ ] **Step 6: smoke 完了を記録して push 可否を判断**
全項目 OK なら push 可。いずれか NG なら fallback を実施し再検証してから push。

---

## 注記・スコープ外項目（実装者への申し送り）

- **haiku を勧める live doc が2箇所残る（設計スコープ外）:** `.claude/skills/subagent-dev/SKILL.md:129` と `templates/PLAN.template.md:57` がモデル選択ガイドとして `haiku` を挙げている。これは frontmatter の固定ではなくサブエージェント dispatch のガイドで、本ポリシー（frontmatter の haiku 全廃）の対象外。ユーザーの「haiku 不使用」意向と整合させるなら別途修正を推奨するが、**本計画では変更しない**（勝手なスコープ拡大を避ける）。実装後にユーザー判断を仰ぐこと。
- **`name` 欠落は別パスで対応（設計 §10-新A 確定）:** Task 7 Step 5 で公式挙動だけ確認。必須と判明した場合のみ別計画で全 agent に付与＋contract check に name 必須則を追加。
- **`version bump` は本ポリシーに含めない:** 哲学変更フェーズ完了後にまとめて判断（親設計 §9）。

---

## Self-Review（計画作成者による点検）

- **Spec coverage:** 設計 §3 確定ポリシー→Task 1–3、§4 enforcement→Task 1、§5 変更面→Task 1–5、§6 example→Task 3、§7 ドキュメント→Task 5、§10.1 advisory→Task 4、§10.2 qa-browser→注記（変更不要、qa-browser は inherit 据え置きで反映済み）、§11 smoke→Task 7、§9 完了条件→Task 6/7。全項目に対応タスクあり。
- **Placeholder scan:** TODO/TBD なし。全コード・コマンド・期待出力を明示。
- **Type consistency:** `MODEL_EFFORT_POLICY`（Task 1 定義）を Task 7 Step 3 の fallback で同名参照。`check_model_effort_policy`/`MODEL_POLICY_ROOTS`/`_frontmatter_section` は Task 1 内で定義・呼び出し一致。frontmatter 置換対象（`model:`/`effort:`）は実測した現値と一致。

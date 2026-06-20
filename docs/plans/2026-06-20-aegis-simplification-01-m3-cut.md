# M3 cut（skill_behavior_manifest 撤去）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 正典設計: `docs/plans/2026-06-20-aegis-simplification-design.md`（判定#3）。
> これは簡素化5ワークストリームの **第1（最小・独立・低リスク）**。後続（examples / docs / M4 / M2）は着手直前に各自の計画を作成する。

**Goal:** skill_behavior_manifest（layer-1 の substring トークン存在チェック）を撤去する。配布先で走らず作者の編集事故しか守らず、自認の限界（同コミットで素通り）があり、git diff＋編集時 AI レビューで代替可能なため。

**Architecture:** 3つの実体（`scripts/skill_behavior_manifest.py` 本体／`check_reference_drift.py` 内の import・関数・ALL_CHECKS 登録／専用テスト）を除去し、ALL_CHECKS を 15→14 に減らす。隠れ依存 `tests/test_arch_overview_currency.py` が ALL_CHECKS 件数と `docs/architecture-overview.md` の「N チェック」記述を機械突合しているので、arch-overview を 14 に同期する。`extensions/skill-pressure-drill/`（layer-2・opt-in addon・contract 非登録）は core 契約外なので **触らない**。

**Tech Stack:** Python 3 / pytest（テストは unittest.TestCase だが pytest で実行）/ git。

**前提:** カレントは framework root（`scripts/`・`tests/`・`docs/` が見える）。テストは `python3 -m pytest` で走る。

---

## File Structure

- Delete: `scripts/skill_behavior_manifest.py`（manifest 本体・SKILL_INVARIANTS 単一オーナー）
- Delete: `tests/test_skill_behavior_contract.py`（layer-1 専用 RED-GREEN 単体）
- Modify: `scripts/check_reference_drift.py`（import 31 / 関数 441-469 / ALL_CHECKS 672 を除去）
- Modify: `docs/architecture-overview.md:407`（「15 チェック」→「14 チェック」＋ skill_behavior 文言削除）

---

### Task 1: ベースライン確認（緑であることを記録）

**Files:** なし（読み取りのみ）

- [ ] **Step 1: 全テストが緑であることを確認**

Run: `python3 -m pytest -q`
Expected: 全 PASS（失敗 0）。総数をメモする（撤去後と比較するため）。

- [ ] **Step 2: drift チェックが現状 exit 0 で通ることを確認**

Run: `python3 scripts/check_reference_drift.py; echo "exit=$?"`
Expected: `exit=0`（現在 15 チェック）。

- [ ] **Step 3: 現行 ALL_CHECKS 件数が 15 であることを確認**

Run: `python3 -c "import re,pathlib; s=pathlib.Path('scripts/check_reference_drift.py').read_text(encoding='utf-8'); b=re.search(r'ALL_CHECKS = \[(.*?)\]', s, re.S); print(b.group(1).count('(\"'))"`
Expected: `15`

---

### Task 2: 原子的撤去（ref 除去 ＋ manifest ＋ 専用テストを1タスクで）

**Files:**
- Modify: `scripts/check_reference_drift.py`（import 31行 / 関数 441-469行 / ALL_CHECKS 登録 672行）
- Delete: `scripts/skill_behavior_manifest.py`
- Delete: `tests/test_skill_behavior_contract.py`

> **なぜ原子的か（grill 致命#1 対応）**: `tests/test_skill_behavior_contract.py` は除去対象シンボル（`SKILL_INVARIANTS` / `check_skill_behavior_contract`）をテストメソッド内で参照する。ref だけ先に消してこのテストを残すと、その間 full suite が AttributeError で RED になる（タスク境界の偽赤＝green-between-tasks 不変条件を破る）。ref 除去と2ファイル削除を**1タスク**で行い、直後の suite で**期待される RED を `test_arch_overview_currency` の件数1つ**に絞る。
> なお import を関数より先に外しても、manifest 本体は本タスク内で削除するので import crash の窓は生じない。

- [ ] **Step 1: import 行（31行目）を削除**

削除する行:
```python
from skill_behavior_manifest import SKILL_INVARIANTS  # noqa: E402  (sibling import)
```

- [ ] **Step 2: `check_skill_behavior_contract` 関数（441-469行）を丸ごと削除**

削除する定義（関数間の標準2空行を保つ）:
```python
def check_skill_behavior_contract(root: Path) -> tuple[list[str], list[str]]:
    """#15: 各判断系 skill が load-bearing 不変条件トークンを保持しているか
    （skill behavior contract）。manifest は root 専用・非ミラーのため、
    scripts/skill_behavior_manifest.py を持つ framework root でのみ発火し、
    installed project では inert。"""
    failures: list[str] = []
    warnings: list[str] = []

    if not (root / "scripts" / "skill_behavior_manifest.py").exists():
        return failures, warnings

    skills_dir = root / ".claude" / "skills"
    for skill_name, tokens in sorted(SKILL_INVARIANTS.items()):
        skill_md = skills_dir / skill_name / "SKILL.md"
        if not skill_md.is_file():
            failures.append(
                "skill behavior contract: manifest skill '%s' has no SKILL.md "
                "(expected .claude/skills/%s/SKILL.md)" % (skill_name, skill_name)
            )
            continue
        text = _read(skill_md)
        for token in tokens:
            if token not in text:
                failures.append(
                    "skill behavior contract: skill '%s' is missing load-bearing "
                    "invariant token %r" % (skill_name, token)
                )

    return failures, warnings
```

- [ ] **Step 3: ALL_CHECKS の登録行を削除**

削除する行（現 672行目）:
```python
    ("skill behavior contract", check_skill_behavior_contract),
```

- [ ] **Step 4: manifest 本体と専用テストを git から削除**

Run:
```bash
git rm scripts/skill_behavior_manifest.py tests/test_skill_behavior_contract.py
```
Expected: 2 files staged for deletion。

- [ ] **Step 5: drift チェックが exit 0・件数 14 を確認**

Run: `python3 scripts/check_reference_drift.py; echo "exit=$?"`
Expected: `exit=0`

Run: `python3 -c "import re,pathlib; s=pathlib.Path('scripts/check_reference_drift.py').read_text(encoding='utf-8'); b=re.search(r'ALL_CHECKS = \[(.*?)\]', s, re.S); print(b.group(1).count('(\"'))"`
Expected: `14`

- [ ] **Step 6: full suite を走らせ、期待される RED が currency 件数「ただ1つ」であることを確認（RED 証拠）**

Run: `python3 -m pytest -q`（pytest 不在環境なら `python3 -m unittest discover -s tests -q`）
Expected: **失敗は `tests/test_arch_overview_currency.py` の drift 件数テスト（"claims 15 ... ALL_CHECKS = 14"）のみ**。他は全 PASS。`test_skill_behavior_contract.py` の6ケースは削除済みで一覧から消えている（赤ではない）。総数は Task 1 Step 1 から「6ケース減」。この単一 RED が ALL_CHECKS↔arch-overview の機械突合（隠れ依存）が効いている証拠。

---

### Task 3: arch-overview を同期して全緑に（GREEN）

**Files:**
- Modify: `docs/architecture-overview.md:407`
- Test: `tests/test_arch_overview_currency.py`（既存・編集しない）

- [ ] **Step 1: arch-overview 407行を 14 に更新し skill_behavior 文言を削除**

変更前（407行）:
```
| `check_reference_drift.py` | 参照名ドリフト検出（15 チェック。本体↔example の mirror-identity を byte 比較。platform_manifest による event/tool ドリフトと検証日 staleness、skill_behavior_manifest による skill behavior contract を含む） |
```
変更後:
```
| `check_reference_drift.py` | 参照名ドリフト検出（14 チェック。本体↔example の mirror-identity を byte 比較。platform_manifest による event/tool ドリフトと検証日 staleness を含む） |
```
（grill 実証: arch-overview 内の skill_behavior/層1/層2 言及はこの407行のみ。他に残骸なし。）

- [ ] **Step 2: full suite が全緑になることを確認（GREEN）**

Run: `python3 -m pytest -q`（または `python3 -m unittest discover -s tests -q`）
Expected: 全 PASS（失敗0）。Task 1 Step 1 の総数から `test_skill_behavior_contract.py` の6ケース分だけ減っている。

---

### Task 4: dangling 参照ゼロ検証 ＋ STATUS/gate ＋ コミット

**Files:** なし（検証＋コミット＋状態更新）

- [ ] **Step 1: コード（py/sh/json）に dangling 参照が無いことを確認**

Run:
```bash
grep -rn "skill_behavior\|SKILL_INVARIANTS\|check_skill_behavior_contract" --include='*.py' --include='*.sh' --include='*.json' . | grep -v '.git/'
```
Expected: **出力なし（0件）**。（grill 実証済み: `extensions/` 配下にも該当文字列の py/sh/json は無い。）docs 内の歴史記述（STATUS.md の iteration 30 メモ等）はワークストリーム5（docs 整理）で扱うため対象外。

- [ ] **Step 2: 最終確認（drift exit 0 ＋ full suite 全緑）**

Run: `python3 scripts/check_reference_drift.py; echo "exit=$?"`
Expected: `exit=0`

Run: `python3 -m pytest -q`
Expected: 全 PASS。

- [ ] **Step 3: ステージ内容を確認してコミット**

Run: `git status --short`
Expected: `D scripts/skill_behavior_manifest.py`・`D tests/test_skill_behavior_contract.py`（Task 2 の git rm 済み）＋ `M scripts/check_reference_drift.py`・`M docs/architecture-overview.md`。

Run:
```bash
git add scripts/check_reference_drift.py docs/architecture-overview.md
git commit -m "$(cat <<'EOF'
refactor(simplification): remove skill_behavior_manifest (M3 cut)

配布先で走らず作者の編集事故のみを守り、同コミットで素通りする限界が
あるため撤去。skill 健全性は git diff＋編集時 AI レビューへ委譲。
ALL_CHECKS 15→14、arch-overview を同期。設計: docs/plans/2026-06-20-aegis-simplification-design.md #3

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: コミット成立を確認**

Run: `git status --short && git log --oneline -1`
Expected: 作業ツリーがクリーン（簡素化対象に関して）、最新コミットが上記メッセージ。

- [ ] **Step 5: STATUS / Aegis ゲート（フレームワーク手順）**

`docs/STATUS.md` の phase / current_refs / failure_tracking を更新し、framework の `review` ゲート（S サイズ最小）へ回す。**arch-overview §15 ファイル数サマリ（scripts は実13・記載は stale）はワークストリーム5（docs 整理）で拾う**（既に untested/stale のため本タスクでは不変更）。

---

## Self-Review

- **Spec coverage:** 設計 #3（skill_behavior_manifest = cut／AI委譲）を完全実装。3実体（本体・drift 内 import/関数/登録・専用テスト）すべて除去し、隠れ依存（arch-overview 件数）を同期。
- **Placeholder scan:** 各 step に実コマンド／実コード／期待値あり。TBD なし。
- **green-between-tasks（grill 致命#1 対応）:** ref 除去と2ファイル削除を Task 2 で原子化。各タスク境界の状態を確定（Task2 後＝currency 1件のみ RED／Task3 後＝全緑）。偽赤の窓を排除。
- **隠れ依存の実証:** ALL_CHECKS 件数に結合するテストは `test_arch_overview_currency` *だけ*（`test_platform_manifest_consumers.py` は個別 drift 関数呼びで件数非依存／scripts ファイル数を pin するテストは無し）を grep で確認済み＝前提が正しい。`-k`/class 名非依存は通常実行（full suite）に統合したため不要化。
- **スコープ外の明示:** extensions/ layer-2、docs 歴史記述、examples ミラー（skill_behavior は非ミラー）、arch-overview §15 ファイル数サマリ（ワークストリーム5へ）は本計画で触らない。

## 注記（Aegis ゲート）

本作業は Aegis Dev-mode の framework 変更（S サイズ・1ファイル中心の独立変更）。Task 4 Step 5 でコミット後に STATUS 更新＋`review` ゲート（最小）へ。`writing-plans` の TDD 計画はコード変更の手順であり、ゲート承認・STATUS 更新はフレームワーク手順に従う。

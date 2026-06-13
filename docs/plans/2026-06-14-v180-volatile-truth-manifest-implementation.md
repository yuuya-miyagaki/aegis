# volatile-truth マニフェスト Implementation Plan (v1.8.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** プラットフォーム結合値（model/effort・hook event 名・tool 名・schema 検証日）を `scripts/platform_manifest.py` に隔離し、既存 checker が import で消費する単一ソースを作る。

**Architecture:** 新規 python モジュール `scripts/platform_manifest.py`（root 専用・非ミラー）が原子（frozenset）＋検証日（dict）＋ pure 関数 `stale_keys()` を export。`check_framework_contract.py` が model 原子を import して frontmatter とポリシー表を照合（FAIL）、`check_reference_drift.py` が event/tool 原子と `stale_keys()` を import して template の event drift（FAIL）・tool レジストリ（WARN）・staleness（WARN）を検査。emit.sh は不可侵（schema は検証日のみ記録）。

**Tech Stack:** Python 3（標準ライブラリのみ：`datetime`, `json`, `re`, `pathlib`）、pytest。既存 import 規約は `from <module> import ...`（scripts/ が sys.path[0]）。

**設計書:** `docs/plans/2026-06-14-volatile-truth-manifest-design.md`

---

## File Structure

| ファイル | 役割 | 操作 |
|---|---|---|
| `scripts/platform_manifest.py` | プラットフォーム結合原子＋検証日＋ `stale_keys()` の単一ソース | Create |
| `tests/test_platform_manifest.py` | マニフェスト不変条件＋ `stale_keys()` 純関数テスト | Create |
| `scripts/check_framework_contract.py` | model/effort をマニフェスト原子で照合（リテラル置換＋ポリシー表 self-consistency 追加） | Modify（17, 12 付近 import, 340, 374-379, 979 付近） |
| `scripts/check_reference_drift.py` | event drift / tool レジストリ / staleness の新規 check | Modify（16 付近 import, 559-572 ALL_CHECKS, 新規 check_fn） |
| `tests/test_check_status.py` 等 既存 contract/drift テスト | 新挙動の回帰テスト追加 | Modify or 新規 `tests/test_platform_manifest_consumers.py` |
| `CLAUDE.md` | Model Policy の値出典をマニフェストに一本化と明記 | Modify |
| 版数 stamp ×4 | `check_framework_contract.py:17` / `templates/STATUS.template.md:3` / `docs/STATUS.md:3` / `examples/minimal-project/docs/STATUS.md:3` | Modify |

非ミラー確認: `check_framework_contract.py` / `check_reference_drift.py` は `MIRROR_DIRS`/`MIRROR_FILES` に含まれない＝example scaffold に存在しない。よって両者が import する `platform_manifest.py` も root 専用で、`MIRROR_FILES` 追加は不要。

---

## Task 1: platform_manifest.py（単一ソース）＋不変条件テスト

**Files:**
- Create: `scripts/platform_manifest.py`
- Test: `tests/test_platform_manifest.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_platform_manifest.py`:

```python
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import platform_manifest as pm


def test_required_constants_are_frozensets():
    for name in (
        "ALLOWED_MODELS", "FORBIDDEN_MODELS", "EFFORT_LEVELS",
        "OPUS_ONLY_EFFORTS", "KNOWN_HOOK_EVENTS",
        "TOOL_MATCHING_EVENTS", "KNOWN_TOOL_NAMES",
    ):
        assert isinstance(getattr(pm, name), frozenset), name


def test_allowed_and_forbidden_models_are_disjoint():
    assert pm.ALLOWED_MODELS & pm.FORBIDDEN_MODELS == frozenset()


def test_opus_only_efforts_subset_of_effort_levels():
    assert pm.OPUS_ONLY_EFFORTS <= pm.EFFORT_LEVELS


def test_tool_matching_events_subset_of_known_events():
    assert pm.TOOL_MATCHING_EVENTS <= pm.KNOWN_HOOK_EVENTS


def test_verification_dates_parse_as_iso():
    assert set(pm.PLATFORM_VERIFIED) == {
        "models", "hook_events", "tool_names", "hook_output_schema",
    }
    for iso in pm.PLATFORM_VERIFIED.values():
        date.fromisoformat(iso)  # raises if malformed


def test_stale_keys_flags_old_dates_only():
    # 全キーが today なら stale 無し
    today = date.fromisoformat(pm.PLATFORM_VERIFIED["models"])
    assert pm.stale_keys(today=today) == []
    # 検証日 + STALENESS_DAYS + 1 日後は全キー stale
    from datetime import timedelta
    base = max(date.fromisoformat(v) for v in pm.PLATFORM_VERIFIED.values())
    future = base + timedelta(days=pm.STALENESS_DAYS + 1)
    assert sorted(pm.stale_keys(today=future)) == sorted(pm.PLATFORM_VERIFIED)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_platform_manifest.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'platform_manifest'`）

- [ ] **Step 3: 最小実装を書く**

`scripts/platform_manifest.py`:

```python
#!/usr/bin/env python3
"""Single source of truth for platform-coupled (volatile) values.

Isolates values that shift when the Claude Code platform or the Claude model
lineup evolves, so a platform change is a one-place edit. Consumed by import:
  - check_framework_contract.py -> model/effort validity (FAIL)
  - check_reference_drift.py     -> hook-event drift (FAIL) / tool registry (WARN) / staleness (WARN)

emit.sh is intentionally NOT a consumer: the hook output schema stays defined in
pure-bash there (deny path must have zero external deps). This module only records
WHEN that schema was last verified against the platform contract.

The harness cannot introspect the live platform, so reality drift is tracked by
human-maintained verification dates (PLATFORM_VERIFIED), surfaced as a
non-blocking staleness advisory. This is what keeps the manifest from becoming a
silent declarative mirror: every value either has a real importing consumer or a
dated human re-verification trigger.
"""

from __future__ import annotations

from datetime import date

# --- Models / effort: validated against agent frontmatter + MODEL_EFFORT_POLICY
#     by check_framework_contract.py. ---
ALLOWED_MODELS = frozenset({"opus", "sonnet", "inherit"})  # lineage alias + inherit
FORBIDDEN_MODELS = frozenset({"haiku"})                    # explicitly not used
EFFORT_LEVELS = frozenset({"high", "xhigh", "max"})
OPUS_ONLY_EFFORTS = frozenset({"xhigh", "max"})

# --- Hook lifecycle events: template events must be a subset of this. ---
KNOWN_HOOK_EVENTS = frozenset({
    "SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "PreCompact", "Stop", "SubagentStop", "UserPromptSubmit", "Notification",
    "TaskCreated", "TaskCompleted",
})

# Events whose `matcher` field holds TOOL names. Others (e.g. SessionStart holds
# session sources like startup|resume|clear|compact) must NOT be checked here.
TOOL_MATCHING_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure"})

# --- Tool / MCP-tool tokens referenced by template matchers today. Extend ONLY
#     when a new tool-matching matcher is added (best-effort registry; do not pad
#     with tools no matcher references, or the registry silently rots). ---
KNOWN_TOOL_NAMES = frozenset({
    "Bash", "Edit", "Write", "NotebookEdit",
    "Skill", "CronCreate",
    "mcp__claude_ai_Vercel__deploy_to_vercel",
})

# --- Human verification dates (YYYY-MM-DD): last time each class was checked
#     against the live Claude Code platform. Bump on re-verification. ---
PLATFORM_VERIFIED = {
    "models": "2026-06-14",
    "hook_events": "2026-06-14",
    "tool_names": "2026-06-14",
    "hook_output_schema": "2026-06-14",
}
STALENESS_DAYS = 180


def stale_keys(today: date | None = None) -> list[str]:
    """Verification keys whose last-verified date is older than STALENESS_DAYS.
    Pure function; `today` is injectable for tests."""
    if today is None:
        today = date.today()
    stale: list[str] = []
    for key, iso in PLATFORM_VERIFIED.items():
        if (today - date.fromisoformat(iso)).days > STALENESS_DAYS:
            stale.append(key)
    return sorted(stale)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_platform_manifest.py -q`
Expected: PASS（6 passed）

- [ ] **Step 5: コミット**

```bash
git add scripts/platform_manifest.py tests/test_platform_manifest.py
git commit -m "feat(manifest): add platform_manifest single source for volatile values (v1.8.0)"
```

---

## Task 2: check_framework_contract.py を manifest 消費に切替

**Files:**
- Modify: `scripts/check_framework_contract.py`（import 追加、`_OPUS_ONLY_EFFORTS` 削除、374-379 のリテラル置換、新規 `check_model_policy_manifest_consistency()`、979 付近で登録）
- Test: `tests/test_platform_manifest_consumers.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_platform_manifest_consumers.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_framework_contract as cfc


def test_policy_consistency_passes_on_real_policy():
    # 実ポリシー表はマニフェストに収まっている＝失敗ゼロ
    assert cfc.check_model_policy_manifest_consistency() == []


def test_policy_consistency_flags_forbidden_model(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"planner.md": ("haiku", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("haiku" in f and "forbidden" in f for f in failures)


def test_policy_consistency_flags_unknown_model(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"planner.md": ("claude-opus-4-8", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("not in ALLOWED_MODELS" in f for f in failures)


def test_policy_consistency_flags_unknown_effort(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"qa.md": ("opus", "ultra")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("not in EFFORT_LEVELS" in f for f in failures)


def test_policy_consistency_flags_opus_only_effort_on_nonopus(monkeypatch):
    bogus = dict(cfc.MODEL_EFFORT_POLICY, **{"reviewer-testing.md": ("sonnet", "max")})
    monkeypatch.setattr(cfc, "MODEL_EFFORT_POLICY", bogus)
    failures = cfc.check_model_policy_manifest_consistency()
    assert any("only allowed on opus" in f for f in failures)


def test_contract_imports_manifest_atoms():
    # マニフェスト原子を import 経由で使用していること（リテラル再定義の防止）
    from platform_manifest import OPUS_ONLY_EFFORTS
    assert cfc.OPUS_ONLY_EFFORTS is OPUS_ONLY_EFFORTS
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_platform_manifest_consumers.py -q`
Expected: FAIL（`AttributeError: module 'check_framework_contract' has no attribute 'check_model_policy_manifest_consistency'` ／ `OPUS_ONLY_EFFORTS` 不在）

- [ ] **Step 3: import を追加**

`scripts/check_framework_contract.py` の `from check_status import validate_status_file`（12 行目）の直後に追加:

```python
from platform_manifest import (
    ALLOWED_MODELS,
    EFFORT_LEVELS,
    FORBIDDEN_MODELS,
    OPUS_ONLY_EFFORTS,
)
```

- [ ] **Step 4: ローカルリテラルを置換**

340 行目を削除:

```python
_OPUS_ONLY_EFFORTS = {"xhigh", "max"}
```

（`_VERSION_ID_RE = re.compile(r"claude-[\w-]*\d")` はメカニズムとして残す。）

`check_model_effort_policy` 内 374-379 行を以下に置換:

```python
            if model in FORBIDDEN_MODELS:
                failures.append(f"model-policy: {rel} uses {model} (forbidden; floor is sonnet)")
            if model and _VERSION_ID_RE.search(model):
                failures.append(f"model-policy: {rel} uses version-pinned id '{model}' (alias or inherit only)")
            if effort and effort not in EFFORT_LEVELS:
                failures.append(f"model-policy: {rel} effort={effort} not in {sorted(EFFORT_LEVELS)}")
            if effort in OPUS_ONLY_EFFORTS and model != "opus":
                failures.append(f"model-policy: {rel} effort={effort} only allowed on opus-pinned roles")
```

- [ ] **Step 5: ポリシー表 self-consistency check を追加**

`check_agent_names`（388 行目）の直前に新規関数を追加:

```python
def check_model_policy_manifest_consistency() -> list:
    """MODEL_EFFORT_POLICY（aegis 設計）の各値が platform_manifest の許容集合に
    収まることを検証。新モデル系統の追加/廃止時の単一更新点を担保する。"""
    failures = []
    for name, (model, effort) in MODEL_EFFORT_POLICY.items():
        if model in FORBIDDEN_MODELS:
            failures.append(f"model-manifest: policy[{name}] model={model} is forbidden")
        elif model not in ALLOWED_MODELS:
            failures.append(
                f"model-manifest: policy[{name}] model={model} not in ALLOWED_MODELS {sorted(ALLOWED_MODELS)}"
            )
        if effort not in EFFORT_LEVELS:
            failures.append(
                f"model-manifest: policy[{name}] effort={effort} not in EFFORT_LEVELS {sorted(EFFORT_LEVELS)}"
            )
        if effort in OPUS_ONLY_EFFORTS and model != "opus":
            failures.append(f"model-manifest: policy[{name}] effort={effort} only allowed on opus")
    return failures
```

- [ ] **Step 6: main() で登録**

979 行目 `failures.extend(check_model_effort_policy(MODEL_POLICY_ROOTS))` の直前に追加:

```python
    failures.extend(check_model_policy_manifest_consistency())
```

- [ ] **Step 7: テストが通ることを確認**

Run: `python3 -m pytest tests/test_platform_manifest_consumers.py -q`
Expected: PASS（6 passed）

- [ ] **Step 8: contract checker が緑であることを確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 9: コミット**

```bash
git add scripts/check_framework_contract.py tests/test_platform_manifest_consumers.py
git commit -m "feat(manifest): source model/effort policy from platform_manifest (v1.8.0)"
```

---

## Task 3: check_reference_drift.py に event/tool/staleness check を追加

**Files:**
- Modify: `scripts/check_reference_drift.py`（16 付近 import＋自己 bootstrap、新規 `check_platform_manifest()` ＋ `check_platform_staleness()`、559-572 ALL_CHECKS に 2 エントリ登録）
- Test: `tests/test_platform_manifest_consumers.py`（追記）

- [ ] **Step 1: 失敗するテストを書く**

まず `tests/test_platform_manifest_consumers.py` の**先頭 import ブロック**（Task 2 の import 群と同じ位置）に追記（mid-file import を避けるため必ず先頭へ hoist）:

```python
import json
import check_reference_drift as crd
```

次に同ファイル末尾へテスト関数を追記。`check_platform_manifest` は template 専用（決定論）、`check_platform_staleness` は検証日専用（時間依存）に分離する設計なので、template 系テストは前者だけを対象にする（staleness を巻き込まない＝壁時計非依存）:

```python
def _write_template(tmp_path, hooks: dict) -> Path:
    root = tmp_path
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "hooks.template.json").write_text(
        json.dumps({"hooks": hooks}), encoding="utf-8"
    )
    return root


def test_drift_clean_template_passes(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUse": [{"matcher": "Edit|Write|NotebookEdit", "hooks": []}],
        "PostToolUse": [{"matcher": "Bash", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert warnings == []  # staleness は別関数なので壁時計に依存しない


def test_drift_unknown_event_fails(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUseX": [{"matcher": "Bash", "hooks": []}],
    })
    failures, _ = crd.check_platform_manifest(root)
    assert any("PreToolUseX" in f and "KNOWN_HOOK_EVENTS" in f for f in failures)


def test_drift_unknown_tool_warns(tmp_path):
    root = _write_template(tmp_path, {
        "PreToolUse": [{"matcher": "Bash|FrobnicateTool", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert any("FrobnicateTool" in w for w in warnings)


def test_drift_ignores_session_source_matchers(tmp_path):
    # SessionStart の matcher は tool ではない＝WARN を出さない
    root = _write_template(tmp_path, {
        "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": []}],
    })
    failures, warnings = crd.check_platform_manifest(root)
    assert failures == []
    assert warnings == []


def test_staleness_skipped_when_not_framework_root(tmp_path):
    # platform_manifest.py を含まない root（例: install 先 scaffold）では staleness を
    # 発火させない＝二重発火を防ぐ。
    failures, warnings = crd.check_platform_staleness(tmp_path)
    assert failures == []
    assert warnings == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_platform_manifest_consumers.py -q -k "drift or staleness"`
Expected: FAIL（`module 'check_reference_drift' has no attribute 'check_platform_manifest'`）

- [ ] **Step 3: import を追加（自己 bootstrap 付き — grill 致命#1）**

`scripts/check_reference_drift.py` の `from pathlib import Path`（16 行目）の直後に追加。**重要**: `test_skill_reachability.py` は `importlib.spec_from_file_location` で本モジュールをロードするが scripts/ を sys.path に入れない。素の top-level import を足すと同テストが単独実行で collection error（現状 `pytest tests/test_skill_reachability.py` は 8 passed＝回帰）。よって import 前に自モジュールのディレクトリを sys.path へ自己挿入し、どのローダ経由でも解決できるようにする（再発クラスごと封鎖）:

```python
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from platform_manifest import (
    KNOWN_HOOK_EVENTS,
    KNOWN_TOOL_NAMES,
    TOOL_MATCHING_EVENTS,
    stale_keys,
)
```

確認: 変更後に `python3 -m pytest tests/test_skill_reachability.py -q` が単独で緑のままであること。

- [ ] **Step 4: check 関数を実装（template 検査と staleness を分離 — grill 致命#2）**

`check_mirror_identity`（516 行目）の直前に**2 つの**新規関数を追加。template 検査（決定論）と検証日 staleness（時間依存）を別関数に分ける。これにより clean-template テストが壁時計に依存せず（staleness 窓超過後も恒久緑）、staleness は framework root のみで発火（install 先 scaffold での二重発火を防止）:

```python
def check_platform_manifest(root: Path) -> tuple[list[str], list[str]]:
    """volatile-truth manifest（決定論部）: template の hook event は既知 event
    集合の部分でなければならない（FAIL）。tool-matcher のトークンは既知 tool
    レジストリに収まるべき（WARN・regex 曖昧性ゆえ best-effort）。"""
    failures: list[str] = []
    warnings: list[str] = []

    template = root / "templates" / "hooks.template.json"
    if not template.exists():
        return failures, warnings
    try:
        data = json.loads(_read(template))
    except (json.JSONDecodeError, OSError):
        warnings.append(f"could not parse {template.name}")
        return failures, warnings

    for event, matchers in data.get("hooks", {}).items():
        if event not in KNOWN_HOOK_EVENTS:
            failures.append(
                f"platform-manifest: hooks.template.json event '{event}' "
                f"not in KNOWN_HOOK_EVENTS (renamed/typo?)"
            )
        if event not in TOOL_MATCHING_EVENTS or not isinstance(matchers, list):
            continue
        for matcher in matchers:
            for token in matcher.get("matcher", "").split("|"):
                token = token.strip()
                if token and token not in KNOWN_TOOL_NAMES:
                    warnings.append(
                        f"platform-manifest: matcher token '{token}' "
                        f"(event {event}) not in KNOWN_TOOL_NAMES registry"
                    )

    return failures, warnings


def check_platform_staleness(root: Path) -> tuple[list[str], list[str]]:
    """volatile-truth manifest（時間依存部）: 検証日が staleness 窓を超えたら
    再確認を促す advisory（WARN・非ブロック）。manifest を持つ framework root
    のみで発火させ、install 先 scaffold での二重発火を避ける。"""
    warnings: list[str] = []
    if not (root / "scripts" / "platform_manifest.py").exists():
        return [], warnings
    for key in stale_keys():
        warnings.append(
            f"platform-manifest: '{key}' verification date exceeds the staleness "
            f"window; re-verify against the live platform and bump PLATFORM_VERIFIED"
        )
    return [], warnings
```

- [ ] **Step 5: ALL_CHECKS に登録（両方）**

571 行目 `("mirror identity (root ↔ example)", check_mirror_identity),` の直後（リスト末尾）に**2 行**追加:

```python
    ("platform manifest (events/tools)", check_platform_manifest),
    ("platform verification staleness", check_platform_staleness),
```

- [ ] **Step 6: テストが通ることを確認**

Run: `python3 -m pytest tests/test_platform_manifest_consumers.py -q`
Expected: PASS（Task 2 の 6 ＋ Task 3 の 5 ＝ 11 passed）

- [ ] **Step 7: drift checker が緑であること＋既存 importlib テスト非回帰を確認**

Run:
```bash
python3 scripts/check_reference_drift.py
python3 -m pytest tests/test_skill_reachability.py -q
```
Expected: drift は `PASS: no reference drift detected`（実 template の event/tool は既知集合内・検証日は当日なので staleness 0 件）。`test_skill_reachability.py` は単独で緑（自己 bootstrap が効いている＝grill 致命#1 解消の実証）。

- [ ] **Step 8: コミット**

```bash
git add scripts/check_reference_drift.py tests/test_platform_manifest_consumers.py
git commit -m "feat(manifest): add event-drift/tool-registry/staleness checks to drift lint (v1.8.0)"
```

---

## Task 4: CLAUDE.md に値出典の一本化を明記

**Files:**
- Modify: `CLAUDE.md`（Model Policy セクション）

- [ ] **Step 1: Model Policy に出典注記を追加**

`CLAUDE.md` の `## Model Policy` セクションの `Rules:` 行末（`...Session-start emits an advisory when that env var is set.` の直後）に 1 文追加:

```markdown

Valid model aliases, the forbidden set (`haiku`), effort levels, and the opus-only effort rule are defined once in `scripts/platform_manifest.py` (the volatile-truth manifest) and enforced by `check_framework_contract.py`. Update model lineage there, not inline.
```

- [ ] **Step 2: drift / 語数制約が緑であることを確認**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_reference_drift.py`
Expected: 両方 PASS（CLAUDE.md は `MAX_CLAUDE_WORDS=650`・`REQUIRED_CLAUDE_HEADINGS` 制約内。超過する場合は注記を 1 文に圧縮）

- [ ] **Step 3: コミット**

```bash
git add CLAUDE.md
git commit -m "docs(manifest): point Model Policy at platform_manifest as value source (v1.8.0)"
```

---

## Task 5: 版数 1.8.0 統一・全回帰・STATUS 更新

**Files:**
- Modify: `scripts/check_framework_contract.py:17` / `templates/STATUS.template.md:3` / `docs/STATUS.md:3` / `examples/minimal-project/docs/STATUS.md:3`
- Modify: `docs/STATUS.md`（next_action / session_history / current_refs.plan・spec）

- [ ] **Step 1: 版数 4 箇所を 1.8.0 に更新**

- `scripts/check_framework_contract.py:17`: `FRAMEWORK_VERSION = "1.8.0"`
- `templates/STATUS.template.md:3`: `framework_version: "1.8.0"`
- `docs/STATUS.md:3`: `framework_version: "1.8.0"`
- `examples/minimal-project/docs/STATUS.md:3`: `framework_version: "1.8.0"`

- [ ] **Step 2: 全テストスイートを実行（回帰）**

Run: `python3 -m pytest tests/ -q`
Expected: 既存 734 ＋ 新規（manifest 6 ＋ consumers 10）＝ 750 passed（件数は実測で確認）。0 failed。

- [ ] **Step 3: contract（全 profile）/ drift / scaffold smoke を実行**

Run:
```bash
python3 scripts/check_framework_contract.py
python3 scripts/check_reference_drift.py
python3 -m pytest tests/poc -q
```
Expected: contract `PASS`、drift `PASS`、PoC 全 PASS。

- [ ] **Step 4: ミラー非対称が無いことを確認**

Run: `make example && git diff --stat`
Expected: `examples/minimal-project/docs/STATUS.md` の版数以外に差分が出ない（`platform_manifest.py` は非ミラーなので example に現れない）。版数差分は Step 1 で手当て済み。

- [ ] **Step 5: STATUS.md を更新**

`docs/STATUS.md` の frontmatter:
- `framework_version: "1.8.0"`（Step 1 済）
- `iteration: 28`
- `last_updated`: 実行時刻（ISO8601）
- `current_refs.plan`: `docs/plans/2026-06-14-v180-volatile-truth-manifest-implementation.md`
- `current_refs.spec`: `docs/plans/2026-06-14-volatile-truth-manifest-design.md`
- `current_refs.requirements`: `docs/full-review-2026-06-13-context-futureproof.md`（据置）
- `next_action`: v1.8.0 実装完了の要約（manifest 新設・consumer 2 本・version 1.8.0・テスト件数・残 backlog=P3 docs archive）
- `session_history` に 2026-06-14 エントリ追記

- [ ] **Step 6: 最終コミット**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md docs/STATUS.md examples/minimal-project/docs/STATUS.md
git commit -m "chore: bump framework_version to 1.8.0 (volatile-truth manifest) + STATUS"
```

---

## Self-Review

**1. Spec coverage（設計書 §1-8 との照合）:**
- §2 アーキ（manifest＋2 consumer＋emit.sh 不可侵）→ Task 1/2/3、emit.sh は一切触らない ✓
- §3 コンポーネント（原子＋検証日）→ Task 1 ✓
- §4 データフロー（model 照合 / event drift / tool WARN / staleness）→ Task 2/3 ✓
- §5 エラー方針（model FAIL / event FAIL / tool WARN / staleness WARN / import FAIL-closed）→ Task 2/3。import 失敗は top-level import が ImportError で停止＝checker 全体が落ちる＝fail-closed ✓
- §6 テスト → Task 1/2/3 のテスト＋ Task 5 回帰 ✓
- §7 docs・版 → Task 4/5 ✓
- §8 スコープガード（emit.sh 不可侵 / schema 日付のみ / tool registry+WARN / JSON 化しない / 新 CI エントリ無し / 新ミラー面無し）→ 全 Task で遵守。新エントリは既存 ALL_CHECKS / main() への追加のみ ✓

**2. Placeholder scan:** TBD/TODO/「適切に」等なし。全コードブロックは実コード。✓

**3. Type consistency:**
- `stale_keys(today=None) -> list[str]`：Task 1 定義、`check_platform_staleness` で引数なし呼び出し、テストで `today=` 注入 — 一致 ✓
- `check_model_policy_manifest_consistency() -> list`：Task 2 定義・登録・テスト — 名前一致 ✓
- `check_platform_manifest(root) / check_platform_staleness(root) -> tuple[list, list]`：Task 3 定義・ALL_CHECKS に 2 エントリ登録・テスト — `(failures, warnings)` 形が ALL_CHECKS 規約（他 check と同型）と一致 ✓
- import される原子名（ALLOWED_MODELS / FORBIDDEN_MODELS / EFFORT_LEVELS / OPUS_ONLY_EFFORTS / KNOWN_HOOK_EVENTS / KNOWN_TOOL_NAMES / TOOL_MATCHING_EVENTS / stale_keys）は Task 1 の定義と全 consumer で綴り一致 ✓

**grill-plan 反映済み（2026-06-14）:**
- 致命#1: check_reference_drift.py に自己 bootstrap（`sys.path.insert(自モジュール dir)`）を追加。importlib ローダ（test_skill_reachability）経由の単独実行 collection error を封鎖。Task 3 Step 3 ＋ Step 7 で実証。
- 致命#2: staleness を `check_platform_staleness` に関数分離（時間依存）。template 検査 `check_platform_manifest` は決定論＝clean-template テストが壁時計非依存に。Task 3 Step 1/4/5 反映。
- 要検討#1: staleness を framework root（`scripts/platform_manifest.py` 存在）のみで発火させ二重発火を防止。`test_staleness_skipped_when_not_framework_root` でガード。
- YAGNI: KNOWN_TOOL_NAMES を template 参照トークンのみに trim（Read/Task 除去）。
- import hoist: Task 3 テストの `import json` / `import check_reference_drift` を先頭へ。

**実装中に確認する残点:**
- STALENESS_DAYS=180 の妥当性（モデル世代更新頻度）— 実装中に固定でよい、後から定数調整可。
- FORBIDDEN_MODELS 置換後のメッセージ文言を固定 assert する既存テストが無いか（Task 5 Step 2 の full suite が最終担保）。
- CLAUDE.md 注記が `MAX_CLAUDE_WORDS=650` を超えないか（Task 4 Step 2 で実証）。

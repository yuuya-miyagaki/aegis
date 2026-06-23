# iter41 Batch 1 (配布正常化＋整合性 fail-closed) Implementation Plan

> **For agentic workers:** TDD task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 配布形態（standard profile・reinstall 型 upgrade）で core 保証を機能させ、整合性 hook の fail-open を fail-closed 化する。

**Architecture:** 6 独立 finding（D1-D4 配布 / I1-I2 整合性）。共有変更は `hooks/lib/safety.sh`（I1）と `scripts/check_framework_contract.py`（D2c）。check-control-plane 本体は不変。**framework_version は 1.14.0 据置**（iter38-40 同様・リリース/tag 無し＝grill 致命較正）。

**参照設計:** `docs/specs/2026-06-24-iter41-batch1-distribution-integrity-design.md`

**Tech Stack:** bash 3.2-safe / python3 stdlib / pytest

**作業前提:** task_type=framework（moat 解錠状態）で control file 編集可。

**⚠ commit 順序（grill 致命 1）:** judge card の `resolve_diff_ref` は working tree vs HEAD を diff する。**task ごとに commit してはならない**（commit すると gate 時に差分が消え judge が変更をレビュー不能）。D1-I2 は実装+test のみ。Task V で grill-code → full suite → contract → standard 配布検証 → gate（review→qa→security→deploy→ship）を **working tree（未 commit）** で実行し、**最後に 1 commit + push**（iter40 と同じ運用）。

---

## Task D1: standard profile に judge ツールチェーンを同梱

**Files:**
- Modify: `templates/profiles/standard.json`（`required` ＋ `recommended`）
- Modify: `README.md`（standard の件数行）
- Test: `tests/test_profile_judge_toolchain.py`（新規）

**根拠:** `scripts/check_status.py:944-947` builder 不在→return 1（fail-closed）＝standard で review/qa/security/deploy 承認不能。`scripts/build-judge-card.py:33` が `run-test-strength-drill.py` を importlib で**必須**ロード（fallback 無し）。
**配置（grill 致命 2）:** gate-blocking な 2 本は `required`（contract が強制）。card build を阻害しない 2 本は `recommended`。

- [ ] **Step 1: failing test**

```python
# tests/test_profile_judge_toolchain.py
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _profile(name):
    return json.loads((ROOT / "templates" / "profiles" / f"{name}.json").read_text())

def test_standard_requires_gate_blocking_judge_scripts():
    """build-judge-card / run-test-strength-drill が無いと run_judge_card が
    return 1 で review/qa/security/deploy を brick する＝required で契約強制。"""
    req = set(_profile("standard").get("required", []))
    for needed in ("scripts/build-judge-card.py", "scripts/run-test-strength-drill.py"):
        assert needed in req, f"standard required missing gate-critical: {needed}"

def test_standard_recommends_judge_support():
    files = set(_profile("standard").get("required", [])) | set(_profile("standard").get("recommended", []))
    for needed in ("scripts/record-test-result.py", "hooks/lib/fingerprint.sh"):
        assert needed in files, f"standard profile missing judge support: {needed}"
```

- [ ] **Step 2: run → FAIL**: `python3 -m pytest tests/test_profile_judge_toolchain.py -q`.

- [ ] **Step 3a: implement** — `standard.json` の `required` 末尾（`hooks/lib/phase-skills.sh` の後）に追加:

```json
    "hooks/lib/phase-skills.sh",
    "scripts/build-judge-card.py",
    "scripts/run-test-strength-drill.py"
```

`recommended` 末尾（`.claude/skills/subagent-dev/SKILL.md` の後）に追加:

```json
    ".claude/skills/subagent-dev/SKILL.md",
    "scripts/record-test-result.py",
    "hooks/lib/fingerprint.sh"
```

- [ ] **Step 3b: README.md** — standard の件数行（`test_readme_profile_counts.py` が JSON と一致を強制）を更新。現状「standard (18 required + 8 recommended)」→ **「standard (20 required + 10 recommended)」**。実装時に `python3 -c "import json;d=json.load(open('templates/profiles/standard.json'));print(len(d['required']),len(d['recommended']))"` で実数を確認してから README を合わせる。

- [ ] **Step 4: run → PASS**（judge_toolchain test ＋ `tests/test_readme_profile_counts.py` ＋ `tests/test_profile_checker_parity.py` ＋ `tests/test_profile_moat_registration.py`）。

- [ ] **Step 5: commit しない**（Task V でまとめて commit）。

---

## Task D2: Task hook を profile・active settings・contract に配線

**Files:**
- Modify: `templates/profiles/standard.json`（`hooks_include` + `required_hook_scripts`）
- Modify: `.claude/settings.local.json`（TaskCreated / TaskCompleted セクション新設）
- Modify: `scripts/check_framework_contract.py`（full self-check に CORE 強制 hook 登録検査）
- Test: `tests/test_task_hook_wiring.py`（新規）

**安全確認済:** check-task-created は phase=implement かつ plan 未承認時のみ hard-stop（現在 brainstorm/plan は pass-through）。check-task-completed は next_action 有・`.claude/evidence-log.jsonl` 有・`--check-completion-evidence` rc=0 を確認済。

- [ ] **Step 1: failing tests**

```python
# tests/test_task_hook_wiring.py
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _json(p): return json.loads((ROOT / p).read_text())

def test_standard_profile_includes_task_hooks():
    std = _json("templates/profiles/standard.json")
    for h in ("check-task-created.sh", "check-task-completed.sh"):
        assert h in std["hooks_include"], f"standard hooks_include missing {h}"
        assert h in std["required_hook_scripts"], f"standard required_hook_scripts missing {h}"

def test_active_settings_register_task_hooks():
    s = _json(".claude/settings.local.json")
    cmds = []
    for entries in s.get("hooks", {}).values():
        for e in entries:
            for hk in e.get("hooks", []):
                cmds.append(hk.get("command", ""))
    for h in ("check-task-created.sh", "check-task-completed.sh"):
        assert any(h in c for c in cmds), f"active settings missing {h}"

def test_contract_core_hook_check_behaviour(tmp_path):
    """grill 要検討 1: 定数存在だけでなく実挙動を検証。CORE hook 未登録の
    settings で FAIL を返し、実 framework settings では空（PASS）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cfc", ROOT / "scripts" / "check_framework_contract.py")
    cfc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cfc)
    # real framework root → no failures
    assert cfc.check_active_settings_core_hooks(ROOT) == []
    # fixture root with a settings missing the Task hooks → failures
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        '{"hooks":{"PreToolUse":[{"hooks":[{"command":"bash hooks/check-gate.sh"}]}]}}')
    fails = cfc.check_active_settings_core_hooks(tmp_path)
    assert any("check-task-completed.sh" in f for f in fails)
```

- [ ] **Step 2: run → FAIL** (all three; the behavioural one errors on missing attr).

- [ ] **Step 3a: standard.json** — `hooks_include` 末尾（`post-bash.sh` の後）に追加:

```json
    "post-bash-observe.sh",
    "post-bash.sh",
    "check-task-created.sh",
    "check-task-completed.sh"
```

`required_hook_scripts` 末尾（`check-deploy-gate.sh` の後）に追加:

```json
    "hooks/check-deploy-gate.sh",
    "hooks/check-task-created.sh",
    "hooks/check-task-completed.sh"
```

- [ ] **Step 3b: `.claude/settings.local.json`** — `PostToolUse` ブロックの後（`PostToolUseFailure` の前）に Task イベント 2 セクションを挿入（テンプレ `templates/hooks.template.json:132-151` 準拠。`continue` シグナル必要のため matcher なし）:

```json
    "TaskCreated": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PROJECT_DIR:-.}\"/hooks/check-task-created.sh"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PROJECT_DIR:-.}\"/hooks/check-task-completed.sh"
          }
        ]
      }
    ],
```

- [ ] **Step 3c: `scripts/check_framework_contract.py`** — full self-check に CORE 強制 hook 登録検査を追加。`VALID_PROFILES` 付近に定数を追加:

```python
# Hooks that mechanically enforce the operating contract's hard guarantees.
# The framework's own active settings MUST register all of these (the dogfood
# config drifted from the template once = D2). NOT the full hooks_include set:
# the dogfood deliberately omits check-tdd / check-skill-gate / check-cron-gate
# etc., so requiring the whole template would false-positive.
CORE_ENFORCEMENT_HOOKS = [
    "check-gate.sh",
    "post-status-audit.sh",
    "check-control-plane.sh",
    "check-task-created.sh",
    "check-task-completed.sh",
]
```

full self-check（framework root を検査する経路。`main()` のプロファイル早期 return 後の本体）に登録検査を追加する関数:

```python
def check_active_settings_core_hooks(root) -> list:
    """The framework's own .claude/settings.local.json must register every
    CORE_ENFORCEMENT_HOOKS command. Catches dogfood hook-wiring drift (D2)."""
    failures = []
    settings = root / ".claude" / "settings.local.json"
    if not settings.exists():
        settings = root / ".claude" / "settings.json"
    if not settings.exists():
        failures.append("active settings (.claude/settings.local.json) not found")
        return failures
    try:
        data = json.loads(read_text(settings))
    except json.JSONDecodeError as e:
        failures.append(f"{settings.name} is not valid JSON: {e}")
        return failures
    cmds = []
    for entries in (data.get("hooks", {}) or {}).values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for hook in entry.get("hooks", []):
                if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                    cmds.append(hook["command"])
    for script in CORE_ENFORCEMENT_HOOKS:
        if not any(script in c for c in cmds):
            failures.append(
                f".claude/settings.local.json missing CORE enforcement hook: {script}"
            )
    return failures
```

そして full self-check の `failures.extend(context_budget.check(ROOT))`（main() 内・確認済の挿入点）の**直後**に追加:

```python
    failures.extend(context_budget.check(ROOT))
    # D2: dogfood active settings must register CORE enforcement hooks.
    failures.extend(check_active_settings_core_hooks(ROOT))
```

- [ ] **Step 4: run → PASS**. 加えて `python3 scripts/check_status.py --root . --check-completion-evidence; echo rc=$?` が rc=0 のまま（live Task hook が自分の作業を阻害しない確認）。`python3 scripts/check_framework_contract.py`（full）が新検査込みで PASS。

- [ ] **Step 5: commit しない**（Task V でまとめて）。

---

## Task D3: upgrade で framework 資産を上書き・user 資産を保全

**Files:**
- Modify: `bin/setup.sh`（`copy_file_force` を diff-gated .bak 化／`is_framework_owned` 追加／required・recommended・hook-script ループのルーティング）
- Test: `tests/test_setup_upgrade_overwrite.py`（新規）

**根拠:** `copy_file`（:144-147）は既存を SKIP。required/recommended（:443,453）と hook script（:327）が SKIP 経路＝upgrade で hooks/scripts が更新されず security 修正が届かない。stamp（:477）だけ前進。

- [ ] **Step 1: failing test**

```python
# tests/test_setup_upgrade_overwrite.py
import subprocess, pathlib, os, tempfile, shutil
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _install(target, profile="standard"):
    subprocess.run(["bash", str(ROOT / "bin/setup.sh"),
                    f"--profile={profile}", f"--target={target}"],
                   check=True, capture_output=True, text=True)

def test_upgrade_overwrites_framework_hook_but_preserves_user_docs(tmp_path):
    target = tmp_path / "proj"
    _install(str(target))
    # Simulate a STALE framework hook + a user-customized STATUS.
    hook = target / "hooks" / "check-gate.sh"
    hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")
    status = target / "docs" / "STATUS.md"
    status.write_text("USER EDIT\n")
    _install(str(target))  # re-install = upgrade
    # framework-owned hook is refreshed from source (no longer STALE):
    assert "# STALE" not in hook.read_text()
    assert hook.read_text() == (ROOT / "hooks" / "check-gate.sh").read_text()
    # a .bak of the overwritten hook exists:
    assert list((target / "hooks").glob("check-gate.sh.bak.*"))
    # user-owned doc preserved:
    assert status.read_text() == "USER EDIT\n"

def test_identical_framework_file_makes_no_bak(tmp_path):
    target = tmp_path / "proj"
    _install(str(target))
    _install(str(target))  # second install, nothing changed
    assert not list((target / "hooks").glob("check-gate.sh.bak.*"))
```

- [ ] **Step 2: run → FAIL** (stale hook persists; no .bak).

- [ ] **Step 3a:** `bin/setup.sh` の `copy_file_force` を diff-gated .bak 付きに置換（hooks/lib も自動で恩恵）:

```bash
copy_file_force() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "  SKIP (source not found): $dst"
    return
  fi
  # No-op when identical: avoids churn and spurious .bak on a same-version
  # re-install (the common case).
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    return
  fi
  # Back up a differing existing copy before overwriting so a user-customized
  # framework file is recoverable (D3). Best-effort; never aborts the install.
  if [[ -f "$dst" ]]; then
    cp "$dst" "${dst}.bak.$(date +%s)" 2>/dev/null || true
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
  INSTALLED_PATHS+=("$dst")
  echo "  COPY (force): $dst"
}
```

- [ ] **Step 3b:** path 分類関数を `copy_file_force` の後に追加:

```bash
# D3: framework-owned paths are overwritten on upgrade (security fixes must
# reach existing installs); user-owned paths keep skip-if-exists (never clobber
# a user's STATUS / LEARNINGS / CLAUDE.md / settings).
is_framework_owned() {
  case "$1" in
    hooks/*|scripts/*|templates/*) return 0 ;;
    .claude/skills/*|.claude/agents/*|.claude/commands/*|.claude/rules/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Route a file to force-overwrite (framework-owned) or skip-if-exists (user).
copy_file_routed() {
  local rel="$1" src="$2" dst="$3"
  if is_framework_owned "$rel"; then
    copy_file_force "$src" "$dst"
  else
    copy_file "$src" "$dst"
  fi
}
```

- [ ] **Step 3c:** required ループ（:441-444）を routed 化:

```bash
while IFS= read -r rel_path; do
  src=$(resolve_source "$rel_path")
  copy_file_routed "$rel_path" "$src" "$TARGET/$rel_path"
done < <(parse_json_array "$PROFILE_JSON" "required")
```

recommended ループ（:451-454）も同様に `copy_file_routed "$rel_path" "$src" "$TARGET/$rel_path"`。

hook script ループ（copy_hooks 内 :326-328）:

```bash
  while IFS= read -r script; do
    copy_file_routed "hooks/$script" "$FRAMEWORK_ROOT/hooks/$script" "$target_dir/hooks/$script"
  done <<< "$hooks_include"
```

> 注: `resolve_source` が template に差し替える user 資産（CLAUDE.md / docs/STATUS.md / docs/LEARNINGS.md / docs/client/* / docs/translation/* / .claude/commands/{validate,retro}.md）は `is_framework_owned` で false 側に落ちる必要がある。`.claude/commands/*` は framework-owned だが validate.md/retro.md は template 差し替え＝**それでも framework-owned 扱いで上書き可**（中身は framework 提供物）。docs/*・CLAUDE.md は false＝保全。整合を grill で確認。

- [ ] **Step 4: run → PASS**（新規 2 test ＋ 既存 `tests/test_setup_distribution.py`・`test_setup_baseline.py`・`test_setup_prereq.py` が緑）。

- [ ] **Step 5: commit しない**（Task V でまとめて）。behavior change（再 install でカスタム framework hook が .bak つきで revert）を後述 CHANGELOG note に記載。

---

## Task D4: 壊れた既存設定の無警告全消しを是正

**Files:**
- Modify: `bin/setup.sh`（generate_settings の python heredoc :272-281）
- Test: `tests/test_setup_broken_settings.py`（新規）

- [ ] **Step 1: failing test**

```python
# tests/test_setup_broken_settings.py
import subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_broken_existing_settings_emits_warning(tmp_path):
    target = tmp_path / "proj"
    (target / ".claude").mkdir(parents=True)
    # Invalid JSON (JSONC-style comment a non-engineer might paste).
    (target / ".claude" / "settings.local.json").write_text(
        '{\n  // my note\n  "permissions": {"allow": ["Bash(ls)"]}\n}\n')
    r = subprocess.run(["bash", str(ROOT / "bin/setup.sh"),
                        "--profile=standard", f"--target={target}"],
                       capture_output=True, text=True)
    combined = r.stdout + r.stderr
    assert "WARNING" in combined and "could not be parsed" in combined
    # a .bak of the unparseable file exists (so the user can recover perms):
    assert list((target / ".claude").glob("settings.local.json.bak.*"))
```

- [ ] **Step 2: run → FAIL** (no warning today).

- [ ] **Step 3: implement** — heredoc 内 :272-281 を:

```python
target = '$target_settings'
if os.path.exists(target):
    try:
        with open(target) as f:
            existing = json.load(f)
    except Exception as e:
        sys.stderr.write(
            'WARNING: existing %s could not be parsed as JSON (%s).\n'
            '         Its permissions/env were NOT carried over. A backup was '
            'saved alongside it (.bak.*); restore values manually if needed.\n'
            % (target, e)
        )
        existing = {}
    for k, v in existing.items():
        if k == 'hooks':
            continue
        out[k] = v
```

（`.bak` は :217-219 で既に生成済＝メッセージはそれを指す。`sys` は import 済。）

- [ ] **Step 4: run → PASS**.

- [ ] **Step 5: commit しない**（Task V でまとめて）。

---

## Task I1: post-status-audit を fail-closed 化

**Files:**
- Modify: `hooks/lib/safety.sh`（PostToolUse 版 helper 追加）
- Modify: `hooks/post-status-audit.sh`（PostToolUse fallback block ＋ aegis_require_lib_block）
- Test: `tests/test_post_status_audit_fail_closed.py`（新規）

**設計:** post-status-audit は PostToolUse blocker。PreToolUse 用 byte-identical fallback（`test_safety_fallback_identity.py` の 12 hook）は schema 違いで流用不可。別マーカー `AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN/END` を使い、identity test 群とは独立。lib source 失敗で `{"decision":"block",...}` を emit。gate/mode tamper（bash のみ）は lib さえあれば検知可。**task_type tamper は I3=Batch 2 で I1 では不追加。** phase-transition の python3 依存部は現挙動維持（最小変更）。

- [ ] **Step 1: failing test**

```python
# tests/test_post_status_audit_fail_closed.py
import subprocess, shutil, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "post-status-audit.sh"

def _run(stdin, scriptdir):
    return subprocess.run(["bash", str(scriptdir / "post-status-audit.sh")],
                          input=stdin, capture_output=True, text=True)

def test_fail_closed_when_safety_lib_missing(tmp_path):
    """safety.sh が読めないと PostToolUse block を出して fail-closed."""
    hooks = tmp_path / "hooks"; (hooks / "lib").mkdir(parents=True)
    shutil.copy(HOOK, hooks / "post-status-audit.sh")
    # copy NO libs → safety.sh absent
    payload = json.dumps({"tool_input": {"file_path": str(tmp_path / "docs/STATUS.md")}})
    r = _run(payload, hooks)
    assert '"decision":"block"' in r.stdout
    assert r.returncode == 0  # explicit block, not crash/fail-open

def test_posttool_fallback_emits_block_schema():
    text = HOOK.read_text()
    assert "AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN" in text
    assert "AEGIS_SAFETY_FALLBACK_POSTTOOL_END" in text
    # the fallback emits PostToolUse block, not PreToolUse deny:
    import re
    m = re.search(r"POSTTOOL_BEGIN(.*?)POSTTOOL_END", text, re.DOTALL)
    assert '"decision":"block"' in m.group(1)
    assert "permissionDecision" not in m.group(1)

def test_pretool_identity_set_unchanged():
    """post-status-audit は 12-hook identity セットに入れない（schema が別）。"""
    t = (ROOT / "tests" / "test_safety_fallback_identity.py").read_text()
    assert "post-status-audit.sh" not in t
```

- [ ] **Step 2: run → FAIL** (markers absent; current script fail-opens with empty stdout).

- [ ] **Step 3a: `hooks/lib/safety.sh`** — 末尾に PostToolUse 版を追加:

```bash
# --- PostToolUse variant (I1) ---
# post-status-audit.sh is a PostToolUse blocker; its fail-closed signal is the
# top-level {"decision":"block"} schema, NOT PreToolUse deny. Reason is static
# (no substitution) for the same JSON-injection / drift-surface reasons.
_aegis_emit_fail_closed_block() {
  local stderr_hint="${1:-unspecified}"
  printf '[aegis-safety] fail-closed: %s\n' "$stderr_hint" >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
}

aegis_require_lib_block() {
  local lib="$1"
  if [ ! -r "$lib" ]; then
    _aegis_emit_fail_closed_block "lib not readable: $(basename "$lib")"
  fi
  set +e
  # shellcheck disable=SC1090
  source "$lib" 2>/dev/null
  local _rc=$?
  set -e
  if [ "$_rc" -ne 0 ]; then
    _aegis_emit_fail_closed_block "lib source failed (rc=$_rc): $(basename "$lib")"
  fi
}
```

- [ ] **Step 3b: `hooks/post-status-audit.sh`** — 現 :25-31 の lib source 群を fail-closed 化。`SCRIPT_DIR=...` の直後（ROOT 算出前）に PostToolUse fallback block を挿入し、その後 require_lib_block で必須 lib を読む:

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN
if [ ! -r "${SCRIPT_DIR}/lib/safety.sh" ]; then
  printf '[aegis-safety] fail-closed: safety.sh not readable\n' >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
fi
set +e
source "${SCRIPT_DIR}/lib/safety.sh" 2>/dev/null
_aegis_safety_rc=$?
set -e
if [ "$_aegis_safety_rc" -ne 0 ]; then
  printf '[aegis-safety] fail-closed: safety.sh source failed\n' >&2
  printf '%s\n' '{"decision":"block","reason":"[integrity] hook safety lib unavailable — check hooks/lib/* integrity"}'
  exit 0
fi
# AEGIS_SAFETY_FALLBACK_POSTTOOL_END
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
STATUS_FILE="${ROOT}/docs/STATUS.md"
SNAPSHOT_FILE="${ROOT}/.claude/.gate-snapshot"
AUDIT_SKIP_LOG="${ROOT}/.claude/.audit-skip.log"

# Load shared libs fail-closed (PostToolUse block on absence/source failure).
aegis_require_lib_block "${SCRIPT_DIR}/lib/extract-input.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/emit.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/frontmatter.sh"
aegis_require_lib_block "${SCRIPT_DIR}/lib/phase-skills.sh"
# layer-2 cp-lock lib (optional — absent in minimal scaffolds).
[ -r "${SCRIPT_DIR}/lib/cp-lock.sh" ] && source "${SCRIPT_DIR}/lib/cp-lock.sh" 2>/dev/null || true
```

（現行の `source "${SCRIPT_DIR}/lib/extract-input.sh"` 〜 cp-lock 行・重複コメントを上記で置換。）

- [ ] **Step 4: run → PASS**. 加えて: `bash -n hooks/post-status-audit.sh`、既存 `python3 -m pytest tests/test_safety_fallback_identity.py -q`（12-hook 同一性が壊れていない）、post-status-audit の正常系（lib 揃い）が従来通り allow/ block する既存テストが緑。

- [ ] **Step 5: commit しない**（Task V でまとめて）。phase-skills.sh は required_lib_block 維持（optional 化すると line 161 の呼び出しが set -e で fail-open 再発＝grill 要検討 4）。

---

## Task I2: 完了evidence 検査を fail-closed 化

**Files:**
- Modify: `scripts/check_status.py:1484-1497`
- Test: `tests/test_completion_evidence_fail_closed.py`（新規）

- [ ] **Step 1: failing test**

```python
# tests/test_completion_evidence_fail_closed.py
import subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def _run(root):
    return subprocess.run(
        ["python3", str(ROOT / "scripts/check_status.py"),
         "--root", str(root), "--check-completion-evidence"],
        capture_output=True, text=True)

def test_absent_status_is_violation(tmp_path):
    r = _run(tmp_path)  # no docs/STATUS.md
    assert r.returncode == 1
    assert "EVIDENCE" in r.stdout

def test_frontmatter_none_is_violation(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text("no frontmatter here\n")
    r = _run(tmp_path)
    assert r.returncode == 1
    assert "EVIDENCE" in r.stdout
```

- [ ] **Step 2: run → FAIL** (today returns rc=0 for both).

- [ ] **Step 3: implement** — :1484-1497 を:

```python
    if args.check_completion_evidence:
        status_path = root / "docs" / "STATUS.md"
        if not status_path.exists():
            print("EVIDENCE: docs/STATUS.md not found — cannot verify completion evidence")
            return 1
        frontmatter = extract_frontmatter(read_text(status_path))
        if frontmatter is None:
            print("EVIDENCE: docs/STATUS.md missing YAML frontmatter — cannot verify completion evidence")
            return 1
        refs = extract_current_refs(frontmatter)
        approvals = extract_approval_map(frontmatter)
        violations = evidence_integrity_violations(refs, approvals, root)
        for v in violations:
            print(f"EVIDENCE: {v}")
        # Exit-code coupled (belt-and-suspenders): the TaskCompleted hook keys on
        # stdout, but any other caller can trust the exit code too.
        return 1 if violations else 0
```

- [ ] **Step 4: run → PASS**. 加えて live: `python3 scripts/check_status.py --root . --check-completion-evidence; echo rc=$?` が rc=0（現リポは STATUS 正常＝退行なし）。

- [ ] **Step 5: commit しない**（Task V でまとめて）。

---

## Task V: 全体検証 + gate + 単一 commit（version は 1.14.0 据置）

**実装順（grill 推奨・リスク低い順）:** D1 → D2 → D4 → I2 → D3 → I1。すべて実装+test まで（**commit しない**）。

**Files:**
- Modify: `docs/LEARNINGS.md`（教訓・confidence 付き）
- Modify: `CHANGELOG.md`（存在すれば・D3 behavior change を 1 行: 再 install で framework 所有ファイルは .bak つき上書き）
- Modify: `docs/security-followups.md`（SF-006 を I1/I2 部分対応 / I3 残として更新）

- [ ] **Step 1: grill-code**（diff 全体を grill-code skill で叩き、全指摘を潰す）。
- [ ] **Step 2:** `python3 -m pytest -q`（既存 ~1038 + 新規が緑）/ `python3 scripts/check_framework_contract.py`（full PASS・**版 1.14.0 据置**）/ `python3 scripts/status_doctor.py --root .`（PASS）/ `bash -n bin/setup.sh hooks/post-status-audit.sh hooks/lib/safety.sh`。
- [ ] **Step 3:** standard 配布の擬似検証: 一時 target に `bin/setup.sh --profile=standard --target=/tmp/aegis-iter41` → `python3 scripts/check_framework_contract.py --profile=standard --root /tmp/aegis-iter41` PASS（judge toolchain + Task hooks 登録を含む）。
- [ ] **Step 4: LEARNINGS / security-followups 更新**（commit 前・working tree のまま）。
- [ ] **Step 5: gate**（**working tree 未 commit のまま**＝judge が diff を見られる）: review→qa→security→deploy→ship。各 gate は judge card（D1 で standard でも機能）。current_refs.<gate> は approve した時のみセット（pending+ref は stale 判定で赤＝既知の罠）。framework・L＝全ゲート必須。
- [ ] **Step 6: 単一 commit + push**: `fix(dist+integrity): standard profile gate/judge wiring, upgrade overwrite, fail-closed audit+evidence (iter41 Batch 1)`（push は yuuya-miyagaki）。最後に STATUS の next_action を iter42 アンカーに更新。

---

## Self-Review（writing-plans）

- **Spec coverage:** D1/D2/D3/D4/I1/I2 各々に Task。SF-006 の I1/I2 を被覆。I3/G1-G3/C1-C4 は明示的に Batch 2/Backlog（やらないこと）。✓
- **Placeholder scan:** 全 step に実コード/実コマンド。✓（D2 の contract 呼び出し位置のみ「既存集約パターンに合わせる」＝実装時確定。grill で固定。）
- **Type consistency:** `copy_file_routed(rel, src, dst)` / `is_framework_owned(rel)` / `aegis_require_lib_block(lib)` / `_aegis_emit_fail_closed_block(hint)` / `CORE_ENFORCEMENT_HOOKS` の名称を全 task で一貫使用。✓
- **未確定（grill-plan で詰める）:** (a) D3 の `.claude/rules/*` と template 差し替え user 資産（CLAUDE.md/STATUS/LEARNINGS）の分類境界が `is_framework_owned` と `resolve_source` で矛盾しないか。(b) D2 contract 検査の呼び出し位置。(c) I1 で phase-transition の python3 失敗を現挙動維持で良いか（advisory 化はレビュー助言）。

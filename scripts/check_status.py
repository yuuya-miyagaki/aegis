#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


# This validator intentionally supports a narrow YAML subset so the scaffold
# stays dependency-free. Keep STATUS.md frontmatter simple and avoid complex YAML
# features such as block scalars, inline comments in values, and nested maps
# beyond the documented schema.

REQUIRED_TOP_LEVEL_KEYS = [
    "framework",
    "framework_version",
    "project_name",
    "mode",
    "phase",
    "task_type",
    "last_updated",
    "gate_approvals",
    "current_refs",
    "next_action",
    "blockers",
    "session_history",
]

OPTIONAL_TOP_LEVEL_KEYS: set[str] = {"task_size", "task_size_rationale", "iteration", "ui_surface", "external_evidence", "failure_tracking", "client_context"}

# Canonical gate -> evidence-ref mapping. Single source of truth reused by
# validate_status_file, pre_approve_gate, and evidence_integrity_violations
# (mirrored in bash by update-gate.sh's get_ref_key).
GATE_REF_MAPPING = {
    "plan": "plan",
    "review": "review",
    "qa": "qa",
    "security": "security",
    "deploy": "deploy",
    "client_ready_for_dev": "translation",
}

# P1-D (OBS-008): client_ready_for_dev is the ONLY machine gate between Client
# and Dev. The handover package below mirrors the client-workflow skill's
# phase table; without an existence check the gate approves on bare assertion.
#
# C-3 (v1.6.1): existence-only allowed `touch` to bypass the gate. Each
# artifact also requires (a) ≥ CLIENT_ARTIFACT_MIN_BYTES of content AND
# (b) the machine-readable sentinel comment associated with the template.
# Templates embed the sentinel at the tail; users filling them out keep it.
CLIENT_GATE_ARTIFACTS = (
    ("docs/requirements/PRD.md",         "prd-context"),
    ("docs/requirements/SCOPE.md",       "scope-in-out"),
    ("docs/requirements/NFR.md",         "nfr"),
    ("docs/requirements/ACCEPTANCE.md",  "acceptance-criteria"),
    ("docs/handover/TO-DEV.md",          "handover-to-dev"),
    ("docs/translation/mapping.md",      "translation-mapping"),
)

CLIENT_ARTIFACT_MIN_BYTES = 200

# P2 (v1.9.0): spec delta review. On the 2nd+ iteration the client must review
# what changed since the last cycle before client_ready_for_dev re-approves.
# Enforced at the GATE ONLY (see _spec_delta_issues) — kept OUT of
# CLIENT_GATE_ARTIFACTS and _client_artifact_issues so the task-completion
# symmetric check (which fires while client_ready_for_dev stays approved) does
# not demand a delta on every later Dev iteration. Same existence + min-bytes +
# sentinel contract as the 6.
SPEC_DELTA_ARTIFACT = ("docs/handover/CHANGES.md", "spec-delta")


def _artifact_content_issue(
    root: Path, rel: str, sentinel: str, template_map: dict
) -> str | None:
    """Existence + min-bytes + sentinel check for one artifact.

    Returns a human-readable issue string, or None if it passes. template_map
    (ARTIFACT_TO_TEMPLATE) supplies the deny-message template hint (K-12) so the
    non-engineer reader can copy templates/X.template.md → docs/Y.md without
    guessing the naming.
    """
    template_hint = ""
    tmpl = template_map.get(rel)
    if tmpl:
        template_hint = f"（テンプレ: {tmpl}）"
    p = root / rel
    if not p.exists():
        return f"- {rel}: 不在 {template_hint}"
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"- {rel}: 読み取り失敗"
    if len(text.encode("utf-8")) < CLIENT_ARTIFACT_MIN_BYTES:
        return (f"- {rel}: 内容が {CLIENT_ARTIFACT_MIN_BYTES} バイト未満 "
                f"（テンプレを実際に埋めてください） {template_hint}")
    marker = f"<!-- aegis-required-section: {sentinel} -->"
    if marker not in text:
        return (f"- {rel}: 必須 sentinel `{marker}` が見つかりません "
                f"（テンプレ末尾のコメントを残してください） {template_hint}")
    return None


def _client_artifact_issues(root: Path) -> list[str]:
    """Return human-readable issues, empty list if all 6 artifacts pass.

    The 6 CLIENT_GATE_ARTIFACTS only. SPEC_DELTA_ARTIFACT is NOT checked here
    (gate-only via _spec_delta_issues) so the task-completion symmetric caller
    is unaffected.
    """
    try:
        from _artifact_template_map import ARTIFACT_TO_TEMPLATE
    except ImportError:
        ARTIFACT_TO_TEMPLATE = {}
    issues: list[str] = []
    for rel, sentinel in CLIENT_GATE_ARTIFACTS:
        issue = _artifact_content_issue(root, rel, sentinel, ARTIFACT_TO_TEMPLATE)
        if issue:
            issues.append(issue)
    return issues


def _spec_delta_iteration(root: Path) -> int | None:
    """STATUS.md iteration when > 1 (a prior cycle exists, so the client must
    review what changed), else None. iteration absent / non-integer / <=1 =>
    None (fail-open). Never raises. Value is stripped before the digit test so
    a trailing space does not silently disable the check. iter56 ⑤: returns the
    value (not just a bool) so the gate approval log can name the iteration."""
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        return None
    try:
        fm = extract_frontmatter(status_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None
    if not fm:
        return None
    it = extract_scalar_value(fm, "iteration")
    if it is None:
        return None
    it = it.strip()
    # isascii() guard: str.isdigit() is True for non-ASCII digits (e.g. "²"),
    # but int("²") raises. ascii + digit => [0-9]+ => int() is safe.
    if not (it.isascii() and it.isdigit()):
        return None
    value = int(it)
    return value if value > 1 else None


def _spec_delta_required(root: Path) -> bool:
    return _spec_delta_iteration(root) is not None


def _spec_delta_issues(root: Path) -> list[str]:
    """Gate-only: when iteration > 1, require docs/handover/CHANGES.md with the
    same existence + min-bytes + sentinel contract. Returns [] when not
    required. Intentionally separate from _client_artifact_issues (C1)."""
    if not _spec_delta_required(root):
        return []
    try:
        from _artifact_template_map import ARTIFACT_TO_TEMPLATE
    except ImportError:
        ARTIFACT_TO_TEMPLATE = {}
    rel, sentinel = SPEC_DELTA_ARTIFACT
    issue = _artifact_content_issue(root, rel, sentinel, ARTIFACT_TO_TEMPLATE)
    return [issue] if issue else []

REQUIRED_APPROVAL_KEYS = [
    "client_ready_for_dev",
    "brainstorm",
    "plan",
    "review",
    "qa",
    "security",
    "deploy",
    "dev_ready_for_client",
]

ALLOWED_APPROVAL_VALUES = {"pending", "approved", "blocked", "n/a"}
ALLOWED_MODES = {"Client", "Dev"}
ALLOWED_PHASES = {
    "onboard",
    "discovery",
    "requirements",
    "scope",
    "acceptance",
    "handover",
    "brainstorm",
    "plan",
    "implement",
    "review",
    "qa",
    "security",
    "deploy",
    "ship",
    "docs",
}
MODE_PHASES = {
    "Client": {"onboard", "discovery", "requirements", "scope", "acceptance", "handover"},
    "Dev": {"brainstorm", "plan", "implement", "review", "qa", "security", "deploy", "ship", "docs"},
}
# Ordered Dev phase sequence (source of truth for phase-order checks).
DEV_PHASE_ORDER = ["brainstorm", "plan", "implement", "review", "qa", "security", "deploy", "ship", "docs"]
EXPECTED_CURRENT_REF_KEYS = {"requirements", "plan", "spec", "review", "qa", "security", "deploy", "translation"}
ALLOWED_TASK_TYPES = {"feature", "refactor", "bugfix", "hotfix", "framework"}
ALLOWED_TASK_SIZES = {"S", "M", "L"}
# Phase flow constraints by task size.
# S: minimal flow (1-file fixes) — skips plan/qa/security/deploy but keeps the
#    ship→docs terminal (docs is unenforced, so its inclusion is purely additive
#    and unifies S with the M/L terminal, closing the 罠 q static/transition split).
# M: skip deploy. L: all phases.
SIZE_ALLOWED_PHASES = {
    "S": {"brainstorm", "implement", "review", "ship", "docs"},
    "M": {"brainstorm", "plan", "implement", "review", "qa", "security", "ship", "docs"},
    "L": {"brainstorm", "plan", "implement", "review", "qa", "security", "deploy", "ship", "docs"},
}

# Task types that require strict gate enforcement (no n/a allowed).
STRICT_GATE_TASK_TYPES = {"feature", "refactor", "framework"}
# Per-phase gates that must be approved (not n/a) for strict task types.
# At deploy: review/qa/security are prerequisites and must already be approved.
# At ship/docs: deploy must also be approved.
STRICT_GATE_BY_PHASE = {
    "deploy": ["review", "qa", "security"],
    "ship": ["review", "qa", "security", "deploy"],
    "docs": ["review", "qa", "security", "deploy"],
}
PHASE_REQUIRES_GATES = {
    "plan": ["brainstorm"],
    "implement": ["brainstorm", "plan"],
    "review": ["brainstorm", "plan"],
    "qa": ["brainstorm", "plan", "review"],
    "security": ["brainstorm", "plan", "review", "qa"],
    "deploy": ["brainstorm", "plan", "review", "qa", "security"],
    "ship": ["brainstorm", "plan", "review", "qa", "security", "deploy"],
    "docs": ["brainstorm", "plan", "review", "qa", "security", "deploy"],
}
MAX_SESSION_HISTORY_ENTRIES = 3
MAX_EXTERNAL_EVIDENCE_ENTRIES = 3
REQUIRED_BODY_HEADINGS = [
    "## Summary",
    "## Recent Decisions",
    "## Session History",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_frontmatter(text: str) -> str | None:
    match = re.search(r"\A---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    return match.group("body")


def has_top_level_key(frontmatter: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}:\s*", frontmatter) is not None


def extract_scalar_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf'(?m)^{re.escape(key)}:\s*"(.*)"\s*$', frontmatter)
    if match:
        return match.group(1).strip()

    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+)\s*$", frontmatter)
    if match:
        return match.group(1).strip().strip('"').strip("'")

    return None


def extract_approval_map(frontmatter: str) -> dict[str, str]:
    approvals: dict[str, str] = {}
    in_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            if re.match(r"^gate_approvals:\s*$", line):
                in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*([A-Za-z0-9_\"'\-/]+)\s*$", line)
        if match:
            approvals[match.group(1)] = match.group(2).strip("\"'")

    return approvals


def extract_current_refs(frontmatter: str) -> dict[str, list[str] | str]:
    refs: dict[str, list[str] | str] = {}
    current_key: str | None = None
    in_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            if re.match(r"^current_refs:\s*$", line):
                in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        key_match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.*)$", line)
        if key_match:
            current_key = key_match.group(1)
            raw_value = key_match.group(2).strip()
            if raw_value in {"null", "[]", ""}:
                refs[current_key] = [] if raw_value == "[]" else "null"
            else:
                refs[current_key] = raw_value.strip("\"'")
            continue

        item_match = re.match(r"^\s{4}-\s*(.+)$", line)
        if item_match and current_key:
            existing = refs.get(current_key)
            value = item_match.group(1).strip().strip("\"'")
            if isinstance(existing, list):
                existing.append(value)
            else:
                refs[current_key] = [value]

    return refs


def extract_session_history(frontmatter: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            # Handle both block form and inline empty list.
            header = re.match(r"^session_history:\s*(.*)$", line)
            if header:
                inline = header.group(1).strip()
                if inline == "[]":
                    return []  # Empty list is valid.
                if inline == "":
                    in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        entry_start = re.match(r"^\s{2}-\s*date:\s*(.+)$", line)
        if entry_start:
            if current:
                entries.append(current)
            current = {"date": entry_start.group(1).strip().strip('"')}
            continue

        entry_field = re.match(r"^\s{4}([A-Za-z0-9_]+):\s*(.+)$", line)
        if entry_field and current is not None:
            current[entry_field.group(1)] = entry_field.group(2).strip().strip('"')

    if current:
        entries.append(current)

    return entries


def extract_blockers(frontmatter: str) -> list[str]:
    """Extract blocker items from frontmatter.

    Handles both inline ``blockers: []`` and block form::

        blockers:
          - "item 1"
          - "item 2"
    """
    blockers: list[str] = []
    in_block = False
    for line in frontmatter.splitlines():
        stripped = line.rstrip()
        if not in_block:
            if stripped.startswith("blockers:"):
                inline = stripped[len("blockers:"):].strip()
                if inline == "[]":
                    return []
                if inline == "":
                    in_block = True
                    continue
                blockers.append(inline.strip('"'))
                return blockers
            continue
        s = stripped.strip()
        if s.startswith("- "):
            blockers.append(s[2:].strip().strip('"'))
        elif s and not stripped.startswith(" "):
            break
    return blockers


REQUIRED_FAILURE_TRACKING_FIELDS = ["goal", "count", "last_attempt"]


def extract_failure_tracking(frontmatter: str) -> dict[str, str] | None:
    """Extract failure_tracking from frontmatter.

    Expected format:
        failure_tracking:
          goal: "description"
          count: 2
          last_attempt: "what was tried"

    ``failure_tracking: null`` means no active tracking (returns None).
    """
    in_block = False
    fields: dict[str, str] = {}

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            header = re.match(r"^failure_tracking:\s*(.*)$", line)
            if header:
                inline = header.group(1).strip()
                if inline == "null" or inline == "":
                    if inline == "null":
                        return None
                    in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        field_match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.+)$", line)
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).strip().strip('"')

    return fields if fields else None


REQUIRED_CLIENT_CONTEXT_FIELDS = ["client_id", "context_loaded"]


def extract_client_context(frontmatter: str) -> dict[str, str] | None:
    """Extract client_context from frontmatter.

    Expected format:
        client_context:
          client_id: "project-name"
          context_loaded: true

    ``client_context: null`` means not set (returns None).
    """
    in_block = False
    fields: dict[str, str] = {}

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            header = re.match(r"^client_context:\s*(.*)$", line)
            if header:
                inline = header.group(1).strip()
                if inline == "null" or inline == "":
                    if inline == "null":
                        return None
                    in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        field_match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*(.+)$", line)
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).strip().strip('"')

    return fields if fields else None


REQUIRED_EVIDENCE_FIELDS = ["type", "scope", "findings", "resolution"]


def extract_external_evidence(frontmatter: str) -> list[dict[str, str]]:
    """Extract external_evidence entries from frontmatter.

    Expected format (list of maps, field order independent):
        external_evidence:
          - type: "codex-review-round-1"
            scope: "v0.5.0 Phase 1-7"
            findings: "..."
            resolution: "..."

    Inline empty list (``external_evidence: []``) is valid and yields [].
    """
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            # Match both "external_evidence:" (block) and
            # "external_evidence: []" (inline empty).
            header = re.match(r"^external_evidence:\s*(.*)$", line)
            if header:
                inline = header.group(1).strip()
                if inline == "[]" or inline == "":
                    in_block = inline == ""
                    # inline [] → return empty list immediately
                    if not in_block:
                        return []
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        # Entry start: "  - <key>: <value>" — field-order independent.
        entry_start = re.match(r"^\s{2}-\s*([A-Za-z0-9_]+):\s*(.+)$", line)
        if entry_start:
            if current:
                entries.append(current)
            current = {entry_start.group(1): entry_start.group(2).strip().strip('"')}
            continue

        # Subsequent fields: "    <key>: <value>"
        entry_field = re.match(r"^\s{4}([A-Za-z0-9_]+):\s*(.+)$", line)
        if entry_field and current is not None:
            current[entry_field.group(1)] = entry_field.group(2).strip().strip('"')

    if current:
        entries.append(current)

    return entries


def evidence_integrity_violations(
    refs: dict[str, list[str] | str],
    approvals: dict[str, str],
    root: Path,
) -> list[str]:
    """Gate/ref consistency + ref-file existence. Returns bare violation
    messages WITHOUT a path prefix, so validate_status_file can prepend the
    path and --check-completion-evidence can use them directly. Never raises."""
    violations: list[str] = []
    try:
        for gate_key, ref_key in GATE_REF_MAPPING.items():
            gate_value = approvals.get(gate_key)
            ref_value = refs.get(ref_key)
            ref_is_empty = ref_value is None or ref_value == "null" or ref_value == []
            if gate_value == "approved" and ref_is_empty:
                violations.append(
                    f"gate '{gate_key}' is approved but current_refs.{ref_key} is empty"
                )
            if gate_value in {"pending", "n/a"} and not ref_is_empty:
                violations.append(
                    f"gate '{gate_key}' is '{gate_value}' but current_refs.{ref_key} "
                    f"still has a value (stale ref: {ref_value})"
                )

        for key in ("plan", "spec", "review", "qa", "security", "deploy", "translation"):
            value = refs.get(key)
            if isinstance(value, str) and value != "null":
                if not (root / value).exists():
                    violations.append(f"points to missing {key} ref: {value}")

        requirements = refs.get("requirements")
        if isinstance(requirements, list):
            for rel_path in requirements:
                if not (root / rel_path).exists():
                    violations.append(f"points to missing requirements ref: {rel_path}")

        if approvals.get("client_ready_for_dev") == "approved":
            # C-3 (v1.6.1): the gate's content check is bilateral —
            # pre-approve enforces it AND task-completion re-checks it.
            # Otherwise an approve-then-delete pattern would let a 6-touch
            # bypass slip back in at completion time.
            for issue in _client_artifact_issues(root):
                violations.append(
                    f"gate 'client_ready_for_dev' is approved but handover "
                    f"artifact failed integrity check: {issue}"
                )
    except Exception as exc:
        # Never raises (callers — validate_status_file and the TaskCompleted hook —
        # must not crash). But do NOT swallow into "no violations": a crashed
        # integrity check is reported as a fail-closed violation, not false-green.
        return [f"evidence integrity check could not be completed: {exc}"]
    return violations


def validate_status_file(path: Path) -> list[str]:
    failures: list[str] = []

    if not path.exists():
        return [f"missing status file: {path}"]

    text = read_text(path)
    frontmatter = extract_frontmatter(text)

    if frontmatter is None:
        return [f"{path} is missing YAML frontmatter"]

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if not has_top_level_key(frontmatter, key):
            failures.append(f"{path} is missing frontmatter key: {key}")

    # Warn about unknown top-level keys (comments excluded).
    allowed_keys = set(REQUIRED_TOP_LEVEL_KEYS) | OPTIONAL_TOP_LEVEL_KEYS
    for line in frontmatter.splitlines():
        key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*", line)
        if key_match:
            found_key = key_match.group(1)
            if found_key not in allowed_keys:
                failures.append(f"{path} has unknown frontmatter key: {found_key}")

    mode = extract_scalar_value(frontmatter, "mode")
    phase = extract_scalar_value(frontmatter, "phase")
    if mode is None or mode not in ALLOWED_MODES:
        failures.append(f"{path} has invalid mode: {mode}")
    if phase is None or phase not in ALLOWED_PHASES:
        failures.append(f"{path} has invalid phase: {phase}")
    if mode in MODE_PHASES and phase not in MODE_PHASES[mode]:
        failures.append(f"{path} has invalid phase for mode {mode}: {phase}")

    task_type = extract_scalar_value(frontmatter, "task_type")
    if task_type and task_type not in ALLOWED_TASK_TYPES:
        failures.append(f"{path} has invalid task_type: {task_type}")

    iteration = extract_scalar_value(frontmatter, "iteration")
    if iteration is not None:
        if not iteration.isdigit() or int(iteration) < 1:
            failures.append(f"{path} has invalid iteration (must be positive integer): {iteration}")

    ui_surface = extract_scalar_value(frontmatter, "ui_surface")
    if ui_surface is not None:
        if ui_surface not in {"true", "false"}:
            failures.append(f"{path} has invalid ui_surface (must be true/false): {ui_surface}")

    task_size = extract_scalar_value(frontmatter, "task_size")
    if task_size is not None:
        if task_size not in ALLOWED_TASK_SIZES:
            failures.append(f"{path} has invalid task_size: {task_size}")
        elif mode == "Dev" and phase and phase in ALLOWED_PHASES:
            allowed = SIZE_ALLOWED_PHASES.get(task_size, ALLOWED_PHASES)
            if phase not in allowed:
                failures.append(
                    f"{path} phase '{phase}' is not allowed for task_size '{task_size}'"
                )
        elif mode == "Client":
            print(
                f"WARNING: {path} task_size '{task_size}' is set in Client mode "
                "(task_size only applies to Dev phases)"
            )

    # task_size sizing should be justified. For strict task types, task_size='S'
    # exempts qa/security (state-machine routing), so a missing rationale there is
    # a FAIL — it prevents silently downgrading enforcement by mislabeling an L/M
    # task as S. Other cases stay a WARNING.
    if task_size is not None:
        rationale = extract_scalar_value(frontmatter, "task_size_rationale")
        if rationale is None or rationale == "":
            if task_type in STRICT_GATE_TASK_TYPES and task_size == "S":
                failures.append(
                    f"{path} task_type '{task_type}' with task_size 'S' skips qa/security "
                    "but has no task_size_rationale (justification required)"
                )
            else:
                print(
                    f"WARNING: {path} has task_size '{task_size}' but no task_size_rationale "
                    "(recommended to document sizing justification)"
                )

    approvals = extract_approval_map(frontmatter)
    for key in REQUIRED_APPROVAL_KEYS:
        if key not in approvals:
            failures.append(f"{path} is missing gate approval: {key}")
            continue
        if approvals[key] not in ALLOWED_APPROVAL_VALUES:
            failures.append(
                f"{path} has invalid approval value for {key}: {approvals[key]}"
            )

    # Phase gate check: prior gates must not be pending/blocked.
    # When task_size is set, only require gates whose phase is in the size flow.
    if phase and phase in PHASE_REQUIRES_GATES:
        required_prior = PHASE_REQUIRES_GATES[phase]
        if task_size and task_size in SIZE_ALLOWED_PHASES:
            allowed_phases = SIZE_ALLOWED_PHASES[task_size]
            required_prior = [g for g in required_prior if g in allowed_phases]
        for required_gate in required_prior:
            gate_value = approvals.get(required_gate)
            if gate_value in {"pending", "blocked"}:
                failures.append(
                    f"{path} is in phase '{phase}' but gate '{required_gate}' is '{gate_value}'"
                )

    # Dev verification by task type: feature/refactor/framework require
    # specific gates to be approved (not n/a) depending on current phase.
    # When task_size is set, only enforce gates whose phase is in the size flow.
    if task_type in STRICT_GATE_TASK_TYPES and task_size != "S" and phase in STRICT_GATE_BY_PHASE:
        strict_gates = STRICT_GATE_BY_PHASE[phase]
        if task_size and task_size in SIZE_ALLOWED_PHASES:
            allowed_phases = SIZE_ALLOWED_PHASES[task_size]
            strict_gates = [g for g in strict_gates if g in allowed_phases]
        for gate in strict_gates:
            gate_value = approvals.get(gate)
            if gate_value == "n/a":
                failures.append(
                    f"{path} task_type '{task_type}' requires gate '{gate}' "
                    f"to be approved at phase '{phase}', but it is 'n/a'"
                )

    for heading in REQUIRED_BODY_HEADINGS:
        if heading not in text:
            failures.append(f"{path} is missing body heading: {heading}")

    refs = extract_current_refs(frontmatter)
    ref_keys = set(refs.keys())
    missing_ref_keys = EXPECTED_CURRENT_REF_KEYS - ref_keys
    unknown_ref_keys = ref_keys - EXPECTED_CURRENT_REF_KEYS
    for key in sorted(missing_ref_keys):
        failures.append(f"{path} is missing current_refs key: {key}")
    for key in sorted(unknown_ref_keys):
        failures.append(f"{path} has unknown current_refs key: {key}")

    # Validate ref value types: requirements must be list, others must be scalar-or-null.
    req_value = refs.get("requirements")
    if req_value is not None and not isinstance(req_value, list):
        failures.append(f"{path} current_refs.requirements must be a list, got scalar: {req_value}")
    for scalar_key in ["plan", "spec", "review", "qa", "security", "deploy", "translation"]:
        sv = refs.get(scalar_key)
        if isinstance(sv, list):
            failures.append(f"{path} current_refs.{scalar_key} must be scalar-or-null, got list")

    # Gate/ref consistency + ref existence (shared with --check-completion-evidence;
    # messages identical to the previous inline form via the path prefix below).
    root = path.parent.parent
    for m in evidence_integrity_violations(refs, approvals, root):
        failures.append(f"{path} {m}")

    history = extract_session_history(frontmatter)
    if len(history) > MAX_SESSION_HISTORY_ENTRIES:
        failures.append(
            f"{path} has too many session_history entries: {len(history)} > {MAX_SESSION_HISTORY_ENTRIES}"
        )
    for index, entry in enumerate(history, start=1):
        for field in ["date", "mode", "phase", "note"]:
            if field not in entry or not entry[field]:
                failures.append(f"{path} session_history entry {index} is missing {field}")
        entry_mode = entry.get("mode")
        entry_phase = entry.get("phase")
        if entry_mode and entry_mode not in ALLOWED_MODES:
            failures.append(
                f"{path} session_history entry {index} has invalid mode: {entry_mode}"
            )
        if entry_phase and entry_phase not in ALLOWED_PHASES:
            failures.append(
                f"{path} session_history entry {index} has invalid phase: {entry_phase}"
            )
        if entry_mode in MODE_PHASES and entry_phase not in MODE_PHASES[entry_mode]:
            failures.append(
                f"{path} session_history entry {index} has invalid phase for mode {entry_mode}: {entry_phase}"
            )

    # Validate external_evidence schema (optional field).
    evidence_entries = extract_external_evidence(frontmatter)
    if len(evidence_entries) > MAX_EXTERNAL_EVIDENCE_ENTRIES:
        failures.append(
            f"{path} has too many external_evidence entries: {len(evidence_entries)} > "
            f"{MAX_EXTERNAL_EVIDENCE_ENTRIES} (archive older entries to docs/evidence-archive.md)"
        )
    allowed_evidence_fields = set(REQUIRED_EVIDENCE_FIELDS)
    for index, entry in enumerate(evidence_entries, start=1):
        for field in REQUIRED_EVIDENCE_FIELDS:
            if field not in entry or not entry[field]:
                failures.append(
                    f"{path} external_evidence entry {index} is missing required field: {field}"
                )
        for field in sorted(set(entry.keys()) - allowed_evidence_fields):
            failures.append(
                f"{path} external_evidence entry {index} has unknown field: {field}"
            )
        # WARNING (not FAIL): recommend kebab-case type naming convention.
        ev_type = entry.get("type", "")
        if ev_type and not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", ev_type):
            print(
                f"WARNING: {path} external_evidence entry {index} type '{ev_type}' "
                "does not follow kebab-case convention (e.g. 'codex-review-v071-1')"
            )

    # Validate client_context (optional field).
    if has_top_level_key(frontmatter, "client_context"):
        cc = extract_client_context(frontmatter)
        if cc is not None:
            client_id = cc.get("client_id", "")
            if not client_id:
                print(
                    f"WARNING: {path} client_context.client_id is empty "
                    "(recommended to set a project identifier)"
                )
            context_loaded = cc.get("context_loaded", "")
            if context_loaded not in ("true", "false"):
                failures.append(
                    f"{path} client_context.context_loaded must be true/false: {context_loaded}"
                )

    # Validate failure_tracking (optional field).
    if has_top_level_key(frontmatter, "failure_tracking"):
        ft = extract_failure_tracking(frontmatter)
        if ft is not None:
            allowed_ft_fields = set(REQUIRED_FAILURE_TRACKING_FIELDS)
            for field in REQUIRED_FAILURE_TRACKING_FIELDS:
                if field not in ft or not ft[field]:
                    failures.append(
                        f"{path} failure_tracking is missing required field: {field}"
                    )
            for field in sorted(set(ft.keys()) - allowed_ft_fields):
                failures.append(
                    f"{path} failure_tracking has unknown field: {field}"
                )
            count_val = ft.get("count", "")
            if count_val and (not count_val.isdigit() or int(count_val) < 1):
                failures.append(
                    f"{path} failure_tracking.count must be a positive integer: {count_val}"
                )

    return failures


def validate_with_pyyaml(text: str, path: Path) -> list[str]:
    """Optional strict validation using PyYAML for cross-checking."""
    try:
        import yaml
    except ImportError:
        return [f"--strict requires PyYAML: pip install pyyaml"]

    failures: list[str] = []
    fm = extract_frontmatter(text)
    if fm is None:
        return [f"{path} missing frontmatter for PyYAML cross-check"]

    try:
        parsed = yaml.safe_load(fm)
    except yaml.YAMLError as e:
        return [f"{path} PyYAML parse error: {e}"]

    if not isinstance(parsed, dict):
        return [f"{path} PyYAML parsed frontmatter is not a dict"]

    # Cross-check key fields.
    regex_mode = extract_scalar_value(fm, "mode")
    yaml_mode = parsed.get("mode")
    if regex_mode != str(yaml_mode):
        failures.append(f"{path} mode mismatch: regex={regex_mode!r}, PyYAML={yaml_mode!r}")

    regex_phase = extract_scalar_value(fm, "phase")
    yaml_phase = parsed.get("phase")
    if regex_phase != str(yaml_phase):
        failures.append(f"{path} phase mismatch: regex={regex_phase!r}, PyYAML={yaml_phase!r}")

    regex_approvals = extract_approval_map(fm)
    yaml_approvals = parsed.get("gate_approvals", {})
    if isinstance(yaml_approvals, dict):
        for key in REQUIRED_APPROVAL_KEYS:
            rv = regex_approvals.get(key)
            yv = yaml_approvals.get(key)
            if (rv != str(yv)) if yv is not None else (rv != yv):
                failures.append(f"{path} gate {key} mismatch: regex={rv!r}, PyYAML={yv!r}")

    return failures


def run_qa_drill(root: Path) -> int:
    """Run the test-strength drill (B1) at qa-gate approval time (Approach A).

    The verdict is computed live by the harness here, so it cannot be forged or
    go stale. A drill spec is required: either a real spec (mutants) for code
    tasks, or an explicit, auditable skip spec ({"skip": true, "reason": "..."})
    for tasks with no testable code (note: qa cannot be set to n/a via
    update-gate.sh, so the skip is declared in the evidence file itself).
    Returns 0 if the drill passes (or is validly skipped), 1 to block approval.
    """
    spec_path = root / "docs" / "qa-reports" / "test-strength.drill"
    report_path = root / "docs" / "qa-reports" / "test-strength.md"
    if not spec_path.is_file():
        print("ERROR: qa を approve するにはテスト強度ドリル仕様が必要です。")
        print("       コードを変更したタスク: mutant 入りの .drill を作成してください。")
        print('       テスト対象コードが無いタスク: {"skip": true, "reason": "..."} '
              "の .drill を作成してください。")
        print(f"       場所: {spec_path}")
        return 1
    # Explicit, auditable skip for tasks with no testable code. Unlike silently
    # omitting the drill, the reason is recorded in the evidence file the user
    # reviews, so a non-engineer can question it.
    try:
        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"ERROR: ドリル仕様が不正な JSON です: {exc}")
        return 1
    if isinstance(spec_data, dict) and spec_data.get("skip") is True:
        reason = spec_data.get("reason", "(理由未記載)")
        print(f"テスト強度ドリル: スキップ宣言（テスト対象コードなし）。理由: {reason}")
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                "# テスト強度ドリル結果（機械ブロック・ハーネス生成）\n\n"
                "```\nverdict: SKIP\n"
                f"reason: {reason}\n```\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        return 0
    runner = Path(__file__).resolve().parent / "run-test-strength-drill.py"
    if not runner.is_file():
        print(f"ERROR: ドリルランナーが見つかりません: {runner}")
        return 1
    try:
        proc = subprocess.run(
            ["python3", str(runner), "--root", str(root),
             "--spec", str(spec_path), "--report", str(report_path)],
            capture_output=True, text=True,
        )
    except OSError as exc:
        print(f"ERROR: ドリル起動に失敗: {exc}")
        return 1
    # surface the runner's plain output so update-gate.sh echoes it to the user
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return 0 if proc.returncode == 0 else 1


JUDGE_GATES = ("review", "qa", "security", "deploy")


def run_judge_card(gate: str, root: Path) -> int:
    """Build the B2 judge card live at approval. Returns tri-state 0/1/2.
    Builder crash => 1 (fail-closed)."""
    builder = Path(__file__).resolve().parent / "build-judge-card.py"
    if not builder.is_file():
        print(f"ERROR: judge ビルダーが見つかりません: {builder}")
        return 1
    try:
        proc = subprocess.run(
            ["python3", str(builder), "--gate", gate, "--root", str(root)],
            capture_output=True, text=True,
        )
    except OSError as exc:
        print(f"ERROR: judge ビルダー起動失敗: {exc}")
        return 1
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip())
    return proc.returncode if proc.returncode in (0, 1, 2) else 1


def check_gate_prerequisites(
    gate_name: str, root: Path, phase: str, task_type: str,
    task_size: str, approvals: dict,
) -> int:
    """Deterministic gate-prerequisite check: mode-transition requirements,
    phase ordering, prerequisite gate approvals, and strict-gate enforcement.

    Returns 0 if the gate's prerequisites are satisfied, 1 if blocked. This is
    pure gating logic (the gate-state mapping); it deliberately does NOT run the
    B1 drill or the B2 judge card — those are evidence-quality checks layered on
    top by pre_approve_gate. Kept separate so the mapping can be unit-tested in
    isolation from the (non-deterministic, fixture-heavy) evidence checks.
    """
    # Mode-transition gates.
    if gate_name == "dev_ready_for_client":
        # Require review gate to be approved before handing back to Client.
        required = ["review"]
        # For strict task types (feature/refactor/framework) with size > S,
        # also require qa and security.
        if task_type in STRICT_GATE_TASK_TYPES and task_size != "S":
            required.extend(["qa", "security"])
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
            print("       → .claude/skills/uat/SKILL.md を Read して UAT を実施")
            return 1
        return 0

    if gate_name == "client_ready_for_dev":
        # C-3 (v1.6.1): existence + ≥200 bytes + sentinel comment.
        # Templates carry the sentinel at the tail so a normal "copy template
        # → fill body → save" flow keeps it. `touch`-created empty files,
        # sentinel-removed files, and < 200-byte files all DENY.
        issues = _client_artifact_issues(root)
        issues.extend(_spec_delta_issues(root))  # P2: gate-only spec delta (iteration>1)
        if issues:
            print("ERROR: client_ready_for_dev に必要な引き渡し成果物が不足しています:")
            for issue in issues:
                print(f"       {issue}")
            print("       → .claude/skills/client-workflow/SKILL.md を Read し、"
                  "不足フェーズを完了してください。")
            print("       （mapping.md の作り方は "
                  ".claude/skills/translation-mapping/SKILL.md）")
            return 1
        # iter56 ⑤: required かつ合格時のみ肯定1行（対象外は無言のまま）。
        # 出力のみの追加 — 判定ロジックは動かさない。
        delta_iter = _spec_delta_iteration(root)
        if delta_iter is not None:
            print(f"[spec-delta] CHANGES.md 検査 OK（iteration={delta_iter}）")
        return 0

    # --- Phase order check ---
    if gate_name in DEV_PHASE_ORDER and phase in DEV_PHASE_ORDER:
        gate_idx = DEV_PHASE_ORDER.index(gate_name)
        phase_idx = DEV_PHASE_ORDER.index(phase)
        if phase_idx < gate_idx:
            print(f"ERROR: Cannot approve '{gate_name}' — current phase is '{phase}'.")
            print(f"       This gate requires reaching at least the '{gate_name}' phase.")
            return 1

    # --- Prerequisite gates check ---
    required_prior = list(PHASE_REQUIRES_GATES.get(gate_name, []))
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        allowed_phases = SIZE_ALLOWED_PHASES[task_size]
        required_prior = [g for g in required_prior if g in allowed_phases]
    for prereq in required_prior:
        prereq_val = approvals.get(prereq, "pending")
        if prereq_val not in ("approved", "n/a"):
            print(
                f"ERROR: Cannot approve '{gate_name}' — prerequisite gate "
                f"'{prereq}' is '{prereq_val}' (must be approved or n/a)."
            )
            return 1

    # --- Strict gate enforcement ---
    # feature/refactor/framework require specific prior gates to be approved
    # (not n/a) at certain phases. Uses STRICT_GATE_TASK_TYPES and
    # STRICT_GATE_BY_PHASE as source of truth (same as validate_status_file).
    if task_type in STRICT_GATE_TASK_TYPES and task_size != "S":
        strict_prereqs = list(STRICT_GATE_BY_PHASE.get(gate_name, []))
        if task_size and task_size in SIZE_ALLOWED_PHASES:
            allowed_phases = SIZE_ALLOWED_PHASES[task_size]
            strict_prereqs = [g for g in strict_prereqs if g in allowed_phases]
        for strict_gate in strict_prereqs:
            gate_val = approvals.get(strict_gate, "pending")
            if gate_val == "n/a":
                print(
                    f"ERROR: Cannot approve '{gate_name}' — task_type "
                    f"'{task_type}' requires gate '{strict_gate}' to be "
                    f"approved (not n/a)."
                )
                return 1

    return 0


def pre_approve_gate(gate_name: str, root: Path) -> int:
    """Check if a gate can be approved given current STATUS.md state.

    Returns tri-state: 0 = approvable, 1 = blocked (🔴), 2 = needs ack (🟡).
    Composes the deterministic prerequisite check (check_gate_prerequisites)
    with evidence-quality checks: the B1 test-strength drill (qa) and the B2
    judge card (review/qa/security/deploy). Uses PHASE_REQUIRES_GATES,
    SIZE_ALLOWED_PHASES, and gate_ref_mapping as the source of truth for the
    gate approval contracts. Called by update-gate.sh via --pre-approve-gate.
    """
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        print("ERROR: docs/STATUS.md not found")
        return 1

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        print("ERROR: docs/STATUS.md is missing YAML frontmatter")
        return 1

    phase = extract_scalar_value(frontmatter, "phase")
    task_type = extract_scalar_value(frontmatter, "task_type")
    task_size = extract_scalar_value(frontmatter, "task_size")
    approvals = extract_approval_map(frontmatter)
    refs = extract_current_refs(frontmatter)

    # --- Gate-ref consistency (approval-time ADVISORY) ---
    # Approval-time is advisory only; the invariant is ENFORCED at completion by
    # the TaskCompleted hook (check_status.py --check-completion-evidence).
    if gate_name in GATE_REF_MAPPING:
        ref_key = GATE_REF_MAPPING[gate_name]
        ref_value = refs.get(ref_key)
        ref_is_empty = ref_value is None or ref_value == "null" or ref_value == []
        if ref_is_empty:
            print(
                f"ADVISORY: Approving '{gate_name}' but "
                f"current_refs.{ref_key} is empty."
            )
            print(
                f"         Set current_refs.{ref_key} to the evidence file path; "
                f"it is enforced at completion by the TaskCompleted hook."
            )

    # --- Deterministic prerequisite gating (mode/phase/prereq/strict) ---
    prereq_rc = check_gate_prerequisites(
        gate_name, root, phase, task_type, task_size, approvals)
    if prereq_rc != 0:
        return prereq_rc

    # --- qa test-strength drill (B1, Approach A) ---
    # Run the drill LIVE at approval; the verdict cannot be forged or go stale.
    if gate_name == "qa":
        if run_qa_drill(root) != 0:
            return 1

    # --- B2 judge card (review/qa/security/deploy, tri-state) ---
    if gate_name in JUDGE_GATES:
        rc = run_judge_card(gate_name, root)
        if rc != 0:
            return rc  # 1=🔴 block / 2=🟡 needs ack

    return 0


def pre_na_gate(gate_name: str, root: Path) -> int:
    """Check if a gate can be set to n/a.

    Only brainstorm and plan gates support n/a, and only for bugfix/hotfix flows.
    feature/refactor/framework require brainstorm and plan to be actively approved.
    Returns 0 if allowed, 1 otherwise.
    Called by update-gate.sh via --pre-na-gate.
    """
    na_allowed_gates = {"brainstorm", "plan"}
    if gate_name not in na_allowed_gates:
        print(f"ERROR: Gate '{gate_name}' cannot be set to n/a.")
        print(f"       Only {sorted(na_allowed_gates)} support n/a.")
        return 1

    # Read task_type from STATUS.md — only bugfix/hotfix may skip brainstorm/plan.
    status_path = root / "docs" / "STATUS.md"
    if status_path.exists():
        content = status_path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
        if frontmatter:
            task_type = extract_scalar_value(frontmatter, "task_type") or ""
            na_allowed_task_types = {"bugfix", "hotfix"}
            if task_type and task_type not in na_allowed_task_types:
                print(f"ERROR: Cannot set '{gate_name}' to n/a for task_type '{task_type}'.")
                print(f"       Only {sorted(na_allowed_task_types)} task types may skip brainstorm/plan.")
                return 1

    return 0


def check_deploy_ready(root: Path) -> int:
    """Check if deploy commands are allowed given current gate state.

    Returns 0 if deploy is allowed, 1 otherwise.
    Reuses PHASE_REQUIRES_GATES, STRICT_GATE_BY_PHASE, and
    SIZE_ALLOWED_PHASES as the single source of truth for gate logic.
    Called by check-deploy-gate.sh via --check-deploy-ready.
    """
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        print("ERROR: docs/STATUS.md not found")
        return 1

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        print("ERROR: docs/STATUS.md is missing YAML frontmatter")
        return 1

    task_type = extract_scalar_value(frontmatter, "task_type")
    task_size = extract_scalar_value(frontmatter, "task_size")
    approvals = extract_approval_map(frontmatter)

    # If deploy phase is not in the allowed phases for this task size, the gate
    # has no inspection to run — surface that as ASK (human confirm), not a
    # silent allow (P2-3: size-skip means "phase skipped", not "deploy vetted").
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        if "deploy" not in SIZE_ALLOWED_PHASES[task_size]:
            print(f"ASK: task_size '{task_size}' は deploy フェーズをスキップする設定のため、"
                  "ゲート検査なしのデプロイになります。意図したデプロイであることを確認してください。")
            return 2

    # Check prerequisite gates for deploy phase.
    required_prior = list(PHASE_REQUIRES_GATES.get("deploy", []))
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        allowed_phases = SIZE_ALLOWED_PHASES[task_size]
        required_prior = [g for g in required_prior if g in allowed_phases]

    missing = []
    for prereq in required_prior:
        prereq_val = approvals.get(prereq, "pending")
        if prereq_val not in ("approved", "n/a"):
            missing.append(f"'{prereq}' is '{prereq_val}'")

    # Strict gate enforcement for feature/refactor/framework.
    if task_type in STRICT_GATE_TASK_TYPES and task_size != "S":
        strict_prereqs = list(STRICT_GATE_BY_PHASE.get("deploy", []))
        if task_size and task_size in SIZE_ALLOWED_PHASES:
            allowed_phases = SIZE_ALLOWED_PHASES[task_size]
            strict_prereqs = [g for g in strict_prereqs if g in allowed_phases]
        for strict_gate in strict_prereqs:
            gate_val = approvals.get(strict_gate, "pending")
            if gate_val == "n/a":
                missing.append(
                    f"'{strict_gate}' is 'n/a' (task_type '{task_type}' requires approved)"
                )

    if missing:
        print("ERROR: Deploy is blocked — prerequisite gates not met:")
        for m in missing:
            print(f"  - {m}")
        print("Approve required gates via /gate before deploying.")
        return 1

    return 0


def check_phase_transition(old_phase: str, new_phase: str, root: Path) -> int:
    """Validate that a phase transition is allowed.

    Returns 0 if transition is valid, 1 otherwise.
    Uses DEV_PHASE_ORDER, PHASE_REQUIRES_GATES, and SIZE_ALLOWED_PHASES
    as the single source of truth. Dev phases only.
    Called by post-status-audit.sh via --check-phase-transition.

    Rules:
    1. Cross-mode transitions require boundary gates.
    2. Non-Dev intra-mode phases: always allowed.
    3. Backward/same transitions: always allowed (rework).
    4. Forward transitions: must go to the NEXT allowed phase
       (per SIZE_ALLOWED_PHASES). Phase skipping is denied. A forward
       transition out of the task_size terminal phase (no allowed phase
       beyond old_phase) is explicitly denied.
    5. Prerequisite gates for the target phase must be met.
    """
    CLIENT_PHASES = MODE_PHASES["Client"]
    DEV_PHASES = MODE_PHASES["Dev"]

    # Cross-mode boundary checks.
    if old_phase in CLIENT_PHASES and new_phase in DEV_PHASES:
        # Client→Dev: client_ready_for_dev required.
        status_path = root / "docs" / "STATUS.md"
        if status_path.exists():
            text = read_text(status_path)
            fm = extract_frontmatter(text)
            if fm:
                approvals = extract_approval_map(fm)
                gate_val = approvals.get("client_ready_for_dev", "pending")
                if gate_val != "approved":
                    print(
                        f"ERROR: {old_phase}→{new_phase} crosses Client→Dev boundary."
                    )
                    print(
                        f"       Gate 'client_ready_for_dev' is '{gate_val}' "
                        f"(must be approved)."
                    )
                    return 1
        return 0

    if old_phase in DEV_PHASES and new_phase in CLIENT_PHASES:
        # Dev→Client: dev_ready_for_client required.
        status_path = root / "docs" / "STATUS.md"
        if status_path.exists():
            text = read_text(status_path)
            fm = extract_frontmatter(text)
            if fm:
                approvals = extract_approval_map(fm)
                gate_val = approvals.get("dev_ready_for_client", "pending")
                if gate_val != "approved":
                    print(
                        f"ERROR: {old_phase}→{new_phase} crosses Dev→Client boundary."
                    )
                    print(
                        f"       Gate 'dev_ready_for_client' is '{gate_val}' "
                        f"(must be approved)."
                    )
                    return 1
        return 0

    # Only validate Dev phase transitions (intra-mode).
    if old_phase not in DEV_PHASE_ORDER or new_phase not in DEV_PHASE_ORDER:
        return 0

    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        print("ERROR: docs/STATUS.md not found")
        return 1

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        print("ERROR: docs/STATUS.md is missing YAML frontmatter")
        return 1

    task_size = extract_scalar_value(frontmatter, "task_size")
    approvals = extract_approval_map(frontmatter)

    old_idx = DEV_PHASE_ORDER.index(old_phase)
    new_idx = DEV_PHASE_ORDER.index(new_phase)

    # Backward or same transitions: always allowed (rework).
    if new_idx <= old_idx:
        return 0

    # Forward transition: enforce adjacency.
    # Build the allowed phase list for this task_size, in order.
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        allowed = SIZE_ALLOWED_PHASES[task_size]
    else:
        allowed = set(DEV_PHASE_ORDER)

    # Find the next allowed phase after old_phase.
    allowed_after_old = [
        p for p in DEV_PHASE_ORDER
        if DEV_PHASE_ORDER.index(p) > old_idx and p in allowed
    ]

    if not allowed_after_old:
        # old_phase is the terminal allowed phase for this task_size — no forward
        # transition exists beyond it. Explicit deny (defense in depth): without
        # this, an empty allowed_after_old would skip the adjacency check and fall
        # through to the prerequisite gate check, which could pass spuriously.
        print(
            f"ERROR: Phase skip detected: {old_phase}→{new_phase}."
        )
        print(
            f"       '{old_phase}' is the terminal phase for task_size={task_size}; "
            f"no forward transition beyond it is allowed."
        )
        return 1

    if new_phase != allowed_after_old[0]:
        next_allowed = allowed_after_old[0]
        print(
            f"ERROR: Phase skip detected: {old_phase}→{new_phase}."
        )
        print(
            f"       Next allowed phase for task_size={task_size} is "
            f"'{next_allowed}'. Advance to '{next_allowed}' first."
        )
        return 1

    # Check that all prerequisite gates for new_phase are met.
    required_prior = list(PHASE_REQUIRES_GATES.get(new_phase, []))
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        allowed_phases = SIZE_ALLOWED_PHASES[task_size]
        required_prior = [g for g in required_prior if g in allowed_phases]

    missing = []
    for prereq in required_prior:
        prereq_val = approvals.get(prereq, "pending")
        if prereq_val not in ("approved", "n/a"):
            missing.append(f"'{prereq}' is '{prereq_val}'")

    if missing:
        print(
            f"ERROR: Phase transition {old_phase}→{new_phase} blocked — "
            f"prerequisite gates not met:"
        )
        for m in missing:
            print(f"  - {m}")
        print("Approve required gates via /gate before advancing phase.")
        return 1

    return 0


def check_status_health(root: Path) -> list[str]:
    """Check STATUS.md maintenance health. Returns list of warnings.

    Checks:
    1. Body Session History entry count (warn if > 10).
    2. external_evidence entry count (warn if >= 3).
    3. last_updated staleness (warn if > 7 days, exempt for docs/ship phase).

    Always returns warnings only — never blocks.
    """
    from datetime import datetime, timezone

    warnings: list[str] = []
    status_path = root / "docs" / "STATUS.md"
    if not status_path.exists():
        return []

    text = read_text(status_path)
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        return []

    # 1. Body Session History length check.
    body = text.split("---", 2)[-1] if text.count("---") >= 2 else ""
    history_match = re.search(
        r"## Session History\n(.*?)(?=\n## |\Z)", body, re.DOTALL
    )
    if history_match:
        history_lines = [
            line
            for line in history_match.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]
        if len(history_lines) > 10:
            warnings.append(
                f"Body Session History has {len(history_lines)} entries "
                f"(recommended: <=10). Consider archiving older entries."
            )

    # 2. External evidence count.
    evidence = extract_external_evidence(frontmatter)
    if len(evidence) >= 3:
        warnings.append(
            f"external_evidence has {len(evidence)} entries (max 3). "
            f"Archive older entries to docs/evidence-archive.md."
        )

    # 3. last_updated staleness.
    last_updated = extract_scalar_value(frontmatter, "last_updated")
    phase = extract_scalar_value(frontmatter, "phase")
    if last_updated and phase not in ("docs", "ship"):
        try:
            updated_str = last_updated.strip('"').strip("'")
            updated_dt = datetime.fromisoformat(
                updated_str.replace("Z", "+00:00")
            )
            # Ensure timezone-aware for comparison.
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_stale = (now - updated_dt).days
            if days_stale > 7:
                warnings.append(
                    f"last_updated is {days_stale} days old. "
                    f"Update last_updated in STATUS.md frontmatter."
                )
        except (ValueError, TypeError):
            pass

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root containing docs/STATUS.md")
    parser.add_argument("--strict", action="store_true",
                        help="Enable PyYAML cross-validation (requires PyYAML)")
    parser.add_argument("--pre-approve-gate", dest="pre_approve_gate", default=None,
                        help="Check if a gate can be approved (used by update-gate.sh)")
    parser.add_argument("--pre-na-gate", dest="pre_na_gate", default=None,
                        help="Check if a gate can be set to n/a (used by update-gate.sh)")
    parser.add_argument("--check-deploy-ready", dest="check_deploy_ready",
                        action="store_true",
                        help="Check if deploy commands are allowed (used by check-deploy-gate.sh)")
    parser.add_argument("--check-phase-transition", dest="check_phase_transition",
                        nargs=2, metavar=("OLD", "NEW"), default=None,
                        help="Validate a phase transition (used by post-status-audit.sh)")
    parser.add_argument("--check-status-health", dest="check_status_health",
                        action="store_true",
                        help="Check STATUS.md maintenance health (warnings only)")
    parser.add_argument("--check-completion-evidence", dest="check_completion_evidence",
                        action="store_true",
                        help="Check STATUS.md gate-ref evidence integrity at task "
                             "completion (used by check-task-completed.sh)")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    if args.pre_approve_gate:
        return pre_approve_gate(args.pre_approve_gate, root)

    if args.pre_na_gate:
        return pre_na_gate(args.pre_na_gate, root)

    if args.check_deploy_ready:
        return check_deploy_ready(root)

    if args.check_phase_transition:
        return check_phase_transition(
            args.check_phase_transition[0], args.check_phase_transition[1], root
        )

    if args.check_status_health:
        health_warnings = check_status_health(root)
        for w in health_warnings:
            print(f"HEALTH: {w}")
        return 0

    if args.check_completion_evidence:
        status_path = root / "docs" / "STATUS.md"
        # I2: fail-closed (symmetric with validate_status_file). A missing or
        # frontmatter-less STATUS.md means we cannot verify completion evidence,
        # so it must be a violation (exit 1) — not a silent PASS that an adversary
        # could trigger by deleting/corrupting STATUS.md before TaskCompleted.
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

    status_path = root / "docs" / "STATUS.md"
    failures = validate_status_file(status_path)

    if args.strict and status_path.exists():
        text = read_text(status_path)
        failures.extend(validate_with_pyyaml(text, status_path))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"PASS: status file is valid: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from check_status import validate_status_file


ROOT = Path(__file__).resolve().parents[1]

FRAMEWORK_VERSION = "1.0.0"

PROFILES_DIR = ROOT / "templates" / "profiles"
VALID_PROFILES = ["minimal", "standard", "full"]

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "CLAUDE.md",
    ROOT / "docs/STATUS.md",
    ROOT / "docs/LEARNINGS.md",
    ROOT / "docs/MIGRATION-FROM-v7.md",
    ROOT / "scripts/check_status.py",
    ROOT / "scripts/update-gate.sh",
    ROOT / "scripts/lint_names.py",
    ROOT / "scripts/check_framework_contract.py",
    ROOT / "scripts/retro_report.py",
    ROOT / "scripts/run_eval.py",
    ROOT / "scripts/status_doctor.py",
]

REQUIRED_AGENT_FILES = [
    ROOT / ".claude/agents/planner.md",
    ROOT / ".claude/agents/implementer.md",
    ROOT / ".claude/agents/reviewer.md",
    ROOT / ".claude/agents/qa.md",
    ROOT / ".claude/agents/qa-browser.md",
    ROOT / ".claude/agents/security.md",
    ROOT / ".claude/agents/ui.md",
    ROOT / ".claude/agents/reviewer-testing.md",
    ROOT / ".claude/agents/reviewer-performance.md",
    ROOT / ".claude/agents/reviewer-maintainability.md",
    ROOT / ".claude/agents/translation-specialist.md",
    ROOT / ".claude/agents/integration-specialist.md",
]

REQUIRED_SKILL_FILES = [
    # v0.13.0 Phase 0b: aegis-* に改名（公式同名スキル衝突回避）
    ROOT / ".claude/skills/aegis-brainstorm/SKILL.md",
    ROOT / ".claude/skills/bug-diagnosis/SKILL.md",
    ROOT / ".claude/skills/tdd/SKILL.md",
    ROOT / ".claude/skills/subagent-dev/SKILL.md",
    ROOT / ".claude/skills/deploy/SKILL.md",
    ROOT / ".claude/skills/deploy/platforms.md",
    ROOT / ".claude/skills/client-workflow/SKILL.md",
    ROOT / ".claude/skills/session-recovery/SKILL.md",
    ROOT / ".claude/skills/ship-and-docs/SKILL.md",
    ROOT / ".claude/skills/aegis-review-gate/SKILL.md",
    ROOT / ".claude/skills/aegis-security-gate/SKILL.md",
    ROOT / ".claude/skills/docs-sync/SKILL.md",
    ROOT / ".claude/skills/qa-verification/SKILL.md",
    ROOT / ".claude/skills/translation-mapping/SKILL.md",
    ROOT / ".claude/skills/integration-assist/SKILL.md",
    ROOT / ".claude/skills/browser-assist/SKILL.md",
]

REQUIRED_RULES_FILES = [
    ROOT / ".claude/rules/state-machine.md",
    ROOT / ".claude/rules/routing.md",
]

REQUIRED_COMMAND_FILES = [
    ROOT / ".claude/commands/status.md",
    ROOT / ".claude/commands/gate.md",
    ROOT / ".claude/commands/recover.md",
    ROOT / ".claude/commands/validate.md",
    ROOT / ".claude/commands/next.md",
    ROOT / ".claude/commands/tutorial.md",
    ROOT / ".claude/commands/retro.md",
]

REQUIRED_TEMPLATE_FILES = [
    ROOT / "templates/CLAUDE.template.md",
    ROOT / "templates/STATUS.template.md",
    ROOT / "templates/PRD.template.md",
    ROOT / "templates/SCOPE.template.md",
    ROOT / "templates/NFR.template.md",
    ROOT / "templates/ACCEPTANCE.template.md",
    ROOT / "templates/PLAN.template.md",
    ROOT / "templates/SPEC.template.md",
    ROOT / "templates/REVIEW.template.md",
    ROOT / "templates/QA-REPORT.template.md",
    ROOT / "templates/SECURITY-REVIEW.template.md",
    ROOT / "templates/HANDOVER-TO-DEV.template.md",
    ROOT / "templates/HANDOVER-TO-CLIENT.template.md",
    ROOT / "templates/LEARNINGS.template.md",
    ROOT / "templates/BRAINSTORM-RECORD.template.md",
    ROOT / "templates/VERIFICATION.template.md",
    ROOT / "templates/DEPLOY-CHECKLIST.template.md",
    ROOT / "templates/SECOND-OPINION.template.md",
    ROOT / "templates/CLIENT-CONTEXT.template.md",
    ROOT / "templates/CLIENT-GLOSSARY.template.md",
    ROOT / "templates/CLIENT-OPEN-QUESTIONS.template.md",
    ROOT / "templates/TRANSLATION-MAPPING.template.md",
    ROOT / "templates/DECISION.template.md",
    ROOT / "templates/hooks.template.json",
]

REQUIRED_HOOK_FILES = [
    ROOT / "hooks/session-start.sh",
    ROOT / "hooks/check-gate.sh",
    ROOT / "hooks/check-destructive.sh",
    ROOT / "hooks/check-tdd.sh",
    ROOT / "hooks/post-bash.sh",
    ROOT / "hooks/post-status-audit.sh",
    ROOT / "hooks/pre-compact.sh",
    ROOT / "hooks/check-control-plane.sh",
    ROOT / "hooks/lib/extract-input.sh",
    ROOT / "hooks/check-client-info.sh",
    ROOT / "hooks/check-secrets.sh",
    ROOT / "hooks/check-deploy-gate.sh",
    ROOT / "hooks/check-deploy-mcp-gate.sh",
]

REQUIRED_EXAMPLE_FILES = [
    ROOT / "examples/minimal-project/CLAUDE.md",
    ROOT / "examples/minimal-project/README.md",
    ROOT / "examples/minimal-project/.claude/settings.json",
    ROOT / "examples/minimal-project/docs/STATUS.md",
    ROOT / "examples/minimal-project/docs/LEARNINGS.md",
    ROOT / "examples/minimal-project/docs/requirements/PRD.md",
    ROOT / "examples/minimal-project/docs/requirements/SCOPE.md",
    ROOT / "examples/minimal-project/docs/requirements/NFR.md",
    ROOT / "examples/minimal-project/docs/requirements/ACCEPTANCE.md",
    ROOT / "examples/minimal-project/docs/handover/TO-DEV.md",
    ROOT / "examples/minimal-project/docs/handover/TO-CLIENT.md",
    ROOT / "examples/minimal-project/docs/specs/search-brainstorm-record.md",
    ROOT / "examples/minimal-project/docs/specs/search-design.md",
    ROOT / "examples/minimal-project/docs/plans/search-implementation-plan.md",
    ROOT / "examples/minimal-project/docs/qa-reports/search-review.md",
    ROOT / "examples/minimal-project/docs/qa-reports/search-qa.md",
    ROOT / "examples/minimal-project/docs/qa-reports/search-security.md",
    ROOT / "examples/minimal-project/docs/qa-reports/search-verification.md",
    ROOT / "examples/minimal-project/docs/qa-reports/search-deploy-checklist.md",
    # Native .claude structures (Phase 2 v0.6.0)
    ROOT / "examples/minimal-project/.claude/rules/state-machine.md",
    ROOT / "examples/minimal-project/.claude/rules/routing.md",
    ROOT / "examples/minimal-project/.claude/commands/status.md",
    ROOT / "examples/minimal-project/.claude/commands/gate.md",
    ROOT / "examples/minimal-project/.claude/commands/next.md",
    ROOT / "examples/minimal-project/.claude/commands/recover.md",
    ROOT / "examples/minimal-project/.claude/commands/validate.md",
    ROOT / "examples/minimal-project/.claude/commands/retro.md",
    ROOT / "examples/minimal-project/.claude/commands/tutorial.md",
    ROOT / "examples/minimal-project/.claude/agents/planner.md",
    ROOT / "examples/minimal-project/.claude/agents/implementer.md",
    ROOT / "examples/minimal-project/.claude/agents/reviewer.md",
    ROOT / "examples/minimal-project/.claude/agents/qa.md",
    ROOT / "examples/minimal-project/.claude/agents/qa-browser.md",
    ROOT / "examples/minimal-project/.claude/agents/security.md",
    ROOT / "examples/minimal-project/.claude/agents/ui.md",
    ROOT / "examples/minimal-project/.claude/agents/reviewer-testing.md",
    ROOT / "examples/minimal-project/.claude/agents/reviewer-performance.md",
    ROOT / "examples/minimal-project/.claude/agents/reviewer-maintainability.md",
    ROOT / "examples/minimal-project/scripts/update-gate.sh",
    ROOT / "examples/minimal-project/scripts/check_status.py",
    # Runtime enforcement hooks (referenced by .claude/settings.json)
    ROOT / "examples/minimal-project/hooks/session-start.sh",
    ROOT / "examples/minimal-project/hooks/check-gate.sh",
    ROOT / "examples/minimal-project/hooks/check-destructive.sh",
    ROOT / "examples/minimal-project/hooks/check-tdd.sh",
    ROOT / "examples/minimal-project/hooks/post-bash.sh",
    ROOT / "examples/minimal-project/hooks/post-status-audit.sh",
    ROOT / "examples/minimal-project/hooks/pre-compact.sh",
    ROOT / "examples/minimal-project/hooks/check-control-plane.sh",
    ROOT / "examples/minimal-project/hooks/lib/extract-input.sh",
    ROOT / "examples/minimal-project/docs/client/context.md",
    ROOT / "examples/minimal-project/docs/client/glossary.md",
    ROOT / "examples/minimal-project/docs/client/open-questions.md",
    ROOT / "examples/minimal-project/docs/translation/mapping.md",
    ROOT / "examples/minimal-project/hooks/check-client-info.sh",
    ROOT / "examples/minimal-project/hooks/check-secrets.sh",
    ROOT / "examples/minimal-project/hooks/check-deploy-gate.sh",
    ROOT / "examples/minimal-project/hooks/check-deploy-mcp-gate.sh",
    ROOT / "examples/minimal-project/.claude/agents/translation-specialist.md",
    ROOT / "examples/minimal-project/.claude/agents/integration-specialist.md",
]

# Example skill directories — check SKILL.md exists in each.
# v0.13.0 Phase 0b: brainstorming/review/security-review を aegis-* に改名
REQUIRED_EXAMPLE_SKILL_DIRS = [
    "aegis-brainstorm", "bug-diagnosis", "client-workflow", "deploy",
    "docs-sync", "qa-verification", "aegis-review-gate", "aegis-security-gate",
    "session-recovery", "ship-and-docs", "subagent-dev", "tdd",
    "translation-mapping",
    "integration-assist",
    "browser-assist",
]

# Legacy skill files that should NOT exist (migrated to .claude/skills/ in v0.6.0).
LEGACY_SKILL_DIR = ROOT / "docs/skills"

REQUIRED_CLAUDE_HEADINGS = [
    "## Operating Contract",
    "## Session Start",
    "## State Machine",
    "## Routing",
    "## Context Budget Policy",
    "## Skills",
    "## Source of Truth",
    "## Completion Rule",
]

# Keep the kernel below 650 words. The budget accounts for the mode/phase/gate
# model, the deploy phase, iteration support, the Skills directory listing,
# and the Project Overrides section in the template variant.
MAX_CLAUDE_WORDS = 650

# Template placeholder pattern: <記入>, <topic>, <docs/requirements/ のパス>, etc.
# Matches angle-bracket tokens that look like fill-in markers.
PLACEHOLDER_PATTERN = re.compile(r"<[A-Za-z\u3000-\u9FFF/ \-\.,:\d_]{1,40}>")

# Placeholders that are legitimate in example files (not fill-in markers).
PLACEHOLDER_ALLOWLIST = {
    "<topic>",
    "<パス>",
    "<gate>",
    "<gate-name>",
    # Python source code tokens (docstrings/comments in check_status.py etc.)
    "<body>",
    "<key>",
    "<value>",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
_VERSION_ID_RE = re.compile(r"claude-[\w-]*\d")
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
        for name, (exp_model, exp_effort) in MODEL_EFFORT_POLICY.items():
            path = agents_dir / name
            if not path.exists():
                failures.append(f"model-policy: missing {path.relative_to(ROOT)}")
                continue
            fm = _frontmatter_section(read_text(path))
            mm = re.search(r"^model:\s*(\S+)", fm, re.MULTILINE)
            em = re.search(r"^effort:\s*(\S+)", fm, re.MULTILINE)
            model = mm.group(1).strip("\"'") if mm else None
            effort = em.group(1).strip("\"'") if em else None
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
        for path in sorted(agents_dir.glob("*.md")):
            if path.name not in MODEL_EFFORT_POLICY:
                failures.append(
                    f"model-policy: {path.relative_to(ROOT)} not classified in MODEL_EFFORT_POLICY (assign a tier)"
                )
    return failures


def check_agent_names(roots) -> list:
    """全 agent が frontmatter `name:` を持ち、値がファイル名 stem と一致することを検証。"""
    failures = []
    for base in roots:
        agents_dir = base / ".claude/agents"
        if not agents_dir.exists():
            continue
        for path in sorted(agents_dir.glob("*.md")):
            fm = _frontmatter_section(read_text(path))
            nm = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
            rel = path.relative_to(ROOT)
            if not nm:
                failures.append(f"agent-name: {rel} missing name in frontmatter")
                continue
            name = nm.group(1).strip("\"'")
            if name != path.stem:
                failures.append(f"agent-name: {rel} name={name} expected {path.stem} (must match filename)")
    return failures


def word_count(text: str) -> int:
    return len(text.split())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate aegis contract",
    )
    parser.add_argument(
        "--profile",
        choices=VALID_PROFILES,
        default=None,
        help="Validation profile (minimal/standard/full). "
        "Omit for full framework check.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root to validate (default: framework repo root).",
    )
    return parser.parse_args()


def run_profile_check(profile_name: str, project_root: Path) -> int:
    """Run profile-based validation against a project root."""
    profile_path = PROFILES_DIR / f"{profile_name}.json"
    if not profile_path.exists():
        print(f"ERROR: profile definition not found: {profile_path}")
        return 1

    profile = json.loads(read_text(profile_path))
    required_files: list[str] = profile.get("required", [])
    recommended_files: list[str] = profile.get("recommended", [])
    required_hook_scripts: list[str] = profile.get("required_hook_scripts", [])

    failures: list[str] = []
    warnings: list[str] = []

    # --- File existence checks ---
    for rel_path in required_files:
        if not (project_root / rel_path).exists():
            failures.append(f"missing required file: {rel_path}")

    for rel_path in recommended_files:
        if not (project_root / rel_path).exists():
            # settings.local.json is an accepted alternative to settings.json.
            if rel_path == ".claude/settings.json":
                if (project_root / ".claude" / "settings.local.json").exists():
                    continue
            warnings.append(f"missing recommended file: {rel_path}")

    # --- CLAUDE.md structural checks ---
    claude_path = project_root / "CLAUDE.md"
    if "CLAUDE.md" in required_files and claude_path.exists():
        text = read_text(claude_path)
        for heading in REQUIRED_CLAUDE_HEADINGS:
            if heading not in text:
                failures.append(f"CLAUDE.md is missing heading: {heading}")
        count = word_count(text)
        if count > MAX_CLAUDE_WORDS:
            failures.append(
                f"CLAUDE.md is too large: {count} words > {MAX_CLAUDE_WORDS}"
            )

    # --- STATUS.md validation ---
    status_path = project_root / "docs" / "STATUS.md"
    if "docs/STATUS.md" in required_files and status_path.exists():
        failures.extend(validate_status_file(status_path))

    # --- settings hook registration (standard profile) ---
    # Check both settings.json and settings.local.json (Quick Start recommends
    # settings.local.json for real projects).
    if required_hook_scripts:
        settings_candidates = [
            project_root / ".claude" / "settings.json",
            project_root / ".claude" / "settings.local.json",
        ]
        settings_path = None
        for candidate in settings_candidates:
            if candidate.exists():
                settings_path = candidate
                break
        if settings_path is not None:
            try:
                settings_data = json.loads(read_text(settings_path))
            except json.JSONDecodeError as e:
                failures.append(
                    f"{settings_path.relative_to(project_root)} is not valid JSON: {e}"
                )
                settings_data = {}
            hooks_config = (
                settings_data.get("hooks", {})
                if isinstance(settings_data, dict)
                else {}
            )
            registered_commands: list[str] = []
            for event_entries in hooks_config.values():
                if not isinstance(event_entries, list):
                    continue
                for entry in event_entries:
                    if not isinstance(entry, dict):
                        continue
                    for hook in entry.get("hooks", []):
                        if isinstance(hook, dict):
                            cmd = hook.get("command", "")
                            if isinstance(cmd, str) and cmd:
                                registered_commands.append(cmd)
            settings_rel = settings_path.relative_to(project_root)
            for script in required_hook_scripts:
                if not any(script in cmd for cmd in registered_commands):
                    failures.append(
                        f"{settings_rel} missing hook registration: {script}"
                    )
        else:
            warnings.append(
                ".claude/settings.json (or settings.local.json) not found"
                " — recommended hooks are not registered"
            )

    # --- Report ---
    for w in warnings:
        print(f"WARNING: {w}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(f"PASS: project contract is aligned (profile: {profile_name})")
    return 0


def main() -> int:
    args = parse_args()

    if args.profile is not None and args.profile != "full":
        project_root = args.root.resolve() if args.root else ROOT
        return run_profile_check(args.profile, project_root)

    if args.profile == "full" and args.root is not None:
        print(
            "ERROR: --profile=full always validates the framework repo root."
        )
        print(
            "       Use --profile=minimal or --profile=standard with --root."
        )
        return 1

    # --- Full framework check (always uses framework repo root) ---
    # NOTE: --root is intentionally ignored in full mode because REQUIRED_*
    # paths are computed at module level from ROOT.  run_eval.py passes --root
    # but it always equals ROOT, so the ignored argument is harmless.
    failures: list[str] = []

    for path in REQUIRED_FILES + REQUIRED_AGENT_FILES + REQUIRED_SKILL_FILES + REQUIRED_RULES_FILES + REQUIRED_COMMAND_FILES + REQUIRED_TEMPLATE_FILES + REQUIRED_HOOK_FILES + REQUIRED_EXAMPLE_FILES:
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")

    # Detect legacy skill files in docs/skills/ (migrated to .claude/skills/ in v0.6.0).
    if LEGACY_SKILL_DIR.is_dir():
        for legacy_file in sorted(LEGACY_SKILL_DIR.glob("*.md")):
            failures.append(
                f"legacy skill file found: {legacy_file.relative_to(ROOT)}"
                " (skills migrated to .claude/skills/ in v0.6.0 — delete this file)"
            )

    # Example project skill directories must each contain SKILL.md.
    for skill_name in REQUIRED_EXAMPLE_SKILL_DIRS:
        skill_file = ROOT / "examples/minimal-project/.claude/skills" / skill_name / "SKILL.md"
        if not skill_file.exists():
            failures.append(f"missing example skill: {skill_file.relative_to(ROOT)}")

    for path in [
        ROOT / "CLAUDE.md",
        ROOT / "templates/CLAUDE.template.md",
        ROOT / "examples/minimal-project/CLAUDE.md",
    ]:
        if not path.exists():
            continue
        text = read_text(path)
        for heading in REQUIRED_CLAUDE_HEADINGS:
            if heading not in text:
                failures.append(f"{path.relative_to(ROOT)} is missing heading: {heading}")
        count = word_count(text)
        if count > MAX_CLAUDE_WORDS:
            failures.append(
                f"{path.relative_to(ROOT)} is too large: {count} words > {MAX_CLAUDE_WORDS}"
            )
        if path.name in {"CLAUDE.template.md", "CLAUDE.md"} and path != ROOT / "CLAUDE.md" and "## Project Overrides" not in text:
            failures.append(f"{path.relative_to(ROOT)} is missing heading: ## Project Overrides")
        # No CLAUDE.md variant should reference the old docs/skills/ path.
        if "docs/skills/" in text:
            failures.append(
                f"{path.relative_to(ROOT)} contains legacy docs/skills/ path reference"
                " (skills are now in .claude/skills/)"
            )

    # Template word count limits to prevent bloat.
    TEMPLATE_WORD_LIMITS = {
        ROOT / "templates/PLAN.template.md": 400,
        ROOT / "templates/SECURITY-REVIEW.template.md": 150,
        ROOT / "templates/VERIFICATION.template.md": 120,
    }
    for tpl_path, limit in TEMPLATE_WORD_LIMITS.items():
        if tpl_path.exists():
            tpl_count = word_count(read_text(tpl_path))
            if tpl_count > limit:
                failures.append(
                    f"{tpl_path.relative_to(ROOT)} is too large: {tpl_count} words > {limit}"
                )

    # Failure rule sync check: the block starting with "Stop after 3 failures"
    # must be identical across all CLAUDE.md variants.
    claude_paths = [
        ROOT / "CLAUDE.md",
        ROOT / "templates/CLAUDE.template.md",
        ROOT / "examples/minimal-project/CLAUDE.md",
    ]
    failure_rules: dict[str, str] = {}
    for path in claude_paths:
        if not path.exists():
            continue
        text = read_text(path)
        lines = text.split("\n")
        start = None
        end = None
        for i, line in enumerate(lines):
            if "Stop after 3 failures" in line:
                start = i
            elif start is not None and i > start and line.startswith("- "):
                end = i
                break
        if start is not None:
            block = "\n".join(lines[start : end if end else len(lines)])
            failure_rules[str(path.relative_to(ROOT))] = block
        else:
            failures.append(
                f"{path.relative_to(ROOT)} missing failure rule ('Stop after 3 failures')"
            )
    if len(set(failure_rules.values())) > 1:
        failures.append(
            "failure rule is out of sync across CLAUDE.md variants: "
            + ", ".join(failure_rules.keys())
        )

    for path in [ROOT / "docs/STATUS.md", ROOT / "examples/minimal-project/docs/STATUS.md"]:
        if path.exists():
            failures.extend(validate_status_file(path))

    readme_path = ROOT / "README.md"
    if readme_path.exists():
        readme = read_text(readme_path)
        for token in [
            "python3 scripts/check_framework_contract.py",
            "python3 scripts/check_status.py --root .",
        ]:
            if token not in readme:
                failures.append(f"README.md is missing validation command: {token}")
        if "/Users/" in readme:
            failures.append("README.md contains machine-specific absolute paths")

    # Hook template validation: verify that hooks.template.json registers
    # all required hook scripts in the correct event sections.
    hooks_template_path = ROOT / "templates/hooks.template.json"
    if hooks_template_path.exists():
        try:
            hooks_data = json.loads(read_text(hooks_template_path))
        except json.JSONDecodeError as e:
            failures.append(f"hooks.template.json is not valid JSON: {e}")
            hooks_data = {}
        if not isinstance(hooks_data, dict):
            failures.append("hooks.template.json top-level value is not an object")
            hooks_data = {}
        hooks_config = hooks_data.get("hooks", {})
        if not isinstance(hooks_config, dict):
            failures.append("hooks.template.json 'hooks' value is not an object")
            hooks_config = {}
        # Derive required hook scripts from REQUIRED_HOOK_FILES (single source of truth).
        # lib/ helpers are not directly registered in hooks.template.json.
        required_hook_scripts = {
            p.name
            for p in REQUIRED_HOOK_FILES
            if p.parent == ROOT / "hooks" and p.suffix == ".sh"
        }
        # Collect all registered scripts from hooks.template.json.
        registered_scripts: set[str] = set()
        for event_name, event_entries in hooks_config.items():
            if not isinstance(event_entries, list):
                failures.append(
                    f"hooks.template.json {event_name} value is not an array"
                )
                continue
            for entry in event_entries:
                if not isinstance(entry, dict):
                    failures.append(
                        f"hooks.template.json {event_name} contains non-object entry"
                    )
                    continue
                hooks_list = entry.get("hooks", [])
                if not isinstance(hooks_list, list):
                    failures.append(
                        f"hooks.template.json {event_name} entry 'hooks' is not an array"
                    )
                    continue
                for hook in hooks_list:
                    if not isinstance(hook, dict):
                        failures.append(
                            f"hooks.template.json {event_name} hook entry is not an object"
                        )
                        continue
                    cmd = hook.get("command", "")
                    if not isinstance(cmd, str):
                        failures.append(
                            f"hooks.template.json {event_name} hook command is not a string"
                        )
                        continue
                    if cmd:
                        # Extract script name from "bash hooks/script-name.sh"
                        parts = cmd.rsplit("/", 1)
                        if len(parts) == 2:
                            registered_scripts.add(parts[-1])
        # Check that every required hook is registered in the template.
        for script in sorted(required_hook_scripts - registered_scripts):
            failures.append(
                f"hooks/{script} is in REQUIRED_HOOK_FILES but not registered "
                f"in hooks.template.json"
            )

    # Session-start hook must detect docs/second-opinion.md (PaC for failure rule).
    session_start_path = ROOT / "hooks/session-start.sh"
    if session_start_path.exists():
        session_start_text = read_text(session_start_path)
        if "second-opinion" not in session_start_text:
            failures.append(
                "hooks/session-start.sh missing second-opinion.md detection"
                " (required for failure rule PaC)"
            )

    # Agent structure validation: CSO description, rationalization tables,
    # hallucination guard boundaries, and technical constraints.
    CORE_AGENT_FILES = [
        ROOT / ".claude/agents/planner.md",
        ROOT / ".claude/agents/implementer.md",
        ROOT / ".claude/agents/reviewer.md",
        ROOT / ".claude/agents/qa.md",
        ROOT / ".claude/agents/security.md",
        ROOT / ".claude/agents/ui.md",
    ]
    # Agents that must not modify files (readOnly: true in frontmatter).
    READ_ONLY_AGENT_FILES = {
        ROOT / ".claude/agents/planner.md",
        ROOT / ".claude/agents/reviewer.md",
        ROOT / ".claude/agents/qa.md",
        ROOT / ".claude/agents/security.md",
        ROOT / ".claude/agents/reviewer-testing.md",
        ROOT / ".claude/agents/reviewer-performance.md",
        ROOT / ".claude/agents/reviewer-maintainability.md",
    }
    for path in REQUIRED_AGENT_FILES:
        if not path.exists():
            continue
        text = read_text(path)
        rel = path.relative_to(ROOT)
        # All agents must have CSO-format description.
        if 'description: "Trigger:' not in text:
            failures.append(f"{rel} missing CSO description (must start with 'Trigger:')")
        # All agents must have hallucination guard boundary.
        if "do not claim completion without" not in text:
            failures.append(f"{rel} missing hallucination guard boundary")
        # Core agents must have rationalization table.
        if path in CORE_AGENT_FILES and "## Known Rationalizations" not in text:
            failures.append(f"{rel} missing rationalization table (## Known Rationalizations)")
        # All agents must have maxTurns in frontmatter with matching boundary rule.
        # Scope regex to YAML frontmatter (between first --- pair) and body respectively.
        fm_match = re.match(r"---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
        frontmatter_section = fm_match.group(1) if fm_match else ""
        body_section = text[fm_match.end():] if fm_match else text
        frontmatter_turns = re.search(r"maxTurns:\s*(\d+)", frontmatter_section)
        # Scope turn-limit search to ## Boundaries section only.
        boundaries_match = re.search(
            r"## Boundaries\b(.*?)(?=\n## |\Z)", body_section, re.DOTALL
        )
        boundaries_section = boundaries_match.group(1) if boundaries_match else ""
        boundary_turns = re.search(r"complete within (\d+) turns", boundaries_section)
        if not frontmatter_turns:
            failures.append(f"{rel} missing maxTurns in frontmatter")
        if not boundary_turns:
            failures.append(f"{rel} missing turn limit boundary rule ('complete within N turns')")
        if frontmatter_turns and boundary_turns:
            fm_val = int(frontmatter_turns.group(1))
            bd_val = int(boundary_turns.group(1))
            if fm_val != bd_val:
                failures.append(
                    f"{rel} maxTurns mismatch: frontmatter={fm_val}, boundary={bd_val}"
                )
        # Read-only agents must have readOnly frontmatter and boundary rule.
        if path in READ_ONLY_AGENT_FILES:
            if "readOnly: true" not in text:
                failures.append(f"{rel} missing readOnly: true in frontmatter")
            if "do not use Edit, Write, or Bash commands that modify files" not in text:
                failures.append(f"{rel} missing read-only boundary rule")
        # All agents must have enriched frontmatter fields.
        for field in ["model:", "permissionMode:", "effort:", "color:"]:
            if field not in frontmatter_section:
                failures.append(f"{rel} missing {field.rstrip(':')} in frontmatter")

    # Skill SKILL.md validation: name and description required in frontmatter.
    for path in REQUIRED_SKILL_FILES:
        if not path.exists() or not path.name.endswith("SKILL.md"):
            continue
        text = read_text(path)
        rel = path.relative_to(ROOT)
        fm_match = re.match(r"---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
        if not fm_match:
            failures.append(f"{rel} missing YAML frontmatter")
            continue
        fm = fm_match.group(1)
        for field in ["name:", "description:"]:
            if field not in fm:
                failures.append(f"{rel} missing {field.rstrip(':')} in frontmatter")

    # Command frontmatter validation: description and allowed-tools required.
    for path in REQUIRED_COMMAND_FILES:
        if not path.exists():
            continue
        text = read_text(path)
        rel = path.relative_to(ROOT)
        fm_match = re.match(r"---\s*\r?\n(.*?)\r?\n---", text, re.DOTALL)
        if not fm_match:
            failures.append(f"{rel} missing YAML frontmatter")
            continue
        fm = fm_match.group(1)
        for field in ["description:", "allowed-tools:"]:
            if field not in fm:
                failures.append(f"{rel} missing {field.rstrip(':')} in frontmatter")

    # Example settings.json → hooks integrity: every hook command referenced in
    # settings.json must have its script file present in the example project.
    example_settings_path = ROOT / "examples/minimal-project/.claude/settings.json"
    if example_settings_path.exists():
        try:
            example_settings = json.loads(read_text(example_settings_path))
        except json.JSONDecodeError as e:
            failures.append(f"example settings.json is not valid JSON: {e}")
            example_settings = {}
        example_hooks = example_settings.get("hooks", {}) if isinstance(example_settings, dict) else {}
        for event, entries in example_hooks.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                for hook in entry.get("hooks", []):
                    if not isinstance(hook, dict):
                        continue
                    cmd = hook.get("command", "")
                    if not isinstance(cmd, str) or not cmd:
                        continue
                    # Extract script path from command (e.g. "bash hooks/foo.sh" → "hooks/foo.sh")
                    parts = cmd.split()
                    script_rel = parts[1] if len(parts) >= 2 and parts[0] == "bash" else parts[0]
                    script_path = ROOT / "examples/minimal-project" / script_rel
                    if not script_path.exists():
                        failures.append(
                            f"example settings.json references missing hook: {script_rel}"
                            f" (event: {event})"
                        )

    # Version sync: STATUS.md template and FRAMEWORK_VERSION constant must agree.
    status_template_path = ROOT / "templates/STATUS.template.md"
    if status_template_path.exists():
        st_text = read_text(status_template_path)
        version_match = re.search(r'framework_version:\s*"([^"]+)"', st_text)
        if version_match:
            tpl_ver = version_match.group(1)
            if tpl_ver != FRAMEWORK_VERSION:
                failures.append(
                    f"templates/STATUS.template.md version ({tpl_ver}) != "
                    f"FRAMEWORK_VERSION ({FRAMEWORK_VERSION})"
                )
        else:
            failures.append("templates/STATUS.template.md missing framework_version")

    # LEARNINGS.md lint: check format and multiline for high-confidence entries.
    # Only applied to framework repo and example (not enforced on general projects).
    LEARNINGS_LINT_TARGETS = [
        ROOT / "docs/LEARNINGS.md",
        ROOT / "examples/minimal-project/docs/LEARNINGS.md",
    ]
    LEARNINGS_ENTRY_PATTERN = re.compile(
        r"^[^\S\n]*-[^\S\n]*\[confidence:(\d+)\]"
    )
    for learnings_path in LEARNINGS_LINT_TARGETS:
        if not learnings_path.exists():
            continue
        lines = read_text(learnings_path).splitlines()
        rel = learnings_path.relative_to(ROOT)
        for i, line in enumerate(lines, start=1):
            m = LEARNINGS_ENTRY_PATTERN.match(line)
            if not m:
                continue
            confidence = int(m.group(1))
            # Check that ] is followed by a space and content on the same line.
            if not re.search(r"\]\s+\S", line):
                failures.append(
                    f"{rel}:{i} learning entry has no content after [confidence:{confidence}]"
                )
            # Check that high-confidence entries (>=8) are single-line.
            if confidence >= 8 and i < len(lines):
                next_line = lines[i]  # 0-indexed lines[i] is line i+1
                if next_line and not next_line.startswith("#") and not next_line.startswith("<!--"):
                    # Continuation line: starts with whitespace but not a new entry or heading.
                    if re.match(r"^\s+\S", next_line) and not LEARNINGS_ENTRY_PATTERN.match(next_line):
                        failures.append(
                            f"{rel}:{i} high-confidence learning (confidence:{confidence}) "
                            "spans multiple lines (must be single-line for session-start hook extraction)"
                        )

    # Check example project files for leftover template placeholders.
    for path in REQUIRED_EXAMPLE_FILES:
        if not path.exists():
            continue
        text = read_text(path)
        for match in PLACEHOLDER_PATTERN.finditer(text):
            token = match.group(0)
            if token not in PLACEHOLDER_ALLOWLIST:
                failures.append(
                    f"{path.relative_to(ROOT)} contains template placeholder: {token}"
                )

    # --- Name cross-reference lint ---
    try:
        lint_result = subprocess.run(
            ["python3", str(ROOT / "scripts/lint_names.py"), "--root", str(ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        failures.append("name-lint: timed out after 30 seconds")
        lint_result = None
    if lint_result is not None and lint_result.returncode != 0:
        stdout_lines = lint_result.stdout.strip().splitlines()
        if stdout_lines:
            for line in stdout_lines:
                failures.append(f"name-lint: {line}")
        else:
            # Crash with no stdout — include stderr or generic message.
            stderr_msg = lint_result.stderr.strip()
            if stderr_msg:
                failures.append(f"name-lint: crashed: {stderr_msg[:200]}")
            else:
                failures.append("name-lint: exited with non-zero status but produced no output")

    failures.extend(check_model_effort_policy(MODEL_POLICY_ROOTS))
    failures.extend(check_agent_names(MODEL_POLICY_ROOTS))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("PASS: aegis contract is aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

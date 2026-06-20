#!/usr/bin/env python3
"""Reference drift auto-lint for Aegis.

Detects name/count/path mismatches between documentation surfaces and
actual files.  Exits 1 on any FAIL, 0 on WARNING-only or clean.

Usage:
    python3 scripts/check_reference_drift.py [--root <framework_root>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Some tests load this module via importlib.spec_from_file_location without
# putting scripts/ on sys.path. Self-bootstrap so `platform_manifest` resolves
# regardless of how we are loaded (idempotent: avoid stacking duplicate entries).
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from platform_manifest import (  # noqa: E402  (import follows sys.path bootstrap)
    KNOWN_HOOK_EVENTS,
    KNOWN_TOOL_NAMES,
    TOOL_MATCHING_EVENTS,
    stale_keys,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _glob_stems(directory: Path, pattern: str) -> set[str]:
    """Return stem names of files matching *pattern* under *directory*."""
    return {p.stem for p in directory.glob(pattern)} if directory.is_dir() else set()


def _glob_dir_names(directory: Path) -> set[str]:
    """Return names of immediate child directories that contain SKILL.md."""
    if not directory.is_dir():
        return set()
    return {d.name for d in directory.iterdir() if d.is_dir() and (d / "SKILL.md").exists()}


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def check_agents(root: Path) -> tuple[list[str], list[str]]:
    """#1: agent names in routing.md vs .claude/agents/*.md"""
    failures: list[str] = []
    warnings: list[str] = []

    routing_path = root / ".claude" / "rules" / "routing.md"
    agents_dir = root / ".claude" / "agents"

    if not routing_path.exists():
        failures.append("routing.md not found — cannot check agent drift")
        return failures, warnings

    text = _read(routing_path)
    # Extract backtick-quoted names.
    referenced = set(re.findall(r"`([a-z][a-z0-9_-]*)`", text))
    # "brainstorm" is main context, not a subagent.
    main_context = {"brainstorm"}
    referenced_agents = referenced - main_context

    # Filter out skill names — routing.md may mention skills as context notes.
    skills_dir = root / ".claude" / "skills"
    actual_skills = _glob_dir_names(skills_dir)
    referenced_agents = referenced_agents - actual_skills

    actual_agents = _glob_stems(agents_dir, "*.md")

    missing_files = referenced_agents - actual_agents
    unreferenced = actual_agents - referenced_agents

    for name in sorted(missing_files):
        failures.append(f"agent '{name}' referenced in routing.md but no .claude/agents/{name}.md")
    for name in sorted(unreferenced):
        failures.append(f"agent file .claude/agents/{name}.md exists but not referenced in routing.md")

    return failures, warnings


def check_skills(root: Path) -> tuple[list[str], list[str]]:
    """#2: skill names in CLAUDE.md vs .claude/skills/*/SKILL.md"""
    failures: list[str] = []
    warnings: list[str] = []

    claude_md = root / "CLAUDE.md"
    skills_dir = root / ".claude" / "skills"

    if not claude_md.exists():
        failures.append("CLAUDE.md not found — cannot check skill drift")
        return failures, warnings

    text = _read(claude_md)
    # Skills section: lines starting with "- " after "## Skills" header.
    in_skills = False
    referenced: set[str] = set()
    for line in text.splitlines():
        if line.strip().startswith("## Skills"):
            in_skills = True
            continue
        if in_skills and line.strip().startswith("##"):
            break
        if in_skills and line.strip().startswith("- "):
            # Comma-separated skill names on each bullet line.
            names = line.strip().lstrip("- ").split(",")
            for name in names:
                name = name.strip()
                if name:
                    referenced.add(name)

    actual_skills = _glob_dir_names(skills_dir)

    missing_dirs = referenced - actual_skills
    unreferenced = actual_skills - referenced

    for name in sorted(missing_dirs):
        failures.append(f"skill '{name}' listed in CLAUDE.md but no .claude/skills/{name}/SKILL.md")
    for name in sorted(unreferenced):
        failures.append(f"skill directory .claude/skills/{name}/ exists but not listed in CLAUDE.md")

    return failures, warnings


def check_commands_in_readme(root: Path) -> tuple[list[str], list[str]]:
    """#3: .claude/commands/*.md vs README.md command table"""
    failures: list[str] = []
    warnings: list[str] = []

    commands_dir = root / ".claude" / "commands"
    readme_path = root / "README.md"

    if not readme_path.exists() or not commands_dir.is_dir():
        return failures, warnings

    actual_commands = _glob_stems(commands_dir, "*.md")
    readme_text = _read(readme_path)

    # README command table uses "| `/name` |" pattern.
    readme_commands = set(re.findall(r"`/([a-z][a-z0-9_-]*)`", readme_text))

    missing_in_readme = actual_commands - readme_commands
    for name in sorted(missing_in_readme):
        warnings.append(f"command '/{name}' exists as file but not in README.md command table")

    # Reverse: README command table lists a command without a matching file.
    # Use table-row pattern to avoid matching prose mentions of /name.
    table_commands = set(re.findall(r"^\|\s*`/([a-z][a-z0-9_-]*)`\s*\|", readme_text, re.MULTILINE))
    extra_in_readme = table_commands - actual_commands
    for name in sorted(extra_in_readme):
        warnings.append(f"command '/{name}' in README.md command table but no .claude/commands/{name}.md")

    return failures, warnings


def check_hooks(root: Path) -> tuple[list[str], list[str]]:
    """#4: hooks in settings.json/settings.local.json vs hooks/*.sh"""
    failures: list[str] = []
    warnings: list[str] = []

    hooks_dir = root / "hooks"
    settings_candidates = [
        root / ".claude" / "settings.json",
        root / ".claude" / "settings.local.json",
    ]
    # Also check templates/hooks.template.json for the framework root.
    template_settings = root / "templates" / "hooks.template.json"
    if template_settings.exists():
        settings_candidates.append(template_settings)

    settings_path = None
    for candidate in settings_candidates:
        if candidate.exists():
            settings_path = candidate
            break

    if settings_path is None or not hooks_dir.is_dir():
        return failures, warnings

    try:
        settings = json.loads(_read(settings_path))
    except (json.JSONDecodeError, OSError):
        warnings.append(f"could not parse {settings_path.name}")
        return failures, warnings

    hooks_config = settings.get("hooks", {})
    referenced_scripts: set[str] = set()

    for _event, matchers in hooks_config.items():
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            for hook in matcher.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract "hooks/foo.sh" from "bash hooks/foo.sh"
                match = re.search(r"hooks/([a-z][a-z0-9_-]*\.sh)", cmd)
                if match:
                    referenced_scripts.add(match.group(1))

    actual_scripts = {p.name for p in hooks_dir.glob("*.sh")}

    missing_files = referenced_scripts - actual_scripts
    for name in sorted(missing_files):
        failures.append(f"hook script '{name}' registered in {settings_path.name} but hooks/{name} does not exist")

    return failures, warnings


def check_template_profiles(root: Path) -> tuple[list[str], list[str]]:
    """#5: template profile definitions vs actual template files"""
    failures: list[str] = []
    warnings: list[str] = []

    profiles_dir = root / "templates" / "profiles"
    if not profiles_dir.is_dir():
        return failures, warnings

    for profile_path in sorted(profiles_dir.glob("*.json")):
        try:
            profile = json.loads(_read(profile_path))
        except (json.JSONDecodeError, OSError):
            warnings.append(f"could not parse profile {profile_path.name}")
            continue

        # Drift lint checks framework-owned files only.
        # Profile 'recommended' entries are project-level guidance and may not
        # exist in the framework root, so only check 'required' paths.
        for rel_path in profile.get("required", []):
            full = root / rel_path
            if not full.exists():
                warnings.append(
                    f"profile '{profile_path.stem}' references '{rel_path}' but file does not exist"
                )

    return failures, warnings


def check_readme_counts(root: Path) -> tuple[list[str], list[str]]:
    """#6: README.md counts like '10 bounded specialist roles' vs actual"""
    failures: list[str] = []
    warnings: list[str] = []

    readme_path = root / "README.md"
    if not readme_path.exists():
        return failures, warnings

    text = _read(readme_path)

    # Agents count: "# N bounded specialist roles" or "N agents"
    agents_dir = root / ".claude" / "agents"
    agent_match = re.search(r"#\s*(\d+)\s+bounded specialist roles", text)
    if agent_match and agents_dir.is_dir():
        stated = int(agent_match.group(1))
        actual = len(list(agents_dir.glob("*.md")))
        if stated != actual:
            warnings.append(f"README says {stated} agents but found {actual}")

    return failures, warnings


def check_template_version(root: Path) -> tuple[list[str], list[str]]:
    """#7: framework_version in templates vs FRAMEWORK_VERSION in check_framework_contract.py"""
    failures: list[str] = []
    warnings: list[str] = []

    contract_path = root / "scripts" / "check_framework_contract.py"
    if not contract_path.exists():
        return failures, warnings

    contract_text = _read(contract_path)
    version_match = re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"', contract_text)
    if not version_match:
        return failures, warnings

    canonical_version = version_match.group(1)

    templates_dir = root / "templates"
    if not templates_dir.is_dir():
        return failures, warnings

    for tmpl in sorted(templates_dir.glob("*.template.md")):
        tmpl_text = _read(tmpl)
        for m in re.finditer(r'framework_version:\s*"([^"]+)"', tmpl_text):
            if m.group(1) != canonical_version:
                warnings.append(
                    f"{tmpl.name} has framework_version '{m.group(1)}' "
                    f"but check_framework_contract.py says '{canonical_version}'"
                )

    return failures, warnings


TEMPLATE_REF_RE = re.compile(r"templates/[A-Za-z0-9._-]+\.template\.md")


def check_template_references(root: Path) -> tuple[list[str], list[str]]:
    """#12: templates/ refs in skills must exist AND be shipped by any profile
    that ships the referencing skill (P1-B, OBS-012 — F6-class install gap:
    a skill instructing 'use templates/X' dies at install when X is absent)."""
    failures: list[str] = []
    warnings: list[str] = []

    skills_dir = root / ".claude" / "skills"
    refs_by_file: dict[str, set[str]] = {}
    if skills_dir.is_dir():
        for sk in sorted(skills_dir.glob("*/SKILL.md")):
            refs = set(TEMPLATE_REF_RE.findall(_read(sk)))
            if refs:
                refs_by_file[f".claude/skills/{sk.parent.name}/SKILL.md"] = refs

    # 1) Repo-level: referenced template files must exist.
    for src, refs in sorted(refs_by_file.items()):
        for ref in sorted(refs):
            if not (root / ref).is_file():
                failures.append(f"{src} references {ref} but the template does not exist")

    # 2) Profile-level: a profile shipping the skill must ship its templates.
    profiles_dir = root / "templates" / "profiles"
    if profiles_dir.is_dir():
        for prof in sorted(profiles_dir.glob("*.json")):
            try:
                data = json.loads(_read(prof))
            except ValueError:
                continue  # malformed profile is check_template_profiles' job
            shipped = set(data.get("required", [])) | set(data.get("recommended", []))
            for src, refs in sorted(refs_by_file.items()):
                if src not in shipped:
                    continue
                for ref in sorted(refs):
                    if ref not in shipped:
                        failures.append(
                            f"profile {prof.name} ships {src} (references {ref}) "
                            f"but does not ship the template"
                        )

    return failures, warnings


SKILL_PATH_RE = re.compile(r"\.claude/skills/([a-z][a-z0-9_-]*)/SKILL\.md")
# Anchored per line, comment-prefix excluded, no newline inside quotes: a
# names="..." example inside a header COMMENT must never become a boot root
# (a real skill name in a comment would make reachability permanently CLEAN).
PHASE_MAP_NAMES_RE = re.compile(r'^[^#\n]*\bnames="([^"\n]*)"', re.M)
USER_INVOCABLE_RE = re.compile(r"^user-invocable:\s*true\b", re.M)


def _phase_map_skill_names(root: Path) -> set[str]:
    lib = root / "hooks" / "lib" / "phase-skills.sh"
    if not lib.is_file():
        return set()
    names: set[str] = set()
    for m in PHASE_MAP_NAMES_RE.finditer(_read(lib)):
        names.update(m.group(1).split())
    return names


# Pure existence manifests: they list every skill path as metadata, not as a
# boot instruction. Counting them as reachability roots would make the check
# permanently CLEAN (vacuous) — the exact fake-green this check exists to stop.
SKILL_REF_EXCLUDE = {Path("scripts") / "check_framework_contract.py"}


def _control_file_skill_refs(root: Path) -> set[str]:
    sources: list[Path] = []
    claude_md = root / "CLAUDE.md"
    if claude_md.is_file():
        sources.append(claude_md)
    for sub in ("commands", "agents", "rules"):
        base = root / ".claude" / sub
        if base.is_dir():
            sources.extend(p for p in sorted(base.rglob("*.md")) if p.is_file())
    for sub, exts in (("hooks", (".sh",)), ("scripts", (".sh", ".py"))):
        base = root / sub
        if base.is_dir():
            sources.extend(
                p for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in exts
            )
    refs: set[str] = set()
    for path in sources:
        if path.relative_to(root) in SKILL_REF_EXCLUDE:
            continue
        refs.update(SKILL_PATH_RE.findall(_read(path)))
    return refs


def check_skill_reachability(root: Path) -> tuple[list[str], list[str]]:
    """#8: every skill must have a boot path (phase map / user-invocable / path ref)"""
    failures: list[str] = []
    warnings: list[str] = []

    skills_dir = root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return failures, warnings

    skills: dict[str, Path] = {}
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            skills[entry.name] = skill_md

    roots = _phase_map_skill_names(root) | _control_file_skill_refs(root)
    for name, skill_md in skills.items():
        if USER_INVOCABLE_RE.search(_read(skill_md)):
            roots.add(name)

    reachable: set[str] = set()
    queue = [name for name in sorted(roots) if name in skills]
    while queue:
        name = queue.pop()
        if name in reachable:
            continue
        reachable.add(name)
        for target in SKILL_PATH_RE.findall(_read(skills[name])):
            if target in skills and target not in reachable:
                queue.append(target)

    for name in sorted(skills):
        if name not in reachable:
            failures.append(
                "skill '%s' has no boot path (not in phase-skills.sh, not "
                "user-invocable, and no control file Reads "
                ".claude/skills/%s/SKILL.md)" % (name, name)
            )

    return failures, warnings


# Scaffold-safe command variants: commands present in templates/commands/ whose
# content intentionally diverges from the framework root (e.g. graceful guards
# for optional scripts). Used by eval_scaffold_smoke.verify_command_surface.
SCAFFOLD_SAFE_COMMANDS = {
    Path(".claude") / "commands" / "validate.md",
    Path(".claude") / "commands" / "retro.md",
}


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

    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        warnings.append(f"{template.name}: 'hooks' is not an object")
        return failures, warnings

    for event, matchers in hooks.items():
        if event not in KNOWN_HOOK_EVENTS:
            failures.append(
                f"platform-manifest: hooks.template.json event '{event}' "
                f"not in KNOWN_HOOK_EVENTS (renamed/typo?)"
            )
        if event not in TOOL_MATCHING_EVENTS or not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            for token in (matcher.get("matcher") or "").split("|"):
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    ("agents (routing.md ↔ agents/)", check_agents),
    ("skills (CLAUDE.md ↔ skills/)", check_skills),
    ("commands (files ↔ README)", check_commands_in_readme),
    ("hooks (settings ↔ hooks/)", check_hooks),
    ("template profiles", check_template_profiles),
    ("README counts", check_readme_counts),
    ("template version", check_template_version),
    ("skill reachability", check_skill_reachability),
    ("template references", check_template_references),
    ("platform manifest (events/tools)", check_platform_manifest),
    ("platform verification staleness", check_platform_staleness),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference drift auto-lint")
    parser.add_argument(
        "--root",
        default=None,
        help="Framework root directory (default: parent of scripts/)",
    )
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).resolve()
    else:
        root = Path(__file__).resolve().parents[1]

    all_failures: list[str] = []
    all_warnings: list[str] = []

    for label, check_fn in ALL_CHECKS:
        failures, warnings = check_fn(root)
        all_failures.extend(failures)
        all_warnings.extend(warnings)

    for w in all_warnings:
        print(f"WARNING: {w}")
    for f in all_failures:
        print(f"FAIL: {f}")

    if all_failures:
        return 1

    if not all_warnings:
        print("PASS: no reference drift detected")
    else:
        print(f"PASS (with {len(all_warnings)} warnings)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

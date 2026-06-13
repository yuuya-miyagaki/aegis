# v0.8.0 Client Mode Enhancement --- Review Report

## Review Summary

- Reviewer: reviewer agent (fresh context)
- Date: 2026-04-17
- Scope: 32 files (14 new + 12 updated + 6 example spot-checks)
- Verdict: **PASS with notes** (1 P1, 3 P2, 6 P3)

## Findings

### P1 --- Must Fix (blocks approval)

1. **translation-mapping SKILL.md uses wrong path `docs/handover/mapping.md`**
   - File: `.claude/skills/translation-mapping/SKILL.md` (lines 15, 23, 49)
   - Also: `examples/minimal-project/.claude/skills/translation-mapping/SKILL.md` (same lines)
   - The SKILL.md references `docs/handover/mapping.md` in 3 places, but the correct path everywhere else in the framework is `docs/translation/mapping.md`.
   - This is a functional error: an agent following the SKILL.md instructions would create the mapping file in the wrong directory, causing the `client_ready_for_dev` gate check to fail (it checks `docs/translation/mapping.md`).
   - Fix: Replace all 3 occurrences of `docs/handover/mapping.md` with `docs/translation/mapping.md` in both the framework and example copies.

### P2 --- Should Fix (does not block, but recommended)

1. **docs/translation/mapping.md contains incorrect tool paths**
   - File: `docs/translation/mapping.md` (lines 11, 18)
   - Line 11: `bin/check-gate.sh + bin/update-gate.sh` should be `hooks/check-gate.sh + scripts/update-gate.sh`
   - Line 18: `bin/check_framework_contract.py` should be `scripts/check_framework_contract.py`
   - These are implementation hints in the mapping table. While they are sample data (not executable references), incorrect paths could mislead framework users who refer to the mapping as documentation.

2. **docs/client/glossary.md says "translation phase" but translation is not a phase**
   - File: `docs/client/glossary.md` (line 17)
   - The entry for `translation mapping` says "Client mode no translation phase" but v0.8.0 explicitly decided that translation is an artifact, not a phase. The usage context column should say something like "Client mode handover preparation" or "Client mode pre-handover artifact".

3. **check-client-info.sh hook positioned after check-tdd.sh in hooks.template.json**
   - File: `templates/hooks.template.json` (line 29)
   - Also: `examples/minimal-project/.claude/settings.json` (line 29)
   - The check-client-info.sh hook runs for ALL Edit/Write/NotebookEdit operations, not just requirements files. While the hook itself correctly short-circuits for non-requirements paths, it still incurs shell startup overhead on every edit. Consider registering it under a separate matcher entry with a narrower pattern if Claude Code supports path-based matchers in the future. Not blocking because the hook short-circuits correctly and quickly.

### P3 --- Observations (informational)

1. **Translation-specialist agent Boundaries section says "Write access is limited to `docs/translation/*` only" but allowedTools includes Edit and Write without path restrictions.** The `allowedTools` frontmatter field cannot restrict by path -- it only controls which tools are available. The boundary text serves as a prompt-level constraint, which is the correct approach for non-core agents. No action needed, but worth noting the enforcement is soft (prompt-based) rather than hard (hook-based).

2. **DECISION.template.md is not referenced in any profile.** The template exists in `templates/` and passes contract validation, but no profile includes `docs/decisions/*.md` in `required` or `recommended`. This is by design (decisions are created on demand, and `docs/decisions/` is scaffolded as an empty directory via `mkdir -p`). Documented here for traceability.

3. **Example project STATUS.md has `translation: null` despite having a populated mapping.md.** The example project (minimal-project) has `docs/translation/mapping.md` with real content, but `current_refs.translation` is `null` in STATUS.md. This is acceptable because the example project is in Dev mode at the `docs` phase, and the `translation` ref was never set during the example's lifecycle (it simulates a project that went through Client mode before the v0.8.0 features existed). However, for maximum pedagogical value, it could be set to `docs/translation/mapping.md`.

4. **Brainstorm record correctly preserved in docs/specs/.** The brainstorm record at `docs/specs/v080-client-enhancement-brainstorm.md` contains a comprehensive design rationale with clear traceability from the original 10-step proposal to the final minimal scope. The graduated escalation pattern (artifact -> hook -> agent -> phase) is well-documented.

5. **The setup.sh scaffold generates template files (with placeholders) into docs/client/ and docs/translation/.** This is expected behavior. Users who scaffold a new project will get files with `<placeholder>` markers that they need to fill in during the Client workflow. The contract validator's placeholder check only applies to example project files, not scaffold output.

6. **client_context field in STATUS.template.md is positioned between external_evidence and failure_tracking.** In the actual template it appears after `failure_tracking: null` with `client_context` preceding it in the YAML order. The template shows `client_context` before `failure_tracking: null` and after `external_evidence: []`. The ordering is consistent and the parser handles it correctly regardless of position.

## File-by-File Notes

### Templates (N1-N5)

| File | Status | Notes |
|------|--------|-------|
| `templates/CLIENT-CONTEXT.template.md` | OK | Contains exit-check, all required sections (project overview, stakeholders, business context, tech environment, constraints). Uses `<placeholder>` markers correctly. |
| `templates/CLIENT-GLOSSARY.template.md` | OK | Table structure (Client Term / Definition / Context), exit-check present, update history section. |
| `templates/CLIENT-OPEN-QUESTIONS.template.md` | OK | Numbered question table with status tracking, escalation rule note. |
| `templates/TRANSLATION-MAPPING.template.md` | OK | 3-layer mapping table, invariants, assumptions, open items cross-reference. |
| `templates/DECISION.template.md` | OK | Decision record with context, options table, decision, rationale, impact. Decision ID format (DEC-NNN) defined. |

### Docs Entities (N6-N10)

| File | Status | Notes |
|------|--------|-------|
| `docs/client/context.md` | OK | Real values, no placeholders. Accurately describes framework as its own client. |
| `docs/client/glossary.md` | P2 | "translation phase" wording. Otherwise well-populated with 12 terms. |
| `docs/client/open-questions.md` | OK | 3 real open questions referencing Phase B/C decisions. No placeholders. |
| `docs/translation/mapping.md` | P2 | Incorrect bin/ paths in implementation hints. 8 real mapping entries, good 3-layer examples. |
| `docs/decisions/.gitkeep` | OK | Empty directory preserved. |

### Agent & Skill (N11-N12)

| File | Status | Notes |
|------|--------|-------|
| `.claude/agents/translation-specialist.md` | OK | CSO description, maxTurns=15 matches boundary, hallucination guard present, readOnly=false, allowedTools correctly excludes Bash. |
| `.claude/skills/translation-mapping/SKILL.md` | **P1** | Uses `docs/handover/mapping.md` instead of `docs/translation/mapping.md` in 3 places. |

### Hook (N13)

| File | Status | Notes |
|------|--------|-------|
| `hooks/check-client-info.sh` | OK | Correct structure: sources extract-input.sh, path filtering for docs/requirements/*, Dev mode skip, proper deny/allow JSON output, no injection risks. |

### Updated Files (U1-U12)

| File | Status | Notes |
|------|--------|-------|
| `templates/STATUS.template.md` (U1) | OK | client_context and translation fields correctly added. |
| `scripts/check_status.py` (U2) | OK | OPTIONAL keys, EXPECTED refs, client_context parser, pre_approve_gate mapping.md check all correct. |
| `scripts/check_framework_contract.py` (U3) | OK | All REQUIRED lists updated, FRAMEWORK_VERSION = "0.8.0", hook registration check includes check-client-info.sh. |
| `bin/setup.sh` (U4) | OK | 4 resolve_source mappings added (1:1 template-to-docs), mkdir -p for docs/decisions. |
| `.claude/rules/state-machine.md` (U5) | OK | Purpose statement added. No phase additions (artifact-first by design). |
| `.claude/skills/client-workflow/SKILL.md` (U6) | OK | Translation Artifact section, handover row updated, current_refs.translation update instruction. |
| `.claude/commands/next.md` (U7) | OK | Note added below Client table about mapping.md requirement. |
| `templates/HANDOVER-TO-DEV.template.md` (U8) | OK | mapping.md in canonical documents, open-questions.md cross-reference in unresolved section. |
| `templates/profiles/full.json` (U9) | OK | Agent, skill, docs paths in recommended. check-client-info.sh in hooks_include. No templates in profile (setup.sh indirect reference). |
| `templates/profiles/standard.json` (U10) | OK | docs paths in recommended. No agent/hook (by design for standard). |
| `hooks/session-start.sh` (U11) | OK | Handover hint split: other Client phases unchanged, handover gets translation-mapping skill hint. |
| `templates/hooks.template.json` (U12) | OK | check-client-info.sh registered under PreToolUse Edit/Write/NotebookEdit. Valid JSON. |

### Example Spot-Checks

| File | Status | Notes |
|------|--------|-------|
| `examples/minimal-project/.claude/agents/translation-specialist.md` | OK | Identical to framework source. |
| `examples/minimal-project/.claude/settings.json` | OK | check-client-info.sh registered. Valid JSON. Matches hooks.template.json structure. |
| `examples/minimal-project/docs/STATUS.md` | OK | version 0.8.0, translation: null, passes check_status.py. |
| `examples/minimal-project/docs/client/context.md` | OK | Real values (TaskFlow project). No placeholders. |
| `examples/minimal-project/docs/translation/mapping.md` | OK | 10 real mapping entries with concrete implementation hints. No placeholders. Excellent example quality. |
| `examples/minimal-project/hooks/session-start.sh` | OK | Identical to framework source. Handover hint split present. |

## Validation Evidence

```
$ python3 scripts/check_framework_contract.py
PASS: ultra-framework-claude-code contract is aligned

$ python3 scripts/check_status.py --root .
PASS: status file is valid: docs/STATUS.md

$ python3 scripts/check_status.py --root examples/minimal-project
PASS: status file is valid: examples/minimal-project/docs/STATUS.md

$ python3 scripts/check_status.py --pre-approve-gate client_ready_for_dev --root .
(exit 0 -- PASS, mapping.md exists)

$ bash bin/setup.sh --profile=full --target=<tmpdir>
(all files scaffolded, docs/client/ docs/translation/ docs/decisions/ created)
```

## Cross-Reference Integrity Summary

| Source | Target | Status |
|--------|--------|--------|
| client-workflow SKILL.md -> templates/TRANSLATION-MAPPING.template.md | template exists | OK |
| client-workflow SKILL.md -> translation-specialist agent | agent exists | OK |
| client-workflow SKILL.md -> translation-mapping skill | skill exists | OK |
| translation-mapping SKILL.md -> docs/translation/mapping.md | **WRONG** (says docs/handover/) | **P1** |
| translation-mapping SKILL.md -> translation-specialist agent | agent exists | OK |
| check-client-info.sh -> docs/client/context.md | file exists | OK |
| check_status.py pre_approve_gate -> docs/translation/mapping.md | file exists | OK |
| hooks.template.json -> check-client-info.sh | hook file exists | OK |
| full.json -> all new agent/skill/docs paths | all exist | OK |
| standard.json -> docs paths | all exist | OK |
| setup.sh resolve_source -> all template paths | all templates exist | OK |
| HANDOVER-TO-DEV.template.md -> mapping.md | correct path | OK |
| next.md -> mapping.md note | present | OK |
| state-machine.md -> purpose statement | present, no new phases | OK |

## Verdict

**PASS with notes.**

The v0.8.0 implementation is structurally sound, well-integrated, and passes all three validators. The design decisions from the brainstorm are faithfully implemented: translation as artifact-first (not a phase), single agent, single hook, minimal STATUS.md extension.

**One P1 must be fixed before merge:** the translation-mapping SKILL.md path error (`docs/handover/mapping.md` -> `docs/translation/mapping.md`). This is a 6-line fix across 2 files (framework + example).

The three P2 items are recommended but do not block approval. They involve incorrect sample data paths in mapping.md and a terminology inaccuracy in glossary.md.

Overall implementation quality is high. The example project files are particularly well-crafted with realistic, domain-specific content that demonstrates the 3-layer mapping concept effectively.

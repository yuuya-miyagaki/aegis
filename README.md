# Aegis

Aegis is a Claude Code native distribution of Ultra Framework v7 principles.

It keeps the strongest parts of v7:

- explicit phase control
- user-approved hard gates
- evidence-based completion
- durable handover and restart artifacts

It removes the parts that add overhead in Claude Code:

- `.agents/AGENTS.md` as the primary entrypoint
- broad host-neutral instruction loading
- large always-on rule sets
- unnecessary token-heavy routing

## Design Priorities

- Thin working context by default
- Explicit operational state in `docs/STATUS.md`
- Pull-based document loading
- Small subagent surface area
- Low token waste
- Policy as Code (PaC) via hooks

## Design Philosophy

Each design choice reflects a specific constraint learned from operating
AI-assisted development workflows at scale.

| Principle | Why |
|-----------|-----|
| **Thin CLAUDE.md** (<700 words) | Always-on context that grows steals budget from phase-specific skills. Keeping the kernel small leaves room to pull what matters now. |
| **STATUS.md as human-readable state** | A database is invisible at session restart. A plain-text ledger supports diff, grep, and manual edits — the three things you need when recovery fails. |
| **Pull-based skills** | Loading every skill at once floods the context with rules irrelevant to the current phase. Pull-on-demand keeps signal-to-noise high. |
| **Hard gates + Hook PaC** | Written rules get skipped. Hooks enforce them at runtime — a failed gate blocks the tool call, not just the intention. |
| **Claude Code native only** | Cross-harness ambition adds abstraction layers that prevent native optimizations (skills, agents, commands, hooks). Specializing for one host keeps the framework thin. |

## Repository Structure

```text
aegis/
├── CLAUDE.md                    # control kernel (~360 words)
├── .claude/
│   ├── agents/                  # 12 bounded specialist roles
│   ├── commands/                # slash commands (/status, /gate, etc.)
│   ├── rules/                   # always-loaded rules (state-machine, routing)
│   └── skills/                  # pull-based skill documents
├── docs/
├── hooks/                       # runtime enforcement (PaC)
│   └── lib/                     # shared hook utilities
├── templates/
├── scripts/
├── extensions/                  # optional addons (manual opt-in)
│   └── qa-browser/              # browser QA workflow
└── examples/minimal-project/
```

## Core Model

- `CLAUDE.md` is the control kernel
- `.claude/rules/` holds always-loaded state machine and routing rules
- `docs/STATUS.md` is the operational state index
- canonical docs under `docs/` are the source of project truth
- `.claude/agents/` holds bounded specialist roles with enriched frontmatter
- `.claude/skills/` holds pull-based skill documents (native mechanism)
- `.claude/commands/` provides slash commands for common operations
- `hooks/` provides runtime enforcement via Claude Code hooks
- `templates/` is the project bootstrap source

## Native Feature Mapping

How Aegis maps to Claude Code's built-in capabilities.

| Claude Code Feature | Aegis Usage | Not Used / Reason |
|---------------------|--------------|-------------------|
| `CLAUDE.md` | Control kernel (<700 words) | — |
| `.claude/rules/` | State machine + routing (always-loaded) | — |
| `.claude/skills/` | Pull-based phase documents (`disable-model-invocation: true`) | — |
| `.claude/commands/` | 7 slash commands (`/status`, `/gate`, `/tutorial`, etc.) | — |
| `.claude/agents/` | 12 bounded specialist roles (frontmatter enriched) | — |
| `.claude/settings.json` / `settings.local.json` | Hook registration (PaC). Quick Start recommends `settings.local.json` | — |
| `EnterPlanMode` | — | **Not used.** Framework phases replace it; explicitly prohibited in CLAUDE.md |
| `TodoWrite` / `TaskCreate` | Session-local subtask management only (subagent-dev skill) | Persistent state lives in STATUS.md, not task lists |
| Auto-memory | Personal preferences only | Technical lessons belong in `docs/LEARNINGS.md` |
| Context compaction | Controlled by PreCompact hook | Blocked when STATUS.md is stale |

## Quick Start

### Automated setup (recommended)

```bash
bin/setup.sh --profile=standard --target=<your-project-dir>
```

Available profiles: `minimal` (core only), `standard` (recommended), `full` (everything including agents).

### Manual setup

1. Read [CLAUDE.md](CLAUDE.md)
2. Copy `templates/CLAUDE.template.md` as your project's `CLAUDE.md`
3. Copy the templates you need from `templates/` into your project's `docs/`
4. Copy `.claude/rules/` into the project for state machine and routing rules
5. Copy `.claude/commands/` into the project for slash commands
6. Copy `hooks/` directory and generate `.claude/settings.local.json` from `templates/hooks.template.json`
7. Copy `scripts/check_status.py` and `scripts/update-gate.sh` into the project
8. Validate the scaffold before use

**Skills** (`.claude/skills/`) are loaded by Claude Code natively. Each skill
has a `SKILL.md` with frontmatter (`disable-model-invocation: true` for
pull-based loading). Project CLAUDE.md references skills by name.

**Commands** (`.claude/commands/`) provide slash commands:

| Command | Purpose |
|---------|---------|
| `/status` | Display formatted STATUS.md summary |
| `/gate` | List and approve gates |
| `/recover` | Invoke session recovery |
| `/validate` | Run tiered framework evaluation |
| `/next` | Show next action and phase transition suggestions |
| `/retro` | Generate retrospective report |
| `/tutorial` | Phase transition walkthrough guide |

**Hooks** (`hooks/`) enforce framework rules at runtime:

- **SessionStart**: injects current mode, phase, blockers; initializes gate snapshot
- **PreToolUse (Edit/Write/NotebookEdit)**: blocks code edits when plan gate is not approved;
  blocks framework file edits during non-framework tasks
- **PreToolUse (Bash)**: denies control plane file writes during non-framework tasks;
  warns before destructive commands
- **PostToolUse (Bash)**: detects test runner failures and suggests ReAct approach
- **PostToolUse (Edit/Write/NotebookEdit)**: detects unauthorized gate tampering in STATUS.md
- **PreCompact**: blocks compaction when STATUS.md is stale (not updated within 5 min during active phase); allows with context summary when current

## Validation

From this repository root:

```bash
python3 scripts/run_eval.py --tier 1
```

Profile-based validation for scaffold projects:

```bash
python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project
```

Available profiles: `minimal` (4 core files), `standard` (14 required + 7 recommended). `full` is framework repo root only (do not use with `--root`).
Profile definitions: `templates/profiles/*.json`.

Optional strict YAML validation (requires PyYAML):

```bash
pip install pyyaml
python3 scripts/check_status.py --root . --strict
```

## Migration

### From v0.12.1 to v0.12.2

**Hot-fix release**: Hook output schemas migrated to current Claude Code spec.
The old form (top-level `permissionDecision`/`message`) is silently ignored
by Claude Code 2.x — `deny` / `block` were not actually enforced before this fix.

1. **PreToolUse 8 hooks**: top-level `permissionDecision`/`message` → `hookSpecificOutput.permissionDecision`/`permissionDecisionReason`. Affects `check-gate.sh`, `check-control-plane.sh`, `check-secrets.sh`, `check-destructive.sh`, `check-deploy-gate.sh`, `check-deploy-mcp-gate.sh`, `check-tdd.sh`, `check-client-info.sh`.
2. **PostToolUse hook** (`post-status-audit.sh`): top-level `permissionDecision`/`message` → top-level `decision: "block"`/`reason`. Restores gate-tamper / phase-skip / mode-tamper detection.
3. **post-bash.sh**: migrated from `PostToolUse` to **`PostToolUseFailure`** event. Output uses `hookSpecificOutput.additionalContext` (informational; never blocks). The internal exit-code check is removed — the event itself fires only on failures.
4. **pre-compact.sh**: block path → top-level `decision`/`reason`; allow path → `hookSpecificOutput.additionalContext` + `hookEventName`.
5. **`if` filter removed** from `templates/hooks.template.json` for `post-status-audit.sh`. The official spec restricts `if` to a single permission rule (no `||`). Replaced by the existing `case TARGET_FILE in *STATUS.md` filter inside the hook script (covers Edit/Write/NotebookEdit fully).
6. **New event registration**: `PostToolUseFailure` section added to `templates/hooks.template.json` for `post-bash.sh`.
7. **Contract tests**: new `tests/test_hook_output_schema.py` (12 cases) covers all hook output schemas. Reference: `hooks/session-start.sh` was already conformant.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=<your-profile>` to refresh `.claude/settings.local.json` with the new `templates/hooks.template.json`. The old schema was already non-functional in Claude Code 2.x, so this is a strict improvement (no functional regression).

Driven by a 5-round external review (Round 1〜5, 25 issues raised, all reflected). See `docs/plans/v0130-modernization-plan.md` Rev.5 for full context. The remainder of v0.13.0 (subagent / effort / Plan / Skill / TaskCreated|Completed event hooks etc.) follows.

### From v0.9.0 to v0.10.0

1. **browser-assist skill added**: new `.claude/skills/browser-assist/SKILL.md`
   provides shared browser automation foundation (gstack `$B` + Playwright MCP
   fallback); any agent can load it via `skills:` frontmatter array
2. **integration-assist refactored**: `$B` resolution logic and bash code blocks
   moved to browser-assist; integration-assist now references browser-assist for
   browser operations and focuses on service connection workflow
3. **qa-browser agent updated**: now loads `browser-assist` skill; `$B` preferred
   for navigation/interaction, Playwright MCP for console/network diagnostics;
   `Bash` removed from `disallowedTools` (needed for `$B` commands)
4. **integration-specialist agent updated**: `skills:` expanded to
   `[browser-assist, integration-assist]` (first multi-skill agent)
5. **routing.md updated**: browser-assist availability note added
6. **CLAUDE.md Skills list**: `browser-assist` added to the skill listing
7. **extensions/qa-browser/WORKFLOW.md updated**: browser-assist priority
   (`$B` preferred, Playwright MCP as fallback/diagnostics)
8. **Skill count**: 14 → 15 skills

### From v0.8.0 to v0.9.0

1. **integration-specialist agent added**: new `.claude/agents/integration-specialist.md`
   handles external service integration (API setup, OAuth, webhooks) with browser
   automation via gstack `$B`; copy to your project's `.claude/agents/`
2. **integration-assist skill added**: new `.claude/skills/integration-assist/SKILL.md`
   guides service connection with 6-step workflow (identify → research → automate →
   handoff → configure → test); copy to your project's `.claude/skills/`
3. **routing.md updated**: `integration-specialist` route added
4. **CLAUDE.md Skills list**: `integration-assist` added to the skill listing
5. **Optional dependency**: gstack browse (`$B`) enables browser automation with
   handoff/resume; skill falls back to guided text instructions when not installed
6. **Agent count**: 11 → 12 agents; Skill count: 13 → 14 skills

### From v0.7.3 to v0.8.0

1. **translation-specialist agent added**: new `.claude/agents/translation-specialist.md`
   supports Client→Dev handover translation; copy to your project's `.claude/agents/`
2. **translation-mapping skill added**: new `.claude/skills/translation-mapping/SKILL.md`
   guides creation of `docs/translation/mapping.md`; copy to your project's `.claude/skills/`
3. **check-client-info.sh hook added**: new `hooks/check-client-info.sh` denies
   requirements edits in Client mode when `docs/client/context.md` is absent;
   copy to `hooks/` and register in PreToolUse `Edit|Write|NotebookEdit` matcher
4. **Client directories added**: create `docs/client/`, `docs/translation/`,
   `docs/decisions/` in your project; scaffold with `bin/setup.sh --profile=full`
5. **Client templates added**: 5 new templates in `templates/`:
   `CLIENT-CONTEXT.template.md`, `CLIENT-GLOSSARY.template.md`,
   `CLIENT-OPEN-QUESTIONS.template.md`, `TRANSLATION-MAPPING.template.md`,
   `HANDOVER-TO-DEV.template.md` (updated)
6. **state-machine.md updated**: Client mode purpose statement added
7. **client-workflow SKILL.md updated**: Translation Artifact section added
   with `docs/translation/mapping.md` handover prerequisite
8. **session-start.sh updated**: handover phase hint split from acceptance;
   includes mapping.md requirement note
9. **STATUS.md schema**: add `translation: null` to `current_refs`
10. **Gate contract expanded**: `client_ready_for_dev` gate now checks
    `docs/translation/mapping.md` existence via `check_status.py`
11. **CLAUDE.md Skills list**: `translation-mapping` added to the skill listing
12. **Agent count**: 10 → 11 agents; Skill count: 12 → 13 skills

### From v0.7.2 to v0.7.3

1. **qa-verification skill added**: new `.claude/skills/qa-verification/SKILL.md`
   provides QA phase verification process (test execution, evidence collection,
   reproduction templates); copy to your project's `.claude/skills/`
2. **Agent skills preload unified**: `reviewer.md` now preloads `review`,
   `security.md` preloads `security-review`, `qa.md` preloads `qa-verification`;
   add `skills:` frontmatter to your agent files
3. **MCP catalog added**: `extensions/mcp/` provides configuration templates
   for 5 recommended MCP servers (Playwright, GitHub, Context7, Vercel, Figma);
   copy needed `.json` files and merge into your `.mcp.json`
4. **session-start.sh updated**: qa and security phase hints now include
   skill references (`skill: qa-verification`, `skill: security-review`)
5. **CLAUDE.md Skills list**: `qa-verification` added to the skill listing
6. **Skill count**: 11 → 12 skills

### From v0.7.1 to v0.7.2

1. **check-control-plane.sh added**: new Bash PreToolUse hook that denies
   control plane file writes (STATUS.md, CLAUDE.md, .claude/, hooks/, scripts/)
   during non-framework tasks; register in Bash PreToolUse before check-destructive.sh
2. **NotebookEdit added to matchers**: PreToolUse and PostToolUse matchers
   expanded from `Edit|Write` to `Edit|Write|NotebookEdit` (defense-in-depth)
3. **extract\_file\_path notebook\_path fallback**: `hooks/lib/extract-input.sh`
   now falls back to `notebook_path` when `file_path` is empty (NotebookEdit support)
4. **Template reference drift fixed**: corrected stale skill/agent names in
   PLAN, VERIFICATION, DEPLOY-CHECKLIST templates and session-start.sh
5. **`/validate` scaffold-safe**: example project's `/validate` now runs
   `check_status.py` only (not `check_framework_contract.py`)
6. **check\_status.py in Quick Start**: step 11 added for copying the script
   into scaffolded projects

### From v0.7.0 to v0.7.1

1. **PreCompact hook added**: `hooks/pre-compact.sh` blocks compaction when
   STATUS.md is stale (not updated within 5 min during active phase);
   register `PreCompact` in your hooks settings
2. **qa-browser agent added**: `.claude/agents/qa-browser.md` provides safe
   Playwright MCP access via `disallowedTools` (Edit/Write/NotebookEdit/Bash denied);
   update routing rules to include `qa-browser`
3. **QA agent updated**: browser QA section now delegates to qa-browser
   instead of the "Orchestrator Action Required" handoff
4. **Auto-memory policy relaxed**: CLAUDE.md now permits auto-memory for
   personal preferences (LEARNINGS.md remains primary for technical lessons)
5. **external\_evidence.type lint**: validator now warns on non-kebab-case type values
6. **`/next` enhanced**: suggests trimming body Session History when entries exceed 10
7. **subagent-dev TaskCreate clarified**: TaskCreate usage scoped to
   session-local subtask management only

### From v0.6.0 to v0.7.0

1. **STATUS.md schema expanded**: add `failure_tracking: null` and
   `task_size_rationale` fields to frontmatter
2. **Archive limits enforced**: `session_history` and `external_evidence` capped
   at 3 entries each; older entries archived to body or `docs/evidence-archive.md`
3. **Archive file**: create `docs/evidence-archive.md` for overflow evidence
4. **CLAUDE.md updated**: 3-failure rule now requires writing to
   `failure_tracking` (goal/count/last_attempt); reset to null on resolution
5. **Iteration reset**: `state-machine.md` updated — archive external_evidence
   older than latest 3 on iteration reset
6. **Skills updated**: brainstorming and bug-diagnosis skills now include
   `task_size_rationale` recording step

### From v0.5.0 to v0.6.0

1. **Skills moved**: `docs/skills/` → `.claude/skills/*/SKILL.md`
2. **Rules extracted**: State Machine and Routing moved from CLAUDE.md to `.claude/rules/`
3. **Commands added**: 5 slash commands in `.claude/commands/`
4. **Trust boundary hardened**: `check-gate.sh` blocks framework file edits;
   `post-status-audit.sh` detects gate tampering
5. **Hook library**: shared `hooks/lib/extract-input.sh` for input parsing
6. **Agent frontmatter enriched**: `model`, `permissionMode`, `effort`, `color` fields
7. **Agent language unified**: all agent files now in English
8. **CLAUDE.md slimmed**: 583 → 320 words

## Extensions

Optional addons (manual opt-in) that are not included in `setup.sh` profiles. Copy manually.

### qa-browser

Browser-based QA workflow using browser-assist skill (`$B` preferred,
Playwright MCP as fallback for navigation and diagnostics). Provides a 4-step
verification process: Snapshot → Interact → Verify → Evidence Capture.

```bash
cp -r extensions/qa-browser <your-project>/extensions/qa-browser
```

See [extensions/qa-browser/README.md](extensions/qa-browser/README.md) for details.

## Relationship to Ultra Framework v7

- `ultra-framework-v7` remains the stable, host-neutral framework line
- `aegis` (formerly `ultra-framework-claude-code`) is the Claude Code optimized distribution
- conceptual migration guidance lives in
  [docs/MIGRATION-FROM-v7.md](docs/MIGRATION-FROM-v7.md)

## Language Policy

- control files are written in English: `CLAUDE.md`, `.claude/agents/`,
  `.claude/commands/`, `.claude/rules/`, `hooks/`, `scripts/`
- skills (`.claude/skills/`) follow the project documentation language
  (they are user-facing reference documents loaded on demand)
- project-facing docs are written in Japanese by default
- if a team uses another language, update templates and validation together

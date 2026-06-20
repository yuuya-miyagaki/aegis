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
└── extensions/                  # optional addons (manual opt-in)
    └── qa-browser/              # browser QA workflow
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

## Documentation

- [Onboarding](docs/onboarding/README.md) — guided tutorial, hands-on, and cheat sheet (start here)
- [Architecture overview](docs/architecture-overview.md) — control flow and how the components fit together
- [Migration history](docs/MIGRATION-HISTORY.md) — version-to-version upgrade notes

## Native Feature Mapping

How Aegis maps to Claude Code's built-in capabilities.

| Claude Code Feature | Aegis Usage | Not Used / Reason |
|---------------------|--------------|-------------------|
| `CLAUDE.md` | Control kernel (<700 words) | — |
| `.claude/rules/` | State machine + routing (always-loaded) | — |
| `.claude/skills/` | Pull-based phase documents (`disable-model-invocation: true`) | — |
| `.claude/commands/` | 8 slash commands (`/status`, `/gate`, `/judge`, `/tutorial`, etc.) | — |
| `.claude/agents/` | 12 bounded specialist roles (frontmatter enriched) | — |
| `.claude/settings.json` / `settings.local.json` | Hook registration (PaC). Quick Start recommends `settings.local.json` | — |
| `EnterPlanMode` | — | **Not used.** Framework phases replace it; explicitly prohibited in CLAUDE.md |
| `TodoWrite` / `TaskCreate` | Session-local subtask management only (subagent-dev skill) | Persistent state lives in STATUS.md, not task lists |
| Auto-memory | Personal preferences only | Technical lessons belong in `docs/LEARNINGS.md` |
| Context compaction | Controlled by PreCompact hook | Blocked when STATUS.md is stale |
| Checkpoints / `/rewind` | (complementary) `session-recovery` | **Keep** — `/rewind` undoes file edits (ephemeral); `session-recovery` rebuilds framework state (phase/gates/refs/partials) from STATUS.md. Different problem. |
| `/resume` / `--continue` / `--fork` | (complementary) `/recover` + `session-recovery` | **Complement** — `/resume` restores the conversation (may suffice); `session-recovery` reconstructs/verifies state from STATUS.md when the conversation is gone. `/recover` is the discoverable trigger for that protocol, which `/resume` does not run. |
| Auto Mode | — | **Keep PaC hooks.** aegis's moat is *deterministic* hooks-as-guarantees; a probabilistic permission classifier cannot give the same guarantee (durable reason, independent of Auto Mode's preview status). |
| Routines / scheduling | — | **N/A** — aegis ships no scheduling/cron surface, so there is nothing to delegate or retire here. |

## Quick Start

> 🚀 はじめての方は **[オンボーディング教材](docs/onboarding/README.md)**（説明・ハンズオン・早見表）から。

### Automated setup (recommended)

```bash
bin/setup.sh --profile=standard --target=<your-project-dir>
```

Available profiles: `minimal` (core only), `standard` (recommended), `full` (everything including agents).

TDD backstop strictness follows the profile: `full` installs `check-tdd.sh` (strict — prompts when production code is edited without test changes); `minimal`/`standard` omit it (off). Within `full`, set `AEGIS_TDD_MODE=off` to disable the backstop for a single session (e.g. a large no-test refactor); session-start prints a warning while it is off. Lowercase `off` only.

Phase HINT nudges (the per-phase reminder sermon injected at session start) also follow the profile: `full` shows them; `minimal`/`standard` write `AEGIS_NUDGE=off` into the generated settings `env`, so the sermon is suppressed by default. Set `AEGIS_NUDGE=off` to silence it for a session in any profile (lowercase `off` only). Only the phase HINT is removed — gates, skill boot-paths, blockers, failure-tracking, the unknown-phase diagnostic, and safety warnings always remain. To re-enable nudges on a `minimal`/`standard` install, remove the `env.AEGIS_NUDGE` key from `.claude/settings.local.json` (the unambiguous method; shell-vs-settings env precedence is platform-dependent). Unlike `AEGIS_TDD_MODE`, session-start does not warn when nudges are off (it is benign).

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
| `/judge` | Preview the gate judge card (machine facts vs. claims; read-only) |

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
python3 scripts/check_framework_contract.py --profile=standard --root <your-project-dir>
```

Available profiles: `minimal` (4 core files), `standard` (15 required + 8 recommended). `full` is framework repo root only (do not use with `--root`).
Profile definitions: `templates/profiles/*.json`.

Optional strict YAML validation (requires PyYAML):

```bash
pip install pyyaml
python3 scripts/check_status.py --root . --strict
```

## Migration

Aegis follows semantic versioning against a defined public contract (see the
**Stability & Versioning** section below). Version-to-version upgrade notes
live in [docs/MIGRATION-HISTORY.md](docs/MIGRATION-HISTORY.md).

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

## Stability & Versioning

As of v1.0.0, Aegis follows semantic versioning against a defined **public contract**.

**Public contract (a breaking change bumps MAJOR):**

- the `CLAUDE.md` operating rules (gates, completion rule, state machine)
- the `docs/STATUS.md` frontmatter schema
- profile names: `minimal`, `standard`, `full`
- the gate model (gate names, gate→evidence-ref coupling)
- hook output schemas (as emitted via `hooks/lib/emit.sh`)

**Internal (may change in any release):** script internals, exact message wording,
agent prompts, tests, file line counts, and comment language.

MAJOR = a public-contract break; MINOR = backward-compatible additions; PATCH = fixes.

## Language Policy

- control files are written in English: `CLAUDE.md`, `.claude/agents/`,
  `.claude/commands/`, `.claude/rules/`, `hooks/`, `scripts/`
- skills (`.claude/skills/`) follow the project documentation language
  (they are user-facing reference documents loaded on demand)
- project-facing docs are written in Japanese by default
- if a team uses another language, update templates and validation together

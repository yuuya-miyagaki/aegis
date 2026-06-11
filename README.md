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
python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project
```

Available profiles: `minimal` (4 core files), `standard` (15 required + 8 recommended). `full` is framework repo root only (do not use with `--root`).
Profile definitions: `templates/profiles/*.json`.

Optional strict YAML validation (requires PyYAML):

```bash
pip install pyyaml
python3 scripts/check_status.py --root . --strict
```

## Migration

### From v1.5.0 to v1.5.1

**Non-breaking — grill 残余修正バッチ（防御強化・誤判定緩和）。**

- **テストランナー分類がコマンド位置アンカーになった（T1）。**
  `grep vitest package.json` や `echo pytest` のような「引数・文字列としての
  言及」はテスト実行と分類されなくなり、その失敗が judge の 🔴 を誘発しない。
  分類から外れたコマンドは unverified 方向に倒れる（fail-open しない）。
  `time pytest` 等のラッパー形は分類されないため、ゲート承認前は実テストを
  直接実行（または `scripts/record-test-result.py` で手動記録）すること。
- deploy ゲートの ask/deny 文面に python の警告や traceback が混入しなくなった（T2）。
- `update-gate.sh` の排他ロックが読み取り前に取得され（T3）、kill 等で残った
  stale lock は保持プロセスの死亡を確認して自動回収される（T4）。生きた並行
  実行がある場合は pid 付きのエラーで待機を案内する。
- `check-control-plane.sh` が `find ... -exec/-delete` 系の書込形を deny する
  ようになり、`grep "confirm " hooks/x.sh` 等の正当読取りの誤 deny が解消（T5）。

### From v1.4.0 to v1.5.0

**Non-breaking — E1 activity verification (観測ベースのテスト検証).**

ゲート承認時のテスト判定は、エージェントの自己申告ではなく hook が観測した
実行記録（`.claude/evidence-log.jsonl`）に基づく。PostToolUse/PostToolUseFailure
(Bash) が全実行のメタ（コマンド・成否・worktree fingerprint）を記録し、judge card
が現在のコードと一致する最新のテスト実行を照合する。記録が無い・コード変更後の
場合は 🟡 unverified（`--ack` で承認可）、観測された red は 🔴 ブロック。
Claude Code 外でテストを実行した場合は `scripts/record-test-result.py` で
手動記録できる（同一スキーマ・`src:"manual"`）。

- **`docs/qa-reports/test-result.json`（自己申告ファイル）は廃止。**
  `record-test-result.py` は evidence-log への手動フォールバック書き手に変わった。
- **新規配布物**: `hooks/post-bash-observe.sh`（PostToolUse Bash 観測）、
  `hooks/lib/evidence.sh` / `hooks/lib/fingerprint.sh`（記録・指紋の単一所有）。
  既存インストールは `bash bin/setup.sh --profile=<profile>` を再実行して
  hooks と settings を更新する。
- **完了時の生存チェック**: evidence-log ファイル不在（観測系が一度も発火して
  いない）を TaskCompleted が差し戻す。session-start がログを touch/ローテーション
  する（空ファイルは正常）。

### From v1.3.3 to v1.4.0

**Mostly non-breaking — evolution-review fix batch** (P2-1 … P3-6, B1, K-2;
review 2026-06-10). What changes for existing projects:

- **`standard` now ships the Bash guard moat (P2-1).** `check-destructive.sh`,
  `check-secrets.sh`, `check-deploy-gate.sh`, and `check-control-plane.sh` are
  registered in the `standard` profile's generated settings. Existing
  `standard` installs: re-run `bash bin/setup.sh --profile=standard` (or add
  the four PreToolUse Bash entries to `.claude/settings.local.json` by hand).
- **Deploy gate widened + size-skip now asks (P2-2, P2-3).** Flag-form
  `vercel --prod` and `wrangler deploy|publish` are now gated. S/M tasks
  (which skip the deploy phase) no longer deploy silently: the gate emits an
  `ask` so a human confirms the ungated deploy. RC contract:
  0=allow / 2 with a leading `ASK:`=ask / anything else=deny.
- **`ULTRA_PRECOMPACT_INTERVAL` renamed to `AEGIS_PRECOMPACT_INTERVAL`
  (P3-2).** The old name still works as a fallback for THIS release only and
  will be removed in the next one.
- **Generated settings reference hooks via `$CLAUDE_PROJECT_DIR` (P3-6).**
  cwd-relative `bash hooks/x.sh` silently disabled every hook when Claude Code
  was launched from a subdirectory. Existing installs: regenerate settings by
  re-running setup.sh, or rewrite each command to
  `bash "${CLAUDE_PROJECT_DIR:-.}"/hooks/<name>.sh` (the `:-.` fallback keeps
  hooks alive even where the variable is unset).
- **New: `docs/hook-failure-policy.md`** — the declared fail-open/fail-closed
  policy per hook, with a table-driven test keeping it honest. Read it before
  changing any hook's error handling.

### From v1.3.2 to v1.3.3

**Non-breaking — integrity-hook availability fixes** (evolution review
2026-06-10). The operating contract is unchanged and defense strength is
preserved (every probed bypass form stays denied); these fixes remove two
over-blocking defects that crippled scaffolded projects:

- **`check-control-plane` denied nearly every Bash command during project
  work.** The hook matched control-plane patterns against the RAW hook input,
  and real input always carries `transcript_path` under `~/.claude/projects/`
  (which contains `.claude/`), so the early-allow never fired. The hook now
  extracts the command (python3 first, bash fast-path, raw fallback stays
  fail-closed) and matches patterns against the command only, with root-anchored
  directory boundaries plus fixed-string absolute-path checks (logical and
  physical root forms).
- **`check-gate` blocked ordinary project paths.** Its `*/hooks/*`,
  `*/scripts/*`, `*CLAUDE.md` globs collided with project-owned paths such as
  `src/hooks/`, `src/templates/`, vendored `.claude/`, and nested `CLAUDE.md`.
  Protected paths are now anchored to the project root, dot-segments are
  lexically normalized, and root-escaping relative paths stay conservatively
  denied.
- **Hardening.** The scaffold smoke now drives hooks with a realistic input
  envelope (`transcript_path` included) and seals both fixes with live-fire
  checks, closing the same blind-spot family as v1.3.2's F6 (inspection inputs
  must match the real runtime schema).

**Action for existing projects**: replace the two hooks —
`hooks/check-control-plane.sh` and `hooks/check-gate.sh` — with the v1.3.3
versions (copy by hand, or re-run `bash bin/setup.sh` with `--force`; `--force`
overwrites all managed files, so review local edits first). Without this,
project-work sessions remain heavily over-blocked.

### From v1.3.1 to v1.3.2

**Non-breaking — install-delivery bug fixes** (functional-integrity audit
2026-06-07). The operating contract is unchanged; these fixes make scaffolded
projects actually ship and run what they were designed to. The audit found that
static checks (contract/eval/drift/mirror) only validated the framework repo and
the hand-maintained example — the `setup.sh` install path was never executed — so
several install-only breaks went unnoticed.

- **Hook libraries now ship (the big one).** `setup.sh` copied only
  `hooks/lib/extract-input.sh`, omitting `hooks/lib/emit.sh` (sourced by every
  hook) and `hooks/lib/patterns.sh`. Every hook died at `source lib/emit.sh` in
  `standard`/`full` installs, so the deterministic PaC moat silently failed open.
  `copy_hooks` now copies the whole `hooks/lib/*.sh`.
- **`/judge`, graceful `/retro`, `status_doctor` now ship in `full`.** `/judge`
  was in no profile; `/retro` shipped the non-graceful framework variant that
  hard-runs a script no profile ships; `session-recovery`'s `status_doctor.py`
  call had no installed script. All three are delivered now.
- **Hardening.** The scaffold smoke now *executes* installed hooks/scripts (not
  just checks files exist), and the contract manifest tracks all registered
  hooks. Plus two doc/comment polish items.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full`. The
previously-missing files (`hooks/lib/emit.sh`, `hooks/lib/patterns.sh`,
`.claude/commands/judge.md`, `scripts/status_doctor.py`) copy in automatically
(setup skips only files that already exist). To also replace the older
non-graceful `.claude/commands/retro.md`, pass `--force` or update that one file
by hand (`--force` overwrites all managed files, so review local edits first).

### From v1.3.0 to v1.3.1

**Docs-only — no action required.** Audit 2026-06-06 §4 priority-4 follow-up B4
(native-redundancy inventory). Adds the native delegation map to the
[Native Feature Mapping](#native-feature-mapping) table (what aegis keeps,
complements, or delegates vs. Checkpoints/`/rewind`, `/resume`, Auto Mode,
routines, and why) and a note in the `session-recovery` skill clarifying its
relationship to native `/resume`. No operating-contract, template, or behavior
changes; existing projects are unaffected. This completes the post-audit
B-series (B1–B4).

### From v1.2.0 to v1.3.0

**Non-breaking — additive lifecycle-completion features** (audit 2026-06-06 §4
priority-4 follow-ups B3c and B3b). With B3a (v1.2.0) these complete the
post-delivery lifecycle: ⑨ manual, ⑩ UAT, ⑫ maintenance. Existing projects keep
working; the one behavior change (UAT gate coupling) is conditional on having
defined acceptance criteria.

- **B3c — maintenance lifecycle (⑫).** A new `RUNBOOK.template.md` plus a single
  `maintenance` skill: Part A generates `docs/handover/RUNBOOK.md` (monitoring,
  triage, escalation, incident history) at ship; Part B runs the
  monitor→triage→route→record loop for production incidents, reusing
  `bug-diagnosis` + bugfix/hotfix for the actual fix. `ship-and-docs` (Step 2.6),
  `docs-sync`, and `bug-diagnosis` reference it; no new mode/phase/gate.
- **B3b — UAT execution (⑩).** A new `UAT-RESULTS.template.md` plus a `uat` skill:
  at ship, the client verifies the built product against `ACCEPTANCE.md`, records
  pass/fail + evidence per criterion, and signs off into
  `docs/handover/UAT-RESULTS.md` (`ship-and-docs` Step 2.7).
- **Gate change — `dev_ready_for_client` requires recorded UAT.** When
  `docs/requirements/ACCEPTANCE.md` exists, approving `dev_ready_for_client` is
  blocked unless `docs/handover/UAT-RESULTS.md` exists. Pass/fail is the client's
  sign-off; the machine only checks the artifact exists. Projects without
  ACCEPTANCE are unaffected (legacy behavior).

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full` to
pick up the new `maintenance`/`uat` skills and `RUNBOOK`/`UAT-RESULTS` templates.
Projects on `minimal`/`standard` get the updated `check_status.py` (the UAT gate
check) but not the new skills (those ship only in `full`).

### From v1.1.0 to v1.2.0

**Non-breaking — additive end-user manual generation** (audit 2026-06-06 §4
priority-4 follow-up B3a). No public operating-contract changes; existing
projects keep working.

- **B3a — audience-parameterized operation manual at the docs phase.** A new
  `user-manual` skill (`.claude/skills/user-manual/`) plus
  `templates/MANUAL.template.md` generate a task-oriented operation guide for the
  people who *use* or *operate* the delivered product, written so non-engineers
  can follow it.
- **`ship-and-docs` Step 2.5.** After the TO-CLIENT package is drafted,
  `ship-and-docs` reads `user-manual` and, when the product has users/operators,
  writes `docs/handover/MANUAL.md` (one procedure section per audience) and links
  it from the TO-CLIENT delivery summary. When no one uses or operates the
  product, no manual is generated and the reason is recorded in that slot.
- **`docs-sync` parity check.** For projects that warrant a manual, `docs-sync`
  verifies `docs/handover/MANUAL.md` exists and that its declared audiences
  (front-matter) map one-to-one to its procedure sections — no missing sections,
  no orphan sections — otherwise the "not applicable" reason must be recorded.
- **Registration.** The `user-manual` skill is registered in the `full` profile
  and the framework mirror; `templates/HANDOVER-TO-CLIENT.template.md` gains a
  manual slot.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=full` to
pick up the new `user-manual` skill and `MANUAL.template.md`. Projects on
`minimal`/`standard` are unaffected — the skill ships only in `full`.

### From v1.0.0 to v1.1.0

**Non-breaking — additive deterministic-assurance features** (audit 2026-06-06 §4
priority-4 follow-ups B1/B2, plus the priority 1-3 fix-forwards). No public
operating-contract changes; existing projects keep working.

- **B1 — test-strength drill at the qa gate.** `pre_approve_gate` runs
  `scripts/run-test-strength-drill.py` live at qa approval: tests must catch the
  mutants seeded into changed code, or approval is refused. Tasks with no testable
  code declare an auditable skip (`{"skip": true, "reason": "..."}`) in
  `docs/qa-reports/test-strength.drill`.
- **B2 — judge card (tri-state) at review/qa/security/deploy.** `build-judge-card.py`
  runs at approval and emits 🟢/🔴/🟡: tier-1 machine facts (changed-line stub scan,
  secret scan, fingerprint-verified test result, B1 verdict) that contradict the
  report's recorded `claims:` block hard-block (🔴); a missing/divergent
  self-attested second opinion, absent claims, or a dependency-audit concern are
  advisory (🟡), approvable via `update-gate.sh <gate> approve --ack "reason"`
  (the reason is recorded into the card). `scripts/record-test-result.py` records
  the test result the judge reads; `/judge` previews the card read-only.
- **Gate exit codes are now tri-state.** `pre_approve_gate` / `update-gate.sh`
  return 0/1/2 (was 0/1). A judge that cannot run (e.g. non-git project) yields an
  ack-able 🟡, never a hard block, so one fault cannot lock every gate.
- **Hardening (priority 1-3):** gate fail-closed behavior, deploy boundary, and
  mirror-drift detection. New scripts are registered in the mirror and `full`
  profile; agents/skills document the `claims:` convention and blind second opinion.

### From v0.12.2 to v1.0.0

**Future-proof re-architecture (F→R→A→D).** Everything since the `v0.12.2` tag,
consolidated into the v1.0.0 milestone. The old "v0.13.0" line was reframed onto
the `0.12.x` series and lands here.

**Breaking — skill renames** (Phase 0b, official-name collision avoidance). Update
any external references (e.g. uccc) to the new names:

| Old skill | New skill |
|-----------|-----------|
| `brainstorming` | `aegis-brainstorm` |
| `review` | `aegis-review-gate` |
| `security-review` | `aegis-security-gate` |

**New enforcement / behavior:**

1. **New gate hooks**: `check-skill-gate.sh` (Skill), `check-cron-gate.sh` (CronCreate),
   and Task event hooks — `check-task-created.sh` (TaskCreated → `continue:false` hard
   stop when a gate blocks a new task) and `check-task-completed.sh` (TaskCompleted →
   `exit 2` push-back).
2. **Evidence-completion enforcement** (v0.12.6): TaskCompleted pushes back when an
   approved `review`/`qa`/`security`/`deploy`/`plan` gate has no `current_refs` entry,
   or a declared ref points to a missing file. Same invariant as `check_framework_contract`.
3. **Model/effort policy**: agent frontmatter is now pinned by role tier (quality
   roles on `opus`, cost roles on `sonnet`, default `inherit`); `haiku` removed.
4. **TDD profile**: the `check-tdd.sh` backstop ships only in `full`; within `full`,
   `AEGIS_TDD_MODE=off` disables it for a session (session-start warns).
5. **Leaner rules**: `routing.md` reduced to principles + agent manifest; `CLAUDE.md`
   dropped the hard context-doc count (pull-based).
6. **Internal (behavior-unchanged)**: hook output schemas unified in `hooks/lib/emit.sh`,
   destructive patterns in `hooks/lib/patterns.sh`.

**Action for existing projects**: re-run `bash bin/setup.sh --profile=<your-profile>`
to refresh `.claude/settings.local.json` and hooks, then update any external skill
references to the renamed `aegis-*` skills above.

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

Driven by a 5-round external review (Round 1〜5, 25 issues raised, all reflected). See `docs/plans/v0130-modernization-plan.md` Rev.5 for full context. The follow-on work (Skill/Cron gates, Task event hooks, the re-architecture) shipped on the `0.12.x` line — see *From v0.12.2 to v1.0.0* above.

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

# v0.9.0 Integration Assist --- Security Review

## Review Metadata

- Reviewer: security agent (fresh context)
- Date: 2026-04-18
- Scope: v0.9.0 integration-assist skill + integration-specialist agent
- Model: Opus 4.6
- Methodology: manual source code audit, trust boundary analysis, credential flow tracing, OWASP / STRIDE review

## Threat Model

This review considers the following threat actors and attack surfaces relevant to an integration workflow that handles external service credentials:

| Actor | Capability | Motivation |
|-------|-----------|------------|
| Credential leakage via LLM context | Token/Key values read from browser snapshots remain in agent context | Inadvertent exposure through chat history, reports, or commit messages |
| Prompt injection via service page | Malicious content on an external service's setup page | Trick the agent into writing credentials to wrong locations or executing commands |
| Accidental `.env` commit | Agent or user stages `.env` without checking `.gitignore` | Credential exposure in version control history |
| Agent privilege escalation | Agent uses Bash + Write to modify framework control files | Bypass gate enforcement, alter hooks, corrupt state |
| Browser automation misuse | `$B` binary executes arbitrary URLs and fills forms | Navigation to malicious sites, unintended form submissions |
| LLM hallucination | Agent fabricates API responses or claims success without test | False sense of security, incomplete integration |

Trust boundaries:
- **integration-specialist agent** runs with `readOnly: false`, `permissionMode: default`, and full Bash access
- **$B binary** runs in user's shell with full browser session access, including cookies and auth state
- **handoff** transfers visible browser control to the user, then resumes AI control with session state preserved
- **PreToolUse hooks** (check-control-plane.sh, check-destructive.sh, check-gate.sh) gate Bash and Edit/Write commands

## Findings

### Critical (immediate fix required)

None.

### High

#### H1. `.env` staging/commit hook enforcement --- RESOLVED

**Files:** `hooks/check-secrets.sh`, `templates/hooks.template.json`

**Original issue:** The "do not commit `.env`" rule existed only as natural-language instruction in the skill and agent markdown files. No PreToolUse hook intercepted `git add .env`, `git add -A`, or `git commit` when `.env` was staged.

**Resolution:** `check-secrets.sh` added as a Bash PreToolUse hook. It enforces:
1. Denies `git add` commands that would stage secret `.env` files (`.env`, `.env.local`, `.env.production`, etc.).
2. Denies `git add -A` / `git add .` when secret `.env` files exist on disk.
3. Denies `git commit` when secret `.env` files are in the staging area.
4. Warns on Bash commands that create/write `.env` files when `.gitignore` lacks `.env` protection.

Safe variants (`.env.example`, `.env.template`, `.env.sample`) are excluded from all checks --- these files contain placeholder values and are safe to commit.

Registered in `templates/hooks.template.json`, `templates/profiles/full.json`, and `scripts/check_framework_contract.py`.

### Medium (fix recommended)

#### M1. Agent has `permissionMode: default` instead of `acceptEdits` --- Bash commands prompt the user but context may be insufficient for judgment

**File:** `.claude/agents/integration-specialist.md`, line 6

**Issue:** `permissionMode: default` means every tool call prompts the user for approval. While this is safer than `acceptEdits` for an agent with Bash access, the user may not understand what `$B fill @eN "..."` or `$B snapshot` commands do. Reflexive approval of Bash commands is a realistic risk.

**Mitigating factors:**
1. The `$B` binary is a controlled tool (gstack browse), not arbitrary command execution.
2. The `check-destructive.sh` hook catches obviously destructive patterns.
3. `maxTurns: 30` limits the total number of operations.

**Verdict:** Acceptable for v0.9.0. The alternative (`acceptEdits`) would be worse because it would auto-approve file writes. Document in the agent that users should review Bash commands, especially any that are not `$B` invocations.

#### M2. Credential values may persist in Claude's context window after `$B text @eN` extraction

**File:** `.claude/skills/integration-assist/SKILL.md`, lines 85-87

**Issue:** Step 5 instructs the agent to run `$B snapshot` and `$B text @eN` to extract Token/Key values from the browser page. The extracted text is returned as Bash output, which enters Claude's context window. From that point forward:
1. The credential exists in the conversation context until the session ends or the context is compacted.
2. If the user runs `/compact` or the context auto-compacts, the `pre-compact.sh` hook runs, but it does not scrub credential values from the summary.
3. The credential could appear in error messages, debug output, or follow-up agent reasoning.

The security rules table (line 110) says "パスワードは handoff 経由でユーザーが直接入力する" (passwords via handoff) and ".env の値をレポートやログに含めない" (do not include .env values in reports/logs). However, API keys and tokens are explicitly extracted by the agent in Step 5 via `$B text`, which means they DO enter Claude's context.

**Risk:** MEDIUM. The handoff pattern correctly prevents passwords from entering Claude's context, but API keys/tokens are extracted by the agent itself. This is a design tension: the agent needs the value to write it to `.env`, but holding it in context creates a leakage surface.

**Recommendation:**
1. Modify Step 5 to pipe the extracted value directly into `.env` within a single Bash command, minimizing context exposure: `$B text @eN | xargs -I{} printf 'SERVICE_API_KEY={}\n' >> .env`. The value still appears in Bash output, but this reduces the window.
2. Add an explicit instruction: "After writing the credential to `.env`, do not repeat, reference, or include the credential value in any subsequent output, summary, or report."
3. Consider whether `pre-compact.sh` should warn about credential-like patterns in context (regex for API key formats).

#### M3. `$B` binary path resolution trusts filesystem without integrity verification

**File:** `.claude/skills/integration-assist/SKILL.md`, lines 24-31

**Issue:** The `$B` resolution logic checks for executable binaries at two paths:
1. `$_ROOT/.claude/skills/gstack/browse/dist/browse` (project-local)
2. `~/.claude/skills/gstack/browse/dist/browse` (user-global)

There is no checksum or signature verification. If an attacker can write a malicious binary to either path (e.g., via a supply chain attack on the gstack package, or a compromised npm postinstall script), the agent would execute it with full user privileges.

**Mitigating factors:**
1. Both paths require write access to the user's project or home directory, which implies the attacker already has local access.
2. The `[ -x "$B" ]` check only verifies the file is executable, which is standard for binary resolution.
3. This is a general supply-chain concern that applies to all external binaries (node, python3, git, etc.) and is not specific to this integration.

**Verdict:** Acceptable risk for v0.9.0. This is consistent with how other tools (npm scripts, git hooks, etc.) resolve binaries. Document the assumption that the gstack browse binary is trusted.

#### M4. Agent `allowedTools` includes both `Write` and `Bash` --- broad write surface

**File:** `.claude/agents/integration-specialist.md`, lines 11-20

**Issue:** The agent has access to `Edit`, `Write`, `Bash`, `WebSearch`, `WebFetch`, `Read`, `Grep`, and `Glob`. This is one of the broadest toolsets in the framework, comparable to the `implementer` agent (which has `permissionMode: acceptEdits`). The integration-specialist combines:
- `Bash`: arbitrary command execution (including `$B`, `git`, `npm install`, etc.)
- `Write`: file creation at any path
- `Edit`: file modification at any path

Comparison with other agents:

| Agent | Bash | Write/Edit | readOnly | permissionMode |
|-------|------|-----------|----------|----------------|
| integration-specialist | Yes | Yes | false | default |
| implementer | Yes (implicit) | Yes | false | acceptEdits |
| security | No | No | true | plan |
| reviewer | No | No | true | plan |
| qa | No | No | true | plan |
| translation-specialist | No | Yes | false | default |

The integration-specialist has the same power as the implementer but with `permissionMode: default` instead of `acceptEdits`. The `default` mode is actually more cautious (user prompted for each action). However, the agent's legitimate workflow requires Bash for `$B` commands, npm/pip install, and connection tests. Write/Edit are needed for `.env` and integration code. All tools are justified.

**Mitigating factors:**
1. `permissionMode: default` prompts the user for every tool call.
2. `check-gate.sh` blocks writes to framework control files.
3. `check-control-plane.sh` blocks Bash commands referencing control plane paths.
4. `check-destructive.sh` warns on destructive operations.
5. `maxTurns: 30` provides a blast radius limit.

**Verdict:** All tools are justified for the agent's purpose. The existing hook defense-in-depth adequately constrains the broad toolset. PASS with notes.

### Low / Informational

#### L1. handoff pattern is correctly designed for credential isolation

**Files:** SKILL.md lines 69-77, agent lines 47-48, 56-57

**Analysis:** The handoff workflow is well-designed:
1. `$B handoff "message"` opens a visible browser with the same page state.
2. The user performs password entry, 2FA, and approval clicks directly in the browser.
3. `$B resume` returns control to the agent with session cookies preserved.
4. The agent never sees or processes the password.

The boundary instruction in the agent (line 48: "Never ask the user to type passwords or tokens into the chat") is reinforced by the skill's security rules table. The Known Rationalizations table (agent line 72) even addresses the case where credentials accidentally end up in chat history.

**Verdict:** PASS. The handoff pattern is the correct architectural choice for credential isolation.

#### L2. Fallback (guide mode) maintains security properties

**Files:** SKILL.md lines 66-67, 79-81, 95-97

**Analysis:** When `$B` is not available, the skill falls back to text-based guidance. In guide mode:
- Step 3: URL and instructions are presented as text (no credential content).
- Step 4: User is told to complete approval manually, no credentials flow through chat.
- Step 5: User pastes token/API key via chat. Agent writes to `.env` immediately and never repeats the value.

The Step 5 fallback has a design tension: the token enters Claude's context. However, the agent writes it to `.env` immediately, the "以後再掲しない" rule prohibits repeating the value, and the security rules prohibit including it in reports. This is less secure than the `$B` path but is the only viable option without browser automation. Passwords and 2FA codes are never accepted via chat in either mode.

**Verdict:** PASS. The fallback is inherently less secure but is an acceptable trade-off when browser automation is unavailable.

#### L3. `.gitignore` enforcement is instruction-based, not hook-enforced

**Files:** SKILL.md line 92, agent line 59

**Analysis:** Step 5 instructs the agent to "confirm `.gitignore` includes `.env` (add if missing)". This is a natural-language instruction. The agent should reliably follow it because:
1. It is a simple, concrete action (check file, add line if missing).
2. It is listed in both the skill and the agent boundaries.

However, there is no hook that verifies `.gitignore` contains `.env` before allowing a commit. This is covered by finding H1 above.

**Verdict:** Instruction is correctly specified. Hook-level enforcement added via `check-secrets.sh` (H1 resolved).

#### L4. `maxTurns: 30` is appropriate for the agent's scope

**Analysis:** The integration-specialist has `maxTurns: 30`. This is:
- Less than the implementer (50 turns).
- More than the reviewer (20 turns), security (20 turns), and translation-specialist (15 turns).

30 turns is reasonable for a workflow that includes documentation research, browser automation, credential setup, code generation, and connection testing. The blast radius is bounded.

**Verdict:** PASS.

#### L5. `disable-model-invocation: true` + `user-invocable: false` correctly scopes the skill

**File:** SKILL.md lines 4-5

**Analysis:** The skill cannot be directly invoked by the user or by other models. It is loaded only when the integration-specialist agent is activated. This prevents accidental credential workflows in unrelated contexts.

**Verdict:** PASS. Correct access control.

#### L6. Agent does not have MCP tool access (Context7, Firecrawl, Memory, etc.)

**File:** `.claude/agents/integration-specialist.md`, lines 11-20

**Analysis:** The `allowedTools` list includes `WebSearch` and `WebFetch` but not MCP tools like Context7, Firecrawl, or Memory. The skill's Step 2 uses `WebSearch` and `WebFetch` for documentation research, consistent with the agent's `allowedTools`. From a security perspective, fewer tools means a smaller attack surface.

**Verdict:** PASS. Tool references in skill and agent are now aligned.

#### L7. Known Rationalizations table provides defense against hallucination

**File:** `.claude/agents/integration-specialist.md`, lines 64-72

**Analysis:** The "Known Rationalizations" table explicitly addresses five common failure modes:
1. "The API key looks correct" --- requires running the test.
2. "The setup page might have changed" --- requires `$B snapshot`.
3. "I can't access the service" --- requires handoff.
4. "The test will probably pass" --- requires running it.
5. "Credentials are in the chat history" --- requires deletion, rotation, and handoff.

Entry 5 is particularly security-relevant: it acknowledges that credentials may accidentally enter chat and prescribes a remediation workflow (delete from `.env`, rotate, use handoff). This is excellent defensive design.

**Verdict:** PASS. Strong anti-hallucination and security awareness.

## OWASP Top 10 Relevance

| OWASP Category | Relevant? | Assessment |
|----------------|-----------|------------|
| A01 Broken Access Control | Yes | The agent has broad tool access but is constrained by `permissionMode: default` + hook defense-in-depth. No excessive permission identified beyond what the workflow requires. See M4. |
| A02 Cryptographic Failures | Yes | Credentials are directed to `.env` (not hardcoded). No encryption at rest for `.env`, but this is standard practice for local development. Hook-level enforcement via `check-secrets.sh` (H1 resolved). |
| A03 Injection | Marginal | `$B` commands use positional arguments, not shell-interpolated strings. The `$B fill @eN "value"` pattern is safe against shell injection because the values are quoted and `$B` processes them as arguments. No SQL, LDAP, or XSS surfaces. |
| A04 Insecure Design | No | The handoff pattern is a secure-by-design approach to credential isolation. |
| A05 Security Misconfiguration | Marginal | `.gitignore` enforcement is instruction-based + `check-secrets.sh` warns when `.gitignore` lacks `.env` entry (H1 resolved). |
| A06 Vulnerable Components | Marginal | `$B` binary is not integrity-verified (M3), but this applies to all external tools. |
| A07 Identification/Authentication | Yes | The handoff pattern correctly isolates authentication from the AI agent. Passwords never enter Claude's context. API tokens do enter context (M2). |
| A08 Software/Data Integrity | No | No deserialization, no CI/CD pipeline modifications. |
| A09 Logging/Monitoring | Marginal | Security rules prohibit credential values in logs/reports. No automated enforcement. |
| A10 SSRF | No | `WebSearch`/`WebFetch` are Claude Code built-in tools with their own sandboxing. `$B goto <URL>` navigates a browser, but the URL is derived from API documentation research, not user-supplied input. |

## STRIDE Threat Assessment

| Threat | Risk | Mitigation | Residual Risk |
|--------|------|-----------|---------------|
| **Spoofing** | Can the agent impersonate the user? | `$B handoff` explicitly transfers control; the agent cannot enter passwords or complete 2FA. | LOW. The agent controls the browser session pre/post-handoff, which means it can navigate on behalf of the user, but this is the intended design. |
| **Tampering** | Can the agent modify sensitive config? | `check-gate.sh` blocks writes to `.claude/`, `hooks/`, `scripts/`, `CLAUDE.md`. `check-control-plane.sh` blocks Bash commands referencing these paths. | LOW. Framework control files are protected. `.env` and application code are intentionally writable. |
| **Repudiation** | Can actions be denied? | `permissionMode: default` means the user approves each action. Turn logs exist in Claude Code session history. | LOW. Full audit trail via approval prompts. |
| **Information Disclosure** | Can credentials leak? | Passwords: isolated via handoff (PASS). API tokens: enter context via `$B text` (M2 resolved — "以後再掲しない" rule). `.env` values: instruction + hook prohibition on inclusion in reports. `.env` commit: `check-secrets.sh` hook enforces (H1 resolved). | LOW. Residual risk is token persistence in context window until session end. |
| **Denial of Service** | Can the agent break the project? | `maxTurns: 30` limits operations. `check-destructive.sh` warns on destructive commands. `permissionMode: default` requires user approval. | LOW. The agent could misconfigure an integration, but cannot delete project files without user approval. |
| **Elevation of Privilege** | Does the agent gain access beyond scope? | allowedTools list is explicit. No MCP tools. Hooks protect control plane. Agent boundaries prohibit framework modification. | LOW. The agent has broad but justified access within its scope. |

## Component Analysis

### .claude/skills/integration-assist/SKILL.md

| Property | Assessment |
|----------|-----------|
| Credential isolation (passwords) | handoff pattern prevents password entry in chat. PASS. |
| Credential isolation (API tokens) | Tokens extracted via `$B text` enter context. See M2. ACCEPTABLE with notes. |
| `.env` usage | Correctly directs credentials to `.env`. PASS. |
| `.gitignore` enforcement | Instruction + `check-secrets.sh` hook warns when `.gitignore` lacks `.env`. PASS. |
| Security rules table | Five rules covering handoff, `.env`, `.gitignore`, commit check, and log exclusion. Comprehensive. PASS. |
| Fallback mode security | Guide mode is less secure (token pasted in chat) but acceptable. PASS. |
| `$B` binary resolution | No integrity check. See M3. ACCEPTABLE. |
| Context budget | L2 (task file), loaded only for integration tasks. PASS. |

### .claude/agents/integration-specialist.md

| Property | Assessment |
|----------|-----------|
| readOnly: false | Required for `.env` and code generation. Correct. PASS. |
| permissionMode: default | More cautious than acceptEdits. Correct for Bash-enabled agent. PASS. |
| maxTurns: 30 | Appropriate blast radius. PASS. |
| allowedTools breadth | Broad but justified. All tools serve the workflow. See M4. PASS. |
| Bash access | Required for `$B`, `npm install`, connection tests. Justified. PASS. |
| Credential boundary instructions | "Never ask users to type passwords or tokens into chat." Reinforced in Boundaries and Known Rationalizations. PASS. |
| `.env` commit prohibition | Instruction + `check-secrets.sh` hook denies staging/commit. PASS. |
| Hallucination guard | Requires evidence (2xx API response) before claiming success. PASS. |
| Known Rationalizations | Addresses credential leakage scenario (entry 5). Excellent. PASS. |
| Framework file protection | `check-gate.sh` blocks writes to `.claude/`, `hooks/`, `scripts/`. PASS. |

### check-control-plane.sh coverage for integration-specialist

| Scenario | Covered? | Details |
|----------|----------|---------|
| Agent runs `$B goto <url>` | Yes (allow) | No control plane path referenced. |
| Agent runs `npm install <pkg>` | Yes (allow) | No control plane path referenced. |
| Agent runs `echo "KEY=val" >> .env` | Yes (allow) | `.env` is not a control plane path. Correct: this is intended behavior. |
| Agent runs `cat .claude/agents/integration-specialist.md` | Yes (allow) | Read-only command on control plane path. Correctly allowed by read-only check (line 100). |
| Agent runs `sed -i 's/foo/bar/' hooks/check-gate.sh` | Yes (deny) | Control plane path + write indicator. Correctly denied. |
| Agent runs `git add .env` | Yes (deny) | Covered by `check-secrets.sh` hook (H1 resolved). |

## Summary of Recommendations

| ID | Severity | Action | Status |
|----|----------|--------|--------|
| H1 | High | Add hook-level enforcement for `.env` staging/commit prevention | **RESOLVED** — `check-secrets.sh` hook added |
| M1 | Medium | Document that `permissionMode: default` requires user to review Bash commands | Accept for v0.9.0 |
| M2 | Medium | Minimize credential exposure in context; add "do not repeat credential values" instruction | **RESOLVED** — skill/agent updated with "以後再掲しない" rule |
| M3 | Medium | Document that `$B` binary is trusted without integrity verification | Accept for v0.9.0 |
| M4 | Medium | Document that broad toolset is justified; all tools serve the workflow | Accept for v0.9.0 |
| L1-L7 | Low | Informational notes | No action required |

## Verdict

**PASS** (updated from CONDITIONAL PASS after H1/M2 resolution)

H1 resolved: `check-secrets.sh` hook added — denies `.env` staging, broad `git add`, and staged `.env` commit. M2 resolved: credential boundary updated — token/API key values written to `.env` immediately and never repeated in output. The integration-assist workflow is specifically designed to generate `.env` files containing API keys and tokens. Without a hook-level safety net, the "do not commit `.env`" rule relies entirely on the agent following natural-language instructions and the user not reflexively approving `git add -A`. Given that this is the one workflow in the framework that routinely creates files containing secrets, hook-level enforcement is the appropriate defense-in-depth measure.

The handoff pattern for credential isolation is well-designed and correctly prevents passwords from entering Claude's context. The agent's broad toolset is justified by its workflow requirements and is adequately constrained by existing hooks (check-gate.sh, check-control-plane.sh, check-destructive.sh) and `permissionMode: default`. The Known Rationalizations table demonstrates strong security awareness in the agent design.

No injection vulnerabilities, no privilege escalation paths, and no trust boundary violations were found. Both primary risk surfaces have been mitigated: accidental `.env` commits are blocked by `check-secrets.sh` (H1 resolved), and credential persistence in context is addressed by the "以後再掲しない" rule (M2 resolved). Residual risk is token presence in the context window until session end or compaction.

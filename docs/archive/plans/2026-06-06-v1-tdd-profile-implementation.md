# TDD profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** check-tdd.sh に `AEGIS_TDD_MODE=off` の local escape hatch を追加し、off 時に session-start が警告、profile→strictness を CLAUDE.md/README に明文化、framework を `0.12.5` に bump する。

**Architecture:** profile=ファイル選択が既に strict(full)/off(minimal,standard) を提供している事実を明文化し、full 内で一時降格する env var を追加。未設定=strict で full の既存挙動は不変（fail-safe）。check-tdd は現状テスト未実装なので TDD で新規テストを書く。

**Tech Stack:** Bash hooks（check-tdd.sh・session-start.sh）、Python unittest（test_hook_output_schema.py・`run_hook(env=...)`）、Markdown 規約、検証スクリプト。

**設計書:** `docs/plans/2026-06-06-v1-tdd-profile-design.md`

---

## ベースライン（着手前に確認）

- `python3 -m unittest discover -s tests -q` → `Ran 183 tests ... OK`
- `python3 scripts/check_reference_drift.py` → exit 0
- `python3 scripts/check_framework_contract.py` → exit 0
- 現行 version: `FRAMEWORK_VERSION = "0.12.4"`（`scripts/check_framework_contract.py:17`）/ `framework_version: "0.12.4"`（`templates/STATUS.template.md:3`）

全コマンドは `aegis/`（`git rev-parse --show-toplevel` が `.../aegis`）で実行する。

> **⚠ footgun**:
> - `check-tdd.sh` は root/example **IDENTICAL** → 同一 Edit を両方に。
> - `session-start.sh` は root/example で**全体は差異あり**だが、末尾 `emit_context SessionStart "$CONTEXT"` 行は**両ファイル同一**。この行をアンカーに同一 Edit で advisory を直前挿入（**全文コピー禁止**）。
> - CLAUDE.md の enforcement 行は **root のみ**（example CLAUDE.md に該当行なし）。

---

## Task 1: check-tdd.sh の escape hatch（TDD）

**Files:**
- Test: `tests/test_hook_output_schema.py`（`TestPreToolUseHooks` クラス・line 251 付近に2メソッド追加）
- Modify: `hooks/check-tdd.sh`（`INPUT=$(cat)` 直後に off 分岐）
- Modify: `examples/minimal-project/hooks/check-tdd.sh`（root と同一・IDENTICAL 維持）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_hook_output_schema.py` の `class TestPreToolUseHooks`（既に `setUp` で `self.tmp = tempfile.mkdtemp(...)` を持つ）内に以下2メソッドを追加（例: `test_check_deploy_gate_deny_when_gate_pending` の手前か後ろ）:

```python
    def test_check_tdd_asks_when_no_test_changes(self):
        """AEGIS_TDD_MODE unset (strict default): prod edit without tests → ask."""
        payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
        rc, out, err = run_hook("check-tdd.sh", payload, cwd=Path(self.tmp))
        # 非空を明示 assert（`if out:` ガードだと誤って allow を返しても空振りで PASS する）
        self.assertNotEqual(out, {}, "strict default must not allow ({})")
        self.assert_pretool_decision(out, "ask", hint="check-tdd strict default")

    def test_check_tdd_off_allows(self):
        """AEGIS_TDD_MODE=off: prod edit without tests → allow (bypass)."""
        payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
        rc, out, err = run_hook(
            "check-tdd.sh", payload, cwd=Path(self.tmp), env={"AEGIS_TDD_MODE": "off"}
        )
        self.assertEqual(out, {}, "off must emit allow ({})")
```

補足: `cwd=Path(self.tmp)` は git 管理外の一時dir。`git diff` が空＝「テスト変更なし」を決定論的に再現。`src/app.ts` は check-tdd の非本番 skip（docs/scripts/.md/.json 等）に該当せず本番コード扱い。

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | grep -E "test_check_tdd|FAIL|OK|Ran"`
Expected: `test_check_tdd_asks_when_no_test_changes` は **PASS**（現行コードも ask を返す）、`test_check_tdd_off_allows` は **FAIL**（現行は env を無視し ask を返すため out が `{}` でない）。

- [ ] **Step 3: check-tdd.sh に off 分岐を実装（root）**

`hooks/check-tdd.sh` を Edit:
- old:
```bash
# Read stdin (JSON with tool_input).
INPUT=$(cat)
```
- new:
```bash
# Read stdin (JSON with tool_input).
INPUT=$(cat)

# Local escape hatch: AEGIS_TDD_MODE=off disables the TDD backstop for this session (full profile).
# Lowercase "off" only; any other value (unset/strict/invalid) keeps the strict default (fail-safe).
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
  emit_allow
  exit 0
fi
```

- [ ] **Step 4: example の check-tdd.sh に同一 Edit（IDENTICAL 維持）**

`examples/minimal-project/hooks/check-tdd.sh` に Step 3 と**完全同一**の Edit を適用。

- [ ] **Step 5: root/example が同一であることを確認**

Run: `diff hooks/check-tdd.sh examples/minimal-project/hooks/check-tdd.sh && echo IDENTICAL`
Expected: `IDENTICAL`

- [ ] **Step 6: テストを実行して両方 PASS を確認**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | grep -E "test_check_tdd|FAIL|OK"`
Expected: `test_check_tdd_asks_when_no_test_changes ... ok` と `test_check_tdd_off_allows ... ok`、FAIL なし。

- [ ] **Step 7: 全テスト緑を確認**

Run: `python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `Ran 185 tests ... OK`（既存183 + 新規2）。

- [ ] **Step 8: コミット**

```bash
git add tests/test_hook_output_schema.py hooks/check-tdd.sh examples/minimal-project/hooks/check-tdd.sh
git commit -m "$(cat <<'EOF'
feat(hooks): add AEGIS_TDD_MODE=off local escape hatch to check-tdd

In the full profile the TDD backstop is always on; AEGIS_TDD_MODE=off
lets a developer bypass it for the session (e.g. a large no-test
refactor). Unset/strict/invalid keeps the strict default (fail-safe).
Adds the first check-tdd schema tests (strict asserts non-empty ask).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: session-start advisory（off の可視化）

**Files:**
- Modify: `hooks/session-start.sh`（`emit_context SessionStart "$CONTEXT"` 直前）
- Modify: `examples/minimal-project/hooks/session-start.sh`（同一アンカー行・同一 Edit）

- [ ] **Step 1: root session-start.sh に advisory を挿入**

`hooks/session-start.sh` を Edit（`emit_context SessionStart "$CONTEXT"` は各ファイルで一意）:
- old:
```bash
emit_context SessionStart "$CONTEXT"
```
- new:
```bash
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
  CONTEXT="${CONTEXT} | [WARNING] AEGIS_TDD_MODE=off — TDD backstop disabled this session; production edits will not prompt for tests"
fi

emit_context SessionStart "$CONTEXT"
```

- [ ] **Step 2: example session-start.sh に同一 Edit**

`examples/minimal-project/hooks/session-start.sh` に Step 1 と**完全同一**の Edit を適用（末尾 `emit_context SessionStart "$CONTEXT"` 行は両ファイル同一なのでそのまま使える）。

- [ ] **Step 3: advisory を手動検証（root）**

Run: `AEGIS_TDD_MODE=off bash hooks/session-start.sh < /dev/null 2>&1 | grep -o "AEGIS_TDD_MODE=off — TDD backstop disabled this session" | head -1`
Expected: `AEGIS_TDD_MODE=off — TDD backstop disabled this session`（advisory 文字列が出力 JSON に含まれる）。STATUS.md が無い環境では session-start が早期 `emit_allow` する可能性があるため、リポジトリルートで実行すること（`docs/STATUS.md` 存在下）。

- [ ] **Step 4: off 未設定では advisory が出ないことを確認**

Run: `bash hooks/session-start.sh < /dev/null 2>&1 | grep -c "TDD backstop disabled"`
Expected: `0`（env 未設定では警告なし）。

- [ ] **Step 5: 全テスト緑を確認（session-start のスキーマ非破壊）**

Run: `python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `Ran 185 tests ... OK`。

- [ ] **Step 6: コミット**

```bash
git add hooks/session-start.sh examples/minimal-project/hooks/session-start.sh
git commit -m "$(cat <<'EOF'
feat(hooks): warn at session-start when AEGIS_TDD_MODE=off

Mirrors the CLAUDE_CODE_SUBAGENT_MODEL advisory: surfaces the disabled
TDD backstop each session so off is not silently left on.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 明文化（CLAUDE.md root + README）＋ version 0.12.5

**Files:**
- Modify: `CLAUDE.md`（root のみ・line 17）
- Modify: `README.md`（profiles 節）
- Modify: `scripts/check_framework_contract.py:17`
- Modify: `templates/STATUS.template.md:3`

- [ ] **Step 1: CLAUDE.md の enforcement 行を拡張**

`CLAUDE.md` を Edit:
- old:
```
- Hook enforcement level is set at install via `bin/setup.sh --profile`.
```
- new:
```
- Hook enforcement level is set at install via `bin/setup.sh --profile` — TDD backstop is on in `full`, off in `minimal`/`standard`. In `full`, `AEGIS_TDD_MODE=off` disables it for the session (session-start warns).
```

- [ ] **Step 2: README の profiles 節に TDD strictness を追記**

`README.md` の `Available profiles:` 行を Edit:
- old:
```
Available profiles: `minimal` (core only), `standard` (recommended), `full` (everything including agents).
```
- new:
```
Available profiles: `minimal` (core only), `standard` (recommended), `full` (everything including agents).

TDD backstop strictness follows the profile: `full` installs `check-tdd.sh` (strict — prompts when production code is edited without test changes); `minimal`/`standard` omit it (off). Within `full`, set `AEGIS_TDD_MODE=off` to disable the backstop for a single session (e.g. a large no-test refactor); session-start prints a warning while it is off. Lowercase `off` only.
```

> 着手前に `grep -n "Available profiles:" README.md` で行の存在を確認。複数あれば profiles 節（setup 手順付近）の方を対象にする。

- [ ] **Step 3: FRAMEWORK_VERSION を 0.12.5 へ**

`scripts/check_framework_contract.py:17`:
- old: `FRAMEWORK_VERSION = "0.12.4"`
- new: `FRAMEWORK_VERSION = "0.12.5"`

- [ ] **Step 4: STATUS.template.md の framework_version を 0.12.5 へ**

`templates/STATUS.template.md:3`（contract が version sync を FAIL 強制するため Step 3 と対で）:
- old: `framework_version: "0.12.4"`
- new: `framework_version: "0.12.5"`

- [ ] **Step 5: CLAUDE.md word budget を確認**

Run: `python3 -c "print(len(open('CLAUDE.md').read().split()))"`
Expected: 650 以下（拡張後 ~490 程度）。

- [ ] **Step 6: contract / drift / 全テストを実行**

Run: `python3 scripts/check_framework_contract.py; echo "contract=$?"; python3 scripts/check_reference_drift.py; echo "drift=$?"; python3 -m unittest discover -s tests -q 2>&1 | tail -2`
Expected: `contract=0`（word≤650・version sync）、`drift=0`（#7 version 一致）、`Ran 185 tests ... OK`。

- [ ] **Step 7: コミット**

```bash
git add CLAUDE.md README.md scripts/check_framework_contract.py templates/STATUS.template.md
git commit -m "$(cat <<'EOF'
docs(rules): document TDD backstop profile mapping + escape hatch, bump 0.12.5

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: bookkeeping ＋ 実装計画 commit ＋ memory ＋ push（要ユーザー確認）

**Files:**
- Modify: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`（§3 KEEP TDD 行 / §11）
- Add: `docs/plans/2026-06-06-v1-tdd-profile-implementation.md`（本書）
- Modify: memory `aegis-rearchitecture-direction.md`（git 管理外）

- [ ] **Step 1: §3 KEEP の TDD 行に完了注記**

`docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` の §3 🔒 KEEP テーブルの `**TDD**` 行（`check-tdd.sh`…の行）の「再設計後」セル末尾に追記。着手前に `grep -n "check-tdd.sh\|TDD" docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md` で正確な行を確認してから:
- 追記内容: ` → **完了**（2026-06-06・v0.12.5・profile→strictness 明文化＋`AEGIS_TDD_MODE=off` escape hatch＋session-start advisory。red→green 自動検証は非スコープ・heuristic backstop 維持。`2026-06-06-v1-tdd-profile-design.md`）`

- [ ] **Step 2: §11 チェックリストに TDD 項目を追記**

§11 の完了条件リストに行を追加（routing/context と同様の形式）:
- 追記: `- [x] TDD backstop+profile 化（2026-06-06・v0.12.5・明文化＋escape hatch＋advisory）`

- [ ] **Step 3: bookkeeping をコミット**

```bash
git add docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md
git commit -m "$(cat <<'EOF'
docs(plans): mark TDD profile done in rearchitecture design

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: 実装計画を tracked 化**

```bash
git add docs/plans/2026-06-06-v1-tdd-profile-implementation.md
git commit -m "$(cat <<'EOF'
docs(plans): track TDD profile impl plan as dated snapshot

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: memory の進捗を更新**

`aegis-rearchitecture-direction.md` に TDD profile 完了を追記（Phase R 第3手・main・v0.12.5。check-tdd に `AEGIS_TDD_MODE=off` escape hatch、off 時 session-start advisory、profile→strictness 明文化。red→green 自動検証は非スコープ）。未着手リストから「TDD profile」を外す。git 管理外。

- [ ] **Step 6: push 前の最終状態確認**

Run: `git log --oneline origin/main..HEAD`
Expected: 6コミット — `de44a87`（設計書）、Task 1・2・3 と Task 4 Step 3・4 のコミット。

- [ ] **Step 7: push（ユーザー確認の上で実行）**

実行直前にユーザーへ push 可否を確認してから:

```bash
git push origin main
```

Expected: origin/main へ反映。`docs/architecture-overview.pdf` は含めない。

---

## Self-Review

**Spec coverage（設計書の各部品 → タスク対応）:**
- 部品① check-tdd escape hatch → Task 1（TDD: テスト先行）
- 部品② session-start advisory → Task 2
- 部品③ 明文化（CLAUDE.md root + README）→ Task 3 Step 1-2
- 部品④ テスト2件 → Task 1 Step 1（strict 非空 assert / off allow）
- version 0.12.5 → Task 3 Step 3-4
- footgun（check-tdd IDENTICAL / session-start 共有アンカー / CLAUDE root のみ）→ ベースライン警告＋各 Step に明記
- Verification（185 tests・contract・drift・手動 advisory）→ Task 1 Step 6-7・Task 2 Step 3-5・Task 3 Step 5-6
- 完了後 bookkeeping → Task 4

**Placeholder scan:** 各 Edit に厳密 old/new、テストは完全コード、コマンドは期待出力付き。§3 KEEP 行と README は「着手前に grep 確認」を明記。プレースホルダなし。

**Type/identifier consistency:** env 名 `AEGIS_TDD_MODE`、値 `off`（小文字）、bash 判定 `[ "${AEGIS_TDD_MODE:-}" = "off" ]` を全タスク一貫。version は old `0.12.4` → new `0.12.5` 一貫。テストメソッド名 `test_check_tdd_asks_when_no_test_changes` / `test_check_tdd_off_allows` を Task 1 内で一貫。advisory 文字列は session-start（Task 2）と一致。

ギャップ: session-start advisory のテストは無し（Task 2 Step 3-4 で手動検証）。SessionStart テストクラスが現状存在せず、文字列 append で低リスクのため意図的に手動。欠落でなく設計どおり。

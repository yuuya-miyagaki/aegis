# Aegis Foundation (emit.sh-centric) Implementation Plan — Phase F (revised after Round 1 review)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hook 出力スキーマの手書き重複を `hooks/lib/emit.sh` に集約し（次回 CC スキーマ変更を1ファイル修正に）、検知パターンを `patterns.sh` に隔離し、版・状態の棚卸しで土台を整える。**挙動は1バイトも変えない。**

**Architecture:** Round 1/2 セカンドオピニオンの判定（全面 v1.0.0 = NO-GO、emit.sh 中心の縮約 Foundation = 条件付き GO）を反映。3 サブフェーズに分割: **F0**=棚卸し（STATUS/version/v0.13 実装済み）、**F1**=emit.sh（**pure-bash・fail-closed**）+ 全 hook 出力置換、**F2**=patterns.sh（実装真実）。**seed manifest は Round 2 J-1 に従い Foundation から外す（後回し）**。manifest/context/inherit/TDD profile などの哲学変更も **本計画のスコープ外**（別フェーズで分割審査）。

**Tech Stack:** Bash（hooks, macOS 既定 bash 3.2 互換）、Python 3.9 標準ライブラリ `unittest`（**pytest は本環境に未導入**）、JSON。**新規外部依存なし**。

**Review resolution（Round 1/2 反映）:**
- ① 全面再アーキ撤回 → 本計画は Foundation のみ。
- ② manifest は patterns/schema をミラーしない。さらに **Round 2 J-1: seed manifest 自体を Foundation から外す**（version 二重書きのみで便益薄・YAGNI）。実消費者が出来た後続フェーズで新設。
- ③ emit.sh の python3 依存撤廃 → **pure-bash 実装**（外部 interpreter ゼロ・外部依存ゼロ、fail-open しない。escape は bash command substitution の subshell を使う＝外部プログラムではない）。
- ③' Round 2 P1: 静的 fail-closed テストは **コメント行を除いた実行コードのみ**を検査（emit.sh コメントの "python3/jq" 言及で自己矛盾しないように）。
- ④ inherit 従属 → model ポリシーは本計画スコープ外（design doc の事実誤りは別途訂正）。
- ⑨ STATUS 実態 drift を **F0 として最優先**。
- Round 2 J-2: emit escape は構造的 JSON 文字のみ対象。**外部断片を reason に混ぜる call site は printable に sanitize する方針を emit.sh に明記**。
- 新規: 全テストコマンドを `python3 -m unittest` に統一。テスト数は現状 **174**。version owner を F0 で確定。

---

## File Structure

| File | 責務 | 区分 | サブフェーズ |
|---|---|---|---|
| `docs/STATUS.md` | 実態同期（v0.13 実装済み棚卸し反映） | 改修 | F0 |
| `scripts/check_framework_contract.py` | version 単一 owner に確定 | 改修 | F0 |
| `docs/plans/v0130-implementation-inventory.md` | v0.13 実装済み/未済の棚卸し記録 | 新規 | F0 |
| `hooks/lib/emit.sh` | hook 出力スキーマの単一実装（pure-bash） | 新規 | F1 |
| `tests/test_emit_lib.py` | emit.sh 出力契約 + fail-closed（no-interpreter）テスト | 新規 | F1 |
| `hooks/*.sh`（16本） | 出力サイトを emit.sh へ置換（挙動不変） | 改修 | F1 |
| `hooks/lib/patterns.sh` | 検知パターンのデータ（実装真実・単一真実） | 新規 | F2 |
| `hooks/check-destructive.sh` / `check-secrets.sh` | パターンを patterns.sh から source | 改修 | F2 |
| ~~`aegis.manifest.json` / `tests/test_manifest.py` / drift 拡張~~ | **Round 2 J-1 で Foundation から除外（後回し）** | — | — |

依存順: **F0 → F1 → F2**。F1 内は emit.sh→置換。

---

# F0 — 棚卸し（STATUS / version / v0.13 実装済み）

> Round 1 ⑨ + 新規論点(version 割れ)。コードを触る前に「いま何がどの版で、どこまで実装済みか」を確定する。

## Task F0-1: v0.13.0 実装済み/未済の棚卸し

**Files:**
- Create: `docs/plans/v0130-implementation-inventory.md`

- [ ] **Step 1: 実態を機械的に確認**

Run:
```bash
ls hooks/check-skill-gate.sh hooks/check-cron-gate.sh hooks/check-task-created.sh hooks/check-task-completed.sh 2>&1
python3 -m unittest discover -s tests -v 2>&1 | tail -1
git -C . log --oneline -5
```
Expected: 4 hook すべて存在。`Ran 174 tests`. 直近 ship が v0.12.2。

- [ ] **Step 2: 棚卸し記録を書く**

`docs/plans/v0130-implementation-inventory.md` に、v0130-modernization-plan.md の各 Task（0a/0b/1/2/3）について「実装済み / 部分 / 未着手」を列挙。最低限:
- Phase 0a（hook schema 移行 + if 削除）: **済**（v0.12.2 ship）
- Phase 0b: check-skill-gate / check-cron-gate / check-task-created / check-task-completed = **ファイル存在・テスト有り**、スキル改名3件 = **要確認**、extract_exit_code 両対応 = **済**（lib/extract-input.sh）
- Phase 1/2/3 = 未着手（棚卸しで確定）

- [ ] **Step 3: コミット**

```bash
git add docs/plans/v0130-implementation-inventory.md
git commit -m "docs: inventory v0.13.0 implemented vs pending before Foundation work"
```

## Task F0-2: version 単一 owner の確定

**Files:**
- Modify: `scripts/check_framework_contract.py`, `docs/STATUS.md`

- [ ] **Step 1: 現状の不一致を確認**

Run:
```bash
grep -n 'FRAMEWORK_VERSION' scripts/check_framework_contract.py | head -1
grep -n 'framework_version' docs/STATUS.md templates/STATUS.template.md
git tag | tail -3
```
Expected: contract=`0.12.0`（stale）、STATUS=`0.13.0-pre`、最新 tag=`v0.12.2`。

- [ ] **Step 2: owner ルールを確定（決定事項）**

- **単一 owner = `scripts/check_framework_contract.py` の `FRAMEWORK_VERSION`**（既に `check_reference_drift.py:check_template_version` が canonical 参照源にしている）。
- ルール: `FRAMEWORK_VERSION` = **最後に ship した版**。`docs/STATUS.md:framework_version` = **作業中の版**（`-pre` 可）。両者が違ってよいのは「作業中 > 最後の ship」の時のみ。
- 不整合の修正: `FRAMEWORK_VERSION` を実際の最終 ship `0.12.2` に更新（`0.12.0` は bump 漏れ）。STATUS は `0.13.0-pre` 維持（作業中）。

- [ ] **Step 3: FRAMEWORK_VERSION を 0.12.2 に修正**

`scripts/check_framework_contract.py:17` を編集:
```python
FRAMEWORK_VERSION = "0.12.2"
```

- [ ] **Step 4: テンプレ version 整合を確認**

Run: `python3 scripts/check_reference_drift.py`
Expected: `check_template_version` の WARNING が出れば、`templates/*.template.md` の `framework_version` を `0.12.2` に揃える（STATUS.template は作業中版の規約に従う）。最終的に終了コード 0。

- [ ] **Step 5: 契約テストと全テスト**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`（174 tests）。

- [ ] **Step 6: コミット**

```bash
git add scripts/check_framework_contract.py docs/STATUS.md templates/
git commit -m "fix: reconcile version owner to FRAMEWORK_VERSION (0.12.0→0.12.2 bump-miss)"
```

---

# F1 — emit.sh（pure-bash・fail-closed）+ 全 hook 出力置換

## Task F1-1: `hooks/lib/emit.sh` を pure-bash で実装

**Files:**
- Create: `hooks/lib/emit.sh`
- Test: `tests/test_emit_lib.py`

- [ ] **Step 1: 失敗テストを書く（契約 + fail-closed）**

`tests/test_emit_lib.py`:

```python
#!/usr/bin/env python3
"""Contract + fail-closed tests for hooks/lib/emit.sh (the single emitter).

Run: python3 -m unittest tests.test_emit_lib -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMIT = ROOT / "hooks" / "lib" / "emit.sh"


def emit(call: str) -> tuple[int, object]:
    """Source emit.sh and run one function call. Returns (rc, parsed_or_raw)."""
    script = f'source "{EMIT}"\n{call}\n'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    out = r.stdout.strip()
    try:
        parsed = json.loads(out) if out else {}
    except json.JSONDecodeError:
        return r.returncode, out
    return r.returncode, parsed


class TestEmitContract(unittest.TestCase):
    def test_emit_allow_is_empty_object(self):
        rc, out = emit("emit_allow")
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})

    def test_emit_deny_shape(self):
        rc, out = emit("emit_deny 'no edits allowed'")
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertEqual(hso["permissionDecisionReason"], "no edits allowed")

    def test_emit_ask_shape(self):
        rc, out = emit("emit_ask 'confirm please'")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_emit_block_shape(self):
        rc, out = emit("emit_block 'gate tampered'")
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "gate tampered")
        self.assertNotIn("permissionDecision", out)

    def test_emit_context_shape(self):
        rc, out = emit("emit_context 'SessionStart' 'hello world'")
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SessionStart")
        self.assertEqual(hso["additionalContext"], "hello world")

    def test_emit_continue_false_shape(self):
        rc, out = emit("emit_continue_false 'plan gate pending'")
        self.assertEqual(out["continue"], False)
        self.assertEqual(out["stopReason"], "plan gate pending")
        self.assertNotIn("decision", out)

    def test_escaping_quotes_newlines_backslash(self):
        """Quotes, newline, backslash must produce valid JSON that round-trips."""
        rc, out = emit('emit_deny \'a "q" \\ and\nnewline\'')
        self.assertEqual(
            out["hookSpecificOutput"]["permissionDecisionReason"],
            'a "q" \\ and\nnewline',
        )


class TestEmitFailClosed(unittest.TestCase):
    """Round 1 ③: the deny/block output path must NOT depend on any external
    interpreter (python3/jq/node), so it can never fail open when one is absent."""

    def test_emit_sh_has_no_interpreter_dependency(self):
        # Check EXECUTABLE code only — full-line comments may legitimately
        # discuss the rationale (e.g. "no python3/jq"). Strip lines whose first
        # non-space char is '#'.
        code = "\n".join(
            line
            for line in EMIT.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        for forbidden in ("python3", "python ", "jq ", "node "):
            self.assertNotIn(
                forbidden, code,
                f"emit.sh code must not invoke an external interpreter (found '{forbidden.strip()}'); "
                "the deny/block path must not fail open if it is missing",
            )

    def test_deny_valid_json_with_only_coreutils_path(self):
        """Even with a minimal PATH (no python3), emit_deny must still emit valid blocking JSON."""
        script = f'source "{EMIT}"\nemit_deny "blocked"\n'
        r = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        out = json.loads(r.stdout.strip())
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m unittest tests.test_emit_lib -v`
Expected: FAIL（`emit.sh` 未作成 → source エラーで全ケース FAIL）

- [ ] **Step 3: emit.sh を pure-bash で実装**

`hooks/lib/emit.sh`:

```bash
#!/usr/bin/env bash
# Single source of truth for Aegis hook OUTPUT JSON schemas.
#
# No external interpreter, no external dependency. Escaping uses a bash
# command substitution (a subshell, not an external program), so the
# security-critical deny/block output path NEVER depends on an external
# runtime and can never fail open when one is missing.
# When Claude Code changes a hook output schema, update ONLY this file.
#
# Escaping scope: _aegis_json_escape handles the structural JSON characters
# (backslash, double-quote, newline, tab, CR) found in developer-authored
# reason strings. Call sites that embed EXTERNAL fragments (cron prompts,
# task subjects, file paths, command fragments) into a reason MUST sanitize
# them to printable text first; raw control bytes (0x01-0x08 etc.) are out of
# scope here.
#
# Schema reference (verified 2026-06-05):
#   PreToolUse:            hookSpecificOutput.{permissionDecision, permissionDecisionReason}
#   PostToolUse / PreCompact(block) / Stop / SubagentStop: top-level {decision:"block", reason}
#   PostToolUseFailure / SessionStart / PreCompact(allow) / UserPromptSubmit:
#                          hookSpecificOutput.{hookEventName, additionalContext}
#   TaskCreated (hard stop): top-level {continue:false, stopReason}
#
# Source: source "$(dirname "$0")/lib/emit.sh"

# JSON-escape a string for a double-quoted JSON value. Pure bash parameter
# expansion (works in bash 3.2). Handles the characters that occur in
# developer-authored reason strings: backslash, double-quote, newline, tab, CR.
_aegis_json_escape() {
  local s=$1
  s=${s//\\/\\\\}     # backslash FIRST
  s=${s//\"/\\\"}     # double quote
  s=${s//$'\n'/\\n}   # newline
  s=${s//$'\t'/\\t}   # tab
  s=${s//$'\r'/\\r}   # carriage return
  printf '%s' "$s"
}

# Allow / passthrough.
emit_allow() { printf '{}\n'; }

# PreToolUse decision. $1=decision(deny|ask) $2=reason
emit_pretool() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' \
    "$1" "$(_aegis_json_escape "$2")"
}
emit_deny() { emit_pretool deny "$1"; }
emit_ask()  { emit_pretool ask  "$1"; }

# Top-level block (PostToolUse, PreCompact-block, Stop, SubagentStop). $1=reason
emit_block() {
  printf '{"decision":"block","reason":"%s"}\n' "$(_aegis_json_escape "$1")"
}

# hookSpecificOutput.additionalContext. $1=hookEventName $2=additionalContext
emit_context() {
  printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' \
    "$1" "$(_aegis_json_escape "$2")"
}

# TaskCreated hard stop. $1=stopReason
emit_continue_false() {
  printf '{"continue":false,"stopReason":"%s"}\n' "$(_aegis_json_escape "$1")"
}
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m unittest tests.test_emit_lib -v`
Expected: PASS（9 tests: contract 7 + fail-closed 2）

- [ ] **Step 5: コミット**

```bash
git add hooks/lib/emit.sh tests/test_emit_lib.py
git commit -m "feat(hooks): add pure-bash emit.sh as single source of hook output schema (fail-closed)"
```

## Task F1-2: 全 hook の出力サイトを emit.sh へ置換（挙動不変）

**Files (Modify):** 16 本。各 hook 冒頭の既存 `source ".../lib/extract-input.sh"` の隣に `source "${SCRIPT_DIR}/lib/emit.sh"` を追加（SCRIPT_DIR 変数名は各 hook の既存定義に合わせる。session-start.sh など `lib/` を source していない hook は SCRIPT_DIR を解決して追加）。

置換規則（**reason は生のまま渡す**。各 hook 内の手書きエスケープ `sed 's/"/\\"/g'` や `$ESCAPED`/`$WARN_ESCAPED` 生成行は**削除**し、元文字列を emit へ渡す）:

| 旧 | 新 |
|---|---|
| `echo '{}'` | `emit_allow` |
| `printf '{"hookSpecificOutput":{...,"permissionDecision":"deny",...%s...}}\n' "$X"` | `REASON=$(printf '...%s...' "$X"); emit_deny "$REASON"` |
| 同 `"ask"` | `emit_ask "$REASON"` |
| `printf '{"decision":"block","reason":"...%s..."}\n' "$X"` | `REASON=$(printf '...%s...' "$X"); emit_block "$REASON"` |
| `printf '{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"..."}}\n'` | `emit_context PostToolUseFailure "..."` |
| `printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ESCAPED"` | `emit_context SessionStart "$RAW"`（escape 行削除） |
| `printf '{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":"%s"}}\n' "$ESCAPED"` | `emit_context PreCompact "$RAW"` |
| `printf '{"continue":false,"stopReason":"%s"}\n' "$X"` | `emit_continue_false "$X"` |

**全置換サイト（grep 確定済みチェックリスト）:**

- [ ] **Step 1: `emit_allow`（passthrough・全 hook の `echo '{}'`）**

`check-deploy-gate.sh`:20,27,37,53 / `check-cron-gate.sh`:39,56 / `check-client-info.sh`:24,31,38,45 / `check-control-plane.sh`:32,43,75,83,90,105 / `check-gate.sh`:19,28,35,45,59,83 / `check-secrets.sh`:19,127 / `check-deploy-mcp-gate.sh`:18,37 / `check-destructive.sh`:18,42,111 / `check-task-created.sh`:66,72,94 / `check-tdd.sh`:18,28,38,63 / `pre-compact.sh`:27 / `check-task-completed.sh`:61,66,88 / `check-skill-gate.sh`:34,51 / `post-bash.sh`:31 / `post-status-audit.sh`:37,44,119 / `session-start.sh`:11

- [ ] **Step 2: `emit_deny`（PreToolUse deny）**

`check-deploy-gate.sh`:49 / `check-client-info.sh`:50 / `check-control-plane.sh`:112 / `check-gate.sh`:48,62,73,79 / `check-secrets.sh`:32,44,68,87,97,102 / `check-deploy-mcp-gate.sh`:33

例（`check-gate.sh`:48）before:
```bash
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[integrity] Template edit blocked during project work (task_type=%s). Templates are framework-controlled files."}}\n' "$TASK_TYPE"
```
after:
```bash
REASON=$(printf '[integrity] Template edit blocked during project work (task_type=%s). Templates are framework-controlled files.' "$TASK_TYPE")
emit_deny "$REASON"
```

- [ ] **Step 3: `emit_ask`（PreToolUse ask）**

`check-cron-gate.sh`:51 / `check-secrets.sh`:117,121 / `check-destructive.sh`:107-109（`WARN_ESCAPED` 行削除→ `emit_ask "[careful] $WARN"`）/ `check-tdd.sh`:61 / `check-skill-gate.sh`:45

- [ ] **Step 4: `emit_block`（PostToolUse / PreCompact block）**

`pre-compact.sh`:70（`$ESCAPED` の手書き escape 削除→生 reason）/ `post-status-audit.sh`:63,80,99,105

- [ ] **Step 5: `emit_context`（additionalContext 系）**

`post-bash.sh`:29 → `emit_context PostToolUseFailure "[ReAct] テスト失敗。Observe: エラー出力を読む → Think: 原因仮説1つ → Act: 最小変更1つ。複数変更を同時にしない。"`
`pre-compact.sh`:79 → `emit_context PreCompact "$RAW_MSG"`（escape 行削除）
`session-start.sh`:213 → `emit_context SessionStart "$RAW_MSG"`（escape 行削除）

- [ ] **Step 6: 全テスト実行（挙動不変の証明）**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`。**174 + emit 9 = 183 tests、FAIL ゼロ**。

> FAIL 時は二重エスケープ（escape 削除漏れ）か `%s` 引数順を疑う。

- [ ] **Step 7: 「手書き JSON 全廃」を機械確認**

Run: `grep -rn "printf '{" hooks/*.sh; echo "exit=$?"`
Expected: **0 件**（`exit=1` = grep ノーマッチ）。残れば置換漏れ。

- [ ] **Step 8: コミット**

```bash
git add hooks/
git commit -m "refactor(hooks): route all hook output through emit.sh (behavior-preserving)"
```

---

# F2 — patterns.sh（検知パターンの単一真実）

> Round 1 ②: 検知パターンは **patterns.sh が単一真実**（manifest にミラーしない）。Round 2 J-1: seed manifest 自体も Foundation から外した（下記 DEFERRED 参照）。よって F2 は patterns.sh の抽出のみ。

## Task F2-1: `hooks/lib/patterns.sh` 抽出 + 2 hook リファクタ

**Files:**
- Create: `hooks/lib/patterns.sh`
- Modify: `hooks/check-destructive.sh`, `hooks/check-secrets.sh`

- [ ] **Step 1: patterns.sh を作成（パターンの単一真実）**

`hooks/lib/patterns.sh`:

```bash
#!/usr/bin/env bash
# Detection PATTERN DATA for Aegis hooks. THIS FILE IS THE SINGLE SOURCE OF
# TRUTH for detection patterns (not mirrored in the manifest).
# Source: source "$(dirname "$0")/lib/patterns.sh"

# High-risk credential FILE globs (git add deny 対象).
AEGIS_SECRET_FILE_GLOBS=("*.pem" "id_rsa" "*credentials*.json" "service-account*.json")

# Destructive patterns vs RAW command ($CMD). Parallel arrays: regex ⇒ warning.
# (rm -r は safe-targets 例外があるため check-destructive.sh 側で個別判定。)
AEGIS_DESTRUCTIVE_CMD_REGEX=(
  'git\s+push\s+.*(-f\b|--force)'
  'git\s+reset\s+--hard'
  'git\s+(checkout|restore)\s+\.'
  'git\s+branch\s+(-[a-zA-Z]*[dD]\b|--delete)'
  'git\s+(checkout|restore)\s+--\s+'
  'git\s+clean\s+.*-f'
  'git\s+filter-branch'
  'git\s+update-ref\s+-d'
  'git\s+reflog\s+expire.*--expire=now'
  'npx\s+rimraf'
  'find\s+.+\s+-delete'
)
AEGIS_DESTRUCTIVE_CMD_WARN=(
  "Destructive: git force-push rewrites remote history."
  "Destructive: git reset --hard discards uncommitted changes."
  "Destructive: discards all uncommitted working tree changes."
  "Destructive: branch deletion."
  "Destructive: discards changes to specific files."
  "Destructive: git clean removes untracked files."
  "Destructive: git filter-branch rewrites repository history (irreversible)."
  "Destructive: git update-ref -d deletes a ref permanently."
  "Destructive: git reflog expire --expire=now wipes reflog (no recovery)."
  "Destructive: npx rimraf bulk-deletes files recursively."
  "Destructive: find -delete bulk-deletes matching files."
)

# Destructive patterns vs LOWER-cased command ($CMD_LOWER).
AEGIS_DESTRUCTIVE_LOWER_REGEX=('drop\s+(table|database)' '\btruncate\b')
AEGIS_DESTRUCTIVE_LOWER_WARN=("Destructive: SQL DROP detected." "Destructive: SQL TRUNCATE detected.")
```

- [ ] **Step 2: check-destructive.sh の if チェーンをループへ（挙動不変）**

`hooks/check-destructive.sh` の line 47-105（`WARN=""` から最後の高リスク if まで）を以下に置換。**rm -r safe-targets 特例（line 24-45）は変更しない。** 冒頭 `source` 群に `source "${SCRIPT_DIR}/lib/patterns.sh"` を追加:

```bash
WARN=""

if printf '%s' "$CMD" | grep -qE 'rm\s+(-[a-zA-Z]*r|--recursive)' 2>/dev/null; then
  WARN="Destructive: recursive delete (rm -r). Permanently removes files."
fi

if [ -z "$WARN" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_LOWER_REGEX[@]}"; do
    if printf '%s' "$CMD_LOWER" | grep -qE "${AEGIS_DESTRUCTIVE_LOWER_REGEX[$i]}" 2>/dev/null; then
      WARN="${AEGIS_DESTRUCTIVE_LOWER_WARN[$i]}"; break
    fi
  done
fi

if [ -z "$WARN" ]; then
  for i in "${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}"; do
    if printf '%s' "$CMD" | grep -qE "${AEGIS_DESTRUCTIVE_CMD_REGEX[$i]}" 2>/dev/null; then
      WARN="${AEGIS_DESTRUCTIVE_CMD_WARN[$i]}"; break
    fi
  done
fi
```

（emit_ask 化は F1-2 Step3 で実施済み。本 Step は matching のみ patterns.sh ループへ。）

- [ ] **Step 3: check-secrets.sh の高リスク glob を patterns.sh 参照に**

`hooks/check-secrets.sh` 冒頭 `source` 群に `source "${SCRIPT_DIR}/lib/patterns.sh"` を追加。ファイル内でハードコードされた高リスク拡張子リテラル（`*.pem` / `id_rsa` / `*credentials*.json` / `service-account*.json`）を判定する箇所を `AEGIS_SECRET_FILE_GLOBS` 配列ループに置換。**git add 解析・cached/find scan の判定フローは変えない**（挙動不変）。置換対象は該当 glob リテラル出現位置を grep で特定。

- [ ] **Step 4: secrets/destructive テストで挙動不変を確認**

Run: `python3 -m unittest tests.test_hook_output_schema -v 2>&1 | grep -E "Destructive|Secrets|destructive|secrets|OK|FAIL"`
Expected: `TestCheckDestructiveExtensions`・`TestCheckSecretsHighRisk`・`TestCheckSecretsBroadStaging` ほか全緑。

- [ ] **Step 5: 全テスト**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -3`
Expected: `OK`（FAIL ゼロ）。

- [ ] **Step 6: コミット**

```bash
git add hooks/lib/patterns.sh hooks/check-destructive.sh hooks/check-secrets.sh
git commit -m "refactor(hooks): isolate detection patterns into patterns.sh (single source of truth)"
```

## Task F2-2 / F2-3: seed manifest + manifest drift — DEFERRED（Round 2 J-1）

Round 2 レビュー J-1 の推奨に従い、**seed manifest と manifest drift チェックは Foundation から外す**。
理由: 現状の唯一の消費者が「version の二重書き（manifest.version == FRAMEWORK_VERSION）」の確認だけで便益が薄く、YAGNI に反する。`aegis.manifest.json` は **最初の実消費者（後続フェーズの enforcement.tdd / model 同期 等）が出来た時に新設**する。

→ Foundation の本丸 `emit.sh`（F1）/ `patterns.sh`（F2-1）はこれに依存せず単独で完結する。version owner の確定（0.12.0→0.12.2）は **F0-2 で実施済み**なので、manifest が無くても version は一貫する。

---

## Verification（Foundation 完了条件）

1. `python3 -m unittest discover -s tests -v` 全 PASS（174 既存 + 9 新規（emit_lib）= 183、**FAIL ゼロ**）= 挙動不変の証明
2. `grep -rn "printf '{" hooks/*.sh` が **0 件**（全出力 emit.sh 経由）
3. `bash -c 'source hooks/lib/emit.sh; emit_deny x' | head` が valid JSON、**emit.sh の実行コード（コメント除く）に `python3`/`jq` が無い**（fail-closed）
4. `python3 scripts/check_reference_drift.py` 終了コード 0（既存どおり PASS、本計画では未変更）
5. version owner が単一（FRAMEWORK_VERSION=0.12.2）に確定
6. v0.13 棚卸し記録が存在し、A フェーズ（後続）のスコープ二重計上を防ぐ

---

## スコープ外（後続フェーズで分割審査 — Round 1/2 で合意）

- **seed manifest + manifest drift（Round 2 J-1）= Foundation から除外。実消費者が出来た時に新設**
- manifest 拡張（role_defaults / enforcement / profiles）= 実消費者が出来てから
- model ポリシー（inherit-first と review/security の明示固定）= design doc の事実誤り訂正と併せて別フェーズ
- context 予算 → observability（Read 回数・doc サイズ計測）への移行
- TDD profile（strict 既定、advisory=プロトタイプ、off=minimal/local のみ）
- drift の advisory→FAIL 昇格運用（外部揮発値は advisory 継続）

---

## Self-Review

**1. Spec coverage（Round 1/2）:** ①縮約=Foundation のみ ✓ ②manifest 非ミラー + **Round 2 J-1 で seed manifest を除外** ✓ ③python3 撤廃=F1-1 pure-bash + fail-closed test ✓ ③'静的テストはコメント除外で自己矛盾解消 ✓ ④inherit=スコープ外明示 ✓ ⑨STATUS/version 棚卸し=F0 ✓ J-2 escape sanitize 方針=emit.sh コメントに明記 ✓ 新規(pytest/test数/version owner)=全コマンド unittest・183・F0-2 ✓

**2. Placeholder scan:** check-secrets.sh F2-1 Step3 の「glob リテラル位置を grep で特定」のみ実行時特定（対象文字列は明示済み）。他に TBD/TODO なし。

**3. Name consistency:** emit 関数（emit_allow/deny/ask/block/context/continue_false + _aegis_json_escape）F1-1 定義 ⟷ F1-2 使用一致。patterns 配列（AEGIS_SECRET_FILE_GLOBS / AEGIS_DESTRUCTIVE_CMD_REGEX/_WARN / _LOWER_REGEX/_WARN）F2-1 定義 ⟷ check-destructive 改修一致。manifest/`check_manifest_sync` は Round 2 J-1 で Foundation から除外済み（参照残骸なし）。

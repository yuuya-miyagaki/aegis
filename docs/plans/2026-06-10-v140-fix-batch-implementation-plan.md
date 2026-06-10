# 実装計画 — v1.4.0 fix batch（P2/P3/K-2 一括 fix-forward＋failure ポリシー表＋B1 恒久修正）
<!-- 正本: subagent-dev skill -->

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans または superpowers:subagent-driven-development でタスク単位に実行する。チェックボックスで進捗管理。

## 目的

- この変更で達成すること: 進化レビュー（docs/evolution-review-2026-06-10.md §4）の P2-1〜P2-6・P3-1〜P3-6・K-2 を一括修正し、全 hook の failure 時挙動を `docs/hook-failure-policy.md`（宣言）＋ `tests/test_failure_policy.py`(実発火突合) で恒久固定する。B1 ドリルの docs/ 除外も同梱。v1.4.0 minor で締める。

## 入力

- 参照要件: docs/evolution-review-2026-06-10.md（§4 findings・構造的観察 3/4）
- 参照設計: docs/specs/2026-06-10-v140-fix-batch-design.md

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（フレームワーク内部変更のみ。デプロイ対象なし）
- Database: n/a
- CI/CD: n/a（ローカル `python3 -m pytest tests/ -q`＋contract/smoke）

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: n/a（Web アプリではない）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

Project Overrides 未定義 → main 直コミット（既存リリース慣行に従う。コミットはタスク単位）。

## 不変条件（全タスク共通）

1. **mirror 同期**: `hooks/` 配下を変更したら同一コミットで `cp hooks/<file> examples/minimal-project/hooks/<file>` を実行（`tests/test_mirror_identity.py` が byte-identical を強制）。
2. **pure-bash 維持**: `hooks/lib/*.sh` は外部インタープリタ非依存。
3. **POSIX ERE**: 新規正規表現は GNU/BSD grep 双方で同挙動（既存慣用の `\b`/`\s` は踏襲可）。
4. テスト実行: `python3 -m pytest tests/ -q`（タスク完了ごとに全件 green を確認）。

## ファイル構造（変更マップ）

- 新規: `hooks/lib/frontmatter.sh` — frontmatter/セクション読み取りの単一ソース（P3-5）
- 新規: `docs/hook-failure-policy.md` — 全 hook の failure 時挙動の宣言（観察3）
- 新規: `tests/test_frontmatter_lib.py` — lib 単体
- 新規: `tests/test_failure_policy.py` — 表駆動・実発火突合
- 変更: `hooks/check-task-completed.sh` — python3 不在時 closed 化（P3-1）
- 変更: `hooks/check-gate.sh:127` / `hooks/check-task-created.sh:90` / `hooks/session-start.sh:48` / `hooks/post-status-audit.sh:53,96` — frontmatter_section 置換（P3-5）
- 変更: `hooks/check-secrets.sh:29,60,63-64,99` — id_ed25519/id_ecdsa（P2-4）
- 変更: `hooks/check-control-plane.sh:141` — WRITE_INDICATORS 語境界（P3-4）
- 変更: `hooks/pre-compact.sh:44-45` — AEGIS_PRECOMPACT_INTERVAL（P3-2）
- 変更: `hooks/check-deploy-gate.sh:44,52-61` — DEPLOY_RE 拡大（P2-2）＋RC=2→ask（P2-3）
- 変更: `hooks/check-deploy-mcp-gate.sh:32-38` — RC=2→ask（P2-3 同契約）
- 変更: `scripts/check_status.py:1051-1054` — size-skip を return 2 + `ASK:` マーカー（P2-3）
- 変更: `scripts/update-gate.sh` — mkdir ロック＋1 パス書き込み（P3-3）、frontmatter_section 置換（:38,81,220）
- 変更: `scripts/check_framework_contract.py:121-142,825-835` — lib 追跡（P2-5）＋example 版数同期（P2-6 再発封鎖）
- 変更: `scripts/run-test-strength-drill.py:22,151,163-164,366-367` — docs/ 除外（B1）
- 変更: `templates/profiles/standard.json` — hooks_include +4（P2-1）
- 変更: `templates/hooks.template.json` ＋ `bin/setup.sh:158-186` — `$CLAUDE_PROJECT_DIR` 化（P3-6）
- 変更: `scripts/eval_scaffold_smoke.py` — settings 検証＋standard 実発火（P2-1/P3-6 封鎖）
- 変更: `docs/functional-integrity-audit-report-2026-06-07.md:316-322` — 重複節削除（K-2）
- 変更: `docs/LEARNINGS.md:37` — B1 恒久対応追記
- 変更: `README.md` — Migration 節＋profile 数記述、`FRAMEWORK_VERSION`/STATUS.template/example STATUS = 1.4.0
- テスト変更: `tests/test_hook_output_schema.py`・`tests/test_check_status.py`・`tests/test_test_strength_drill.py` 拡張

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| T0 | `read_frontmatter` / `frontmatter_section`（hooks/lib/frontmatter.sh） | なし |
| T1 | ポリシー表＋test_failure_policy.py（task-completed 行は RED） | 全 hook の現挙動 |
| T2 | check-task-completed の closed 挙動 | T1 の RED テスト |
| T3 | 7 call site の frontmatter_section 化 | T0 |
| T4〜T7 | 各 hook 修正 | なし（独立） |
| T8 | `--check-deploy-ready` RC=2/`ASK:` 契約＋hook の ask マップ | なし |
| T9 | update-gate のロック＋1 パス書込 | T0（frontmatter_section） |
| T10 | contract の lib 追跡＋版数同期検査 | T0（frontmatter.sh 存在） |
| T11 | drill の docs/ 除外 | なし |
| T12 | standard の moat 構成 | なし |
| T13 | `$CLAUDE_PROJECT_DIR` 形式 settings | なし |
| T14 | smoke の新検証 2 種 | T12, T13 |
| T15 | docs 整理 | なし |
| T16 | v1.4.0 版数・README 移行節・全証跡 | T0〜T15 |

循環依存なし。

## タスク分解

### タスク 0: hooks/lib/frontmatter.sh 新設

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 新規 `hooks/lib/frontmatter.sh`、新規 `tests/test_frontmatter_lib.py`、mirror `examples/minimal-project/hooks/lib/frontmatter.sh`
**意図:** `grep -A20` の 20 行上限（P3-5）を排した frontmatter 読み取りの単一ソースを作る。

- [ ] Step 1: `tests/test_frontmatter_lib.py` を作成（RED）。`tests/test_emit_lib.py` と同様に bash -c で関数を実発火:

```python
#!/usr/bin/env python3
"""hooks/lib/frontmatter.sh の単体テスト（P3-5）。"""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "frontmatter.sh"


def run_fn(fn: str, *args: str) -> tuple[int, str]:
    quoted = " ".join(f"'{a}'" for a in args)
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && {fn} {quoted}"],
        capture_output=True, text=True, check=False)
    return r.returncode, r.stdout


class TestReadFrontmatter(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        p = tmp / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_basic_frontmatter(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\nb: 2\n---\nbody\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 0)
            self.assertEqual(out, "a: 1\nb: 2\n")

    def test_body_dashes_not_included(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\n---\nbody\n---\ntail\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(out, "a: 1\n")

    def test_no_frontmatter_rc1_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "plain text\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")

    def test_unterminated_frontmatter_rc1_no_partial_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = self._write(Path(d), "---\na: 1\nno close\n")
            rc, out = run_fn("read_frontmatter", str(p))
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")

    def test_missing_file_rc1(self):
        rc, out = run_fn("read_frontmatter", "/nonexistent/x.md")
        self.assertEqual(rc, 1)


class TestFrontmatterSection(unittest.TestCase):
    def test_section_over_20_lines(self):
        # P3-5 の動機: gate_approvals 開始から 20 行を超えたキーも読めること。
        import tempfile
        pad = "\n".join(f"  k{i:02d}: pending" for i in range(25))
        text = f"---\ngate_approvals:\n{pad}\n  plan: approved\nnext_key: x\n---\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(text, encoding="utf-8")
            rc, out = run_fn("frontmatter_section", str(p), "gate_approvals")
            self.assertEqual(rc, 0)
            self.assertIn("  plan: approved", out)
            self.assertNotIn("next_key", out)

    def test_section_absent_rc1(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text("---\na: 1\n---\n", encoding="utf-8")
            rc, out = run_fn("frontmatter_section", str(p), "gate_approvals")
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] Step 2: `python3 -m pytest tests/test_frontmatter_lib.py -q` → FAIL（lib 不在）を確認
- [ ] Step 3: `hooks/lib/frontmatter.sh` を作成:

```bash
#!/usr/bin/env bash
# Frontmatter readers — single source replacing fragile `grep -A20` YAML
# section reads (P3-5, evolution review 2026-06-10). Pure bash + awk.
#
# read_frontmatter <file>
#   stdout: every line between the leading `---` pair (delimiters excluded).
#   RC 1 + empty stdout when the file is missing, has no frontmatter, or the
#   frontmatter is unterminated (output is buffered so failure never emits
#   partial lines).
#
# frontmatter_section <file> <key>
#   stdout: the top-level `<key>:` line plus its indented block — the shape
#   previously produced by `grep -A20 "^<key>:"`, without the 20-line cap.
#   RC 1 when the key is absent.

read_frontmatter() {
  local file="$1"
  [ -f "$file" ] || return 1
  awk 'NR==1 { if ($0 != "---") exit 1; next }
       /^---[[:space:]]*$/ { found=1; exit }
       { buf = buf $0 ORS }
       END { if (found) printf "%s", buf; exit found ? 0 : 1 }' "$file"
}

frontmatter_section() {
  local file="$1" key="$2" out
  out=$(read_frontmatter "$file" | awk -v key="$key" '
    !f && index($0, key ":") == 1 { f=1; print; next }
    f && /^[^[:space:]]/ { exit }
    f { print }')
  [ -n "$out" ] || return 1
  printf '%s\n' "$out"
}
```

- [ ] Step 4: テスト PASS 確認 → `cp hooks/lib/frontmatter.sh examples/minimal-project/hooks/lib/frontmatter.sh`
- [ ] Step 5: 配送契約の確認（グリル穴1・F6 教訓）: `bin/setup.sh:216` の copy_hooks は `hooks/lib/*.sh` を glob 全コピーするため frontmatter.sh は自動配送される — setup.sh のコード変更は不要であることを確認。install 検証の契約化（smoke の `REQUIRED_HOOK_LIBS` への追加）は T14 Step 0 で行う
- [ ] Step 6: `python3 -m pytest tests/ -q` 全件 green → コミット `feat(hooks): add frontmatter.sh lib (P3-5 groundwork)`

**受入条件:** 上記 7 テスト PASS・mirror 同期済み・配送経路（glob コピー）確認済み
**Deliverable:** [ ] lib が存在し動作 [ ] テストがカバー

### タスク 1: failure ポリシー表＋表駆動テスト新設（U1・宣言と執行）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 新規 `docs/hook-failure-policy.md`、新規 `tests/test_failure_policy.py`
**意図:** 全 16 hook の failure 時挙動を宣言し、実発火で突合するテストを先に作る（観察3）。check-task-completed の行は現状 fail-open のため **RED になるのが正**（T2 で GREEN 化）。

- [ ] Step 1: `docs/hook-failure-policy.md` を作成。表が宣言の単一ソース:

```markdown
# Hook Failure Policy（fail-open / fail-closed 宣言）

宣言の単一ソース。`tests/test_failure_policy.py` が本表をパースし、
各 hook を python3 遮断環境で実発火して宣言と突合する（表の陳腐化＝テスト FAIL）。

- **moat** = ゲート・破壊防止・秘密・完了強制。依存（python3）不在時は fail-closed。
- **advisory** = 可視化・補助。依存不在時は fail-open（セッションを止めない）。
- 入力パース失敗時は全 hook allow（入力不明では誤 deny を避ける）。
- 依存=なし の hook は pure-bash 宣言: python3 遮断下でも通常判定が機能すること。

| hook | 分類 | python3 依存 | python3 不在時 | 入力パース失敗時 |
| --- | --- | --- | --- | --- |
| check-gate.sh | moat | なし | 通常判定 | allow |
| check-tdd.sh | moat | なし | 通常判定 | allow |
| check-client-info.sh | moat | なし | 通常判定 | allow |
| check-destructive.sh | moat | なし | 通常判定 | allow |
| check-secrets.sh | moat | なし | 通常判定 | allow |
| check-deploy-gate.sh | moat | あり | deny | allow |
| check-deploy-mcp-gate.sh | moat | あり | deny | allow |
| check-skill-gate.sh | moat | あり | ask | allow |
| check-cron-gate.sh | moat | あり | ask | allow |
| check-control-plane.sh | moat | あり | deny（raw fallback） | — (※1) |
| check-task-created.sh | moat | あり | hard stop（placeholder subject で判定続行） | allow |
| check-task-completed.sh | moat | あり | 差し戻し（exit 2） | allow |
| post-bash.sh | advisory | なし | 通常動作 | allow |
| post-status-audit.sh | advisory | あり | allow | allow |
| pre-compact.sh | advisory | なし | 通常動作 | allow |
| session-start.sh | advisory | あり | allow（劣化表示） | allow |

※1 check-control-plane は入力パース失敗時に raw input へフォールバックし、
control plane 言及があれば deny（fail-closed）。言及がなければ allow。

## size-skip（task_size S/M の deploy）

`check_status.py --check-deploy-ready` は S/M（deploy フェーズなし）のとき
RC=2＋stdout 先頭 `ASK:` を返し、check-deploy-gate / check-deploy-mcp-gate は
これを **ask**（人間確認）にマップする（観察4: skip＝無検査許可の是正）。
RC=2 でも `ASK:` マーカーが無い出力は deny に倒す（interpreter 異常系の混同防止）。
```

- [ ] Step 2: `tests/test_failure_policy.py` を作成。骨子（表パース＋シナリオ実発火）:

```python
#!/usr/bin/env python3
"""docs/hook-failure-policy.md の宣言と hook 実挙動の突合（観察3）。"""
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "hook-failure-policy.md"
HOOKS = ROOT / "hooks"

ROW_RE = re.compile(r"^\| (check-[a-z-]+\.sh|post-[a-z-]+\.sh|pre-compact\.sh|session-start\.sh) \|")


def parse_policy_table() -> dict[str, dict[str, str]]:
    rows = {}
    for line in POLICY.read_text(encoding="utf-8").splitlines():
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows[cells[0]] = {"class": cells[1], "py_dep": cells[2],
                          "py_absent": cells[3], "parse_fail": cells[4]}
    return rows


def make_broken_python_path() -> str:
    """python3 が RC 127 で死ぬ shim を先頭に置いた PATH を返す。"""
    d = tempfile.mkdtemp(prefix="aegis-nopy-")
    shim = Path(d) / "python3"
    shim.write_text("#!/bin/sh\nexit 127\n")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    return d + os.pathsep + os.environ.get("PATH", "")


def fire(script: str, stdin: str, *, env_extra: dict | None = None) -> tuple[int, str, str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(["bash", str(HOOKS / script)], input=stdin,
                       capture_output=True, text=True, check=False, env=env)
    return r.returncode, r.stdout.strip(), r.stderr


def decision_of(stdout: str) -> str:
    if not stdout or stdout == "{}":
        return "allow"
    data = json.loads(stdout)
    hso = data.get("hookSpecificOutput", {})
    if "permissionDecision" in hso:
        return hso["permissionDecision"]          # deny / ask
    if data.get("continue") is False:
        return "hard-stop"
    if data.get("decision") == "block":
        return "block"
    if "additionalContext" in hso:
        return "allow"
    return "unknown"
```

シナリオ表（同ファイル内・hook → (stdin, fixture, python3 不在時の期待値)）。fixture は
`tests/test_hook_output_schema.py` の `make_pretool_payload` 流儀＋`AEGIS_ROOT_OVERRIDE`
で gates pending な STATUS.md を持つ一時 root を組む。
**ただし check-control-plane は AEGIS_ROOT_OVERRIDE 非対応**（かつ repo 直下 STATUS は
task_type=framework のため protected glob 判定が変わる）— 既存
`test_check_control_plane_*` テストが fixture をどう組んでいるかをそのまま転写し、
新規方式を発明しない（グリル要検討点1）:

| hook | 発火 stdin（要点） | python3 遮断時の期待 decision |
| --- | --- | --- |
| check-gate.sh | Edit で通常ファイル | allow |
| check-tdd.sh | `AEGIS_TDD_MODE=off`＋Edit | allow |
| check-client-info.sh | 無害 Write | allow |
| check-destructive.sh | Bash `rm -rf /tmp/x` | ask |
| check-secrets.sh | Bash `git add .env` | deny |
| check-deploy-gate.sh | Bash `vercel deploy`＋gates pending fixture | deny |
| check-deploy-mcp-gate.sh | `mcp__vercel__deploy_project`＋同 fixture | deny |
| check-skill-gate.sh | Skill `update-config` | ask |
| check-cron-gate.sh | CronCreate prompt に `vercel --prod` | ask |
| check-control-plane.sh | `echo x > hooks/check-gate.sh`（task_type=feature fixture・`\"` 含み） | deny |
| check-task-created.sh | phase=implement・plan pending fixture | hard-stop |
| check-task-completed.sh | next_action あり fixture | exit 2（差し戻し） |
| post-bash.sh / pre-compact.sh / post-status-audit.sh / session-start.sh | 各通常入力 | RC 0（crash しない） |

検証メソッド（必須 3 群）:
1. `test_table_covers_all_hooks` — 表の hook 集合 == `hooks/*.sh` の集合（過不足 FAIL）
2. `test_python3_absent_behavior` — 表の「python3 不在時」と shim PATH 下の実 decision を突合
3. `test_parse_failure_allows` — stdin `not-json{{{` で全 PreToolUse/Task hook が allow/RC0（※1 の control-plane は raw に control plane 言及なし入力で allow を確認）

- [ ] Step 3: 実行 → **check-task-completed の行のみ FAIL（fail-open 検出）、他 PASS** を確認。advisory 4 hook（post-bash/pre-compact/post-status-audit/session-start）が python3 遮断で RC 非 0（crash）になる場合は「fail-open（allow）」の宣言と不一致＝T2 のスコープで修正する（グリル要検討点2）
- [ ] Step 4: **ここではコミットしない**（check-task-completed 行が RED のまま main 履歴に乗り「全タスク green でコミット」の不変条件と矛盾するため — グリル穴2）。T2 の GREEN 後に T2 と同一コミットで投入する

**受入条件:** 表とテストが存在し、既知の P3-1 だけが RED（コミットは T2 と合流）
**Deliverable:** [ ] 宣言 docs [ ] 表駆動テスト

### タスク 2: check-task-completed の closed 化（P3-1・T1 の GREEN 化）

**blockedBy:** T1 | **モデル:** `inherit`
**ファイル:** 対象 `hooks/check-task-completed.sh:33-64,88-95` / テスト `tests/test_failure_policy.py`（T1 作成済み）
**意図:** python3 不在時に check-task-created と対称の fail-closed（差し戻し）へ。

- [ ] Step 1: subject 抽出を PY_RC 捕捉形に変更（check-task-created.sh:40-83 と同型）:

```bash
set +e
SUBJECT=$(printf '%s' "$INPUT" | python3 -c '
（既存の python ワンライナーをそのまま維持）
' 2>/dev/null)
PY_RC=$?
set -e

if [ "$PY_RC" -ne 0 ]; then
  # python3 unavailable/broken: do NOT fail open. The next_action check below is
  # python3-free; the evidence check failure path also closes (policy: moat).
  SUBJECT="(subject unavailable: python3)"
elif [ -z "$SUBJECT" ]; then
  （既存の dump+emit_allow ブロックをそのまま維持）
fi
```

- [ ] Step 2: evidence 検査（:90 付近）を RC 捕捉形に変更:

```bash
set +e
EVIDENCE=$(python3 "${DEFAULT_ROOT}/scripts/check_status.py" --root "$ROOT" --check-completion-evidence 2>/dev/null)
EV_RC=$?
set -e
if [ "$EV_RC" -ne 0 ] && [ -z "$EVIDENCE" ]; then
  printf '[task-completed] evidence 整合性を検証できません（python3 実行不能, rc=%s）。環境を復旧してから完了してください。\n' "$EV_RC" >&2
  exit 2
fi
if [ -n "$EVIDENCE" ]; then
  （既存の差し戻しブロックをそのまま維持）
fi
```

- [ ] Step 3: `python3 -m pytest tests/test_failure_policy.py tests/test_hook_output_schema.py -q` → 全 PASS
- [ ] Step 4: mirror 同期 → 全テスト green → **T1 の成果物（docs/hook-failure-policy.md・tests/test_failure_policy.py）も同時にステージ**してコミット `feat(policy): add hook failure policy table + close check-task-completed fail-open (P3-1, 観察3)`

**受入条件:** T1 の表駆動テスト全行 GREEN・既存 TaskCompleted テスト不変
**Deliverable:** [ ] closed 挙動 [ ] テストがカバー

### タスク 3: `grep -A20` 7 箇所を frontmatter_section へ置換（P3-5）

**blockedBy:** T0 | **モデル:** `inherit`
**ファイル:** `hooks/check-gate.sh:127` / `hooks/check-task-created.sh:90` / `hooks/session-start.sh:48` / `hooks/post-status-audit.sh:53,96` / `scripts/update-gate.sh:38,81,220`
**意図:** gate_approvals が 20 行を超えても読める YAML セクション読み取りへ統一。

- [ ] Step 1: 各 hook の `source .../lib/emit.sh` 直後に `source "${SCRIPT_DIR}/lib/frontmatter.sh"` を追加（update-gate.sh は `source "${ROOT}/hooks/lib/frontmatter.sh"`）
- [ ] Step 2: 7 箇所を機械的に置換。パターン: `grep -A20 "^gate_approvals:" "$STATUS_FILE"` → `frontmatter_section "$STATUS_FILE" gate_approvals`（post-status-audit.sh:53 は `"$file"` 引数のまま）。後続パイプ（`| grep -m1 ...`）は不変。`|| true` 付き箇所はそのまま維持
- [ ] Step 3: 回帰テスト追加 — `tests/test_frontmatter_lib.py` に「gate_approvals 25 行超 STATUS.md で `bash scripts/update-gate.sh`（引数なし）の Current gate status に末尾キーが出る」テスト:

```python
class TestCallSitesUse20PlusLines(unittest.TestCase):
    def test_update_gate_lists_gates_beyond_20_lines(self):
        import tempfile, shutil
        pad = "\n".join(f"  pad{i:02d}: pending" for i in range(22))
        text = ("---\nframework: aegis\ngate_approvals:\n" + pad +
                "\n  deploy: pending\nphase: plan\n---\n")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "scripts").mkdir()
            (root / "hooks" / "lib").mkdir(parents=True)
            (root / "docs" / "STATUS.md").write_text(text, encoding="utf-8")
            shutil.copy(ROOT / "scripts" / "update-gate.sh", root / "scripts")
            shutil.copy(ROOT / "scripts" / "check_status.py", root / "scripts")
            for lib in ("frontmatter.sh", "emit.sh", "extract-input.sh", "patterns.sh"):
                shutil.copy(ROOT / "hooks" / "lib" / lib, root / "hooks" / "lib")
            r = subprocess.run(["bash", str(root / "scripts" / "update-gate.sh")],
                               capture_output=True, text=True, check=False)
            self.assertIn("deploy: pending", r.stdout)
```

- [ ] Step 4: FAIL（置換前）→ 置換後 PASS を確認（テスト先行: Step 3 を Step 1 より先に書いて RED を取ること）
- [ ] Step 5: hooks 4 ファイルを mirror 同期 → 全テスト green → コミット `fix(hooks,scripts): replace grep -A20 frontmatter reads with frontmatter_section (P3-5)`

**受入条件:** リポジトリに `grep -A20 "^gate_approvals:"` が残存しない（`grep -rn 'grep -A20' hooks/ scripts/` が空。examples/ は mirror 同期で消える）
**Deliverable:** [ ] 7 箇所置換 [ ] 20 行超回帰テスト

### タスク 4: check-secrets に id_ed25519 / id_ecdsa（P2-4）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `hooks/check-secrets.sh:29,60,63-64,99` / テスト `tests/test_hook_output_schema.py`
**意図:** 現代 ssh-keygen 既定（ed25519）の鍵を 4 経路すべてで検出。

- [ ] Step 1: RED テストを `TestPreToolUseHooks` に追加:

```python
    def test_check_secrets_deny_git_add_ed25519(self):
        rc, out, _ = run_hook("check-secrets.sh",
            make_pretool_payload("Bash", {"command": "git add ~/.ssh/id_ed25519"}))
        self.assertEqual(self.pretool_decision(out), "deny")

    def test_check_secrets_deny_git_add_ecdsa_pub(self):
        rc, out, _ = run_hook("check-secrets.sh",
            make_pretool_payload("Bash", {"command": "git add id_ecdsa.pub"}))
        self.assertEqual(self.pretool_decision(out), "deny")
```

（assert ヘルパー名は既存クラスの実装に合わせる）
- [ ] Step 2: FAIL 確認 → 4 箇所修正:
  - :29 `HIGH_RISK_RE='\.pem(\b|$)|id_(rsa|ed25519|ecdsa)(\b|$)|credentials.*\.json|service-account.*\.json'`
  - :60 case パターン `*.pem|id_rsa|id_rsa.pub|id_ed25519|id_ed25519.pub|id_ecdsa|id_ecdsa.pub|*credentials*.json|service-account*.json)`
  - :63-64 find に `-o -name 'id_ed25519*' -o -name 'id_ecdsa*'` を追加
  - :99 staged grep `(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$`
- [ ] Step 3: deny メッセージ 2 箇所（:33,:71,:100）の「SSH鍵」表記はそのまま（鍵種を網羅する文言のため変更不要）
- [ ] Step 4: PASS → mirror 同期 → コミット `fix(hooks): detect id_ed25519/id_ecdsa keys in check-secrets (P2-4)`

**受入条件:** ed25519/ecdsa の direct add・broad add・staged commit が deny、id_rsa 既存テスト不変
**Deliverable:** [ ] 4 経路検出 [ ] テストがカバー

### タスク 5: WRITE_INDICATORS の語境界化（P3-4）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `hooks/check-control-plane.sh:141` / テスト `tests/test_hook_output_schema.py`
**意図:** 裸 substring `unlink|remove|rename|truncate` を関数呼び出し形に限定し、`grep -r "remove"` の偽陽性を解消。

- [ ] Step 1: RED テスト（read-only grep が allow になるべき）:

```python
    def test_check_control_plane_allows_readonly_grep_for_remove(self):
        rc, out, _ = run_hook("check-control-plane.sh",
            make_pretool_payload("Bash", {"command": 'grep -r "remove" hooks/'}),
            env={"AEGIS_ROOT_OVERRIDE": <task_type=feature の fixture root>})
        self.assertEqual(self.pretool_decision(out), "allow")

    def test_check_control_plane_still_denies_os_remove_call(self):
        # 真陽性維持: 関数呼び出し形は write indicator のまま
        rc, out, _ = run_hook("check-control-plane.sh",
            make_pretool_payload("Bash",
                {"command": 'find hooks/ -name "*.sh" -exec rm {} +'}),
            env={...同 fixture...})
        self.assertEqual(self.pretool_decision(out), "deny")
```

（fixture 構築は既存 `test_check_control_plane_*` テストの流儀を踏襲。check-control-plane は
ROOT override を持たないため、既存テストが ROOT 直下でどう fixture を組んでいるかに合わせる）
- [ ] Step 2: FAIL 確認 → :141 を置換:

```bash
WRITE_INDICATORS='sed\s+-i|>\s*[^&]|>>\s|tee\s|cp\s|mv\s|chmod\s|rm\s|mkdir\s|touch\s|install\s|ln\s|write_text|write_bytes|open\(.*[wax]|\.write\(|Path\(.*\.write|(unlink|remove|rename|truncate)[[:space:]]*\('
```

- [ ] Step 3: PASS → mirror 同期 → コミット `fix(hooks): word-bound WRITE_INDICATORS to stop grep "remove" false positives (P3-4)`

**受入条件:** `grep -r "remove"` 系 allow・`rm`/`sed -i`/関数呼び出し形 deny 維持
**Deliverable:** [ ] 偽陽性解消 [ ] 真陽性回帰テスト

### タスク 6: pre-compact 環境変数の AEGIS_ 改名（P3-2）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `hooks/pre-compact.sh:44-45` / テスト `tests/test_hook_output_schema.py`（TestPreCompactHook）
**意図:** 旧 ULTRA_ 命名の残滓を解消。旧名は 1 リリース間 fallback で読む。

- [ ] Step 1: RED テスト — `AEGIS_PRECOMPACT_INTERVAL=1` で stale block・`ULTRA_PRECOMPACT_INTERVAL=1`（旧名のみ）でも同様に block、両方設定時は AEGIS_ 優先（AEGIS_=999999 / ULTRA_=1 → allow）
- [ ] Step 2: :44-45 を置換:

```bash
# Default: 5 minutes. Override with AEGIS_PRECOMPACT_INTERVAL
# (legacy ULTRA_PRECOMPACT_INTERVAL is honored as fallback for one release).
STALE_THRESHOLD="${AEGIS_PRECOMPACT_INTERVAL:-${ULTRA_PRECOMPACT_INTERVAL:-300}}"
```

- [ ] Step 3: PASS → mirror 同期 → コミット `fix(hooks): rename precompact interval env to AEGIS_ with legacy fallback (P3-2)`

**受入条件:** 新名動作・旧名 fallback・優先順位テスト PASS
**Deliverable:** [ ] 改名 [ ] fallback テスト

### タスク 7: DEPLOY_RE 拡大（P2-2）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `hooks/check-deploy-gate.sh:44` / テスト `tests/test_hook_output_schema.py`
**意図:** `vercel --prod` 等のオプション付き形と `wrangler deploy|publish` を捕捉。

- [ ] Step 1: RED テスト（gates pending fixture で deny を期待）: `vercel --prod` / `npx vercel --prod` / `vercel --prod --yes` / `vercel --prod && echo ok` / `vercel --prod > deploy.log`（リダイレクト終端 — グリル穴3） / `wrangler deploy` / `wrangler publish`。allow 維持: `my-vercel --prod` / `vercel env ls` / `vercel env pull --prod`（サブコマンド後置 flag — グリル穴3） / `vercel dev` / `rg deploy` / `cat templates/DEPLOY-CHECKLIST.template.md`
- [ ] Step 2: FAIL 確認 → :44 を置換（flags-only 形の終端クラスに `>` を含める — `vercel --prod > deploy.log` のバイパス封鎖）:

```bash
# Patterns: vercel deploy [flags], vercel with ONLY flags (default=deploy, incl.
#           --prod; subcommands like `vercel env` do NOT match), firebase/netlify
#           deploy, npm/pnpm/yarn/bun [run] deploy, flyctl/railway/gcloud deploy,
#           wrangler deploy|publish.
DEPLOY_RE='(^|[[:space:];&|])(vercel +deploy|vercel( +--[A-Za-z][A-Za-z0-9-]*(=[^[:space:];&|]*)?)*[[:space:]]*($|[;&|>])|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy|wrangler +(deploy|publish))'
```

（既存 `vercel[[:space:]]*$` は flags-only 形に包含されるため削除）
- [ ] Step 3: PASS → mirror 同期 → コミット `fix(hooks): widen DEPLOY_RE to flag-form vercel and wrangler (P2-2)`

**受入条件:** Step 1 の match/non-match 全ケース PASS・既存 deploy gate テスト不変
**Deliverable:** [ ] 正規表現拡大 [ ] 境界テスト

### タスク 8: size-skip を ask に（P2-3・観察4）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `scripts/check_status.py:1051-1054` / `hooks/check-deploy-gate.sh:52-61` / `hooks/check-deploy-mcp-gate.sh:32-38` / テスト `tests/test_check_status.py`・`tests/test_hook_output_schema.py`
**意図:** S/M の deploy を「無検査許可」から「人間確認（ask）」へ。RC 契約: 0=allow / 2+`ASK:`=ask / 他=deny。

- [ ] Step 1: RED（check_status 単体）— `check_deploy_ready` が task_size S/M で RC 2 と `ASK:` 始まりの stdout を返す。L は従来どおり（pending→1 / approved→0）
- [ ] Step 2: `scripts/check_status.py:1051-1054` を置換:

```python
    # If deploy phase is not in the allowed phases for this task size, the gate
    # has no inspection to run — surface that as ASK (human confirm), not a
    # silent allow (P2-3: size-skip means "phase skipped", not "deploy vetted").
    if task_size and task_size in SIZE_ALLOWED_PHASES:
        if "deploy" not in SIZE_ALLOWED_PHASES[task_size]:
            print(f"ASK: task_size '{task_size}' は deploy フェーズをスキップする設定のため、"
                  "ゲート検査なしのデプロイになります。意図したデプロイであることを確認してください。")
            return 2
```

- [ ] Step 3: RED（hook 側）— S fixture で check-deploy-gate / check-deploy-mcp-gate が `ask` decision を返す。RC=2 だが `ASK:` 無し（例: スクリプトパス不在で interpreter が RC2）の場合は deny に倒れることもテスト
- [ ] Step 4: 両 hook の委譲ブロックを置換（check-deploy-gate.sh:52-61。mcp 側も同型）:

```bash
set +e
RESULT=$(python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-deploy-ready 2>&1)
RC=$?
set -e
if [ $RC -eq 2 ] && printf '%s' "$RESULT" | grep -q '^ASK:'; then
  MSG=$(printf '%s' "$RESULT" | sed 's/^ASK:[[:space:]]*//' | tr '\n' ' ')
  emit_ask "[deploy-gate] $MSG"
  exit 0
fi
if [ $RC -ne 0 ]; then
  MSG=$(printf '%s' "$RESULT" | tr '\n' ' ')
  REASON=$(printf '[deploy-gate] %s' "$MSG")
  emit_deny "$REASON"
  exit 0
fi
emit_allow
exit 0
```

- [ ] Step 5: PASS → mirror 同期（2 hooks）→ コミット `feat(gates): map size-skip deploys to ask via RC=2 + ASK marker (P2-3)`

**受入条件:** S/M=ask・L=従来・マーカー無し RC2=deny・python3 不在=deny（T1 表と整合）
**Deliverable:** [ ] RC 契約 [ ] hook マップ [ ] テスト 3 層

### タスク 9: update-gate.sh の mkdir ロック＋1 パス書き込み（P3-3）

**blockedBy:** T0（T3 の置換と同一ファイル — T3 先行を推奨） | **モデル:** `inherit`
**ファイル:** `scripts/update-gate.sh:184-203` / テスト 新規 `tests/test_update_gate_lock.py`
**意図:** 並行セッションの lost update を防ぐ（macOS に flock なし → mkdir ロック）。

- [ ] Step 1: RED テスト:

```python
#!/usr/bin/env python3
"""update-gate.sh の排他ロック（P3-3）。"""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestUpdateGateLock(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        # T3 のテストと同じ fixture 構築ヘルパーを共通化してよい
        ...gate_approvals に security: pending を含む STATUS.md と
           scripts/{update-gate.sh,check_status.py}・hooks/lib/* を配置...

    def test_lock_held_fails_explicitly_without_write(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            lock = root / ".claude" / ".gate-update.lock.d"
            lock.mkdir(parents=True)
            before = (root / "docs" / "STATUS.md").read_text()
            r = subprocess.run(
                ["bash", str(root / "scripts" / "update-gate.sh"), "security", "reset"],
                capture_output=True, text=True, check=False, timeout=30)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("lock", (r.stdout + r.stderr).lower())
            self.assertEqual(before, (root / "docs" / "STATUS.md").read_text())

    def test_lock_released_then_succeeds(self):
        ...同 fixture でロック無し → approve 系 1 回成功・STATUS 反映を確認...
```

- [ ] Step 2: FAIL 確認 → update-gate.sh に追加（`--- Update STATUS.md ---` の直前）:

```bash
# --- Exclusive lock (P3-3): mkdir is atomic on POSIX; flock(1) absent on macOS ---
LOCK_DIR="${SNAPSHOT_DIR}/.gate-update.lock.d"
mkdir -p "$SNAPSHOT_DIR"
LOCK_OK=false
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OK=true
    trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
    break
  fi
  sleep 0.2
done
if [ "$LOCK_OK" != "true" ]; then
  echo "ERROR: another gate update holds the lock (${LOCK_DIR})."
  echo "Retry shortly. If no other session is running, remove the stale directory."
  exit 1
fi
```

- [ ] Step 3: 2 回の sed/mv を 1 パス化（:188-203 を置換）:

```bash
TMP="${STATUS_FILE}.tmp.$$"
SED_ARGS=(-e "/^gate_approvals:/,/^[a-z]/ s|\(  ${GATE_NAME_SED}:\).*|\1 ${TARGET_VALUE}|")
if [ "$ACTION" = "reset" ]; then
  REF_KEY=$(get_ref_key "$GATE_NAME")
  if [ -n "$REF_KEY" ]; then
    REF_KEY_SED=$(printf '%s\n' "$REF_KEY" | sed 's/[.[\/*^$&]/\\&/g')
    SED_ARGS+=(-e "/^current_refs:/,/^[a-z]/ s|\(  ${REF_KEY_SED}:\).*|\1 null|")
  fi
fi
sed "${SED_ARGS[@]}" "$STATUS_FILE" > "$TMP" && mv "$TMP" "$STATUS_FILE"
if [ "$ACTION" = "reset" ] && [ -n "${REF_KEY:-}" ]; then
  echo "[${ACTION_TAG}] current_refs.${REF_KEY} → null"
fi
```

（旧 `--- Reset: also null the corresponding ref ---` ブロックは削除）
- [ ] Step 4: PASS → 全テスト green → コミット `fix(scripts): serialize update-gate.sh via mkdir lock + single-pass write (P3-3)`

**受入条件:** ロック保持時は無書込で明示エラー・解放後成功・reset の ref null 化維持
**Deliverable:** [ ] 排他 [ ] 1 パス書込 [ ] テスト

### タスク 10: contract の lib 追跡＋example 版数同期検査（P2-5・P2-6 封鎖）

**blockedBy:** T0 | **モデル:** `inherit`
**ファイル:** `scripts/check_framework_contract.py:121-142,825-835`、`examples/minimal-project/docs/STATUS.md:3`
**意図:** F6 の中心ファイル（emit.sh/patterns.sh/frontmatter.sh）に番人を置き、example の版数 drift を検出器の射程に入れる。

- [ ] Step 1: RED — contract を一時的に検証: `REQUIRED_HOOK_FILES` に 3 lib を加えた状態で `python3 scripts/check_framework_contract.py` が「example 版数 0.12.2 ≠ 1.3.3」を検出する新チェックを先に書く:

```python
    # Version sync: example STATUS.md must match FRAMEWORK_VERSION (P2-6).
    # The example is the non-engineer's copy source; drift there ships stale
    # contracts invisibly (no other drift detector covers it).
    example_status = ROOT / "examples/minimal-project/docs/STATUS.md"
    if example_status.exists():
        m = re.search(r'^framework_version:\s*"([^"]+)"',
                      example_status.read_text(encoding="utf-8"), re.M)
        if not m or m.group(1) != FRAMEWORK_VERSION:
            found = m.group(1) if m else "(missing)"
            errors.append(
                f"examples/minimal-project/docs/STATUS.md framework_version "
                f"({found}) != FRAMEWORK_VERSION ({FRAMEWORK_VERSION})")
```

（:825 の template 検査ブロックと同じ errors 蓄積流儀・変数名に合わせて統合）
- [ ] Step 2: `REQUIRED_HOOK_FILES` に追加:

```python
    ROOT / "hooks/lib/extract-input.sh",
    ROOT / "hooks/lib/emit.sh",
    ROOT / "hooks/lib/patterns.sh",
    ROOT / "hooks/lib/frontmatter.sh",
```

- [ ] Step 3: contract 実行 → example 版数エラーのみ検出を確認 → `examples/minimal-project/docs/STATUS.md:3` を `framework_version: "1.3.3"`（現行 FRAMEWORK_VERSION）に修正 → contract 全 green
- [ ] Step 4: コミット `feat(contract): track hook libs + enforce example version sync (P2-5, P2-6)`

**受入条件:** lib 3 件削除で contract FAIL・example 版数 drift で contract FAIL・現状 green
**Deliverable:** [ ] lib 番人 [ ] 版数同期検査

### タスク 11: ドリルの docs/ 除外（B1 恒久修正）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `scripts/run-test-strength-drill.py:22,151,163-164,366-367` / テスト `tests/test_test_strength_drill.py`
**意図:** docs/** の簿記ハンクが mutant 生成・coverage floor を汚染する構造問題を閉じる（LEARNINGS:37）。

- [ ] Step 1: RED テスト追加:

```python
    def test_docs_hunks_excluded_from_added_lines(self):
        # docs/ 配下の新規ファイルは mutant 対象に入らない
        ...fixture repo に docs/STATUS.md（untracked）と src/x.py を置き、
        added_lines_by_file の結果に "docs/STATUS.md" が含まれないこと、
        "src/x.py" は含まれることを assert...

    def test_docs_tracked_changes_excluded_from_coverage_floor(self):
        ...tracked 変更に docs/LEARNINGS.md と src/x.py がある状態で、
        coverage floor の対象集合（run_drill が組む tracked 相当のフィルタ）に
        docs/LEARNINGS.md が入らないことを assert（既存テストの fixture 流儀を踏襲）...
```

- [ ] Step 2: FAIL 確認 → 実装:

```python
DRILL_ARTIFACT_PREFIX = "docs/qa-reports/"
# B1 permanent fix (evolution review 2026-06-10): bookkeeping hunks under docs/
# are not task code — they pollute both mutant generation and the coverage
# floor on framework-mixed diffs (38-hunk case, LEARNINGS:37).
DRILL_EXCLUDED_PREFIXES = ("docs/",)  # superset of DRILL_ARTIFACT_PREFIX


def _drill_excluded(rel: str) -> bool:
    return rel.startswith(DRILL_EXCLUDED_PREFIXES)
```

3 箇所の `startswith(DRILL_ARTIFACT_PREFIX)` を `_drill_excluded(rel)` / `_drill_excluded(f)` に置換（:151・:163-164・:366-367）
- [ ] Step 3: PASS → 全テスト green → コミット `fix(drill): exclude docs/** from mutants and coverage floor (B1 permanent fix)`

**受入条件:** docs/ ハンクが mutant・floor 両方から消える・既存 35 テスト不変
**Deliverable:** [ ] 除外定数 [ ] 2 経路テスト

### タスク 12: standard プロファイルへ Bash ガード 4 種（P2-1）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `templates/profiles/standard.json` / 検証は T14 の smoke
**意図:** 「recommended」プロファイルの moat 不在（破壊・秘密・deploy・control-plane ガードが settings 未登録）を解消。check-tdd は full 限定のまま。

- [ ] Step 1: `hooks_include` を更新:

```json
  "hooks_include": [
    "session-start.sh",
    "check-gate.sh",
    "post-status-audit.sh",
    "pre-compact.sh",
    "check-control-plane.sh",
    "check-destructive.sh",
    "check-secrets.sh",
    "check-deploy-gate.sh"
  ]
```

- [ ] Step 2: `required` に `"hooks/lib/frontmatter.sh"` を追加（extract-input.sh と並び）。`recommended` に `"hooks/check-secrets.sh"`・`"hooks/check-deploy-gate.sh"` を追加（ファイル配布の宣言一貫性）
- [ ] Step 3: `bash bin/setup.sh --profile standard --root /tmp/aegis-std-check` で settings.local.json に PreToolUse Bash 4 hook が並ぶことを目視確認 → `rm -rf /tmp/aegis-std-check`
- [ ] Step 4: コミット `feat(profiles): register Bash guard hooks in standard profile (P2-1)`

**受入条件:** standard install の settings に 4 ガード登録・check-tdd 不在・T14 smoke で実発火
**Deliverable:** [ ] profile 更新 [ ] install 確認

### タスク 13: hooks.template.json の `$CLAUDE_PROJECT_DIR` 化（P3-6）

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `templates/hooks.template.json`（全 command）、`bin/setup.sh:158,177`（script 名抽出）
**意図:** cwd 相対 `bash hooks/x.sh` はサブディレクトリ起動で全 hook 不発になる。プロジェクト絶対参照へ。

- [ ] Step 1: 全 command を置換。形式（クォートは PROJECT_DIR 変数のみを囲む — `/` split 抽出を温存するため）:

```json
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/hooks/session-start.sh"
```

（`sed -i '' 's|"command": "bash hooks/|"command": "bash \\"$CLAUDE_PROJECT_DIR\\"/hooks/|' templates/hooks.template.json` 相当を全 16+ エントリに適用）
- [ ] Step 2: `bin/setup.sh` の抽出 2 箇所（all_hooks 収集 :158 付近と filter :177 付近）を防御的に:

```python
            parts = cmd.split('/')
            if len(parts) >= 2:
                script = parts[-1].strip('"')
```

（all_hooks 側は `all_hooks.add(parts[-1].strip('"'))`）
- [ ] Step 3: 検証: `bash bin/setup.sh --profile standard --root /tmp/aegis-p36` → settings.local.json の全 command が `$CLAUDE_PROJECT_DIR` を含み、hooks_include のフィルタが正しく効いている（standard で check-tdd.sh が落ちている）こと → cleanup
- [ ] Step 4: 既存パーサ回帰（グリル要検討点3）: `python3 -m pytest tests/test_hook_required_coverage.py tests/test_check_status.py -q` — `_HOOK_RE`（`hooks/` アンカー search）と `cmd.split("hooks/")[-1]` は接頭辞付与に耐える設計だが、FAIL した場合は抽出側を追従修正する
- [ ] Step 5: コミット `fix(templates): reference hooks via $CLAUDE_PROJECT_DIR in generated settings (P3-6)`

**受入条件:** template・生成 settings 双方が絶対参照・フィルタ回帰なし（T14 smoke が恒久検証）
**Deliverable:** [ ] template 更新 [ ] 抽出追従

### タスク 14: scaffold smoke の拡張（P2-1/P3-6 の再発封鎖）

**blockedBy:** T0, T12, T13 | **モデル:** `inherit`
**ファイル:** `scripts/eval_scaffold_smoke.py`
**意図:** install 出力の契約化を v1.4.0 分まで拡張（F6 教訓の踏襲）。

- [ ] Step 0: lib 配送契約に frontmatter.sh を追加（グリル穴1）— `eval_scaffold_smoke.py:42` を更新:

```python
REQUIRED_HOOK_LIBS = ["emit.sh", "patterns.sh", "frontmatter.sh"]
```

- [ ] Step 1: 検証関数を追加:

```python
def verify_settings_project_dir(target: Path, profile: str) -> tuple[bool, str]:
    """Generated settings must reference hooks via $CLAUDE_PROJECT_DIR (P3-6)."""
    settings_path = target / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return True, f"{profile}: no settings.local.json (nothing to verify)"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    bad = []
    for entries in data.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if "hooks/" in cmd and "$CLAUDE_PROJECT_DIR" not in cmd:
                    bad.append(cmd)
    if bad:
        return False, f"{profile}: cwd-relative hook commands: {bad}"
    return True, f"{profile}: all hook commands use $CLAUDE_PROJECT_DIR"
```

- [ ] Step 2: standard install の moat 実発火を追加 — 既存 `verify_hooks_runnable` の check-destructive 実発火（:139-144）は「ファイルが存在すれば」発火する実装。T12 後は standard にも配布されるため、**standard プロファイルの run でも check-destructive の ask/deny 発火を必須化**（存在チェックを「standard/full では存在しなければ FAIL」に強める）:

```python
    if profile in ("standard", "full"):
        if not (hooks_dir / "check-destructive.sh").exists():
            return False, f"{profile}: check-destructive.sh not installed (P2-1)"
```

- [ ] Step 3: `main()` の record 群に `verify_settings_project_dir` を minimal/standard/full 各 run へ追加
- [ ] Step 4: `python3 scripts/eval_scaffold_smoke.py` 実行 → 全 PASS 確認 → コミット `feat(smoke): verify $CLAUDE_PROJECT_DIR settings + standard guard + frontmatter lib delivery (P2-1, P3-6)`

**受入条件:** smoke が新 3 検証（lib 配送・settings 参照形・standard 実発火）込みで PASS・T12/T13 を意図的に巻き戻すと FAIL
**Deliverable:** [ ] settings 検証 [ ] standard 実発火

### タスク 15: docs 整理（K-2・LEARNINGS・README 移行節）

**blockedBy:** T1〜T14 の内容確定後 | **モデル:** `inherit`
**ファイル:** `docs/functional-integrity-audit-report-2026-06-07.md:316-322`、`docs/LEARNINGS.md:37`、`README.md`（Migration 節）
**意図:** K-2 重複削除と、B1 恒久対応の記録、v1.4.0 移行手順の明文化。

- [ ] Step 1: 監査レポートの重複節（:316-322 の 2 つ目の `## Layer 3 ...（未着手）` と `## Layer 4 ...（未着手）` ブロック）を削除（:262 の正本と :288 の正本は不変）
- [ ] Step 2: LEARNINGS:37 の B1 エントリ末尾に追記: 「**→ v1.4.0 で恒久対応済み**: run-test-strength-drill.py が docs/** を mutant 生成と coverage floor の両方から除外（DRILL_EXCLUDED_PREFIXES）。」
- [ ] Step 3: README Migration に「### From v1.3.3 to v1.4.0」を v1.3.3 節の上に追加。必須内容: (1) standard プロファイルに Bash ガード 4 種が登録される（再 install または settings.local.json へ手動追記）、(2) deploy gate の拡大（`vercel --prod`/`wrangler`）と S/M の ask 化、(3) `ULTRA_PRECOMPACT_INTERVAL` → `AEGIS_PRECOMPACT_INTERVAL`（旧名は今リリースのみ fallback）、(4) hooks.template.json が `$CLAUDE_PROJECT_DIR` 参照（既存 install は settings 再生成推奨）、(5) `docs/hook-failure-policy.md` 新設の案内。README:161 の standard ファイル数（14 required + 7 recommended）を実数に更新
- [ ] Step 4: コミット `docs: drop duplicate audit sections, record B1 permanent fix, add v1.4.0 migration (K-2)`

**受入条件:** `grep -c "## Layer 3" docs/functional-integrity-audit-report-2026-06-07.md` が 1
**Deliverable:** [ ] K-2 解消 [ ] 移行節

### タスク 16: 版数 v1.4.0＋全証跡

**blockedBy:** T0〜T15 | **モデル:** `inherit`
**ファイル:** `scripts/check_framework_contract.py:17`、`templates/STATUS.template.md:3`、`examples/minimal-project/docs/STATUS.md:3`
**意図:** version owner 一括更新と最終エビデンス（リリース可否は deploy/ship ゲートで判断）。

- [ ] Step 1: `FRAMEWORK_VERSION = "1.4.0"`・template/example の framework_version を `"1.4.0"` に更新（T10 の同期検査が drift を握る）
- [ ] Step 2: フル証跡を取得:
  - `python3 -m pytest tests/ -q`（全 green・件数記録）
  - `python3 scripts/check_framework_contract.py`（および standard 検証モードがあれば同様に）
  - `python3 scripts/check_reference_drift.py`
  - `python3 scripts/eval_scaffold_smoke.py`
  - `python3 scripts/check_status.py --root . --strict`
- [ ] Step 3: コミット `chore(release): v1.4.0 — fix batch (P2/P3/K-2) + hook failure policy + B1 drill fix`（tag はゲート承認後）

**受入条件:** 全検査 PASS・版数 3 箇所一致
**Deliverable:** [ ] 版数 [ ] 証跡一式

## External Integrations

n/a（外部サービス連携なし）

## 事前準備

- [x] python3 / pytest 利用可能（既存 332 tests が前提）
- [x] ベースブランチ main = v1.3.3 リリースコミット以降
- [ ] 作業前に `python3 -m pytest tests/ -q` で現状 green を確認

## トレーサビリティ（要件 → Task → Test）

| 要件 | Task | テスト |
|------|------|--------|
| P2-1 standard の moat 不在 | T12, T14 | eval_scaffold_smoke（settings 登録＋実発火） |
| P2-2 DEPLOY_RE 漏れ | T7 | test_hook_output_schema（match/non-match） |
| P2-3 size-skip fail-open | T8 | test_check_status＋test_hook_output_schema（ask） |
| P2-4 ed25519/ecdsa 未検出 | T4 | test_hook_output_schema（4 経路） |
| P2-5 contract lib 未追跡 | T10 | check_framework_contract 実行 |
| P2-6 example 版数 drift | T10, T16 | contract 版数同期検査 |
| P3-1 task-completed fail-open | T1, T2 | test_failure_policy |
| P3-2 ULTRA_ 旧命名 | T6 | test_hook_output_schema（fallback/優先） |
| P3-3 update-gate 排他なし | T9 | test_update_gate_lock |
| P3-4 WRITE_INDICATORS 偽陽性 | T5 | test_hook_output_schema（偽陽性/真陽性） |
| P3-5 grep -A20 脆弱 | T0, T3 | test_frontmatter_lib（20 行超回帰） |
| P3-6 cwd 相対 hook | T13, T14 | eval_scaffold_smoke（PROJECT_DIR 検証） |
| K-2 監査レポート重複 | T15 | grep -c 受入条件 |
| B1 ドリル構造不能 | T11 | test_test_strength_drill（2 経路） |
| 観察3 ポリシー不在 | T1 | test_failure_policy（表駆動） |
| 観察4 skip 意味論 | T8, T1 | ポリシー表 size-skip 節＋ask テスト |

## 自己レビュー

- 仕様カバレッジ: 設計ノート U1〜U6 の全項目がタスクにマップ済み（U1=T1/T2、U2=T2/T4/T5/T6/T7/T8、U3=T0/T3、U4=T8/T9/T10/T11、U5=T12/T13/T14、U6=T15/T16）
- 設計からの plan 段階確定事項: (a) `frontmatter_section` 補助関数の追加（7 call site の DRY 化、read_frontmatter 契約は設計どおり）、(b) RC=2 の ask マップに `ASK:` マーカー必須（interpreter 異常 RC2 と区別し deny へ倒す）、(c) check-deploy-mcp-gate も同契約で更新（同じ `--check-deploy-ready` を消費するため、放置すると S/M の MCP デプロイが ask 文言の deny になり契約が割れる）、(d) mkdir ロックのリトライ = 0.2s×10 回
- 型整合: `frontmatter_section`（T0 定義）を T3/T9 が同名で消費。`ASK:` マーカー（T8 定義）を T1 のポリシー表 size-skip 節が同語で宣言
- 境界整合: Boundary Map の Consumes はすべて先行タスクの Produces に存在
- grill-plan 反映（2026-06-10）: 穴1=frontmatter.sh 配送契約（T0 Step 5 確認＋T14 Step 0 で REQUIRED_HOOK_LIBS 契約化）、穴2=T1 RED コミット矛盾（T1 はコミットせず T2 と合流）、穴3=DEPLOY_RE 終端クラスに `>` 追加＋境界テスト 2 件。要検討点1=control-plane fixture は既存テスト流儀を転写、要検討点2=advisory crash は T2 スコープ、要検討点3=T13 にパーサ回帰ステップ追加

## リスク

- リスク: T1 のシナリオ fixture が hook ごとの ROOT 解決方式の差（AEGIS_ROOT_OVERRIDE 対応/非対応）で複雑化する
- 対策: override 非対応 hook（check-control-plane 等）は既存 test_hook_output_schema の fixture 流儀をそのまま流用し、新規方式を発明しない
- リスク: DEPLOY_RE の flags-only 形が BSD/GNU grep で挙動差を出す
- 対策: POSIX ERE のみ使用（`+`/`*`/文字クラス）。T7 のテストが両系の回帰を握る（CI は macOS、開発も macOS — GNU 差分は `grep -qEi` の既存利用範囲内）
- リスク: standard への 4 hook 追加で既存 standard install 利用者の体感が変わる（deny/ask が増える）
- 対策: minor 版数＋README 移行節で明示（brainstorm サブ決定 3）

## 完了条件

- [ ] 全テスト pass（pytest・contract・drift・smoke・--strict）
- [ ] レビュー完了（grill-code → review gate）
- [ ] `grep -rn 'grep -A20' hooks/ scripts/ examples/` が空
- [ ] ポリシー表と全 hook 実挙動の突合 green
- [ ] mirror byte-identical（test_mirror_identity）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

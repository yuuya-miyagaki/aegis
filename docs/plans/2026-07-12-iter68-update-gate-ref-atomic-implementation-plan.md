# update-gate `approve --ref` 原子化＋SIGPIPE 耐性＋pending+ref advisory 降格 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-dev（.claude/skills/subagent-dev/SKILL.md）でタスク単位に実装せよ。Steps は checkbox（`- [ ]`）。

**Goal:** ゲート承認と evidence ref 設定を1コマンド・1書込みに原子化し、SIGPIPE でも状態が壊れない writer にし、pending/n/a+ref の contract FAIL を advisory に降格する（罠 a,b,c の機構的根治）。

**Architecture:** bash writer（scripts/update-gate.sh）に `--ref` フラグと「検証→書込み→ACK→snapshot→best-effort 出力」順序＋`trap '' PIPE` を実装。python contract（scripts/check_status.py）は共有関数 `evidence_integrity_violations` の pending/n/a+ref 分岐を WARNING print に降格（呼び出し側2箇所へ自動波及）。ゲート→ref 対応は既存の bash `get_ref_key` ↔ python `GATE_REF_MAPPING` をそのまま使う。

**参照設計:** docs/specs/2026-07-12-iter68-update-gate-ref-atomic-design.md（brainstorm record: 同日 -brainstorm-record.md）

**Tech Stack:** bash 3.2 互換・python3 標準ライブラリのみ・unittest（tests/）

**モデル方針:** implementer subagent は `model:"opus"`（書く=opus）。レビュー/判定は親（fable）。

---

## 事前確認済みの事実（実装者向けコンテキスト）

- `scripts/update-gate.sh` の現行 approve 経路: 検証（check_status --pre-approve-gate）→ **judge カード全文 cat（241-252行）→ `[gate-approve]` echo（304行）→ sed 書込み（320行）** → snapshot → 結果表示。書込み前に大量 stdout があるため pipe 早期クローズで SIGPIPE 死＝状態未変更（罠 a）。
- `reset` は既に「gate 値＋ref null 化」を**単一 sed パス**（SED_ARGS 配列に -e 2本・1回の TMP+mv）で書く（306-320行）。`approve --ref` はこの型の対称形。
- `evidence_integrity_violations`（scripts/check_status.py:549-600）は validate_status_file（=check_framework_contract 経由で full suite の contract テスト）と `--check-completion-evidence`（=TaskCompleted hook）の**2箇所から共有**される。ここを1点変更すれば両方に波及する。
- `pre_approve_gate`（check_status.py:1084-）は ref 空のとき ADVISORY を print する（1111-1126行）。`--ref` 併用時はこの ADVISORY が誤誘導になるので env `AEGIS_PENDING_REF` で抑止する。
- 成功時の `check_gate_prerequisites` は**無出力**（client_ready_for_dev の [spec-delta] 1行を除く）。plan gate は JUDGE_GATES（review/qa/security/deploy）にも qa drill にも該当しない → fixture は plan gate が最も静かで決定的。
- 既存テスト: `tests/test_update_gate_lock.py` の `_scaffold`（scripts copy＋check_status.py symlink＋hooks/lib）を踏襲。`tests/test_check_status.py::TestCheckCompletionEvidence::test_pending_gate_with_ref_is_stale_violation`（2172行）が旧挙動（FAIL）をピン。`tests/test_check_status.py:693-765` の ADVISORY テスト群は env 無しの挙動として存続可能。`tests/test_judge_card_push.py` は出力順序をピンしていない（内容 assertIn のみ）→ 並べ替えの影響なし。
- ランタイム hook（check-runtime-state.sh）は「manifest 許可スクリプトの単体コマンド」を許可判定するため、`--ref <path>` の引数追加は影響しない（`--ack "…"` が既に通っている）。

## File Structure

- Modify: `scripts/update-gate.sh`（flag parser・--ref 検証・書込み先行・trap '' PIPE・na の ref null 化・usage）
- Modify: `scripts/check_status.py`（evidence_integrity_violations 降格・pre_approve_gate ADVISORY 抑止/文言）
- Create: `tests/test_update_gate_ref_atomic.py`（bash 挙動＝原子性・検証系・SIGPIPE E2E・構造ピン）
- Modify: `tests/test_check_status.py`（pending+ref ピンを advisory へ書換え・n/a 対称・AEGIS_PENDING_REF 抑止）
- Modify（guidance 同期）: `.claude/commands/gate.md`・`CLAUDE.md`（Completion Rule 1文）・`.claude/skills/aegis-review-gate/SKILL.md`・`.claude/skills/aegis-security-gate/SKILL.md`・`.claude/skills/qa-verification/SKILL.md`・`.claude/skills/ship-and-docs/SKILL.md`・`.claude/skills/deploy/SKILL.md`・`.claude/skills/client-workflow/SKILL.md`（approve 手順を `approve --ref` 正順へ。該当行は `grep -n "update-gate.sh" <file>` で特定）

---

### Task 1: RED — 失敗するテストを先に書く

**Files:**
- Create: `tests/test_update_gate_ref_atomic.py`
- Modify: `tests/test_check_status.py`（2172行 `test_pending_gate_with_ref_is_stale_violation` 書換え＋追加2本）

- [ ] **Step 1-1: 新規テストファイルを作成**

`tests/test_update_gate_ref_atomic.py`:

```python
#!/usr/bin/env python3
"""update-gate.sh の approve --ref 原子化と SIGPIPE 耐性（iter68・full-review 1-3）。

罠a: 旧実装は状態書込み（sed）より前に judge カード等を stdout へ流すため、
pipe 早期クローズで SIGPIPE 死＝gate 未承認のまま出力だけ欠ける。
罠b/c: gate 値と current_refs が別書込みのため、どちらの順でも
contract（pending+ref / approved+空）が赤くなる窓が開く。
本テストは「--ref 同時書込み」「書込みが承認主張出力に先行」を契約として固定する。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# phase=plan / brainstorm approved → plan gate が prereq を満たし、
# JUDGE_GATES にも qa drill にも該当しない＝pre-approve が無出力で決定的。
STATUS_PLAN_PHASE = """---
framework: aegis
framework_version: "0.12.0"
project_name: test
mode: Dev
phase: plan
task_type: feature
task_size: L
last_updated: "2026-01-01"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: null
  plan: null
  spec: null
  review: null
  qa: null
  security: null
  deploy: null
  translation: null
---
"""

# na 検証用（pre_na_gate は bugfix/hotfix のみ na 許可）。plan gate に
# pending+ref を先置き＝降格後は advisory なので fixture として合法。
STATUS_BUGFIX_NA = STATUS_PLAN_PHASE.replace(
    "task_type: feature", "task_type: bugfix").replace(
    "  plan: null", '  plan: "docs/plans/plan.md"', 1)


class TestUpdateGateRefAtomic(unittest.TestCase):
    def _scaffold(self, d: Path, status: str = STATUS_PLAN_PHASE) -> Path:
        docs = d / "docs"
        (docs / "plans").mkdir(parents=True)
        (docs / "STATUS.md").write_text(status, encoding="utf-8")
        (docs / "plans" / "plan.md").write_text("# plan\n", encoding="utf-8")
        scripts = d / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "update-gate.sh",
                     scripts / "update-gate.sh")
        (scripts / "check_status.py").symlink_to(
            ROOT / "scripts" / "check_status.py")
        shutil.copytree(ROOT / "hooks" / "lib", d / "hooks" / "lib")
        return d

    def _run(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(root / "scripts" / "update-gate.sh"), *args],
            capture_output=True, text=True, check=False, timeout=60)

    def _status(self, root: Path) -> str:
        return (root / "docs" / "STATUS.md").read_text(encoding="utf-8")

    # --- 原子化（罠 b/c） ---

    def test_approve_ref_sets_gate_and_ref_together(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: approved", status)
            self.assertIn('  plan: "docs/plans/plan.md"', status)

    def test_approve_ref_leaves_contract_green_immediately(self):
        """approve --ref 直後に evidence 整合が成立（窓なしの観測的証明）。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            chk = subprocess.run(
                ["python3", str(root / "scripts" / "check_status.py"),
                 "--root", str(root), "--check-completion-evidence"],
                capture_output=True, text=True, check=False, timeout=60)
            self.assertEqual(chk.returncode, 0, f"{chk.stdout}\n{chk.stderr}")
            self.assertNotIn("EVIDENCE:", chk.stdout)

    # --- --ref 検証系（すべて状態不変で exit 1） ---

    def _assert_rejected_no_write(self, root: Path, *args: str) -> None:
        before = self._status(root)
        r = self._run(root, *args)
        self.assertNotEqual(r.returncode, 0,
                            f"must reject: {args}\n{r.stdout}\n{r.stderr}")
        self.assertEqual(before, self._status(root),
                         f"STATUS must be untouched: {args}")

    def test_ref_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", "docs/plans/nope.md")

    def test_ref_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            abs_path = str(root / "docs" / "plans" / "plan.md")
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", abs_path)

    def test_ref_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", "docs/plans/../plans/plan.md")

    def test_ref_unlisted_chars_rejected(self):
        """YAML/sed 安全性は文字 allowlist（[A-Za-z0-9._/-]）で担保する。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            weird = 'docs/plans/we"ird.md'
            (Path(d) / "docs" / "plans" / 'we"ird.md').write_text("x")
            self._assert_rejected_no_write(
                root, "plan", "approve", "--ref", weird)

    def test_ref_on_gate_without_ref_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "brainstorm", "approve", "--ref", "docs/plans/plan.md")

    def test_ref_with_reset_and_na_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "brainstorm", "reset", "--ref", "docs/plans/plan.md")
            self._assert_rejected_no_write(
                root, "plan", "na", "--ref", "docs/plans/plan.md")

    def test_unknown_flag_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            self._assert_rejected_no_write(
                root, "plan", "approve", "--bogus")

    def test_already_approved_ref_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            status = STATUS_PLAN_PHASE.replace("  plan: pending",
                                               "  plan: approved", 1)
            root = self._scaffold(Path(d), status)
            r = self._run(root, "plan", "approve", "--ref", "docs/plans/plan.md")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            self.assertIn("  plan: null", self._status(root),
                          "already-approved は ref を書き換えない")

    # --- na の ref null 化（writer 衛生の対称性） ---

    def test_na_nulls_ref(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d), STATUS_BUGFIX_NA)
            r = self._run(root, "plan", "na")
            self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: n/a", status)
            self.assertNotIn("docs/plans/plan.md", status,
                             "na は current_refs.plan を null 化する")

    # --- SIGPIPE 耐性（罠 a） ---

    def test_closed_stdout_pipe_still_approves(self):
        """読み手のいない pipe に stdout を繋いでも状態変更は完遂する。
        旧実装は書込み前の echo/cat が SIGPIPE 死 → gate pending のまま＝RED。"""
        with tempfile.TemporaryDirectory() as d:
            root = self._scaffold(Path(d))
            r_fd, w_fd = os.pipe()
            os.close(r_fd)  # 読み手なし → write は即 SIGPIPE/EPIPE
            try:
                r = subprocess.run(
                    ["bash", str(root / "scripts" / "update-gate.sh"),
                     "plan", "approve", "--ref", "docs/plans/plan.md"],
                    stdout=w_fd, stderr=subprocess.PIPE, text=True,
                    check=False, timeout=60)
            finally:
                os.close(w_fd)
            self.assertEqual(r.returncode, 0,
                             f"closed pipe must not abort state change: "
                             f"stderr={r.stderr}")
            status = self._status(root)
            self.assertIn("  plan: approved", status)
            self.assertIn('  plan: "docs/plans/plan.md"', status)

    # --- 構造ピン（順序退行の静的ガード） ---

    def test_write_precedes_success_output_structure(self):
        """状態書込み（mv）が承認主張出力（[${ACTION_TAG}] 行・JUDGE CARD push）
        より前にあること。SIGPIPE trap の存在もピンする。"""
        text = (ROOT / "scripts" / "update-gate.sh").read_text(encoding="utf-8")
        self.assertIn("trap '' PIPE", text)
        write_idx = text.index('mv "$TMP" "$STATUS_FILE"')
        self.assertLess(write_idx, text.index("JUDGE CARD"),
                        "judge card push must come after the state write")
        self.assertLess(write_idx, text.index('[${ACTION_TAG}] ${GATE_NAME}:'),
                        "success report must come after the state write")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1-2: 既存ピンを advisory 挙動へ書き換え＋追加**

`tests/test_check_status.py` の `test_pending_gate_with_ref_is_stale_violation`（2172行）を置換し、直後に n/a 対称・ADVISORY 抑止の2本を追加:

```python
    def test_pending_gate_with_ref_is_advisory_not_violation(self):
        # iter68 (1-3): pending gate + present ref は WARNING（advisory）に降格。
        # writer が reset/na で null 化・approve --ref で原子設定するため、
        # 残置 ref は運用衛生であって evidence 偽装ではない。
        content = make_status_md(approvals=dict(ALL_PENDING),
                                 refs={"qa": "docs/qa-reports/qa1.md"})
        with TempProject(content) as root:
            (Path(root) / "docs" / "qa-reports").mkdir(parents=True)
            (Path(root) / "docs" / "qa-reports" / "qa1.md").write_text("ok")
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertEqual(rc, 0, f"pending+ref must not fail: {out}")
            self.assertNotIn("EVIDENCE:", out)
            self.assertIn("WARNING", out, "advisory WARNING must still surface")
            self.assertIn("stale", out)

    def test_na_gate_with_ref_is_advisory_not_violation(self):
        content = make_status_md(approvals={**ALL_PENDING, "qa": "n/a"},
                                 refs={"qa": "docs/qa-reports/qa1.md"})
        with TempProject(content) as root:
            (Path(root) / "docs" / "qa-reports").mkdir(parents=True)
            (Path(root) / "docs" / "qa-reports" / "qa1.md").write_text("ok")
            rc, out = run_check(root, "--check-completion-evidence")
            self.assertEqual(rc, 0, f"n/a+ref must not fail: {out}")
            self.assertNotIn("EVIDENCE:", out)
            self.assertIn("WARNING", out)
```

`TestPreApproveGateRefCheck`（692行のクラス）に追加。`run_check` は env 非対応なので直接 subprocess で呼ぶ（CHECK_STATUS はファイル冒頭の既存定数）:

```python
    def test_pending_ref_env_suppresses_advisory(self):
        """update-gate.sh approve --ref 経由（AEGIS_PENDING_REF セット）では
        「ref が空」ADVISORY を出さない（--ref が原子的に設定するため）。"""
        content = make_status_md(
            phase="plan", task_size="L",
            approvals={"brainstorm": "approved"},
            refs={"plan": "null"},
        )
        with TempProject(content) as root:
            result = subprocess.run(
                ["python3", str(CHECK_STATUS), "--root", root,
                 "--pre-approve-gate", "plan"],
                capture_output=True, text=True,
                env={**os.environ, "AEGIS_PENDING_REF": "docs/plans/plan.md"},
            )
            out = (result.stdout + result.stderr).strip()
            self.assertEqual(result.returncode, 0, out)
            self.assertNotIn("ADVISORY", out,
                             f"--ref 経由では空ref ADVISORY を出さない: {out}")
```

（既存 ADVISORY テスト群（695-765行）は env 無しの挙動として**変更しない**。`test_plan_gate_ref_empty_warns` は文言中の "completion" もピンしているため、Task 2-2 の新 ADVISORY 文言は "completion" を含むこと。`import os` が test_check_status.py 冒頭に無ければ追加。）

- [ ] **Step 1-3: RED を確認**

Run: `python3 -m pytest tests/test_update_gate_ref_atomic.py tests/test_check_status.py -q 2>&1 | tail -15`
Expected: 新ファイルは「unknown argument '--ref'」等で大半 FAIL（`test_write_precedes_success_output_structure` は `trap '' PIPE` 不在で FAIL）。`test_pending_gate_with_ref_is_advisory_not_violation`・`test_na_gate_...`・`test_pending_ref_env_...` FAIL。**既存テストの新規 FAIL がないこと**（分布を記録）。

- [ ] **Step 1-4: Commit**

```bash
git add tests/test_update_gate_ref_atomic.py tests/test_check_status.py
git commit -m "test(iter68): RED — approve --ref 原子化・SIGPIPE 耐性・pending+ref advisory の契約テスト"
```

---

### Task 2: GREEN(1/2) — check_status.py の降格と ADVISORY 抑止

**Files:**
- Modify: `scripts/check_status.py:567-571`（降格）・`scripts/check_status.py:1111-1126`（ADVISORY）

- [ ] **Step 2-1: evidence_integrity_violations の pending/n/a+ref を WARNING print に変更**

置換（567-571行）:

```python
            if gate_value in {"pending", "n/a"} and not ref_is_empty:
                # iter68 (full-review 1-3): advisory, not a violation. The
                # authorized writer nulls refs on reset/na and sets them
                # atomically at `approve --ref`, so a lingering ref under a
                # pending/n/a gate is operator hygiene, not an evidence
                # breach. Enforced invariants stay: approved ⇒ ref exists.
                print(
                    f"WARNING: gate '{gate_key}' is '{gate_value}' but "
                    f"current_refs.{ref_key} still has a value "
                    f"(stale ref: {ref_value}) — advisory only"
                )
```

関数 docstring の「Gate/ref consistency」節に「pending/n/a+ref は WARNING print（非 violation）」の1文を追記。

- [ ] **Step 2-2: pre_approve_gate の ADVISORY を AEGIS_PENDING_REF で抑止＋文言を --ref 推奨へ**

置換（1114-1126行の if ブロック内）:

```python
        if ref_is_empty and not os.environ.get("AEGIS_PENDING_REF"):
            print(
                f"ADVISORY: Approving '{gate_name}' but "
                f"current_refs.{ref_key} is empty."
            )
            print(
                f"         Prefer atomic: bash scripts/update-gate.sh "
                f"{gate_name} approve --ref <evidence-path>; the ref is "
                f"enforced at completion by the TaskCompleted hook."
            )
```

（2行目は既存テスト `test_plan_gate_ref_empty_warns` が "completion" をピンしているため、この語を必ず含める。`import os` が check_status.py 冒頭に無ければ追加＝既存 import 群を確認。）

- [ ] **Step 2-3: python 側テストが GREEN・bash 側は依然 RED を確認**

Run: `python3 -m pytest tests/test_check_status.py -q 2>&1 | tail -5`
Expected: PASS（既存 ADVISORY テスト群含む）。
Run: `python3 -m pytest tests/test_update_gate_ref_atomic.py -q 2>&1 | tail -5`
Expected: 依然 FAIL（bash 未実装）。

- [ ] **Step 2-4: Commit**

```bash
git add scripts/check_status.py
git commit -m "feat(iter68): pending/n/a+ref を advisory WARNING に降格＋approve --ref 時の空ref ADVISORY 抑止"
```

---

### Task 3: GREEN(2/2) — update-gate.sh の --ref・書込み先行・trap

**Files:**
- Modify: `scripts/update-gate.sh`

- [ ] **Step 3-1: trap と usage**

`set -euo pipefail` の直後に:

```bash
# 罠a (full-review R6): SIGPIPE を無視し、pipe 早期クローズ（| head 等）が
# 状態書込み前にスクリプトを殺せないようにする。以降の出力は EPIPE で失敗
# しうるが、書込み前の出力は fail-closed（exit≠0・状態不変）、書込み後は
# best-effort（|| true）で exit 0 を保つ。
trap '' PIPE
```

Usage 文（32-43行と Invalid action 部）を更新:
`Usage: bash scripts/update-gate.sh <gate-name> [approve|na|reset] [--ref <path>] [--ack "reason"]`
＋ `--ref <path>: approve と同時に current_refs.<gate> を原子的に設定（repo 相対・実在ファイルのみ）` の説明行。

- [ ] **Step 3-2: flag parser（positional $3/$4 を置換）**

`ACK_FLAG="${3:-}"` / `ACK_REASON="${4:-}"` を削除し、`ACTION` 定義の後に:

```bash
ACK_SET=false
ACK_REASON=""
REF_PATH=""
if [ "$#" -ge 2 ]; then shift 2; else shift "$#"; fi
while [ "$#" -gt 0 ]; do
  case "$1" in
    --ack)
      [ "$#" -ge 2 ] || { echo "ERROR: --ack requires a reason"; exit 1; }
      ACK_SET=true; ACK_REASON="$2"; shift 2 ;;
    --ref)
      [ "$#" -ge 2 ] || { echo "ERROR: --ref requires a path"; exit 1; }
      REF_PATH="$2"; shift 2 ;;
    *)
      echo "ERROR: unknown argument '$1'"
      echo "Usage: bash scripts/update-gate.sh <gate-name> [approve|na|reset] [--ref <path>] [--ack \"reason\"]"
      exit 1 ;;
  esac
done
```

後段の `[ "$ACK_FLAG" != "--ack" ]` 判定は `[ "$ACK_SET" != "true" ]` に置換（`--ack ""` が従来同様「理由なし」扱いになることを保つ）。

- [ ] **Step 3-3: get_ref_key を前方移動し GATE_REF_KEY を一度だけ計算、--ref を検証**

`get_ref_key()`（289-300行）を gate 名検証の直後へ移動し、続けて:

```bash
GATE_REF_KEY=$(get_ref_key "$GATE_NAME")

if [ -n "$REF_PATH" ]; then
  if [ "$ACTION" != "approve" ]; then
    echo "ERROR: --ref is only valid with the 'approve' action."
    exit 1
  fi
  if [ -z "$GATE_REF_KEY" ]; then
    echo "ERROR: gate '$GATE_NAME' has no current_refs key; --ref is not applicable."
    exit 1
  fi
  case "$REF_PATH" in
    /*) echo "ERROR: --ref path must be repo-relative: $REF_PATH"; exit 1 ;;
    *..*) echo "ERROR: --ref path must not contain '..': $REF_PATH"; exit 1 ;;
    *[!A-Za-z0-9._/-]*)
      # allowlist: YAML 引用と sed 置換の双方を追加エスケープなしで安全にする
      echo "ERROR: --ref path contains unsupported characters: $REF_PATH"; exit 1 ;;
  esac
  if [ ! -f "${ROOT}/${REF_PATH}" ]; then
    echo "ERROR: --ref file not found: ${REF_PATH}"
    exit 1
  fi
fi
```

既存 reset 分岐の `REF_KEY=$(get_ref_key "$GATE_NAME")` は `GATE_REF_KEY` 参照に統一。

- [ ] **Step 3-4: approve case の再構成（書込み前は検証のみ・出力は guard）**

approve case（196-255行）を以下に:
1. already-approved 早期 exit: `--ref` 併用時は `echo "NOTE: --ref は未適用（既 approved の ref 差し替えはスコープ外）" || true` を追加。
2. n/a エラーはそのまま。
3. GATE_CHECK 呼び出しの直前に `[ -n "$REF_PATH" ] && export AEGIS_PENDING_REF="$REF_PATH"`（`if` 形式で set -e 安全に）。
4. `echo "$GATE_CHECK"` → `if [ -n "$GATE_CHECK" ]; then echo "$GATE_CHECK" || true; fi`
5. 🟡 branch: 指示 echo 群に `|| true` を付け、`ACK_RECORD=true` フラグだけ立てる（**ACK 追記とその echo をここから削除**）。
6. **B2 judge-card push ブロック（237-252行）をここから削除**（Step 3-6 の report へ移動）。
7. `TARGET_VALUE="approved"` / `ACTION_TAG="gate-approve"` は従来どおり。
（case の外・冒頭付近に `ACK_RECORD=false` を初期化）

- [ ] **Step 3-5: 書込みブロック（単一 sed パス＝reset の型を三態に拡張）**

302-323行を置換:

```bash
# --- Update STATUS.md (STATE FIRST — before any success output; 罠a) ---
TMP="${STATUS_FILE}.tmp.$$"
SED_ARGS=(-e "/^gate_approvals:/,/^[a-z]/ s|\(  ${GATE_NAME_SED}:\).*|\1 ${TARGET_VALUE}|")
if { [ "$ACTION" = "reset" ] || [ "$ACTION" = "na" ]; } && [ -n "$GATE_REF_KEY" ]; then
  REF_KEY_SED=$(printf '%s\n' "$GATE_REF_KEY" | sed 's/[.[\/*^$&]/\\&/g')
  SED_ARGS+=(-e "/^current_refs:/,/^[a-z]/ s|\(  ${REF_KEY_SED}:\).*|\1 null|")
elif [ "$ACTION" = "approve" ] && [ -n "$REF_PATH" ]; then
  REF_KEY_SED=$(printf '%s\n' "$GATE_REF_KEY" | sed 's/[.[\/*^$&]/\\&/g')
  # REF_PATH は allowlist 検証済み（\ & | " を含み得ない）→ 置換部そのまま安全
  SED_ARGS+=(-e "/^current_refs:/,/^[a-z]/ s|\(  ${REF_KEY_SED}:\).*|\1 \"${REF_PATH}\"|")
fi
sed "${SED_ARGS[@]}" "$STATUS_FILE" > "$TMP" && mv "$TMP" "$STATUS_FILE"
```

（旧 304行の `echo "[${ACTION_TAG}] ..."` と 321-323行の reset echo は削除＝report へ移動。na の ref null 化はここで挙動追加）

- [ ] **Step 3-6: 書込み後 — ACK 追記→snapshot→best-effort report**

```bash
# --- Post-write file mutations (stdout 非依存・書込み成立後のみ記録) ---
if [ "$ACK_RECORD" = "true" ]; then
  CARD="${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md"
  if [ -f "$CARD" ]; then
    printf '\n## ACK\n- %s （%s）\n' "$ACK_REASON" "$(date '+%Y-%m-%d %H:%M')" >> "$CARD"
  fi
fi

# --- Update snapshot atomically（既存コメントごと維持） ---
source "${ROOT}/hooks/lib/snapshot.sh" 2>/dev/null || true
if command -v aegis_write_snapshot >/dev/null 2>&1; then
  aegis_write_snapshot "$ROOT" || true
fi

# --- Best-effort report: 状態は永続化済み。出力失敗（EPIPE 等）は無害化 ---
print_report() {
  echo "[${ACTION_TAG}] ${GATE_NAME}: ${CURRENT} → ${TARGET_VALUE}"
  if { [ "$ACTION" = "reset" ] || [ "$ACTION" = "na" ]; } && [ -n "$GATE_REF_KEY" ]; then
    echo "[${ACTION_TAG}] current_refs.${GATE_REF_KEY} → null"
  fi
  if [ "$ACTION" = "approve" ] && [ -n "$REF_PATH" ]; then
    echo "[${ACTION_TAG}] current_refs.${GATE_REF_KEY} → \"${REF_PATH}\""
  fi
  if [ "$ACK_RECORD" = "true" ]; then
    # Brace-delimit ${GATE_NAME}: bash 3.2 は多バイト文字直前の bare 変数を誤解析
    echo "[gate-ack] ${GATE_NAME}: 🟡 を ack で承認（理由記録: ${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md）"
  fi
  if [ "$ACTION" = "approve" ]; then
    # B2 judge-card push (P1-C2, OBS-019)（既存コメントごと移設）
    case "$GATE_NAME" in
      review|qa|security|deploy)
        CARD_FILE="${ROOT}/docs/qa-reports/judge-${GATE_NAME}.md"
        if [ -f "$CARD_FILE" ]; then
          echo ""
          echo "===== JUDGE CARD (${GATE_NAME}) ====="
          cat "$CARD_FILE"
          echo "===== END JUDGE CARD ====="
          echo "[judge-card] 上のカードを平易な日本語で依頼者に提示してください（「次のアクション」欄は文脈に合わせて補完）。"
        fi
        ;;
    esac
  fi
  echo "[${ACTION_TAG}] STATUS.md and .gate-snapshot updated."
  echo ""
  echo "Current gate status:"
  frontmatter_section "$STATUS_FILE" gate_approvals | grep "^  " | sed 's/^  /  /'
}
print_report 2>/dev/null || true
```

注意: 旧 336-343行（updated echo＋Show result）は print_report に吸収して削除。`[gate-reset] current_refs...` の文言は従来と同一形を保つ（test_update_gate_lock は STATUS 内容しか見ないが、演習ログ互換のため）。

- [ ] **Step 3-7: 全テスト GREEN を確認**

Run: `python3 -m pytest tests/test_update_gate_ref_atomic.py tests/test_update_gate_lock.py tests/test_judge_card_push.py tests/test_check_status.py -q 2>&1 | tail -5`
Expected: 全 PASS（lock 系は既知 flaky `test_lock_held_blocks_noop_approve` に注意＝fail 時は単独再実行で切り分け）。

- [ ] **Step 3-8: full suite**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -5`
Expected: 全 PASS（iter67 時点 1148 passed/2 skipped ＋今回追加分。guidance トークン系テストが skill 文言をピンしていて赤くなる場合は Task 4 で該当 guidance を先に直してから再実行）。

- [ ] **Step 3-9: Commit**

```bash
git add scripts/update-gate.sh
git commit -m "feat(iter68): update-gate approve --ref 原子書込み＋状態変更を出力より先に（trap '' PIPE・best-effort report）＋na の ref null 化"
```

---

### Task 4: guidance 同期＋記録

**Files:**
- Modify: `.claude/commands/gate.md`・`CLAUDE.md`・`.claude/skills/{aegis-review-gate,aegis-security-gate,qa-verification,ship-and-docs,deploy,client-workflow}/SKILL.md`

- [ ] **Step 4-1: /gate command doc**

`.claude/commands/gate.md` の approve 節（30行付近）に正順を追記:

```markdown
# 推奨（原子承認: gate 値と evidence ref を1書込みで設定・stale-ref 窓なし）
bash scripts/update-gate.sh <gate-name> approve --ref <evidence-path>
```

＋ na/reset が ref を null 化すること・pending+ref は WARNING（advisory）へ降格済みであることを1-2行で注記。

- [ ] **Step 4-2: CLAUDE.md Completion Rule の1文更新**

現行: 「approved `review`/`qa`/`security`/`deploy`/`plan` gates declare their `current_refs` entry (and `pending`/`n/a` gates leave it null); every declared ref points to an existing file.」
→ 「approved `review`/`qa`/`security`/`deploy`/`plan` gates declare their `current_refs` entry (set atomically via `approve --ref`); every declared ref points to an existing file. `pending`/`n/a` gates keep refs null — deviations are advisory WARNINGs.」
（Enforced 文はそのまま。context budget: 増分 ~10 語）

- [ ] **Step 4-3: skill の approve 手順を --ref 正順へ**

各ファイルで `grep -n "update-gate.sh" <file>` し、gate approve 行を evidence ref 付きの正順に更新（例: `bash scripts/update-gate.sh review approve --ref docs/qa-reports/iterNN-review.md`）。「ref を先に set してから approve」「approve 後に ref を set」を指示する記述があれば「approve --ref で同時に」へ書き換え。ref を持たない gate（brainstorm/dev_ready_for_client）の行は変更しない。

- [ ] **Step 4-4: full suite＋record**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: 全 PASS。
Run: `python3 scripts/record-test-result.py "python3 -m pytest tests/ -q"`（src:manual で green を記録）
Run: `python3 scripts/check_framework_contract.py 2>&1 | tail -3`
Expected: PASS。

- [ ] **Step 4-5: Commit**

```bash
git add .claude/commands/gate.md CLAUDE.md .claude/skills/
git commit -m "docs(iter68): approve --ref 正順を guidance へ同期（/gate・CLAUDE.md 完了規則・gate 系 skill）"
```

---

## 受入条件（サマリ）

1. `approve --ref` で gate 値と ref が**1書込み**で立ち、直後の `--check-completion-evidence` が rc 0（窓なし）。
2. stdout が閉じた pipe でも approve が完遂し rc 0（罠 a 根治）・状態書込みが承認主張出力に先行（構造ピン）。
3. pending/n/a+ref は contract/完了検査とも rc 0＋WARNING（罠 b/c の FAIL 根治）。approved+空 ref・ref 不在は FAIL 維持（無緩和）。
4. --ref の不正入力（不在/絶対/../allowlist 外/対象外 gate/approve 以外）は全て exit 1・状態不変。
5. 既存挙動の非退行: reset の ref null 化・lock プロトコル・--ack 経路・B2 card push 内容・ADVISORY（env 無し時）。
6. full suite green・contract PASS・guidance 同期済み。

## 残課題・ship 判断メモ

- version bump は ship フェーズで判断: CLI 加算（--ref）＋enforcement 意味論変更（FAIL→WARNING）＝ **MINOR（v1.26.2→v1.27.0）候補**。
- LEARNINGS line137 の ref-window 軸「解消済み」更新は docs フェーズで実施。
- bash `get_ref_key` ↔ python `GATE_REF_MAPPING` の drift guard: 既存 parity テスト群（test_parser_parity_driftguard 等）に未収載なら、grill-plan/review の指摘次第で追加検討（本計画では見送り＝両者に同時変更なし）。

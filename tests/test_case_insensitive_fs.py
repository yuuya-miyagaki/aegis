#!/usr/bin/env python3
"""iter54 C-1: ケース非依存FS（macOS/Windows 既定）での moat / secrets バイパス封鎖。

2026-07-02 グリルで再現した新規クラス: 実運用 OS のケース非依存 FS では
`cp evil HOOKS/lib/emit.sh` が実ファイル hooks/lib/emit.sh に書き込むのに、
deny hook 群は小文字リテラル前提の文字列判定で allow していた
（control-plane moat と secrets ガードの両方がバイパス可能）。

修正 = 条件付き case-fold:
- `hooks/lib/safety.sh` の `aegis_fs_case_insensitive <root>`（`-ef` で同一 inode 確認）
  が真のときだけ fold（case-sensitive Linux の実在別 dir HOOKS/ は誤ブロックしない）。
- `AEGIS_CASE_FOLD_FORCE=1` は fold を**強制 ON**する strengthen-only の
  テスト/運用オーバーライド（deny を広げる方向のみ。OFF 側の環境変数は存在しない
  — session env 汚染で moat を弱体化できないため）。
- check-secrets の credential 判定は無条件 -i（case-sensitive FS でも大文字鍵名
  KEY.PEM は実在の鍵ファイル＝捕捉は純増）。

ハーネスは tests/test_control_plane_allowlist.py / test_check_gate_root_external.py と同一。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- FS のケース非依存性をプローブ（skip 判定用） ---
with tempfile.TemporaryDirectory() as _t:
    (Path(_t) / "casefold_probe_lc").mkdir()
    CASE_INSENSITIVE_FS = (Path(_t) / "CASEFOLD_PROBE_LC").is_dir()

FORCE_ENV = {"AEGIS_CASE_FOLD_FORCE": "1"}


def _env(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env.pop("AEGIS_CASE_FOLD_FORCE", None)
    if extra:
        env.update(extra)
    return env


# ---------------------------------------------------------------------------
# safety.sh: aegis_fs_case_insensitive プローブヘルパ
# ---------------------------------------------------------------------------
class TestProbeHelper(unittest.TestCase):
    def _probe(self, root: Path, env_extra: dict | None = None) -> int:
        r = subprocess.run(
            ["bash", "-c",
             'source "$1"; aegis_fs_case_insensitive "$2"',
             "_", str(ROOT / "hooks" / "lib" / "safety.sh"), str(root)],
            capture_output=True, text=True, env=_env(env_extra))
        return r.returncode

    def test_helper_exists(self):
        text = (ROOT / "hooks" / "lib" / "safety.sh").read_text(encoding="utf-8")
        self.assertIn("aegis_fs_case_insensitive", text)

    def test_missing_hooks_dir_is_case_sensitive_verdict(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertNotEqual(self._probe(Path(t)), 0,
                                "root without hooks/ must NOT report case-insensitive")

    @unittest.skipUnless(CASE_INSENSITIVE_FS, "needs a case-insensitive FS")
    def test_case_insensitive_fs_detected(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "hooks").mkdir()
            self.assertEqual(self._probe(Path(t)), 0)

    @unittest.skipIf(CASE_INSENSITIVE_FS, "needs a case-sensitive FS")
    def test_separate_uppercase_dir_not_misdetected(self):
        """case-sensitive FS 上の実在別 dir HOOKS/ は -ef で弁別され偽（grill 穴2）。"""
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "hooks").mkdir()
            (Path(t) / "HOOKS").mkdir()
            self.assertNotEqual(self._probe(Path(t)), 0)

    def test_force_env_strengthens_only(self):
        """AEGIS_CASE_FOLD_FORCE=1 はどの FS でも fold を ON にする（deny 拡大方向のみ）。"""
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self._probe(Path(t), FORCE_ENV), 0)


# ---------------------------------------------------------------------------
# iter57: check-control-plane.sh 退役。安定 CP（hooks/scripts/templates/CLAUDE.md）
# への **Bash write** の case-fold バイパス防御は、静的 hook ではなく OS-lock が担う
# ようになった（syscall はケース非依存 FS で HOOKS/→hooks/ を解決して EACCES＝形非
# 依存に遮断）。その回帰は tests/test_cp_lock_sf_catalog.py の case-fold 形が固定する。
# check-gate（Edit/Write の CP 編集 deny）と check-secrets（credential 判定）の
# case-fold は下記クラスで存置する（これらは退役しない）。
# ---------------------------------------------------------------------------
def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _denied_or_ask(out: str) -> bool:
    return ('"permissionDecision":"deny"' in out
            or '"permissionDecision":"ask"' in out)


# ---------------------------------------------------------------------------
# check-gate.sh
# ---------------------------------------------------------------------------
GATE_STATUS_TMPL = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ngate_approvals:\n  plan: {plan}\n---\n"
)


def _gate_scratch(mode="Dev", task_type="feature", plan="pending",
                  phase="implement") -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        GATE_STATUS_TMPL.format(mode=mode, task_type=task_type, plan=plan,
                                phase=phase), encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _gate_hook(root: Path, file_path: str, env_extra: dict | None = None) -> str:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-gate.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root),
        env=_env(env_extra))
    return r.stdout


class TestGateCaseFold(unittest.TestCase):
    def test_uppercase_hooks_edit_denied(self):
        with _gate_scratch(task_type="feature", plan="approved") as name:
            root = Path(name)
            out = _gate_hook(root, "HOOKS/lib/emit.sh", FORCE_ENV)
            self.assertTrue(_denied(out),
                            f"HOOKS/ edit must deny for non-framework task: {out[:200]!r}")

    def test_uppercase_claude_md_edit_denied(self):
        with _gate_scratch(task_type="feature", plan="approved") as name:
            root = Path(name)
            out = _gate_hook(root, "CLAUDE.MD", FORCE_ENV)
            self.assertTrue(_denied(out), f"CLAUDE.MD edit must deny: {out[:200]!r}")

    def test_uppercase_root_absolute_still_gated(self):
        """ROOT を大文字化した絶対パスは case-insensitive FS では project 内部
        ＝ROOT-external 短絡 allow に流れてはならない（plan pending なら deny）。"""
        with _gate_scratch(task_type="feature", plan="pending") as name:
            root = Path(name)
            upper = str(root).upper()
            if upper == str(root):  # パスに英字が無い等 — 大文字化が無意味なら skip
                self.skipTest("root path has no case to flip")
            out = _gate_hook(root, upper + "/src/app.py", FORCE_ENV)
            self.assertTrue(_denied(out),
                            f"uppercase-ROOT internal path must stay gated: {out[:200]!r}")

    def test_framework_task_uppercase_hooks_edit_allowed(self):
        with _gate_scratch(task_type="framework", plan="approved") as name:
            root = Path(name)
            out = _gate_hook(root, "HOOKS/lib/emit.sh", FORCE_ENV)
            self.assertTrue(_allowed(out),
                            f"framework task may edit hooks (any case): {out[:200]!r}")

    def test_lowercase_hooks_edit_denied_without_force(self):
        with _gate_scratch(task_type="feature", plan="approved") as name:
            root = Path(name)
            out = _gate_hook(root, "hooks/lib/emit.sh")
            self.assertTrue(_denied(out), f"baseline deny must hold: {out[:200]!r}")


# ---------------------------------------------------------------------------
# check-secrets.sh（credential 判定は無条件 -i ＝ FORCE 不要・全 FS で決定論）
# ---------------------------------------------------------------------------
def _secrets_scratch(git: bool = False) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-secrets.sh", hooks_dir / "check-secrets.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "secrets-patterns.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    if git:
        subprocess.run(["git", "init", "-q"], cwd=str(p), check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit", "--allow-empty",
                        "-q", "-m", "init"],
                       check=True, capture_output=True)
    return tmp


def _secrets_hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-secrets.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root),
        env=_env())
    return r.stdout


class TestSecretsCaseFold(unittest.TestCase):
    def test_uppercase_pem_stage_denied(self):
        with _secrets_scratch() as name:
            out = _secrets_hook(Path(name), "git add key.PEM")
            self.assertTrue(_denied(out), f"key.PEM stage must deny: {out[:200]!r}")

    def test_uppercase_id_rsa_stage_denied(self):
        with _secrets_scratch() as name:
            out = _secrets_hook(Path(name), "git add ID_RSA")
            self.assertTrue(_denied(out), f"ID_RSA stage must deny: {out[:200]!r}")

    def test_uppercase_env_example_stage_allowed(self):
        """対称 -i（grill 穴4）: .ENV.EXAMPLE は safe variant＝deny してはならない。"""
        with _secrets_scratch() as name:
            out = _secrets_hook(Path(name), "git add .ENV.EXAMPLE")
            self.assertTrue(_allowed(out),
                            f".ENV.EXAMPLE must stay allowed: {out[:200]!r}")

    def test_broad_stage_with_uppercase_pem_denied(self):
        with _secrets_scratch(git=True) as name:
            root = Path(name)
            (root / "KEY.PEM").write_text("---BEGIN---\n")
            out = _secrets_hook(root, "git add -A")
            self.assertTrue(_denied(out),
                            f"broad stage with KEY.PEM present must deny: {out[:200]!r}")

    def test_commit_with_staged_uppercase_pem_denied(self):
        with _secrets_scratch(git=True) as name:
            root = Path(name)
            (root / "KEY.PEM").write_text("---BEGIN---\n")
            subprocess.run(["git", "-C", str(root), "add", "KEY.PEM"],
                           check=True, capture_output=True)
            out = _secrets_hook(root, "git commit -m x")
            self.assertTrue(_denied(out),
                            f"commit with staged KEY.PEM must deny: {out[:200]!r}")

    def test_commit_with_staged_uppercase_env_example_allowed(self):
        with _secrets_scratch(git=True) as name:
            root = Path(name)
            (root / ".ENV.EXAMPLE").write_text("KEY=placeholder\n")
            subprocess.run(["git", "-C", str(root), "add", "-f", ".ENV.EXAMPLE"],
                           check=True, capture_output=True)
            out = _secrets_hook(root, "git commit -m x")
            self.assertTrue(_allowed(out),
                            f"staged .ENV.EXAMPLE must stay allowed: {out[:200]!r}")

    def test_uppercase_git_commit_with_staged_pem_denied(self):
        """grill-code Should-fix: `GIT COMMIT` も FS lookup で /bin/git に解決
        ＝トリガは CMD_LC で fold（-C パス抽出は raw のまま）。"""
        with _secrets_scratch(git=True) as name:
            root = Path(name)
            (root / "KEY.PEM").write_text("---BEGIN---\n")
            subprocess.run(["git", "-C", str(root), "add", "KEY.PEM"],
                           check=True, capture_output=True)
            out = _secrets_hook(root, "GIT COMMIT -m x")
            self.assertTrue(_denied(out),
                            f"uppercase GIT COMMIT must still scan staged: {out[:200]!r}")

    def test_lowercase_pem_stage_still_denied(self):
        with _secrets_scratch() as name:
            out = _secrets_hook(Path(name), "git add key.pem")
            self.assertTrue(_denied(out), f"baseline deny must hold: {out[:200]!r}")

    def test_plain_add_still_allowed(self):
        with _secrets_scratch(git=True) as name:
            out = _secrets_hook(Path(name), "git add src/app.py")
            self.assertTrue(_allowed(out), f"plain add must allow: {out[:200]!r}")


# ---------------------------------------------------------------------------
# post-status-audit.sh（gate-tamper 検知の target filter）
# ---------------------------------------------------------------------------
AUDIT_STATUS = (
    "---\nframework: aegis\nmode: Dev\nphase: implement\n"
    "task_type: feature\ntask_size: M\n"
    "gate_approvals:\n  client_ready_for_dev: n/a\n  brainstorm: approved\n"
    "  plan: {plan}\n  review: pending\n  qa: pending\n  security: pending\n"
    "  deploy: pending\n  dev_ready_for_client: pending\n---\n"
)


def _audit_scratch(status_plan: str, snapshot_plan: str) -> tempfile.TemporaryDirectory:
    """snapshot と STATUS の plan gate を食い違わせた（=tamper 状態の）scratch root。"""
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        AUDIT_STATUS.format(plan=status_plan), encoding="utf-8")
    (p / ".claude").mkdir()
    (p / ".claude" / ".gate-snapshot").write_text(
        "gate_approvals:\n  client_ready_for_dev: n/a\n  brainstorm: approved\n"
        f"  plan: {snapshot_plan}\n  review: pending\n  qa: pending\n"
        "  security: pending\n  deploy: pending\n  dev_ready_for_client: pending\n"
        "phase: implement\nmode: Dev\ntask_type: feature\ntask_size: M\n",
        encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "post-status-audit.sh",
                 hooks_dir / "post-status-audit.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh",
                "snapshot.sh", "phase-skills.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _audit_hook(root: Path, file_path: str, env_extra: dict | None = None) -> str:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    env = _env(env_extra)
    env["CLAUDE_PROJECT_DIR"] = str(root)
    r = subprocess.run(
        ["bash", str(root / "hooks" / "post-status-audit.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root), env=env)
    return r.stdout


class TestStatusAuditCaseFold(unittest.TestCase):
    """grill-code Critical: filter `*STATUS.md)` が case-sensitive だと、macOS の
    `Edit(docs/STATUS.MD)` は実 STATUS.md への gate tamper なのに監査ごとスキップ。"""

    def test_uppercase_status_edit_tamper_blocked(self):
        with _audit_scratch(status_plan="approved", snapshot_plan="pending") as name:
            root = Path(name)
            out = _audit_hook(root, str(root / "docs" / "STATUS.MD"), FORCE_ENV)
            self.assertIn('"decision":"block"', out,
                          f"case-variant STATUS edit must still be audited: {out[:200]!r}")
            self.assertIn("gate-tamper", out)

    def test_lowercase_status_edit_tamper_blocked(self):
        """挙動保存: 従来経路の tamper 検知は不変。"""
        with _audit_scratch(status_plan="approved", snapshot_plan="pending") as name:
            root = Path(name)
            out = _audit_hook(root, str(root / "docs" / "STATUS.md"), FORCE_ENV)
            self.assertIn('"decision":"block"', out)

    def test_unrelated_uppercase_file_still_skipped(self):
        """fold 後も STATUS.md 以外（README.MD 等）は監査対象外のまま。"""
        with _audit_scratch(status_plan="approved", snapshot_plan="pending") as name:
            root = Path(name)
            out = _audit_hook(root, str(root / "docs" / "README.MD"), FORCE_ENV)
            self.assertEqual(out.strip(), "{}",
                             f"non-STATUS file must skip the audit: {out[:200]!r}")

    def test_clean_uppercase_status_edit_allowed(self):
        """tamper が無ければ大文字表記の STATUS 編集も allow（誤 block しない）。"""
        with _audit_scratch(status_plan="pending", snapshot_plan="pending") as name:
            root = Path(name)
            out = _audit_hook(root, str(root / "docs" / "STATUS.MD"), FORCE_ENV)
            self.assertEqual(out.strip(), "{}",
                             f"clean edit must stay allowed: {out[:200]!r}")


if __name__ == "__main__":
    unittest.main()

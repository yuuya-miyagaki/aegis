#!/usr/bin/env python3
"""Fix 1 (本丸): check-gate.sh の最終ゲート判定を size-aware にする。

背景: 現行 check-gate.sh はコード編集を無条件で plan gate 承認要求していたが、
S サイズの phase 集合に plan フェーズは存在せず（impl->review->ship->docs・
docs は Fix 3a で追加）、
feature/refactor/framework は plan を n/a 化もできない → S でコード編集が
構造的に不能だった。本修正は task_size を読み、S は implement 直前の承認
ゲート（brainstorm）を検査、それ以外（M/L/未設定/不正値）は従来どおり
plan gate を検査する（保守的デフォルト＝gate を緩めない）。

ハーネスは tests/test_check_gate_root_external.py を踏襲: scratch root に
check-gate.sh をコピーし hooks/lib を symlink、STATUS fixture を書き、
PreToolUse JSON を stdin に渡して起動。emit_allow は exactly "{}" を出す
(hooks/lib/emit.sh) ので allow は厳密 assert（`if out:` ガード不可）。

STATUS テンプレートは既存より拡張: task_size キーと gate_approvals の
brainstorm・plan 両キーを持つ。
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_check_status():
    """check_status.py を in-process import（読み取り専用・差し替え禁止）。

    module-level 定数（SIZE_ALLOWED_PHASES / PHASE_REQUIRES_GATES）を SoT として
    直接参照するためだけに import する。main() は __name__ ガード下なので副作用なし。
    """
    path = ROOT / "scripts" / "check_status.py"
    spec = importlib.util.spec_from_file_location("check_status_sot", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# 拡張テンプレ: task_size を持ち、gate_approvals に brainstorm・plan 双方を持つ。
STATUS_TMPL = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ntask_size: {task_size}\n"
    "gate_approvals:\n  brainstorm: {brainstorm}\n  plan: {plan}\n---\n"
)

# task_size キー自体を省いたテンプレ（後方互換ケース e 用）。
STATUS_TMPL_NO_SIZE = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\n"
    "gate_approvals:\n  brainstorm: {brainstorm}\n  plan: {plan}\n---\n"
)

# gate_approvals に brainstorm キー自体を省いたテンプレ（fail-closed ケース g 用）。
STATUS_TMPL_NO_BRAINSTORM = (
    "---\nframework: aegis\nmode: {mode}\nphase: {phase}\n"
    "task_type: {task_type}\ntask_size: {task_size}\n"
    "gate_approvals:\n  plan: {plan}\n---\n"
)


def _scratch_root(status_text: str) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(status_text, encoding="utf-8")
    (p / "src").mkdir()
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-gate.sh", hooks_dir / "check-gate.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, file_path: str, tool: str = "Edit") -> str:
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-gate.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


def _allowed(out: str) -> bool:
    return out.strip() == "{}"


def _denied(out: str) -> bool:
    return '"permissionDecision":"deny"' in out


def _src(root: Path) -> str:
    return str(root / "src" / "app.py")


class TestCheckGateSizeAware(unittest.TestCase):
    def test_a_size_s_brainstorm_approved_plan_pending_allows(self):
        """(a) S・brainstorm=approved・plan=pending・implement → allow ({}).
        現行実装は plan pending で deny するため RED。この失敗が欠陥の実証。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="feature",
                                 task_size="S", brainstorm="approved", plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_allowed(out),
                        f"S+brainstorm approved must allow ({{}}), got: {out!r}")

    def test_b_size_s_brainstorm_pending_denies_reason_mentions_brainstorm(self):
        """(b) S・brainstorm=pending → deny、deny 理由に 'brainstorm' を含む。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="feature",
                                 task_size="S", brainstorm="pending", plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_denied(out), f"S+brainstorm pending must deny, got: {out!r}")
        self.assertIn("brainstorm", out,
                      f"deny reason must mention brainstorm (fail-visible), got: {out!r}")

    def test_c_bugfix_size_s_brainstorm_na_plan_pending_allows(self):
        """(c) bugfix・S・brainstorm=n/a・plan=pending → allow。
        bugfix は brainstorm/plan が n/a（bug-diagnosis）。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="bugfix",
                                 task_size="S", brainstorm="n/a", plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_allowed(out),
                        f"bugfix S+brainstorm n/a must allow ({{}}), got: {out!r}")

    def test_d1_size_m_plan_pending_denies(self):
        """(d) M・plan=pending → deny（従来挙動の回帰ピン）。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="feature",
                                 task_size="M", brainstorm="approved", plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_denied(out), f"M+plan pending must deny, got: {out!r}")

    def test_d2_size_m_plan_approved_brainstorm_pending_allows(self):
        """(d) M・plan=approved・brainstorm=pending → allow。
        M は brainstorm を見ない（plan gate のみ）ことの回帰ピン。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="feature",
                                 task_size="M", brainstorm="pending", plan="approved")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_allowed(out),
                        f"M+plan approved must allow regardless of brainstorm, got: {out!r}")

    def test_e_no_task_size_key_plan_pending_denies(self):
        """(e) task_size キー自体なし・plan=pending → deny（後方互換）。"""
        txt = STATUS_TMPL_NO_SIZE.format(mode="Dev", phase="implement",
                                         task_type="feature", brainstorm="approved",
                                         plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_denied(out),
                        f"missing task_size + plan pending must deny, got: {out!r}")

    def test_f_invalid_task_size_xl_plan_pending_denies(self):
        """(f) task_size=XL（不正値）・plan=pending → deny（保守的デフォルト）。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="feature",
                                 task_size="XL", brainstorm="approved", plan="pending")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_denied(out),
                        f"invalid task_size XL + plan pending must deny, got: {out!r}")

    def test_h_bugfix_size_m_plan_na_allows(self):
        """(h) bugfix・M・plan=n/a → allow（else 分岐の n/a 許容ピン）。

        bugfix/hotfix は brainstorm+plan=n/a（bug-diagnosis）であり、task_size は
        S に限らない（M/L の bugfix は実運用パス）。else 分岐（S 以外）の
        `plan=n/a` 受理が削除されると正当な bugfix-M 編集が誤 deny される
        （false-deny 回帰）。review 1次 finder（テスト強度）の変異生存分析で
        このセルの無テストが検出されたため追加（iter65）。"""
        txt = STATUS_TMPL.format(mode="Dev", phase="implement", task_type="bugfix",
                                 task_size="M", brainstorm="n/a", plan="n/a")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_allowed(out),
                        f"bugfix M+plan n/a must allow ({{}}), got: {out!r}")

    def test_g_size_s_missing_brainstorm_key_plan_approved_denies(self):
        """(g) S・gate_approvals に brainstorm キーなし・plan=approved → deny。
        fail-closed の明示ピン: S は brainstorm を見るので、キー欠落は空値
        （!=approved/n/a）＝deny。plan approved に流れて allow してはならない。"""
        txt = STATUS_TMPL_NO_BRAINSTORM.format(mode="Dev", phase="implement",
                                               task_type="feature", task_size="S",
                                               plan="approved")
        with _scratch_root(txt) as name:
            root = Path(name)
            out = _hook(root, _src(root))
        self.assertTrue(_denied(out),
                        f"S + missing brainstorm key must deny (fail-closed), got: {out!r}")


class TestSizeGateDriftGuard(unittest.TestCase):
    """check-gate.sh の size→gate ハードコードが python SoT から drift したら赤く落ちる guard。

    背景: b796f95 で hooks/check-gate.sh は size-aware 化され、size→ゲートの対応を
    pure-bash でハードコードした（task_size=S → brainstorm gate を検査／それ以外
    〔M/L/未設定/不正値〕 → plan gate を検査）。この bash 側前提は python SoT
    ――scripts/check_status.py の SIZE_ALLOWED_PHASES / PHASE_REQUIRES_GATES――の
    「複製」であり、将来 size 追加や集合変更で bash が陳腐化すると gate が静かに
    緩む/壊れる。本 guard は SoT を in-process import して bash 前提を機械照合し、
    drift した瞬間に赤く落ちて保守者を hooks/check-gate.sh の size-aware 分岐へ誘導する。

    参照:
      - hooks/check-gate.sh: task_size=S 分岐（brainstorm gate 検査）と else 分岐
        （plan gate 検査）が本 guard の照合対象。
      - iter53 の REGEX↔WARN parity ドリフトガードと同パターン
        （tests/test_destructive_warning_language.py）: SoT を単一化できない複製に
        機械的 parity テストで歯を付ける手法。
    """

    def setUp(self):
        self.mod = _load_check_status()

    def test_only_S_skips_plan(self):
        """plan フェーズを持たない（＝plan gate を skip する）size は S のみ。

        M/L に plan が復活したり別 size が plan を落としたら、check-gate.sh の
        「S だけ brainstorm gate・他は plan gate」ハードコードが陳腐化する。
        """
        sap = self.mod.SIZE_ALLOWED_PHASES
        skip_plan = {s for s, phases in sap.items() if "plan" not in phases}
        self.assertEqual(
            skip_plan, {"S"},
            "check-gate.sh の size→gate ハードコードとの同期が壊れた: plan を skip "
            f"する size が {{'S'}} でなく {skip_plan} になった。"
            "hooks/check-gate.sh の size-aware 分岐（S→brainstorm gate／他→plan gate）"
            "を更新せよ。")

    def test_S_implement_prior_gate_is_brainstorm_only(self):
        """S の implement 直前ゲート列は [brainstorm]（check-gate.sh の S 分岐と一致）。

        PHASE_REQUIRES_GATES['implement'] を S の許可フェーズ集合で絞ると
        brainstorm だけが残る＝bash の「S は brainstorm gate を検査」に対応。
        """
        prior = [g for g in self.mod.PHASE_REQUIRES_GATES["implement"]
                 if g in self.mod.SIZE_ALLOWED_PHASES["S"]]
        self.assertEqual(
            prior, ["brainstorm"],
            "check-gate.sh の size→gate ハードコードとの同期が壊れた: S の implement "
            f"直前ゲート列が ['brainstorm'] でなく {prior} になった。"
            "hooks/check-gate.sh の size-aware 分岐（S→brainstorm gate）を更新せよ。")

    def test_M_and_L_implement_prior_gate_is_brainstorm_then_plan(self):
        """M・L の implement 直前ゲート列は [brainstorm, plan]（check-gate.sh の else 分岐と一致）。

        両 size とも brainstorm/plan を許可フェーズに持つので絞り込みで両方残る＝
        bash の「S 以外は plan gate を検査」に対応。
        """
        for size in ("M", "L"):
            prior = [g for g in self.mod.PHASE_REQUIRES_GATES["implement"]
                     if g in self.mod.SIZE_ALLOWED_PHASES[size]]
            self.assertEqual(
                prior, ["brainstorm", "plan"],
                "check-gate.sh の size→gate ハードコードとの同期が壊れた: "
                f"size={size} の implement 直前ゲート列が ['brainstorm', 'plan'] "
                f"でなく {prior} になった。"
                "hooks/check-gate.sh の size-aware 分岐（他→plan gate）を更新せよ。")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""K-1 (v1.6.2): test-marker forge を 3 軸独立判定で塞ぐ。

第6回 Phase A REDTEAM-01 の PoC:
  echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__
は v1.6.1 の strong marker 単独判定では `marker_verified=true` に倒れる。

本テストは strong marker 検出後に 3 軸で zero-run シグナルを検査することを契約：

  軸 1: 出力 zero-run regex（collected 0 items, Ran 0 tests など）
  軸 2: pytest exitCode 5（no tests collected）
  軸 3: pytest プロローグ欠落（platform / rootdir / collected が出ない）

いずれかが zero-run を示せば marker_verified=false。
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "evidence.sh"


def _check(payload: dict) -> str:
    """`_check_test_marker` を直接叩いて 'true' / 'false' を取る。"""
    script = (
        f'source "{LIB}"; '
        f'_check_test_marker "$(cat)"'
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30,
    )
    return proc.stdout.strip()


class TestZeroRunAxis1Output(unittest.TestCase):
    """軸 1: 出力に zero-run シグナルがあれば strong marker でも false"""

    def test_pytest_collected_0_items_is_not_verified(self):
        """REDTEAM-01 基本 PoC: strong marker + `collected 0 items` → false"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__'
            },
            "tool_response": {
                "output": "===== 3 passed in 0.42s =====\ncollected 0 items\n",
                "exitCode": 5,
            },
        }
        self.assertEqual(_check(payload), "false")

    def test_unittest_ran_0_tests_is_not_verified(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest"},
            "tool_response": {
                "output": "Ran 0 tests in 0.001s\nOK\n",
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "false")

    def test_cargo_test_zero_passed_is_not_verified(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "cargo test"},
            "tool_response": {
                "output": (
                    "running 0 tests\n"
                    "test result: ok. 0 passed; 0 failed; 0 ignored\n"
                ),
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "false")

    def test_pytest_no_tests_ran_is_not_verified(self):
        """`pytest -k __NEVER__` の終端行: `no tests ran in 0.42s`"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest -k __NEVER__"},
            "tool_response": {
                "output": "===== 0 passed in 0.42s =====\nno tests ran in 0.42s\n",
                "exitCode": 5,
            },
        }
        self.assertEqual(_check(payload), "false")


class TestZeroRunAxis2ExitCode(unittest.TestCase):
    """軸 2: 攻撃側がフィルタで zero-run 出力を削除しても pytest exit 5 が残る"""

    def test_pytest_exit_5_implies_not_verified_even_if_output_filtered(self):
        """grill 派生 G-1/G-2: `2>/dev/null` や `| grep -v` で
        zero-run の出力シグナルを削除しても、exit 5 が残れば false"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__ 2>/dev/null'
            },
            "tool_response": {
                "output": "===== 3 passed in 0.42s =====\n",  # フィルタ後
                "exitCode": 5,
            },
        }
        self.assertEqual(_check(payload), "false")

    def test_pytest_exit_nonzero_with_strong_marker_is_still_verified(self):
        """回帰: 失敗時 (exit=1) でも strong marker + プロローグありなら verified
        （失敗は失敗で別経路で検出される）"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest"},
            "tool_response": {
                "output": (
                    "platform darwin -- Python 3.11.5, pytest-7.4.3\n"
                    "rootdir: /tmp/proj\n"
                    "collected 3 items\n\n"
                    "tests/test_x.py F..\n\n"
                    "===== 1 failed, 2 passed in 0.1s =====\n"
                ),
                "exitCode": 1,
            },
        }
        self.assertEqual(_check(payload), "true")


class TestZeroRunAxis3Prologue(unittest.TestCase):
    """軸 3: pytest 系コマンドで strong marker が出ているがプロローグが
    完全に欠落していれば echo 由来疑いで false（pytest にのみ適用）"""

    def test_pytest_strong_marker_without_prologue_is_not_verified(self):
        """G-3 想定: `echo "===== 3 passed ====="` のみで pytest を一切
        走らせない場合、プロローグ（platform / rootdir / collected）が
        出ないので false"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__'
            },
            "tool_response": {
                "output": "===== 3 passed in 0.42s =====\n",
                "exitCode": 0,  # echo の exit (pytest が後段で失敗しても shell の最終 exit に依存)
            },
        }
        self.assertEqual(_check(payload), "false")

    def test_non_pytest_runner_without_prologue_check(self):
        """軸 3 は pytest にのみ適用。jest 等は不問
        （jest プロローグは安定せず誤検出リスクが高い）"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "npm run test"},
            "tool_response": {
                "output": "Tests:       5 passed, 5 total\n",
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "true")


class TestRegressionStillVerifies(unittest.TestCase):
    """通常の合法な test run が引き続き verified=true になる回帰確認"""

    def test_normal_pytest_three_passed_still_verified(self):
        """プロローグあり、exit 0、出力に zero-run なし"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest"},
            "tool_response": {
                "output": (
                    "platform darwin -- Python 3.11.5, pytest-7.4.3\n"
                    "rootdir: /home/user/proj\n"
                    "collected 3 items\n\n"
                    "tests/test_x.py ...\n\n"
                    "===== 3 passed in 0.42s =====\n"
                ),
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "true")

    def test_large_verbose_pytest_output_keeps_prologue_via_head(self):
        """grill-code Critical 2: 8KB 超の verbose 出力でも、head 抽出で
        プロローグ（platform / rootdir / collected）が保持されるため
        marker_verified=true に倒れる。

        v1.6.2 初版は output[-4096:] で tail のみ抽出していたため、200 件規模
        の `pytest -v` ではプロローグが完全に欠落し、軸 3（プロローグ欠落
        → false）で実テスト走行を誤って 🟡 化していた。head+tail に修正。"""
        prologue = (
            "platform darwin -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0\n"
            "rootdir: /tmp/proj\n"
            "plugins: anyio-4.0.0\n"
            "collected 200 items\n\n"
        )
        # 200 行 × 約 40 文字 ≈ 8 KB の進捗行
        middle = "".join(
            f"tests/test_module_{i:03d}.py::test_function_{i:03d} PASSED [ {i // 2:2d}%]\n"
            for i in range(200)
        )
        summary = "\n===== 200 passed in 12.34s =====\n"
        full_output = prologue + middle + summary
        # 物理的に > 4KB であることを assert（テストの前提）
        assert len(full_output) > 8000, f"test fixture too small: {len(full_output)}"
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest -v"},
            "tool_response": {
                "output": full_output,
                "exitCode": 0,
            },
        }
        self.assertEqual(
            _check(payload), "true",
            "verbose pytest output (with prologue at head) must verify "
            "even when head+tail extraction is needed to keep prologue."
        )

    def test_normal_unittest_passed_still_verified(self):
        """unittest プロローグは pytest と異なるが、軸 3 は pytest のみ適用
        なので unittest は strong/weak のみで判定。WEAK pair: Ran N + OK"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest"},
            "tool_response": {
                "output": "test_x (m.T) ... ok\nRan 3 tests in 0.1s\n\nOK\n",
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "true")

    def test_normal_unittest_passed_still_verified(self):
        """unittest プロローグは pytest と異なるが、軸 3 は pytest のみ適用
        なので unittest は strong/weak のみで判定。WEAK pair: Ran N + OK"""
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -m unittest"},
            "tool_response": {
                "output": "test_x (m.T) ... ok\nRan 3 tests in 0.1s\n\nOK\n",
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "true")

    def test_normal_cargo_test_still_verified(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "cargo test"},
            "tool_response": {
                "output": (
                    "running 3 tests\ntest tests::a ... ok\n"
                    "test tests::b ... ok\ntest tests::c ... ok\n"
                    "test result: ok. 3 passed; 0 failed; 0 ignored\n"
                ),
                "exitCode": 0,
            },
        }
        self.assertEqual(_check(payload), "true")


if __name__ == "__main__":
    unittest.main()

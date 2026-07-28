"""iter78 Task1 RED — pytest execution attestation の差分 pin バッテリ。

このバッテリは iter78 の新契約（これから作られる仕様）に対して書かれた
差分 pin である。旧実装（attest-test-run.py 不在・judge の pytest family
green 制限なし・record の pytest redirect なし）では大半が RED になり、
Task 2-5 の実装で緑化する。**このファイル 1 つのみが Task 1 の成果物**で、
プロダクションコードは一切書かない。

4 グループ:
  A — attestor 検証拒否（実行前 rc2・記録なし）: `scripts/attest-test-run.py`
      を subprocess で叩き rc2 と stderr、evidence-log 非生成を検証。
  B — attest e2e: tmp git repo に極小 pytest suite を置き、実 attestor で
      実走して rc/エントリを検証。出力非依存・positive proof の本命 pin。
  C — judge 契約: `_ev_line` 相当ヘルパーで evidence-log を合成し、
      pytest family × observed/manual ok が decide しなくなり、attested が
      decide することを pin。**現行実装では pytest ok が green＝RED**。
  D — record 誘導: 整形式 pytest family が実行前に rc2 で attest へ誘導
      されること。**現行実装では実行されて rc0＝RED**。

契約要点（design/plan 正本より）:
  - attestor: rc0=green 記録（stdout `attested: green`）／rc1=red 記録
    （`attested: red`）／rc2=不成立・拒否（記録なし・stderr に理由）。
    pytest を shell なし argv spawn（`-p aegis_attest_plugin`）で起動し、
    プラグインの構造化イベントと実 exit code を突合。子出力は非パース。
  - verdict: green ⇔ exit==0 ∧ executed>=1 ∧ failed==errors==
    collection_errors==0。executed = call-phase の passed+failed+xfailed+
    xpassed（skip 除外）。exit!=0 → red 記録 rc1（pytest exit 5 も red）。
    exit==0 ∧ executed==0（all-skip/collect-only）→ rc2 記録なし。
    sessionfinish 欠落・exitstatus≠実 exit・イベント JSON 破損 → rc2 記録なし。
  - judge: src allowlist が {"manual","observed","attested"} に拡張。
    pytest family × src∈{manual,observed} × ok は TRANSPARENT skip。
    status fail は decidable red のまま。src=attested は fp 一致で decidable。
  - record: 整形式 pytest family は malformation 検査の後・実行の前に rc2
    で拒否し attest-test-run.py へ誘導（ログ非書込・非実行）。非 pytest は不変。
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = ROOT_DIR / "scripts" / "build-judge-card.py"
RECORDER = ROOT_DIR / "scripts" / "record-test-result.py"
ATTESTOR = ROOT_DIR / "scripts" / "attest-test-run.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# judge は Task 4 で契約が変わるが、既存 public 関数（current_fingerprint など）は
# Task 1 時点でも読める。record は Task 5 で redirect が入る。両方 importlib load。
judge = _load("judge_attest", SCRIPT)
# record モジュールは Task 5 未実装でも load 可能（main を呼ぶのはグループ D のみ）。
try:
    record = _load("record_attest", RECORDER)
except Exception:  # pragma: no cover - 念のため（現行でも load できるはず）
    record = None


def _copy_lib(root: Path) -> None:
    """judge/record/attestor は hooks/lib/{fingerprint,patterns,marker}.sh に
    委譲する。tmp root にライブラリ一式をコピー（test_judge_card.py と同契約）。"""
    shutil.copytree(ROOT_DIR / "hooks" / "lib", root / "hooks" / "lib")


def _git_repo(root: Path) -> None:
    """tmp git repo を初期化（fingerprint が要る・test_judge_card.py 流儀）。"""
    sp.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
    sp.run(["git", "-C", str(root), "config", "user.email", "t@t"],
           check=True, capture_output=True)
    sp.run(["git", "-C", str(root), "config", "user.name", "t"],
           check=True, capture_output=True)


def _commit(root: Path, msg="i") -> None:
    sp.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    sp.run(["git", "-C", str(root), "commit", "-qm", msg],
           check=True, capture_output=True)


def _ev_line(cmd: str, status: str, fp: str, *, src: str = "observed",
             marker_verified: bool = True, counts: dict = None,
             exit_code: int = None) -> str:
    """合成 evidence エントリを 1 行（test_judge_card.py._ev_line の拡張）。

    observed 既定は marker_verified=True（実走を模す）。attested を組み立てる
    時は src="attested"＋counts/exit を渡す（手書きの attested エントリ＝実 writer
    が付ける counts/exit を模す）。判定に不要なら counts/exit は省略可。
    """
    row = {"v": 1, "ts": "2026-07-28T00:00:00Z", "src": src,
           "cmd": cmd, "status": status, "payload_sha": "0" * 64, "fp": fp}
    if src == "observed":
        row["marker_verified"] = marker_verified
    if counts is not None:
        row["counts"] = counts
    if exit_code is not None:
        row["exit"] = exit_code
    return json.dumps(row) + "\n"


# ---------------------------------------------------------------------------
# グループ A — attestor 検証拒否（実行前 rc2・記録なし）
# ---------------------------------------------------------------------------
class _AttestorFixture(unittest.TestCase):
    """tmp git repo + hooks/lib コピー。attestor は本体 repo の scripts/ を
    直接叩き、--root に tmp repo を渡す（そこから patterns.sh/fingerprint を読む）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _git_repo(self.root)
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        _copy_lib(self.root)
        _commit(self.root)
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _attest(self, cmd, *, timeout=120):
        """本体 repo の attest-test-run.py を subprocess 起動。(rc, stdout, stderr)。"""
        r = sp.run(["python3", str(ATTESTOR), "--root", str(self.root), cmd],
                   capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr


class TestAttestorRejection(_AttestorFixture):
    def test_reject_non_pytest_cmd(self):
        # A1: 非 pytest コマンドは pytest family 外 → rc2・記録なし・record 誘導。
        rc, out, err = self._attest("npm test")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists(),
                         "拒否されたコマンドは evidence-log を書いてはならない")
        self.assertIn("record-test-result", err,
                      f"非 pytest は record へ誘導すべき: {err!r}")

    def test_reject_shell_operator(self):
        # A2: シェル演算子連結は exit 洗浄の温床 → rc2（記録なし）。
        rc, out, err = self._attest("python3 -m pytest; true")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists())

    def test_reject_env_assign_prefix(self):
        # A3: env 代入 prefix は shell 専用構文（argv[0] に '='）→ rc2。
        rc, out, err = self._attest("X=1 pytest")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists())

    def test_reject_plugin_suppression(self):
        # A4: attestation プラグインの打ち消し（-p no:aegis_attest_plugin）は
        # positive proof を無効化するので拒否 → rc2（記録なし）。
        rc, out, err = self._attest("pytest -p no:aegis_attest_plugin")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists())

    def test_reject_unparsable_quote(self):
        # A5: クォート不整合は shlex.split 不能 → rc2（記録なし）。
        rc, out, err = self._attest('pytest "x')
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists())


# ---------------------------------------------------------------------------
# グループ B — attest e2e（tmp repo に極小 suite を作り実 attestor で実走）
# ---------------------------------------------------------------------------
class TestAttestE2E(unittest.TestCase):
    """tmp git repo（init+user 設定+初回 commit）に hooks/lib 一式コピー。
    極小 pytest ファイルは tmp repo 内に置き、コマンドは相対パスで書く
    （attestor の cwd は --root=tmp repo）。attestor は本体 repo の scripts/ を
    直接叩き、プラグイン（scripts/aegis_attest_plugin.py）も本体 repo 側にある。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _git_repo(self.root)
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        _copy_lib(self.root)
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, body):
        (self.root / name).write_text(body, encoding="utf-8")

    def _attest(self, cmd, *, timeout=180):
        # suite ファイル群を commit してから attest（fingerprint を安定させる）。
        _commit(self.root)
        r = sp.run(["python3", str(ATTESTOR), "--root", str(self.root), cmd],
                   capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr

    def _last_row(self):
        return json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])

    def test_green_recorded_on_passing_suite(self):
        # B1: 2 passed の suite → rc0・stdout `attested: green`・
        # src=attested/status ok/counts.executed==2/exit==0/fp 64hex。
        self._write("t_pass.py",
                    "def test_a():\n    assert True\n"
                    "def test_b():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_pass.py")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("attested: green", out)
        row = self._last_row()
        self.assertEqual(row["src"], "attested")
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["counts"]["executed"], 2, row)
        self.assertEqual(row["exit"], 0, row)
        self.assertRegex(row["fp"], r"^[0-9a-f]{64}$")

    def test_red_recorded_on_failing_suite(self):
        # B2: 1 failed → rc1・status fail（fail-visible）。
        self._write("t_fail.py", "def test_a():\n    assert False\n")
        rc, out, err = self._attest("python3 -m pytest t_fail.py")
        self.assertEqual(rc, 1, out + err)
        self.assertIn("attested: red", out)
        row = self._last_row()
        self.assertEqual(row["src"], "attested")
        self.assertEqual(row["status"], "fail")

    def test_zero_run_rejected_all_skip(self):
        # B3: 全 @pytest.mark.skip（実行 0 件）→ exit 0 でも executed==0 →
        # rc2・記録なし。all-skip forgery を positive proof が塞ぐ。
        self._write("t_skip.py",
                    "import pytest\n"
                    "@pytest.mark.skip\ndef test_a():\n    assert True\n"
                    "@pytest.mark.skip\ndef test_b():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_skip.py")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists(),
                         "実行 0 件は green 不成立＝記録してはならない")

    def test_no_tests_collected_recorded_red(self):
        # B4: test を含まないファイルを指定 → pytest exit 5（収集 0）→ rc1・
        # status fail 記録。exit≠0 は red の実信号（record の exit-5 先例と整合）。
        self._write("nothing.py", "x = 1\n")
        rc, out, err = self._attest("python3 -m pytest nothing.py")
        self.assertEqual(rc, 1, out + err)
        row = self._last_row()
        self.assertEqual(row["src"], "attested")
        self.assertEqual(row["status"], "fail")

    def test_collect_only_rejected(self):
        # B5: --collect-only 付き passing suite → exit 0・executed 0 → rc2・
        # 記録なし。NO_RUN denylist なしで positive proof が塞ぐことの実証。
        self._write("t_pass.py", "def test_a():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest --collect-only t_pass.py")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists())

    def test_all_xfail_green(self):
        # B6: 全テストが @pytest.mark.xfail で実際に fail する suite →
        # pytest exit 0・executed==N（xfailed は実行済み）→ rc0 green。
        # SF-015（xfail の false negative）を attested 経路で解消する pin。
        self._write("t_xfail.py",
                    "import pytest\n"
                    "@pytest.mark.xfail\ndef test_a():\n    assert False\n"
                    "@pytest.mark.xfail\ndef test_b():\n    assert False\n")
        rc, out, err = self._attest("python3 -m pytest t_xfail.py")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("attested: green", out)
        row = self._last_row()
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["counts"]["executed"], 2, row)

    def test_collection_error_red(self):
        # B7: import エラーを起こす test ファイル → rc1・status fail・
        # counts.collection_errors>=1。
        self._write("t_boom.py",
                    "import nonexistent_module_xyz\n"
                    "def test_a():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_boom.py")
        self.assertEqual(rc, 1, out + err)
        row = self._last_row()
        self.assertEqual(row["status"], "fail")
        self.assertGreaterEqual(row["counts"]["collection_errors"], 1, row)

    def test_fake_output_ignored(self):
        # B8: テスト内で偽サマリ行を print しつつ assert False → rc1・status
        # fail。出力を一切パースせず構造化イベントで判定する本命 pin。
        self._write("t_fake.py",
                    "def test_a():\n"
                    "    print('===== 999 passed in 0.01s =====')\n"
                    "    assert False\n")
        rc, out, err = self._attest("python3 -m pytest t_fake.py")
        self.assertEqual(rc, 1, out + err)
        row = self._last_row()
        self.assertEqual(row["status"], "fail")

    def test_event_file_sabotage_fails_closed(self):
        # B9: conftest の sessionfinish hook で event ファイルを truncate →
        # passing suite でも green 不能（イベント欠落 or executed 0 の
        # どちらの評価順でも fail-closed）→ rc2・記録なし。in-process 妨害が
        # 安全側に倒れることの実証。
        self._write("conftest.py",
                    "import os\n"
                    "def pytest_sessionfinish(session):\n"
                    "    p = os.environ.get('AEGIS_ATTEST_EVENT_PATH')\n"
                    "    if p:\n"
                    "        open(p, 'w').close()\n")
        self._write("t_pass.py", "def test_a():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_pass.py")
        self.assertEqual(rc, 2, out + err)
        self.assertFalse(self.log.exists(),
                         "イベント妨害で green を証明できない＝記録してはならない")

    def test_event_file_invalid_bytes_fails_closed_rc2(self):
        # B11（grill-code 🟡 fix-forward）: event ファイルへの不正 UTF-8 バイト
        # 注入（truncate と別綴りの in-process 妨害）。素の UnicodeDecodeError
        # traceback（rc1＝「red 記録済み」の誤信号）ではなく、破損＝評価不能
        # として rc2・記録なし・診断メッセージに倒れること。
        self._write("conftest.py",
                    "import os\n"
                    "def pytest_sessionfinish(session):\n"
                    "    p = os.environ.get('AEGIS_ATTEST_EVENT_PATH')\n"
                    "    if p:\n"
                    "        open(p, 'ab').write(b'\\xff\\xfe broken\\n')\n")
        self._write("t_pass.py", "def test_a():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_pass.py")
        self.assertEqual(rc, 2, out + err)
        self.assertNotIn("Traceback", err)
        self.assertIn("attest 不成立", err)
        self.assertFalse(self.log.exists())

    def test_forged_sessionfinish_mismatch_rejected(self):
        # B12（iter78 review テスト強度 M3 gap fix-forward）: exitstatus と実
        # returncode の突合（sessionfinish != rc → rc2）に検知者が無かった。
        # conftest の pytest_unconfigure（プラグインの sessionfinish より後に
        # 発火＝last-wins で上書き）が偽 exitstatus を注入 → 実 rc=0 と不一致
        # → rc2・記録なし。この突合を消すと green 化する＝差分 pin。
        self._write("conftest.py",
                    "import os\n"
                    "def pytest_unconfigure(config):\n"
                    "    p = os.environ.get('AEGIS_ATTEST_EVENT_PATH')\n"
                    "    if p:\n"
                    "        open(p, 'a').write("
                    "'{\"e\":\"sessionfinish\",\"exitstatus\":7}\\n')\n")
        self._write("t_pass.py", "def test_a():\n    assert True\n")
        rc, out, err = self._attest("python3 -m pytest t_pass.py")
        self.assertEqual(rc, 2, out + err)
        self.assertIn("突合不一致", err)
        self.assertFalse(self.log.exists())

    def test_forged_pass_events_cannot_green_a_real_red(self):
        # B13（load-bearing 不変・review 敵対 5a/5c の in-session 裁定）: 被
        # テスト側 conftest が偽 call passed イベントを注入しても、実失敗
        # suite は real exit!=0 が突合で勝ち **red 記録**（green 化不能）。
        # attestation の中核保証＝「本物の red は偽イベントでも green にできない」。
        self._write("conftest.py",
                    "import os, json\n"
                    "def pytest_sessionstart(session):\n"
                    "    p = os.environ.get('AEGIS_ATTEST_EVENT_PATH')\n"
                    "    if p:\n"
                    "        open(p, 'a').write(json.dumps("
                    "{'e':'test','nodeid':'f::x','when':'call',"
                    "'outcome':'passed','wasxfail':False}) + '\\n')\n")
        self._write("t_fail.py", "def test_a():\n    assert False\n")
        rc, out, err = self._attest("python3 -m pytest t_fail.py")
        self.assertEqual(rc, 1, out + err)
        self.assertEqual(self._last_row()["status"], "fail")


# ---------------------------------------------------------------------------
# グループ C — judge 契約（合成 evidence-log で新契約を pin）
# ---------------------------------------------------------------------------
class TestJudgeContract(unittest.TestCase):
    """tmp git repo + hooks/lib コピー + judge.current_fingerprint。
    合成 evidence-log を書いて read_test_result の verdict を pin する。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _git_repo(self.root)
        sp.run(["git", "-C", str(self.root), "commit", "-q", "--allow-empty",
                "-m", "init"], check=True, capture_output=True)
        _copy_lib(self.root)
        (self.root / ".claude").mkdir()
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _fp(self):
        return judge.current_fingerprint(self.root)

    def test_observed_pytest_ok_no_longer_decides(self):
        # C1: observed/ok/marker_verified:true/fp 一致・cmd が pytest のみ →
        # unverified。pytest family green は attestation でしか決められない
        # （出力/exit ベース proof は attestation が置き換える層）。
        # **現行実装では green を返す＝この pin が Task 1 時点の主役 RED。**
        fp = self._fp()
        self.log.write_text(_ev_line("python3 -m pytest -q", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_manual_pytest_ok_no_longer_decides(self):
        # C2: manual/ok/fp 一致・cmd が pytest のみ → unverified。manual 経路も
        # 同時に閉じる（現行では manual pytest ok は green＝RED）。
        fp = self._fp()
        self.log.write_text(_ev_line("pytest tests/", "ok", fp, src="manual"))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_observed_pytest_ok_transparent_falls_through_to_attested(self):
        # C3: 新しい observed pytest ok の「下」に attested ok（手書き・counts
        # 付き・fp 一致）→ observed は transparent skip され attested が decide
        # → green。src は attested が deciding。
        fp = self._fp()
        counts = {"executed": 2, "passed": 2, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested",
                     counts=counts, exit_code=0)
            + _ev_line("python3 -m pytest -q", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_attested_decides_green(self):
        # C4: attested/ok/fp 一致のみ → green。
        fp = self._fp()
        counts = {"executed": 1, "passed": 1, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_attested_decides_red(self):
        # C5: attested/fail/fp 一致のみ → red。
        fp = self._fp()
        counts = {"executed": 1, "passed": 0, "failed": 1, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "fail", fp, src="attested",
                     counts=counts, exit_code=1))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_attested_stale_fp_unverified(self):
        # C6: attested/ok/fp 不一致 → unverified（コード変更後の古い記録で
        # 承認できない）。
        counts = {"executed": 1, "passed": 1, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", "f" * 64, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_observed_pytest_fail_still_red(self):
        # C7: observed/fail/marker_verified:true/pytest cmd → red（fail-visible
        # 維持。green 制限は ok にのみ効き、fail の実信号は殺さない）。
        fp = self._fp()
        self.log.write_text(_ev_line("python3 -m pytest -q", "fail", fp))
        self.assertEqual(judge.read_test_result(self.root), "red")

    def test_non_pytest_observed_ok_still_decides(self):
        # C8: observed/ok/marker_verified:true・cmd "npm test"（非 pytest）→
        # green 不変。非 pytest ランナーは marker 経路のまま挙動不変。
        fp = self._fp()
        self.log.write_text(_ev_line("npm test", "ok", fp))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_manual_nonpytest_still_decides(self):
        # C9: manual/ok・cmd "python3 -m unittest"（非 pytest）→ green 不変。
        fp = self._fp()
        self.log.write_text(
            _ev_line("python3 -m unittest", "ok", fp, src="manual"))
        self.assertEqual(judge.read_test_result(self.root), "green")

    def test_attested_washed_cmd_transparent(self):
        # C10: 手書き attested/ok・cmd に `;`（シェル演算子）→ transparent
        # ＝単独なら unverified。attested の実 writer は shell 演算子 cmd を
        # 構造上生成しない（argv spawn）ので該当は手書き偽造のみ。washed-green
        # 透明化を attested にも広げる防御多層 pin。
        fp = self._fp()
        counts = {"executed": 1, "passed": 1, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest; true", "ok", fp, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_is_pytest_family_cmd_none_fail_closed(self):
        # C11: patterns.sh の無い root → is_pytest_family_cmd が None（fail-
        # closed）。**現行実装では is_pytest_family_cmd が存在しない＝
        # AttributeError で RED。**
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(judge.is_pytest_family_cmd(Path(d), "pytest"))

    def test_handwritten_attested_no_counts_fails_closed(self):
        # C12（iter78 review adversarial 2nd で契約強化）: counts の無い手書き
        # attested/ok/fp 一致 → **unverified**（fail-closed）。旧契約は green
        # だったが、judge が read-time に counts.executed>=1 を要求するよう
        # 強化＝「counts 皆無の attested が fp 一致だけで green」の非対称を除去。
        fp = self._fp()
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested"))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_handwritten_attested_zero_executed_fails_closed(self):
        # C12b: counts.executed==0 の手書き attested/ok → unverified。
        # executed>=1 の positive proof を read-time でも要求する mutation killer
        # （この check を消すと green に戻る＝差分 pin）。
        fp = self._fp()
        counts = {"executed": 0, "passed": 0, "failed": 0, "skipped": 3,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_handwritten_attested_bool_executed_fails_closed(self):
        # C12d（iter78 盲検2次 review 摘発・post-close hardening）: counts.executed
        # が JSON boolean（true）だと Python の bool は int の subclass で
        # isinstance(int) を通過し True>=1 で green 化していた型混同ホール。実
        # attestor は int しか吐かないので bool は定義上 hand-forged＝positive
        # proof gate の宣言意図（実整数 executed>=1）を silently 破らせない。
        fp = self._fp()
        counts = {"executed": True, "passed": True, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "unverified")

    def test_handwritten_attested_forge_residual_documented(self):
        # C12c documenting pin: read-time counts 検証は trust boundary では
        # ない。counts.executed>=1 を「捏造」した手書き attested/ok/fp 一致は
        # 依然 green＝同一ユーザー権限内の手書き偽造天井（fp が唯一の moat・
        # manual 非 pytest と同クラス・SF ledger 記載）。この天井を閉じるには
        # 別ユーザー/コンテナの trust boundary が要る（roadmap §6 で対象外）。
        # 防御多層（drill=all-skip は marker false で BLOCKED / human preview /
        # fingerprint）で contain。反転契約が入ったら天井の意図的許容を再確認。
        fp = self._fp()
        counts = {"executed": 1, "passed": 1, "failed": 0, "skipped": 0,
                  "errors": 0, "xfailed": 0, "xpassed": 0, "collection_errors": 0}
        self.log.write_text(
            _ev_line("python3 -m pytest", "ok", fp, src="attested",
                     counts=counts, exit_code=0))
        self.assertEqual(judge.read_test_result(self.root), "green")


# ---------------------------------------------------------------------------
# グループ D — record 誘導（record.main() を importlib load して呼ぶ）
# ---------------------------------------------------------------------------
def _run_record(argv):
    """record.main(argv) を呼び stderr を捕捉。(rc, stderr_text)。"""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = record.main(argv)
    return rc, buf.getvalue()


class _RecordFixture(unittest.TestCase):
    """tmp git repo + hooks/lib コピー + 極小 pytest/unittest ファイル。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _git_repo(self.root)
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        # 実在する極小 pytest ファイル（record が「実行しない」ことを確認する対象）。
        (self.root / "t_pass.py").write_text(
            "def test_a():\n    assert True\n", encoding="utf-8")
        # 非 pytest（unittest）双子: 従来経路が不変であることの回帰 pin 用。
        # 実出力で weak pair marker（Ran N tests in ... / OK）が成立する。
        (self.root / "u_pass.py").write_text(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_a(self):\n        self.assertTrue(True)\n",
            encoding="utf-8")
        _copy_lib(self.root)
        _commit(self.root)
        self.log = self.root / ".claude" / "evidence-log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()


class TestRecordRedirect(_RecordFixture):
    def test_record_rejects_pytest_family(self):
        # D1: 整形式 pytest family（実在する極小ファイル指定）→ rc2・stderr に
        # "attest-test-run" を含む・evidence-log 非書込・**テストが実行されない**。
        # 実行されないことを、テスト内でマーカーを作る副作用ファイルで検証する。
        # **現行実装では実行されて marker 成立 rc0＝RED。**
        marker = self.root / "ran.marker"
        (self.root / "t_side.py").write_text(
            f"def test_a():\n"
            f"    open({str(marker)!r}, 'w').close()\n"
            f"    assert True\n", encoding="utf-8")
        _commit(self.root, "side")
        cmd = f"python3 -m pytest {self.root / 't_side.py'}"
        self.assertLess(len(cmd), 500)
        rc, err = _run_record(["--root", str(self.root), cmd])
        self.assertEqual(rc, 2, err)
        self.assertIn("attest-test-run", err,
                      f"pytest family は attest へ誘導すべき: {err!r}")
        self.assertFalse(self.log.exists(),
                         "誘導された pytest は evidence-log を書いてはならない")
        self.assertFalse(marker.exists(),
                         "誘導された pytest は実行されてはならない（副作用なし）")

    def test_record_nonpytest_unchanged(self):
        # D2: 非 pytest（python3 -m unittest u_pass）実走 green → rc0 受理のまま。
        # 従来経路が不変であることの回帰 pin（現行でも green＝GREEN）。
        cmd = f"python3 -m unittest u_pass"
        rc, err = _run_record(["--root", str(self.root), cmd])
        self.assertEqual(rc, 0, err)
        self.assertTrue(self.log.exists())
        row = json.loads(self.log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(row["src"], "manual")
        self.assertEqual(row["status"], "ok")


if __name__ == "__main__":
    unittest.main()

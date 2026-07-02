"""iter54 C-4: 日本語（非 ASCII）ファイル名が judge/drill から黙って消える穴の封鎖。

2026-07-02 グリル再現: git の core.quotepath 既定（on）では非 ASCII パスが
`"\\343..."` 形式で quote され、run-test-strength-drill.py の
_tracked_added_lines / _untracked_files が「実在しないファイル名」として
map に載せる → read が OSError → 呼び出し側の continue で **silent skip**。
結果: 日本語ファイル名の追加行が judge の secret/stub スキャンから消え
security ゲートが false-green（silent-green）。日本語ユーザー特有の Critical。

修正 = git 呼びに `-c core.quotepath=off`（fingerprint.sh:54 と同型）＋
quotepath=off 後も quote が残る名前（制御文字等）は DrillError で fail-closed
（continue の silent skip は禁止）。build-judge-card.py はパスを emit する
直接の git 呼びを持たない（drill モジュール経由）ため drill 側修正が伝播する。
"""
import importlib.util
import subprocess as sp
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


drill = _load("drill_qp", SCRIPTS / "run-test-strength-drill.py")
judge = _load("judge_qp", SCRIPTS / "build-judge-card.py")


def _git(root, *args):
    sp.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp):
    root = Path(tmp)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "base.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "base.py")
    _git(root, "commit", "-q", "-m", "init")
    return root


class TestJapaneseTrackedDiff(unittest.TestCase):
    def test_tracked_japanese_filename_lines_visible(self):
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            f = root / "テスト.py"
            f.write_text("a = 1\n", encoding="utf-8")
            _git(root, "add", "テスト.py")
            _git(root, "commit", "-q", "-m", "add jp file")
            f.write_text("a = 1\nsecret_line = 2\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertIn("テスト.py", added,
                          f"japanese tracked file must appear unquoted: {added}")
            self.assertIn(2, added["テスト.py"])

    def test_untracked_japanese_filename_visible(self):
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            (root / "新規.py").write_text("y = 1\ny = 2\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertIn("新規.py", added,
                          f"japanese untracked file must appear unquoted: {added}")
            self.assertEqual(added["新規.py"], {1, 2})


class TestJudgeScansJapaneseFiles(unittest.TestCase):
    def test_secret_in_japanese_file_is_caught(self):
        """C-4 の本丸: 日本語ファイル内のシークレットが scan_secrets に載る。"""
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            # シークレット literal はトークン連結で組み立てる: このテストファイル自身の
            # 追加行が judge の scan_secrets（tests/ は除外対象外）に載って security
            # ゲートが 🔴 になるのを避ける（scan_secrets は「変更行にシークレット様
            # パターン」を検出するため、one-liner だと自己ヒットする）。
            secret_line = "api" + "_key" + ' = "' + "sk-live-0123456789abcdef" + '"\n'
            (root / "設定.py").write_text(secret_line, encoding="utf-8")
            hits = judge.scan_secrets(root)
            self.assertTrue(any("設定.py" in h for h in hits),
                            f"secret in japanese file must be caught: {hits}")

    def test_stub_in_japanese_file_is_caught(self):
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            # マーカーはトークン連結で組み立てる: このテストファイル自身の追加行が
            # judge の stub スキャン（tests/ は除外対象外）に literal で載ると
            # ゲートが 🔴 になるため。
            marker = "# " + "TO" + "DO" + ": implement\n"
            (root / "作業.py").write_text(marker, encoding="utf-8")
            hits = judge.scan_stubs(root)
            self.assertTrue(any("作業.py" in h for h in hits),
                            f"stub in japanese file must be caught: {hits}")


class TestResidualQuotedPathFailsClosed(unittest.TestCase):
    def test_control_char_filename_raises_drill_error(self):
        """quotepath=off でも quote が残る名前（tab 等）は silent skip でなく
        DrillError（drill=BLOCKED / judge=🟡）に倒す。"""
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            try:
                (root / "bad\tname.py").write_text("z = 1\n", encoding="utf-8")
            except OSError:
                self.skipTest("FS forbids control chars in filenames")
            with self.assertRaises(drill.DrillError):
                drill.added_lines_by_file(root, "HEAD")


class TestAsciiNonRegression(unittest.TestCase):
    def test_ascii_paths_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            root = _repo(t)
            (root / "plain.py").write_text("p = 1\n", encoding="utf-8")
            added = drill.added_lines_by_file(root, "HEAD")
            self.assertIn("plain.py", added)
            self.assertEqual(added["plain.py"], {1})


if __name__ == "__main__":
    unittest.main()

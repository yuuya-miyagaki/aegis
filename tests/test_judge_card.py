import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build-judge-card.py"

def _load():
    spec = importlib.util.spec_from_file_location("judge", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

judge = _load()


class TestReadClaims(unittest.TestCase):
    def test_parses_fenced_claims_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text(
                "# review\n\n```claims\n"
                "tests_pass: true\nno_stubs: true\nverdict: approve\n```\n",
                encoding="utf-8")
            claims = judge.read_claims(p)
            self.assertEqual(claims["tests_pass"], True)
            self.assertEqual(claims["verdict"], "approve")

    def test_missing_block_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.md"
            p.write_text("# review\n\nno claims here\n", encoding="utf-8")
            self.assertIsNone(judge.read_claims(p))

    def test_missing_file_returns_none(self):
        self.assertIsNone(judge.read_claims(Path("/nonexistent/x.md")))


if __name__ == "__main__":
    unittest.main()

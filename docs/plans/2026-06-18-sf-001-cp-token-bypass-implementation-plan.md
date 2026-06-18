# SF-001 control-plane トークン分割バイパス 修正 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: aegis の `tdd` skill（`.claude/skills/tdd/SKILL.md`）に従い task ごとに RED→GREEN→commit。Steps は checkbox（`- [ ]`）で追跡。

**Goal:** control-plane フックがシェルのクォート除去/隣接連結/backslash/trailing-slash 無し bare-dir operand で再構成される CP 書込み先を取りこぼすバイパス（SF-001・Critical）を、既存判定を一切後退させずに塞ぐ。

**Architecture:** Augment。`cmd_mentions_control_plane` の末尾（cmdsub 分岐の後）に `cmd_token_mentions_cp` を1本足し、true なら `return 0`。2サブチェック: ①bare-dir（pure-bash 語境界正規表現＋echo/printf/git-commit 救済・python 非依存）②quote分割/backslash（python3 `shlex(posix,punctuation_chars)` で語分割→redirect-target/operand 分類→`_word_is_cp`）。`CONTROL_PLANE`/`CP_DIRS` は env で python に渡し単一ソース維持。

**Tech Stack:** bash 3.2（macOS 既定）, python3（shlex）, pytest（unittest 経由）, `make example`（mirror 同期）。

**参照設計:** `docs/specs/2026-06-18-sf-001-cp-token-bypass-design.md`

---

## File Structure

- Modify: `hooks/check-control-plane.sh` — `_word_is_cp` / `_cmd_is_rescued_message` / `cmd_token_mentions_cp` を追加し、`cmd_mentions_control_plane` 末尾に1行配線。
- Auto-sync: `examples/minimal-project/hooks/check-control-plane.sh` — `make example` で byte-identical 再生成（手編集しない）。
- Create: `tests/test_control_plane_token_split.py` — SF-001 全 repro（deny 化）＋回帰 allow を `_scratch_root`/`_hook` 流儀で。
- Modify（版 bump 1.11.0→1.12.0）: `scripts/check_framework_contract.py:24`, `templates/STATUS.template.md:3`, `examples/minimal-project/docs/STATUS.md:3`, `docs/STATUS.md:3`。

---

## Task 0: スパイク（実装前の挙動実測・破棄可）

Sub-check 2 は「shlex の分割」と「ERE 由来 `CONTROL_PLANE` の python `re.compile`」の2仮定に乗る。実装前に実測し、差異があれば設計へ反映する。

- [ ] **Step 1: shlex 分割を実測**

Run:
```bash
python3 - <<'PY'
import shlex
cases = [
  'cp safe.txt hooks""/lib/emit.sh',
  'cp safe.txt "ho""oks/lib/emit.sh"',
  "cp safe.txt 'hoo'ks/lib/emit.sh",
  'cp safe.txt hooks"/"lib/emit.sh',
  'cp safe.txt hooks\\/lib/emit.sh',
  'echo evil > "hoo""ks/lib/emit.sh"',
  'cp evil "STAT"US.md',
  'echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh',
]
for c in cases:
    lex = shlex.shlex(c, posix=True, punctuation_chars=True); lex.whitespace_split = True
    print(repr(c), "->", list(lex))
PY
```
Expected: 各ケースで再構成語に `hooks/lib/emit.sh` / `STATUS.md` が現れ、`>` と `|` が独立トークンになる。差異（例: `whitespace_split` と `punctuation_chars` 併用時の想定外分割）があれば記録し設計修正。

- [ ] **Step 2: `re.compile(CONTROL_PLANE)` の互換を実測**

Run（root の `CONTROL_PLANE` 構築式を bash から取り出して python に渡す）:
```bash
CP_DIRS='hooks|scripts|templates'
CONTROL_PLANE='STATUS\.md|CLAUDE\.md|\.claude/|\.claude[^A-Za-z0-9_/]'
CONTROL_PLANE="${CONTROL_PLANE}|(^|[^A-Za-z0-9_./-])(\\./)*(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|(\\.\\./)+(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|/\\./(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|[)\`'\"]/(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|\\\$[A-Za-z_{][A-Za-z0-9_}]*/(${CP_DIRS})/"
CONTROL_PLANE="${CONTROL_PLANE}|:[-=+](${CP_DIRS})}?/"
AEGIS_CP_RE="$CONTROL_PLANE" python3 - <<'PY'
import os, re
r = re.compile(os.environ["AEGIS_CP_RE"])
for w, exp in [("hooks/lib", True), ("STATUS.md", True), ("xhooks/lib", False),
               ("scripts/x", True), ("notes.txt", False)]:
    print(w, bool(r.search(w)), "expect", exp)
PY
```
Expected: `re.compile` が例外を出さず、判定が期待どおり（`xhooks/lib`=False）。差異があれば設計修正（最悪、python 側で境界を別途実装）。

- [ ] **Step 3: 結論を1行メモ**

スパイク結果（想定どおり/要修正点）を Task 2 着手前に確認。コードは破棄（実装は Task 2）。

---

## Task 1: 失敗するテストを書く（新ファイル）

**Files:**
- Create: `tests/test_control_plane_token_split.py`

ハーネスは `tests/test_control_plane_allowlist.py` と同一（`_scratch_root` が `task_type: feature` の STATUS＋hook＋lib symlink、`_hook` が JSON stdin 実走、`_allowed`=`{}`/`_denied`/`_asked`）。

- [ ] **Step 1: テスト作成（全 repro と回帰 allow）**

```python
#!/usr/bin/env python3
"""SF-001: control-plane フックの quote/escape/bare-dir トークン分割バイパス。
変更前(8f8eb2d 系)は task_type=feature でこれらが allow になっていた(Critical)。
Augment は既存 allow を後退させずこれらを deny 化する。"""
from __future__ import annotations
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _scratch_root() -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name)
    (p / "docs").mkdir()
    (p / "docs" / "STATUS.md").write_text(
        "---\nframework: aegis\nmode: Dev\nphase: implement\n"
        "task_type: feature\n---\n", encoding="utf-8")
    hooks_dir = p / "hooks"; hooks_dir.mkdir()
    shutil.copy2(ROOT / "hooks" / "check-control-plane.sh",
                 hooks_dir / "check-control-plane.sh")
    lib_dir = hooks_dir / "lib"; lib_dir.mkdir()
    for lib in ("extract-input.sh", "emit.sh", "safety.sh", "frontmatter.sh"):
        (lib_dir / lib).symlink_to(ROOT / "hooks" / "lib" / lib)
    return tmp

def _hook(root: Path, cmd: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(["bash", str(root / "hooks" / "check-control-plane.sh")],
                       input=payload, capture_output=True, text=True, cwd=str(root))
    return r.stdout

def _allowed(out): return out.strip() == "{}"
def _denied(out): return '"permissionDecision":"deny"' in out

class TestQuoteSplitBypass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root(); cls.root = Path(cls._tmp.name)
    @classmethod
    def tearDownClass(cls): cls._tmp.cleanup()

    def test_empty_quote_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'cp safe.txt hooks""/lib/emit.sh')))
    def test_adjacent_quote_concat_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'cp safe.txt "ho""oks/lib/emit.sh"')))
    def test_single_quote_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, "cp safe.txt 'hoo'ks/lib/emit.sh")))
    def test_slash_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'cp safe.txt hooks"/"lib/emit.sh')))
    def test_backslash_escape_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'cp safe.txt hooks\\/lib/emit.sh')))
    def test_redirect_split_target_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'echo evil > "hoo""ks/lib/emit.sh"')))
    def test_status_md_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'cp evil "STAT"US.md')))
    def test_xargs_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh')))
    def test_find_exec_split_denied(self):
        self.assertTrue(_denied(_hook(self.root, 'find . -name x -exec cp {} "hoo"ks/lib/emit.sh \\;')))

class TestBareDirBypass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root(); cls.root = Path(cls._tmp.name)
    @classmethod
    def tearDownClass(cls): cls._tmp.cleanup()

    def test_find_bare_dir_exec_rm_denied(self):
        self.assertTrue(_denied(_hook(self.root, "find hooks -type f -exec rm {} +")))
    def test_rm_rf_bare_dir_denied(self):
        self.assertTrue(_denied(_hook(self.root, "rm -rf hooks")))
    def test_cp_to_bare_dir_denied(self):
        self.assertTrue(_denied(_hook(self.root, "cp evil hooks")))
    def test_rm_rf_bare_scripts_denied(self):
        self.assertTrue(_denied(_hook(self.root, "rm -rf scripts")))
    def test_rm_rf_bare_templates_denied(self):
        self.assertTrue(_denied(_hook(self.root, "rm -rf templates")))

class TestNoRegressionAllows(unittest.TestCase):
    """既存 allow を後退させない（偽陽性ゼロの確認）。"""
    @classmethod
    def setUpClass(cls):
        cls._tmp = _scratch_root(); cls.root = Path(cls._tmp.name)
    @classmethod
    def tearDownClass(cls): cls._tmp.cleanup()

    def test_commit_message_status_allowed(self):
        self.assertTrue(_allowed(_hook(self.root, 'git commit -m "update STATUS.md handling"')))
    def test_echo_quoted_cp_redirect_noncp_allowed(self):
        self.assertTrue(_allowed(_hook(self.root, "echo 'see hooks/ for details' >> notes.txt")))
    def test_ls_bare_dir_allowed(self):
        self.assertTrue(_allowed(_hook(self.root, "ls hooks")))
    def test_find_bare_dir_read_allowed(self):
        self.assertTrue(_allowed(_hook(self.root, "find hooks -type f")))
    def test_subdir_named_hooks_allowed(self):
        # 上位 src/hooks は CP ではない（語境界で除外）。
        self.assertTrue(_allowed(_hook(self.root, "rm -rf src/hooks")))

class TestPython3Absent(unittest.TestCase):
    """degraded mode（python3 が壊れている/不在）: bare-dir は Sub-check 1(pure-bash)
    で deny、read は許可、フックはクラッシュしない。quote分割は既存挙動に fallback。"""
    @classmethod
    def setUpClass(cls):
        import os
        cls._tmp = _scratch_root(); cls.root = Path(cls._tmp.name)
        binr = cls.root / "nopybin"; binr.mkdir()
        shim = binr / "python3"; shim.write_text("#!/bin/sh\nexit 127\n"); shim.chmod(0o755)
        cls._env = dict(os.environ, PATH=f"{binr}:{os.environ.get('PATH','')}")
    @classmethod
    def tearDownClass(cls): cls._tmp.cleanup()

    def _hook_nopy(self, cmd: str) -> str:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        r = subprocess.run(["bash", str(self.root / "hooks" / "check-control-plane.sh")],
                           input=payload, capture_output=True, text=True,
                           cwd=str(self.root), env=self._env)
        return r.stdout

    def test_bare_dir_denied_without_python(self):
        self.assertTrue(_denied(self._hook_nopy("rm -rf hooks")))
    def test_read_allowed_without_python(self):
        self.assertTrue(_allowed(self._hook_nopy("ls hooks")))
    def test_no_crash_without_python(self):
        self.assertTrue(self._hook_nopy("rm -rf hooks").strip() != "")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED 実証**

Run: `python3 -m pytest tests/test_control_plane_token_split.py -v`
Expected: `TestQuoteSplitBypass` と `TestBareDirBypass` が **FAIL**（現状 allow＝バイパス）、`TestNoRegressionAllows` は **PASS**（既存挙動）。

---

## Task 2: 実装（`hooks/check-control-plane.sh` に inline）

**Files:**
- Modify: `hooks/check-control-plane.sh`（`cmd_mentions_control_plane` 関数定義の直後に新関数群、関数末尾に配線）

- [ ] **Step 1: ヘルパと本体を追加**

`cmd_mentions_control_plane()` の `}` の直後に以下を追加:

```bash
# --- SF-001 AUGMENT: token-aware control-plane WRITE-TARGET detection ---------
# 既存 (a)(b)(c) はリテラル `hooks/`|`scripts/`|`templates/`|`STATUS.md`|... に
# 一致するため、シェルが CP パスに再構成するが当該リテラルを含まない形を取りこぼす:
#   quote分割/隣接連結 (hooks""/lib, "ho""oks/lib", 'hoo'ks/), backslash (hooks\/lib),
#   trailing-slash 無し bare-dir operand (rm -rf hooks, cp x hooks, find hooks)。
# 下記は deny を ADD するのみ（既存決定を緩めない）。CP パスは echo/printf/git commit の
# メッセージ語かつ chain 演算子なしのときだけ救済する（OBS-006・(c) と同一規約）。

# 1語の literal value（クォート除去後）が control plane に解決するか。
_word_is_cp() {
  local w="$1" base
  _text_mentions_cp "$w" && return 0
  case "$w" in
    hooks|scripts|templates|./hooks|./scripts|./templates|\
hooks/|scripts/|templates/|./hooks/|./scripts/|./templates/) return 0 ;;
  esac
  for base in "$ROOT" "$ROOT_REAL"; do
    case "$w" in
      "${base}/hooks"|"${base}/scripts"|"${base}/templates") return 0 ;;
    esac
  done
  return 1
}

# echo/printf/git commit でかつ chain 演算子なし＝CP 引数が書込み先でない救済対象。
_cmd_is_rescued_message() {
  local cmd="$1"
  printf '%s' "$cmd" | grep -qE '[;&|]' && return 1
  printf '%s' "$cmd" | grep -qE '^[[:space:]]*(echo|printf|git[[:space:]]+commit)([[:space:]]|$)'
}

cmd_token_mentions_cp() {
  local cmd="$1" verdict rc
  # cmdsub/backtick は上流の raw fail-closed が担当。shlex は実行される置換を
  # モデル化できないのでここでは決してトークン化しない。
  printf '%s' "$cmd" | grep -qE '\$\(|`' && return 1

  # Sub-check 1 — bare（unquoted・whitespace 区切り）CP ディレクトリ operand。
  # pure-bash（python 非依存）。左右境界が whitespace|^|$ なのでクォート隣接形
  # （"hooks" は引用符に隣接）と path 修飾形（src/hooks）は一致しない＝真にbareな
  # 最上位ディレクトリ語のみ拾う。
  if printf '%s' "$cmd" \
       | grep -qE '(^|[[:space:]])(\./)?(hooks|scripts|templates)/?([[:space:]]|$)'; then
    _cmd_is_rescued_message "$cmd" || return 0
  fi

  # Sub-check 2 のゲート（性能＋ドメイン明確化）: quote/backslash を含まないコマンドは
  # shlex 分割==空白分割で、bare-dir は Sub-check 1 が処理済み・それ以外は既存 regex が
  # 見ている。per-command フックでの余計な python spawn を避けるため早期 return。
  # Sub-check 2 が捕る2クラス（quote分割/backslash）は定義上これらの文字を含むので
  # 取りこぼしゼロ。
  case "$cmd" in
    *\'*|*\"*|*\\*) : ;;
    *) return 1 ;;
  esac

  # Sub-check 2 — quote分割/backslash 再構成（python3 shlex）。CONTROL_PLANE と
  # CP_DIRS を env で渡し python 側に正規表現を複製しない（単一ソース）。
  # python3 不在 → skip（bare-dir は Sub-check 1 で担保済み・quote分割/backslash は
  # 既存 mask+regex 挙動に fallback＝無回帰。既知制約: 完全網羅は python3 前提）。
  command -v python3 >/dev/null 2>&1 || return 1
  verdict=$(AEGIS_CMD="$cmd" AEGIS_CP_RE="$CONTROL_PLANE" AEGIS_CP_DIRS="$CP_DIRS" \
            AEGIS_ROOT="$ROOT" AEGIS_ROOT_REAL="$ROOT_REAL" \
            python3 - <<'PY' 2>/dev/null
import os, re, shlex, sys
cmd = os.environ.get("AEGIS_CMD", "")
cp_re = re.compile(os.environ.get("AEGIS_CP_RE", ""))
cp_dirs = [d for d in os.environ.get("AEGIS_CP_DIRS", "").split("|") if d]
root = os.environ.get("AEGIS_ROOT", ""); root_real = os.environ.get("AEGIS_ROOT_REAL", "")
bare = set()
for d in cp_dirs:
    for pre in ("", "./"):
        for suf in ("", "/"):
            bare.add(pre + d + suf)
    for b in (root, root_real):
        if b:
            bare.add(b.rstrip("/") + "/" + d)
def word_is_cp(w):
    return bool(cp_re.search(w)) or w in bare
try:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
except ValueError:
    sys.exit(3)
CHAIN = {";", "|", "&", "&&", "||", "(", ")"}
chain = any(t in CHAIN for t in toks)
# 先頭の VAR=val 代入を読み飛ばし、最初のコマンド語を得る。
words = [t for t in toks if t not in CHAIN and t not in (">", ">>", "<")]
ci = 0
while ci < len(words) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[ci]):
    ci += 1
c0 = words[ci] if ci < len(words) else ""
c1 = words[ci + 1] if ci + 1 < len(words) else ""
rescued = (not chain) and (c0 in ("echo", "printf") or (c0 == "git" and c1 == "commit"))
redir = False
operand_cp = False
for t in toks:
    if t in (">", ">>"):
        redir = True; continue
    if t == "<":
        redir = False; continue
    if t in CHAIN:
        redir = False; continue
    if redir:
        if word_is_cp(t):
            print("1"); sys.exit(0)   # redirect target=CP は常に write
        redir = False; continue
    if word_is_cp(t):
        operand_cp = True
print("1" if (operand_cp and not rescued) else "0")
PY
)
  rc=$?
  if [ "$rc" -eq 3 ] || [ "$verdict" = "1" ]; then
    return 0
  fi
  return 1
}
```

- [ ] **Step 2: `cmd_mentions_control_plane` 末尾に配線**

既存 `cmd_mentions_control_plane` の最終 `return 1` の直前に1行追加:

```bash
  # SF-001 augment: token-aware split/escaped/bare-dir CP write target.
  if cmd_token_mentions_cp "$cmd"; then
    return 0
  fi
  return 1
```

（cmdsub 分岐 `if printf '%s' "$cmd" | grep -qE '\$\(|`'; then _text_mentions_cp ...; return $?; fi` は手前にあるので、augment は非 cmdsub 経路でのみ実行される。）

- [ ] **Step 3: GREEN 実証**

Run: `python3 -m pytest tests/test_control_plane_token_split.py -v`
Expected: 全 PASS（QuoteSplit/BareDir が deny、NoRegression が allow）。

- [ ] **Step 4: bash 構文検査**

Run: `bash -n hooks/check-control-plane.sh`
Expected: エラーなし（rc=0）。

---

## Task 3: 回帰（既存 moat / 全 suite / REDTEAM）

- [ ] **Step 1: 既存 control-plane テスト**

Run: `python3 -m pytest tests/test_control_plane_allowlist.py tests/test_control_plane_var_expansion.py -v`
Expected: 全 PASS（後退ゼロ）。

- [ ] **Step 2: full suite**

Run: `python3 -m pytest tests/ -q`
Expected: 既存 baseline（830 passed/1 skip）＋新規 22（QuoteSplit 9・BareDir 5・NoRegression 5・Python3Absent 3）を加えて全 PASS（既知 flake `test_python3_absent_advisory_hooks_do_not_crash` は単独実行で緑）。

- [ ] **Step 3: REDTEAM PoC**

Run: `bash tests/poc/v162-redteam-rerun.sh && bash tests/poc/v163-redteam.sh`
Expected: 18/18 ＋ 5/5（緑維持）。

---

## Task 4: mirror 同期 + drift

- [ ] **Step 1: mirror 再生成**

Run: `make example`
Expected: `examples/minimal-project/hooks/check-control-plane.sh` が root と byte-identical に更新。

- [ ] **Step 2: drift / mirror identity**

Run: `python3 scripts/check_reference_drift.py && python3 -m pytest tests/test_mirror_identity.py tests/test_sync_example_mirror.py -q`
Expected: 全 PASS。

---

## Task 5: 版 bump 1.11.0 → 1.12.0

新規 deny 挙動を伴う（`npm run hooks` 等が deny 化）＝挙動変更 → minor。

- [ ] **Step 1: 4箇所を 1.12.0 に**

- `scripts/check_framework_contract.py:24` `FRAMEWORK_VERSION = "1.12.0"`
- `templates/STATUS.template.md:3` `framework_version: "1.12.0"`
- `examples/minimal-project/docs/STATUS.md:3` `framework_version: "1.12.0"`
- `docs/STATUS.md:3` `framework_version: "1.12.0"`

- [ ] **Step 2: contract（全 profile）**

Run: `python3 scripts/check_framework_contract.py && python3 scripts/check_status.py --root .`
Expected: 全 PASS。

---

## Task 6: commit

- [ ] **Step 1: commit**

```bash
git add hooks/check-control-plane.sh examples/minimal-project/hooks/check-control-plane.sh \
  tests/test_control_plane_token_split.py scripts/check_framework_contract.py \
  templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md
git commit -m "fix(security): close SF-001 control-plane token-split bypass (v1.12.0)"
```

（push は明示承認まで禁止。）

---

## Self-Review

- **Spec coverage:** quote分割/隣接連結/single-quote/slash分割=Sub-check2 ✓ / backslash=Sub-check2 ✓ / redirect分割=Sub-check2 redirect-target ✓ / STATUS分割=Sub-check2 regex ✓ / xargs・find -exec split=Sub-check2 ✓ / bare-dir(find/rm/cp)=Sub-check1 ✓ / OBS-006 救済=`_cmd_is_rescued_message` + python rescued ✓ / read 救済=下流 read-only carve-out ✓ / fail-closed(ValueError/cmdsub/python不在)=明記 ✓。
- **Placeholder scan:** なし（全コード/コマンド実体）。
- **Type consistency:** `_word_is_cp`/`_cmd_is_rescued_message`/`cmd_token_mentions_cp` 名はタスク間一致。env キー `AEGIS_CMD/AEGIS_CP_RE/AEGIS_CP_DIRS/AEGIS_ROOT/AEGIS_ROOT_REAL` 一致。`CONTROL_PLANE`/`CP_DIRS`/`_text_mentions_cp`/`ROOT`/`ROOT_REAL` は既存定義を参照。

## 既知残リスク（記録）

- bare 語が CP ディレクトリ名と完全一致する非 fs コマンド（`npm run hooks`/`make templates`/`git status hooks` 等）は deny になる（fail-closed・列挙漏れゼロを優先・task_type=framework で回避可）。`git diff hooks/` 等は既存挙動でも既に deny ＝ bare 形と整合させるだけで新規後退ではない。
- python3 不在時、quote分割/backslash クラスは既存 mask+regex 挙動に fallback（bare-dir は pure-bash で担保）。python3 は framework 全体の hard 依存。`TestPython3Absent` で degraded 時の bare-dir deny・非クラッシュを固定。
- **glob メタ文字バイパス（`rm -rf hooks*` 等）は本タスクのスコープ外＝`SF-002` として `docs/security-followups.md` に記録**（既存 moat も素通り・別タスクで消化）。
- `git -C <dir> commit` のメッセージ救済漏れは既存 (c) と共通の既存欠陥（新規後退なし）・SF-001 スコープ外。

## grill-plan 反映（2026-06-18・自己グリル）

- 致命1: shlex / `re.compile(CONTROL_PLANE)` 未検証 → **Task 0 スパイク**を新設。
- 致命2: per-command フックでの余計な python spawn → Sub-check 2 に**クォート/バックスラッシュ ゲート**（`case` 早期 return）を追加。
- 要検討1: python-absent 未検証 → **`TestPython3Absent`** を Task 1 に追加。
- 要検討2: glob → **SF-002** として記録しスコープ固定。
- 要検討3: `git -C ... commit` 救済漏れ → 記録のみ（既存共通・繰延）。

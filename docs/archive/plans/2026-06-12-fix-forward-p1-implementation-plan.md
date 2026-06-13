# Aegis fix-forward P1 実装計画（v1.6.0）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 行動レビュー（`docs/behavioral-review-report-2026-06-12.md` §5.1）の P1×4 — A: skill 到達性、B: templates/ 配布、C: judge card クラッシュ修正＋push 化、D: Client ゲート artifact 検査 — を v1.6.0（minor）として封鎖する。

**Architecture:** 各 P1 を「ランタイム修正（hook/lib/script）＋契約検査（tier0 テスト / drift / scaffold smoke）」の対で実装する。F6 の教訓（install 出力の死角）に従い、repo 静的検査だけでなく install 先の検証まで契約化する。skill 起動は「phase→必読 skill パス」を `hooks/lib/phase-skills.sh` に単一所有させ、SessionStart と phase 遷移（PostToolUse）の両方から Read 指示として注入する。

**Tech Stack:** bash 3.2 互換（macOS 既定）、Python 3 標準ライブラリのみ、unittest（tier 0）、既存 tier 1〜3 検査群。

**作業ディレクトリ:** aegis リポジトリのルート（このファイルから見て `../..`）。

---

## 背景（§5.1 → 設計対応）

| P1 | 根本原因（OBS） | 本計画の対応 |
|----|----|----|
| C① judge crash | commit ゼロ→empty-tree fallback で index 全量がスコープ化、node_modules のバイナリ（Mach-O、NUL なし）を `read_text` が strict decode→`UnicodeDecodeError`（`except OSError` で捕捉されず）(OBS-023) | Task 1-3: drill 側に vendor 区画除外を単一所有（judge は drill 経由で自動享受）＋ diff/`read_text` の decode 耐性 |
| C② judge 未到達 | カードは pull 専用（/judge）で client に届かず、/gate の承認確認がカード生成より先 (OBS-019/026) | Task 4-5: update-gate.sh がカード全文を transcript に push ＋ /gate の提示→確認 順序修正 |
| D Client ゲート無検査 | `client_ready_for_dev` が mapping.md 1 点しか見ず素通し (OBS-008/034) | Task 6-7: 引き渡し成果物 6 点の存在検査を承認側＋完了側（対称）に追加 |
| B templates 未配布 | setup.sh が templates/ を配らず 7 skill × 9 参照が install 先で死ぬ（F6 同類） (OBS-012) | Task 8-9: full.json に 6 テンプレート追加＋ drift / smoke で参照を契約化 |
| A skill 起動不能 | 全 skill が `disable-model-invocation: true`（session-recovery 以外 `user-invocable: false`）で、name-form ヒントでは起動経路が無い (OBS-004/020/031/032/034/035) | Task 10-14: phase→skill マップ単一所有＋SessionStart/遷移時の Read 指示注入＋全 skill の到達性を drift で契約化＋name-form 参照の path-form 正規化 |

## 変更ファイルマップ

| 区分 | ファイル | 内容 |
|------|---------|------|
| P1-C① | `scripts/run-test-strength-drill.py` | `VENDOR_SEGMENTS`/`vendor_excluded()` 追加、`_drill_excluded` 拡張、`_tracked_added_lines` に `errors="replace"` |
| P1-C① | `scripts/build-judge-card.py` | `scan_stubs`/`scan_secrets` の `except` に `UnicodeDecodeError` 追加 |
| P1-C② | `scripts/update-gate.sh` | judge ゲート承認成功時にカード全文を stdout へ push |
| P1-C② | `.claude/commands/gate.md` | 承認フローを「カード提示→確認→実行」に順序修正 |
| P1-D | `scripts/check_status.py` | `CLIENT_GATE_ARTIFACTS` 新設、`check_gate_prerequisites` の client 分岐書替、`evidence_integrity_violations` 拡張 |
| P1-B | `templates/profiles/full.json` | recommended に 6 テンプレート追加 |
| P1-B | `scripts/check_reference_drift.py` | `check_template_references` 新設 |
| P1-B | `scripts/eval_scaffold_smoke.py` | `verify_template_references` 新設・連結 |
| P1-A | `hooks/lib/phase-skills.sh` | **新規**: phase→必読 skill マップ（単一所有） |
| P1-A | `hooks/session-start.sh` | HINT から skill 名を分離し、lib 由来の Read 指示を注入＋保守期トリガ |
| P1-A | `hooks/post-status-audit.sh` | 正当な phase 遷移時に additionalContext で Read 指示を注入 |
| P1-A | `hooks/lib/emit.sh` | schema コメントに PostToolUse(context) を追記 |
| P1-A | `scripts/check_reference_drift.py` | `check_skill_reachability` 新設（`check_session_start_hints` を置換） |
| P1-A | skills/agents/rules/`check_status.py` | name-form 参照 14 箇所を path-form に正規化 |
| 版数 | `scripts/check_framework_contract.py:17`、`templates/STATUS.template.md:3`、`examples/minimal-project/docs/STATUS.md:3`、`docs/STATUS.md:3` | `1.5.2` → `1.6.0`（example STATUS は contract が一致を要求） |
| ミラー | `examples/minimal-project/**` | 上記のうち MIRROR_DIRS/MIRROR_FILES 該当分をバイト同一同期 |

**新規テスト:** `tests/test_phase_skills_lib.py`、`tests/test_phase_skill_injection.py`、`tests/test_skill_reachability.py`、`tests/test_judge_card_push.py`
**既存テスト拡張:** `tests/test_test_strength_drill.py`、`tests/test_judge_card.py`、`tests/test_check_status.py`

## 共通規約

- **ミラー同期**: `.claude/agents|rules|skills|commands`・`hooks/` 全体（MIRROR_DIRS）と `scripts/{check_status.py, update-gate.sh, run-test-strength-drill.py, build-judge-card.py, record-test-result.py, status_doctor.py}`（MIRROR_FILES）はバイト同一が契約（tier0 `test_mirror_identity` が検査）。**該当ファイルを変更したタスクは、コミット前に必ず `cp` でミラーへ同期する。**
- **検証コマンド**:
  - tier0 全体: `python3 scripts/run_eval.py --tier 0`（479 tests 起点）
  - 単体: `python3 -m unittest tests.test_judge_card -v` など
  - tier1: `python3 scripts/run_eval.py --tier 1` / tier2: `--tier 2` / tier3: `--tier 3`
  - strict: `python3 scripts/check_status.py --root . --strict`
- **コミット**: タスク単位。メッセージは既存流儀（`fix:`/`feat:`/`test:`）。

---

### Task 1: drill — vendor 区画の恒久除外（OBS-023 スコープ汚染の根治）

empty-tree fallback（commit ゼロ）では index 全量が「追加行」になる。vendor/build 区画はタスクコードではないので、drill の除外述語に恒久追加する。judge（`build-judge-card.py`）は `added_lines_by_file` を経由して消費するため、ここを直すと両方に効く（単一所有）。

**Files:**
- Modify: `scripts/run-test-strength-drill.py:20-33`（定数群）
- Test: `tests/test_test_strength_drill.py`（クラス追記）
- Mirror: `examples/minimal-project/scripts/run-test-strength-drill.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_test_strength_drill.py` の末尾にクラスを追加（ファイル冒頭で drill モジュールは `drill` 名でロード済み。`tempfile`/`Path`/`sp` も import 済み）:

```python
class TestVendorExclusion(unittest.TestCase):
    """OBS-023: empty-tree fallback 下で vendor/build 区画がスコープ汚染しない。"""

    def test_vendor_excluded_segments(self):
        self.assertTrue(drill.vendor_excluded("node_modules/.bin/esbuild"))
        self.assertTrue(drill.vendor_excluded("packages/app/node_modules/x/index.js"))
        self.assertTrue(drill.vendor_excluded("dist/main.js"))
        self.assertTrue(drill.vendor_excluded(".venv/lib/python3.12/site-packages/x.py"))
        self.assertFalse(drill.vendor_excluded("src/app.py"))
        self.assertFalse(drill.vendor_excluded("src/dist.py"))           # ファイル名は対象外
        self.assertFalse(drill.vendor_excluded("distribution/x.py"))    # セグメント完全一致のみ
        # 既知の境界（grill-plan B 🟡-1 で受容・残余リスク 1 に記録）:
        # dist/build 等は深さ問わず除外されるため、src/dist/ のような
        # 正規ソースのディレクトリ名衝突も drill スコープから外れる
        self.assertTrue(drill.vendor_excluded("src/dist/gen.js"))

    def test_added_lines_exclude_vendor_under_empty_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
            nm = root / "node_modules" / "pkg"
            nm.mkdir(parents=True)
            (nm / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")
            _git(root, "add", "-A")
            added = drill.added_lines_by_file(root, drill.EMPTY_TREE)
            self.assertIn("src/app.py", added)
            self.assertNotIn("node_modules/pkg/index.js", added)
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_test_strength_drill.TestVendorExclusion -v`
期待: FAIL（`AttributeError: module 'drill' has no attribute 'vendor_excluded'`）

- [ ] **Step 3: 最小実装**

`scripts/run-test-strength-drill.py` の `DRILL_EXCLUDED_PREFIXES` ブロック（26-30 行付近）を次に置換:

```python
DRILL_EXCLUDED_PREFIXES = ("docs/",)  # superset of DRILL_ARTIFACT_PREFIX

# Vendor/build/VCS output is never task code (OBS-023): under the empty-tree
# fallback (no commits yet) the WHOLE index becomes "added lines", and
# node_modules/dist would otherwise dominate the drill scope and feed binaries
# to the judge scanners. Matched as full directory segments at any depth
# (monorepo packages/*/node_modules included); the final path segment is the
# filename and is deliberately not matched.
VENDOR_SEGMENTS = frozenset({
    "node_modules", "vendor", "dist", "build", "out", "coverage",
    ".git", ".venv", "venv", ".next", ".nuxt", ".astro",
})


def vendor_excluded(rel: str) -> bool:
    return any(seg in VENDOR_SEGMENTS for seg in rel.split("/")[:-1])


def _drill_excluded(rel: str) -> bool:
    return rel.startswith(DRILL_EXCLUDED_PREFIXES) or vendor_excluded(rel)
```

（既存の `def _drill_excluded` 2 行定義は上記に統合して削除。）

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_test_strength_drill -v`
期待: 全 PASS（既存テスト含む）

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py
git add scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "fix: exclude vendor/build segments from drill scope (OBS-023 scope pollution)"
```

---

### Task 2: drill — バイナリ diff の decode 耐性

NUL を含まない不正 UTF-8（Mach-O ヘッダ等）は git に「テキスト」扱いされ、`git diff` の +行に生バイトが乗る。`_tracked_added_lines` は `text=True`（errors=strict）で decode するため、ここでもクラッシュし得る。

**Files:**
- Modify: `scripts/run-test-strength-drill.py:85-92`（`_tracked_added_lines`）
- Test: `tests/test_test_strength_drill.py`（メソッド追記）
- Mirror: `examples/minimal-project/scripts/run-test-strength-drill.py`

- [ ] **Step 1: 失敗するテストを書く**

`TestVendorExclusion` クラスにメソッドを追加:

```python
    def test_undecodable_tracked_diff_does_not_crash(self):
        # NUL なし不正 UTF-8: git はテキスト扱いで +行に生バイトを乗せる
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _git_init(root)
            (root / "src").mkdir()
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
            _git(root, "add", "-A")
            added = drill.added_lines_by_file(root, drill.EMPTY_TREE)  # 例外なく返る
            self.assertIn("src/app.py", added)
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_test_strength_drill.TestVendorExclusion.test_undecodable_tracked_diff_does_not_crash -v`
期待: ERROR（`UnicodeDecodeError` が `_tracked_added_lines` から伝播）
（環境のロケール次第で latin-1 系にフォールバックして偶然通る場合は、その旨をテスト docstring に追記したうえで Step 3 の恒久化だけ行う — decode 既定は環境依存であり、`errors="replace"` の明示が契約。）

- [ ] **Step 3: 最小実装**

`scripts/run-test-strength-drill.py` の `_tracked_added_lines` 内 `subprocess.run` を変更:

```python
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--unified=0", ref],
            capture_output=True, text=True, check=True,
            errors="replace",  # binary-ish diffs must not crash scope discovery
        ).stdout
```

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_test_strength_drill -v`
期待: 全 PASS

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py
git add scripts/run-test-strength-drill.py examples/minimal-project/scripts/run-test-strength-drill.py tests/test_test_strength_drill.py
git commit -m "fix: tolerate undecodable bytes in drill diff scope discovery"
```

---

### Task 3: judge — scanner の decode 耐性＋OBS-023 統合再現

drill 側の除外で vendor 由来のバイナリは届かなくなるが、ソース区画に直接置かれたバイナリ（committed .png 等）で `scan_stubs`/`scan_secrets` の `read_text` がなおクラッシュし得る（`UnicodeDecodeError` ⊄ `OSError`）。例外捕捉を広げ、OBS-023 の再現コマンドを統合テストとして封鎖する。

**Files:**
- Modify: `scripts/build-judge-card.py:88-91, 229-232`（scan_stubs / scan_secrets の except）
- Test: `tests/test_judge_card.py`（クラス追記）
- Mirror: `examples/minimal-project/scripts/build-judge-card.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_judge_card.py` の末尾にクラスを追加（冒頭で judge モジュールは `judge` 名、`_copy_lib`/`sp`/`tempfile` 定義済み）:

```python
class TestBinaryScanResilience(unittest.TestCase):
    """OBS-023: バイナリ混入 index で judge ビルダーがクラッシュしない。"""

    def _scaffold_repo(self, root: Path) -> None:
        sp.run(["git", "init", "-q"], cwd=str(root), check=True)
        _copy_lib(root)
        (root / "docs" / "qa-reports").mkdir(parents=True)
        (root / "docs" / "STATUS.md").write_text(
            "---\nframework: aegis\nmode: Dev\nphase: review\n"
            "task_type: feature\ntask_size: M\n"
            "gate_approvals:\n  review: pending\n"
            "current_refs:\n  review: null\n---\n", encoding="utf-8")

    def test_scan_skips_undecodable_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scaffold_repo(root)
            (root / "src").mkdir()
            # NUL なし不正 UTF-8 → drill は追加行として返し、read_text が strict だと落ちる
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            sp.run(["git", "add", "-A"], cwd=str(root), check=True)
            self.assertEqual(judge.scan_stubs(root), [])    # 例外なく skip
            self.assertEqual(judge.scan_secrets(root), [])

    def test_obs023_cli_repro_no_traceback(self):
        # 再現コマンド: python3 scripts/build-judge-card.py --gate review --root .
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scaffold_repo(root)
            nm = root / "node_modules" / ".bin"
            nm.mkdir(parents=True)
            (nm / "esbuild").write_bytes(b"\xcf\xfa\xed\xfe" * 256 + b"\n")
            (root / "src").mkdir()
            (root / "src" / "blob.bin").write_bytes(b"\xcf\xfa\xed\xfe" * 64 + b"\n")
            sp.run(["git", "add", "-A"], cwd=str(root), check=True)
            r = sp.run(["python3", str(SCRIPT), "--gate", "review", "--root", str(root)],
                       capture_output=True, text=True, timeout=120)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn(r.returncode, (0, 1, 2))
            self.assertTrue((root / "docs" / "qa-reports" / "judge-review.md").is_file())
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_judge_card.TestBinaryScanResilience -v`
期待: `test_scan_skips_undecodable_changed_file` が ERROR（`UnicodeDecodeError`）。
（`test_obs023_cli_repro_no_traceback` は build() の catch-all が 🟡 degrade に拾う場合 PASS し得る — その場合も前者の RED で十分。catch-all 越しの degrade はカード信頼性の毀損なので、root cause を直す。）

- [ ] **Step 3: 最小実装**

`scripts/build-judge-card.py` の `scan_stubs` と `scan_secrets` 両方（2 箇所）で:

```python
        except (OSError, UnicodeDecodeError):
            continue
```

（変更前はどちらも `except OSError:` のみ。）

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_judge_card -v`
期待: 全 PASS

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py
git add scripts/build-judge-card.py examples/minimal-project/scripts/build-judge-card.py tests/test_judge_card.py
git commit -m "fix: judge scanners skip undecodable files instead of crashing (OBS-023)"
```

---

### Task 4: update-gate.sh — judge カードの transcript push（OBS-019）

カードが pull 専用（/judge）だと client に届かないことが実証された。決定論側の対処として、judge ゲート（review/qa/security/deploy）の承認成功時に update-gate.sh がカード全文を stdout に流す。stdout は transcript に載るため、LLM が「提示し忘れる」余地を構造的に減らす。

**Files:**
- Modify: `scripts/update-gate.sh:236-237`（approve ケースの tri-state 判定直後）
- Test: `tests/test_judge_card_push.py`（新規）
- Mirror: `examples/minimal-project/scripts/update-gate.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_judge_card_push.py` を新規作成:

```python
#!/usr/bin/env python3
"""P1-C② (OBS-019): judge ゲート承認時、update-gate.sh はカード全文を
stdout に push する（pull 専用カードは client に届かないことが行動レビューで実証済み）。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_CONTENT = """---
framework: aegis
framework_version: "1.6.0"
project_name: test
mode: Dev
phase: review
task_type: feature
task_size: M
last_updated: "2026-06-12"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: null
  plan: null
  spec: null
  review: docs/qa-reports/review.md
  qa: null
  security: null
  deploy: null
  translation: null
---
"""


class TestJudgeCardPush(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        docs = d / "docs"
        (docs / "qa-reports").mkdir(parents=True)
        (docs / "STATUS.md").write_text(STATUS_CONTENT, encoding="utf-8")
        (docs / "qa-reports" / "review.md").write_text("# review\n", encoding="utf-8")
        scripts = d / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "update-gate.sh", scripts / "update-gate.sh")
        for name in ("check_status.py", "build-judge-card.py",
                     "run-test-strength-drill.py", "record-test-result.py"):
            (scripts / name).symlink_to(ROOT / "scripts" / name)
        shutil.copytree(ROOT / "hooks" / "lib", d / "hooks" / "lib")
        return d

    def test_approve_pushes_card_to_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            # git なし → drill 系は build() の catch-all で 🟡 degrade → --ack 経路
            r = subprocess.run(
                ["bash", str(root / "scripts" / "update-gate.sh"),
                 "review", "approve", "--ack", "テスト確認済み"],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
            self.assertIn("JUDGE CARD", r.stdout)
            card = root / "docs" / "qa-reports" / "judge-review.md"
            self.assertTrue(card.is_file())
            # カード本文（ヘッダ行）が stdout に含まれる = 全文 push
            first_line = card.read_text(encoding="utf-8").splitlines()[0]
            self.assertIn(first_line, r.stdout)
            self.assertIn("review: approved",
                          (root / "docs" / "STATUS.md").read_text(encoding="utf-8")
                          .replace("  review: approved", "review: approved"))
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_judge_card_push -v`
期待: FAIL（`'JUDGE CARD' not found in ...` — 承認自体は成功するが push がない）
※ fixture 側の不備（rc≠0）で落ちる場合は、stdout/stderr を読んで fixture を直すこと（例: 不足ライブラリの symlink 追加）。RED の根拠は「JUDGE CARD 不在」のアサーションであること。
※ 安定しない場合の代替（grill-plan A 🟡-2）: fixture に `git init`＋空コミットを足して 🟢 経路に倒してもよい。その場合は `--ack` を外し、アサーションは同一のまま（push ブロックは Step 3 のとおり tri-state 判定の外にあるため 🟢/🟡 どちらの経路でも実行される）。

- [ ] **Step 3: 最小実装**

`scripts/update-gate.sh` の approve ケース、tri-state 判定の `fi` 直後・`TARGET_VALUE="approved"` の直前に挿入:

```bash
    # B2 judge-card push (P1-C2, OBS-019): print the full card into the
    # transcript so the LLM relays it to the client. Pull-only cards (/judge)
    # never reached non-engineer clients in the behavioral review.
    # Gate list duplicates check_status.py JUDGE_GATES (bash cannot import it).
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
```

実装メモ（grill-plan B 🟡-2 の鮮度懸念への回答）: 挿入位置は tri-state 判定の外なので
🟢（rc=0）と 🟡（--ack）の両経路で push される。カードの鮮度は
`check_status.py --pre-approve-gate` が approve 実行のたびにカードを再生成することで担保される
（実装時に `pre_approve_gate` が build を毎回呼ぶことを確認。呼ばない経路があれば push 直前に
`build-judge-card.py` を 1 回実行する行を足す）。

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_judge_card_push -v` → PASS
追加確認: `python3 -m unittest tests.test_update_gate_lock -v` → 既存ロック挙動が無傷で PASS

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh
git add scripts/update-gate.sh examples/minimal-project/scripts/update-gate.sh tests/test_judge_card_push.py
git commit -m "feat: push full judge card into transcript on gate approval (OBS-019)"
```

---

### Task 5: /gate — カード提示→確認の順序修正（OBS-026）

現行の /gate は「確認→update-gate.sh→（その過程で）カード生成」で、ユーザはカードを見ずに承認判断している。判断材料を先に出す順序へ書き替える（LLM 手順層の修正。決定論側の押さえは Task 4 の push）。

**Files:**
- Modify: `.claude/commands/gate.md:18-28`（Approve mode）
- Mirror: `examples/minimal-project/.claude/commands/gate.md`

- [ ] **Step 1: gate.md の Approve mode を置換**

現行の手順 3〜5 を次に置換:

```markdown
3. **Pre-validation check**: For gates with ref mappings (plan, review, qa, security, deploy), verify `current_refs.<gate>` is set. If empty, display the ref status and warn the user before proceeding.
4. **Judge preview (review/qa/security/deploy のみ)**: 承認を求める**前に**カードを提示する:
   - Run: `python3 scripts/build-judge-card.py --gate <gate-name> --root .`
   - Read `docs/qa-reports/judge-<gate-name>.md` and present it to the user in plain Japanese, filling the「次のアクション」section from context. The user decides by looking at the card — never summarize it away.
5. Confirm with the user: "Approve {gate} gate? This advances the workflow."
6. On confirmation, run:

```bash
bash scripts/update-gate.sh <gate-name> approve
```

If the result is 🟡, relay the card's 🟡 items and ask the user for an explicit reason, then run:

```bash
bash scripts/update-gate.sh <gate-name> approve --ack "<user-stated reason>"
```

The reason must come from the user's reply — never invent one.
```

- [ ] **Step 2: 検証**

実行: `python3 scripts/check_reference_drift.py`（commands ↔ README の drift がないこと）
期待: PASS

- [ ] **Step 3: ミラー同期してコミット**

```bash
cp .claude/commands/gate.md examples/minimal-project/.claude/commands/gate.md
git add .claude/commands/gate.md examples/minimal-project/.claude/commands/gate.md
git commit -m "docs: present judge card before approval confirmation in /gate (OBS-026)"
```

---

### Task 6: check_status.py — Client ゲートの成果物検査（承認側、OBS-008）

`client_ready_for_dev` は Client→Dev の唯一の機械ゲートなのに mapping.md しか見ていない。client-workflow skill のフェーズ表が定める引き渡しパッケージ 6 点の存在検査に置き換える。不足は**一括で全件**報告し、誘導は path-form（Read 可能な形）にする。

**Files:**
- Modify: `scripts/check_status.py:37` 付近（定数追加）、`:878-885`（client 分岐置換）
- Test: `tests/test_check_status.py`（クラス追記）
- Mirror: `examples/minimal-project/scripts/check_status.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_check_status.py` の末尾にクラスを追加（冒頭の `make_status_md`/`CHECK_STATUS` を利用）:

```python
CLIENT_ARTIFACTS = [
    "docs/requirements/PRD.md",
    "docs/requirements/SCOPE.md",
    "docs/requirements/NFR.md",
    "docs/requirements/ACCEPTANCE.md",
    "docs/handover/TO-DEV.md",
    "docs/translation/mapping.md",
]


def _pre_approve(root: Path, gate: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(CHECK_STATUS), "--root", str(root),
         "--pre-approve-gate", gate],
        capture_output=True, text=True, timeout=60)


class TestClientGateArtifacts(unittest.TestCase):
    """P1-D (OBS-008): client_ready_for_dev は引き渡し成果物 6 点の存在を要求する。"""

    def _scaffold(self, d: Path, present: list[str]) -> Path:
        (d / "docs").mkdir(parents=True, exist_ok=True)
        (d / "docs" / "STATUS.md").write_text(
            make_status_md(mode="Client", phase="handover",
                           approvals={"client_ready_for_dev": "pending",
                                      "brainstorm": "pending", "plan": "pending"}),
            encoding="utf-8")
        for rel in present:
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# stub\n", encoding="utf-8")
        return d

    def test_blocks_and_lists_all_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), present=[])
            r = _pre_approve(root, "client_ready_for_dev")
            self.assertNotEqual(r.returncode, 0)
            for rel in CLIENT_ARTIFACTS:
                self.assertIn(rel, r.stdout, f"missing artifact {rel} must be listed")
            self.assertIn(".claude/skills/client-workflow/SKILL.md", r.stdout)

    def test_lists_only_missing_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            present = CLIENT_ARTIFACTS[:4]
            root = self._scaffold(Path(tmp), present=present)
            r = _pre_approve(root, "client_ready_for_dev")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("docs/handover/TO-DEV.md", r.stdout)
            self.assertIn("docs/translation/mapping.md", r.stdout)
            self.assertNotIn("docs/requirements/PRD.md", r.stdout)

    def test_passes_with_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), present=CLIENT_ARTIFACTS)
            r = _pre_approve(root, "client_ready_for_dev")
            self.assertEqual(r.returncode, 0, f"stdout={r.stdout}")
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_check_status.TestClientGateArtifacts -v`
期待: `test_blocks_and_lists_all_missing` と `test_lists_only_missing_subset` が FAIL（現行は mapping.md しか報告しない／PRD 等は素通し）。`test_passes_with_all_artifacts` は PASS（互換確認）。

- [ ] **Step 3: 最小実装**

`scripts/check_status.py` の `GATE_REF_MAPPING`（37 行付近）直後に定数を追加:

```python
# P1-D (OBS-008): client_ready_for_dev is the ONLY machine gate between Client
# and Dev. The handover package below mirrors the client-workflow skill's
# phase table; without an existence check the gate approves on bare assertion.
CLIENT_GATE_ARTIFACTS = (
    "docs/requirements/PRD.md",
    "docs/requirements/SCOPE.md",
    "docs/requirements/NFR.md",
    "docs/requirements/ACCEPTANCE.md",
    "docs/handover/TO-DEV.md",
    "docs/translation/mapping.md",
)
```

`check_gate_prerequisites` の `client_ready_for_dev` 分岐（878-885 行）を置換:

```python
    if gate_name == "client_ready_for_dev":
        missing = [rel for rel in CLIENT_GATE_ARTIFACTS
                   if not (root / rel).exists()]
        if missing:
            print("ERROR: client_ready_for_dev に必要な引き渡し成果物が不足しています:")
            for rel in missing:
                print(f"       - {rel}")
            print("       → .claude/skills/client-workflow/SKILL.md を Read し、"
                  "不足フェーズを完了してください。")
            print("       （mapping.md の作り方は "
                  ".claude/skills/translation-mapping/SKILL.md）")
            return 1
        return 0
```

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_check_status -v`
期待: 全 PASS（既存の routing matrix テスト含む）

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/check_status.py examples/minimal-project/scripts/check_status.py
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "feat: require full handover package for client_ready_for_dev (OBS-008)"
```

---

### Task 7: check_status.py — 完了側の対称検査（evidence_integrity_violations 拡張）

Dev 側ゲートは TaskCompleted hook（`--check-completion-evidence`）で完了時にも検査される。Client ゲートにも同じ対称性を与える: `client_ready_for_dev: approved` なのに成果物が消えている（または最初から無い）状態は完了違反。

**仕様変更の明示:** 旧版で mapping.md のみで approved にした既存プロジェクトは、artifact が揃うまで完了がブロックされる（fix-forward の意図どおり）。`n/a` のプロジェクト（Dev 発進、Aegis 自身を含む）は無影響。

**Files:**
- Modify: `scripts/check_status.py:422-462`（`evidence_integrity_violations`）
- Test: `tests/test_check_status.py`（クラス追記）
- Mirror: `examples/minimal-project/scripts/check_status.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_check_status.py` に追加:

```python
class TestClientGateCompletionEvidence(unittest.TestCase):
    """P1-D 完了側: approved な client ゲートは成果物の実在を要求し続ける。"""

    # 注意（grill-plan B 🔴-1）: 既存ルールが「approved な client ゲート × current_refs.translation
    # が空」で violation を出すため、approved ケースは refs.translation を必ず埋める。
    # これを怠ると clean ケースが既存ルール起因のメッセージ（'client_ready_for_dev' を含む）で
    # 誤 FAIL する。
    def _scaffold(self, d: Path, gate: str, present: list[str],
                  refs: dict[str, str] | None = None) -> Path:
        (d / "docs").mkdir(parents=True, exist_ok=True)
        (d / "docs" / "STATUS.md").write_text(
            make_status_md(mode="Dev", phase="implement",
                           approvals={"client_ready_for_dev": gate},
                           refs=refs),
            encoding="utf-8")
        for rel in present:
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# stub\n", encoding="utf-8")
        return d

    def _check(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(CHECK_STATUS), "--root", str(root),
             "--check-completion-evidence"],
            capture_output=True, text=True, timeout=60)

    def test_approved_with_missing_artifact_is_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(
                Path(tmp), "approved",
                present=CLIENT_ARTIFACTS[:-1],  # TO-DEV までは存在、mapping.md が欠落
                refs={"translation": "docs/translation/mapping.md"})
            r = self._check(root)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("handover artifact is missing", r.stdout + r.stderr)
            self.assertIn("docs/translation/mapping.md", r.stdout + r.stderr)

    def test_na_gate_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "n/a", present=[])
            r = self._check(root)
            out = r.stdout + r.stderr
            self.assertNotIn("client_ready_for_dev", out)

    def test_approved_with_all_artifacts_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(
                Path(tmp), "approved", present=CLIENT_ARTIFACTS,
                refs={"translation": "docs/translation/mapping.md"})
            r = self._check(root)
            self.assertNotIn("client_ready_for_dev",
                             r.stdout + r.stderr)
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_check_status.TestClientGateCompletionEvidence -v`
期待: `test_approved_with_missing_artifact_is_violation` が FAIL（現行は「handover artifact is missing」を出さない）。RED の根拠はこの新ルール固有のメッセージであり、既存の refs-empty ルールのメッセージでは GREEN 偽装にならない。

- [ ] **Step 3: 最小実装**

`evidence_integrity_violations` の `try` ブロック内、requirements ループの直後に追加:

```python
        if approvals.get("client_ready_for_dev") == "approved":
            for rel in CLIENT_GATE_ARTIFACTS:
                if not (root / rel).exists():
                    violations.append(
                        "gate 'client_ready_for_dev' is approved but handover "
                        f"artifact is missing: {rel}"
                    )
```

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_check_status -v` → 全 PASS
追加確認: `python3 scripts/check_status.py --root . --strict` → Aegis 自身（client ゲート n/a）が無影響で PASS

※ 既存 fixture 点検（grill-plan B 🔴-2）: `DEFAULT_APPROVALS` は
`client_ready_for_dev: "approved"` 固定のため、`--check-completion-evidence` や strict 経路を
呼ぶ既存テストが新ルール（artifact 不在 violation）に該当して FAIL する可能性がある。
FAIL した場合は**ルール側を緩めず**、該当 fixture に成果物 6 点を作成するか
approvals を `n/a` に上書きして調整する。tier0 全体
（`python3 -m unittest discover tests/`）でも回帰ゼロを確認してからコミットする。

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp scripts/check_status.py examples/minimal-project/scripts/check_status.py
git add scripts/check_status.py examples/minimal-project/scripts/check_status.py tests/test_check_status.py
git commit -m "feat: enforce client handover artifacts at completion (Dev/Client symmetry)"
```

---

### Task 8: templates 配布 — full.json 追加＋drift 契約（OBS-012）

skill 7 本が `templates/*.template.md` 9 参照を持つのに、profile はテンプレートを 1 つも配らない（F6 同類: install 先で参照が死ぬ）。配布リストに加え、**「skill を配るなら参照テンプレートも配る」を drift の恒久契約にする**（再発封鎖。テンプレート参照を持つ skill を将来追加した時に機械が止める）。

setup.sh は変更不要: `resolve_source` の default 分岐が `templates/X` をそのまま `$FRAMEWORK_ROOT/templates/X` から copy する。

**Files:**
- Modify: `scripts/check_reference_drift.py`（`check_template_references` 新設＋ALL_CHECKS 登録）
- Modify: `templates/profiles/full.json`（recommended に 6 件）
- Mirror: なし（どちらも MIRROR 対象外）

- [ ] **Step 1: 検査を先に書く（システムレベル RED の準備）**

`scripts/check_reference_drift.py` の `check_session_start_hints` の直前に追加（`json` は import 済み）:

```python
TEMPLATE_REF_RE = re.compile(r"templates/[A-Za-z0-9._-]+\.template\.md")


def check_template_references(root: Path) -> tuple[list[str], list[str]]:
    """#12: templates/ refs in skills must exist AND be shipped by any profile
    that ships the referencing skill (P1-B, OBS-012 — F6-class install gap:
    a skill instructing 'use templates/X' dies at install when X is absent)."""
    failures: list[str] = []
    warnings: list[str] = []

    skills_dir = root / ".claude" / "skills"
    refs_by_file: dict[str, set[str]] = {}
    if skills_dir.is_dir():
        for sk in sorted(skills_dir.glob("*/SKILL.md")):
            refs = set(TEMPLATE_REF_RE.findall(_read(sk)))
            if refs:
                refs_by_file[f".claude/skills/{sk.parent.name}/SKILL.md"] = refs

    # 1) Repo-level: referenced template files must exist.
    for src, refs in sorted(refs_by_file.items()):
        for ref in sorted(refs):
            if not (root / ref).is_file():
                failures.append(f"{src} references {ref} but the template does not exist")

    # 2) Profile-level: a profile shipping the skill must ship its templates.
    profiles_dir = root / "templates" / "profiles"
    if profiles_dir.is_dir():
        for prof in sorted(profiles_dir.glob("*.json")):
            try:
                data = json.loads(_read(prof))
            except ValueError:
                continue  # malformed profile is check_template_profiles' job
            shipped = set(data.get("required", [])) | set(data.get("recommended", []))
            for src, refs in sorted(refs_by_file.items()):
                if src not in shipped:
                    continue
                for ref in sorted(refs):
                    if ref not in shipped:
                        failures.append(
                            f"profile {prof.name} ships {src} (references {ref}) "
                            f"but does not ship the template"
                        )

    return failures, warnings
```

`ALL_CHECKS` に登録（`("session-start hints", ...)` の直後）:

```python
    ("template references", check_template_references),
```

- [ ] **Step 2: RED を確認（検査が現実の欠陥を検出する）**

実行: `python3 scripts/check_reference_drift.py`
期待: FAIL ×6（`profile full.json ships .claude/skills/aegis-brainstorm/SKILL.md (references templates/BRAINSTORM-RECORD.template.md) but does not ship the template` など、6 テンプレート分）。これが本タスクの「失敗するテスト」。

- [ ] **Step 3: full.json を修正**

`templates/profiles/full.json` の `recommended` 配列末尾（`"docs/translation/mapping.md"` の後）に追加:

```json
    "templates/BRAINSTORM-RECORD.template.md",
    "templates/SPEC.template.md",
    "templates/TRANSLATION-MAPPING.template.md",
    "templates/RUNBOOK.template.md",
    "templates/MANUAL.template.md",
    "templates/UAT-RESULTS.template.md"
```

- [ ] **Step 4: GREEN を確認**

```bash
python3 scripts/check_reference_drift.py        # PASS
python3 scripts/run_eval.py --tier 1            # 全 validator PASS
bash bin/setup.sh --profile=full --target=/tmp/aegis-p1b-check --force \
  && ls /tmp/aegis-p1b-check/templates/         # 6 テンプレートが配布される
rm -rf /tmp/aegis-p1b-check
```

- [ ] **Step 5: コミット**

```bash
git add scripts/check_reference_drift.py templates/profiles/full.json
git commit -m "feat: ship skill-referenced templates in full profile + drift contract (OBS-012)"
```

---

### Task 9: scaffold smoke — install 先のテンプレート参照検証

F6 の教訓: repo 静的検査（Task 8）は repo しか見ない。install **出力**に対して同じ不変条件（installed skill が参照する templates/X が install 先に実在）を tier 2 で検査する。

**Files:**
- Modify: `scripts/eval_scaffold_smoke.py`（`verify_template_references` 新設＋`run_scaffold_test`/`run_full_hook_exec_test` へ連結）

- [ ] **Step 1: verifier を実装**

`verify_status_doctor` の直前に追加:

```python
TEMPLATE_REF_RE = re.compile(r"templates/[A-Za-z0-9._-]+\.template\.md")


def verify_template_references(target: Path, profile: str) -> tuple[bool, str]:
    """Installed skills must not reference templates that were not distributed
    (P1-B / OBS-012 — the F6 lesson: validate the INSTALL OUTPUT, not the repo)."""
    skills_dir = target / ".claude" / "skills"
    if not skills_dir.is_dir():
        return True, f"{profile}: no skills installed"
    missing: list[str] = []
    for sk in sorted(skills_dir.glob("*/SKILL.md")):
        text = sk.read_text(encoding="utf-8")
        for ref in sorted(set(TEMPLATE_REF_RE.findall(text))):
            if not (target / ref).is_file():
                missing.append(f"{sk.parent.name} -> {ref}")
    if missing:
        return False, (
            f"{profile}: installed skills reference undistributed templates: "
            + "; ".join(missing)
        )
    return True, f"{profile}: template refs resolve"
```

（ファイル冒頭に `import re` が無ければ追加。）

- [ ] **Step 2: 連結**

`run_scaffold_test` の `verify_settings_project_dir` 呼び出しの直後に:

```python
    # Template-reference validation in the install output (P1-B, OBS-012).
    ok, detail = verify_template_references(target, profile)
    if not ok:
        return "FAIL", detail
```

`run_full_hook_exec_test` の `verify_settings_project_dir` 呼び出しの直後にも同様に:

```python
    ok, detail = verify_template_references(target, "full")
    if not ok:
        return "FAIL", detail
```

- [ ] **Step 3: 検出能力を実証してから GREEN を確認**

```bash
# (a) 検出実証: 壊れた install を作って FAIL すること（一時的・手元のみ）
bash bin/setup.sh --profile=full --target=/tmp/aegis-p1b-smoke --force
rm /tmp/aegis-p1b-smoke/templates/MANUAL.template.md
python3 - << 'PY'
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("smoke", "scripts/eval_scaffold_smoke.py")
smoke = importlib.util.module_from_spec(spec); spec.loader.exec_module(smoke)
ok, detail = smoke.verify_template_references(Path("/tmp/aegis-p1b-smoke"), "full")
assert not ok and "MANUAL.template.md" in detail, detail
print("detection OK:", detail)
PY
rm -rf /tmp/aegis-p1b-smoke
# (b) 正常系: tier 2 全体
python3 scripts/run_eval.py --tier 2   # 全 profile PASS
```

- [ ] **Step 4: コミット**

```bash
git add scripts/eval_scaffold_smoke.py
git commit -m "feat: verify template refs resolve in install output (tier-2 smoke)"
```

---

### Task 10: hooks/lib/phase-skills.sh 新設 — phase→必読 skill の単一所有（OBS-004/020）

全 skill は `disable-model-invocation: true`（session-recovery 以外 `user-invocable: false`）なので、起動経路は「Read 指示の注入」だけ。phase→skill パスのマップを lib に単一所有させ、SessionStart（Task 11）と phase 遷移（Task 12)の両方が同じマップを使う。行動レビューで露呈したマップ欠落（review に aegis-review-gate が無い、ship/docs に user-manual/uat/maintenance が無い）もここで修正する。

`bin/setup.sh` の `copy_hooks` は `hooks/lib/*.sh` を全量 copy するため、新 lib は自動配布される（追加変更不要）。

**Files:**
- Create: `hooks/lib/phase-skills.sh`
- Test: `tests/test_phase_skills_lib.py`（新規）
- Mirror: `examples/minimal-project/hooks/lib/phase-skills.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_phase_skills_lib.py` を新規作成:

```python
#!/usr/bin/env python3
"""P1-A (OBS-004/020): hooks/lib/phase-skills.sh — phase→必読 skill マップの単一所有。

全 skill は disable-model-invocation:true のため、Read 指示の注入が唯一の起動経路。
このマップの欠落 = その skill は到達不能（行動レビューで実証）。
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "phase-skills.sh"


def paths_for(root: Path, phase: str, task_type: str = "feature") -> list[str]:
    script = (f'source "{LIB}"\n'
              f'aegis_phase_skill_paths "{root}" "{phase}" "{task_type}"\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError(f"lib failed: {r.stderr}")
    return [l for l in r.stdout.splitlines() if l]


def make_skills(root: Path, names: list[str]) -> None:
    for n in names:
        d = root / ".claude" / "skills" / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: {n}\n---\n", encoding="utf-8")


class TestPhaseSkillPaths(unittest.TestCase):
    def test_review_includes_review_gate_skill(self):
        # OBS-020 再発防止: review フェーズで aegis-review-gate が必読に入る
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["aegis-review-gate", "subagent-dev"])
            got = paths_for(root, "review")
            self.assertIn(".claude/skills/aegis-review-gate/SKILL.md", got)
            self.assertIn(".claude/skills/subagent-dev/SKILL.md", got)

    def test_ship_includes_back_half_skills(self):
        # 北極星後半 (OBS-031/032/034/035): ship/docs で配布系 skill が必読に入る
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            names = ["ship-and-docs", "user-manual", "uat", "maintenance", "docs-sync"]
            make_skills(root, names)
            got = paths_for(root, "ship")
            for n in names:
                self.assertIn(f".claude/skills/{n}/SKILL.md", got)

    def test_bugfix_brainstorm_routes_to_bug_diagnosis(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["bug-diagnosis", "tdd", "aegis-brainstorm"])
            got = paths_for(root, "brainstorm", "bugfix")
            self.assertIn(".claude/skills/bug-diagnosis/SKILL.md", got)
            self.assertNotIn(".claude/skills/aegis-brainstorm/SKILL.md", got)

    def test_existence_filter_for_partial_installs(self):
        # minimal/standard install: 配布されていない skill の Read 指示を出さない
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_skills(root, ["subagent-dev"])  # tdd は未配布
            got = paths_for(root, "implement")
            self.assertEqual(got, [".claude/skills/subagent-dev/SKILL.md"])

    def test_unknown_phase_emits_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(paths_for(Path(d), "nonsense"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_phase_skills_lib -v`
期待: 全件 ERROR（lib 不在で `source` 失敗）

- [ ] **Step 3: lib を実装**

`hooks/lib/phase-skills.sh` を新規作成:

```bash
#!/usr/bin/env bash
# Single owner of the phase -> required-skill map (P1-A, OBS-004/020/031/035).
#
# Every Aegis skill ships with disable-model-invocation:true and (except
# session-recovery) user-invocable:false, so the ONLY way a skill can boot is
# an explicit instruction to Read its file. This lib turns the current phase
# into that instruction. Consumers: hooks/session-start.sh (session entry) and
# hooks/post-status-audit.sh (phase transition).
#
# Contract: scripts/check_reference_drift.py (check_skill_reachability) parses
# the `names="..."` assignments below as reachability roots. Keep the literal
# `names="` syntax when editing.

# aegis_phase_skill_paths <root> <phase> [task_type]
# Prints one skill path per line. Existence-filtered: partial installs
# (minimal/standard profiles) must never be told to Read an undistributed file.
aegis_phase_skill_paths() {
  local root="$1" phase="$2" task_type="${3:-}"
  local names=""
  case "$phase" in
    onboard|discovery|requirements|scope|acceptance)
      names="client-workflow" ;;
    handover)
      names="client-workflow translation-mapping" ;;
    brainstorm)
      if [ "$task_type" = "bugfix" ] || [ "$task_type" = "hotfix" ]; then
        names="bug-diagnosis tdd"
      else
        names="aegis-brainstorm"
      fi ;;
    plan)
      names="subagent-dev" ;;
    implement)
      names="subagent-dev tdd" ;;
    review)
      names="aegis-review-gate subagent-dev" ;;
    qa)
      names="qa-verification" ;;
    security)
      names="aegis-security-gate" ;;
    deploy)
      names="deploy" ;;
    ship|docs)
      names="ship-and-docs user-manual uat maintenance docs-sync" ;;
    *)
      names="" ;;
  esac
  local n
  for n in $names; do
    if [ -f "${root}/.claude/skills/${n}/SKILL.md" ]; then
      printf '.claude/skills/%s/SKILL.md\n' "$n"
    fi
  done
}
```

- [ ] **Step 4: GREEN を確認**

実行: `python3 -m unittest tests.test_phase_skills_lib -v` → 全 PASS

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp hooks/lib/phase-skills.sh examples/minimal-project/hooks/lib/phase-skills.sh
git add hooks/lib/phase-skills.sh examples/minimal-project/hooks/lib/phase-skills.sh tests/test_phase_skills_lib.py
git commit -m "feat: add phase-skills lib — single owner of phase->skill Read map (P1-A)"
```

---

### Task 11: session-start.sh — phase-skills 委譲＋保守期トリガ

HINT の case 文から skill 名を取り除き（規律ヒントだけ残す）、必読 skill は lib 由来の **path-form Read 指示**として注入する。保守期（RUNBOOK 納品後）の maintenance skill 導線も追加（OBS-034: 保守フェーズに入る機械的トリガが無かった）。

**Files:**
- Modify: `hooks/session-start.sh:120-165`（HINT case）＋ source 追加
- Test: `tests/test_phase_skills_lib.py`（hook 統合テストを追記）
- Mirror: `examples/minimal-project/hooks/session-start.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_phase_skills_lib.py` に追加:

```python
class TestSessionStartInjection(unittest.TestCase):
    """session-start.sh が phase の必読 skill を path-form で注入する。"""

    def _scaffold(self, d: Path, phase: str, skills: list[str],
                  runbook: bool = False) -> Path:
        (d / "docs").mkdir(parents=True)
        (d / "docs" / "STATUS.md").write_text(
            f"---\nframework: aegis\nmode: Dev\nphase: {phase}\n"
            "task_type: feature\ntask_size: M\n"
            "gate_approvals:\n  review: pending\n"
            "current_refs:\n  review: null\n---\n", encoding="utf-8")
        make_skills(d, skills)
        if runbook:
            (d / "docs" / "handover").mkdir(parents=True)
            (d / "docs" / "handover" / "RUNBOOK.md").write_text("# r\n", encoding="utf-8")
        # hook 一式を実体 copy（session-start.sh は dirname 基準で lib を解決）
        import shutil
        shutil.copytree(ROOT / "hooks", d / "hooks")
        (d / "scripts").mkdir()
        (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
        return d

    def _run(self, root: Path) -> str:
        r = subprocess.run(
            ["bash", str(root / "hooks" / "session-start.sh")],
            capture_output=True, text=True, timeout=60,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})
        return r.stdout

    def test_review_phase_injects_read_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "review",
                                  ["aegis-review-gate", "subagent-dev"])
            out = self._run(root)
            self.assertIn(".claude/skills/aegis-review-gate/SKILL.md", out)

    def test_runbook_triggers_maintenance_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "docs", ["ship-and-docs", "maintenance"],
                                  runbook=True)
            out = self._run(root)
            self.assertIn(".claude/skills/maintenance/SKILL.md", out)
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_phase_skills_lib.TestSessionStartInjection -v`
期待: FAIL（現行 HINT は name-form のみで、path-form 文字列が出力に無い）
※ session-start.sh が STATUS の場所や環境変数を別解決している場合は、まず素の実行出力を見て fixture を合わせること（テストの本質は「path-form 注入の有無」）。

- [ ] **Step 3: 実装**

(a) `hooks/session-start.sh` の既存 `source .../emit.sh` 行の直後に追加:

```bash
source "${SCRIPT_DIR}/lib/phase-skills.sh"
```

（session-start.sh の lib 解決変数名が `SCRIPT_DIR` でない場合は emit.sh の source と同じ書式に合わせる。）

(b) HINT case（120-165 行）を次に置換（skill 名を除去し規律ヒントのみ残す）:

```bash
# Phase-aware rule hints. Required-skill paths come from lib/phase-skills.sh
# (single owner) — never name skills here (name-form hints proved dead in the
# 2026-06-12 behavioral review; drift enforces reachability separately).
HINT=""
case "$PHASE" in
  handover)
    HINT="mapping.md必須"
    ;;
  brainstorm)
    if [ "$TASK_TYPE" = "bugfix" ] || [ "$TASK_TYPE" = "hotfix" ]; then
      HINT="TDD必須 / brainstorm+plan=n/a"
    else
      HINT="TDD必須 / エビデンスなき完了なし"
    fi
    ;;
  plan)
    HINT="Boundary Map必須 / TDD必須"
    ;;
  implement)
    HINT="TDD必須: テストを先に書け / エビデンスなき完了なし"
    ;;
  review)
    HINT="Review Army: diff-scope分析でspecialist起動"
    ;;
  qa)
    HINT="エビデンスなき完了なし / 再現・検証を実行せよ"
    ;;
  security)
    HINT="エビデンスなき完了なし / 残留リスクを記録せよ"
    ;;
  deploy)
    HINT="Security Blockers確認必須 / 3回失敗=ゴールベースカウント"
    ;;
  ship|docs)
    HINT="LEARNINGS更新必須(confidence付き)"
    ;;
  onboard|discovery|requirements|scope|acceptance)
    HINT=""
    ;;
  *)
    if [ -n "$PHASE" ]; then
      HINT="unknown phase: ${PHASE} — docs/STATUS.md を確認"
    fi
    ;;
esac
if [ -n "$HINT" ]; then
  CONTEXT="${CONTEXT} | ${HINT}"
fi

# P1-A: explicit Read instruction for the phase's required skills — their ONLY
# boot path (all skills ship disable-model-invocation:true).
SKILL_PATHS=$(aegis_phase_skill_paths "$ROOT" "$PHASE" "$TASK_TYPE" | tr '\n' ' ')
SKILL_PATHS="${SKILL_PATHS% }"
if [ -n "$SKILL_PATHS" ]; then
  CONTEXT="${CONTEXT} | 必読skill(Readで読み込んで従う): ${SKILL_PATHS}"
fi

# Maintenance period (OBS-034): a delivered RUNBOOK means ops/incident
# questions may arrive regardless of phase.
if [ -f "${ROOT}/docs/handover/RUNBOOK.md" ] && [ -f "${ROOT}/.claude/skills/maintenance/SKILL.md" ]; then
  CONTEXT="${CONTEXT} | 保守期: 障害・問い合わせ対応は .claude/skills/maintenance/SKILL.md をRead"
fi
```

- [ ] **Step 4: GREEN を確認**

```bash
python3 -m unittest tests.test_phase_skills_lib -v   # 全 PASS
python3 -m unittest tests.test_hook_output_schema -v # SessionStart 出力 schema が無傷
```

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp hooks/session-start.sh examples/minimal-project/hooks/session-start.sh
git add hooks/session-start.sh examples/minimal-project/hooks/session-start.sh tests/test_phase_skills_lib.py
git commit -m "feat: inject path-form skill Read instructions at session start (P1-A)"
```

---

### Task 12: post-status-audit.sh — phase 遷移時の skill 注入

SessionStart 注入だけでは「セッション途中の phase 遷移」に届かない（行動レビューの欠落点はまさにここ: 遷移しても誰も skill を読まない）。正当な phase 遷移を検証した直後に、新 phase の必読 skill を additionalContext で注入する。

**スキーマ前提:** PostToolUse は top-level `decision:block` に加えて `hookSpecificOutput.additionalContext` を受け付ける。未対応クライアントでは無視される＝fail-safe（注入が消えるだけで block 系は無傷）。`emit.sh` のスキーマコメントにも追記する。

**Files:**
- Modify: `hooks/post-status-audit.sh:118-127`（終端ブロック）＋ source 追加
- Modify: `hooks/lib/emit.sh:20-21`（スキーマコメント）
- Test: `tests/test_phase_skill_injection.py`（新規）
- Mirror: `examples/minimal-project/hooks/post-status-audit.sh`、`examples/minimal-project/hooks/lib/emit.sh`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_phase_skill_injection.py` を新規作成:

```python
#!/usr/bin/env python3
"""P1-A: 正当な phase 遷移時、post-status-audit.sh が新 phase の必読 skill を
additionalContext で注入する（セッション途中の遷移は SessionStart 注入が届かない穴）。"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_TMPL = """---
framework: aegis
mode: Dev
phase: {phase}
task_type: feature
task_size: M
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
  plan: null
---
"""

SNAPSHOT = """gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
phase: brainstorm
mode: Dev
"""


class TestPhaseTransitionInjection(unittest.TestCase):
    def _scaffold(self, d: Path) -> Path:
        (d / "docs").mkdir()
        (d / "docs" / "STATUS.md").write_text(
            STATUS_TMPL.format(phase="plan"), encoding="utf-8")
        (d / ".claude").mkdir()
        (d / ".claude" / ".gate-snapshot").write_text(SNAPSHOT, encoding="utf-8")
        sk = d / ".claude" / "skills" / "subagent-dev"
        sk.mkdir(parents=True)
        (sk / "SKILL.md").write_text("---\nname: subagent-dev\n---\n", encoding="utf-8")
        shutil.copytree(ROOT / "hooks", d / "hooks")
        (d / "scripts").mkdir()
        (d / "scripts" / "check_status.py").symlink_to(ROOT / "scripts" / "check_status.py")
        return d

    def _run(self, root: Path) -> dict:
        stdin = json.dumps({"tool_name": "Edit",
                            "tool_input": {"file_path": str(root / "docs" / "STATUS.md")}})
        r = subprocess.run(
            ["bash", str(root / "hooks" / "post-status-audit.sh")],
            input=stdin, capture_output=True, text=True, timeout=60,
            env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_legit_transition_injects_new_phase_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            out = self._run(root)  # brainstorm -> plan（brainstorm approved 済 = 正当）
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn(".claude/skills/subagent-dev/SKILL.md", ctx)

    def test_no_transition_emits_allow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp))
            (root / ".claude" / ".gate-snapshot").write_text(
                SNAPSHOT.replace("phase: brainstorm", "phase: plan"), encoding="utf-8")
            out = self._run(root)
            self.assertEqual(out, {})  # 遷移なし → 素の allow


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: RED を確認**

実行: `python3 -m unittest tests.test_phase_skill_injection -v`
期待: `test_legit_transition_injects_new_phase_skills` が FAIL（現行は `{}` を返す）
※ hook の ROOT 解決は `dirname $0/..`（CLAUDE_PROJECT_DIR ではない）なので、fixture が hooks/ を実体 copy していれば temp root に解決される。落ち方が想定と違う場合は stdout/stderr を見て fixture を直すこと。

- [ ] **Step 3: 実装**

(a) `hooks/post-status-audit.sh` の `source "${SCRIPT_DIR}/lib/frontmatter.sh"` 行の直後に:

```bash
source "${SCRIPT_DIR}/lib/phase-skills.sh"
```

(b) 終端ブロック（snapshot 更新 3 行＝sed gate / grep phase / grep mode の後、`emit_allow` / `exit 0` を置換。TASK_TYPE 抽出は `frontmatter.sh` に既存 helper があればそれを優先使用）:

```bash
# Phase-skill injection (P1-A): a legitimate phase transition is the moment the
# next phase's skills must be loaded — SessionStart injection cannot reach a
# mid-session transition (2026-06-12 behavioral review). additionalContext is
# advisory: clients that ignore it lose only the hint, never the audit (fail-safe).
if [ -n "$OLD_PHASE" ] && [ -n "$NEW_PHASE" ] && [ "$OLD_PHASE" != "$NEW_PHASE" ]; then
  TASK_TYPE=$(grep -m1 "^task_type:" "$STATUS_FILE" | sed "s/^task_type:[[:space:]]*//" | sed 's/^"//;s/"$//' || true)
  SKILL_PATHS=$(aegis_phase_skill_paths "$ROOT" "$NEW_PHASE" "$TASK_TYPE" | tr '\n' ' ')
  SKILL_PATHS="${SKILL_PATHS% }"
  if [ -n "$SKILL_PATHS" ]; then
    emit_context PostToolUse "[phase-skills] phase=${NEW_PHASE}: 必読skill(Readで読み込んで従う): ${SKILL_PATHS}"
    exit 0
  fi
fi

emit_allow
exit 0
```

(c) `hooks/lib/emit.sh` のスキーマコメント（20-21 行）を更新:

```bash
#   PostToolUseFailure / SessionStart / PreCompact(allow) / UserPromptSubmit /
#   PostToolUse(advisory context): hookSpecificOutput.{hookEventName, additionalContext}
```

- [ ] **Step 4: GREEN を確認**

```bash
python3 -m unittest tests.test_phase_skill_injection -v  # 全 PASS
python3 -m unittest tests.test_hook_output_schema tests.test_evidence_hooks -v  # 既存 schema/hook 無傷
```

- [ ] **Step 5: ミラー同期してコミット**

```bash
cp hooks/post-status-audit.sh examples/minimal-project/hooks/post-status-audit.sh
cp hooks/lib/emit.sh examples/minimal-project/hooks/lib/emit.sh
git add hooks/post-status-audit.sh hooks/lib/emit.sh \
  examples/minimal-project/hooks/post-status-audit.sh examples/minimal-project/hooks/lib/emit.sh \
  tests/test_phase_skill_injection.py
git commit -m "feat: inject phase skills on legit phase transition (P1-A mid-session gap)"
```

---

### Task 13: skill 到達性 drift チェック（P1-A 再発封鎖・実装のみ、ALL_CHECKS 未登録）

**Files:**
- Modify: `scripts/check_reference_drift.py`（`check_skill_reachability` 追加。**ALL_CHECKS にはまだ登録しない**）
- Test: `tests/test_skill_reachability.py`（新規）

**狙い:** 「起動経路のない skill」を契約として禁止する。起動経路は 3 種:
(1) `hooks/lib/phase-skills.sh` の phase map（`names="..."` 文字列）、
(2) SKILL.md frontmatter の `user-invocable: true`、
(3) 制御ファイル（CLAUDE.md / .claude/{commands,agents,rules} / hooks / scripts）内の
path 形式参照 `.claude/skills/<name>/SKILL.md`。到達済み skill からの path 参照は edge として BFS 伝播する。

**コミット green 戦略:** 現時点の実 repo は browser-assist / integration-assist が name 形式参照のみで
FAIL する（真陽性）。そこで本 Task では関数とユニットテストのみ実装し、ALL_CHECKS 登録は
Task 14（正規化後）で行う。実 repo への RED 観測は直接実行で行い、登録は GREEN 化後に swap する。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_skill_reachability.py` を新規作成:

```python
"""skill 到達性 drift チェックのユニットテスト（P1-A 再発封鎖）。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_reference_drift.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_reference_drift", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


drift = _load()


def _make_skill(root: Path, name: str, body: str = "", user_invocable: bool = False) -> None:
    d = root / ".claude" / "skills" / name
    d.mkdir(parents=True)
    fm = ["---", f"name: {name}", "description: test skill"]
    if user_invocable:
        fm.append("user-invocable: true")
    fm.append("disable-model-invocation: true")
    fm.append("---")
    (d / "SKILL.md").write_text("\n".join(fm) + "\n" + body + "\n", encoding="utf-8")


def _make_phase_map(root: Path, names: str) -> None:
    lib = root / "hooks" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "phase-skills.sh").write_text(
        '#!/bin/bash\ncase "$phase" in\n  implement) names="%s" ;;\nesac\n' % names,
        encoding="utf-8",
    )


class TestSkillReachability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_unreachable_skill_fails(self):
        _make_skill(self.root, "orphan")
        failures, warnings = drift.check_skill_reachability(self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("orphan", failures[0])
        self.assertIn("no boot path", failures[0])
        self.assertEqual(warnings, [])

    def test_phase_map_skill_is_root(self):
        _make_skill(self.root, "tdd")
        _make_phase_map(self.root, "tdd")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_user_invocable_skill_is_root(self):
        _make_skill(self.root, "session-recovery", user_invocable=True)
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_control_file_path_ref_is_root(self):
        _make_skill(self.root, "deploy")
        cmd = self.root / ".claude" / "commands"
        cmd.mkdir(parents=True)
        (cmd / "ship.md").write_text(
            ".claude/skills/deploy/SKILL.md を Read して従う\n", encoding="utf-8"
        )
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_transitive_skill_edge_reaches(self):
        _make_skill(
            self.root, "parent",
            body="次に .claude/skills/child/SKILL.md を Read する",
            user_invocable=True,
        )
        _make_skill(self.root, "child")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(failures, [])

    def test_edge_from_unreachable_skill_does_not_rescue(self):
        _make_skill(self.root, "island-a", body=".claude/skills/island-b/SKILL.md")
        _make_skill(self.root, "island-b")
        failures, _ = drift.check_skill_reachability(self.root)
        self.assertEqual(len(failures), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python3 -m unittest tests.test_skill_reachability -v
```

期待: 全テストが `AttributeError: module 'check_reference_drift' has no attribute 'check_skill_reachability'` で FAIL。

- [ ] **Step 3: チェック本体を実装**

`scripts/check_reference_drift.py` の `check_session_start_hints` の直後に追加
（モジュール先頭の import に追加は不要。`re` / `Path` / `_read` は既存）:

```python
SKILL_PATH_RE = re.compile(r"\.claude/skills/([a-z][a-z0-9_-]*)/SKILL\.md")
PHASE_MAP_NAMES_RE = re.compile(r'names="([^"]*)"')
USER_INVOCABLE_RE = re.compile(r"^user-invocable:\s*true\b", re.M)


def _phase_map_skill_names(root: Path) -> set[str]:
    lib = root / "hooks" / "lib" / "phase-skills.sh"
    if not lib.is_file():
        return set()
    names: set[str] = set()
    for m in PHASE_MAP_NAMES_RE.finditer(_read(lib)):
        names.update(m.group(1).split())
    return names


def _control_file_skill_refs(root: Path) -> set[str]:
    sources: list[Path] = []
    claude_md = root / "CLAUDE.md"
    if claude_md.is_file():
        sources.append(claude_md)
    for sub in ("commands", "agents", "rules"):
        base = root / ".claude" / sub
        if base.is_dir():
            sources.extend(p for p in sorted(base.rglob("*.md")) if p.is_file())
    for sub, exts in (("hooks", (".sh",)), ("scripts", (".sh", ".py"))):
        base = root / sub
        if base.is_dir():
            sources.extend(
                p for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in exts
            )
    refs: set[str] = set()
    for path in sources:
        refs.update(SKILL_PATH_RE.findall(_read(path)))
    return refs


def check_skill_reachability(root: Path) -> tuple[list[str], list[str]]:
    """#8: every skill must have a boot path (phase map / user-invocable / path ref)"""
    failures: list[str] = []
    warnings: list[str] = []

    skills_dir = root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return failures, warnings

    skills: dict[str, Path] = {}
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if skill_md.is_file():
            skills[entry.name] = skill_md

    roots = _phase_map_skill_names(root) | _control_file_skill_refs(root)
    for name, skill_md in skills.items():
        if USER_INVOCABLE_RE.search(_read(skill_md)):
            roots.add(name)

    reachable: set[str] = set()
    queue = [name for name in sorted(roots) if name in skills]
    while queue:
        name = queue.pop()
        if name in reachable:
            continue
        reachable.add(name)
        for target in SKILL_PATH_RE.findall(_read(skills[name])):
            if target in skills and target not in reachable:
                queue.append(target)

    for name in sorted(skills):
        if name not in reachable:
            failures.append(
                "skill '%s' has no boot path (not in phase-skills.sh, not "
                "user-invocable, and no control file Reads "
                ".claude/skills/%s/SKILL.md)" % (name, name)
            )

    return failures, warnings
```

実装メモ（自己マッチ回避の確認済み事項）: `SKILL_PATH_RE` のソース文字列リテラルは
`skills/` 直後が `(` なので自分自身にマッチしない。failure メッセージの
`.claude/skills/%s/SKILL.md` も `%` が文字クラス外なのでマッチしない
（scripts/ は scan 対象だが自己マッチの v1.5.x 再演はない）。

- [ ] **Step 4: ユニットテスト GREEN を確認**

```bash
python3 -m unittest tests.test_skill_reachability -v  # 6 PASS
```

- [ ] **Step 5: 実 repo への RED 観測（システムレベル TDD・登録前の真陽性確認）**

```bash
python3 -c "
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location('d', 'scripts/check_reference_drift.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f, w = m.check_skill_reachability(Path('.'))
print('\n'.join(f) or 'CLEAN')
"
```

期待: `browser-assist` と `integration-assist` の 2 件が "no boot path" で列挙される
（Task 11/12 完了時点で phase map が 15 skill、user-invocable が session-recovery を
カバーするが、この 2 つは name 形式参照しかないため）。これが Task 14 正規化の RED。
もし他の skill も列挙された場合は Task 14 の正規化対象に追加する（チェック側は変えない）。

- [ ] **Step 6: コミット（ALL_CHECKS 未登録なので tier1 は green のまま）**

```bash
python3 scripts/check_reference_drift.py  # 既存チェックのみ・PASS 確認
git add scripts/check_reference_drift.py tests/test_skill_reachability.py
git commit -m "feat: add skill reachability check (unregistered until refs normalized)"
```

---

### Task 14: skill 参照の path 形式正規化 ＋ 到達性チェックの ALL_CHECKS 登録

**Files:**
- Modify: `.claude/skills/ship-and-docs/SKILL.md:59,66,74,88`
- Modify: `.claude/skills/uat/SKILL.md:28,37`
- Modify: `.claude/skills/user-manual/SKILL.md:38,50`
- Modify: `.claude/skills/maintenance/SKILL.md:34`
- Modify: `.claude/skills/qa-verification/SKILL.md:74`
- Modify: `.claude/rules/routing.md:16`
- Modify: `.claude/agents/integration-specialist.md:27-28`（＋intro に integration-assist path 参照を新設）
- Modify: `.claude/agents/qa-browser.md:44`
- Modify: `scripts/check_status.py:874`（`:883` は Task 6 で置換済みのため対象外）
- Modify: `scripts/check_reference_drift.py`（`check_session_start_hints` 削除・ALL_CHECKS swap）
- Mirror: `examples/minimal-project/` の同名ファイル全部（check_reference_drift.py はミラー対象外）

**狙い:** name 形式参照（モデルが Read できない）を path 形式（Read 可能な唯一の起動形）へ正規化し、
Task 13 の到達性チェックを GREEN 化したうえで ALL_CHECKS に登録する。
RED は Task 13 Step 5 の実 repo 観測（browser-assist / integration-assist ×2 件）。

- [ ] **Step 1: skill→skill の name 形式 7 箇所を path 形式に置換**

各行の before → after（Edit ツールで正確に置換）:

`.claude/skills/ship-and-docs/SKILL.md`:
```
59: `user-manual` skill を読み、              → `.claude/skills/user-manual/SKILL.md` を Read し、
66: `maintenance` skill（Part A）を読み、      → `.claude/skills/maintenance/SKILL.md`（Part A）を Read し、
74: `uat` skill を読み、                      → `.claude/skills/uat/SKILL.md` を Read し、
88: まず `docs-sync` skill を読み、            → まず `.claude/skills/docs-sync/SKILL.md` を Read し、
```
（66 行は grill-plan A 🔴-1 で検出した脱落分。phase map で maintenance は root 化されるため
到達性チェックは通るが、ship-and-docs 内部からの起動誘導が Read 可能な path 形式にならず
P1-A が部分残存するため必須。）

`.claude/skills/uat/SKILL.md:37` / `.claude/skills/user-manual/SKILL.md:50` /
`.claude/skills/maintenance/SKILL.md:34`（3 ファイル同形）:
```
`docs-sync` skill を読み、 → `.claude/skills/docs-sync/SKILL.md` を Read し、
```

- [ ] **Step 2: browser-assist 参照 5 箇所に path を併記**

`.claude/rules/routing.md:16`:
```
before: `browser-assist` skill is available to any agent needing browser automation.
after:  `browser-assist` skill (`.claude/skills/browser-assist/SKILL.md`) is available to any agent needing browser automation.
```

`.claude/skills/qa-verification/SKILL.md:74`:
```
before: qa-browser は browser-assist スキルを使用。
after:  qa-browser は browser-assist スキル（`.claude/skills/browser-assist/SKILL.md`）を使用。
```

`.claude/skills/uat/SKILL.md:28`:
```
before: UI は `browser-assist`/`qa-browser` で実画面を確認、
after:  UI は `browser-assist`（`.claude/skills/browser-assist/SKILL.md`）/`qa-browser` で実画面を確認、
```

`.claude/skills/user-manual/SKILL.md:38`:
```
before: `browser-assist`（または `qa-browser`）で
after:  `browser-assist`（`.claude/skills/browser-assist/SKILL.md`。または `qa-browser`）で
```

`.claude/agents/qa-browser.md:44`:
```
before: 1. Check if `$B` is available (browser-assist skill resolution logic).
after:  1. Check if `$B` is available (browser-assist skill resolution logic; see `.claude/skills/browser-assist/SKILL.md`).
```

- [ ] **Step 3: integration-specialist.md に path 参照を導入**

`.claude/agents/integration-specialist.md:26-29` の intro 段落:
```
before:
Handles external service integration with minimal user effort. Uses
browser-assist skill for browser automation (gstack `$B` or Playwright MCP
fallback), with guided text instructions when neither is available.

after:
Handles external service integration with minimal user effort. Read
`.claude/skills/integration-assist/SKILL.md` for the integration procedure
before starting. Uses browser-assist skill
(`.claude/skills/browser-assist/SKILL.md`) for browser automation (gstack `$B`
or Playwright MCP fallback), with guided text instructions when neither is
available.
```

- [ ] **Step 4: check_status.py の uat hint を path 形式に**

`scripts/check_status.py:874`:
```python
# before
            print("       → uat skill を使用")
# after
            print("       → .claude/skills/uat/SKILL.md を Read して UAT を実施")
```

- [ ] **Step 5: GREEN 観測（Task 13 Step 5 と同じコマンド）**

```bash
python3 -c "
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location('d', 'scripts/check_reference_drift.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
f, w = m.check_skill_reachability(Path('.'))
print('\n'.join(f) or 'CLEAN')
"
```

期待: `CLEAN`（browser-assist は routing.md＋skill 3 本＋agent 2 本、integration-assist は
integration-specialist.md の path 参照で root 化）。

- [ ] **Step 6: check_session_start_hints を削除し ALL_CHECKS を swap**

`scripts/check_reference_drift.py`:
(a) `check_session_start_hints` 関数（約 291-316 行）を丸ごと削除
（Task 11 で session-start.sh の HINT から skill 名が消えるため空振りチェック化している。
外部参照ゼロは grep 確認済み）。
(b) ALL_CHECKS の entry を置換:
```python
# before
    ("session-start hints", check_session_start_hints),
# after
    ("skill reachability", check_skill_reachability),
```

- [ ] **Step 7: tier0/tier1 GREEN を確認**

```bash
python3 -m unittest discover tests/ 2>&1 | tail -3   # 全 PASS
python3 scripts/check_reference_drift.py             # PASS（skill reachability 含む）
python3 scripts/run_eval.py --tier 1                 # PASS
```

- [ ] **Step 8: ミラー同期してコミット**

```bash
for f in \
  .claude/skills/ship-and-docs/SKILL.md \
  .claude/skills/uat/SKILL.md \
  .claude/skills/user-manual/SKILL.md \
  .claude/skills/maintenance/SKILL.md \
  .claude/skills/qa-verification/SKILL.md \
  .claude/rules/routing.md \
  .claude/agents/integration-specialist.md \
  .claude/agents/qa-browser.md \
  scripts/check_status.py; do
  cp "$f" "examples/minimal-project/$f"
done
python3 -m unittest tests.test_mirror_identity -v   # PASS
git add .claude examples/minimal-project scripts/check_status.py scripts/check_reference_drift.py
git commit -m "feat: normalize skill refs to path form and register reachability check (P1-A)"
```

---

### Task 15: smoke への到達性検査統合 ＋ 版数 1.6.0 ＋ 最終検証

**Files:**
- Modify: `scripts/eval_scaffold_smoke.py`（verify_skill_reachability 追加・2 経路に配線）
- Modify: `scripts/check_framework_contract.py:17`（`FRAMEWORK_VERSION = "1.6.0"`）
- Modify: `templates/STATUS.template.md:3`（`framework_version: "1.6.0"`）

**狙い:** F6 級（install 先の死角）の再発封鎖。framework repo が GREEN でも、profile が
「skill は配るが起動経路ファイルを配らない」構成なら install 先で到達性が死ぬ。
smoke で install 出力そのものに check_skill_reachability を実行して契約化する。

- [ ] **Step 1: verify_skill_reachability を実装**

`scripts/eval_scaffold_smoke.py` の既存 import 行（32 行目）を拡張:

```python
from check_reference_drift import MIRROR_ALLOWLIST, check_skill_reachability  # noqa: E402
```

`verify_settings_project_dir` の直後に追加:

```python
def verify_skill_reachability(target: Path, profile: str) -> tuple[bool, str]:
    """Installed skills must each have a boot path inside the install target."""
    failures, _warnings = check_skill_reachability(target)
    if failures:
        return False, (
            f"skill reachability failed in {profile} install: "
            + "; ".join(failures)
        )
    return True, ""
```

`run_scaffold_test` と `run_full_hook_exec_test` の両方で、
`verify_settings_project_dir` 呼び出しの直後に配線:

```python
    # Skill boot-path validation at the install target (P1-A, F6-class).
    ok, detail = verify_skill_reachability(target, profile)
    if not ok:
        return "FAIL", detail
```

- [ ] **Step 2: 検出力の実証（壊した install で RED を観測）**

```bash
rm -rf /tmp/aegis-reach-poc && bash bin/setup.sh --profile full --target /tmp/aegis-reach-poc
rm /tmp/aegis-reach-poc/.claude/agents/integration-specialist.md   # integration-assist の唯一の root を破壊
python3 -c "
from pathlib import Path
import sys; sys.path.insert(0, 'scripts')
from check_reference_drift import check_skill_reachability
f, _ = check_skill_reachability(Path('/tmp/aegis-reach-poc'))
print('\n'.join(f) or 'CLEAN')
"
```

期待: `skill 'integration-assist' has no boot path ...` の 1 件（検出力の実証＝RED 相当）。
CLEAN が出た場合は verify が機能していないので配線を見直す。

- [ ] **Step 3: tier2 GREEN を確認**

```bash
python3 scripts/run_eval.py --tier 2
```

期待: 全 profile PASS。もし特定 profile が reachability で FAIL したら、
**チェックを緩めず** `templates/profiles/<profile>.json` に起動経路ファイル
（routing.md / agents / phase-skills.sh を含む hooks 等）を追加して解消する。

- [ ] **Step 4: 版数を 1.6.0 に（minor: 機能追加＝phase 注入・card push・ゲート検査強化）**

```bash
grep -rn '"1\.5\.2"' scripts templates examples *.md 2>/dev/null
```

で全 owner を列挙し更新する。既知の owner は 4 つ（grill-plan A/B で実測確認済み）:
1. `scripts/check_framework_contract.py:17`（`FRAMEWORK_VERSION`）
2. `templates/STATUS.template.md:3`
3. `examples/minimal-project/docs/STATUS.md:3` — **contract 検査
   （check_framework_contract.py の example STATUS version 一致要求）があるため更新必須**
4. `docs/STATUS.md:3` — Aegis 自身の STATUS（iteration 締めの STATUS 更新と同時でよい）

他に出たら同様に更新。Edit で置換:

```python
FRAMEWORK_VERSION = "1.6.0"
```
```yaml
framework_version: "1.6.0"
```

- [ ] **Step 5: 最終検証（全 tier ＋ strict）**

```bash
python3 scripts/run_eval.py --tier 0 && \
python3 scripts/run_eval.py --tier 1 && \
python3 scripts/run_eval.py --tier 2 && \
python3 scripts/run_eval.py --tier 3
python3 scripts/check_status.py --root . --strict
python3 scripts/check_reference_drift.py
python3 -m unittest discover tests/ 2>&1 | tail -3
```

期待: 全 PASS。テスト総数は 479 から増加（新規: phase-skills lib / 注入 / reachability /
judge push / vendor / decode / client gate 系）。

- [ ] **Step 6: コミット**

```bash
git add scripts/eval_scaffold_smoke.py scripts/check_framework_contract.py templates/STATUS.template.md
git commit -m "feat: verify skill reachability at install targets; bump to 1.6.0"
```

---

## 残余リスク（受容・記録対象）

実装後の security ゲート証跡（`docs/qa-reports/v160-security.md` 相当）に以下を記録する:

1. **vendor 除外による scan 縮小**: Task 1 の vendor 除外で、vendored コード内の stub/secret は
   drill/judge の走査対象外になる。補償: judge card は advisory 層（deny 層ではない）であり、
   秘密情報の書込時点では `check-secrets.sh` hook（deny 系・未変更）が独立に効く。
   また `dist`/`build`/`out`/`coverage` セグメントは深さ問わず除外されるため、
   `src/dist/` のような正規ソースのディレクトリ名衝突も drill スコープから外れる
   （grill-plan B 🟡-1。境界はテストでピン留め済み・false-OK 方向＝mutant 未設置に留まり
   green 偽装にはならない）。
2. **PostToolUse additionalContext のクライアント依存**: Task 12 の phase 遷移注入は
   additionalContext を解さない古いクライアントでは無視される。fail-safe（注入が消えるだけで
   deny/block 系は不変）。SessionStart 注入（Task 11）が冗長カバーする。
3. **JUDGE_GATES の二重定義**: `update-gate.sh`（bash）と `check_status.py` の判定対象ゲートが
   別々に列挙される。drift はこれを検査しない。両所にクロス参照コメントを置くこと（Task 4 Step 3）。
4. **same-turn ack の LLM 層残余**: gate.md の並び替え（Task 5）は手順であって強制ではない。
   モデルがカード提示を飛ばして --ack する経路は決定論では塞げない（card push＝Task 4 が
   transcript への決定論的提示で実質補償）。
5. **到達性チェックは静的・path 形式限定**: 動的に組み立てた path（変数展開）は edge として
   見えない。phase map root は `names="` パース契約（phase-skills.sh ヘッダコメントに明記、
   Task 10）で結合しており、書式変更時は両方を直すこと。
6. **template 参照チェックは `templates/*.template.md` 形のみ**: 別形式（相対 path 省略等）の
   参照は Task 8 の regex に掛からない。skill 側の参照書式を標準形に保つ運用前提。
7. **judge card の double-render**: /gate のプレビュー（Task 5）と承認時の再生成（Task 4 経由の
   pre-approve）でカードが同一 turn に 2 回 build される。評価系出力（git diff 等）が両者間で
   変化するとプレビューと push に差分が出うる（整合性ノイズ・低頻度）。push 側＝記録が正。
8. **phase-skills.sh 不在時は session-start.sh が source で死ぬ**: emit.sh / patterns.sh と同じ
   「lib 不在＝install 不全＝fail-closed」ポリシーに整合（意図的）。scaffold smoke の hook 実発火
   検査（既存）と copy_hooks の全量配布で install 経路は契約済み。
9. **制御ファイル内コメントの false-root**: 到達性チェック（Task 13）は hooks/scripts の
   コメント中の path 文字列も root として扱う（過剰許可方向のみ・過剰排除はない）。
   「制御ファイルに skill path を書く＝起動経路を宣言する」を規約とする。

## 完了基準

- [ ] P1-A: 全 18 skill に起動経路（phase map / user-invocable / path 参照）があり、drift＋smoke が契約化
- [ ] P1-B: 6 テンプレートが full profile で配布され、drift＋smoke が契約化
- [ ] P1-C: judge card がバイナリ混在 repo でクラッシュせず、承認時に transcript へ決定論 push される
- [ ] P1-D: client_ready_for_dev が 6 成果物を承認側＋完了側の両面で検査する
- [ ] 全 tier（0/1/2/3）＋ --strict ＋ drift ＋ mirror identity が PASS
- [ ] 版数 1.6.0、ミラー byte-identical
- [ ] grill-code（独立 2 本）実施 → 指摘対応 → 4 ゲート承認 → 証跡 v160-*.md → tag v1.6.0

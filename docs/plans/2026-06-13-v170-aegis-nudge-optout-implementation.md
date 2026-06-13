# AEGIS_NUDGE opt-out 実装計画（P2-a / v1.7.0）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** session-start の phase HINT 説教だけを `AEGIS_NUDGE=off` で抑制し（enforcement/state/boot-path/safety は全残し）、profile 連動（full=on / minimal・standard=off）を setup.sh の settings.local.json env 注入で実現する。

**Architecture:** session-start.sh の HINT 追記行を `[ "${AEGIS_NUDGE:-}" != "off" ]` で条件化（小文字 off のみ off、他は fail-safe で on）。setup.sh の `generate_settings()` が minimal/standard 生成時に `env.AEGIS_NUDGE=off` を注入。settings env→hook 伝播は Claude Code 公式仕様で実証済み。example は full プロファイルなので env 変更不要だが、session-start.sh 編集分は byte-identical ミラーへ同期。

**Tech Stack:** bash（hooks）, Python（setup.sh 内の埋め込み生成 + scaffold smoke + contract）, unittest。

設計書: `docs/plans/2026-06-13-aegis-nudge-optout-design.md`

---

## File Structure

- `hooks/session-start.sh` — HINT 追記を nudge ON 時のみに条件化（1 箇所）。
- `examples/minimal-project/hooks/session-start.sh` — 上記の byte-identical ミラー（drift 契約 `check_mirror_identity`）。
- `bin/setup.sh` — `generate_settings()` の埋め込み Python に minimal/standard 用 env 注入を追加。
- `tests/test_phase_skills_lib.py` — `TestSessionStartInjection` に nudge on/off/fail-safe テストを追加。
- `scripts/eval_scaffold_smoke.py` — `verify_settings_nudge_env()` を追加し `run_scaffold_test()` に登録。
- `CLAUDE.md` / `README.md` / `docs/architecture-overview.md` — opt-out と profile 既定を明記。
- 版数 4 箇所: `scripts/check_framework_contract.py`（`FRAMEWORK_VERSION`）, `templates/STATUS.template.md`, `examples/minimal-project/docs/STATUS.md`, `docs/STATUS.md`。

---

## Task 1: session-start.sh の HINT を AEGIS_NUDGE で条件化

**Files:**
- Test: `tests/test_phase_skills_lib.py`（`TestSessionStartInjection` クラスに追加 + `_run` を env 受け取りへ拡張）
- Modify: `hooks/session-start.sh:176-178`
- Mirror: `examples/minimal-project/hooks/session-start.sh`（byte-identical）

- [ ] **Step 1: `_run` を env 上書き対応に拡張**

`tests/test_phase_skills_lib.py` の `_run`（現 97-102 行）を、追加 env を受け取れる形へ置換する:

```python
    def _run(self, root: Path, extra_env: dict | None = None) -> str:
        env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(root)}
        if extra_env:
            env.update(extra_env)
        r = subprocess.run(
            ["bash", str(root / "hooks" / "session-start.sh")],
            capture_output=True, text=True, timeout=60,
            env=env)
        return r.stdout
```

既存の 2 テスト（`test_review_phase_injects_read_instruction` / `test_runbook_triggers_maintenance_hint`）は引数なし呼び出しのままで動く（`extra_env=None`）。

- [ ] **Step 2: nudge on/off/fail-safe の失敗テストを追加**

`TestSessionStartInjection` クラス末尾（`test_runbook_triggers_maintenance_hint` の後、116 行目の直後）に追加する:

```python
    # --- AEGIS_NUDGE opt-out (P2-a / v1.7.0) -------------------------------
    def test_nudge_default_injects_phase_hint(self):
        # 未設定（既定 on）: implement 期の HINT 説教が文脈に乗る
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            out = self._run(root)
            self.assertIn("TDD必須", out, "nudge on: HINT must be present")
            self.assertIn(".claude/skills/tdd/SKILL.md", out)

    def test_nudge_off_drops_hint_keeps_enforcement(self):
        # off: HINT 説教は消えるが、state/skill パス等の enforcement は残る
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            out = self._run(root, {"AEGIS_NUDGE": "off"})
            self.assertNotIn("TDD必須", out, "nudge off: HINT sermon must be gone")
            self.assertIn("phase=implement", out, "off must keep phase state")
            self.assertIn("必読skill", out, "off must keep skill boot path")
            self.assertIn(".claude/skills/tdd/SKILL.md", out)

    def test_nudge_non_exact_off_keeps_hint(self):
        # fail-safe: 小文字 off 以外（大文字/末尾空白/別語）は on のまま
        with tempfile.TemporaryDirectory() as tmp:
            root = self._scaffold(Path(tmp), "implement", ["tdd", "subagent-dev"])
            for value in ("OFF", "Off", "off ", "on", "1", "true"):
                with self.subTest(value=value):
                    out = self._run(root, {"AEGIS_NUDGE": value})
                    self.assertIn("TDD必須", out, f"{value!r} must keep HINT (fail-safe)")
```

- [ ] **Step 3: テストを実行して失敗を確認**

Run: `python3 -m unittest tests.test_phase_skills_lib.TestSessionStartInjection -v`
Expected: `test_nudge_off_drops_hint_keeps_enforcement` が FAIL（`AssertionError: nudge off: HINT sermon must be gone` — 現状 off でも HINT が出る）。他 2 つの新規テストは現状でも PASS しうる（既定 on のため）。少なくとも off テストが赤になること。

- [ ] **Step 4: session-start.sh の HINT 追記を条件化**

`hooks/session-start.sh` の現 176-178 行:

```bash
if [ -n "$HINT" ]; then
  CONTEXT="${CONTEXT} | ${HINT}"
fi
```

を次に置換する:

```bash
# AEGIS_NUDGE=off suppresses the phase HINT sermon (path-telling); gates,
# skill paths, blockers, and warnings stay (they are enforcement, not nudge).
# Lowercase "off" only — any other value keeps the nudge on (fail-safe = more guidance).
if [ -n "$HINT" ] && [ "${AEGIS_NUDGE:-}" != "off" ]; then
  CONTEXT="${CONTEXT} | ${HINT}"
fi
```

- [ ] **Step 5: テストを実行して緑を確認**

Run: `python3 -m unittest tests.test_phase_skills_lib.TestSessionStartInjection -v`
Expected: 5 テスト全 PASS（既存 2 + 新規 3）。

- [ ] **Step 6: example ミラーへ byte-identical 同期**

Run: `cp hooks/session-start.sh examples/minimal-project/hooks/session-start.sh`
検証: `diff hooks/session-start.sh examples/minimal-project/hooks/session-start.sh && echo IDENTICAL`
Expected: `IDENTICAL`（差分なし）。

- [ ] **Step 7: drift（ミラー identity）を確認**

Run: `python3 -m unittest tests.test_mirror_identity -v`
Expected: 全 PASS（session-start.sh の drift なし）。

- [ ] **Step 8: Commit**

```bash
git add hooks/session-start.sh examples/minimal-project/hooks/session-start.sh tests/test_phase_skills_lib.py
git commit -m "$(cat <<'EOF'
feat(session-start): gate phase HINT behind AEGIS_NUDGE (P2-a)

off で phase HINT 説教のみ抑制。gates/skill パス/blockers/各 warning は
無条件で残す。小文字 off のみ off、他は fail-safe で on。example ミラー同期。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: setup.sh の profile 連動 env 注入

**Files:**
- Test: `scripts/eval_scaffold_smoke.py`（`verify_settings_nudge_env()` 追加 + `run_scaffold_test()` へ登録）
- Modify: `bin/setup.sh`（`generate_settings()` 内の埋め込み Python、現 226-287 行）

- [ ] **Step 1: scaffold smoke に nudge-env 検査を追加（失敗テスト）**

`scripts/eval_scaffold_smoke.py` の `verify_settings_project_dir` 関数（現 242 行付近）の**直後**に新関数を追加する:

```python
def verify_settings_nudge_env(target: Path, profile: str) -> tuple[bool, str]:
    """profile 連動 nudge 既定 (P2-a): minimal/standard は env.AEGIS_NUDGE=off を
    既定で持ち、full は持たない（nudges on）。settings env→hook 伝播で効く。"""
    settings_path = target / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return True, f"{profile}: no settings.local.json (nothing to verify)"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    nudge = data.get("env", {}).get("AEGIS_NUDGE")
    if profile in ("minimal", "standard"):
        if nudge != "off":
            return False, f"{profile}: env.AEGIS_NUDGE expected 'off', got {nudge!r}"
        return True, f"{profile}: env.AEGIS_NUDGE=off"
    if nudge is not None:
        return False, f"full: env.AEGIS_NUDGE must be unset (on), got {nudge!r}"
    return True, "full: env.AEGIS_NUDGE unset (nudges on)"
```

次に `run_scaffold_test()`（現 325 行付近）の `verify_settings_project_dir` 呼び出しブロック（現 357-360 行付近）の**直後**に登録する:

```python
    # Profile-linked nudge default (P2-a).
    ok, detail = verify_settings_nudge_env(target, profile)
    if not ok:
        return "FAIL", detail
```

- [ ] **Step 2: scaffold smoke を実行して失敗を確認**

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: minimal と standard が FAIL（`env.AEGIS_NUDGE expected 'off', got None` — setup.sh がまだ注入していない）。full は PASS。

- [ ] **Step 3: setup.sh の埋め込み Python に env 注入を追加**

`bin/setup.sh` の `generate_settings()` 内、ユーザーキー保全ループ（現 279-282 行）:

```python
    for k, v in existing.items():
        if k == 'hooks':
            continue  # framework-owned, never preserve user mutations
        out[k] = v   # preserve permissions / env / future keys
```

の**直後**（`with open(target, 'w') as f:` の直前、現 283-284 行の間）に追加する:

```python

# P2-a (v1.7.0): minimal/standard default the phase-HINT nudge OFF via settings
# env (settings env propagates to hook process env). full leaves it unset = on.
# Never remove a user-set value for full; only ADD the default for lean profiles.
profile_name = profile.get('name', '')
if profile_name in ('minimal', 'standard'):
    out.setdefault('env', {})['AEGIS_NUDGE'] = 'off'
```

（`profile` 変数は同ブロック現 234 行 `profile = json.load(f)` で既にロード済み。`profile.get('name')` は profiles/*.json の `"name"` フィールドを読む。）

- [ ] **Step 4: scaffold smoke を実行して緑を確認**

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: minimal / standard / full / full (hooks) すべて PASS。

- [ ] **Step 5: 手動スポット確認（minimal 生成物の env）**

```bash
TMP=$(mktemp -d) && bash bin/setup.sh --profile=minimal --target="$TMP" >/dev/null 2>&1 && python3 -c "import json;print(json.load(open('$TMP/.claude/settings.local.json')).get('env'))" && rm -rf "$TMP"
```
Expected: `{'AEGIS_NUDGE': 'off'}`

```bash
TMP=$(mktemp -d) && bash bin/setup.sh --profile=full --target="$TMP" >/dev/null 2>&1 && python3 -c "import json;print(json.load(open('$TMP/.claude/settings.local.json')).get('env'))" && rm -rf "$TMP"
```
Expected: `None`

- [ ] **Step 6: Commit**

```bash
git add bin/setup.sh scripts/eval_scaffold_smoke.py
git commit -m "$(cat <<'EOF'
feat(setup): profile-linked AEGIS_NUDGE default (minimal/standard=off)

generate_settings が minimal/standard の settings.local.json に
env.AEGIS_NUDGE=off を注入（full は未設定=on）。既存 env キーは保全。
scaffold smoke に verify_settings_nudge_env を追加し全 profile で検証。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: ドキュメント整備

**Files:**
- Modify: `CLAUDE.md`（Operating Contract の TDD backstop 行）
- Modify: `README.md`（profiles 節）
- Modify: `docs/architecture-overview.md`（session-start.sh 行）

- [ ] **Step 1: CLAUDE.md に opt-out 行を追記**

`CLAUDE.md` の現行 L17:

```
- Hook enforcement level is set at install via `bin/setup.sh --profile` — TDD backstop is on in `full`, off in `minimal`/`standard`. In `full`, `AEGIS_TDD_MODE=off` disables it for the session (session-start warns).
```

の直後に新しい箇条書きを追加する:

```
- Phase HINT nudges follow the profile: `full` shows them, `minimal`/`standard` default `AEGIS_NUDGE=off` (set in settings env at install). `AEGIS_NUDGE=off` suppresses the phase-HINT sermon for the session; gates, skill boot-paths, blockers, and warnings are unaffected. Lowercase `off` only; session-start does NOT warn (off is benign).
```

- [ ] **Step 2: README.md の profiles 節に追記**

`README.md` の TDD backstop を説明している段落（現 L106 付近、`TDD backstop strictness follows the profile...` の段落）の直後に追加する:

```
Phase HINT nudges (the per-phase reminder sermon injected at session start) also follow the profile: `full` shows them; `minimal`/`standard` set `AEGIS_NUDGE=off` in the generated settings `env` so the sermon is suppressed by default. Set `AEGIS_NUDGE=off` yourself to silence it for a single session in any profile (lowercase `off` only). Only the phase HINT is removed — gates, skill boot-paths, blockers, failure-tracking, and safety warnings always remain. Unlike `AEGIS_TDD_MODE`, session-start does not print a warning when nudges are off (it is benign).
```

- [ ] **Step 3: architecture-overview.md の session-start 行に注記**

`docs/architecture-overview.md` を開き、`session-start.sh` を説明している表行または項目を特定する:

Run: `grep -n "session-start" docs/architecture-overview.md`

該当行（session-start.sh の責務説明）に「phase HINT は `AEGIS_NUDGE=off`（minimal/standard 既定）で抑制可。enforcement/state/skill パスは無条件」の趣旨を1文追記する。表形式なら説明セル末尾に ` HINT は AEGIS_NUDGE=off で抑制可（minimal/standard 既定 off）。` を足す。

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md docs/architecture-overview.md
git commit -m "$(cat <<'EOF'
docs(P2-a): document AEGIS_NUDGE opt-out and profile-linked default

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: framework_version を 1.7.0 へ（4 箇所同期）

**背景:** v1.6.3 commit は `docs/STATUS.md` のみ bump し、scaffold stamp（`FRAMEWORK_VERSION` 定数 / template / example）は 1.6.2 のまま残った。v1.7.0 で 4 箇所すべてを揃えて split を解消する。contract は「template == 定数 == example」を強制する。

**Files:**
- Modify: `scripts/check_framework_contract.py:17`（`FRAMEWORK_VERSION = "1.6.2"`）
- Modify: `templates/STATUS.template.md:3`（`framework_version: "1.6.2"`）
- Modify: `examples/minimal-project/docs/STATUS.md`（`framework_version: "1.6.2"`）
- Modify: `docs/STATUS.md:3`（`framework_version: "1.6.3"`）

- [ ] **Step 1: 4 箇所の現在値を確認**

Run: `grep -rn 'framework_version\|FRAMEWORK_VERSION' scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md`
Expected: 定数/template/example=`1.6.2`、docs/STATUS.md=`1.6.3`。

- [ ] **Step 2: 4 箇所を 1.7.0 に更新**

- `scripts/check_framework_contract.py:17`: `FRAMEWORK_VERSION = "1.6.2"` → `FRAMEWORK_VERSION = "1.7.0"`
- `templates/STATUS.template.md:3`: `framework_version: "1.6.2"` → `framework_version: "1.7.0"`
- `examples/minimal-project/docs/STATUS.md`: `framework_version: "1.6.2"` → `framework_version: "1.7.0"`
- `docs/STATUS.md:3`: `framework_version: "1.6.3"` → `framework_version: "1.7.0"`

- [ ] **Step 3: contract を全 profile で実行して版数同期を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full --root=. && python3 scripts/check_framework_contract.py --profile=standard --root=. && python3 scripts/check_framework_contract.py --profile=minimal --root=.`
Expected: 3 profile すべて `PASS`（版数ミスマッチ failure なし）。

- [ ] **Step 4: Commit**

```bash
git add scripts/check_framework_contract.py templates/STATUS.template.md examples/minimal-project/docs/STATUS.md docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore: bump framework_version to 1.7.0 (P2-a AEGIS_NUDGE opt-out)

scaffold stamp（定数/template/example）は 1.6.2 残置だったため
docs/STATUS.md(1.6.3) と合わせて 4 箇所を 1.7.0 に統一。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 全体検証ゲート

**Files:** なし（検証のみ）

- [ ] **Step 1: 全テスト**

Run: `python3 -m unittest discover tests -v 2>&1 | tail -20`
Expected: `OK`（既存 705 + 新規 3 = 708 前後、失敗 0）。

- [ ] **Step 2: contract（全 profile）**

Run: `for p in minimal standard full; do python3 scripts/check_framework_contract.py --profile=$p --root=. || echo "FAIL:$p"; done`
Expected: 各 `PASS`、`FAIL:` 出力なし。

- [ ] **Step 3: drift**

Run: `python3 scripts/check_reference_drift.py 2>&1 | tail -5`
Expected: drift なし（exit 0 / PASS）。

- [ ] **Step 4: scaffold smoke**

Run: `python3 scripts/eval_scaffold_smoke.py`
Expected: 全 profile + full(hooks) PASS。

- [ ] **Step 5: 既存 PoC（redteam）が緑のまま**

Run: `bash tests/poc/v162-redteam-rerun.sh; bash tests/poc/v163-redteam.sh`
Expected: 18/18 + 5/5 PASS（nudge 変更は enforcement に無影響）。

- [ ] **Step 6: docs/STATUS.md を本タスクの結果で更新**

`docs/STATUS.md` の `phase` / `next_action` / `session_history` を v1.7.0 着地内容へ更新（session_history は最新3件維持）。gate_approvals の該当ゲート（review/qa は本変更の検証フローに従い更新）。

- [ ] **Step 7: 最終コミット**

```bash
git add docs/STATUS.md
git commit -m "$(cat <<'EOF'
chore(STATUS): record v1.7.0 P2-a AEGIS_NUDGE opt-out landing

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review メモ

- **Spec coverage:** 設計 §2(機構)=Task1,2 / §3(境界)=Task1 Step4+テスト / §4(advisory 無)=Task1 で警告行を足さない・README に明記 / §5(テスト)=Task1,2 / §6(docs/版数)=Task3,4 / §7(検証)=Task5。example ミラー=Task1 Step6-7。全項目に対応タスクあり。
- **Type consistency:** env 名 `AEGIS_NUDGE`、値 `off`（小文字）、bash 判定 `[ "${AEGIS_NUDGE:-}" != "off" ]`、Python 関数 `verify_settings_nudge_env`、profile 名 `minimal`/`standard`/`full` を全タスク一貫。版数 old `1.6.2`(stamp)/`1.6.3`(STATUS) → new `1.7.0` 一貫。
- **No placeholders:** 各 step に実コード/実コマンド/期待出力を記載。
- **未確定で実装時に実測する点:** ① shell env と settings env の優先順位（Claude Code 未文書化）→ Task3 docs 記述前に実測し README 表現を確定。② docs/architecture-overview.md の session-start 行の正確な形（Task3 Step3 で grep して特定）。
- **grill-plan 重点:** example が full プロファイル＝env 変更不要という前提の再確認（誤れば minimal-project の settings.json 修正が漏れる）。Task1 の "TDD必須" 文字列が off 出力の他箇所に出ないこと（learnings 未生成前提）。

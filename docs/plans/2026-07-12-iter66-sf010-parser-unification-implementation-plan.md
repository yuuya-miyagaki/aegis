# 実装計画: SF-010 封鎖＋frontmatter 読取意味論統一（iter66）
<!-- 正本: subagent-dev skill -->

> **For agentic workers:** REQUIRED SUB-SKILL: subagent-dev（フレッシュ subagent per task＋2段レビュー）。各ステップは checkbox（`- [ ]`）で追跡。

## 目的

- この変更で達成すること: 「**frontmatter 内の最初の値**」という単一読取意味論を bash/python 全読点に適用し、SF-010（task_size empty-baseline raw-Edit×migration-grace 穴）と同根のパーサ drift 3 件（F-1/F-2/重複キー乖離）を一括根治。migration-grace は「snapshot に `task_type:` 行が無い真の旧フォーマット」限定に絞る。

## 入力

- 参照要件: なし（framework 反復・動機正本 docs/security-followups.md SF-010）
- 参照設計: docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（ローカル bash/python フレームワーク）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ対象なし・bash 3.2/macOS 既定互換を維持）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

main 直コミット・per-task commit（iter65 踏襲）。push は全ゲート後にユーザー指示で。

## グローバル制約（全タスクに適用）

- hook は pure-bash 維持（python3 委譲禁止＝fail-open 退行・iter65 却下済み）。
- bash 3.2（macOS 既定）互換: `declare -A` 禁止・`BASH_SOURCE`/`declare -F` は可。
- 読取契約不変: absent/malformed → 空 stdout＋rc0（`frontmatter_value`/`gate_value`）。
- 全変更は fail-closed 方向のみ（allow が増える変更ゼロ）。
- 各タスク TDD RED-first: テスト→FAIL 確認→最小実装→PASS→full suite→コミット。
- full suite 基準: 1096 passed / 2 skipped。既知 flaky `test_update_gate_lock` は再実行で切り分け（回帰外・full-review R10 test#8）。
- クォート正規化の契約はダブルクォートのみ（STATUS 実態）。シングルクォート値は契約外（YAGNI・parity fixture に含めない）。

## ファイル構造（変更マップ）

- 変更: `hooks/lib/frontmatter.sh`（`frontmatter_value` スコープ化・`gate_value` fallback 厳格化）— 読取意味論の単一ソース
- 変更: `hooks/lib/snapshot.sh`（`aegis_write_snapshot` を frontmatter スコープ生成へ・malformed 時は既存 snapshot 温存・task_size 欠落で regen が silent fail する潜在バグ修復）
- 変更: `hooks/post-status-audit.sh`（task field＋gate loop 両 tamper 判定の grace 絞り込み）
- 変更: `scripts/check_status.py`（`extract_scalar_value` 行順 first-match 化・`extract_approval_map` 先勝ち化）
- 変更: `hooks/check-gate.sh:258-266`（インライン scoped 読みを `frontmatter_value` 呼び出しへ dedup）
- テスト変更: `tests/test_frontmatter_lib.py`・`tests/test_snapshot_helper.py`・`tests/test_post_status_audit_task_tamper.py`・`tests/test_check_status_parsers.py`（新規）・`tests/test_parser_parity_driftguard.py`（新規）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 0 | STATUS 読点の全数台帳（enforcement/advisory/writer 分類・grill-plan 指摘②） | なし |
| Task 1 | `frontmatter_value`: `---` ファイルで frontmatter 内 first-match（新保証） | Task 0（対象読点の確定） |
| Task 2 | `gate_value`: `---` ファイルで本文 fallback しない（新保証） | Task 1 の predicate 実装様式 |
| Task 3 | snapshot 内容＝STATUS frontmatter 由来のみ・欠落キーで regen 不失敗 | Task 1（`read_frontmatter`/`_section_filter` 流用） |
| Task 4 | audit: grace 絞り込み＝**task fields＋gate loop の両方**（grill-plan 指摘①） | Task 1（NEW 側 scoped 読み）・Task 3（baseline 清浄） |
| Task 5 | python 読取＝bash と同意味論（行順 first-match・先勝ち） | なし（独立） |
| Task 6 | check-gate の task_size 読み＝library 単一ソース | Task 1 |
| Task 7 | parity drift-guard（bash↔python 一致の機械ピン） | Task 1-6 全部 |

循環なし。Task 5 は独立だが parity（Task 7）が全体を束縛。

---

### Task 0: STATUS 読点の全数調査（census・grill-plan 指摘②反映）

**blockedBy:** なし | **モデル:** 親セッション（調査のみ・コード変更なし）
**意図:** 設計は「全読点の意味論統一」を主張する。主張の根拠として、STATUS.md を直接読む箇所を機械的に列挙し、enforcement（→本計画で library 経由化）／advisory（表示のみ・変換不要の理由記録）／authorized writer（書込側・対象外の理由記録）に分類した台帳を残す。

- [ ] **Step 1: census 実行**

Run: `grep -rnE '(grep|sed|awk).*(STATUS_FILE|STATUS\.md)' hooks/ scripts/*.sh | grep -v frontmatter.sh`

- [ ] **Step 2: 分類台帳の確認**（plan 作成時の事前実施結果。implement 時に再実行し、**新規 hit がないこと**を確認。増えていたら分類を追記してから進む）

| 読点 | 分類 | 処置 |
|------|------|------|
| `hooks/check-gate.sh:266`（task_size） | enforcement | Task 6 で library 化 |
| `hooks/post-status-audit.sh`（frontmatter_value/gate_value 経由） | enforcement | Task 1/2/4 で封鎖 |
| `hooks/lib/snapshot.sh:32-36`（生成） | enforcement baseline | Task 3 で封鎖 |
| `hooks/session-start.sh:68-71`（blockers） | advisory（警告表示のみ・gate 判定に不使用） | 変換不要・理由記録 |
| `hooks/session-start.sh:113-115`（failure_tracking） | advisory（同上） | 変換不要・理由記録 |
| `hooks/session-start.sh:132`（session_history） | advisory（同上） | 変換不要・理由記録 |
| `scripts/update-task.sh:128-136`（sed/awk 書換） | authorized writer（書込側） | 対象外。※sed は無アドレスで全 `^key:` 行を authorized 値に書換＝本文行も収束方向（緩和ではない）と記録 |
| `scripts/update-gate.sh:320`（sed 書換） | authorized writer | 対象外（同上） |

- [ ] **Step 3: 台帳を qa evidence 用に記録**（本表を implement 時の実行結果で確定し、review レポートから参照）

---

## タスク分解

---

### Task 1: `frontmatter_value` の library 級スコープ化（Fix ②）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 対象 `hooks/lib/frontmatter.sh` / テスト `tests/test_frontmatter_lib.py`
**意図:** `---` 開始ファイルでは frontmatter 内のみを first-match（本文 spoof 不可視）。`---` 開始だが未終端 → 空（fail-closed）。`---` 非開始（bare `.gate-snapshot`）→ 従来 whole-file。
**Interfaces:** Produces: `frontmatter_value <file> <key>` → 上記新保証・absent→空+rc0 不変。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_frontmatter_lib.py` の `TestFrontmatterValue` クラスに追記）

```python
    def test_body_spoof_line_invisible_in_frontmattered_file(self):
        # SF-010 class: --- ファイルでは本文の key: 行は読まれない
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text("---\nmode: Dev\n---\nbody\ntask_size: S\n",
                         encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "task_size")
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "")

    def test_frontmatter_first_match_wins_over_body(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text("---\ntask_size: M\n---\nbody\ntask_size: S\n",
                         encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "task_size")
            self.assertEqual(out.strip(), "M")

    def test_unterminated_frontmatter_value_empty_failclosed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text("---\ntask_size: S\nno close\n", encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "task_size")
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "")

    def test_bare_file_whole_file_read_preserved(self):
        # .gate-snapshot 形式（--- なし）は従来どおり
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("phase: implement\ntask_type: framework\n",
                         encoding="utf-8")
            rc, out = run_fn("frontmatter_value", str(p), "task_type")
            self.assertEqual(out.strip(), "framework")
```

- [ ] **Step 2: FAIL 確認**

Run: `python3 -m pytest tests/test_frontmatter_lib.py -k "spoof or unterminated_frontmatter_value or first_match_wins" -v`
Expected: FAIL（spoof で `S` が返る／unterminated で `S` が返る）。`bare_file_whole_file` は現行でも PASS（回帰ピン）。

- [ ] **Step 3: 最小実装**（`hooks/lib/frontmatter.sh` の `frontmatter_value` を置換。ヘッダコメントの契約説明も同期）

```bash
# frontmatter_value <file> <key>
#   stdout: top-level scalar value (surrounding double-quotes stripped).
#   Files starting with `---` are read WITHIN the frontmatter scope only
#   (first match; body lines are invisible — SF-010). `---` present but
#   unterminated -> empty (fail-closed). Bare frontmatter files
#   (.gate-snapshot, no ---) keep the whole-file read. Empty stdout + RC 0
#   when the file or key is absent (callers test -n/-z; unchanged contract).
frontmatter_value() {
  local file="$1" key="$2" src=""
  [ -f "$file" ] || return 0
  if [ "$(head -n1 "$file" 2>/dev/null)" = "---" ]; then
    src=$(read_frontmatter "$file") || src=""
  else
    src=$(cat "$file" 2>/dev/null) || src=""
  fi
  printf '%s\n' "$src" | grep -m1 "^${key}:" \
    | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

- [ ] **Step 4: PASS 確認**

Run: `python3 -m pytest tests/test_frontmatter_lib.py -v`
Expected: 全 PASS（既存含む）。

- [ ] **Step 5: full suite＋コミット**

Run: `python3 -m pytest tests/ -q` → Expected: 1096+4 passed / 2 skipped 相当（新規4本加算・回帰ゼロ）
`git add hooks/lib/frontmatter.sh tests/test_frontmatter_lib.py && git commit -m "fix(iter66): frontmatter_value を frontmatter スコープ化（Fix②・本文 spoof 不可視・未終端 fail-closed）"`

---

### Task 2: `gate_value` の本文 fallback 厳格化（Fix ④・F-2）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/lib/frontmatter.sh` / テスト `tests/test_frontmatter_lib.py`
**意図:** `raw_section` fallback を「`---` frontmatter を持たないファイル」限定に。`---` ありで gate_approvals 節なし → 空＝下流 not-approved（fail-closed）。
**Interfaces:** Produces: `gate_value <file> <gate>` → 新保証。bare snapshot の読取は不変。

- [ ] **Step 1: 失敗するテストを書く**（`TestGateValue` クラスに追記）

```python
    def test_body_gate_block_not_adopted_when_frontmattered(self):
        # F-2: frontmatter に節がなくても本文ブロックへ fallback しない
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "STATUS.md"
            p.write_text(
                "---\nmode: Dev\n---\nbody\n"
                "gate_approvals:\n  review: approved\n", encoding="utf-8")
            rc, out = run_fn("gate_value", str(p), "review")
            self.assertEqual(rc, 0)
            self.assertEqual(out.strip(), "")

    def test_bare_snapshot_gate_read_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("gate_approvals:\n  review: approved\nphase: qa\n",
                         encoding="utf-8")
            rc, out = run_fn("gate_value", str(p), "review")
            self.assertEqual(out.strip(), "approved")
```

- [ ] **Step 2: FAIL 確認**

Run: `python3 -m pytest tests/test_frontmatter_lib.py -k "body_gate_block or bare_snapshot_gate" -v`
Expected: `body_gate_block` FAIL（現行は `approved` が返る）／`bare_snapshot_gate` PASS（回帰ピン）。

- [ ] **Step 3: 最小実装**（`gate_value` を置換・ヘッダコメント同期）

```bash
# gate_value <file> <gate>
#   stdout: the value of `<gate>:` under the gate_approvals section.
#   Files starting with `---`: frontmatter_section ONLY (no body fallback —
#   F-2: a body gate_approvals block must never drive gate decisions).
#   Bare files (.gate-snapshot, no ---): raw_section as before. 2-space
#   anchor prevents substring matches. Empty stdout + RC 0 when absent.
gate_value() {
  local file="$1" gate="$2" src=""
  [ -f "$file" ] || return 0
  if [ "$(head -n1 "$file" 2>/dev/null)" = "---" ]; then
    src=$(frontmatter_section "$file" gate_approvals 2>/dev/null) || src=""
  else
    src=$(raw_section "$file" gate_approvals 2>/dev/null) || src=""
  fi
  printf '%s\n' "$src" | grep -m1 "  ${gate}:" \
    | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

- [ ] **Step 4: PASS 確認** → `python3 -m pytest tests/test_frontmatter_lib.py -v` 全 PASS
- [ ] **Step 5: full suite＋コミット**

`git add hooks/lib/frontmatter.sh tests/test_frontmatter_lib.py && git commit -m "fix(iter66): gate_value の本文 fallback を ---無しファイル限定に（Fix④・F-2 封鎖）"`

---

### Task 3: snapshot 生成の frontmatter スコープ化（Fix ③）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/lib/snapshot.sh` / テスト `tests/test_snapshot_helper.py`
**意図:** snapshot 内容を STATUS の frontmatter 由来のみに（baseline 毒込み封鎖）。malformed frontmatter → 既存 snapshot 温存（rc1・K-7 の非破壊原則）。**潜在バグ修復**: 現行は compound block の最終 `grep -m1 "^task_size:"` が rc1 だと `&&` 連鎖が切れ regen が silent fail（empty-baseline install で snapshot が更新されない）→ 欠落キーは単に行を出さず regen 自体は成功させる。
**Interfaces:** Produces: `aegis_write_snapshot <root>` → snapshot＝frontmatter 由来のみ・欠落キー耐性。Consumes: `read_frontmatter`/`_section_filter`（frontmatter.sh）。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_snapshot_helper.py` に追記。既存ハーネスの scratch 生成関数を流用し、無ければ同ファイル既存様式に合わせて `_scratch` 相当を書く）

```python
    def test_body_spoof_lines_excluded_from_snapshot(self):
        # 本文の task_size/gate_approvals 行が snapshot に混入しない
        status = ("---\nmode: Dev\nphase: plan\ntask_type: framework\n"
                  "gate_approvals:\n  review: pending\n---\n"
                  "body\ntask_size: S\ngate_approvals:\n  review: approved\n")
        with self._scratch(status) as root:
            self._run_write_snapshot(root)
            snap = (Path(root) / ".claude" / ".gate-snapshot").read_text()
            self.assertNotIn("task_size: S", snap)
            self.assertNotIn("review: approved", snap)
            self.assertIn("task_type: framework", snap)

    def test_absent_task_size_still_regenerates(self):
        # 潜在バグ修復: task_size 行なしでも regen は成功し task_type は記録される
        status = ("---\nmode: Dev\nphase: brainstorm\ntask_type: framework\n"
                  "gate_approvals:\n  review: pending\n---\nbody\n")
        with self._scratch(status) as root:
            rc = self._run_write_snapshot(root)
            self.assertEqual(rc, 0)
            snap = (Path(root) / ".claude" / ".gate-snapshot").read_text()
            self.assertIn("task_type: framework", snap)
            self.assertNotIn("task_size:", snap)

    def test_malformed_frontmatter_keeps_existing_snapshot(self):
        status_ok = ("---\nmode: Dev\nphase: plan\ntask_type: framework\n"
                     "task_size: M\ngate_approvals:\n  review: pending\n---\n")
        with self._scratch(status_ok) as root:
            self._run_write_snapshot(root)
            before = (Path(root) / ".claude" / ".gate-snapshot").read_text()
            (Path(root) / "docs" / "STATUS.md").write_text(
                "---\nmode: Dev\nno close\n", encoding="utf-8")
            rc = self._run_write_snapshot(root)
            self.assertNotEqual(rc, 0)
            after = (Path(root) / ".claude" / ".gate-snapshot").read_text()
            self.assertEqual(before, after)
```

（`_run_write_snapshot` は既存様式に合わせ `bash -c "source hooks/lib/frontmatter.sh && source hooks/lib/snapshot.sh && aegis_write_snapshot '<root>'"` を `subprocess.run` で呼び rc を返すヘルパー。既存テストに同等ヘルパーがあればそれを使う。）

- [ ] **Step 2: FAIL 確認**

Run: `python3 -m pytest tests/test_snapshot_helper.py -k "spoof or absent_task_size or malformed" -v`
Expected: `spoof` FAIL（本文行が混入）・`absent_task_size` FAIL（rc≠0）・`malformed` FAIL（whole-file grep が拾い snapshot 更新）。

- [ ] **Step 3: 最小実装**（`aegis_write_snapshot` 本体を置換。冒頭に frontmatter.sh の防御的 source を追加）

```bash
# snapshot.sh consumes read_frontmatter/_section_filter; source defensively
# so a caller that loads snapshot.sh alone still works (bash 3.2 safe).
if ! declare -F read_frontmatter >/dev/null 2>&1; then
  . "$(dirname "${BASH_SOURCE[0]}")/frontmatter.sh"
fi

aegis_write_snapshot() {
  local root="$1"
  [ -n "$root" ] || return 1
  local status_file="${root}/docs/STATUS.md"
  local snapshot_dir="${root}/.claude"
  local snapshot_file="${snapshot_dir}/.gate-snapshot"
  [ -f "$status_file" ] || return 1
  # Frontmatter-scoped source (Fix③): body lines can never poison the
  # tamper baseline. Malformed/unterminated frontmatter -> keep the existing
  # snapshot untouched (non-destructive, K-7) and report failure.
  local fm
  fm=$(read_frontmatter "$status_file") || return 1
  [ -n "$fm" ] || return 1
  mkdir -p "$snapshot_dir" 2>/dev/null || return 1
  local tmp="${snapshot_file}.tmp.$$"
  # `|| true` per key: an absent OPTIONAL key (task_size before Step D) must
  # not abort the regen — the old whole-file version silently failed here,
  # leaving a stale snapshot (one enabler of the SF-010 empty-baseline window).
  {
    printf '%s\n' "$fm" | _section_filter gate_approvals
    printf '%s\n' "$fm" | grep -m1 "^phase:" || true
    printf '%s\n' "$fm" | grep -m1 "^mode:" || true
    printf '%s\n' "$fm" | grep -m1 "^task_type:" || true
    printf '%s\n' "$fm" | grep -m1 "^task_size:" || true
  } > "$tmp" 2>/dev/null && mv "$tmp" "$snapshot_file" 2>/dev/null || {
    rm -f "$tmp" 2>/dev/null || true
    return 1
  }
  return 0
}
```

- [ ] **Step 4: PASS 確認** → `python3 -m pytest tests/test_snapshot_helper.py tests/test_snapshot_atomic.py tests/test_snapshot_consumer_policy.py -v` 全 PASS

- [ ] **Step 4.5: 呼出側の rc 取り扱い確認**（grill-plan 要検討反映）

新失敗モード（malformed frontmatter → rc1）が `set -euo pipefail` の呼出側を中断させないか確認する:

Run: `grep -rn "aegis_write_snapshot" hooks/ scripts/ | grep -v snapshot.sh`
各呼出箇所（post-status-audit.sh / session-start.sh / update-gate.sh / update-task.sh 想定）について `|| true` ガードの有無を確認し、無い場合は「malformed STATUS で中断＝fail-closed として妥当」か「ガード追加」かを判断して記録する（authorized writer 内での中断は STATUS/snapshot の不整合を残さない位置かを見る）。

- [ ] **Step 4.6: 正常系 byte-shape ピン**（grill-plan 要検討反映・`tests/test_snapshot_helper.py` に追記）

```python
    def test_normal_status_snapshot_shape_pinned(self):
        # 正常系 STATUS では出力形状が従来と同一（行集合・順序）であることをピン
        status = ("---\nmode: Dev\nphase: plan\ntask_type: framework\n"
                  "task_size: M\ngate_approvals:\n  brainstorm: approved\n"
                  "  plan: pending\n---\nbody\n")
        with self._scratch(status) as root:
            self._run_write_snapshot(root)
            snap = (Path(root) / ".claude" / ".gate-snapshot").read_text()
            self.assertEqual(snap,
                "gate_approvals:\n  brainstorm: approved\n  plan: pending\n"
                "phase: plan\nmode: Dev\ntask_type: framework\ntask_size: M\n")
```

- [ ] **Step 5: full suite＋コミット**

`git add hooks/lib/snapshot.sh tests/test_snapshot_helper.py && git commit -m "fix(iter66): snapshot 生成を frontmatter スコープ化（Fix③・baseline 毒込み封鎖＋task_size 欠落 regen 失敗の潜在バグ修復）"`

---

### Task 4: migration-grace の絞り込み — task fields＋gate loop（Fix ①・SF-010 本丸・grill-plan 指摘①反映）

**blockedBy:** Task 1, Task 3 | **モデル:** `opus`
**ファイル:** 対象 `hooks/post-status-audit.sh`（gate tamper loop :146-158 付近＋task field tamper loop :200-217 付近） / テスト `tests/test_post_status_audit_task_tamper.py`
**意図:** grace を「真の旧フォーマット snapshot」限定に絞る — **task fields と gate loop の両方**。gate loop（`if [ "$OLD" != "$NEW" ] && [ -n "$OLD" ]`・post-status-audit.sh:152）にも同じ empty-grace が実在し、K-7 integrity check は phase/mode の非空しか見ないため、**gate 行が欠落した snapshot**（silent-fail 時代の stale snapshot 等）では raw-Edit による `deploy: approved` 注入が素通りする（SF-010 (iii) の empty-baseline class・grill-plan で実コード確認済み）。gate 用の現行フォーマット判定＝snapshot に `^gate_approvals:` 行が存在するか（snapshot は発足時から gate ブロックを常載＝grace が生きるのは事実上「破損・手彫り snapshot」のみで、これは block が正しい）。
**Interfaces:** Consumes: `frontmatter_value`/`gate_value`（Task 1/2 の scoped 読み・snapshot は bare なので whole-file のまま正しい）。Produces: `[task-tamper]`/`[gate-tamper]` block（メッセージ既存様式）。
**注記（missing-snapshot 残余）:** snapshot ファイル自体が無い場合は既存の first-edit allowance（AUDIT_SKIP_LOG に記録・:122-131）が先に emit_allow する。これは bootstrap 用の意図された窓であり本タスクで変更しない。snapshot の削除・改変は check-runtime-state.sh／K-7 integrity check が担う（リスク4）。

- [ ] **Step 1: 失敗するテストを書く**（既存 `_status`/`_snapshot`/`_scratch`/`_audit`/`_is_block` ハーネスを流用して `TestTaskTamper` に追記）

```python
    def test_sf010_empty_baseline_size_injection_blocked(self):
        # SF-010: snapshot は現行フォーマット（task_type あり）だが task_size 行なし
        # → STATUS への raw-Edit task_size 追加は block（現行は grace で素通り＝RED）
        with _scratch(_status(task_size="S"),
                      _snapshot(task_type="framework", task_size=None)) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"empty-baseline size injection must block: {out!r}")
                self.assertIn("task-tamper", out)
            finally:
                _unlock_tree(p)

    def test_task_type_removal_blocked_self_defense(self):
        # grace を開ける前段（task_type 行の除去）自体が block される
        status_no_type = _status().replace("task_type: framework\n", "")
        with _scratch(status_no_type, _snapshot()) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"task_type removal must block: {out!r}")
            finally:
                _unlock_tree(p)

    def test_gate_line_missing_in_snapshot_injection_blocked(self):
        # SF-010 (iii) empty-baseline class: snapshot の gate ブロックに deploy 行が
        # 欠落 → STATUS raw-Edit で deploy: approved は block（現行は grace＝RED）
        status = _status().replace("  deploy: pending\n", "  deploy: approved\n")
        snapshot = _snapshot().replace("  deploy: pending\n", "")
        with _scratch(status, snapshot) as tmp:
            p = Path(tmp)
            try:
                rc, out = _audit(p)
                self.assertEqual(rc, 0)
                self.assertTrue(_is_block(out),
                                f"gate empty-baseline injection must block: {out!r}")
                self.assertIn("gate-tamper", out)
            finally:
                _unlock_tree(p)
```

- [ ] **Step 2: FAIL 確認**

Run: `python3 -m pytest tests/test_post_status_audit_task_tamper.py -v`
Expected: `sf010_empty_baseline` FAIL・`gate_line_missing_in_snapshot` FAIL（いずれも block されない）。`task_type_removal` は現行でも PASS（既存判定 OLD 非空×値相違・回帰ピン）。既存 4 本（downgrade/type_change/matching/old_format_grace）PASS 維持。

- [ ] **Step 3a: gate loop の grace 絞り込み**（`hooks/post-status-audit.sh:146-158` の gate loop を置換）

```bash
# Check ALL gates for unauthorized value changes.
# Detect ANY change (not just →approved) to prevent bypass via direct edit.
# Authorized changes go through update-gate.sh which updates the snapshot
# atomically. Empty-OLD grace is narrowed (iter66 / SF-010 (iii)): if the
# snapshot carries a gate_approvals section at all (it always has, since the
# format's inception), a gate line missing from it is a broken/hand-edited
# baseline — blocking empty→value there is correct, not a migration case.
SNAP_HAS_GATE_SECTION=false
if grep -q "^gate_approvals:" "$SNAPSHOT_FILE" 2>/dev/null; then
  SNAP_HAS_GATE_SECTION=true
fi
for gate in client_ready_for_dev brainstorm plan review qa security deploy dev_ready_for_client; do
  OLD=$(gate_value "$SNAPSHOT_FILE" "$gate")
  NEW=$(gate_value "$STATUS_FILE" "$gate")

  if [ "$OLD" != "$NEW" ]; then
    if [ -n "$OLD" ] || [ "$SNAP_HAS_GATE_SECTION" = "true" ]; then
      REASON=$(printf '[gate-tamper] %s gate changed %s→%s without authorization. Use the /gate command to change gate values.' "$gate" "${OLD:-<unset>}" "${NEW:-<unset>}")
      emit_block "$REASON"
      exit 0
    fi
  fi
done
```

- [ ] **Step 3b: task field tamper loop の置換**（コメントも grace の新定義に同期）

```bash
# --- Task field tamper validation (iter43 / I3, narrowed iter66 / SF-010) ---
# task_type controls gate requirements AND the layer-2 moat lock; task_size
# controls which gates apply (size-aware since iter65). Authorized changes go
# through scripts/update-task.sh (snapshot updated atomically). A raw Edit that
# changes either field is tamper — block. Migration grace is ONLY for a true
# old-format snapshot (pre-iter43: no task_type line at all). A current-format
# snapshot (task_type line present) blocks even empty→value transitions —
# otherwise the OPTIONAL task_size could be injected during the empty-baseline
# window (fresh scaffold / rollover before brainstorm Step D) to flip the
# implement gate to brainstorm-only (SF-010).
# NOTE: this MUST run before aegis_cp_apply below — see the moved-cp_apply note above.
SNAP_IS_CURRENT_FORMAT=false
if grep -q "^task_type:" "$SNAPSHOT_FILE" 2>/dev/null; then
  SNAP_IS_CURRENT_FORMAT=true
fi
for tf in task_type task_size; do
  OLD_TF=$(frontmatter_value "$SNAPSHOT_FILE" "$tf")
  NEW_TF=$(frontmatter_value "$STATUS_FILE" "$tf")
  if [ "$OLD_TF" != "$NEW_TF" ]; then
    if [ -n "$OLD_TF" ] || [ "$SNAP_IS_CURRENT_FORMAT" = "true" ]; then
      REASON=$(printf '[task-tamper] %s changed %s→%s without authorization. Use scripts/update-task.sh to change task_type/task_size.' "$tf" "${OLD_TF:-<unset>}" "${NEW_TF:-<unset>}")
      emit_block "$REASON"
      exit 0
    fi
  fi
done
```

- [ ] **Step 4: PASS 確認** → `python3 -m pytest tests/test_post_status_audit_task_tamper.py tests/test_post_status_audit_fail_closed.py -v` 全 PASS
- [ ] **Step 5: full suite＋コミット**

`git add hooks/post-status-audit.sh tests/test_post_status_audit_task_tamper.py && git commit -m "fix(iter66): migration-grace を真の旧フォーマット snapshot 限定に（Fix①・task fields＋gate loop・SF-010 本丸封鎖）"`

---

### Task 5: python 読取の意味論同期（Fix ⑤・F-1）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 対象 `scripts/check_status.py:264-296`（`extract_scalar_value`/`extract_approval_map`） / テスト `tests/test_check_status_parsers.py`（新規）
**意図:** `extract_scalar_value` の引用形優先 2-pass を行順 first-match 1-pass に（F-1: bash=M/python=S の割れ根治）。`extract_approval_map` を重複キー先勝ちに（bash `grep -m1` と一致）。
**Interfaces:** Produces: 両関数のシグネチャ不変・返値意味論のみ bash と同期。正規化（`.strip('"').strip("'")`）は既存踏襲。

- [ ] **Step 1: 失敗するテストを書く**（新規ファイル `tests/test_check_status_parsers.py`）

```python
#!/usr/bin/env python3
"""iter66 Fix⑤: check_status.py パーサの行順 first-match / 先勝ち契約（F-1）。"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_status", ROOT / "scripts" / "check_status.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


class TestExtractScalarFirstMatch(unittest.TestCase):
    def test_quoted_later_does_not_override_first_unquoted(self):
        # F-1 再現: M の後に "S" を追記しても M（bash grep -m1 と同値）
        fm = 'task_size: M\nother: x\ntask_size: "S"'
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_quoted_value_still_normalized(self):
        fm = 'task_size: "M"'
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_duplicate_unquoted_first_wins(self):
        fm = "task_size: M\ntask_size: S"
        self.assertEqual(cs.extract_scalar_value(fm, "task_size"), "M")

    def test_absent_returns_none(self):
        self.assertIsNone(cs.extract_scalar_value("mode: Dev", "task_size"))


class TestApprovalMapFirstWins(unittest.TestCase):
    def test_duplicate_gate_key_first_wins(self):
        fm = ("gate_approvals:\n  review: approved\n  review: pending\n"
              "phase: qa")
        self.assertEqual(cs.extract_approval_map(fm)["review"], "approved")

    def test_normal_map_unchanged(self):
        fm = "gate_approvals:\n  review: approved\n  qa: pending\nphase: qa"
        m = cs.extract_approval_map(fm)
        self.assertEqual(m["review"], "approved")
        self.assertEqual(m["qa"], "pending")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: FAIL 確認**

Run: `python3 -m pytest tests/test_check_status_parsers.py -v`
Expected: `quoted_later_does_not_override` FAIL（現行は S）・`duplicate_gate_key_first_wins` FAIL（現行は pending）。他は PASS（回帰ピン）。

- [ ] **Step 3: 最小実装**（`scripts/check_status.py` の 2 関数を置換）

```python
def extract_scalar_value(frontmatter: str, key: str) -> str | None:
    # First match in LINE ORDER (iter66 / F-1): the old quoted-form-priority
    # two-pass let a later `key: "S"` override an earlier `key: M`, splitting
    # python consumers from the bash `grep -m1` enforcement readers.
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", frontmatter)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return None


def extract_approval_map(frontmatter: str) -> dict[str, str]:
    approvals: dict[str, str] = {}
    in_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not in_block:
            if re.match(r"^gate_approvals:\s*$", line):
                in_block = True
            continue

        if not line.strip():
            continue
        if re.match(r"^\S", line):
            break

        match = re.match(r"^\s{2}([A-Za-z0-9_]+):\s*([A-Za-z0-9_\"'\-/]+)\s*$", line)
        if match and match.group(1) not in approvals:
            # first occurrence wins (iter66): mirrors the bash `grep -m1`
            # readers so duplicate keys cannot split enforcement from checks
            approvals[match.group(1)] = match.group(2).strip("\"'")

    return approvals
```

- [ ] **Step 4: PASS 確認** → `python3 -m pytest tests/test_check_status_parsers.py -v` 全 PASS。既存 check_status 系テストも: `python3 -m pytest tests/ -k "check_status or status_doctor or contract" -q`
- [ ] **Step 5: full suite＋コミット**

`git add scripts/check_status.py tests/test_check_status_parsers.py && git commit -m "fix(iter66): check_status.py を行順 first-match／先勝ちへ同期（Fix⑤・F-1 封鎖）"`

---

### Task 6: check-gate.sh の task_size 読み dedup

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/check-gate.sh:256-266` / テスト 既存 `tests/test_check_gate_size_aware.py`（変更なし・回帰ピンとして全走）
**意図:** iter65 b9c95f7 のインライン scoped 読みを Task 1 の `frontmatter_value` へ戻し、読取意味論を library 単一ソース化。挙動不変（テスト無変更で green が証明）。

- [ ] **Step 1: 置換**（`hooks/check-gate.sh:266`）

現行:
```bash
TASK_SIZE=$(read_frontmatter "$STATUS_FILE" | grep -m1 '^task_size:' | sed 's/^task_size:[[:space:]]*//; s/^"//; s/"$//' || true)
```
置換後:
```bash
TASK_SIZE=$(frontmatter_value "$STATUS_FILE" task_size)
```
併せて直前コメント（258-265 行）を「frontmatter スコープ読みは iter66 で library 保証化（frontmatter_value）。本文 spoof は library 層で不可視」旨に短縮同期。

- [ ] **Step 2: 挙動不変の確認**

Run: `python3 -m pytest tests/test_check_gate_size_aware.py tests/test_check_gate_root_external.py -v`
Expected: 全 PASS（テスト無変更）。

- [ ] **Step 3: full suite＋コミット**

`git add hooks/check-gate.sh && git commit -m "refactor(iter66): check-gate の task_size 読みを frontmatter_value へ dedup（意味論の単一ソース化）"`

---

### Task 7: bash↔python parity drift-guard（新規テスト）

**blockedBy:** Task 1-6 | **モデル:** `opus`
**ファイル:** テスト `tests/test_parser_parity_driftguard.py`（新規）
**意図:** 敵対 fixture 表で bash 読点（`frontmatter_value`/`gate_value`）と python 読点（`extract_scalar_value`/`extract_approval_map`）の返値一致を機械ピン。将来どちらかが drift したら赤（iter53/65 parity 型）。

- [ ] **Step 1: テストを書く**（実装完了後なので GREEN-first で可＝drift-guard の性質。fixture は設計ノートの (a)-(f)）

```python
#!/usr/bin/env python3
"""iter66: bash↔python frontmatter 読取意味論の parity drift-guard。

契約 = 「frontmatter 内の最初の値」。fixture ごとに bash 読点と python 読点の
返値一致をアサートする。どちらかが将来 drift したらここが赤になる。
bare/unterminated は bash 側のみの挙動ピン（python は STATUS frontmatter 専用）。
"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "hooks" / "lib" / "frontmatter.sh"
_spec = importlib.util.spec_from_file_location(
    "check_status", ROOT / "scripts" / "check_status.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def bash_value(path: Path, key: str) -> str:
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && frontmatter_value '{path}' '{key}'"],
        capture_output=True, text=True, check=False)
    return r.stdout.strip()


def bash_gate(path: Path, gate: str) -> str:
    r = subprocess.run(
        ["bash", "-c", f"source '{LIB}' && gate_value '{path}' '{gate}'"],
        capture_output=True, text=True, check=False)
    return r.stdout.strip()


def py_value(text: str, key: str) -> str:
    fm = cs.extract_frontmatter(text)
    if fm is None:
        return ""
    v = cs.extract_scalar_value(fm, key)
    return "" if v is None else v


def py_gate(text: str, gate: str) -> str:
    fm = cs.extract_frontmatter(text)
    if fm is None:
        return ""
    return cs.extract_approval_map(fm).get(gate, "")


class TestParserParity(unittest.TestCase):
    def _file(self, d: str, text: str) -> Path:
        p = Path(d) / "STATUS.md"
        p.write_text(text, encoding="utf-8")
        return p

    def assert_parity(self, text: str, key: str, expected: str):
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            b, py = bash_value(p, key), py_value(text, key)
            self.assertEqual(b, py, f"bash={b!r} python={py!r} for {key}")
            self.assertEqual(b, expected)

    def assert_gate_parity(self, text: str, gate: str, expected: str):
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            b, py = bash_gate(p, gate), py_gate(text, gate)
            self.assertEqual(b, py, f"bash={b!r} python={py!r} for {gate}")
            self.assertEqual(b, expected)

    def test_a_duplicate_key_in_frontmatter(self):
        self.assert_parity(
            "---\ntask_size: M\ntask_size: S\n---\nbody\n", "task_size", "M")

    def test_a_duplicate_gate_key(self):
        self.assert_gate_parity(
            "---\ngate_approvals:\n  review: approved\n  review: pending\n"
            "---\nbody\n", "review", "approved")

    def test_b_quoted_and_unquoted_mixed(self):
        # F-1 の再発防止ピン
        self.assert_parity(
            '---\ntask_size: M\ntask_size: "S"\n---\nbody\n', "task_size", "M")

    def test_c_body_spoof_line(self):
        self.assert_parity(
            "---\ntask_size: M\n---\nbody\ntask_size: S\n", "task_size", "M")
        self.assert_parity(
            "---\nmode: Dev\n---\nbody\ntask_size: S\n", "task_size", "")

    def test_d_gate_section_missing_body_block_ignored(self):
        # F-2 の再発防止ピン
        self.assert_gate_parity(
            "---\nmode: Dev\n---\nbody\ngate_approvals:\n  review: approved\n",
            "review", "")

    def test_e_bare_snapshot_bash_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".gate-snapshot"
            p.write_text("task_type: framework\n", encoding="utf-8")
            self.assertEqual(bash_value(p, "task_type"), "framework")

    def test_f_unterminated_frontmatter_both_absent(self):
        text = "---\ntask_size: S\nno close\n"
        with tempfile.TemporaryDirectory() as d:
            p = self._file(d, text)
            self.assertEqual(bash_value(p, "task_size"), "")
            self.assertEqual(py_value(text, "task_size"), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: PASS 確認**

Run: `python3 -m pytest tests/test_parser_parity_driftguard.py -v`
Expected: 全 PASS。**歯の確認（mutant flip）**: `check_status.py` の `extract_scalar_value` を一時的に旧 2-pass に戻して `test_b` が FAIL することを確認し、元に戻す（結果を実装ログに記録）。

- [ ] **Step 3: full suite＋contract＋コミット**

Run: `python3 -m pytest tests/ -q && python3 scripts/check_framework_contract.py`
Expected: full green（新規分加算）＋ contract PASS
`git add tests/test_parser_parity_driftguard.py && git commit -m "test(iter66): bash↔python パーサ parity drift-guard（fixture 表 a-f・意味論の機械ピン）"`

---

## External Integrations

なし。

## 事前準備

- [x] 依存なし（pure bash + python3 stdlib）
- [x] ベースブランチ main 最新（8675009）
- [ ] 実装開始時に `git status` clean を確認

## トレーサビリティ（要件 → Task → Test）

| 要件（設計ノート） | Task | テスト |
|------|------|--------------|
| 読点の全数統一（設計の中核主張） | Task 0 | census 台帳（enforcement 全件が Task 1-6 へ写像・advisory/writer は理由記録） |
| Fix ① grace 絞り込み（SF-010 本丸・task fields） | Task 4 | `test_post_status_audit_task_tamper.py::test_sf010_empty_baseline_size_injection_blocked` ほか |
| Fix ① grace 絞り込み（gate loop・SF-010 (iii)） | Task 4 | `test_gate_line_missing_in_snapshot_injection_blocked` |
| Fix ① grace 温存（真の旧フォーマット） | Task 4 | 既存 `test_old_format_snapshot_migration_grace`（無変更 green） |
| Fix ① 自己防衛（task_type 除去 block） | Task 4 | `test_task_type_removal_blocked_self_defense` |
| Fix ② frontmatter_value スコープ化 | Task 1 | `test_frontmatter_lib.py` 新規 4 本 |
| Fix ③ snapshot 毒込み封鎖＋regen 潜在バグ | Task 3 | `test_snapshot_helper.py` 新規 3 本 |
| Fix ④ gate_value fallback 厳格化（F-2） | Task 2 | `test_body_gate_block_not_adopted_when_frontmattered` |
| Fix ⑤ python 同期（F-1・先勝ち） | Task 5 | `test_check_status_parsers.py` 新規 6 本 |
| dedup（意味論の単一ソース化） | Task 6 | 既存 `test_check_gate_size_aware.py`（無変更 green） |
| parity drift-guard | Task 7 | `test_parser_parity_driftguard.py` fixture a-f |
| 正規経路（update-task.sh）無影響 | Task 4 | 既存 `test_post_status_audit_task_tamper.py` の update-task 経由テスト（無変更 green） |

## 自己レビュー

- 仕様カバレッジ: 設計ノート Fix ①-⑤＋dedup＋parity すべてに Task あり（上表）
- 曖昧さ: 「現行フォーマット判定」＝snapshot 内 `^task_type:` **行の存在**（値の空/非空ではない）で一意
- 型整合: `frontmatter_value`/`gate_value` のシグネチャ・rc 契約は全タスクで不変
- 境界整合: Task 4 の Consumes（scoped NEW 読み）は Task 1 の Produces に一致

## リスク

- リスク1: library 変更（Task 1/2）の回帰面が 9 hook ファイルに及ぶ。
  対策: 呼出契約（absent→空+rc0）不変・必須キーは first-match 位置が frontmatter 内で不変・full suite 1096 本＋scaffold smoke でピン。
- リスク2: snapshot 生成変更（Task 3）で正規フローの snapshot 内容が変わる。
  対策: 正常系 STATUS では出力 byte 同一（frontmatter 由来行のみ・順序不変）。既存 snapshot 系テスト 3 ファイル全走で確認。
- リスク3: 未終端 frontmatter の STATUS で全読点が空を返す＝挙動変化。
  対策: fail-closed 方向のみ（deny が増える）。破損 STATUS はそもそも session-start/doctor が警告する運用前提。corrupting Edit 自体が gate/task-tamper 判定で block される（OLD 非空×NEW 空）。
- リスク4: snapshot 削除→grace 窓（脅威モデル外）。
  対策: `.claude/` への Bash 書込みは check-runtime-state.sh が block・snapshot 欠落時は既存 first-edit allowance が AUDIT_SKIP_LOG に記録・SF-006 較正と同じ境界と設計ノートに明記済み（コード変更なし）。
- リスク5: gate loop の grace 絞り込み（Task 4 Step 3a）が正規フローを誤 block する。
  対策: 正規 gate 変更は update-gate.sh が snapshot を原子更新するため audit 比較に差分が出ない（既存テスト群でピン）。grace が絞られるのは「snapshot に gate 行が欠落」という破損状態のみで、そこでの block は fail-closed として正しい。
- リスク6: CRLF 化された STATUS は `---` 判定に掛からず whole-file 読みに落ちる。
  対策: 値末尾に \r が残り厳格一致（approved 等）に失敗する＝deny 方向に退化するため緩和にはならない（事故スコープでは LF 前提・変換は意図的操作＝脅威モデル外）。

## 完了条件

- [ ] 全テスト pass（full suite・新規 15 本前後加算・flaky は切り分け記録）
- [ ] `python3 scripts/check_framework_contract.py` PASS
- [ ] grill-code → review（1次＋盲検2次）→ qa → security の各ゲート
- [ ] docs フェーズで `docs/security-followups.md` SF-010 を **CLOSED** 化（対応コミット・(i)(ii)(iii) の消化を明記）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

# 実装計画 — iter64: fingerprint tree-hash 化＋OR marker 厳格化（R6 根1・LOW-1・v1.25.0）

> 設計正本: docs/specs/2026-07-08-iter64-fingerprint-tree-hash-design.md
> 動機正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R6・§4 Phase 1「1-1」／ iter63 LOW-1
> 実証（2026-07-08 本セッション）:
> - tree-hash: `git ls-tree -r HEAD | grep -v -e $'\tdocs/' -e $'\t\.claude/' | shasum -a256` が
>   docs-only コミット後で不変・code コミット後で変化・.claude-only コミット後は code と一致。
> - OR marker: stamp `66e59e8`(2026-06-13) は cp-lock `1e46e4d`(2026-06-21) より先行 → 全 lockable install は stamp 保有。

## タスク分解（TDD: 各タスク RED → GREEN）

### Task 1: fingerprint tree-hash 化（fingerprint.sh＋test）— RED 先行

**1a. RED テスト追加** `tests/test_fingerprint_lib.py`（`TestFingerprint` 内）:

```python
def test_docs_only_commit_does_not_change_fp(self):
    # 罠 r 根切り: docs-only コミットは非 docs tree を動かさない＝fp 不変。
    # 旧 head:<sha> 実装では HEAD 進行で fp が動き a≠b（RED）。
    (self.root / "app.py").write_text("print(1)\n")
    subprocess.run(["git", "-C", str(self.root), "add", "app.py"], check=True)
    subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-q", "-m", "code"],
                   check=True)
    a = run_fp(self.root)  # クリーンツリー
    (self.root / "docs").mkdir()
    (self.root / "docs" / "NOTE.md").write_text("hi\n")
    subprocess.run(["git", "-C", str(self.root), "add", "docs/NOTE.md"],
                   check=True)
    subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-q", "-m", "docs only"],
                   check=True)
    b = run_fp(self.root)  # クリーンツリー・docs-only コミット後
    self.assertRegex(b, HEX64)
    self.assertEqual(a, b)
```

**1a-2. RED テスト追加②**（grill-plan 致命1 の回帰。`TestFingerprintHardening` 内）:

```python
def test_committed_dir_resembling_dotclaude_is_not_excluded(self):
    # grill-plan 致命1: ls-tree 除外の '.claude/' はリテラル。bare-dot(any-char)
    # だと 'aclaude/' 等「1文字+claude/」のコード dir を誤除外し silent-green 穴。
    # aclaude/ をコミット→内容変更して再コミット。両ツリー clean なので committed
    # 成分のみ差。誤除外あり=A==B(RED)、char-class [.] で保持=A!=B(GREEN)。
    d = self.root / "aclaude"
    d.mkdir()
    (d / "code.py").write_text("print(1)\n")
    subprocess.run(["git", "-C", str(self.root), "add", "aclaude/code.py"],
                   check=True)
    subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-q", "-m", "c1"], check=True)
    a = run_fp(self.root)
    (d / "code.py").write_text("print(2)\n")
    subprocess.run(["git", "-C", str(self.root), "add", "aclaude/code.py"],
                   check=True)
    subprocess.run(["git", "-C", str(self.root), "-c", "user.email=t@t",
                    "-c", "user.name=t", "commit", "-q", "-m", "c2"], check=True)
    b = run_fp(self.root)
    self.assertRegex(b, HEX64)
    self.assertNotEqual(a, b)
```

モジュール docstring の「HEAD コミット sha…混入する理由」節を「非 docs/.claude の
committed tree-hash」に更新（`test_new_commit_changes_fp_even_when_tree_clean` は
無改変で維持＝コード commit で fp が動く pin＝silent-green 保存）。

RED 確認: `python3 -m pytest tests/test_fingerprint_lib.py -k "docs_only or resembling" -v` → 2 FAIL。

**1b. 実装** `hooks/lib/fingerprint.sh`:

ヘッダの「Hash input = HEAD commit sha … Mixing in the HEAD sha is load-bearing」
段落を tree-hash 説明に更新。本体 42-52 行の head/ref 取得を差し替え:

```bash
fingerprint_worktree() {
  local root="${1:-.}"
  if ! git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'nogit\n'
    return 0
  fi
  # Committed code state = sha256 of `git ls-tree -r HEAD` with docs/ and
  # .claude/ paths removed (罠 r 根切り). A docs/.claude-only commit leaves the
  # non-excluded lines unchanged → fp unchanged; a code commit moves a blob sha
  # → fp moves (silent-green prevention fully preserved). Replaces the old
  # `head:<sha>` line, which moved on EVERY commit incl. docs-only.
  local ref="$AEGIS_FP_EMPTY_TREE" committed listing=""
  if git -C "$root" rev-parse --verify -q HEAD >/dev/null 2>&1; then
    ref="HEAD"
    listing=$(git -C "$root" -c core.quotepath=off ls-tree -r HEAD 2>/dev/null) \
      || { printf 'error\n'; return 0; }
  fi
  # 除外は TAB+パス先頭。.claude/ は char-class [.] でリテラルドット固定
  # ($'\t\.claude/' は bash が \. を bare-dot=any-char に潰し aclaude/ 等を誤除外
  # ＝silent-green 穴。grill-plan 致命1 で実証)。
  local tab
  tab=$'\t'
  local filtered
  filtered=$(printf '%s\n' "$listing" \
               | grep -v -e "${tab}docs/" -e "${tab}[.]claude/" || true)
  committed=$(printf '%s' "$filtered" | _fp_sha256)
  # ... (diff_files / untracked_files 以降は現状不変) ...
```

ハッシュ入力の第1行（86-87 行）を置換:

```bash
  {
    printf 'tree:%s\n' "$committed"
    while IFS= read -r rel; do
    ...
```

`head` 変数は削除。`ref` は diff 用に残す。それ以外（framed cat・count/bytes・
oversize・quoted→error）は無改変。

GREEN 確認: `python3 -m pytest tests/test_fingerprint_lib.py -v` → 全 PASS（15 既存＋2 新規）。
`bash -n hooks/lib/fingerprint.sh`。（既存 15 は tree-hash プロトタイプで PASS 実証済み）

### Task 2: OR marker 厳格化（setup.sh＋test）— RED 先行

**2a. RED テスト追加** `tests/test_setup_locked_target_upgrade.py`:

```python
@pytest.mark.skipif(ROOTUSER, reason="chmod a-w does not bind root")
def test_cplock_present_without_stamp_does_not_self_heal(tmp_path):
    # LOW-1: authoritative stamp (.aegis-install-version) が唯一の身元証明。
    # cp-lock.sh の存在だけでは self-heal 発火しない（旧 OR ロジックは発火し
    # rc0＋"OS-locked"＝RED）。stamp 削除後 lock → 再 install は fail-closed。
    target = tmp_path / "proj"
    try:
        _run(str(target), check=True)                 # フル install（stamp 生成）
        (target / ".claude" / ".aegis-install-version").unlink()  # stamp 除去
        hook = target / "hooks" / "check-gate.sh"
        hook.write_text("#!/usr/bin/env bash\n# STALE\nexit 0\n")  # 差分を作る
        _lock(str(target))
        r = _run(str(target))
        assert r.returncode != 0                       # stamp 無 → self-heal せず fail-closed
        assert "OS-locked" not in r.stdout             # unlock 発火せず
        assert "is not writable" in r.stderr           # 帰属エラー
        assert not os.access(str(target / "hooks"), os.W_OK)  # lock 不変
    finally:
        _unlock_all(tmp_path)
```

RED 確認: `python3 -m pytest tests/test_setup_locked_target_upgrade.py -k without_stamp -v` → FAIL。

**2b. 実装** `bin/setup.sh` `selfheal_unlock_target`（640-642 行）:

```bash
  # 身元判定は authoritative stamp 単独（LOW-1）。cp-lock.sh は単なる framework
  # ファイルで install 証明にならない。stamp（K-11 66e59e8・2026-06-13）は
  # cp-lock（1e46e4d・2026-06-21）より先行導入されるため、OS-lock され得る
  # install は必ず stamp を持つ＝正規 self-heal を失わない。stamp は locked CP
  # 集合（hooks/scripts/templates/CLAUDE.md/.claude/{rules,skills,commands,agents}）
  # 外なので lock 下でも読める。実 lock 検出（aegis_cp_verify）の第2防御は不変。
  if [ ! -f "$target/.claude/.aegis-install-version" ]; then
    return 0
  fi
```

関数頭コメント（624-634 行）の「Gated on BOTH (a) an aegis-install marker …」を
「the authoritative install stamp」に整合更新。

GREEN 確認: `python3 -m pytest tests/test_setup_locked_target_upgrade.py -v` → 全 PASS
（5 既存＋1 新規）。`bash -n bin/setup.sh`。

### Task 3: 対象スイート → full suite

1. `python3 -m pytest tests/test_fingerprint_lib.py tests/test_setup_locked_target_upgrade.py -v`
2. consumer 回帰（契約不変の確認）: `python3 -m pytest tests/test_build_judge_card.py tests/test_evidence_lib.py -q`（存在するもの）
3. `bash -n hooks/lib/fingerprint.sh bin/setup.sh`
4. full: `python3 -m pytest tests/ -q`（record は qa フェーズで）
5. 手動: `bash hooks/lib/fingerprint.sh .` が 64-hex を返すこと。

## grill-plan で検証してほしい確定事項

1. **pipefail/set-e 安全性**: `filtered=$(printf … | grep -v … || true)` と
   `committed=$(printf '%s' "$filtered" | _fp_sha256)` が abort しない形か
   （grep 空マッチ rc1 を `|| true` で受ける・既存 60 行と同型）。
2. **既存 14 テスト無改変で green**: tree-hash 化が clean 決定論・deleted 変化・
   no-HEAD・非ASCII・境界連結・oversize を壊さないか（committed 成分は blob sha を
   含む ls-tree 出力を直接ハッシュ＝cat しない＝quotepath silent-green 経路なし）。
3. **grep 除外の正確性**: `$'\tdocs/'`/`$'\t\.claude/'` が ls-tree 出力
   `<mode> blob <sha>\t<path>` のパス先頭のみに一致し、ルート直下の同名 **ファイル**
   （`docs`・末尾スラッシュ無し）を誤除外しないか。
4. **committed 空の決定論**: 全 committed が docs/.claude（filtered=""）と no-HEAD が
   ともに sha256("") 定数に落ち、clean-tree hash への危険な alias を作らないか
   （head:<sha> 廃止で「新コミットで fp が動く」は committed 成分が担保）。
5. **OR marker 安全性**: stamp 先行導入の実証（先の日付比較）で正規 self-heal を
   失わないこと。stamp が locked CP 集合外で lock 下でも `[ -f ]` が真になること。
6. **consumer 非依存**: `current_fingerprint`/evidence.sh が 64-hex 判定後の不透明
   比較のみで、`head:`→`tree:` 内部表現変更の影響を受けないこと。

## qa フェーズ（B1 drill）方針

- 実 drill（skip なし）。mutant 候補（`bash -n` 通過の意味変異）:
  1. `grep -v` の除外を削除（docs も混入）→ docs-only 不感テストが catch
  2. `printf 'tree:%s'` を定数化 → new-commit-changes / content-change が catch
  3. selfheal stamp ガードを常真化 → without_stamp テストが catch
  4. `committed` を空文字固定 → new-commit-changes が catch
  5. char-class `[.]claude/` を bare-dot `.claude/` に戻す → resembling 回帰テストが catch
- test_command: `python3 -m pytest tests/test_fingerprint_lib.py tests/test_setup_locked_target_upgrade.py -q`
- drill 後は pyc 汚染対策で full suite を再実走してから record（iter62 教訓）。

## security フェーズ方針（fingerprint は E1 moat 中核）

- silent-green 経路の非復活を最重視（tree-hash が code commit で必ず動く・
  committed 空 alias が clean-tree を certify しない）。
- fp 移行の fail-closed 性（既存 record → unverified、silent-green にならない）。
- OR marker 厳格化がバイパス lever を作らない（機能を減らす方向のみ）。

## ship フェーズ

- version bump 3箇所（iter63 実績 `git show 936dbe0`）:
  ①`scripts/check_framework_contract.py` FRAMEWORK_VERSION
  ②`docs/STATUS.md` frontmatter `framework_version`
  ③`templates/STATUS.template.md` `framework_version`。
  v1.24.0 → **v1.25.0（MINOR）**（fp 定義変更で record 再取得を要する運用変更）。
- `docs/handover/TO-CLIENT.md` の該当行更新（fp 移行の一言＝既存 record は一度再実行）。

## リスク・残余

- fp 移行の一過性 unverified: 全 record が初回 unverified 化。fail-closed で安全。
  該当タスクのテスト再実行で解消（marker_verified 前例）。ship note で周知。
- 履歴分岐で非 docs tree が同一なら fp 一致（同一コード状態＝同一 fp）は仕様どおり
  （head:<sha> より正しい・silent-green ではない）。

## grill-plan 反映簿記（2026-07-08・全指摘実コマンド実証）

- **致命1**（実証済）: ls-tree 除外 `$'\t\.claude/'` は bash が `\.` を bare-dot
  （any-char）に潰し `aclaude/foo.py` 等を誤除外＝silent-green 穴（実バイト
  `09 2e ...` と grep 実演で確認）。既存15＋docs-only テストも空白。→ char-class
  `${tab}[.]claude/` に修正（`.claude/`のみ除外・`aclaude/`/`xdocs/` 保持を実演）＋
  回帰テスト `test_committed_dir_resembling_dotclaude_is_not_excluded` 追加。Task 1a-2/1b に反映済み。
- **要検討1**（実証で解消）: 既存15テストを tree-hash プロトタイプで全 PASS 確認＝無回帰。
  full suite に fp 値ハードコードはゼロ（grep 確認）＝算法変更は安全。GREEN で full 再確認。
- **要検討2**（受容）: 性能 +25ms/回（ls-tree 459 files・メタデータのみ・hot-path 外）。
  設計「性能」節に明記。
- **要検討3**（周知）: fp 移行で既存 record 一過性 unverified（fail-closed）。ship note に明記。
- **確認**: consumer は `head:`/`tree:` 内部表現非依存（`head:` 参照は fingerprint.sh:87
  のみと grep 確認）。RED#2 前提（standard install は target に cp-lock.sh と stamp を
  両方置く）を実 install で確認。OR marker 安全性は stamp(2026-06-13)＜cp-lock(2026-06-21)
  の日付順で確定。

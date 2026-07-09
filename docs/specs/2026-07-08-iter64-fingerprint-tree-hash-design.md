# 設計ノート — iter64: fingerprint tree-hash 化＋OR marker 厳格化（R6 根1・LOW-1）

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-08-iter64-fingerprint-tree-hash-brainstorm-record.md`
- 要件（正本）: `docs/full-review-2026-07-06-six-dimensions-evolution.md` §2 R6・§4 Phase 1「1-1」
- iter63 由来: security 盲検2次 approve_with_notes（LOW-1「OR marker」）
- 実証（本セッション 2026-07-08）:
  - tree-hash: 初期＝docs-only コミット後で **一致**、code コミット後で **相違**、.claude-only コミット後は code と **一致**（`git ls-tree -r HEAD | grep -v -e $'\tdocs/' -e $'\t\.claude/' | shasum -a256`）。
  - OR marker: stamp K-11 `66e59e8`（2026-06-13）は cp-lock `1e46e4d`（2026-06-21）より **8日先行** → OS-lock され得る install は必ず stamp を持つ。

## 問題整理

- 背景:
  - **fp（罠 r 根1）**: fingerprint.sh は「`head:<HEAD-sha>` ＋ HEAD 比変更/未追跡ファイルの framed 内容（docs/.claude 除外）」を sha256 する。`head:<sha>` 混入は「クリーンツリー同士が同一 fp になる→未テストの新コミットが旧 record と一致（silent green）」を塞ぐための load-bearing 成分。しかし副作用として **docs-only コミットでも HEAD が進み fp が動く**＝無変更コードの green が unverified 化し、再 record 儀式を強制する（順序制約 b/c/d を連鎖）。
  - **OR marker（LOW-1）**: `selfheal_unlock_target` は身元判定に `.aegis-install-version` OR `hooks/lib/cp-lock.sh` を使う。後者は単なる framework ファイルで、authoritative な install 証明ではない。
- 判断が必要な論点:
  - `head:` 成分をどう置換すれば **silent-green 防止を保存したまま docs-only 不感** にできるか → committed 成分を「非 docs/.claude の tree-hash」にする（コード状態を直接ハッシュ）。
  - 既存 record の扱い → fail-closed 移行（unverified・要再 record）。marker_verified 前例。
- 制約条件:
  - **トークン契約不変**: stdout=1 行 `64-hex | oversize | nogit | error`、常に rc=0。consumer は 64-hex 判定後に不透明比較のみ（`head:`/`tree:` は内部表現で外部非依存）。
  - **既存テスト無改変で green**: fingerprint 14・setup-locked 5。
  - **bash 3.2 互換**（macOS）・`set -e`/`pipefail` 下でも grep の空マッチ（rc1）で abort しない受け方。
  - **fingerprint.sh は E1 単一所有者**（python 再実装を生やさない）。

## 推奨アプローチ

- 採用方針:
  1. **fp**: ハッシュ入力先頭の `printf 'head:%s\n' "$head"` を、非 docs/.claude committed tree-hash の `printf 'tree:%s\n' "$committed"` に置換。`ref`（作業ツリー diff の基点＝`HEAD` or empty-tree）は現状維持。
  2. **fp 移行**: 明示機構なし。fp 定義変更で既存 record は初回ロードで unverified に自然降格（silent-green にならない fail-closed）。
  3. **OR marker**: `selfheal_unlock_target` の身元ガードを stamp 単独へ。`aegis_cp_verify` 実 lock 要求（第2防御）は不変。
- 採用理由: committed 成分を「コード状態そのもの」にすることで、docs 変更は原理的に fp へ寄与せず（除外）、コード変更（コミット済/未コミットとも）は必ず fp を動かす。分岐追加なし・意味明快。OR marker は実証済みで正規経路を失わずに身元判定を authoritative 1 本に締める。
- 検討した代替案と不採用理由: BRAINSTORM-RECORD 参照（B=複雑化/YAGNI、C=silent-green 復活）。

## コンポーネント分解

- **ユニット1（fp コア）** `hooks/lib/fingerprint.sh`:
  - HEAD 検証分岐で committed listing を取得（HEAD 無し＝empty listing）。docs/.claude 行を除外し sha256 → `committed`。
  - ハッシュ入力の第1行を `tree:%s` に置換。それ以降（framed cat）は不変。
  - 確定文言（実証済みスニペット）:
    ```bash
    # HEAD の committed 状態から docs/.claude を除いた tree-hash（罠 r 根切り）。
    # git ls-tree -r HEAD の各行 `<mode> blob <sha>\t<path>` を除外→sha256。
    # docs/.claude のみのコミットは非除外行が不変＝fp 不変。コード変更コミットは
    # blob sha が動く＝tree-hash が動く＝silent-green 防止を完全保存。
    local ref="$AEGIS_FP_EMPTY_TREE" committed listing=""
    if git -C "$root" rev-parse --verify -q HEAD >/dev/null 2>&1; then
      ref="HEAD"
      listing=$(git -C "$root" -c core.quotepath=off ls-tree -r HEAD 2>/dev/null) \
        || { printf 'error\n'; return 0; }
    fi
    # 除外は TAB+パス先頭で。docs/ は素の文字列、.claude/ は char-class [.] で
    # リテラルドット（$'\t\.claude/' だと bash が \. のバックスラッシュを剥がし
    # bare-dot=any-char になり aclaude/ 等を誤除外＝silent-green 穴。grill-plan 実証）。
    local tab
    tab=$'\t'
    local filtered
    filtered=$(printf '%s\n' "$listing" \
                 | grep -v -e "${tab}docs/" -e "${tab}[.]claude/" || true)
    committed=$(printf '%s' "$filtered" | _fp_sha256)
    ```
    - ハッシュ入力: `printf 'tree:%s\n' "$committed"`（旧 `head:%s` の置換）。
  - `head` ローカル変数は削除（未使用化）。`ref` は diff 用に残す。
- **ユニット2（fp テスト）** `tests/test_fingerprint_lib.py`:
  - RED-first 追加①: `test_docs_only_commit_does_not_change_fp`（app.py コミット→fp A、docs/NOTE.md のみコミット→fp B、`assertEqual(a,b)`＋`assertRegex(b, HEX64)`）。旧コードでは HEAD 進行で a≠b＝RED、新コードで GREEN。
  - RED-first 追加②（grill-plan 致命1 の回帰）: `test_committed_dir_resembling_dotclaude_is_not_excluded`（`aclaude/code.py` をコミット→fp A、内容変更して再コミット→fp B、`assertNotEqual`）。両ツリー clean なので committed 成分のみ差＝除外パターンが bare-dot（any-char）だと `aclaude/` が誤除外され A==B＝RED、char-class `[.]` だと保持され A≠B＝GREEN。既存15＋新 docs-only テストの空白を埋める。
  - モジュール docstring を「HEAD sha 混入」→「非 docs/.claude committed tree-hash」に更新。`test_new_commit_changes_fp_even_when_tree_clean` は無改変で維持（コード commit で fp が動く＝silent-green 保存の pin）。
- **ユニット3（OR marker）** `bin/setup.sh`:
  - `selfheal_unlock_target` の早期 return を stamp 単独へ:
    ```bash
    # 身元判定は authoritative stamp 単独（LOW-1）。cp-lock.sh は単なる framework
    # ファイルで install 証明にならない。stamp は cp-lock（layer-2）より先行導入
    # されるため、OS-lock され得る install は必ず stamp を持つ（正規 self-heal を
    # 失わない）。stamp は locked CP 集合外なので lock 下でも読める。
    if [ ! -f "$target/.claude/.aegis-install-version" ]; then
      return 0
    fi
    ```
  - 関数頭のコメント（「Gated on BOTH (a) an aegis-install marker …」）を stamp 単独に整合更新。
- **ユニット4（OR marker テスト）** `tests/test_setup_locked_target_upgrade.py`:
  - RED-first 追加: `test_cplock_present_without_stamp_does_not_self_heal`（フル install→stamp 削除→hook stale 化→lock→再 install。旧 OR コードは cp-lock.sh 存在で self-heal 発火し rc0＋"OS-locked"＝RED、新コードは stamp 無しで早期 return→fail-closed rc≠0・"OS-locked" 非出力・stderr に "is not writable"＝GREEN）。ROOTUSER skip・teardown で `chmod -R u+w`。
- **ユニット5（簿記）**: version bump は ship（v1.24.0→v1.25.0 MINOR＝fp 定義変更で既存 record の再 record が要るため）。

## インターフェース定義

- `fingerprint_worktree <root>` → stdout `64-hex | oversize | nogit | error`、rc=0。**契約不変**。
- consumer 契約（`current_fingerprint` / evidence.sh）: 変更なし。64-hex を要求してからの不透明比較。
- `selfheal_unlock_target <target>` → 副作用（unlock＋NOTE）or 無音 return。**発火条件のみ厳格化**（stamp 必須）、出力契約不変。

## データフロー / 構造

- fp: `git ls-tree -r HEAD`（committed）＋`git diff --name-only HEAD`／`ls-files --others`（working）→ docs/.claude 除外 → `tree:<h>` ＋ framed 内容 → sha256 → トークン。
- setup: stamp 検出 → 実 lock 検出（`aegis_cp_verify`）→ `aegis_cp_unlock` → NOTE。

## 依存関係

- 依存方向: consumer → fingerprint.sh（単一所有者・循環なし）。setup.sh → cp-lock.sh（単一所有者）。
- 外部依存: `git`・`shasum`/`sha256sum`（現状同一）。新規依存なし。

## エラーハンドリング

- 想定失敗と対応:
  - `git ls-tree` 失敗 → `error` トークン（空 listing に倒さない＝clean-tree hash への alias を防ぐ、既存 diff 失敗と同方針）。
  - grep 空マッチ（全 committed が docs/.claude）→ `|| true` で受け filtered="" → sha256("") 定数（決定論的・非除外コード無しを正しく表す）。
  - HEAD 無し → listing="" → 同経路（committed 成分は定数）。作業ツリー成分でコードを拾う。
  - quotepath: committed 成分は ls-tree の **blob sha を含む出力行**を直接ハッシュするため、パスが quote されても内容変化は blob sha で必ず検出（cat しない＝silent-green 経路なし）。作業ツリー成分は既存の quotepath=off＋quoted-name→error を維持。
- 伝播方針: すべて rc=0 のトークンに畳む（既存契約）。consumer は非 64-hex を unverified 化。

## テスト戦略

- 単体（fp）: 既存 15（clean 決定論・untracked/content 変化・docs/.claude 除外・oversize×2・no-HEAD・new-commit 変化・非ASCII×2・境界連結・unreadable/quoted→error・deleted 変化）を無改変で維持（プロトタイプで全 15 PASS 実証済み）＋新規 2（docs-only 不感・`aclaude/` 誤除外回帰）。
- 単体（setup）: 既存 5（self-heal・fresh 無音・AND 第2 leg・opt-out fail-closed・non-aegis 不介入）を維持＋新規 stamp 必須 1。
- 結合: full suite（前回 1076 passed/2 skipped 基準）green。
- エッジケース: 上「エラーハンドリング」の各分岐をテストで担保（既存が大半をカバー、docs-only 不感を追加）。
- 手動確認: 実 aegis repo で `bash hooks/lib/fingerprint.sh .` が 64-hex を返すこと、docs 修正コミット前後で不変・コード修正で変化することを ship 前に確認。

## 性能（grill-plan 要検討）

- 追加コストは `git ls-tree -r HEAD` 1 回（aegis 実測 459 committed files）＋grep＋sha256。
  実測 96ms→121ms/回（+25ms）。メタデータのみ（内容 cat なし）で規模に緩やか、かつ
  fingerprint は evidence.sh の hot-path 最適化（L241）で常時計算されない＝許容トレードオフ。

## 互換性・バージョン

- consumer 無改変（契約不変）。既存テスト無改変で green（プロトタイプで全 15 実証済み・
  fp 値をハードコードするテストは全 suite に存在しないと grep 確認）。
- **移行**: fp 定義変更で `.claude/evidence-log.jsonl` の既存 record は初回ロードで unverified に降格（fail-closed・silent-green にならない）。運用影響＝「該当タスクのテストを一度再実行して record を上書き」。marker_verified（v1.6.1）導入時と同型。
- バージョン: v1.24.0 → **v1.25.0（MINOR）**。fp 定義変更（record 再取得を要する運用上の意味変更）と OR marker 挙動変更のため MINOR。bump 3 箇所（`scripts/check_framework_contract.py`・`docs/STATUS.md`・`templates/STATUS.template.md`＝iter63 前例）。

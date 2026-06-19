# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-18-sf-001-cp-token-bypass-brainstorm-record.md`
- 要件 / 正典ブリーフ: `docs/security-followups.md` SF-001
- 既存要件: `docs/full-review-2026-06-13-context-futureproof.md`

## 問題整理

- 背景: `hooks/check-control-plane.sh` の control-plane 判定（正規表現＋`mask_quoted`）はシェルの「クォート除去＋隣接トークン連結＋backslash＋パス解決」を再現しない。リテラル `hooks/`|`scripts/`|`templates/`|`STATUS.md`|`CLAUDE.md`|`.claude/` 部分文字列に一致するだけ。
- 判断が必要な論点: シェル忠実なトークン化をどう導入するか。既存の battle-tested ロジック（OBS-006 メッセージ救済・redirect・cmdsub fail-closed）を壊さないか。
- 制約条件: ①既存 allow/deny 挙動・moat テスト・REDTEAM(18/18+5/5) を緑維持 ②セキュリティ境界＝fail-closed 厳守 ③配布面（setup.sh copy_hooks / example mirror）を増やさない ④ブロックリスト（書込みコマンド列挙）は採らない（iter31 learning「列挙漏れ」）。

## 推奨アプローチ

- 採用方針: **Augment**。`cmd_mentions_control_plane()` の末尾（cmdsub 分岐より後＝非 cmdsub 経路のみ）に新関数 `cmd_token_mentions_cp "$cmd"` を1本追加し、true なら `return 0`（mention 扱い）。既存 (a)(b)(c) は無改変。コードは `check-control-plane.sh` に **inline**。
- 採用理由: deny を足すだけ＝回帰リスク最小。既存の勝ちを構造的に温存。新規 lib を作らず配布面/mirror 面を増やさない。
- 検討した代替案と不採用理由: Replace（mention 検出をトークナイザで作り直す）はセキュリティ境界で全エッジ（OBS-006/redirect/cmdsub）を再導出＝高リスク・盲検負荷増のため不採用。

## コンポーネント分解

- 分割方針: 検出を「シェル忠実トークン化」と「語→CP 判定」に分け、最終 allow/deny は既存下流（allowlist / task_type=framework / read-only carve-out / bare-git-add / default deny）に委ねる。
- 各ユニットの責務:
  - ユニット A `cmd_token_mentions_cp(cmd)`: コマンドを語に分割し、redirect-target 語と operand 語に分類。各語の literal value が CP 解決なら、規約に従い mention(=0) を返す。
  - ユニット B 語分割（python3 `shlex.split(posix=True)`・inline）: クォート除去＋隣接連結＋backslash を忠実再現。`>`/`>>` を演算子分離し redirect-target を同定。
  - ユニット C `_word_is_cp(value)`: 語の literal value が CP か = 既存 `CONTROL_PLANE` 正規表現マッチ **OR** bare-name 厳密一致（`^(\./)?(hooks|scripts|templates)/?$` および root 絶対形 `${ROOT}`/`${ROOT_REAL}` 直下の同名ディレクトリ）。
  - ユニット D fail-closed フォールバック（pure-bash）: python3 不在かつクォート/バックスラッシュ含む → mention=true。

## インターフェース定義

- ユニット間の契約:
  - `cmd_token_mentions_cp(cmd: str) -> rc`: 0=CP mention あり（deny-eligible）、1=なし。副作用なし。
  - 語分割 → (operands[], redirect_targets[]) を内部表現として返す（NUL/改行区切りで bash に受け渡し）。
  - `_word_is_cp(value: str) -> rc`: 0=CP、1=非CP。
- 公開 API: なし（フック内部関数のみ）。既存 `_text_mentions_cp` / `CONTROL_PLANE` を再利用。

## データフロー / 構造

- 入力: 抽出済み `$CMD`（既存どおり python3-first 抽出＋改行→`;` 正規化済み）。
- 処理:
  1. `cmd_mentions_control_plane` の既存 (a)(b)(c) を実行（無改変）。
  2. mention 未検出のとき末尾で `cmd_token_mentions_cp` を実行。
     - cmdsub/backtick 含む → 何もしない（既存 raw fail-closed が担当済み）。
     - 語分割（python3 shlex / fail-closed）。
     - **redirect-target** 語が CP → return 0（echo でも書込みは書込み）。
     - **operand** 語が CP → return 0、ただし「先頭語（先頭の `VAR=` 代入と flag を読み飛ばした最初の語）が `echo`/`printf`/`git commit`」かつ「chain 演算子 `;&|` 無し」なら救済（OBS-006・既存 (c) と同一規約）。
  3. mention=true なら既存下流へ流れ、read-only carve-out（`ls/cat/grep/find/wc/stat...` ＋ write indicator 無し）が安全 read を救済、最終的に write/delete 形のみ deny。
- 出力: `emit_allow` / `emit_ask` / `emit_deny`（既存 emit のみ。新規出力経路なし）。

## 依存関係

- 依存方向: `check-control-plane.sh` → `lib/{safety,extract-input,emit,frontmatter}.sh`（既存・不変）。新関数は同ファイル内・既存 `CONTROL_PLANE`/`_text_mentions_cp` を参照。循環なし。
- 外部依存: python3（既存 extract と同じ前提・あくまで優先で不在時 fail-closed）。新規外部依存なし。
- 配布: 新規ファイルなし＝setup.sh copy_hooks 変更不要。mirror `examples/minimal-project/hooks/check-control-plane.sh` を同期（`make example` / `sync_example_mirror.py` で検証）。

## エラーハンドリング

- 想定失敗と対応（すべて fail-closed＝deny 側）:
  - python3 不在 かつ クォート(`'"`)/バックスラッシュ(`\`)含む → mention=true。
  - python3 不在 かつ 上記メタ文字なし（bare-dir 系）→ pure-bash 語分割で判定可（python3 不要）。
  - shlex `ValueError`（unbalanced quote 等）→ mention=true。
  - cmdsub/backtick → augment 非実行（既存 raw fail-closed に委譲）。
- エラー伝播の方針: 不確実は必ず deny-eligible（mention=true）に倒す。allow 側に倒さない。

## テスト戦略

- 単体（end-to-end フック・JSON stdin で実走＝SF-001 の粒度に一致。`task_type=feature` 文脈）:
  - RED→GREEN（deny 化を実証）: `cp x hooks""/lib/emit.sh`・`"ho""oks/lib/emit.sh"`・`'hoo'ks/lib/emit.sh`・`hooks"/"lib/emit.sh`・`hooks\/lib/emit.sh`・`echo evil > "hoo""ks/lib/emit.sh"`・`cp evil "STAT"US.md`・`echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh`・`find . -name x -exec cp {} "hoo"ks/lib/emit.sh \;`・`find hooks -type f -exec rm {} +`・`rm -rf hooks`・`cp evil hooks`。
- 結合/回帰（緑維持を実証）: 既存 moat テスト全部・REDTEAM(18/18 + 5/5)・full suite・contract（全 profile）・drift・mirror・scaffold smoke。
- エッジケース（**allow のまま**を実証＝偽陽性ゼロ）: `git commit -m "update STATUS.md handling"`・`echo 'see hooks/' >> notes.txt`・`ls hooks`・`cat hooks/lib/emit.sh`（read）・`MY_VAR=safe make build`・`task_type=framework` 時の全 allow。
- 既知残（記録のみ）: bare `cd hooks`/`pushd hooks` は deny になりうる（fail-safe・非framework に正当用途なし）。
- 手動確認: orig(現 HEAD) vs new で全 repro を実走差分。security 盲検2次が独立に再実行。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-18-sf-001-cp-token-bypass-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

---

## 改訂（iteration 32 review・盲検 break-attempt 由来）

当初の「リテラル形を正規表現でマッチ」する Sub-check 設計は、盲検レビューの能動的 break-attempt で**3つの追加 Critical**（いずれも pre-existing クラスの取りこぼし）を露呈した。リテラル形の列挙は whack-a-mole で収束しないため、**Sub-check 2 を path-resolution に再設計**（ユーザー合意）。

### 検出された追加 Critical（実走確認）

- **F-1**: 末尾スラッシュ無しの絶対 root パス bare-dir（`rm -rf ${ROOT}/hooks`）が allow。設計 unit C が約束した abs 形が未配線（grill-code で消した `_word_is_cp` が唯一の経路だった）。
- **F-2**: ANSI-C `$'...'` クォート（`rm -rf $'hook\x73'`）が allow。shlex(posix) は `$'...'` を展開しない。
- **F-3**: パス正規化（`.//hooks`・`/./hooks`・`foo/../hooks`）と `$PWD/hooks` が allow（ROOT 知識不要・`echo > .//hooks/lib/emit.sh` で moat 全崩壊）。`CONTROL_PLANE` 左境界 `[^A-Za-z0-9_./-]` が `/` を除外し、`(\./)*` が単一 `./` のみ想定だったため。

### 最終アーキテクチャ（path-resolution・単一検出器）

- Sub-check 1（bash 語境界正規表現）と python の `bare` 集合を**廃止し python の単一検出器に統合**（保守性レビューが指摘した二重ロジックの drift を解消）。
- **ゲート**: `*hooks*|*scripts*|*templates*|*'*|*"*|*\*` を含むときだけ python 実行（CP ディレクトリへ解決し得る命令のみ・per-command spawn を抑制）。
- **python**: `decode_ansic` で `$'...'` を literal 化 → `shlex` で語分割（redirect-target/operand 分類）→ 各語を **resolve**: `$PWD`/`${PWD}`→ROOT 展開（cwd は信用せず ROOT 相対に固定＝`cd` チェーン耐性）、相対は ROOT 連結、`os.path.normpath` で `.`/`..`/`//` を畳み、**実 CP ディレクトリの絶対パス**（ROOT・ROOT_REAL 配下の hooks/scripts/templates）と一致/配下判定。STATUS.md/CLAUDE.md/.claude は正規化に強い非アンカー正規表現を維持。redirect-target は常に・operand は echo/printf/git commit ＋ chain 無しで救済。
- **fail-closed**: python 非ゼロ終了（ValueError 含む）/不在は mention 扱い。cmdsub/backtick は上流 raw に委譲。
- **var-built ASK の順序修正**: `cmd_var_built_write` の ASK を cmd_mentions 判定・`task_type=framework` allow より**前に独立発火**（難読化 CP 書込みは framework でも常に ASK）。path-resolving augment が `printf -v D %s hooks`（REDTEAM-02）の**データ引数** `hooks` を mention と誤認して ASK を短絡する回帰を封じる。

### スコープ

- F-1/F-2/F-3 は本タスクで修正（path-resolution に内包）。
- glob（`rm -rf hooks*`）は引き続き `SF-002` として繰延（別クラス・別タスク）。
- `$PWD` 以外の外部 `$VAR`（`$FOO/hooks`）は静的に解決不能＝既存 `cmd_var_built_write` の ASK 領域（代入を伴う場合）。残余リスクとして記録。

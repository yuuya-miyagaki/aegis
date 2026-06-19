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

### 追加改訂（review round3・F-4 cmdsub/var）

round3 の盲検 break-attempt が **F-4: cmdsub 経由 bare-dir**（`rm -rf $(pwd)/hooks`・`` `pwd`/hooks ``・`$(echo hooks)/lib`）を検出。当初「cmdsub は原理的に静的解決不能」と整理したが、**ユーザーの指摘で再検証**した結果これは不正確で、大半は解決可能と判明（プロトタイプで実証）。augment を **3-verdict（deny/ask/none）＋ unknown 展開の sentinel 化**に拡張:

- **cmdsub bail を廃止**。shlex 前に whole-command を置換: `pwd`/`$PWD`/`$(pwd)`/`` `pwd` `` → ROOT（cwd・副作用ゼロ）、その他の `$(...)`/backtick/`$VAR`/`${VAR}` → 不透明 sentinel（`\x01`・`/` を含まない）。これで `$(...)` の括弧で shlex(punctuation_chars) が割れる問題も回避。
- 各語を classify: 完全解決して実 CP 絶対パス＝**deny**／sentinel（未知前置）の後に CP ディレクトリ名が path component として残る＝**ask**（cwd/root かもしれない）／それ以外＝none。
- security: CP **リテラル**を含む cmdsub は上流 `cmd_mentions_control_plane` の raw 分岐が先に deny するため、augment に到達する cmdsub コマンドは CP リテラルを持たない＝sentinel 化は実行される書込みを隠さない。
- main flow: literal-CP(deny) > var-built(ask) > **augment verdict（deny/ask/none）** > allow。python 非ゼロ終了は fail-closed(deny)。
- python 正規表現内のバックティックは `$(...)` ラップ heredoc 内でリテラル backtick が bash パーサを壊すため `\x60`（hex）で表記。

**真の残余（accepted）**: `$(echo hooks)/lib` ＝ CP ディレクトリ名が**不透明な cmdsub の中に消える**形。静的に名前を復元できず（cmdsub を実行しない限り）、かつ「accidental 書込み防止」という moat の脅威モデル外の**意図的難読化**（どの静的 moat も同じ／敵対エージェントは無限に回避路を持つ）。`docs/security-followups.md` SF-003 に記録。

検証: 全再構成機構の網羅的敵対行列（BLOCK 24＝quote/backslash/ANSI-C/bare/abs/normalize/$PWD/$(pwd)/`pwd`/unknown-ask/$VAR-ask/write-utils/redirect 変種、ALLOW 15＝reads/non-CP/messages/cmdsub-source/residual/~ ）を実走で ALL OK（誤検知ゼロ）。

### 追加改訂（review round4・F-5 param-default ＋ F-6 brace）

round4 の盲検 break-attempt が **F-5: パラメータ展開デフォルト**（`rm -rf ${X:-hooks}`＝X 未設定時に静的リテラル `hooks` へ展開）を検出。`hooks` はコマンドに**静的に見えている**のに `_VAR` sentinel が `${X:-hooks}` 全体を潰して取りこぼしていた（SF-003 残余＝名前が動的 cmdsub に消える、より悪い）。ユーザー合意で **静的リテラルを露出する展開形を包括的に閉じる**:

- **param-default**: shlex 前に `${VAR:-LIT}`/`:=`/`:+`/`-`/`+` の **LIT（静的デフォルト）を解決**（sentinel 化しない）。`${X:-hooks}`→`hooks`→deny。`${X:-/tmp/safe}`→none。pwd 展開の後・cmdsub/var sentinel の前に適用。VAR が CP に set される稀形は外部変数残余（既存 `cmd_var_built_write` 領域）。
- **F-6 brace 展開**: classify を `classify_one`＋brace ラッパに分割。単一 flat `{a,b,c}` を**シェルの alternatives として展開**し各候補を classify して worst を取る（`rm -rf {hooks,build}`→deny／`{a,b}`→none）。nested/multi-brace は保守的に「CP 名が brace/path token に出れば ask」。
- 保守性 minor 3 件反映: `\x60`（backtick hex）の理由を**インラインコメント**化／sentinel `\x01` 衝突＝over-eager ask（fail-safe）を明記／python 真の不在＝none（framework hard 依存）を `command -v` コメントに明記。

検証: 拡張敵対行列（BLOCK 17＝param-default 5・brace 3・nested cmdsub・`${PWD}`・全前クラス、ALLOW 14＝non-CP default/brace・reads・messages・cmdsub-source・residual・~）を実走で **ALL OK**（誤検知ゼロ）。CP テスト 163 件・REDTEAM 18/18+5/5。

**収束の論拠**: 静的リテラルを露出する再構成形（quoting/escaping/ANSI-C/param-default/brace）は有界で全て閉じた。残るは **runtime 値依存**（cmdsub 出力・外部 $VAR 値・`$(echo hooks)/lib`＝SF-003／glob=SF-002）＝既に ask/sentinel/residual で処理済み。任意の静的 moat が持つ本質的限界で、敵対エージェントは無限に回避路を持つ（moat はサンドボックスではない）。

---

## 継続メモ（次セッション resume・/clear 後に最初に読む）

> iteration 32 / phase=review の継続。ユーザー判断 = **obscure な静的バイパス形も徹底的に閉じる**（コンテキスト肥大のため /clear or コンパクション後に再開）。現在 HEAD=`1644cd3`・作業ツリー clean・未 push。

### 現状サマリ
- SF-001（control-plane フックがシェル再構成 CP 書込みを取りこぼす）を path-resolution で修正中。盲検 break-attempt 5 ラウンドで F-1〜F-6 を検出→全閉鎖（commits 9c7624f/ec7587e/e0d21d8/ac0ecac/1644cd3）。
- 保守性 2 次レビュー(round5)=approve_with_notes（構造健全・minor のみ・反映済 or 任意）。
- 版 1.12.0（4 箇所: scripts/check_framework_contract.py / templates/STATUS.template.md / examples/minimal-project/docs/STATUS.md / docs/STATUS.md）。

### 今 OPEN（round5 で発見・最優先で閉じる）
1. **tilde-plus**: `rm -rf ~+/hooks` → ALLOW。bash で `~+`=PWD。修正: `~+`(末尾 `/` or 単独)→ROOT を `_PWD` 正規表現に追加（`~-`=OLDPWD は unknown→sentinel/ask、`~`=HOME は CP でない）。
2. **入れ子 param-default**: `${X:-${Y:-hooks}}` → ALLOW。`_PARAM.sub` が単一 pass で入れ子を解決しきれない。修正: `_PARAM` 置換を `_CMDSUB` と同様に fixpoint ループ化（while prev != cmd）。

### 次に確認すべき obscure 候補（round6 を先回り）
- indirect `${!ref}`／`$OLDPWD`・`~-`／`${X#pat}`・`${X%pat}`・`${X/a/b}`（VAR 値依存→sentinel/ask で良いはず・要実走確認）。
- multi-group brace `{a,b}{hooks,c}` は現状 over-ASK（fail-safe・展開は ahooks/bhooks で実は非CP）＝精緻化は低優先。
- process substitution `<(...)`/`>(...)`、`exec`/`eval`/`xargs` 経由、ANSI-C × param/brace 組合せ。
- `${X:?hooks}`=正しく allow（X 未設定でエラー・書込まない）。glob `hooks*`=SF-002。

### 作業手順（各 obscure 形ごと）
TDD: tests/test_control_plane_token_split.py に RED テスト追加→fix（augment は `cmd_token_verdict`・置換順序 `_PWD`→`_PARAM`→`_CMDSUB`ループ→`_VAR`・`classify_one`+`classify`(brace)）→GREEN→敵対行列→REDTEAM→mirror→full suite→盲検レビュー再ディスパッチ。静的リテラル露出形は**解決**、runtime 値依存は **sentinel→ask**、CP リテラル cmdsub は上流 raw 分岐が deny。

### 検証コマンド
- 対象: `python3 -m pytest tests/test_control_plane_token_split.py tests/test_control_plane_allowlist.py tests/test_control_plane_var_expansion.py tests/test_destructive_recursive.py "tests/test_check_status.py::TestControlPlaneRealisticInput" -q`
- REDTEAM: `bash tests/poc/v162-redteam-rerun.sh; bash tests/poc/v163-redteam.sh`（18/18+5/5）
- mirror: `make example && python3 scripts/check_reference_drift.py`／contract: `python3 scripts/check_framework_contract.py`／status: `python3 scripts/check_status.py --root .`
- full suite: `python3 -m pytest tests/ -q`（~3min・baseline 892 passed/1 skip・bg 実行推奨）
- 敵対行列: temp root に task_type=feature の docs/STATUS.md＋hook＋lib(extract-input/emit/safety/frontmatter) symlink を置き JSON stdin で実走する python ハーネス（既存パターン）。

### ツール gotcha（重要）
Bash ツールの**コマンド文字列**に `${...}`・`~+`・`:-`・brace `{...}` 等を含めると、ツール側パースエラー（"undefined is not an object (evaluating 'H.replace')"）で呼び出しが中断することがある。回避: そうしたコマンド/テストは **python ハーネス FILE**（Write→`python3 /tmp/x.py`）に入れる。git commit は **`git commit -F <msgfile>`**（メッセージは Write で作成）。reviewer サブエージェントにも同 gotcha を伝える。

### gates/phase
phase=review。brainstorm+plan=approved、review/qa/security/deploy=pending。obscure 形を閉じ切ったら盲検 break-attempt が新形を出さなくなるのを確認→review gate 承認→qa→security（盲検2次必須）→deploy→ship→docs。push は明示承認まで禁止。failure_tracking は review 通過時に null へ。

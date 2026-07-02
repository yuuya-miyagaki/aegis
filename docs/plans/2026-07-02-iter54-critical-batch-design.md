# iter54 設計: ドッグフード前 Critical バッチ修正

> 作成日: 2026-07-02
> task_type: framework / size: L
> 出典: 2026-07-02 徹底グリル（6並列＋自己再現）。詳細は会話ログ／auto-memory `project-aegis-grill-2026-07-02`。
> ステータス: 設計承認済み（ユーザー「おすすめですすめて」＋スコープ確認）。
> grill-plan 済み（2026-07-02・致命5件を反映: 高速ゲート fold／-ef プローブ／
> required ループ rc 検査／対称 -i／quoted 残存 fail-closed 仕様＋judge 裏取り確定。
> 要検討: v1.15.0 bump・FS 依存2層テスト戦略・env 明示代入を追記）。

## 背景・目的

実ドッグフード（予約LP）を `bin/setup.sh` で repo 外に導入して日本語で運用開始する直前。
グリルで、**あなたの実運用環境（macOS＋日本語＋setup.sh 導入）で確実に踏む Critical**
が複数見つかった。導入前に束ねて潰す。構造リアーキ（文字列判定→FS解決/OS-lock 昇格で
894行 `check-control-plane.sh` 退役）は**別テーマ**に切り出し、本イテレーションは
「最小の正しい hotfix」に留める（YAGNI・スコープ肥大回避）。

## スコープ（6件）

| ID | 重大度 | 対象 | 症状（再現済み） |
|----|--------|------|------------------|
| C-1 | 🔴 Critical | `check-control-plane.sh` / `check-gate.sh` / `check-secrets.sh` | ケース非依存FS（macOS）で `cp evil HOOKS/lib/emit.sh`・`git add key.PEM` が allow。moat＋secret ガード両方バイパス。SF-001〜009 未カバーの新規クラス |
| C-2 | 🔴 Critical | `bin/setup.sh` | 壊れ profile JSON／パス中の `'` で「Setup complete.」rc0 なのに CLAUDE.md/settings/hooks 未install＝moat ゼロ（fail-open） |
| C-3 | 🔴 Critical | `bin/setup.sh` | `--force` が STATUS.md/CLAUDE.md を無バックアップ上書き＝運用状態のデータ損失 |
| C-4 | 🔴 Critical | `scripts/run-test-strength-drill.py`（＋`build-judge-card.py` 要確認） | git 呼びに `quotepath=off` 欠落＝日本語ファイル名の追加行を judge secret スキャナが黙ってスキップ＝security ゲート false-green（silent-green） |
| S-glob-1 | 🟡 Should | `check-destructive.sh:64` | `for target in $SAFE_TARGETS` の glob 展開で cwd が build/dist のみだと `rm -rf *` が「安全成果物のみ」判定＝警告漏れ（fail-open） |
| S-glob-2 | 🟡 Should | `check-gate.sh:61` | `for seg in $p` の glob 展開で Next.js `app/[id]/page.tsx` を `app/d/i/page.tsx` に歪める（誤判定リスク） |
| C-1b | 🔴 Critical | `hooks/post-status-audit.sh:80` | （grill-code で追加発見）target filter `*STATUS.md` が case-sensitive＝macOS で `Edit(docs/STATUS.MD)` の gate/task tamper が監査ごとスキップ。C-1 と同一クラス。probe 条件付き fold で修正 |

## 各修正の設計

### C-1 ケース非依存 case-fold（条件付き）

**方針**: 「常に fold」ではなく **FSのケース非依存性を1回検出して条件付き fold**。
- control-plane 名は全て既知の固定小文字（`hooks`/`scripts`/`templates`/`.claude`/`CLAUDE.md`/`STATUS.md`）。
- 検出プローブ（grill 穴2 反映）: `[ -d "$ROOT/HOOKS" ] && [ "$ROOT/HOOKS" -ef "$ROOT/hooks" ]`。
  `-d` 単独だと case-sensitive FS に実在するユーザー所有の別 dir `HOOKS/` を誤検知して
  false-deny に巻き込むため、**同一 device+inode（`-ef`）確認を必須**とする。
  case-insensitive FS では HOOKS→hooks が同一 inode で真。2 stat で安価。
  **macOS で作動確認済み**（2026-07-02）。
- 共有ヘルパ `aegis_fs_case_insensitive <root>` を **`hooks/lib/safety.sh`** に追加
  （3 deny hook が全て冒頭で source 済み＝DRY・重複回避）。返り値 0/1。
- env 攻撃面（grill 要検討3）: 検出結果はセッション env から**継承しない**。hook が毎回
  プローブを実行し、python 子プロセスへは `AEGIS_CASE_INSENSITIVE=<probe結果>` を
  **呼び出し時に明示代入**して渡す（session env に `=0` を仕込む弱体化を封じる）。
- テスト用オーバーライド（実装で確定）: `AEGIS_CASE_FOLD_FORCE=1` はプローブ結果に
  かかわらず fold を**強制 ON**にする **strengthen-only** の env（deny を広げる方向のみ。
  OFF 側の env は意図的に存在しない）。これにより bash hook の fold 経路も
  どの FS でも決定論的にテスト可能（skipif が必要なのはプローブ自体の実測テストのみ）。
- 適用:
  - `check-control-plane.sh`:
    - `_text_mentions_cp` の `grep -qE` → 検出時 `grep -qiE`／fixed-string `grep -qF` → `grep -qiF`。
    - **`cmd_token_verdict` の bash 高速ゲート（`:244` の `case "$cmd" in *hooks*|...`）も fold 必須**
      （grill 穴1）: このゲートは小文字リテラル前提で、bare `rm -rf HOOKS` や `$PWD/HOOKS` は
      クォートもグロブも含まず `echo none` で python resolver 未起動のまま素通りする
      （regex 層はスラッシュ付き `hooks/` しか拾わない）。検出時は
      `tr '[:upper:]' '[:lower:]'` した文字列でゲート判定する。
    - python resolver は `AEGIS_CASE_INSENSITIVE` env を受け casefold 比較に切替
      （cp_targets/cp_glob 前方一致・fnmatch・cp_re は `re.IGNORECASE` 再コンパイル、全経路）。
  - `check-gate.sh`: `is_protected_dir`／`is_control_file`／ROOT-external 判定の `case` を
    検出時 `shopt -s nocasematch` で囲む（save/restore で局所化）。
  - `check-secrets.sh`: `.env` 以外の credential grep（`:109`/`:200`/`:205`）に `-i`、
    broad-stage の `find -name` を `-iname` に（case-sensitive Linux でも実鍵名の大文字を捕捉＝純増・無条件適用）。
    **対称性（grill 穴4）**: 陽性 grep を `-i` 化する箇所では、対になる safe-variant 除外
    （`:205` の `grep -vE "${SAFE_ENV_SUFFIXES}$"`）と strip（`:118`/`:233`/`:246` の sed）も
    同等に case-fold する（`.ENV.EXAMPLE` が陽性にだけ引っかかる false-deny を防ぐ）。
    sed の `I` フラグは GNU 拡張のため、POSIX 互換の文字クラス書法（`[eE]` 等）か
    パターン変数の -i 対応版を用意する。
- **case-sensitive Linux**: プローブ偽＝現行挙動据置（`HOOKS/` はユーザー所有の別 dir＝誤ブロックしない）。
- **残余（非スコープ・security レポートに明記）**: 大文字コマンド名（`CP`/`MV` 等が exec の
  FS lookup で /bin/cp に解決する経路）は write-indicator regex が小文字前提のまま。
  mention/redirect 層で大半は deny-eligible になるため受容。
- **非スコープ**: FS 実解決（realpath＋inode 比較）による構造リアーキは別テーマ。

### C-2 fail-open install の封鎖（`bin/setup.sh`）

1. profile JSON を**冒頭（`-f` チェック直後）**で `python3 -c 'import json,sys;json.load(open(sys.argv[1]))'`
   検証。失敗時は明示エラー＋`exit 1`（fail-closed）。
2. Python への全パス引き渡しを**argv 経由**に統一（`parse_json_array`/`copy_hooks`/`generate_settings`）。
   `:116-122` の version heredoc で確立済みの手法を横展開＝`'`/`\` を含むパスで壊れない。
3. `copy_hooks`/`generate_settings` の `... 2>/dev/null) || return 0` を、
   「キー不在（正常）」と「python 失敗（中断）」で分岐。
4. **`required`/`recommended` ループの rc 検査（grill 穴3）**: `:538-541` の
   `while ... < <(parse_json_array ...)` は process substitution の失敗が伝播しない
   （K-10 コメントが自認する経路）。`required=$(parse_json_array ...) || { echo ERROR >&2; exit 1; }`
   の capture-with-rc-check 形へ書き換え（`recommended` の `|| true` も
   「空 = 正常 / rc≠0 = 中断」に分岐）。完了条件: **全 parse_json_array 呼び出しが rc 検査済み**。

### C-3 `--force` データ損失（`bin/setup.sh`）

- `copy_file` の FORCE 経路で、宛先が存在し内容差分があれば上書き前に
  `cp "$dst" "${dst}.bak.$(date +%s)"`、`OVERWRITE (user file, backed up)` を明示出力。
- framework 所有用 `copy_file_force:184-193` の D3 哲学（差分時のみ .bak）をユーザー所有ファイルにも適用。
- **挙動保存の最小差分（grill 要検討4）**: FORCE＋同一内容のときは .bak を作らないが、
  copy 自体・`COPY:` 出力・INSTALLED_PATHS 追加は現状どおり維持
  （copy_file_force 型の early-return には**しない**）。
- 同一秒再installの `.bak` 衝突は既存 `copy_file_force` と同挙動＝本イテレーションでは踏襲（別途 Nice-to-have）。

### C-4 quotepath（`scripts/run-test-strength-drill.py`）

- `_tracked_added_lines`（`:98-99` git diff）・`_untracked_files`（`:128-129` git ls-files）の
  git 呼びに `-c core.quotepath=off` を追加（`fingerprint.sh:54` と同型）。
- **quoted 残存の fail-closed 仕様（grill 穴5）**: `quotepath=off` 後も git は制御文字入り名を
  quote する。先頭 `"` のパスを検出したら **`DrillError` を raise**（drill=BLOCKED／
  judge は except 経由で 🟡＋理由表示）— `continue` の silent skip は同型の穴なので禁止。
  あわせて `_untracked_files` の subprocess にも `errors="replace"` を統一し、
  置換文字 `�` を含むパスも同様に DrillError へ倒す。
- **`build-judge-card.py` は修正不要（裏取り済・grill 穴5c）**: パスを emit する直接の
  git 呼びは無い（fingerprint は fingerprint.sh 委譲＝修正済／patterns.sh 読みはパス非依存／
  秘密スキャン・stub スキャンは drill モジュールの added_lines_by_file 経由＝drill 側修正が伝播）。

### S-glob-1 / S-glob-2 glob 展開封鎖

- `check-destructive.sh` の `SAFE_TARGETS` ループと `check-gate.sh` の `normalize_target`
  ループを `set -f`（noglob）で囲む（前後で save/restore）。挙動保存リファクタ。

## テスト方針（TDD RED-first）

- C-1: ケース variant fixture（`HOOKS/`・`CLAUDE.MD`・`key.PEM`・broad-stage 大文字鍵名・
  **bare `rm -rf HOOKS`（高速ゲート fold の検証）**）で deny/ask を assert。
  case-sensitive 経路の非退行も（プローブ偽の分岐）。
  **`.ENV.EXAMPLE` が deny されない**（対称 -i）も assert。
- **FS 依存の2層戦略（grill 要検討2）**: bash hook の case-fold 挙動テストは
  case-insensitive FS でしか再現できないため、tmpdir プローブ（`-ef` 同型）で判定する
  `pytest.mark.skipif` を付ける（macOS 開発機では実測される）。python resolver 経路は
  `AEGIS_CASE_INSENSITIVE=1` の env 注入でどの FS でも決定論的にテストする。
  プローブヘルパ自体（`-ef` の別 dir 弁別）は case-sensitive/insensitive 両分岐を
  fixture でテスト（case-sensitive 側は tmpdir に実在の `HOOKS`/`hooks` 別 dir を作れた時のみ）。
- C-2: 壊れ profile JSON→rc≠0 assert／`'` 入りパス→install 完遂 assert（CLAUDE.md/settings/hooks 実在）。
- C-3: user file 編集→`--force`→`.bak` 生成＋内容保全を assert。
- C-4: 日本語ファイル名（`テスト.py`）に追加行→drill/judge が正しく scan/mutant を認識する fixture。
  制御文字入りファイル名（quoted 残存）→ DrillError（fail-closed）も assert。
- S-glob: cwd 汚染下で `rm -rf *` が警告される／`[id]` パスが歪まない assert。
- 実行は**素の pytest**（本セッションは親 dir で aegis 自身の hooks/ゲートは非発火）。

## バージョン（grill 要検討1）

deny hook の判定挙動が変わる（case-fold・noglob）＝moat 変更を含むため、
`FRAMEWORK_VERSION` を **1.14.0 → 1.15.0** に上げる（iter51-53 の「据置」は
hook 判定ロジック不変が理由だった。今回は変わるので minor bump）。

## 非スコープ（別テーマへ）

- 構造リアーキ: 文字列判定→FS解決/OS-lock 昇格・894行 `check-control-plane.sh` 退役。
- プロンプト層の意味ドリフト（ship-and-docs n/a・state-machine 表・review-gate skill 等）。
- モデル manifest の Fable 5 再ティア。
- CI 新設・テスト分離リーク・その他 Should-fix/Nice-to-have。

## 完了条件

- 6件が RED-first で緑化・全既存テスト緑・grill-code 自己グリル通過。
- `aegis/docs/STATUS.md` を記録として更新。
- feat コミット作成（**push 手前で停止しユーザー確認**）。

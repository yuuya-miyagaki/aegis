# grill 🟢残余 小修正バッチ 設計ノート（v1.5.1）

日付: 2026-06-11 ／ 種別: framework patch ／ task_size: L（ミラー・テスト込み 12 ファイル前後）

## 1. 背景と出典

v1.4.0／v1.5.0 の grill-code で 🟢（任意・記録のみ）とされた残余 5 件を 1 バッチで解消する。
出典: `docs/qa-reports/v140-review.md`（🟢所見）、`docs/qa-reports/v140-security.md`・
`docs/qa-reports/v150-security.md`（残余リスク記録）。

5 件はいずれも fail-closed 方向（放置しても偽 green にはならない）だが、
T5(b) のみ「防御の実穴」（control-plane 書込バイパス）であり優先度が最も高い。

## 2. 各件の設計

### T1: false-RED 緩和 — テストランナー分類のコマンド先頭位置アンカー

- **問題**: `hooks/lib/patterns.sh` の `AEGIS_TEST_RUNNER_REGEX` が「文字列中のどこかに
  ランナー名」で一致するため、`grep vitest package.json`（rc=1、一致なし）の失敗が
  fail 記録→judge が最新テスト行と誤分類→🔴 になる。
- **変更**: 左境界を「コマンド位置」に強化する。ランナー名は (1) 文字列先頭、
  (2) `;` `&` `|` `(` の直後（空白許容）、(3) env 代入プレフィックス
  （`FOO=bar `、0 回以上）越し、(4) 既存どおり `npx ` 越し、のいずれかでのみ一致:

  ```
  旧: (^|[^a-zA-Z0-9_])(npx +)?vitest($|[^a-zA-Z0-9_])
  新: (^|[;&|(] *)([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*(ランナーラッパー)?vitest($|[^a-zA-Z0-9_])
      ランナーラッパー = ((npx|bunx) +|(uv|poetry|pipenv) +run +)
  ```

  7 パターン全てに同じ接頭部を適用する（`pytest`／`python3? +-m +unittest`／
  `cargo +test`／`go +test`／`(npm|pnpm|bun|yarn) +(run +)?test...` も同様）。
  頻出形 `python3? +-m +pytest` を 8 個目のパターンとして追加する（grill-plan 🟡-1）。
- **改行の正規化（grill-plan 🔴-1）**: `^` の意味が grep（行単位＝各行頭）と Python re
  （文字列先頭のみ）で異なり、複数行コマンド（`echo build done\nvitest run`）で
  パリティが割れる。**パターンはエンジン純粋のまま**とし、両消費者が照合前に
  改行を `;` に正規化する（post-bash.sh は `tr '\n' ';'`、build-judge-card.py は
  `cmd.replace("\n", ";")`）。`tests/test_patterns_parity.py` に複数行 fixture を追加。
- **制約**: BSD/GNU `grep -E` ∩ Python `re` の共通サブセット（`\b`・`[[:space:]]` 禁止、
  リテラル空白を使用）。`tests/test_patterns_parity.py` に fixture を追加。
- **既存 fixture の反転（grill-plan 🟡-2）**: `tests/test_patterns_parity.py` の
  `("echo pytest", True)` は新規則で `False` に変わる。これは挙動契約の意図的な
  書換えであり、fixture の期待値更新と CHANGELOG（README Migration 節）への明記を
  実装タスクに含める。
- **既知の不一致（受容）**: 空白入りクォート env 値（`NODE_OPTIONS="-a -b" jest`）・
  タブ区切り・`bash -c "pytest"` 等のラッパー形は不一致＝unverified 方向（fail-closed）。
- **挙動変化の境界**:
  - 一致しなくなる（false-RED 解消）: `grep vitest package.json`、`echo "pytest done"`、
    `cat jest.config.js`（引数・クォート内・読取り対象としての言及）
  - 一致が残る: `vitest run`、`cd app && vitest`、`CI=1 pytest -x`、`npx jest`
  - 取りこぼし（許容）: `bash -c "pytest"`、`time pytest` 等のラッパー形は不一致
    → テストと分類されない＝unverified 方向（fail-closed）なので安全。必要なら
    実テストを直接実行すれば green になる。
- **消費者**: `hooks/post-bash.sh`（ReAct ヒント）と `scripts/build-judge-card.py`
  （`read_test_result`）の両方が patterns.sh を単一ソースとするため、1 修正で両直り。

### T2: check-deploy-gate の stderr 分離

- **問題**: `hooks/check-deploy-gate.sh:58` の `2>&1` で python の警告・traceback が
  ask/deny 文面に混入し得る（ASK 検出自体は行頭一致で安全）。
- **変更**: stdout と stderr を分離。`RESULT=$(python3 ... 2>"$ERR_FILE")` とし、
  - ASK 検出・ask/deny 文面は **stdout のみ** を使用
  - RC≠0 かつ stdout が空（interpreter 故障等）のときだけ stderr 内容を deny 文面に
    併合（診断性の維持。`2>/dev/null` 単純破棄は不採用）
  - 使用後に `rm -f "$ERR_FILE"` で削除（この hook に既存 trap はなく衝突しない）
- **mktemp 失敗の fail-open 封鎖（grill-plan 🔴-4）**: 本 hook は `set -euo pipefail` で、
  `ERR_FILE=$(mktemp)` の失敗は hook 即死＝PreToolUse の非ブロッキング扱いで
  **ゲート判定なしに deploy が通る**（F6 同型の silent fail-open）。
  `ERR_FILE=$(mktemp 2>/dev/null) || ERR_FILE=/dev/null` のフォールバックを必須とする
  （/dev/null 時は stderr 診断が落ちるだけで判定経路は維持）。
- **不変**: RC 契約（0=allow / 2+`ASK:`=ask / その他=deny）は変更しない。

### T3: update-gate の CURRENT 読込 TOCTOU 解消

- **問題**: `scripts/update-gate.sh` が CURRENT 値を読む（:83）のが排他ロック取得
  （:186-202）より前。書込は直列化済みで実害は「表示ログと事前検証の競合」のみ。
- **変更**: ロック取得ブロックを引数検証・STATUS_FILE 存在確認の直後
  （CURRENT 読込の前）へ移動する。読み→検証→書きが全てロック内に入る。
- **トレードオフ**: ロック保持時間が pre-approve の python 実行分（~1 秒）延びるが、
  CLI 用途では無害。早期 exit 経路（already approved 等）でも `trap ... EXIT` が
  解放するため漏れなし。
- **trap の更新（grill-plan 🔴-2）**: T4 で pid ファイルを置くため、現行 trap の
  `rmdir` 単発では**非空ディレクトリの削除が必ず失敗**しロックが残留する
  （正常終了でも stale 回収が常態経路化＝test_update_gate_lock.py の解放検証も破損）。
  trap を `rm -f "$LOCK_DIR/pid" 2>/dev/null; rmdir "$LOCK_DIR" 2>/dev/null || true`
  に更新する。

### T4: stale lock の PID ベース自動回収

- **問題**: kill -9 等でロックディレクトリが残ると以後 fail-closed 固着
  （手動削除ガイダンスのみ）。
- **変更**: PID ファイル方式＋**原子 mv による claim プロトコル**（grill-plan 🔴-3）。
  素朴な `rm -f pid && rmdir` は二重回収レースで排他が破れる（回収者 B の遅延 rm が
  別の回収者 C の再取得済みロックの pid を消し、B の rmdir が C の保持ロックを破壊
  ＝2 プロセス同時保持）。pid ファイルの mv（同一 fs 内 rename＝原子）で回収権を
  1 プロセスに限定する:
  1. ロック取得成功直後に `printf '%s' "$$" > "$LOCK_DIR/pid"` を記録（owner 側）
  2. 競合時（mkdir 失敗時）: `pid1=$(cat "$LOCK_DIR/pid" 2>/dev/null)` を読む。
     **pid1 が無い/空なら回収しない**（mkdir 直後の書込前ウィンドウ、または
     回収者クラッシュの残骸＝現行どおり手動ガイダンスへ fail-closed）
  3. `kill -0 "$pid1"` 成功（生存）なら回収しない（待機継続）
  4. 死亡なら `mv "$LOCK_DIR/pid" "$LOCK_DIR/pid.claim.$$"` で claim
     （mv 失敗＝他者が claim 中 → 待機継続）
  5. claim ファイルの中身が pid1 と一致するか検証。不一致（観測後に別回収者が
     回収→再取得していた＝生きた owner の pid を奪った）なら
     `mv` で元に戻して待機継続。一致なら `rm -f` claim → `rmdir "$LOCK_DIR"` → 待機
     ループ継続（次周の mkdir 競争へ。勝者は 1 プロセスのみ）
- **受容リスク**: (1) PID 再利用による「生存誤判定」→ 回収しないだけ＝現行と同じ
  fail-closed。(2) `kill -0` の EPERM（他ユーザー所有で生存）は死亡誤判定の理論可能性
  → ローカル CLI の同一ユーザー前提で受容。(3) 回収者が claim 後・rmdir 前に
  クラッシュ → pid 無しディレクトリが残り「回収しない」分岐＝手動ガイダンス
  （現行と同じ fail-closed、排他は破れない）。
- **文言更新（grill-plan 🟡-4）**: ロック取得失敗時のメッセージ
  「remove the stale directory」は自動回収導入後は pid 生存（=正当な並行実行）が
  主因になるため、「another live gate update (pid N) holds the lock — retry shortly」
  系へ更新。pid 無し残骸の場合のみ手動削除を案内する。

### T5: WRITE_INDICATORS の二点強化（check-control-plane.sh）

**(a) 左境界の追加（誤 deny 解消）**

- **問題**: `cp\s` `rm\s` `tee\s` `ln\s` 等に左境界がなく、`grep "confirm " hooks/x.sh`
  （confir**m␣**）、`grep "scp " ...`、`grep "vuln " ...` 等の正当読取りが誤 deny。
- **変更**: 単語形インジケータに `(^|[^A-Za-z0-9_])` の左境界を付与:

  ```
  旧: tee\s|cp\s|mv\s|chmod\s|rm\s|mkdir\s|touch\s|install\s|ln\s
  新: (^|[^A-Za-z0-9_])(tee|cp|mv|chmod|rm|mkdir|touch|install|ln)\s
  ```

  `sed\s+-i` も同様に境界化。関数呼出し形（`write_text` 等）は現行維持。
- **不変条件**: 現行で検知できる書込形（`cat x | tee hooks/y` は chain で別途 deny、
  read-only 先頭からの `find ... cp` 類）が全て検知のまま残ることをテストで固定。

**(b) find 実行系フラグの封鎖（実穴の修正）**

- **問題**: `find hooks/ -name "*.sh" -exec truncate -s 0 {} +` が read-only 判定を
  すり抜ける（`find` は READ_ONLY_STARTS、`-exec ... +` は `;` を含まないため
  CHAIN_OPS も通過、truncate のシェル形は WRITE_INDICATORS 外）。`-exec dd of={} +`
  も同様＝**control-plane 書込の実バイパス**（コード読解＋一致検証で確認済み）。
- **変更**: 穴の本質は truncate/dd ではなく **find の実行系フラグ**。WRITE_INDICATORS に
  find の書込能力フラグを**左境界付き**で追加する（grill-plan 🟡-3 反映）:

  ```
  (^|[^A-Za-z0-9_])-(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)($|[^A-Za-z0-9_])
  ```

  - 左境界の理由: (1) 境界なしでは `cat hooks/pre-exec.log`・`cat hooks/on-delete.sh`
    等のファイル名言及が誤 deny になる（実験で確認済み）。(2) 既存 WRITE_INDICATORS
    変数への連結で使う（先頭 `-` で始まる単独パターンを `grep -qE` に渡すと BSD grep
    が invalid option で rc=2 死→ `!` 否定で **allow＝fail-open** になる地雷を回避）。
  - 攻撃形は deny 維持: `find hooks/ -exec dd of={} +`（空白が左境界）、クォート
    バイパス `find hooks/ "-delete"`（`"` が左境界）— 実験で確認済み。
  - フラグ一覧は GNU/BSD find の副作用 action 全網羅を確認済み（`-printf`/`-print0`
    は stdout のみで対象外）。
- **不採用案**: truncate/dd のシェル語を直接追加 — `grep "truncate -s" hooks/x.sh` の
  正当読取りを誤爆させ（P3-4 で解消済みの過去問題が再発）、`-exec cp` 等の同型穴も残る。
- **受容トレードオフ**: `grep -e "-exec" hooks/x.sh` のような「フラグ文字列を検索する」
  読取りは誤 deny になるが、頻度は低く fail-closed 方向（Edit/Write は通常どおり可能）。

## 3. 横断方針

- **TDD**: 各件 RED→GREEN。既存テストの拡張先:
  `tests/test_patterns_parity.py`（T1 fixture）、`tests/test_hook_output_schema.py`／
  `tests/test_failure_policy.py`（T2・T5 実発火）、`tests/test_update_gate_lock.py`
  （T3・T4）。詳細なテスト配置は実装計画で確定。
- **ミラー契約**: `hooks/check-control-plane.sh`・`hooks/check-deploy-gate.sh`・
  `hooks/lib/patterns.sh`・`scripts/update-gate.sh` の変更は同一コミットで
  `examples/minimal-project/` へ byte-identical 同期。
- **ゲート**: task_size L → review/qa/security/deploy 全ゲート。
- **SemVer**: **patch（1.5.0 → 1.5.1）**。全て既存防御の強化・表示品質・誤判定緩和で、
  運用契約（公開契約）への追加・変更なし。
  - 注記: T1 は judge の分類規則の変更だが、tri-state の見え方・トークン契約は不変。
    分類が外れたコマンドは unverified 方向に倒れるのみ（fail-open しない）。

## 4. 検証計画（受入基準）

1. `grep vitest package.json` 失敗後に judge テスト行が 🔴 にならない（unverified または
   直前の有効記録を維持）。複数行コマンド（`echo x\nvitest run`）の分類が grep／
   Python で一致する（parity fixture）— T1
2. check-deploy-gate の deny/ask 文面に stderr 由来文字列が混入しない。mktemp 失敗
   経路でも判定が実行される（fail-open しない）— T2
3. CURRENT 読込がロック取得後に行われる構造をテストで固定（ロック保持中の別実行が
   CURRENT 読込前に待機/失敗する）— T3
4. 死んだ PID の stale lock が自動回収され、生きた PID では回収されない。正常終了で
   ロック（pid ファイル含む）が完全解放される（既存 test_update_gate_lock.py の
   解放検証を pid 対応に更新）— T4
5. `grep "confirm " hooks/x.sh` が allow、`find hooks/ -exec dd of={} +`・
   `find hooks/ "-delete"` が deny、`cat hooks/pre-exec.log` が allow — T5
6. 既存 436 tests・contract・drift・smoke 全 PASS（fixture の意図的反転
   `("echo pytest", True→False)` を除き回帰なし）

## 5. grill-plan 来歴（2026-06-11）

独立サブエージェント 1 本による敵対的レビュー（regex 実機実験付き）。
判定: 条件付き GO → 🔴4・🟡4 を本設計に全反映済み:

- 🔴-1 複数行コマンドの grep/Python パリティ割れ → 消費者側で改行→`;` 正規化（§T1）
- 🔴-2 pid ファイルが trap の rmdir を恒久的に殺す → trap を pid 削除込みに更新（§T3）
- 🔴-3 二重回収レースで排他が破れる → 原子 mv claim プロトコル（§T4）
- 🔴-4 mktemp 失敗で deploy ゲートが fail-open → /dev/null フォールバック（§T2）
- 🟡-1 `python -m pytest` 等の頻出形が green 退行 → パターン追加＋ラッパー接頭部（§T1）
- 🟡-2 既存 fixture `("echo pytest", True)` の反転が未記載 → 明記＋CHANGELOG 対象（§T1）
- 🟡-3 find フラグ regex の先頭 `-` 地雷とファイル名誤爆 → 左境界付与（§T5）
- 🟡-4 ロック失敗文言の陳腐化 → pid 生存系文言へ更新（§T4）

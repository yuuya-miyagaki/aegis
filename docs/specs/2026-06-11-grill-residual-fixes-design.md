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
  新: (^|[;&|(] *)([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*(npx +)?vitest($|[^a-zA-Z0-9_])
  ```

  7 パターン全てに同じ接頭部を適用する（`pytest`／`python3? +-m +unittest`／
  `cargo +test`／`go +test`／`(npm|pnpm|bun|yarn) +(run +)?test...` も同様）。
- **制約**: BSD/GNU `grep -E` ∩ Python `re` の共通サブセット（`\b`・`[[:space:]]` 禁止、
  リテラル空白を使用）。`tests/test_patterns_parity.py` に fixture を追加。
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
  - `ERR_FILE` は `mktemp` で作成し `trap`/直後削除でクリーンアップ
- **不変**: RC 契約（0=allow / 2+`ASK:`=ask / その他=deny）は変更しない。

### T3: update-gate の CURRENT 読込 TOCTOU 解消

- **問題**: `scripts/update-gate.sh` が CURRENT 値を読む（:83）のが排他ロック取得
  （:186-202）より前。書込は直列化済みで実害は「表示ログと事前検証の競合」のみ。
- **変更**: ロック取得ブロックを引数検証・STATUS_FILE 存在確認の直後
  （CURRENT 読込の前）へ移動する。読み→検証→書きが全てロック内に入る。
- **トレードオフ**: ロック保持時間が pre-approve の python 実行分（~1 秒）延びるが、
  CLI 用途では無害。早期 exit 経路（already approved 等）でも `trap ... EXIT` が
  rmdir するため解放漏れなし。

### T4: stale lock の PID ベース自動回収

- **問題**: kill -9 等でロックディレクトリが残ると以後 fail-closed 固着
  （手動削除ガイダンスのみ）。
- **変更**: PID ファイル方式。
  - ロック取得成功直後に `printf '%s' "$$" > "$LOCK_DIR/pid"` を記録
  - 競合時（mkdir 失敗時）: `pid=$(cat "$LOCK_DIR/pid" 2>/dev/null)` を読み、
    pid が非空かつ `kill -0 "$pid"` が失敗（プロセス死亡）なら
    `rm -f "$LOCK_DIR/pid" && rmdir "$LOCK_DIR"` で回収して再試行
  - **pid ファイルが無い/空のときは回収しない**（mkdir 直後の書込前ウィンドウと
    区別できないため fail-closed 維持＝現行の手動ガイダンスへ）
- **受容リスク**: (1) PID 再利用による「生存誤判定」→ 回収しないだけ＝現行と同じ。
  (2) `kill -0` の EPERM（他ユーザー所有で生存）も非ゼロ→死亡誤判定の理論可能性が
  あるが、ローカル CLI の同一ユーザー前提で受容（設計に明記）。
  (3) 2 プロセス同時回収 → rmdir 後の mkdir 競争で必ず片方だけが勝つ（原子性維持）。

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
  find の書込能力フラグを追加する:

  ```
  -(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)($|[^A-Za-z0-9_])
  ```

- **不採用案**: truncate/dd のシェル語を直接追加 — `grep "truncate -s" hooks/x.sh` の
  正当読取りを誤爆させ（P3-4 で解消済みの過去問題が再発）、`-exec cp` 等の同型穴も残る。
- **受容トレードオフ**: `grep -- "-exec" hooks/x.sh` のような「フラグ文字列を検索する」
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
   直前の有効記録を維持）— T1
2. check-deploy-gate の deny/ask 文面に stderr 由来文字列が混入しない — T2
3. 並行 update-gate 実行で CURRENT 表示が常にロック内読みの値 — T3
4. 死んだ PID の stale lock が自動回収され、生きた PID では回収されない — T4
5. `grep "confirm " hooks/x.sh` が allow、`find hooks/ -exec dd of={} +` が deny — T5
6. 既存 436 tests・contract・drift・smoke 全 PASS（回帰なし）

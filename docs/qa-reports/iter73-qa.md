# iter73 QA Report — locale/byte 掃討（deny 側フック byte-wise 決定化）

- **日付**: 2026-07-19
- **対象**: `hooks/check-destructive.sh`・`hooks/check-secrets.sh`（各 `export LC_ALL=C LC_CTYPE=C LANG=C` を抽出前に追加）＋`tests/test_hook_locale_byte.py`（10 pin）
- **設計/計画/review**: `docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md` / `docs/plans/2026-07-18-iter73-locale-byte-sweep-implementation-plan.md` / `docs/qa-reports/iter73-review.md`

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | invalid-byte で crash→fail-open を封鎖 | check-destructive/secrets | UTF-8 locale で byte 混入コマンド→rc=0＋正判定 | PASS |
| 2 | byte 下でも moat 維持（destructive=ask） | check-destructive | `rm -rf /realdir #<0xFF>`→ask（main-path msg） | PASS |
| 3 | byte 下でも moat 維持（実 .env staging=deny） | check-secrets | `git add .env realfile<0xFF>`→deny | PASS |
| 4 | i18n 非退行（valid 多バイト） | 両フック | 日本語パス→ask/deny 維持 | PASS |
| 5 | 正常 ASCII 非退行 | 両フック | 既存 destructive/secrets 全 pin | PASS |
| 6 | 掃討完全性（非該当フック非 crash） | runtime-state/deploy-gate | byte-in-CMD→rc=0・非 crash | PASS |
| 7 | 受容 residual（Unicode 空白区切り） | 両フック | NBSP 区切り→allow（非コマンド・SF-016） | PASS |

## 検証項目

### 検証項目1: invalid-byte crash 封鎖（主目的）
- 操作: `tests/test_hook_locale_byte.py` を UTF-8 locale 明示で実行（crash 回帰 pin）。
- 期待: rc=0＋正判定（fix 前は rc=1・stdout 空の crash）。
- 実際: 10 passed。crash 回帰 4 pin（byte_in_comment/trailing・real_env/byte_after_env）とも rc=0。
- 判定: **PASS**

### 検証項目2: テスト強度（mutation・手動バッテリー）
> qa drill は skip（framework per-task-commit で working-tree diff 空＝想定どおりの縁ケース・SKILL 147-150）。`"since"` 案は新規テストファイルを coverage-floor 対象化し無意味な mutant を要求するため不採。代替実証を手動 mutation で固めた（`docs/qa-reports/test-strength.drill` の skip 理由に詳細）。
- **M1** check-destructive.sh:51 `export LC_ALL=C…`→`…=en_US.UTF-8`（C-locale をバグへ戻す）: destructive 3 pin RED（byte_in_comment/trailing/unicode_ws_separator）＝killed。
- **M2** check-secrets.sh:62 同 mutant: secrets 3 pin RED（real_env/byte_after_env/unicode_ws_separator）＝killed。
- **M3** 配置 mutation（export を抽出後へ）: 強化後 destructive pin（main-path「再帰削除」msg）＋secrets pin RED＝killed（review fix-forward 2c5c575）。
- **M4** export 全削除: 両フック crash→RED（reviewer-testing 独立実測）＝killed。
- 各 mutant は一時適用→scoped 実行→byte 一致 revert（本体 tree 不接触）。復元後 10 passed・tree clean。
- 判定: **PASS**（全 mutant killed＝export-locale 行は両フックで完全に pin 済み）

### 検証項目3: moat 非退行（multibyte 隣接）
- 操作: multibyte 隣接コマンドを両フックへ（`rm -rf café`・`rm -rf 日本語/data`・`DROP TABLE 日本語;`・`git push --force 日本語`・`git add café/.env`）。
- 期待: ASCII-anchored パターンが正しく発火。
- 実際: すべて ask/deny 正判定（C locale narrow は miss を作らない・review 1次17 プローブ＋親verify 実測と一致）。
- 判定: **PASS**

### 検証項目4: 掃討完全性（非該当フック）
- 操作: `check-runtime-state.sh`・`check-deploy-gate.sh` に byte-in-CMD。
- 期待: crash しない（同型不成立）。
- 実際: 両フックとも rc=0・`{}`（python3 抽出でバイト→空 CMD or tr 前 BSD grep で非 crash）。
- 判定: **PASS**（掃討スコープが 2 フックで正しい）

### 検証項目5: full suite 回帰
- 操作: `python3 -m pytest tests/`（record 経由・marker 検証）。
- 実際: **1302 passed, 2 skipped**・`recorded: green`（marker:true）。`check_framework_contract.py` PASS。
- 判定: **PASS**

## エビデンスチェックリスト
- [x] テストスイート実行・記録（full suite green record・marker:true）
- [x] plan 受入条件と突合（対照表 7 項目 PASS）
- [x] 各項目 PASS/FAIL 付与
- [x] mutation 代替実証（M1-M4 全 killed）
- [x] FAIL 項目なし

## ブロッカー / 残余
- ブロッカー: なし。
- 残余: SF-016（Unicode 空白区切りの narrowing・非 exploitable・accepted residual・pin 済み）。security ゲートで F-B1 非 exploitability と PEP 540 fail-safe を独立再確認。

## 判定: **PASS**

```claims
tests_pass: true
drill_verdict: skip
drill_reason: "framework per-task-commit（working-tree diff 空）＝想定どおりの縁ケース。代替実証＝手動 mutation バッテリー M1-M4 全 killed＋RED-first TDD＋full suite 1302 green＋独立レビュー（reviewer-testing/盲検2次）"
verdict: approve
```

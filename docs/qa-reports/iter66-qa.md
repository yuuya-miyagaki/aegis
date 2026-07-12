# iter66 QA レポート — SF-010 封鎖＋frontmatter 読取意味論統一

- 対象: `git diff deb4a8a..HEAD`（実装 per-task コミット済み `abf6d04`〜`6148a60`・HEAD=3fdf923）
- 仕様正本: `docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md` ／ 計画 `docs/plans/2026-07-12-iter66-sf010-parser-unification-implementation-plan.md`
- テストコマンド: `python3 -m pytest -q`（README/CLAUDE.md 準拠）
- 検証体制: qa 一次（fresh 変異＋hook 直接発火の独立再実測・read-only 拘束・変異は scratch clone 内のみ）→ 親判定（scoped green・tree clean・引用テスト名実在を独立確認）

## 機能対照表（要件/plan → 検証対象 → 方法 → 判定）

| # | plan の機能（トレーサビリティ表 :791-806） | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | Fix① grace 絞り込み・task fields（SF-010 本丸） | `hooks/post-status-audit.sh` | `test_sf010_empty_baseline_size_injection_blocked`＋fresh 変異 M1 kill＋独立再実測(a) BLOCK | PASS |
| 2 | Fix① grace 絞り込み・gate loop（SF-010 (iii)） | 同上 gate tamper loop | `test_gate_line_missing_in_snapshot_injection_blocked`（scoped green）＋独立再実測(b) BLOCK | PASS |
| 3 | Fix① grace 温存（真の旧フォーマット） | 同上 | 既存 migration-grace テスト無変更 green＋独立再実測(c) 非 block | PASS |
| 4 | Fix① 自己防衛（task_type 除去 block） | 同上 | `test_task_type_removal_blocked_self_defense`（scoped green 内） | PASS |
| 5 | Fix② frontmatter_value スコープ化 | `hooks/lib/frontmatter.sh` | 新規 4 本 green＋fresh 変異 M2 で 5 テスト kill（本文 spoof/未終端/末尾空白/parity c・f） | PASS |
| 6 | Fix③ snapshot 生成スコープ化（毒込み封鎖＋regen） | `hooks/lib/snapshot.sh` | 新規 3 本 green＋fresh 変異 M5 kill（`test_body_spoof_lines_excluded_from_snapshot`＝本文 task_size 混入を検出） | PASS |
| 7 | Fix④ gate_value 本文 fallback 厳格化（F-2） | `frontmatter.sh::gate_value` | `test_body_gate_block_not_adopted_when_frontmattered`＋fresh 変異 M3 で 3 テスト kill | PASS |
| 8 | Fix⑤ python 意味論同期（F-1・first-match） | `scripts/check_status.py` | 新規 6 本 green＋fresh 変異 M4 で 4 テスト kill（first-match pin＋parity a・b） | PASS |
| 9 | dedup（読取意味論の単一ソース化） | `hooks/check-gate.sh` | 既存 `test_check_gate_size_aware.py` 無変更 green（挙動不変ピン） | PASS |
| 10 | parity drift-guard（fixture a-f＋FF g-k） | `tests/test_parser_parity_driftguard.py` | M2/M3/M4 の各変異で parity テストが交差検出＝bash↔python drift に歯があることを実証 | PASS |
| 11 | 正規経路（update-task.sh/update-gate.sh）無影響 | 正規 writer 経路 | 既存 update-task 経由テスト green＋独立再実測(d) snapshot-synced・audit allow | PASS |
| 12 | Task 0 census（読点の全数調査） | 台帳（調査のみ・実装対象外） | review で 2 regex 再実行一致・新規 enforcement hit 0 | PASS |

全 plan 機能に検証対象が存在（実装漏れなし）。

## テストスイート実行

- **full suite**: **1138 passed / 2 skipped**（231s・既知 skip＝case-insensitive FS・shellcheck 不在）。緑記録済み（`recorded: green`・fp=tree-hash）。
- **contract**: `python3 scripts/check_framework_contract.py` → PASS。
- **scoped fresh 再実測**: 変更系 6 テストファイル `93 passed`（qa 一次と親判定の双方で独立実行・一致）。
- lint/type-check/build: 専用ビルドなし。`bash -n` frontmatter.sh/snapshot.sh/post-status-audit.sh/check-gate.sh 全 OK・`python3 -m py_compile scripts/check_status.py` OK。
- **flaky（申し送り）**: 既知 `test_update_gate_lock`（lock 待ちタイミング・full-review R10 test#8）は本 qa の full run では顕在化せず。本 diff は update-gate/lock 機構不接触＝回帰外。

## B1 mutation drill

- **skip（sanctioned 縁ケース）**: 実装を per-task コミット済みで `git diff HEAD` の code 差分が空（qa-verification skill 137-141・iter64 conf7 前例）。skip 宣言＝`docs/qa-reports/test-strength.drill`。
- **代替実証（qa 一次 fresh 確認変異・5/5 kill＝計 14 テスト・すべて scratch clone 内で適用→scoped test→復元）**:
  - **M1** post-status-audit の現行フォーマット判定を恒偽化（`grep -q "^task_type:"` → `false`）→ `test_sf010_empty_baseline_size_injection_blocked` **failed**（1 failed / 8 passed）。
  - **M2** frontmatter_value を whole-file 読みへ戻す → **5 failed**（本文 spoof 不可視/末尾空白 fail-closed/未終端 fail-closed＋parity c・f）。
  - **M3** gate_value の本文 fallback を復活 → **3 failed**（F-2 pin `test_body_gate_block_not_adopted_when_frontmattered`＋gate 末尾空白＋parity d）。
  - **M4** check_status.py extract_scalar_value を last-match（旧 2-pass 相当）へ戻す → **4 failed**（first-match pin×2＋parity a・b）。
  - **M5** snapshot 生成を whole-file 読みへ戻す → `test_body_spoof_lines_excluded_from_snapshot` **failed**（本文 `task_size: S` の baseline 混入を検出）。
  - 各変異とも復元後 green 復帰・メイン tree は全工程 clean（変異生存ゼロ）。
- **補強**: Task 1-5 RED-first TDD（RED 生出力コミット記録）＋review 盲検2次の mutant 5 件全赤（python 旧 2-pass/gate アンカー緩め/SNAP_IS_CURRENT_FORMAT 除去/SNAP_HAS_GATE_SECTION 除去/single-quote strip 削除）。

## 検証項目（再現・pytest 非経由の hook 直接発火）

### 検証項目: canonical SF-010（task_size empty-baseline 注入）が block される
- 前提: snapshot は task_type 行あり（現行フォーマット）・task_size 行欠落。STATUS frontmatter へ raw-Edit で `task_size: S` を注入。
- 操作: `hooks/post-status-audit.sh` を `CLAUDE_PROJECT_DIR` 指定で直接発火（tamper テストの `_status/_snapshot/_audit` 様式を移植した driver）。
- 期待結果（受入条件）: BLOCK（旧実装は empty-OLD grace で ALLOWED＝穴）。
- 実際結果: `{"decision":"block", ... [task-tamper] task_size changed <unset>→S ...}`。
- 判定: **PASS**

### 検証項目: gate 行欠落 snapshot への gate 値注入（SF-010 (iii)）が block される
- 前提: snapshot に deploy 行なし（gate_approvals 節は存在）。STATUS へ `deploy: approved` を注入。
- 操作: 同上。
- 期待結果: BLOCK（gate_approvals 節を持つ snapshot の行欠落は破損 baseline＝fail-closed が正）。
- 実際結果: `{"decision":"block", ... [gate-tamper] deploy gate changed <unset>→approved ...}`。
- 判定: **PASS**

### 検証項目: 真の旧フォーマット grace 温存＋正規経路無影響（false-block なし）
- 前提: (c) snapshot に task_type/task_size 行そのものが無い旧フォーマット／(d) `scripts/update-task.sh --type bugfix` の正規実行。
- 操作: 同上。
- 期待結果: (c) 非 block（grace 温存）／(d) snapshot 原子更新で audit 差分なし＝allow。
- 実際結果: (c) stdout=`{}`（allow）／(d) update-task rc=0・snapshot 同期・audit stdout=`{}`。
- 判定: **PASS**

## エビデンスチェックリスト

- [x] テストスイートを実行し結果を記録（1138 passed・`recorded: green`）
- [x] lint/type-check/build（該当分＝bash -n×4・py_compile・N/A 明記）
- [x] plan の受入条件と突合（機能対照表 12 項目・トレーサビリティ表全写像）
- [x] 各検証項目に PASS/FAIL 付与
- [x] FAIL 項目なし（flaky は回帰外と切り分け・申し送り）

## 残存リスク申し送り（security へ）

- **SF-010 閉塞の security 検証**: (i)(ii)(iii) の消化を security gate で確認（qa では canonical/gate/grace/正規経路の 4 ケースを実測済み）。CLOSED 化自体は docs フェーズ（plan 完了条件）。
- **snapshot 削除→grace 窓**: 脅威モデル外（`.claude/` Bash 書込みは check-runtime-state.sh が block・欠落時 first-edit allowance は AUDIT_SKIP_LOG 記録・SF-006 較正と同境界＝plan リスク4）。security で ack 前提。
- flaky `test_update_gate_lock`（env timing・full-review R10 test#8・回帰外）。

## 判定

**PASS**。全 plan 機能 12/12 PASS・fresh 変異 5/5 kill（計 14 テスト）・SF-010 閉塞 4 ケース独立再実測一致・full suite 1138 passed 緑記録・contract PASS。

```claims
tests_pass: true
suite_scope: "full (python3 -m pytest -q) — 1138 passed / 2 skipped"
drill: "skip (sanctioned・per-task committed) ＋ qa 一次 fresh 変異 5/5 kill（計14テスト）＋SF-010 hook 直接発火 4 ケース再実測"
no_stubs: true
verdict: approve
residual: "SF-010 閉塞の security 検証＋snapshot 削除窓の ack（SF-006 同境界）・flaky test_update_gate_lock (回帰外)"
```

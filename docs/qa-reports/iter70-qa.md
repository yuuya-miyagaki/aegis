# iter70 QA レポート — record 引数事前検証＋audit_deps no-manifest info 降格＋judge カード tests スコープ表示

## 対象

- 変更内容: `scripts/record-test-result.py`（引数事前検証 3 段）／`scripts/build-judge-card.py`（`_norm_cmd_match`/`runner_cmd_matches` 抽出・`audit_deps` no-manifest 第4状態＋UNAUDITABLE_MANIFESTS/GLOBS・`read_test_result_detail`＋カードスコープ＋`_sanitize_card_field`）／`tests/test_record_test_result.py`（新規）／`tests/test_judge_card.py`（拡張）。commit 4eb5a51..b32deb0。
- 環境: darwin / python3 / bash / git。ui_surface: false（ブラウザ QA 非該当）。
- 計画正本: docs/plans/2026-07-14-iter70-record-guard-judge-card-implementation-plan.md（受入条件 FR-1〜3）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| FR-1 | record 引数事前検証（runner照合/非シェル互換/NO_RUN・rc2 fail-closed・ログ非書込み・非実行） | record.main 事前検証・runner_cmd_matches | E2E 4拒否＋1受理／fresh 変異 M1-M4／既存テスト 9 | PASS |
| FR-2 | audit_deps no-manifest info 降格＋既知 manifest unverified 維持 | audit_deps・compute_verdict | E2E no-manifest→info／fresh 変異 M5-M8／回帰テスト（lockfile/ecosystem 16・glob 5） | PASS |
| FR-3 | read_test_result_detail 同一走査＋カード tests スコープ表示＋注入遮断 | read_test_result_detail・render_card・_sanitize_card_field | E2E カード src/cmd/ts／fresh 変異 M9-M11／注入テスト 2 | PASS |
| 互換 | read_test_result シグネチャ・意味論不変／受理経路 rc0 | wrapper／既存 ~30 ピン | full suite＋wrapper compat テスト | PASS |

## 実施した確認

- [x] full suite 実行・record green（1242 passed / 2 skipped・既知 flaky test_update_gate_lock 非顕在）
- [x] qa fresh 変異バッテリー 11 種を独立 clone（scratchpad/qa70・HEAD b1a52d8 一致）で実走 → 10/11 KILLED
- [x] 実環境 E2E 3 機能とも PASS
- [x] plan 受入条件（FR-1〜3）と突合
- [x] B1 drill は sanctioned skip（per-task committed framework 変更・代替実証付き）

## 実行コマンドと結果

```bash
python3 -m pytest tests/ -q     # 1242 passed, 2 skipped
python3 scripts/record-test-result.py "python3 -m pytest -q"   # recorded: green
```

### qa fresh 変異バッテリー（独立 clone・本体 tree 不接触・baseline 98 passed）

| 変異 | 破壊対象 | 対象テスト | 判定 |
|------|---------|-----------|------|
| M1 | record runner-match 常時 True | test_non_runner_command_rejected | KILLED |
| M2 | record NO_RUN 検査除去 | test_no_run_flag_rejected | KILLED |
| M3 | record shell-op 検査無効化 | test_shell_operator_token_rejected | KILLED |
| M4 | record shlex.split→str.split | test_unparseable_quote_rejected | **SURVIVED（下記・多層防御 subsumed）** |
| M5 | audit_deps no-manifest→unverified | test_no_manifest_is_no_manifest_state | KILLED |
| M6 | audit_deps UNAUDITABLE 検査除去 | test_every_unauditable_manifest_stays_unverified | KILLED |
| M7 | audit_deps glob 検査除去 | test_globbed_manifests_stay_unverified | KILLED |
| M8 | verdict no-manifest info→yellow | test_no_manifest_is_info_not_yellow | KILLED |
| M9 | detail green が cmd/src/ts 落とす | test_detail_green_has_cmd_src_ts | KILLED |
| M10 | sanitize backtick 置換除去 | test_backtick_becomes_apostrophe | KILLED |
| M11 | sanitize 切詰 off-by-one | test_truncation_is_exactly_limit_chars | KILLED |

**M4 survivor の評価（穴ではない）**: record step2 の `shlex.split` を `str.split` に退行させても `test_unparseable_quote_rejected` は緑のまま。理由は**多層防御**＝step3 の `drill.check_no_run_command` 自身が内部で `shlex.split` を行い、同じ不正クォートを `DrillError`→rc2「クォート」で捕捉するため。テストが検証する**安全性（不正クォート→fail-closed・ログ非書込み）は 2 層で保護され健在**で、mutation が survive するのは冗長な防御が存在するからであり、保護の欠落ではない。単層に絞って pin したい場合は step3 を一時無効化した状態で step2 を pin する追加テストが可能だが、実運用の安全性は現状で満たされているため非ブロッキング。

### 実環境 E2E（独立 clone・実 subprocess）

| # | 検証項目 | 操作 | 期待 | 実測 | 判定 |
|---|---------|------|------|------|------|
| 1 | no-manifest → info | compute_verdict(security, deps=no-manifest, claims+2次 approve) | overall=0・deps-yellow なし・info に「依存 manifest なし」 | overall=0・yellow-deps=[]・info=[依存 manifest なし…] | PASS |
| 2a | 非runner 拒否 | record `ls -la` | rc2・ログ非書込み | rc=2・log_written=False | PASS |
| 2b | no-run 拒否 | record `pytest --collect-only` | rc2・ログ非書込み | rc=2・log_written=False | PASS |
| 2c | quoted no-run 拒否 | record `pytest "--collect-only"` | rc2・ログ非書込み | rc=2・log_written=False | PASS |
| 2d | shell-op 拒否 | record `pytest -q && echo x` | rc2・ログ非書込み | rc=2・log_written=False | PASS |
| 3a | valid runner 記録 | record `python3 -m pytest -q t_pass.py` | rc0・src=manual/status=ok | rc=0・src=manual・status=ok | PASS |
| 3b | カード tests スコープ | render_card（green 記録後） | tests 行に src=/cmd=/ts= | `- テスト: green（判定源: src=manual / cmd=… / ts=…）` | PASS |

## 残留リスク / 非ブロッキング

- **zero-test forge（SF-014 同クラス・pre-existing・非ブロッキング）**: `unittest discover -p <nomatch>`（exit 0）や `npm test`→`"test":"true"` は runner 該当かつゼロテストで green 記録できる。baseline 37ec449 の record は無検証で任意コマンドを green 化していた＝iter70 は net 改善・回帰ゼロ（親 verify 差分実測）。`-p` は正当フラグで denylist 不可＝positive N-tests-executed proof が根治（SF-014・iter71+）。record docstring に残余明記済み。
- **audit_deps no-manifest denylist 残余**: 未知エコシステムの manifest は誤って no-manifest になりうる（本 iter で 15+ 種を unverified に寄せて回帰は閉塞済み）。同じく SF-014 の positive-proof 根治対象。

## B1 drill 判定

**sanctioned skip**（`docs/qa-reports/test-strength.drill` に理由記録）。per-task committed framework 変更のため working-tree diff が空＝想定どおりの縁ケース。代替実証は上記 RED-first TDD＋fresh 変異 11 種（10 KILLED・M4 は多層防御 subsumed）＋E2E 3 機能。

## 判定

**PASS**。FR-1〜3 すべて実環境 E2E とテストで PASS。fresh 変異は core 分岐を確実に KILL（唯一の survivor は多層防御の冗長性による subsumed で安全性健在）。full suite 1242 passed・record green。残留は SF-014 同クラスの pre-existing のみで本 gate 非ブロッキング。

```claims
tests_pass: true
no_stubs: true
verdict: approve
```

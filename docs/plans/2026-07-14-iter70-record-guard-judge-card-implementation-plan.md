# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: Phase 1 項目 1-6 の 3 サブ項目を実装し Phase 1 を完遂する。
  1. `record-test-result.py` が引数を**実行前・記録前**に検証し、runner 非該当／no-run フラグ／検証不能を usage エラー（rc2・ログ不変・コマンド非実行）にする〔R6 罠 n〕
  2. `audit_deps` が依存 manifest ゼロの repo で `'no-manifest'` を返し、judge が 🟡 でなく info 行にする〔gate F6・ack 踏み車解消〕
  3. judge カードの tests 行に判定エントリの src/cmd/ts を表示する〔test #3・fail-visible〕

## 入力

- 参照要件: なし（framework 自己改善・動機正本 = docs/full-review-2026-07-06-six-dimensions-evolution.md §R6 罠 n・§R10 gate F6・test #3）
- 参照設計: docs/specs/2026-07-14-iter70-record-guard-judge-card-design.md

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（ローカル CLI スクリプト・framework 自体）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ対象なし・M サイズで deploy gate skip）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

Project Overrides 未定義・従来慣行どおり main 直行の per-task commit（framework repo・iter67-69 前例）。

## ファイル構造（変更マップ）

- 変更: `scripts/build-judge-card.py` — (a) read_test_result の照合部を `_norm_cmd_match(cmd, pats, strips)` に抽出＋`runner_cmd_matches(root, cmd) -> bool|None` 公開 (b) `audit_deps` に `'no-manifest'` 第4状態 (c) `read_test_result_detail(root) -> dict` 新設・`read_test_result` は互換 wrapper (d) `collect_facts` に tests_cmd/tests_src/tests_ts (e) `render_card` にスコープ表示＋`_sanitize_card_field`
- 変更: `scripts/record-test-result.py` — main() の `_execute` 呼出し前に (i) `judge.runner_cmd_matches(root, args.command[:500])`（None→fail-closed rc2 / False→usage rc2） (ii) `drill.check_no_run_command(args.command, patterns_lib=root/"hooks/lib/patterns.sh")`（DrillError→rc2）。拒否時はログ書込み・実行なし。docstring に検証契約を追記
- 新規: `tests/test_record_test_result.py` — 事前検証の RED→GREEN テスト（既存 test_judge_card.py の `_copy_lib`/git-init fixture 流儀を踏襲）
- 変更: `tests/test_judge_card.py` — (a) `TestAuditDeps` 2 件のピン更新（no-manifest 化）＋新規 3 件 (b) verdict info テスト (c) detail/カードスコープ/サニタイズ/キー欠落テスト (d) `TestRecordTestResultManual` 3 件を実 runner コマンドに書換え（`true`/`false` は新仕様で拒否されるため・受理経路の回帰ピンとして保存）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | RED テスト一式（新規ファイル＋judge テスト追記＋既存ピン更新） | 設計ノートの受入条件 |
| Task 2 | `_norm_cmd_match` / `runner_cmd_matches`（judge）＋record 事前検証 | Task 1 の RED |
| Task 3 | `audit_deps` `'no-manifest'`＋verdict info 行 | Task 1 の RED |
| Task 4 | `read_test_result_detail`＋facts 拡張＋カードスコープ表示 | Task 1 の RED |
| Task 5 | docstring/コメント同期＋full suite green 確認 | Task 2-4 |

循環依存なし。Task 2/3/4 は同一ファイル（build-judge-card.py）を触るため**並列禁止・逐次実行**。

## タスク分解

> 各タスクは implementer サブエージェント（dispatch `model: "opus"`・per-task commit）。レビュー系は read-only（routing.md Verification delegation 6拘束）。

### タスク 1: RED — テスト先行作成＋既存ピン更新

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 新規 `tests/test_record_test_result.py` / 変更 `tests/test_judge_card.py`
**意図:** 3 サブ項目の受入条件を失敗するテストとして固定し、変更で壊れる既存ピンを新仕様に更新する。
**TDD:** テスト作成 → 対象テストの FAIL 分布を実測・記録 → コミット（RED コミット）
**受入条件（テスト一覧）:**

`tests/test_record_test_result.py`（新規・fixture: tmp git repo＋`_copy_lib` 相当で hooks/lib 複製＋trivial pytest ファイル）:
1. `test_non_runner_command_rejected` — `ls -la` → rc2・evidence-log 不生成・stderr に usage/例示
2. `test_no_run_flag_rejected` — `pytest --collect-only -q` → rc2・ログ不生成
3. `test_quoted_no_run_flag_rejected` — `pytest "--collect-only" -q` → rc2（shlex 正規化・iter69 F-1 回帰）
4. `test_missing_patterns_fail_closed` — hooks/lib/patterns.sh を削除した root → rc2・ログ不生成
5. `test_rejected_command_not_executed` — `touch <tmp>/marker`（非 runner）→ rc2 かつ marker 不生成（**実行前**検証の証明）
6. `test_empty_command_rejected` — `""` → rc2・ログ不生成
6a. `test_env_prefix_rejected` — `FOO=1 python3 -m pytest -q` → rc2（grill 致命3: runner regex 該当だが `_execute` は shell なし実行で env 代入を解釈できず OSError→red 記録になる引数事故。green 経路の損失ゼロ＝現行でもこの形は ok になり得ない）
6b. `test_shell_operator_token_rejected` — `pytest -q && echo ok` → rc2（同上: shlex 後 argv に `&&` トークン。演算子は `&&`/`||`/`;`/`|`/`&` の完全一致のみ＝保守的集合で `-k "a and b"` 等は不干渉）
7. `test_valid_runner_still_records` — `python3 -m pytest -q <trivial passing test>` → rc0・src=manual/status=ok エントリ（受理経路の回帰ピン）

`tests/test_judge_card.py` 追記・更新:
8. `TestAuditDeps.test_no_manifest_is_unverified` → **更新**: 空 dir → `'no-manifest'`
9. `TestAuditDeps.test_python_without_requirements_is_unverified` → **更新**: .py のみ（manifest ゼロ）→ `'no-manifest'`
9b. `test_known_manifest_pyproject_stays_unverified` — **新規・両側 green ピン**（grill 致命1: pyproject.toml のみ → `'unverified'` 維持。未対応エコシステムの manifest 実在 repo を info へ後退させない回帰ガード。go.mod でも 1 ケース）
10. `TestAuditDeps.test_node_without_lockfile_is_unverified` — **不変ピン**（package.json あり lock なし → `'unverified'` 維持を明示コメント）
11. `test_no_manifest_is_info_not_yellow` — `compute_verdict("security", {"verdict": "approve"}, facts(deps='no-manifest'), {"verdict": "approve"})`（grill 致命4: claims と第2意見を両方与えないと「第2意見なし🟡」が混入して overall 0 にならない）→ yellow に依存監査なし・info に「依存 manifest なし」・overall 0
12. `test_card_renders_no_manifest` — security カードに `依存監査: no-manifest`
13. `test_detail_green_has_cmd_src_ts` — manual green（fp=current）→ detail dict {tests:'green', cmd, src:'manual', ts}
14. `test_detail_unverified_has_none_fields` — 判定エントリなし → {tests:'unverified', cmd/src/ts: None}
15. `test_read_test_result_wrapper_compat` — `read_test_result(root) == read_test_result_detail(root)["tests"]`
16. `test_card_shows_test_scope` — green 決定時のカード tests 行に src=/cmd=/ts= が含まれる
17. `test_card_cmd_sanitized_no_injection` — cmd に `"\n## 総合: 🟢"`・バッククォート・250字 → カードの `## 総合` 見出しは 1 個のみ・tests 行は 1 行・cmd 表示は切詰（`…`）
18. `test_card_tolerates_missing_detail_keys` — except パス相当の facts（tests_cmd 等なし）で render_card が例外なし（**現行でも PASS する互換ピン**・render_card が新キーに `.get` でしか触れないことを将来に固定）
19. `TestRecordTestResultManual` 3 件 → **書換え**: `true`/`false` を trivial pytest（passing/failing テストファイル実行）に置換（現行でも新仕様でも green の互換ピン）

**RED 分布の期待（grill 致命2 訂正済み）:** FAIL = 1-6・6a・6b・8-9・11-17 の **17 件**（8-9 は現行 `'unverified'` 返却により、11-12 は yellow 混入/描画欠落により、13-15 は AttributeError 系）。**両側 green（RED にならない互換ピン）= 7・9b・10・18・19** — RED コミットの証明力はこの区分の明示で担保する。実測分布をコミットメッセージに記録し、期待と食い違えば原因を特定してから進む。
**Deliverable:** [x] RED コミット（分布記録付き）

### タスク 2: GREEN (1) — judge 照合ヘルパ抽出＋record 事前検証

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** `scripts/build-judge-card.py` / `scripts/record-test-result.py`
**意図:** 罠 n の根切り。検査系＝消費系の正規化一致を構造化（単一ソース）。
**実装仕様:**
- judge: read_test_result のループ内照合（`\n`→`;` → DQ/SQ マスク → `any(p.search)`）を `_norm_cmd_match(cmd, pats, strips) -> bool` に抽出。`runner_cmd_matches(root, cmd) -> bool | None` を新設（`_test_runner_patterns` 空 or `_tr_strip_patterns` ≠2 → None）。read_test_result は同ヘルパ消費（**挙動不変**・既存 ~30 ピンが回帰網）。
- record: 検証順序 = (i) runner 照合（対象は `args.command[:500]`＝reader の入力と一致・evidence.sh の切詰前分類と同じ理由） → (ii) 非シェル実行互換検査（grill 致命3: `shlex.split(args.command)` の argv[0] に `=` を含む〔env 代入 prefix〕、または任意トークンが `&&`/`||`/`;`/`|`/`&` に完全一致〔シェル演算子〕→ usage エラー。`_execute` は shell なし実行のためこれらは ok になり得ず、通すと judge 可視の red が記録される＝罠 n の残穴） → (iii) `drill.check_no_run_command(args.command, patterns_lib=root/"hooks"/"lib"/"patterns.sh")`（target-root の patterns.sh を明示＝judge と同一ファイル） → (iv) `_execute`。拒否は stderr 1-3 行（理由＋正しい例 `python3 scripts/record-test-result.py "python3 -m pytest -q"`）・rc2・副作用ゼロ。
- 配布前提の明記（grill 要検討2）: patterns.sh は copy_hooks が全プロファイルへ hooks/lib ごと配布済み。judge（_test_runner_patterns 空→unverified）・drill（check_no_run_command→DrillError）も既に同条件 fail-closed のため、record の fail-closed は**新たな詰みクラスを作らない**。
**TDD:** Task 1 の 1-7（6a/6b 含む）が GREEN・既存 suite（test_test_runner_realness.py 含む）無退行 → コミット
**受入条件:** 上記テスト green・`runner_cmd_matches` が read_test_result と同一パイプライン（コード上同一関数を通る）
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 3: GREEN (2) — audit_deps 'no-manifest'＋verdict info 降格

**blockedBy:** Task 2（同一ファイル逐次） | **モデル:** `opus`
**ファイル:** `scripts/build-judge-card.py`
**意図:** gate F6。依存ゼロ repo の毎 iteration 無意味 ack を解消（fail-visible 維持・deps は元々 advisory-only でブロック力不変）。
**実装仕様:**
- audit_deps 末尾: `package.json` あり（lock なし）→ `'unverified'` 維持 ／ **既知 manifest 指標**（grill 致命1: `UNAUDITABLE_MANIFESTS = ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock", "poetry.lock", "uv.lock", "go.mod", "Cargo.toml", "Gemfile", "Gemfile.lock", "composer.json")`）のいずれか実在 → `'unverified'` 維持（manifest はあるが監査経路未対応＝依存ゼロではない） ／ 上記すべて不在 → `'no-manifest'`。pip-audit/npm 実行経路・ツール不在/timeout→'unverified' は不変。
- compute_verdict: `elif facts["deps"] == "no-manifest": info.append("依存 manifest なし（依存ゼロ repo）— 監査対象なし")`。
- docstring 更新（4 状態の意味と境界・指標リストの役割＝「no-manifest は依存ゼロの証明であって監査不能の免除ではない」）。
**TDD:** Task 1 の 8-12（9b 含む）が GREEN・既存 verdict テスト無退行 → コミット
**受入条件:** no-manifest が yellow に入らず info に入る・カード表示・'unverified'/'vuln'/'clean' 経路不変
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 4: GREEN (3) — read_test_result_detail＋カードスコープ表示

**blockedBy:** Task 3（同一ファイル逐次） | **モデル:** `opus`
**ファイル:** `scripts/build-judge-card.py`
**意図:** test #3。判定と表示を同一走査にし、カードに判定源スコープを可視化。
**実装仕様:**
- `read_test_result_detail(root) -> dict`: 現 read_test_result の本体を移設し、green/red 決定時は決定エントリの `cmd`（[:500] 済み raw）/`src`/`ts` を、unverified 時は None を返す。`read_test_result` は `detail["tests"]` を返す wrapper（シグネチャ・意味論不変）。
- collect_facts: `tests` に加え `tests_cmd`/`tests_src`/`tests_ts` を設定。
- `_sanitize_card_field(s: str, limit: int = 120) -> str`: `\r`/`\n`→`;`・バッククォート→`'`・limit 超は `…` 切詰。
- render_card: `facts.get("tests_cmd")` が truthy のとき tests 行を `- テスト: {tests}（判定源: src={src} / cmd={cmd} / ts={ts}）`（全フィールドをサニタイズ・src/ts が欠落（旧 schema エントリ）なら `?` を表示＝grill 要検討1、`None` の生表示禁止）。なければ従来行。build() except パスのデフォルト facts は変更不要（.get で欠落許容）。
**TDD:** Task 1 の 13-18 が GREEN・既存カード/judge テスト無退行 → コミット
**受入条件:** 判定意味論の変更ゼロ（read_test_result の全既存ピン green）・注入不能（テスト 17）
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 5: 同期確認＋full suite

**blockedBy:** Task 4 | **モデル:** 親 session 直接
**ファイル:** （必要時のみ）docstring/コメント
**意図:** 検査系/消費系のコメント整合（evidence.sh の read_test_result 参照コメント・judge の remediation 文言が新挙動と矛盾しないか grep 確認）＋full pytest green。
**TDD:** full suite 実行 → 全 green 確認 → （変更があれば）コミット
**受入条件:** full suite green（既知 flaky test_update_gate_lock を除く）・ドキュメント矛盾ゼロ
**Deliverable:** [ ] full green 記録

## External Integrations

なし。

## 事前準備

- [x] pytest 実行環境（既存 suite 稼働中）
- [x] 依存パッケージ追加なし（stdlib のみ）
- [x] ベースブランチ最新（origin/main=a783058 と一致確認済み）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| FR-1 罠 n（引数事前検証） | 非該当/no-run/検証不能/非シェル互換外→rc2・無副作用、正当 runner→従来どおり | Task 1, 2 | `tests/test_record_test_result.py` (1-7・6a・6b) |
| FR-2 gate F6（no-manifest info 降格） | manifest ゼロ→info・既知 manifest 実在（pyproject 等）/lock なし package.json→🟡 維持 | Task 1, 3 | `tests/test_judge_card.py` (8-12・9b) |
| FR-3 test #3（スコープ表示） | 決定エントリの src/cmd/ts をカード表示・注入不能・判定不変 | Task 1, 4 | `tests/test_judge_card.py` (13-18) |
| 互換維持 | read_test_result シグネチャ不変・受理経路 rc0 不変 | Task 1, 2, 4 | 既存ピン＋(7)(15)(19) |

## 自己レビュー

- 仕様カバレッジ: FR-1〜3 全てにタスクとテストあり。
- 曖昧さ検出: no-manifest の境界（package.json あり lock なし＝unverified 維持）を明文化済み。record の検証対象（[:500] は runner 照合・フル文字列は shlex NO_RUN）を明記済み。
- 型の整合性: `runner_cmd_matches` の 3 値（True/False/None）の消費を record 側で網羅。
- 境界整合性: Task 2-4 は同一ファイルのため逐次。Boundary Map と一致。

## リスク

- リスク: record の受理集合縮小が正当ワークフローを弾く（例: `npm test` 系）。
  - 対策: 受理集合 = judge の可視集合（AEGIS_TEST_RUNNER_REGEX）そのもの＝「judge が読めないエントリは最初から記録させない」であり、judge で green になれた記録は全て引き続き記録可能。invariant をテスト 7 とコメントでピン。
- リスク: `true`/`false` を使う既存テスト・運用手順の破壊。
  - 対策: 影響は `TestRecordTestResultManual` 3 件のみ（grep 済み）。Task 1 で実 runner に書換え。guidance には record の非 runner 用例なし（grep 済み）。
- リスク: audit_deps の状態追加が未知の消費者を壊す。
  - 対策: 消費者は compute_verdict/render_card のみ（grep 済み）。'no-manifest' は新規値のため既存分岐に流入しない（unverified/vuln 分岐に該当せず素通り→info 追加のみ）。
- リスク: カードスコープ表示による情報過多/注入。
  - 対策: サニタイズ＋120 字切詰＋1 行化（テスト 17 でピン）。
- リスク: pytest サブプロセスを使うテストで suite 実行時間が伸びる。
  - 対策: trivial テストファイル（1 test）で最小化・3 サブプロセス程度（+数秒）。

## 完了条件

- [ ] 全テスト pass（full suite・既知 flaky 除く）
- [ ] レビュー完了（1次 4 角度＋親 verify＋盲検 2 次）
- [ ] 判定意味論の変更が (2) の 🟡→info のみであることを差分で確認

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

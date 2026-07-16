# 納品サマリー — iteration 71（v1.30.0・marker positive proof・SF-014 恒久策）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 何を作ったか

反ガミング検証（テストが本当に走ったかの判定）を、**「悪い入力を列挙して弾く（denylist）」から「良い実行が起きた証拠を要求する（positive proof）」へ置換**しました。SF-014（iter69 起票・唯一の Major-class OPEN）の恒久策です。

- **共有 lib 化**: evidence.sh にあった4段検証コア（NO_RUN 失格 → STRONG marker → WEAK pair → zero-run gate）を新規 `hooks/lib/marker.sh` に**逐語移動**（byte 一致・挙動不変）。3消費者（hook 観測 evidence.sh／手動記録 record／drill baseline）が**同一実装**を使う。
- **record の green ゲート**: `record-test-result.py` は green（exit 0）を記録する前に marker verdict を必須化。0件実行の偽 green（`unittest discover -p nomatch`／`npm test`→`"test":"true"`）を **rc2 拒否・ログ非書込**で根治。red は従来どおり記録。
- **drill の baseline ゲート**: `run-test-strength-drill.py` の `check_baseline` は exit 0 に加え positive proof を要求。非ランナー import プローブ＋import-crash mutant の偽 DRILL PASS を `DRILL BLOCKED (baseline no-test-proof)` で根治。

## 主要な設計判断

- **案A（bash 共有 lib）採用**: python への 4段ロジック再実装（2重実装）は SF-014 を生んだ「同じ入力を別経路で解釈」構造の再生産のため不採用。record/drill は subprocess で marker.sh を呼び、同一エンジンを保証。
- **評価不能＝拒否（fail-closed）**: patterns.sh 欠落・marker.sh 不在等は rc3/DrillError で一律拒否。緩和は一切入れない。
- **denylist で塞がない残余**: 出力を任意 script が支配するランナー（`npm test` の echo-marker）と all-skip suite（unittest/go は skip を「実行」と数える）は出力ベース proof の原理的限界。列挙で追わず（denylist 回帰）、SF-014 の恒久策（passed/failed **実数カウント** proof・iter72+）へ委譲。

## 変更ファイル

- 新規 `hooks/lib/marker.sh`（4段検証コア・逐語移動）
- 変更 `hooks/lib/evidence.sh`（marker.sh 委譲・挙動不変・`[ -f ]` ガード source）
- 変更 `hooks/lib/patterns.sh`（marker/zero-run 配列の bracket 内 `\t`→リテラル TAB＝BSD grep 対応・mocha `\b`→共通部分集合＝いずれも pre-existing cross-engine 欠陥の semantics-preserving 修正）
- 変更 `scripts/record-test-result.py`（green marker ゲート・rc2 拒否・`marker:true` 監査フィールド・usage/docstring）
- 変更 `scripts/run-test-strength-drill.py`（`marker_verdict` ヘルパ・`check_baseline` no-test-proof）
- 変更 `scripts/build-judge-card.py`（🟡案内文の `-q` 除去・ロジック不変）
- 変更 `.claude/skills/qa-verification/SKILL.md`（positive proof 運用契約の同期）
- テスト: 新規 `tests/test_marker_lib.py`＋`test_record_test_result.py`／`test_test_strength_drill.py`／`test_check_status.py`／`test_judge_card.py`／`test_test_runner_realness.py`／`test_patterns_parity.py` 追記
- docs: `docs/architecture-overview.md`（hooks/lib 13本）・`docs/security-followups.md`（SF-014 更新）・版上げ3箇所

## テスト・QA・セキュリティ結果（証拠参照）

- **実装**: TDD RED 先行（Task1 RED 19失敗＝機能未実装由来・commit 037545c）→ 5タスク per-task commit（`docs/plans/2026-07-15-iter71-marker-positive-proof-implementation-plan.md`）
- **review**（`docs/qa-reports/iter71-review.md`）: 1次4角度（仕様/敵対/テスト強度/保守性 全 approve_with_notes）＋grill-code Critical0＋親verify 独立実証＋盲検2次 fable 独立 approve_with_notes＝収束・divergence なし
- **qa**（`docs/qa-reports/iter71-qa.md`）: 独立 clone baseline 1271 passed/3 skipped＋fresh 変異 6/6 KILLED（対称変異も二層被覆で subsumed）＋実環境 E2E 4/4 PASS
- **security**（`docs/qa-reports/iter71-security.md`）: 新規脆弱性0・command injection 44 calls 0 成功・全経路 fail-closed・新規依存0（1次 opus＋盲検2次 fable 物理隔離 clone）
- **deploy**（`docs/qa-reports/iter71-deploy.md`）: marker.sh の install 先配布＋moat 動作を実測・Mandatory Security Blockers 全非該当
- **full suite**: 1272 passed / 2 skipped / 0 failed（本体・fix-forward 後）

## 運用上の注意点（保守者向け）

- **pytest は `-q` を外して記録/ドリルする**: `pytest -q` はサマリ marker（`===== N passed =====`）も prologue も出さないため、iter71 以降は green として**受理されません**（rc2 拒否・「`-q` を外して」案内）。`.drill` の `test_command` も同様に実ランナー（非 `-q`）が必須。
- **`.drill` の test_command は実ランナー必須**: `grep`/`true` 等の非ランナーは `DRILL BLOCKED (baseline no-test-proof)`。対応ランナー: pytest（デフォルト出力）/ jest / vitest / go test / cargo test / unittest。

## 残留リスク・既知の制限

- **F-A（marker 粒度限界・pre-existing・contained）**: unittest/go の all-skip suite（全テスト skip）は「skip を実行と数える」出力で marker true→green になり得る。pytest/cargo は安全（実測）。**外部攻撃者の経路ではなく自己欺瞞脅威モデル**。drill が subsume（all-skip baseline は mutant を殺せず FAIL）で contained。恒久策は passed/failed 実数カウント proof（SF-014・iter72）。
- **iter72+ トラック**: audit_deps の positive proof（attestation 型）／rc3 guard 個別条件の回帰網（テスト強度 F1）／保守性 minor 2件（命名語彙・record→drill 依存）／SF-011/012/013。

## 版

v1.29.0 → **v1.30.0 MINOR**（marker.sh 新規＝内部 lib 追加・record accept 集合の縮小＝運用契約 hardening・後方互換／iter68-70 の accept 集合縮小=MINOR 前例に整合）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- 操作マニュアル: 不要（framework 自己改善・利用者向け新規操作なし。運用注意点は本書「運用上の注意点」に集約）
- 運用 RUNBOOK: 不要（新規サービス/監視対象なし）
- UAT: 不要（`docs/requirements/ACCEPTANCE.md` なし・framework 内部改修）

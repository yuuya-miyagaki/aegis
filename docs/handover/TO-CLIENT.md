# 納品サマリー — iteration 72（v1.31.0・marker count proof・SF-014 完結編）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 何を作ったか

反ガミング検証の positive proof を、**「サマリ marker の**マッチ**」から「passed/failed の**実数カウント**（skip 除外・executed≧1）」へ強化**しました。iter71 で導入した marker positive proof（SF-014 恒久策の本丸）の**完結編**で、残余 F-A（all-skip suite の偽 green）を封鎖します。

- **Stage 5「count proof」追加**: `hooks/lib/marker.sh` の `aegis_marker_verdict` に第5段を追加。count 族（unittest/pytest/jest/vitest/cargo/go -v）のサマリを検出した場合、executed＝passed+failed（skip 除外）≧1 を要求。これで **unittest の all-skip（`Ran N ... OK (skipped=N)`）と `go test -v` の all-skip（`--- SKIP:` のみ）は CLOSED**（iter71 の残余 F-A を封鎖）。
- **cargo/jest/vitest の pre-existing 偽陰性を修正**: cargo の doc-tests 空セクション（`test result: ok. 0 passed`＝doc-test を持たない全 crate の実出力）を誤拒否していた zero-run 行 deny を削除し count 合計に委譲／jest の実サマリ順序（`failed, skipped, todo, passed`）で skipped 混在時に marker が破れる隣接要求を緩和／vitest のインデント付きサマリにアンカーを緩和。いずれも**正当な green run の誤拒否（false-negative）**の修正で、実測に基づく。
- **verdict インターフェース不変**: stdin=出力全文／stdout="true"/"false"／rc3=評価不能 は変えず、3 消費者（evidence.sh source／record・drill subprocess）は無改修。

## 主要な設計判断

- **case A（count 族データを patterns.sh・算術を marker.sh）採用**: attestation 型（`go test -json` 等の機械可読出力を強制）は footprint 激増＋全ランナーの test コマンド契約変更＝ユーザー負担のため不採用（iter73+ の audit_deps positive proof と同機構クラスで別トラック）。skip 列挙 denylist は「N==K（全 skip）を regex で表現できない」＝算術が要る時点で不成立。
- **fail-closed の徹底**: malformed な count 族 entry・host grep が非対応の regex は一律 rc3（評価不能）。過剰減算・族誤検出は false 側（安全側の摩擦）に倒す。
- **byte-wise（C locale）決定化**: 全 grep を `LC_ALL=C` で実行（下記 security 参照）。

## 変更ファイル

- 変更 `hooks/lib/marker.sh`（Stage 5 count proof・rc3 guard 7ソース化・**LC_ALL=C byte-wise**・EXEC/MINUS grep の rc>1→rc3）
- 変更 `hooks/lib/patterns.sh`（`AEGIS_TEST_COUNT_FAMILIES` 新規・cargo zero-run 行 deny 削除・jest STRONG 緩和・vitest アンカー緩和・unittest MINUS アンカー）
- 変更 `scripts/record-test-result.py`（docstring/拒否メッセージのみ・ロジック不変＝4-stage→5-stage・残余 (a)(b)(c) 記述）
- テスト: `tests/test_marker_lib.py`（count proof pin・moat 保護 pin・byte-injection pin 等 20+本追加）・`tests/test_patterns_parity.py`（count 族 parity）
- docs: `docs/security-followups.md`（SF-014 に iter72 適用＋F-CRIT-1 記録・SF-015 起票）・`.claude/skills/qa-verification/SKILL.md`（count 契約同期）・設計/計画/qa-reports・版上げ3箇所

## テスト・QA・セキュリティ結果（証拠参照）

- **実装**: TDD RED 先行（Task1 RED 正確に 10 failed＝機能未実装由来・commit 5e10163）→ per-task commit（`docs/plans/2026-07-16-iter72-count-proof-implementation-plan.md`）
- **review**（`docs/qa-reports/iter72-review.md`）: 1次4角度（opus）＋公式 code-review workflow（high・16 agent）＋親verify＋盲検2次（fable）。**摘発した false-GREEN 1件（F-2 vitest all-skip）・false-negative 2件（F0/F1）・fail-open 3件（F5/F6/M-1）・moat pin 欠落（強度F-1）を fix-forward 2 ラウンドで全解決**。盲検2次は fix 後に新規 false-GREEN/false-negative ゼロを実測（1次と収束）
- **qa**（`docs/qa-reports/iter72-qa.md`）: B1 drill sanctioned skip（per-task committed・代替実証明記）＋独立 clone で fresh 変異 8/8 KILLED（**M6=strict field-count guard の無 pin を qa が摘発→pin 追加で是正**）＋実環境 E2E 6/6 PASS＋clone baseline 1290 passed
- **security**（`docs/qa-reports/iter72-security.md`）: **盲検2次（fable・物理隔離 clone）が 1次（opus・approve）の見落とした High 級 moat bypass〔F-CRIT-1・locale 依存 false-GREEN〕を reject で摘発→security 内 fix-forward〔LC_ALL=C byte-wise 決定化〕で CLOSED**・command injection 0/44・secrets/新規依存 0・全経路 fail-closed
- **full suite**: 1111 tests OK / 2 skipped / 0 failed（本体・全 fix-forward 後）・record green（marker:true）

## 運用上の注意点（保守者向け）

- **all-skip suite は green として受理されません**（iter72 以降）: 全テストが skip の unittest／`go test -v` は「実行 0 件」として record rc2 拒否・drill BLOCKED。混在（1 件でも実行）は従来どおり green。pytest の `-q` 不可（iter71 以降）も継続。
- **cargo は doc-tests 空でも受理**（偽陰性修正）: doc-test を持たない crate の `test result: ok. N passed` ＋ 空 doc-tests セクションは正しく green。
- **対応ランナー**: pytest（デフォルト出力）/ jest / vitest / go test（`-v` 推奨）/ cargo test / unittest。素の `go test`（非 -v）は count 情報が出ないため all-skip 判定不能（残余・下記）。

## 残留リスク・既知の制限

- **SF-014 残余（marker 層の原理的天井・pre-existing・contained）**: (a) echo フォージ（`npm test` がカウント様行を echo）／(b) 素の `go test` all-skip（非 verbose 出力に count なし・実 pass と byte 同形）／(c) unittest の skip レポータ抑止（`TextTestResult.addSkip` を monkeypatch すると `skipped=` が消え実 pass と区別不能＝unittest CLOSED は「ランナーが skip を honest 自己申告する」前提下）。いずれも出力ベース proof の限界で drill が subsume。恒久策候補は execution attestation（iter73+）。
- **SF-015（新規起票・pre-existing・Low・fail-closed）**: pytest の all-xfail suite（`===== 3 xfailed in 0.5s =====`）は STRONG marker 不成立で false（実行済み green の誤拒否・安全側摩擦）。iter72 は STRONG 未改修。
- **iter73+ トラック**: audit_deps の positive proof（attestation 型）／SF-011/012/013。

## 版

v1.30.0 → **v1.31.0 MINOR**（Stage 5 count proof 追加＝accept 集合の縮小〔all-skip green 不成立〕＝運用契約 hardening・後方互換／偽陰性修正で正当 green の受理は拡大／iter68-71 の accept 集合縮小=MINOR 前例に整合）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- 操作マニュアル: 不要（framework 自己改善・利用者向け新規操作なし。運用注意点は本書「運用上の注意点」に集約）
- 運用 RUNBOOK: 不要（新規サービス/監視対象なし）
- UAT: 不要（`docs/requirements/ACCEPTANCE.md` なし・framework 内部改修）

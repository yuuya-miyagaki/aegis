# Evidence Archive

Archived external_evidence entries from `docs/STATUS.md`.
STATUS.md retains only the latest 3 entries; older entries are moved here.

## Archived Entries

### codex-review-round-1 (v0.5.0 Phase 1-7)

- **findings:** P1x3 (gate接続, contract, security pattern), P2x2 (iteration refs, browser QA), P3x1 (STATUS更新)
- **resolution:** 全P1修正済み、P2修正済み、P3一部修正+理由付き現状維持

### codex-review-round-2 (v0.5.0 修正後)

- **findings:** P2x1 (n/a gate stale ref), P3x1 (external evidence構造化)
- **resolution:** P2 PaC実装、P3 external_evidence追加

### codex-review-v060-round-1 (v0.6.0 Phase 0-5)

- **findings:** P1x2 (post-status-audit不完全, /gate構造矛盾), P2x1 (template bootstrap失敗)
- **resolution:** 全3件修正。update-gate.sh新設、post-status-audit全8ゲート化、template task_size除去

### codex-review-v060-round-2 (v0.6.0 配布整合)

- **findings:** P1x1 (README update-gate.sh手順欠落), P2x1 (example update-gate.sh未同梱)
- **resolution:** README Step10追加、example scripts/コピー

### session-history: iteration 18 (v1.5.0 E1 activity verification, 2026-06-11)

検証の実行ベース化を 13 タスク TDD で完走。hook 観測の Bash 実行記録 `.claude/evidence-log.jsonl` を judge card テスト判定の唯一ソース化（自己申告 test-result.json 廃止）、fingerprint.sh 単一所有（HEAD sha 混入）、記録=fail-open／判定=fail-closed、observer 生存チェック（TaskCompleted 差し戻し）、smoke の観測系実発火。設計逸脱2件（payload_sha／HEAD 比 fingerprint）はユーザー事前承認・spec 同期済み。grill-code（独立2サブエージェント）が 🔴1（quotepath で非ASCII名の fp 不感＝silent green・実証付き）＋🟡4（無区切り連結衝突／example observer 未登録＋presence 穴／smoke 失敗側未発火／観測→判定 e2e 不在）を検出し全て同セッション修正。436 tests OK・contract・drift・smoke 全 PASS。テスト行は record-test-result.py の手動記録（manual ok・fp 一致）で green、4 ゲートを --ack 承認。v1.5.0 minor で締め・tag v1.5.0。

### session-history: iteration 20 (v1.5.2 残余消化, 2026-06-11)

v151-security.md 記録の残余 5 系統を Task 1〜9 TDD で完走（461→479 tests）。T1=クォート span の Q 置換マスク（false-RED 根治、置換であって削除でない＝green 偽装封鎖、sed/python re バイト一致パリティ、len(strips)!=2→unverified の fail-closed ガード、deny 系 3 hook 不波及を TestMaskScopeBoundary で契約化）、T2=入れ子 ( アンカー、T3=フィデリティ ルーティング、T4=孤児 claim 復元＋pid なしロックの O_EXCL 採用、T5=待機窓 10s。grill-code 独立 2 本（A=条件付き 🟡1、B=🟢3）: A J1=マスク置換が production 消費者で未ピン → mutation-killer テストで充足（b79184a）。受容残余（混在クォート横断・SIGSTOP >2分窓・PID 再利用）は v152-security.md に記録。v1.5.2 patch・tag v1.5.2。

### session-history: iteration 34 (レビュー集中修正, 2026-06-21)

全力レビュー（内製5レンズ）＋外部レビュー(E1-E5)の確定 P1/P2 を TDD で修正。A1 emit.sh 利用 6 hook の fail-closed 統一（byte-identity 12 hook・新規 test_hook_emit_failclosed が emit.sh を使う check-*.sh の fallback 必須を動的検査）/ A2 standard で moat4 hook required-registration / C1 setup baseline を実コピー path 限定 / B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。検証: full suite 1006 passed/1 skip・contract(full)・Tier1・各タスク RED→GREEN・盲検3エージェント（核心の fail-closed/normal-path を実走確認・Critical0・scope creep0）。grill-plan 致命2（Task0 を update-gate.sh 経路へ・B4 phase↔gate 自動検査は YAGNI で Batch E 繰延）と grill-code 🟡1 を反映。review gate approve。qa/security/deploy はユーザー判断で短絡し push で締め。コミット f8aff7a〜dd4c593。push は yuuya-miyagaki。

### session-history: iteration 33 (M4 rebuild・簡素化 WS4 最終, 2026-06-21)

観測 hook（E1）の fingerprint/marker 計算を全 Bash hot-path からテストランナー検出時のみへ寄せた。共有 is_test_runner_cmd（evidence.sh・消費側 read_test_result と同一正規化＋AEGIS_TEST_RUNNER_REGEX・単一 sed -e -e/単一 grep -e -e・bash3.2 安全）を新設し append_evidence を条件分岐＝非ランナーは fp 番兵 'skipped'＋marker false の安価記録。post-bash.sh の検出も同関数へ統合（単一ソース化＝recorder/ヒント/reader がドリフト不能）。ゲート時の緑認証ロジック（fail-closed・silent-green 禁止・fp binding）は byte 不変＝『いつ呼ぶか』だけ変更。grill-code（🔴0・🟡1 closed・🟢2 受容）→REDTEAM PoC 18/18→盲検2次 security 独立 approve。pytest 998 passed/1 skip・contract・Tier1・scaffold smoke・パリティ 9。ゲート review🟢／qa🟢／security🟡ack（deps N/A）。版 1.12.0 据置。コミット f02680d/878af23/fb5c5d1/ffd5050/a710328。tests 緑化は record-test-result.py（trusted manual runner）。

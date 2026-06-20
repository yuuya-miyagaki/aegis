# Aegis 簡素化 — M4/M2 引き継ぎメモ

> 2026-06-21 作成。`/clear` 後の新セッションが簡素化の残り（WS4=M4 rebuild / WS2=M2 据置）を
> 文脈ロスなく再開するための引き継ぎ。正典設計＝`docs/plans/2026-06-20-aegis-simplification-design.md`。

## ここまでの完了（3/5・全て push 済み）

| WS | コミット | 状態 |
|----|---------|------|
| 3 M3（skill_behavior_manifest 層1＋skill-pressure-drill 層2 撤去） | 5212c25 / 0658781 | ✅ push |
| 1 examples ミラー廃止（templates/commands へ抽出→撤去） | ecc58c1 / f3eaf08 / 53240a7 / e041a27 | ✅ push |
| 5 docs 整理（archive/reviews/旧 qa-reports/MIGRATION-HISTORY 撤去） | 68ad461 / 6d2d264 | ✅ push |

累計 **約43,000行減**＋自己整合機械の大半（mirror/sync/drift example チェック/manifest/pressure-drill）撤去。origin/main 最新。全層緑で締め。

## 残り

### WS4 = M4 rebuild（**唯一コード挙動を変える・最高 stakes**）
- **要求**: 観測 hook（E1）＝「AI のテスト自己申告でなく*観測実行*でゲート判定」を**保つ**。North Star 直結の B（end user は AI 申告を検証できない）。
- **問題**: fingerprint/marker 計算を**全 Bash コマンドで無条件**に払っている（python3×2＋`fingerprint.sh`→git サブプロセス）。実際に使うのは*テストランナー*の記録だけ。
- **rebuild 方針**: 重い計算を hot-path から外す——「テストランナー検出時のみフル記録／非テストは安価記録 or skip」あるいは「fingerprint はゲート時に遅延計算」。**ゲート時の保証（fail-closed・silent-green 禁止・fingerprint binding）は不変に保つ**。
- **最悪の失敗**: ミスると silent-green（未テストコードが緑認証）＝North Star 最悪。だから慎重に。
- **関連ファイル**: `hooks/post-bash-observe.sh`（記録 hook）→ `hooks/lib/evidence.sh`（`append_evidence`/`_check_test_marker`）→ `hooks/lib/fingerprint.sh`（`fingerprint_worktree`・HEAD sha 混入が load-bearing・docs/.claude 除外）。消費側＝`scripts/build-judge-card.py`（最新テストランナー記録の fp == 現 worktree fp で 🟢）。既存の有界化＝`AEGIS_FP_MAX_FILES`/`AEGIS_FP_MAX_BYTES`（LEARNINGS）。
- **進め方**: design は既に正典#4 にあり。`writing-plans`→`grill-plan`→per-task TDD（RED 実証）→`grill-code`→push。盲検2次も検討（control-plane/検証境界）。

### WS2 = M2 据置（軽微）
- test-strength-drill は **keep**。必要なら「framework タスクは skip 想定」を1行明文化するのみ（コード変更ほぼ無し）。設計#2。

## 必ず適用する今セッションの教訓（hard-won）

1. **検証は pytest だけでは不十分**。`python3 -m pytest -q`＋`python3 scripts/check_framework_contract.py`＋`python3 scripts/run_eval.py`（Tier1）＋`python3 scripts/eval_scaffold_smoke.py`＋dangling grep の**多層**で判定。contract の full self-check は CLI 専用で pytest から到達しない（examples cut で pytest 992 緑のまま contract 19 FAIL を経験）。
2. **参照を消す/変える前に全網羅 grep**：コード（py/sh/json）＋**docs prose**＋**STATUS の structured current_refs**。コード参照だけの manifest は STATUS current_refs（例: requirements=full-review）/ active backlog（security-followups）/ live doc 参照（TO-CLIENT→iter31-batch1）を見落とす。
3. **Bash ツール glitch**：パスを必ずダブルクォート（ハイフン入りパスでも H.replace エラー）。コミットは `git commit -F <file>`。`${...}`/brace は python FILE 経由。
4. **green-between-tasks**：結合した削除は1タスクに原子化。想定 RED（arch-overview の `test_arch_overview_currency` 件数）を RED→GREEN の証拠に使う。`ALL_CHECKS` を増減したら arch-overview の件数を同期。
5. **subagent implementer は大規模 WS で2度タイムアウト**。WS は小タスクに割るか、controller が verify/finish する。
6. **grill が毎回効いた**：grill-plan が examples の `test_phase_skills_required` 見落としを、grill-code が docs の iter31-batch1 過削除を、push 前に捕捉。**plan後 grill-plan・実装後 grill-code は必ず挟む**。

## 参照
- 正典設計: `docs/plans/2026-06-20-aegis-simplification-design.md`
- 各 WS 計画: `docs/plans/2026-06-20-aegis-simplification-0{1,2,3}-*.md`
- 学び: `docs/LEARNINGS.md`（contract CLI 検証・examples cut の教訓）
- STATUS: `docs/STATUS.md`（注: simplification は grill フローで進めたため iteration/gate には未反映＝iteration 32 SF-001 のまま。M4 を formal iteration として起こすかは要判断）

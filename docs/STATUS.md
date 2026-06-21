---
framework: aegis
framework_version: "1.12.1"
project_name: "Aegis"
mode: Dev
phase: review
task_type: framework
task_size: L
task_size_rationale: "iteration 34 = レビュー集中修正（L・完了）: 内製5レンズ＋外部レビューで確定した P1/P2 を修正。A1 emit.sh 利用 6 hook の fail-closed 統一（外部 3→検証で check-deploy-gate 取りこぼし捕捉し 6 hook・byte-identity 12 hook 固定）/ A2 standard で moat4 hook を required-registration / C1 setup baseline を実コピー path 限定 / B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。ゲート: review 承認（judge 緑）・qa/security/deploy はユーザー判断で短絡し push で締め。計画 docs/plans/2026-06-21-aegis-iteration34-review-fixes.md。"
iteration: 34
ui_surface: false
last_updated: "2026-06-21T16:30:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-13-context-futureproof.md
  plan: docs/plans/2026-06-21-aegis-iteration34-review-fixes.md
  spec: null
  review: docs/qa-reports/iter34-review.md
  qa: null
  security: null
  deploy: null
  translation: null
external_evidence:
  - type: "second-opinion-v1-foundation-r1-r2"
    scope: "future-proof 再アーキ計画 2 ラウンドレビュー（IDE Chat）"
    findings: "R1: 全面再アーキは YAGNI(P1) / manifest は declarative mirror=第3同期先(P1) / emit.sh の python3 deny 依存=fail-open(P1) / inherit 従属 / context 数値撤廃のコスト退行 / TDD off / drift advisory 放置 / Phase F schema 過大 / STATUS 実態 drift。R2: emit.sh コメントで静的テスト自己矛盾(P1) / design doc 旧方針残骸(P2)。"
    resolution: "全面 v1.0.0=NO-GO、emit.sh 中心の縮約 Foundation=条件付き GO。pure-bash emit.sh で fail-open 解消、seed manifest と check-secrets 集約は descope。Foundation を F0/F1/F2 で実装し main にマージ（183 tests green）。"
  - type: "second-opinion-v0130-r5"
    scope: "v0.13.0 計画 5 ラウンドレビュー"
    findings: "Round 1〜5 で計 25 件の指摘（hook 出力スキーマ陳腐化、TaskCreated/Completed 制御方式、Plan 条件付き許可、effort 配分、pre-compact.sh 同種破損、`if` 単一 rule 制約等）"
    resolution: "Rev.5 で全件反映、Phase 0a 即時実装着手 GO。hotfix/v0122-hook-schema ブランチで開始。"
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "**【iteration 34 = レビュー集中修正・完了・push 済み 2026-06-21】** 全力レビュー（内製5レンズ）＋外部レビュー(E1-E5)で確定した P1/P2 を修正: A1 emit.sh 利用 6 hook の fail-closed 統一（emit.sh/safety.sh 欠損時の fail-open を解消・外部は 3 hook 指摘だが検証で CLI 版 check-deploy-gate 取りこぼしを捕捉し 6 hook・byte-identity 12 hook 固定）/ A2 standard で moat4 hook を required-registration（登録ドリフト無検出を解消）/ C1 setup baseline を実コピー path 限定（既存ユーザーファイル巻き込み解消）/ B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字(minimal8/standard18+8)+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。検証: full suite 1006 passed/1 skip・contract(full)・run_eval Tier1・各タスク TDD RED→GREEN・盲検3エージェント収束（security: emit.sh/safety.sh 欠損で 6 hook fail-closed 実走確認 / reviewer: normal-path / reviewer-maintainability: approve_with_notes・Critical0・scope creep0）。フロー: brainstorm→plan→grill-plan（致命2: Task0 gate経路/B4繰延）→per-task TDD→grill-code（Critical0・🟡1 C1完全性テスト修正 dd4c593）→盲検3レビュー→review gate approve（judge 緑・証拠 docs/qa-reports/iter34-review.md）。**qa/security/deploy の formal ゲート儀式はユーザー判断で短絡し push で締め（iteration 32 と同パターン・security WORK は盲検 fail-closed 検証済）。** コミット 2071cac〜dd4c593。**残: Batch E（M3/M4 集約・version-sync 集約・P3 群: M7 STATUS tool 非対称/M8 .git/M10 array ガード/M11 ALL_CHECKS/M12 test env 依存）＋戦略（案A immutable moat PoC・ターゲットユーザー検証）＝別 iteration。次タスク未定。** Bash gotcha: パスはクォート・commit は -F・特殊文字は python FILE。push は yuuya-miyagaki アカウント。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-21"
    mode: Dev
    phase: "review"
    note: "iteration 34（レビュー集中修正）完了・push: 全力レビュー（内製5レンズ）＋外部レビュー(E1-E5)の確定 P1/P2 を TDD で修正。A1 emit.sh 利用 6 hook の fail-closed 統一（byte-identity 12 hook・新規 test_hook_emit_failclosed が emit.sh を使う check-*.sh の fallback 必須を動的検査）/ A2 standard で moat4 hook required-registration / C1 setup baseline を実コピー path 限定（INSTALLED_PATHS funnel＋git-ignore skip）/ B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。検証: full suite 1006 passed/1 skip・contract(full)・Tier1・各タスク RED→GREEN・盲検3エージェント（2件 infra stall だが核心の fail-closed/normal-path を実走確認・1件 complete=approve_with_notes・Critical0・scope creep0）。grill-plan 致命2（Task0 を update-gate.sh 経路へ・B4 phase↔gate 自動検査は YAGNI＋ロジック不全で Batch E 繰延）と grill-code 🟡1（C1 baseline 完全性テスト）を反映。review gate approve（judge 緑・record-test-result で緑確立）。qa/security/deploy の formal ゲートはユーザー判断で短絡し push で締め（iteration 32 同パターン）。コミット f8aff7a〜dd4c593。push は yuuya-miyagaki アカウント。残=Batch E＋戦略 PoC は別 iteration。"
  - date: "2026-06-21"
    mode: Dev
    phase: "security"
    note: "iteration 33（M4 rebuild・簡素化 WS4 最終）完了: 観測 hook（E1）の fingerprint/marker 計算を全 Bash hot-path からテストランナー検出時のみへ寄せた。共有 is_test_runner_cmd（evidence.sh・消費側 read_test_result と同一正規化＋AEGIS_TEST_RUNNER_REGEX・単一 sed -e -e/単一 grep -e -e・bash3.2 安全）を新設し append_evidence を条件分岐＝非ランナーは fp 番兵 'skipped'＋marker false の安価記録。post-bash.sh の検出も同関数へ統合（単一ソース化＝recorder/ヒント/reader がドリフト不能）。ゲート時の緑認証ロジック（fail-closed・silent-green 禁止・fp binding）は byte 不変＝『いつ呼ぶか』だけ変更。フロー: brainstorm（設計#4 既承認）→plan→grill-plan（致命2: 検出 grep 畳み込み/契約ベースライン、YAGNI: 版バンプ撤去 を反映）→per-task TDD（各タスク RED 実証）→grill-code（🔴0・🟡1=canonical FIXTURES 40+形を実関数に通すパリティ実証で closed・🟢2 受容）→REDTEAM PoC 18/18（marker forge fail-closed 不変）→盲検2次 security 独立=approve（silent-green 不可能を 64-hex 番兵壁で実証・4方向 fail-close 実走確認）。検証多層: pytest 998 passed/1 skip・contract・Tier1・scaffold smoke・パリティ 9。ゲート: review🟢／qa🟢（B1 は committed-code で working-tree diff 空＝skip 宣言＋手動 mutation 同等実証）／security🟡ack（外部依存 manifest 無し＝deps N/A）。版 1.12.0 据置（iteration counter と framework_version は直交・他簡素化 WS と同様バンプなし）。コミット f02680d/878af23/fb5c5d1/ffd5050/a710328＋ゲート証拠。本 session は observe hook が tool_response.output を hook に渡さない（全 1160 エントリ marker_verified:false）ため tests 緑化は record-test-result.py（trusted manual runner・実行記録・src=manual は marker 不要）で確立。deploy/ship/docs は solo の push で締め。残: 簡素化 WS2=M2 据置（1行明文化）。push は yuuya-miyagaki アカウント。"
  - date: "2026-06-18"
    mode: Dev
    phase: "docs"
    note: "iteration 31（ドッグフード由来 改善・Batch1 / v1.11.0）完了: スタジオ・ナギ予約LP で v1.10.0 を Client→Dev 一周ドッグフードして見つかったハーネス自身の摩擦（OBS-001〜022）のうち配布ブロッカー 6 タスクを修正。1.1 setup.sh が新規 install に baseline commit（fresh のみ・既存リポ no-op・scoped add・identity fallback／OBS-017）、1.2 judge stub 走査のみ control-plane 除外・secret 走査は全走査維持（後退ゼロ）、1.3 証拠スクリプト allowlist、1.4 bare git add staging→ask、1.5 read-only パイプ allow（最終セグメント fail-open を TDD で捕捉）、1.6 書込み先 path のみ deny（pure-bash mask_quoted＋redirect target＋no-write コマンドのアロウリスト・cmdsub/改行 fail-closed）。設計核心: write-target 判定は安全コマンドのアロウリスト（echo/printf/git commit）で行いブロックリストは使わない（列挙漏れ）。全タスク Step0→TDD→commit。ユーザー選択 A（Batch1 先行ゲート）で review→qa→security→deploy 全承認。review=3 ラウンド盲検 break-attempt が Batch1 由来 Critical 2 件（write-util ブロックリスト穴 76112bc・改行バイパス 8f85a5b）を検出→fix-forward。security=1次（security エージェント）＋盲検2次とも approve_with_notes、新規 WRITE バイパス ゼロを orig(8f8eb2d) vs new HEAD 実走で確認。qa=B1 mutation drill は committed-code 構造制約（working-tree diff 空）で skip 宣言＋手動 4-mutant 実証（4/4 CAUGHT）。版 1.10.0→1.11.0（contract/template/example/live STATUS 統一）。full suite 830 passed/1 skip・REDTEAM 18/18＋5/5・contract 全 profile・drift・mirror・scaffold smoke・distribution 全 PASS。コミット 52dff43〜6d1b938＋76112bc/8f85a5b＋evidence/版 367e1f0。**SF-001（control-plane の literal `hooks/` 一致回避＝quote分割/backslash/bare-dir。pre-existing＝orig でも同一 allow を実走確認・Critical・deploy blocker 非該当）を docs/security-followups.md に durable 記録＝最優先 follow-up（繰延合意）。** 残: Batch2（skill/契約/配布整合5）+Batch3（Client書込み2）+X.1/X.2＝iteration 32。**残: dev_ready_for_client 承認 → push（明示承認まで保留・自動 push しない）。**"
---

## Summary

Claude Code ネイティブの Aegis 運用フレームワーク。2026-06-05、モデル進化（Opus 4.8）
に耐える future-proof 再アーキに着手。v0.13.0 Phase 0b（新 Skill/Cron gate・Task event hook・
スキル aegis-* 改名）を確定後、Foundation を実装: hook 出力スキーマを `hooks/lib/emit.sh` に
単一化（pure-bash・外部依存ゼロ）、破壊パターンを `hooks/lib/patterns.sh` に隔離、version owner
を一本化。挙動不変・183 tests green・main マージ済み（origin 未push）。

## Recent Decisions

- 設計原則を「保証=決定論的強制 / 手順=モデル委譲 / 揮発値=隔離」の 3 層に分解（再アーキの土台）
- emit.sh は pure-bash（python3/jq 非依存）→ deny/block が fail-open しない（Round 2 P1 解決）
- 全面 v1.0.0 再アーキは見送り、emit.sh 中心の Foundation を先行（YAGNI、Round 1）
- seed manifest と check-secrets の patterns 集約は descope（実消費者が出来てから、Round 2 J-1）
- MCP matcher: `mcp__.*__deploy.*` — `push` は除外（通常リモート更新と区別不能）
- Ref チェック: v0.12.0 は DEPRECATION WARNING のみ、v0.13.0 で ERROR 化予定
- Name lint: regex 一本ではなく、ファイル種別ごとの小さい extractor に分割
- Health check: 警告のみ（ブロックなし）、session-start.sh から呼び出し
- Item 3 (Lean/Full プロファイルモード) はセカンドオピニオンにより v0.13.0 に延期

## Session History

- 2026-04-15: v0.7.0-v0.7.2 実装。ネイティブ機能改善、scaffold自己完結性、信頼境界ハードニング。
- 2026-04-17: v0.8.0 Client モード強化 実装完了+全ゲート通過+コミット+プッシュ。48ファイル変更。
- 2026-04-18: v0.9.0-v0.10.0 integration-assist, browser-assist。全ゲート通過+コミット+プッシュ。
- 2026-04-22: v0.11.0 Hair Salon Bloom 振り返り7施策実装+コミット+プッシュ。
- 2026-04-22: v0.12.0 MCP gate + ref check + name lint + health check。48テスト全PASS。
- 2026-06-05: future-proof 再アーキ着手。Phase 0b 確定 + Foundation（emit.sh 単一出力源 / patterns.sh / version owner）実装。Round 1/2 セカンドオピニオン反映。183 tests PASS、main マージ（未push）。
- 2026-06-06: Phase R 再配分を連続 ship（routing 0.12.3／context 0.12.4／model-effort／name-hygiene／TDD 0.12.5／evidence 完了強制 0.12.6）。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋version **1.0.0**。各タスクで brainstorm→2段グリル→実装→grill-code を完走。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0「トレッドミルから降りる」看板を掲示。**
- 2026-06-07: 機能整合性監査（charter 2026-06-07）。Layer 0-4 で 7 finding（P1×1/P2×4/P3×2）全修復。核心 F6（P1）＝setup.sh が hooks/lib を配布せず install 先で moat 全死→copy_hooks 修復＋scaffold smoke の hook 実発火で install 経路を契約化。v1.3.2 patch（298 tests・tag v1.3.2）。

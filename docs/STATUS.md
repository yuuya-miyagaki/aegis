---
framework: aegis
framework_version: "1.6.2"
project_name: "Aegis"
mode: Dev
phase: deploy
task_type: framework
task_size: L
task_size_rationale: "確定（brainstorm→plan→grill-plan→実装→grill-code）: 第6回全力レビュー（full-review-2026-06-13.md、6 軸並列）で実証された Critical 16 件のうち機械 moat + 配布パス + UX の 13 件（K-1〜K-13）+ S-1/DIST-12 前倒し。実装は計画通り 7 task + 9 commit、grill-code が指摘した残 Critical 2 件（Path B 全 redirect 走査・evidence.sh head+tail 抽出）を追加 1 commit で吸収。合計 10 commit + release。"
iteration: 23
ui_surface: false
last_updated: "2026-06-13T06:50:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: approved
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-13.md
  plan: docs/plans/2026-06-13-v162-improvement-plan.md
  spec: null
  review: docs/qa-reports/v162-review.md
  qa: docs/qa-reports/v162-qa.md
  security: docs/qa-reports/v162-security.md
  deploy: docs/qa-reports/v162-deploy-checklist.md
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
next_action: "iteration 23（v1.6.2 全力レビュー fix-forward）完了: 10 commit + release で Critical 13 件（K-1〜K-13）+ S-1/DIST-12 前倒し + grill-code Critical 2 件を消化、683 tests / contract / drift / smoke / 18 PoC 全 PASS。残: tag v1.6.2 付与＋origin push（ユーザ判断）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-13"
    mode: Dev
    phase: "deploy"
    note: "iteration 23（v1.6.2 第6回全力レビュー fix-forward）完了: 6 軸並列レビュー（敵対バイパス再 PoC + 障害モード + パフォーマンス + 配布パス + 競合比較 + 非エンジニア E2E）で Critical 16 件抽出。grill-plan で致命 5 件反映、Task 1〜7 を TDD 実装（K-1 3 軸 zero-run gate / K-2-4 cmdsub + quoted-var fail-closed / K-5-7 safety.sh + atomic snapshot + timeout / K-8-11 配布パス破壊抑止 + version stamp / K-10 prereq + K-12 ARTIFACT_TO_TEMPLATE + K-13 cheatsheet 🟡 ack 例）。grill-code が Path B 単一 redirect 走査と evidence.sh tail-only 抽出の 2 Critical を発見、追加 1 commit で吸収。18 PoC 全 PASS、683 tests OK（unittest discover）、contract / drift / smoke 全 PASS。配布パスは framework_version stamp + atomic snapshot + ユーザ設定保存 + framework_root self-install abort + python3 prereq で F6 / DIST 系統を根治。S-1 と DIST-12 は v1.7 計画から前倒し。残 K-14（PERF-1）/ K-15（PERF-2）/ K-16（README）は v1.7 へ送り。"
  - date: "2026-06-12"
    mode: Dev
    phase: "implement"
    note: "iteration 22（v1.6.1 全力レビュー fix-forward）開始: 第5回全力レビュー（軸 A〜F 並列 6 サブエージェント・docs/full-review-2026-06-12.md）で実証された Critical 7 件 + S-3/S-11 の fix-forward。Critical 全 9 件は PoC/grep/measurement で実証済み（C-1 制御プレーン変数展開・C-2 test green 偽装・C-3 client gate touch・C-4 SessionStart resume 欠落・C-5 user-invocable 表 17 件 drift・C-6 hook/lib/drift カウント・C-7 テスト sleep 70%・C-8 巨大関数・C-9 credentials 4 形式）。C-7/C-8 は構造 refactor のため v1.7 へ送り、v1.6.1 は狭く深い security + drift 修正に絞る。plan は grill-plan で 5 致命的・5 要検討を指摘されて全反映（Schema Migration / Phase 進行表 / Commit プラン / 受容済みリスク / Release Checklist の 5 章追加、Task 1/2/3/7 の検知ロジック精緻化、Task 0/6 のテスト境界修正）。ブランチ fix/v1.6.1-critical-bypasses で TDD 実装中。"
  - date: "2026-06-12"
    mode: Dev
    phase: "deploy"
    note: "iteration 21（v1.6.0 fix-forward P1×4）: behavioral-review-report-2026-06-12 §5.1 の P1×4 を Task 1〜15 TDD で完走（479→508 tests）。P1-A=skill 構造起動（phase-skills.sh 単一所有＋SessionStart/phase 遷移 additionalContext 注入＋BFS 到達性の drift/smoke 契約化＋path 形式正規化 14 箇所）、P1-B=full への skill 参照テンプレ 6 件配布＋参照実在契約、P1-C=judge card 承認時 transcript push＋scanner decode 耐性、P1-D=client_ready_for_dev 6 成果物の承認側＋完了側対称検査。計画乖離 2 件は強化方向（SKILL_REF_EXCLUDE=存在マニフェストの root 化除外・tier0 timeout 300s 追従）。grill-code 独立 2 本（A=マージ可 🟡3/🟢3、B=S1 修正後マージ 🟡4/🟢3）: 合流点 S1=names regex のコメント横断偽 root（vacuous CLEAN 再演リスク）→ 非コメント行 anchor＋テストで充足（a8411fb・実 repo トークン 15 件ちょうどを実測）。B-S2/S3/S4・A🟡2/3 は理由付き記録（v160-review.md）・B-S3 は security 残余 #4 に統合。テスト記録 manual green（信頼ランナー・fp=HEAD 一致）・4 ゲート --ack 承認＝ユーザー委任の代行（証跡 v160-*.md）。v1.6.0 minor で締め・tag v1.6.0。origin push は別途ユーザー判断。"
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

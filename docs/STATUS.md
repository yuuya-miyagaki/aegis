---
framework: aegis
framework_version: "1.3.2"
project_name: "Aegis"
mode: Dev
phase: brainstorm
task_type: framework
task_size: L
task_size_rationale: "機能整合性監査（charter 2026-06-07）の修正フェーズを完了し v1.3.2 patch で締め。調査 Layer 0-4 で7 finding（P1×1/P2×4/P3×2）を実証検出。核心 **F6（P1）**＝setup.sh が hooks/lib/emit.sh・patterns.sh を配布せず install 先で全 hook が source 時に死＝moat 全死を、copy_hooks の lib 全コピーで修復。F3 retro graceful 版配送／F2 judge 配布／F4 status_doctor 配布／F1 contract manifest に稼働 hook4件追跡／F5・F7 polish。各 TDD（RED→GREEN）＋2段グリル（grill-plan→grill-code）。install 経路を scaffold smoke の hook 実発火検証で契約化し静的検査の死角（setup.sh 出力が無検査だった）を恒久封鎖。FRAMEWORK_VERSION 1.3.1→1.3.2＋STATUS template/docs 同期＋README 移行節 v1.3.1→v1.3.2＋tag v1.3.2。298 tests・contract(full/standard)・drift(mirror)・tier2・--strict 全 PASS。運用契約に変更なし。出典 docs/functional-integrity-audit-report-2026-06-07.md。"
iteration: 15
ui_surface: false
last_updated: "2026-06-07T12:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: pending
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: null
  spec: null
  review: null
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
next_action: "機能整合性監査 v1.3.2 締め完了（全 finding F1-F7 修正・install 先で moat 実発火を実地確認・298 tests／contract(full/standard)／drift(mirror)／tier2／--strict 全 PASS・tag v1.3.2）。report＝docs/functional-integrity-audit-report-2026-06-07.md。最大の収穫＝install 経路（setup.sh 出力）が無検査だった死角を scaffold smoke の hook 実発火で契約化。**次タスク未定。**"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-05"
    mode: Dev
    phase: "implement"
    note: "future-proof 再アーキ着手。Phase 0b WIP を確定コミット後、Foundation 実装（F0 棚卸し+version owner / F1 pure-bash emit.sh 単一出力源+全16hook置換 / F2 patterns.sh）。Round 1/2 セカンドオピニオン反映。183 tests PASS、main にマージ（origin 未push）。"
  - date: "2026-06-06"
    mode: Dev
    phase: "implement"
    note: "Phase R 再配分(0.12.3〜0.12.6: routing/context/model-effort/name-hygiene/TDD/evidence)を連続 ship。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋**version 1.0.0**。各 2段グリル反映。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0。**"
  - date: "2026-06-07"
    mode: Dev
    phase: "docs"
    note: "機能整合性監査（charter 2026-06-07）を実行。Layer 0-4 で7 finding 実証検出（P1×1/P2×4/P3×2）。**F6（P1）＝setup.sh が hooks/lib/emit.sh・patterns.sh を配布せず install 先で全 hook が source 時に死＝決定論 moat 全死**を copy_hooks 全 lib コピーで修復。F3 retro graceful 配送／F2 judge 配布／F4 status_doctor 配布／F1 contract hook4件追跡／F5・F7 polish。各 TDD＋2段グリル。install 経路を scaffold smoke の hook 実発火で契約化（静的検査の死角を恒久封鎖）。再検証で Layer 0 全 green＋ライブ install の moat 実発火を実証。v1.3.2 patch で締め（298 tests・contract・drift・tier2・--strict 全 PASS・tag v1.3.2）。"
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

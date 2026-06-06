---
framework: aegis
framework_version: "0.12.6"
project_name: "Aegis"
mode: Dev
phase: implement
task_type: framework
task_size: M
task_size_rationale: "Phase R 最終項目: evidence 完了の TaskCompleted 強制化。(B) check-task-completed.sh 拡張。grill-plan 2巡で『新規二層実装』→『validate_status_file の gate-ref＋実在ロジックを evidence_integrity_violations に抽出・再利用』へ転換（gate_ref_mapping→GATE_REF_MAPPING 定数化で3重複解消）。Stop hook 却下・バイパス無し。実装完了: check_status.py + hook(root/example IDENTICAL) + テスト + v0.12.6、195 tests green。"
iteration: 9
ui_surface: false
last_updated: "2026-06-06T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: "docs/plans/2026-06-06-v1-evidence-completion-hook-implementation.md"
  spec: "docs/plans/2026-06-06-v1-evidence-completion-hook-design.md"
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
next_action: "evidence 完了強制化(B案) 実装完了（v0.12.6・195 tests green・contract/drift 0）。validate_status_file ロジック再利用＋check-task-completed.sh 配線＋CLAUDE.md 明文化。次は grill-code → review ゲート。governing doc: docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md。Phase R は本件で完了。残: README/INTEGRATION/version 整理(v1.0.0)・context observability(YAGNI 保留)。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-05-15"
    mode: Dev
    phase: "docs"
    note: "v0.12.2 hotfix ship 完了。Round 6-9 で 9 件追加修正（pre-compact exit 0 化、minimal-project 完全同期、コメント整合、stale last_updated 解消等）。134 tests PASS + tier 1/2 PASS。"
  - date: "2026-06-05"
    mode: Dev
    phase: "implement"
    note: "future-proof 再アーキ着手。Phase 0b WIP を確定コミット後、Foundation 実装（F0 棚卸し+version owner / F1 pure-bash emit.sh 単一出力源+全16hook置換 / F2 patterns.sh）。Round 1/2 セカンドオピニオン反映。183 tests PASS、main にマージ（origin 未push）。"
  - date: "2026-06-06"
    mode: Dev
    phase: "implement"
    note: "Phase R 再配分を連続実装・origin push: routing 原則化(0.12.3)・context budget 原則化(0.12.4)・model/effort inherit・name-hygiene・TDD profile(0.12.5)。続けて Phase R 最終 evidence 完了強制化(0.12.6): validate_status_file の gate-ref＋実在ロジックを evidence_integrity_violations に抽出・再利用し check-task-completed.sh で TaskCompleted 時に強制。2段グリル反映。195 tests green。Phase R 完了。"
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
- 2026-06-06: Phase R 再配分を連続 ship（origin push 済み）。routing 原則化(0.12.3)・context budget 原則化(0.12.4)・model/effort inherit・name-hygiene・TDD profile + escape hatch(0.12.5)。続けて Phase R 最終 evidence 完了強制化(0.12.6): validate_status_file の gate-ref＋実在ロジックを evidence_integrity_violations に抽出・再利用、check-task-completed.sh で TaskCompleted 時に強制。2段グリルで再実装→再利用へ転換。195 tests green。Phase R 完了。

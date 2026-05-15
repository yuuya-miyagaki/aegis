---
framework: aegis
framework_version: "0.12.2"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "v0.12.2 hotfix: 11 hooks の出力スキーマ移行（PreToolUse 8 + PostToolUse 1 + PostToolUseFailure 1 + PreCompact 1）+ if 削除 + テスト追加。各 hook 小規模パターン適用。"
iteration: 7
ui_surface: false
last_updated: "2026-05-15T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: n/a
  dev_ready_for_client: approved
current_refs:
  requirements: []
  plan: "docs/plans/v0130-modernization-plan.md"
  spec: null
  review: "docs/qa-reports/v0122-review.md"
  qa: "docs/qa-reports/v0122-review.md"
  security: "docs/qa-reports/v0122-review.md"
  deploy: null
  translation: null
external_evidence:
  - type: "second-opinion-v0130-r5"
    scope: "v0.13.0 計画 5 ラウンドレビュー"
    findings: "Round 1〜5 で計 25 件の指摘（hook 出力スキーマ陳腐化、TaskCreated/Completed 制御方式、Plan 条件付き許可、effort 配分、pre-compact.sh 同種破損、`if` 単一 rule 制約等）"
    resolution: "Rev.5 で全件反映、Phase 0a 即時実装着手 GO。hotfix/v0122-hook-schema ブランチで開始。"
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "v0.13.0 Phase 0b へ。新 PreToolUse / event hook（Skill, CronCreate, TaskCreated, TaskCompleted）追加、スキル名衝突解消、secrets/destructive パターン拡張、`extract_exit_code` 両キー対応。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-04-22"
    mode: Dev
    phase: "review"
    note: "v0.12.0→v0.12.1 レビュー2ラウンド。Client/Dev境界・n/a model・reset ref・template保護等11件修正。118テスト全PASS。"
  - date: "2026-05-08"
    mode: Dev
    phase: "implement"
    note: "v0.13.0 計画策定 + 5 ラウンドレビュー（25件指摘 全反映）。v0.12.2 hotfix Phase 0a 着手。Claude Code 公式 hook 出力スキーマへ全面移行 + if 削除 + post-bash PostToolUseFailure 移行。"
  - date: "2026-05-15"
    mode: Dev
    phase: "docs"
    note: "v0.12.2 hotfix ship 完了。Round 6-9 で 9 件追加修正（pre-compact exit 0 化、minimal-project 完全同期、コメント整合、stale last_updated 解消等）。134 tests PASS + tier 1/2 PASS。"
---

## Summary

Claude Code ネイティブの Aegis 運用フレームワーク。v0.12.0 では
MCP deploy gate hook、/gate ref チェック強化（DEPRECATION WARNING）、
Skill/Agent/Command 名 lint、STATUS.md health check の 4 項目を実装。

## Recent Decisions

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

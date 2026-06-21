---
framework: aegis
framework_version: "1.13.0"
project_name: ""
mode: Client
phase: onboard
task_type: feature
iteration: 1
ui_surface: false
# task_size_rationale: "サイズ判定の根拠を書く（task_size 設定時に推奨）"
last_updated: ""
# gate name = phase whose output is approved; mode-transition gates unlock
# movement between Client and Dev
gate_approvals:
  client_ready_for_dev: pending
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
# external_evidence.type は kebab-case 推奨（例: codex-review-v071-1）
external_evidence: []
client_context:
  client_id: ""
  context_loaded: false
failure_tracking: null
next_action: ""
blockers: []
session_history: []
---

## Summary

- 現在の状況を 3〜5 行で簡潔に記録する
- 詳細本文は別ファイルに置き、ここは index と next step に集中する

## Recent Decisions

- 重要な判断だけを箇条書きで残す

## Session History

- frontmatter の session_history は最新 3 件のみ保持する
- 古いエントリはこのセクションに退避する
- external_evidence も最新 3 件のみ保持し、古いものは docs/evidence-archive.md に移す
- 完了した second-opinion ファイルは docs/reviews/ にアーカイブする

# v0.12.0 → v0.12.1 Review Report

Date: 2026-04-22
Reviewer: User (2 rounds) + Claude Opus 4.6

## Verdict

**PASS** (全所見修正済み)

## Round 1 — v0.12.0 レビュー所見 (6 件)

| ID | Priority | 項目 | 修正 |
|----|----------|------|------|
| P1 | CRITICAL | Client/Dev 境界 gate enforcement | check_phase_transition に cross-mode 境界チェック追加 |
| P2a | HIGH | translation ref 契約漏れ | ファイル存在チェック + gate_ref_mapping に追加 |
| P2b | HIGH | templates 整合性保護 | check-gate.sh で templates を docs allowlist から分離 |
| P2c | HIGH | secrets hook monorepo gap | check-secrets.sh を recursive find に変更 |
| P2d | CRITICAL | n/a gate model 衝突 | update-gate.sh に na/reset action 追加、post-status-audit 全変更検出 |
| P3 | MEDIUM | eval coverage gaps | tier 0 追加、full profile を PROFILES に追加 |

## Round 2 — v0.12.1 レビュー所見 (5 件)

| ID | Priority | 項目 | 修正 |
|----|----------|------|------|
| P1a | P1 | reset で ref fields 未クリア | update-gate.sh に gate→ref mapping 追加、reset 時に ref を null 化 |
| P1b | P1 | na が feature/refactor/framework で bypass 可能 | pre_na_gate に task_type チェック追加 (bugfix/hotfix のみ許可) |
| P2a | P2 | tier 2 full profile 常時 FAIL | eval_scaffold_smoke.py から full を除外 (framework repo 検証は tier 1) |
| P2b | P2 | example STATUS.md translation ref 不整合 | translation: null → docs/translation/mapping.md |
| P3 | P3 | example gate.md angle-bracket placeholder | PLACEHOLDER_ALLOWLIST に `<gate>` 追加 |

## Validation

- `python3 -m unittest discover tests -v` → 118 tests PASS
- `python3 scripts/lint_names.py` → 0 issues
- `python3 scripts/run_eval.py --tier 0` → PASS
- `python3 scripts/run_eval.py --tier 2` → PASS (minimal + standard)

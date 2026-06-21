# iteration 34 review gate — レビュー証拠

> bug-fix イテレーション（レビュー集中修正）。計画: `docs/plans/2026-06-21-aegis-iteration34-review-fixes.md`。
> 対象 diff: `git diff f8aff7a..HEAD`（実装コミット 2071cac〜dd4c593）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 |
|---|------------|------------|------|
| A1 | emit.sh 利用 6 hook の fail-closed 統一 | hooks/check-{deploy-gate,deploy-mcp-gate,skill-gate,cron-gate,client-info,tdd}.sh / tests/test_hook_emit_failclosed.py / tests/test_safety_fallback_identity.py | done |
| A2 | standard で moat4 hook を required-registration | templates/profiles/standard.json / tests/test_profile_moat_registration.py | done |
| C1 | setup.sh baseline を実コピー path に限定 | bin/setup.sh / tests/test_setup_baseline.py | done |
| B1 | vacuous な full-scaffold safety テスト実効化 | tests/test_safety_lib_registered_in_profiles.py | done |
| B3 | missing-ref テストに rc 検証 | tests/test_check_status.py | done |
| D1 | README profile 数字 + guarantee 限定 | README.md / tests/test_readme_profile_counts.py | done |
| D2 | check-secrets scope 明記 | hooks/check-secrets.sh | done |
| V1 | 版 1.12.0→1.12.1 | scripts/check_framework_contract.py / templates/STATUS.template.md / docs/STATUS.md | done |

未着手タスク: なし。Batch E / B4 / 案A は計画どおり別 iteration（scope 外・diff 混入なし＝盲検レビューで scope creep ゼロ確認）。

## Findings（severity / confidence）

### Critical
該当なし。

### Major
該当なし。（grill-code が挙げた C1 baseline 完全性テスト欠落＝当初 Major 相当は dd4c593 で解消済み。）

### Minor
- tests/test_hook_emit_failclosed.py:23（conf 6）— test 間 import（`from test_safety_lib_missing import ...`）。pytest 下で動作。共有ヘルパ抽出は churn 回避で据置。
- bin/setup.sh（baseline ループ・conf 6）— `git check-ignore` を path ごとに subprocess 起動。install は一度きりで実害なし。
- bin/setup.sh:348（conf 7）— `ensure_target_gitignore` の INSTALLED_PATHS 追記条件は全ケースで正しいが推論が fragile（盲検2次指摘）。実害なし＝据置。

## Evidence checklist
- [x] diff を実読した（self grill-code ＋ 盲検3エージェントが実ファイル走査）
- [x] plan の受入条件と突合（対照表・全タスク done）
- [x] 未カバーのエッジケース列挙（C1 の空配列/空 dir/check-ignore error・A1 normal-path）
- [x] 全 finding に severity + confidence 付与

## 多層検証（machine facts）
- full suite: **1006 passed / 1 skipped**（pytest tests/）
- contract: `check_framework_contract.py --profile=full` **PASS**
- tier1: `run_eval.py --tier 1` **PASS**（status_doctor / contract / drift）
- 各タスク TDD: RED（失敗実証）→ GREEN を個別に確認（A1 は emit.sh 欠損で実 fail-open を RED 実証）
- A1 fail-closed: byte-identity を 12 hook で機械固定（test_safety_fallback_identity）＋ emit.sh/safety.sh 欠損実走で 6 hook が deny rc=0
- check-deploy-mcp-gate の normal DENY（`ls` payload）は deploy-ready 未充足による pre-existing 挙動。diff 上、決定ロジックは byte 不変（fallback 挿入と source→aegis_require_lib のみ）＝regression 非該当

## 判定: **PASS**（Critical/Major ゼロ・全タスク done・多層緑・scope creep ゼロ）

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["なし（1次/2次とも非ブロッキング note のみ・Critical 0 で収束）"]
  agents:
    reviewer_general: partial（infra stall）— 全 hook normal-path exit 0 + valid output を独立確認
    security: partial（infra stall）— emit.sh/safety.sh 欠損で 6 hook 全て fail-closed（deny rc=0）を独立実走確認・regression 懸念は diff で closed
    reviewer_maintainability: complete — verdict=approve_with_notes / Critical 0 / scope creep 0 / A1 byte-identity OK / C1 accumulation 完全
  note: agent stall は本リポ既知の infra 事象（iteration 32-33 と同様）。部分結果＋diff 突合で核心主張を確証。
```

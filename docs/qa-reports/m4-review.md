# M4 review レポート（iteration 33）

対象: 観測 hook の fingerprint/marker を hot-path から外す（commits `457f632..HEAD`）。
計画: `docs/plans/2026-06-21-aegis-m4-fingerprint-hotpath-rebuild.md` / 設計: `docs/plans/2026-06-20-aegis-simplification-design.md` #4。

## 対照表（plan タスク → 実装）

| # | plan タスク | 実装ファイル | 状態 |
|---|------------|------------|------|
| 1 | 共有 is_test_runner_cmd | `hooks/lib/evidence.sh:202-227` ＋ `tests/test_evidence_lib.py::TestIsTestRunnerCmd` | 完了 |
| 2 | append_evidence ゲート化 | `hooks/lib/evidence.sh:240-252`（条件分岐）＋ schema コメント ＋ `tests/test_evidence_lib.py`（非ランナー skip/ランナー fp） | 完了 |
| 3 | post-bash.sh 統合 | `hooks/post-bash.sh:30-34`（検出を共有関数へ） | 完了 |
| 4 | 不変条件ガード＋多層検証 | `tests/test_evidence_hooks.py::test_non_runner_observation_does_not_certify` | 完了 |
| grill | パリティ実証 | `tests/test_patterns_parity.py::test_fixtures_is_test_runner_cmd` | 完了 |

未着手タスクなし。版・iteration・gate 構成は計画どおり（逸脱なし）。

## findings（1次＝grill-code）

- 🔴 Critical: 0
- 🟡 Should fix: 1 ＝「canonical FIXTURES が is_test_runner_cmd 実関数を通っていない」→ `test_fixtures_is_test_runner_cmd`（40+ 形・緑偽装防止 `'"echo" pytest'`→False 含む）を追加し**実証で closed**（commit a710328）。
- 🟢 Nice to have: 2（呼出側の cmd 長差コメント・char500 超 false-negative＝pre-existing fail-closed）。受容。

## evidence checklist

- [x] diff を実読（chat summary でなく実ファイル・`git diff 457f632..HEAD`）
- [x] plan/spec の受入条件（#4・保証不変）と突合
- [x] エッジケース列挙（空配列/不正 regex/set-e -u/truncation/失敗パス）
- [x] 全 finding に severity 付与

## 判定: PASS（理由: 🔴 ゼロ・🟡 は実証付きで closed・保証不変を多層で確認）

```claims
verdict: approve
tests_pass: true
no_stubs: true
second_opinion:
  verdict: approve
  divergence_points: none
```

注: 2次は security 観点の盲検独立レビュー（1次 verdict 非開示・diff/spec のみ）。`docs/qa-reports/m4-security.md` に詳細。1次/2次とも approve＝相違なし。

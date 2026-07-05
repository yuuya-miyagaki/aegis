# QA レポート（iter56）
<!-- 正本: qa agent -->

> QA agent が実行した確認と証拠を要約する。VERIFICATION は自己検証用であり、
> 本レポートとは別物。

## 対象

- 変更内容: iter56 M2 フィードバック反映（候補①〜⑥＋可視性⑦a/b・9コミット・
  仕様= docs/specs/2026-07-05-iter56-m2-feedback-design.md）
- 環境: macOS（darwin）・Python 3 stdlib・bash 3.2（macOS 既定）・pytest

## 実施した確認

- [x] full suite 実行（1319 passed / 3 skipped・0:04:06）
- [x] 決定論検査一式（check_status / check_framework_contract / check_reference_drift /
      lint_names / context_budget）すべて PASS
- [x] ① 実地スモーク: `git add .env.example` → allow（`{}`）・`(cd sub && git add .)`
      → deny・`git add .>out` → deny を hook への実入力で確認
- [x] ③⑦a 実挙動: compute_verdict を直接実行し、approve×approve_with_notes の
      🟡 抑止＋情報行・bool/プレースホルダ verdict の値不正 🟡・unverified 文言の
      是正手順を確認（review 承認時のカードで③の実運用初通過も確認）
- [x] ⑥ install 実在: setup.sh --profile=full を tmp へ実走し、manifest 実行可
      （allow|ask）全スクリプトの実在を検証（test_full_profile_runnable_scripts）
- [x] ②(b) evidence 受理: qa ref=claims 付き QA レポートを TaskCompleted 検査が
      受理することを回帰固定（test_qa_ref_claims_report_is_accepted）
- [x] test-strength ドリル: skip 宣言（working-tree diff 空・代替実証を .drill に明記）

## 実行コマンド

```bash
python3 -m pytest -q tests/            # 1319 passed, 3 skipped
python3 scripts/check_status.py        # PASS
python3 scripts/check_framework_contract.py  # PASS
python3 scripts/check_reference_drift.py     # PASS
python3 scripts/lint_names.py          # LINT: all names consistent
python3 scripts/record-test-result.py "python3 -m pytest -q"  # recorded: green
```

## 結果

- Pass: full suite 1319（うち iter56 新規テスト 32: broad-dot 11・方向4/配布整合 7・
  judge 段階化/値不正/情報行 9・spec-delta 1行 2・guidance token 4・evidence 受理 1 ほか）
- Fail: 0
- Skip: 3（既存・環境依存の意図的 skip）

## ブラウザ QA（ui_surface: true の場合）

- 対象外（ui_surface: false・framework 内部変更のみ）

## Blockers

- なし

## Claims（judge が機械読取する）

```claims
verdict: approve
tests_green: true
```

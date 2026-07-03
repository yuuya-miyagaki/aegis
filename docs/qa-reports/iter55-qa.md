# iter55 QA — ドッグフード一周目フィードバック反映

- 対象: iteration 55（v1.15.0→v1.16.0）。許可リスト単一正本化ほか P0-P4＋2次レビュー修正。
- 参照: 計画 `docs/plans/2026-07-03-iter55-dogfood-feedback-plan.md`／レビュー `docs/qa-reports/iter55-review.md`

## 機能対照表（要件/plan の機能 → 検証対象 → 方法 → 判定）

| # | plan 機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | scripts-manifest.tsv 単一正本＋is_allowlisted manifest 化 | hooks/check-control-plane.sh・hooks/lib/scripts-manifest.tsv | test_scripts_manifest_hook（allow∪ask 12本 ALLOW・framework-only DENY・欠落 fail-closed・chain/redirect DENY） | PASS |
| 2 | 実行形プレフィックスマッチ（grill-code 🔴） | manifest_script_in | test_write_to_allowlisted_script_denied ほか（cp evil scripts/x.sh DENY・bare/`./` invocation ALLOW） | PASS |
| 3 | setup.sh .tsv 配布（F6 級） | bin/setup.sh | test_install_ships_scripts_manifest・test_installed_hook_allows_manifest_script | PASS |
| 4 | contract 3方向 drift 検査＋逆方向＋agents 走査 | scripts/check_framework_contract.py::check_scripts_manifest | test_scripts_manifest_contract（16件・幽霊 permission/agents/CRLF/whitespace/override 含む） | PASS |
| 5 | SCRIPT_CLASS を manifest 由来化 | tests/test_permission_allowlist_install.py | 既存17件 green（意味等価置換） | PASS |
| 6 | 安全 stderr リダイレクト正規化 | hooks/check-control-plane.sh | test_safe_stderr_redirect（2>/dev/null・2>&1 ALLOW／2>>・2>file・2>/dev/nullish・fd1・残存> DENY） | PASS |
| 7 | deny/ask メッセージ改善 | hooks/check-control-plane.sh | test_control_plane_messages（単体実行案内・正規手段・git add docs/ ヒント・誤診回避） | PASS |
| 8 | repo 直下 *.md prose allow＋symlink 除外 | hooks/check-gate.sh | test_gate_root_prose_md（Client/plan allow・CLAUDE.md/サブdir/コード DENY・symlink DENY） | PASS |
| 9 | client-workflow translation ref タイミング＋テンプレ対応表 | .claude/skills/client-workflow/SKILL.md | test_skill_guidance_tokens（token pin＋parity） | PASS |
| 10 | qa-browser 委譲粒度ガイド | .claude/skills/qa-verification/SKILL.md | test_skill_guidance_tokens（granularity token） | PASS |
| 11 | 版数 v1.16.0 | 4箇所 | test_cp_lock_contract・full suite | PASS |

実装漏れ（検証対象なし）: なし。全 plan Task に対応実装＋テストあり。

## テスト強度ドリル（B1）

- **SKIP 判定**（`docs/qa-reports/test-strength.drill` に skip:true）。framework イテレーションで全コード変更を
  per-task コミット済み＝qa 承認時の `git diff HEAD` が空＝mutant を置く未コミット追加行が無い縁ケース
  （qa-verification skill 記載の想定どおり・欠陥ではない）。
- **手動 mutation 同等の代替実証**:
  1. 全 Task を RED-first TDD（各テストが実装前に失敗することを確認してから実装）。
  2. grill-code で `manifest_script_in` の substring→prefix 変更を **`cp evil scripts/update-gate.sh` が
     allow→deny になる RED→GREEN** で実証（実際にバグを再現→修正を確認）。pin=test_write_to_allowlisted_script_denied。
  3. fail-closed（manifest 欠落＝全 deny）を test_missing_manifest_denies_everything で実証。
  4. stderr 正規化の回避形（2>>・2>file・チェーン後続）が deny を維持することを TestUnsafeRedirectsStayDenied で実証。
  5. CRLF/whitespace 非対称（bash silent deny）を contract が fail-visible にすることを実証。

## テスト実行

- full suite: `python3 -m pytest -q` = **1285 passed, 3 skipped**（record-test-result で権威記録）。
- `python3 scripts/check_framework_contract.py` = PASS／`check_status.py` = PASS／`check_reference_drift.py` = PASS。

## verdict

全 plan 機能に検証対象＋PASS。実装漏れなし。B1 は per-task コミットの縁ケースで SKIP＋手動 mutation 相当を
5点で代替実証（grill-code の 🔴 は実バグ再現→修正確認済み）。full suite 1285 passed。**PASS**。

```claims
verdict: pass
tests: verified
drill: skip
notes: "framework per-task コミットで B1 は想定 SKIP＝手動 mutation 相当（RED-first TDD＋grill-code の cp-write allow→deny 実バグ再現→修正＋fail-closed 実証）で代替。full suite 1285 passed・contract/status/drift 全 PASS。"
```

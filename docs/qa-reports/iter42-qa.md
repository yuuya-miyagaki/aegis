# iteration 42 G1-G3 — QA Report

- date: 2026-06-24
- task: framework / L
- test command: `python3 -m pytest -q`（record green）／`check_framework_contract.py`／`status_doctor.py`／`bash -n`

## 機能対照表

| # | 機能 | 検証方法 | 判定 |
|---|------|---------|------|
| G1 | dd/chmod -R/mkfs/shred/system-truncate を ask | check-destructive 実起動：危険 7 種で ask、benign（chmod 644/-v・>>・>/dev/null・2>/etc・cat）で allow | PASS |
| G3 deploy | deploy-gate が single-source 後も engage/allow 保存 | vercel deploy→engage・rg deploy→allow | PASS |
| G3 cron | cron-gate が G1 破壊パターン＋deploy を継承 | chmod -R prompt→ask・vercel deploy prompt→ask・benign→allow | PASS |
| G2 | git -C/--git-dir で対象 repo の staged .env を deny | -C/--git-dir=/--git-dir space/quoted -C/CWD 直/メッセージ内 -C の 6 形で検証 | PASS |
| infra | hook 新 lib 依存に test scratch 同期 | deploy-gate hook tests（TempProjectWithHooks）緑 | PASS |

実装漏れなし。

## テスト強度（mutation drill）

- **skip-drill**（`docs/qa-reports/test-strength.drill`）。理由: framework 混在 diff に B1 構造的不適用（LEARNINGS conf9）。
- **代替＝RED-first TDD**: G1/G2/G3 各テストを fix 無し（=mutant 相当）で赤化実測→実装で緑。grill-code 由来の 2 修正（fd-redirect 誤検知・quoted -C）も赤→緑を確認。

## エビデンス

- full suite: **1067 passed, 1 skipped**（record green・fingerprint bind 済）。
- contract（full）: PASS（v1.14.0 据置）。
- status_doctor: PASS（warning=3 ship 連続のみ・advisory）。
- bash -n: patterns.sh / check-destructive / check-deploy-gate / check-cron-gate / check-secrets PASS。

## 判定

**PASS。** ブロッカーなし。

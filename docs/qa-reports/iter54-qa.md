# iteration 54 — QA Report（ドッグフード前 Critical バッチ修正）

- date: 2026-07-02
- task: framework / L / v1.15.0
- 参照: docs/plans/2026-07-02-iter54-critical-batch-design.md

```claims
gate: qa
verdict: PASS
tests: green
suite: 1232 passed, 3 skipped
b1_drill: SKIP（framework混在の大型diff・代替実証あり）
```

## 機能対照表（欠陥 → 検証対象 → 検証方法 → 判定）

| # | 欠陥（グリル再現） | 検証対象 | 検証方法 | 判定 |
|---|-------------------|---------|---------|------|
| C-1 | ケース非依存FSで control-plane moat バイパス | check-control-plane.sh（fold＋高速ゲート fold） | test_case_insensitive_fs.py TestControlPlaneCaseFold(8)/ProbePath(2)/NonRegression(2) | PASS |
| C-1 | 同・edit ゲートバイパス | check-gate.sh（nocasematch＋ROOT-external fold） | 同 TestGateCaseFold(5) | PASS |
| C-1 | 同・secrets ガードバイパス | check-secrets.sh（無条件 fold・対称 strip） | 同 TestSecretsCaseFold(9) | PASS |
| C-1b | STATUS.MD の gate tamper 監査スキップ（grill-code 発見） | post-status-audit.sh（filter fold） | 同 TestStatusAuditCaseFold(4) | PASS |
| C-2 | 壊れ profile JSON / `'` 入りパスで fail-open install | bin/setup.sh（JSON検証＋argv化＋rc検査） | test_setup_failclosed.py（broken JSON 2・quote path 3） | PASS |
| C-3 | --force 無バックアップ上書き | bin/setup.sh（copy_file diff-gated .bak） | 同（force backup 4） | PASS |
| C-4 | 日本語ファイル名が judge/drill から silent 消失 | run-test-strength-drill.py（quotepath=off＋fail-closed） | test_drill_quotepath.py（6） | PASS |
| S-glob-1 | `rm -rf *` 警告漏れ | check-destructive.sh（set -f） | test_glob_expansion_hooks.py TestDestructive(3) | PASS |
| S-glob-2 | `[id]`/`[h]ooks` パス歪み | check-gate.sh normalize_target（set -f） | 同 TestGate(3) | PASS |

実装漏れなし（全欠陥に検証対象と RED-first テストが存在）。

## テストスイート実行

- コマンド: `python3 -m pytest tests/ -q`
- 結果: **1232 passed, 3 skipped**（3 skip は FS ケース依存の環境条件付きテスト）
- contract: `check_framework_contract.py` → PASS（FRAMEWORK_VERSION 1.15.0 同期・STATUS.template.md 一致）
- bash -n: 全 hook・bin/setup.sh 構文 PASS
- git mode-flip: なし

## テスト強度（B1 ドリル）— SKIP + 代替実証

自動ドリルは coverage floor（tracked 変更の全連続 run に mutant 必須）を満たせない。
本 diff は tracked 追加行の連続 run=**86 本** ≫ `MAX_MUTANTS=25`、かつコメント・argv 化
リファクタ・バージョン定数・REQUIRED 差分など behavior-catching mutant を置けないハンクが
多数。iter43（同・L・同 hook 群）と同一クラスにつき `.drill` に `{"skip":true,...}` を宣言。
代替実証:

### (1) RED-first TDD（全欠陥）
新規4テストファイル（test_case_insensitive_fs.py / test_setup_failclosed.py /
test_drill_quotepath.py / test_glob_expansion_hooks.py）を**実装前に作成し、RED（各欠陥で
fail）を確認 → 実装 → GREEN** のサイクルで進めた（会話ログに RED 実測: 31 failed → 実装後 全 pass）。

### (2) 核判定行への手動 mutation 実測
| mutant | 変異 | 対象テスト | 実測 |
|--------|------|-----------|------|
| M2b | check-secrets.sh `CMD_LC=$(...tr...)` → `CMD_LC="$CMD"`（fold 無効化） | TestSecretsCaseFold | CAUGHT ✅ |
| M3 | run-test-strength-drill.py `-c core.quotepath=off` 除去（tracked diff） | TestJapaneseTrackedDiff | CAUGHT ✅ |
| M4 | check-destructive.sh SAFE_TARGETS ループの `set -f` 除去 | TestDestructiveGlobExpansion | CAUGHT ✅ |
| M5 | check-gate.sh normalize_target の `set -f` 除去 | TestGateGlobExpansion | CAUGHT ✅ |
| M6 | post-status-audit.sh filter の `\|*status.md` 除去（fold 無効化） | TestStatusAuditCaseFold | CAUGHT ✅ |
| M1 | safety.sh プローブの `-ef` を常時真化 | TestProbeHelper | 当該 macOS では判別テスト（test_separate_uppercase_dir_not_misdetected）が `skipIf(CASE_INSENSITIVE_FS)` で skip されるため再現不能。`-ef` ガードは **case-sensitive Linux で実在の別 dir HOOKS/ を誤検知しない**ための判別で、その FS でのみ意味を持つ＝Linux では当該テストが走り捕捉する。macOS 側は `AEGIS_CASE_FOLD_FORCE=1` 経路で fold 挙動を決定論テスト済み。 |

全 mutant は適用→判定→revert 後に suite 緑復帰を実測。M1 の限界は「テスト穴」ではなく
FS 依存の構造的制約（当該機で case-sensitive を再現できない）で、Linux CI 相当で解消する。

## grill-code 由来の修正（QA 確認済）

- Critical（grill-code 自己グリル）: C-1b（post-status-audit.sh の filter が case-sensitive
  ＝macOS で STATUS.MD の gate tamper が監査ごとスキップ）。C-1 と同一クラスで追加検出し、
  probe 条件付き fold で修正・TestStatusAuditCaseFold(4) 追加。
- Should（同）: check-secrets.sh Check2（commit トリガ）の CMD_LC fold 漏れを修正・
  test_uppercase_git_commit_with_staged_pem_denied 追加。

## 判定

**PASS（B1 は SKIP + 代替実証）。** 全機能対照 PASS、実装漏れなし、退行なし
（既存 setup/secrets/gate/destructive/drill/judge 回帰スイート全緑）。
残留リスク: 大文字コマンド名（`CP`/`MV` が exec の FS lookup で解決する経路）は
write-indicator regex が小文字前提のまま（security レポートで受容理由を明記）。

# QA レポート

## 対象

- iter61: iter60 事故クラスの機械防御（destructive patterns 9エントリ拡張＋snapshot 退行ガード）
- 参照: docs/plans/2026-07-07-iter61-incident-class-machine-defense-plan.md（Rev.4）／docs/qa-reports/iter61-review.md

## 実施した確認

1. **RED-first 実証**: 新テスト追加時点で ask 側テストが FAIL（`git checkout docs/*` 等が現行 allow）・preservation テストが FAIL（snapshot 無条件再生成）→ 実装後 GREEN（TDD 履歴どおり）。
2. **B1 mutation drill（実 mutation・SKIP なし）**: 未コミット diff の全9ハンク（hooks 3ファイル＋tests 3ファイル）に behavioral mutant 各1体 → **DRILL PASS（9/9 caught）**。mutant 内訳: glob 文字クラス破壊／WARN 英語化／退行判定の述語すり替え／警告 init 汚染／ガード恒偽化／CONTEXT 合流削除／テストデータ良性化／配列長 pin ずらし／revert シミュレーション無効化。
3. **実フック起動での挙動確認**: 事故コマンド（`git checkout docs/*`・`git stash`・`git checkout HEAD -- docs/STATUS.md`・`git checkout *`）→ ask、良性高頻度形（`git checkout main`・redirect 付き・`-b`・`stash pop/list`・`restore --staged`）→ allow。
4. **full suite**: 1061 passed / 2 skipped（既知の環境条件 skip: case-sensitive FS・shellcheck 不在）・実行後 `git status` で tracked ツリー無変更。
5. **contract / drift**: `check_framework_contract.py` PASS・`check_reference_drift.py` PASS。
6. **復旧ループ E2E**（盲検2次の独立実証を採録): 正規 approve→reset→session-start＝無警告／raw revert→session-start＝snapshot 温存＋警告／snapshot 一致 Edit＝audit 通過／復旧後＝無警告。

## 実行コマンド

```
python3 -m pytest -q                       # 1061 passed, 2 skipped
python3 scripts/run-test-strength-drill.py --root . \
  --spec docs/qa-reports/test-strength.drill \
  --report docs/qa-reports/test-strength.md   # DRILL PASS 9/9
python3 scripts/check_framework_contract.py   # PASS
python3 scripts/check_reference_drift.py      # PASS
```

## 結果

- 全項目 PASS。誤爆（良性 ask 化）ゼロ・見逃しは plan の受容残余リストに全件文書化済み。

## ブラウザ QA（ui_surface: true の場合)

- 非該当（ui_surface: false・hooks/CLI のみ）。

## Blockers

- なし。

## Claims（judge が機械読取する）

```claims
verdict: approve
```

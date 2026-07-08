# QA 記録 — iter63（setup.sh self-heal unlock）

## 対象

- 変更: bin/setup.sh（selfheal_unlock_target／explain_unwritable_dst／copy_file・
  copy_file_force の explained abort）＋tests/test_setup_locked_target_upgrade.py（新規5テスト）
- 参照: plan=docs/plans/2026-07-07-iter63-setup-self-heal-plan.md／
  spec=docs/specs/2026-07-07-iter63-setup-self-heal-design.md／
  review=docs/qa-reports/iter63-review.md（1次 approve_with_notes＋盲検2次 approve_with_notes）

## B1 テスト強度ドリル（実 drill・skip なし）

- spec: docs/qa-reports/iter63-drill-spec.json（mutant 7・全5 hunk 被覆＋テスト側1）
- 機械 verdict: docs/qa-reports/iter63-drill-report.md — **PASS 7/7 caught・baseline green・survived []**
- test_command: `python3 -B -m pytest -p no:cacheprovider tests/test_setup_locked_target_upgrade.py -q`
  （`-B`＋cache 無効で iter62 の pyc ミラーキャッシュ汚染経路を構造的に回避）
- mutant 内訳: M1 帰属行の $why 削除（hunk1）／M2 copy_file cp 条件反転（hunk2）／
  M3 copy_file_force explain 削除（hunk3）／M4 verify ゲート反転（hunk4）／
  M5 env ゲート反転（hunk4）／M6 main 呼び出し no-op 化（hunk5）／
  M7 テスト assert 改変（新規テストファイル）
- **drill が実穴を検出→テスト強化の実績**: 初回 drill で M1 相当（$why 帰属行の削除）が
  生存 — T3/T4 の stderr assert が remedy 行の `cp-lock.sh` トークンで偽充足するため
  「帰属そのもの」が未 pin だった。T3/T4 に `is not writable`（帰属句）assert を追加して
  封鎖後、7/7 caught。（中間に mutant 設計不備1件: 変異行が `$why` を保持し意味変異に
  なっていなかった→変異文言を修正。経緯は本レポートに透明記録）

## full suite（drill 後再実走・record）

- `python3 scripts/record-test-result.py "python3 -m pytest -q"` → **recorded: green**
  （1076 passed / 2 skipped 相当・新規5テスト含む）
- drill 後再実走の理由: iter62 教訓（同長 mutant の pyc 汚染＝ソース無汚染のテスト改変
  経路）。本 iter は `-B`＋`no:cacheprovider` で当該経路自体を遮断済みだが規律として実施。

## 経路検証（レビュー2系で実証済み・qa で追認）

- locked upgrade self-heal: rc0・NOTE・stale hook 刷新・.bak 保全・unlock 残置（T1）
- fresh／marker∧未lock: NOTE 非出力（T2/T2b＝AND ゲート第2脚 pin）
- opt-out fail-closed: rc≠0＋帰属 stderr（T3）
- 非 aegis read-only dir 不介入: perms 0o555 不変（T4）
- 旧新 stdout パリティ（3 profile）0行差・minimal/full profile の locked upgrade も rc0
  （盲検2次 probe13/14）

## 判定

```claims
verdict: approve
notes: ["B1 実 drill 7/7 caught（初回生存1→テスト強化で封鎖＝drill の実効性実証）", "full suite recorded green（drill 後再実走）", "残余: AEGIS_SETUP_SELFHEAL は小文字 off のみ（doc は ship で反映）"]
```

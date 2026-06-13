# F4 修正計画: /recover の status_doctor.py 依存（採用: status_doctor を full に配布）

> 監査: `docs/functional-integrity-audit-report-2026-06-07.md` F4（P2）
> 種別: bugfix（framework・install 配送）
> 設計判断: grill-plan で (a)graceful vs (b)配布 を精査 → **(b) 採用**（ユーザー承認 2026-06-07）

## 問題（実証済）

`.claude/skills/session-recovery/SKILL.md` Step 1.5 が `python3 scripts/status_doctor.py --root .` を
無条件実行するが、status_doctor.py はどの profile も配布しない → full install で `/recover` がそこで止まる。

## 設計判断（採用: (b) status_doctor を full に配布）

grill-plan で前提を正した結果:
- status_doctor を呼ぶのは **session-recovery ただ1箇所**（全 surface grep 確認）。
- session-recovery は **full profile にのみ同梱**（minimal/standard には無い）。
- ∴ status_doctor の呼出は **full install でしか発生しない** → full に status_doctor を配布すれば
  **ガード不要でクリーンに解決**。((a) 不採用の元前提「minimal/standard 用ガードが要る」は事実誤認だった。)
- 北極星「harness＝決定論チェック / LLM＝判断」に照らし、status_doctor の健全性チェック（last_updated 鮮度・
  gate/ref 整合・second-opinion 有無）は **harness が担うべき決定論処理**。(a) の「LLM 手動目視」格下げより
  (b) が原則整合。retro 前例（便利レポート）は性質が違い束縛しない。

## 修正方針

### (A) status_doctor.py を full profile に追加
`templates/profiles/full.json` の `recommended` に `scripts/status_doctor.py` を追加（他 script と並ぶ）。
status_doctor は check_status を import するのみ＝full は check_status を配布するので scaffold で実行可能。

### (B) example mirror に status_doctor.py を追加（整合）
example/minimal-project は session-recovery skill を持ち（status_doctor を参照）、現状 status_doctor.py を
欠く＝同じ F4 break を内包。root の status_doctor.py を example/scripts へ **byte 一致**でコピー。
- `check_reference_drift.MIRROR_FILES` に `scripts/status_doctor.py` を追加（root↔example 同期強制）。
- `check_framework_contract.REQUIRED_EXAMPLE_FILES` に example/scripts/status_doctor.py を追加（存在強制）。

### (C) session-recovery skill は無編集
status_doctor が session-recovery 同梱先（full）に常在するため、Step 1.5 の無条件実行は**正しくなる**。
prose 編集・ガードは不要。

### (D) 回帰防止: scaffold smoke に status_doctor 実在＋実行検証
`eval_scaffold_smoke.py` の full 検証に、`scripts/status_doctor.py` が install され、
`python3 scripts/status_doctor.py --root .` が **import 失敗/未配置で落ちない**（status-doctor の正常出力を返す）
ことを assert。F6/F3 と同じ install 実行検証の哲学で、prose lint より堅牢。
- 判定: 実行が「No such file」「Traceback/ImportError」で死なないこと＝status-doctor の既知出力マーカーを含む
  こと（exit code は STATUS 内容次第で 0/非0 ありうるので、クラッシュ非死を主判定にする）。

## TDD 手順

1. **RED**: (D) を追加。現状 full scaffold に status_doctor.py が無く実行不能 → FAIL。
2. **GREEN**: (A)(B) を適用 → full scaffold に status_doctor 実在＋実行可能 → PASS。
3. mirror-identity・contract(full/standard)・全層 green を確認。

## 影響範囲・非影響

- 変更: `templates/profiles/full.json`／`examples/minimal-project/scripts/status_doctor.py`(新規・byte 一致)／
  `scripts/check_reference_drift.py`(MIRROR_FILES)／`scripts/check_framework_contract.py`(REQUIRED_EXAMPLE_FILES)／
  `scripts/eval_scaffold_smoke.py`(検証追加)。
- session-recovery SKILL.md は**無編集**（mirror も無影響）。
- version: 版締めまで保留。

## 完了条件

- (D) が RED→GREEN。contract(full/standard)・drift(mirror-identity 含む)・全層 green。
- 実 full install で status_doctor.py 実在＋`--root .` 実行が正常出力を返すことを手動確認。
- grill-code 通過。

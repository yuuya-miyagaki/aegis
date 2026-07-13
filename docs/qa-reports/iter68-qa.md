# QA レポート — iter68 update-gate `approve --ref` 原子化＋SIGPIPE 耐性＋advisory 降格
<!-- 正本: qa agent -->

## 対象

- 変更内容: git 範囲 `8ab52ed..9970cdf`（scripts/update-gate.sh・scripts/check_status.py・scripts/build-judge-card.py・tests 3ファイル・guidance 11ファイル）。review 承認済み（docs/qa-reports/iter68-review.md・盲検2次収束 approve_with_notes）。
- 環境: macOS（bash 3.2.57）・python3・本体リポジトリ＋独立 scratch clone（HEAD=9970cdf 一致）

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|
| 1 | `approve --ref` 原子書込み（gate+ref 1書込み・窓なし） | update-gate.sh 書込みブロック | テスト（atomic 2本）＋変異 M1/M2＋実環境 E2E | PASS |
| 2 | --ref 入力検証（不在/絶対/../allowlist/refless gate/na・reset/空文字/key 行欠損） | 同 検証ブロック | テスト 8本（全て rc≠0・STATUS byte 不変） | PASS |
| 3 | SIGPIPE 耐性（書込みが承認主張出力に先行・closed pipe で完遂） | trap＋print_report 構造 | closed-pipe E2E＋構造ピン＋変異 M3 | PASS |
| 4 | 書込み失敗 fail-closed（偽成功出力の封鎖・review 4-A） | 明示 if 書込み | chmod555 回帰テスト＋変異 M4 | PASS |
| 5 | pending/n/a+ref の advisory 降格（stderr・stdout=violation チャネル維持） | check_status.py 共有関数 | ストリーム分離テスト＋変異 M5 | PASS |
| 6 | ADVISORY 抑止＋judge の AEGIS_PENDING_REF 読取 | check_status.py／build-judge-card.py | env テスト2本＋変異 M6＋実環境 E2E | PASS |
| 7 | na の ref null 化・reset/lock/--ack/card push 非退行 | update-gate.sh | 既存＋新規テスト（na null 化・--ref×--ack 併用） | PASS |
| 8 | guidance 同期（--ref 正順・旧手順残骸ゼロ） | gate.md/CLAUDE.md/skills/onboarding | review 1次＋盲検2次が独立確認・grep 掃討 | PASS |

## 実施した確認

- [x] fresh 変異 M1-M6（独立 scratch clone・1変異ずつ適用→scoped 実行→revert）: **全 KILLED**。baseline 213 passed（clean run 証明・本体 tree 不接触・HEAD 不変）
- [x] full suite: **1173 passed / 2 skipped / 0 failed**（record green は 57fbedf 直後・以降のコミットは docs のみ＝fp 不変で有効）
- [x] contract: `check_framework_contract.py` → PASS
- [x] 実環境 E2E（本 iter 機能の実運用）: review gate を `approve --ref docs/qa-reports/iter68-review.md` で承認 — {操作: 原子承認コマンド1発, 期待: gate=approved と ref が同時確定・judge が pending ref から claims を読み ack 不要, 実測: STATUS で `review: approved`＋`review: "docs/qa-reports/iter68-review.md"` 同時成立・judge card 表示・rc=0}
- [x] B1 drill: skip 宣言（per-task committed の sanctioned 縁ケース・代替実証 6 系列を .drill に明記）
- [x] plan の受入条件6項目と突合（review レポート項目4＝全充足・full suite 実行は本フェーズで fresh 確認）

## 実行コマンド

```bash
# fresh 変異（scratch clone 内・各変異で scoped pytest → revert）
python3 -m pytest tests/test_update_gate_ref_atomic.py -q  # M1-M4
python3 -m pytest tests/test_check_status.py -k "pending_gate_with_ref or na_gate_with_ref or advisory_goes_to_stderr" -q  # M5
python3 -m pytest tests/test_judge_card.py::TestResolveReport -q  # M6
# 本体
python3 -m pytest tests/ -q                       # 1173 passed, 2 skipped
python3 scripts/check_framework_contract.py        # PASS
bash scripts/update-gate.sh review approve --ref docs/qa-reports/iter68-review.md  # 実環境 E2E
```

## 結果

- Pass: 機能対照表 8/8・変異 6/6 KILLED・full suite 1173 passed・contract PASS・実環境 E2E 成功
- Fail: なし
- Skip: full suite 内 2 skipped（既存・本 diff 無関係）。B1 drill=skip 宣言（代替実証付き）

## Blockers

- なし。繰延（非ブロッキング・review レポートに理由記録済み）: client_ready_for_dev の --ref 実行経路テスト（iter69/70）・--ref symlink 越境（4-B Minor）・SF-013（sed 範囲終端の hardening・security フェーズで起票）

## Claims（judge が機械読取する）

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: []
  evidence: "qa 一次=fresh clone 変異 M1-M6 全 KILLED（qa agent・opus・独立実測）＋親検証（fable）＝F-1 レース 58/3000→0/3000 の単離実測・実環境 E2E（review gate 原子承認の実運用成功）。review フェーズの盲検2次（fresh fable・reject→fix→approve_with_notes 収束）と合わせ、独立検証 3 系列が同一結論。"
```

<!-- exit-check: 全チェック実施・結果記入済み → security へ -->

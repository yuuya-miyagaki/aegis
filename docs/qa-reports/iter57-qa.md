# QA レポート（iter57）
<!-- 正本: qa agent -->

> QA agent が実行した確認と証拠を要約する。VERIFICATION は自己検証用であり、
> 本レポートとは別物。

## 対象

- 変更内容: iter57 主 moat 交代（OS-lock 昇格・check-control-plane.sh 979行 退役・
  残余ガード check-runtime-state.sh／EACCES advisory explain-oslock-eacces.sh 新設・
  aegis_cp_verify 全数照合追加）＋review fix-forward。仕様= docs/specs/2026-07-05-iter57-oslock-promotion-design.md
- 環境: macOS（darwin）・Python 3 stdlib・bash 3.2（macOS 既定）・pytest

## 機能対照表（plan 機能 × 検証）

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | OS-lock による形非依存の物理阻止（主 moat） | cp-lock.sh・sf_catalog | lock 下で難読化形（cmdsub/backtick/glob/case-fold/subshell/python3 -c/find -exec/touch/rename）実走→EACCES＋INTACT | ✅ PASS |
| 2 | half-locked の可視化（全数照合） | aegis_cp_verify | 人工 half-locked を作り検出・framework/非framework 反転・symlink 非誤検知 | ✅ PASS |
| 3 | session-start の fail-visible 化 | session-start.sh | verify 不一致で強警告＋是正手順・Windows 分岐で no-op スパム防止 | ✅ PASS |
| 4 | runtime-state 書込みの静的 deny（残余） | check-runtime-state.sh | deny/allow/ask/fail-closed 全分岐 35 テスト | ✅ PASS |
| 5 | unlock 形 deny・broad chmod ask | check-runtime-state.sh | chmod/chflags/chattr×CP=deny・chmod -R .=ask・非 CP chmod=allow | ✅ PASS |
| 6 | manifest allowlist 継承（全数） | check-runtime-state.sh | allow\|ask 全12本の runtime-state 文脈 ALLOW＋framework-only 全数 DENY | ✅ PASS |
| 7 | EACCES advisory（純 advisory） | explain-oslock-eacces.sh | EACCES×CP 共起で発火・非該当で沈黙・壊れ JSON で fail-open | ✅ PASS |
| 8 | 退役の空白なし・置換マッピング | test 群 | コード/テンプレ/live 参照 0件・1対1 置換・受け皿全緑 | ✅ PASS |
| 9 | install 契約（配線交換・prune） | setup.sh・scaffold smoke | 退役 hook prune・新配線・OS-lock apply+verify（deploy で実走） | ✅ PASS（本体）／deploy で再確認 |

## 実施した確認

- [x] full suite 実行（**1045 passed / 2 skipped**・record-test-result 経由で green 記録）
- [x] 決定論検査一式（check_framework_contract / check_reference_drift / context_budget /
      status_doctor）すべて PASS
- [x] 実地スモーク（POC ハーネス）: `bash tests/poc/v162-redteam-rerun.sh` → **18/18 passed**
      （REDTEAM-02/02b の難読化形が OS-lock で阻止・ファイル INTACT／F-01 lib 欠落 fail-closed deny）
- [x] check-runtime-state 実挙動: manifest allow|ask 全数の ALLOW・framework-only の DENY・
      unlock 形 deny・broad chmod ask を hook 実入力で確認（test_runtime_state_hook.py）
- [x] aegis_cp_verify 実挙動: half-locked（ネスト残 writable）検出・空 root fail を実証
- [x] test-strength ドリル: skip 宣言（working-tree diff 空・RED-first 代替実証を .drill に明記）

## 実行コマンド

```bash
python3 scripts/record-test-result.py "python3 -m pytest -q"  # recorded: green（1045 passed / 2 skipped）
python3 scripts/check_framework_contract.py                   # PASS: aegis contract is aligned
python3 scripts/check_reference_drift.py                      # PASS: no reference drift detected
python3 scripts/context_budget.py check                       # exit 0
python3 scripts/status_doctor.py --root .                     # PASS
bash tests/poc/v162-redteam-rerun.sh                          # 18/18 passed
```

## 結果

- Pass: full suite 1045（iter57 新規/改修テスト＝test_runtime_state_hook 35・test_cp_lock_verify 6・
  test_explain_oslock_eacces 7・test_cp_lock_sf_catalog 拡張・test_session_start_cp_lock 追加・
  退役群の 1対1 置換ほか）
- Fail: 0
- Skip: 2（既存・環境依存の意図的 skip。root euid スキップ含む）

## ブラウザ QA（ui_surface: true の場合）

- 対象外（ui_surface: false・framework 内部変更のみ）

## Blockers

- なし

## 残余リスク（脅威モデル内・記録のみ）

- 敵対的 os.chmod による解錠は従来どおり脅威モデル外（事故防止が目的・sandbox 化しない）。
- `mv hooks hooks_bak`（root 非 lock ゆえ rename 成功しうる）は rev.2 既定の accepted residual・
  hooks/ 内ファイルは INTACT。Windows ネイティブは OS-lock 無効（公式サポート外・毎セッション明示）。

## Claims（judge が機械読取する）

```claims
verdict: approve
tests_green: true
```

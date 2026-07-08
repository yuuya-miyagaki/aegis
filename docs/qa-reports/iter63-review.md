# レビュー記録
<!-- 正本: reviewer agent -->

## 対象

- 変更内容: iter63 — setup.sh self-heal unlock（全体レビュー R3・v1.24.0 予定）。OS-lock 済み install への正規 upgrade（`Re-run bin/setup.sh`）が `cp: Permission denied` で即死する問題を、(1) main 冒頭の `selfheal_unlock_target()`（marker ∧ verify findings の AND 発火・再 lock は次回 session-start 任せ・`AEGIS_SETUP_SELFHEAL=off` seam）、(2) `explain_unwritable_dst()`（最近傍実在祖先の遡り帰属）、(3) `copy_file`/`copy_file_force` の mkdir/cp を説明つき abort 化、で解消。
- 対象ファイル: bin/setup.sh（+84/-4）・tests/test_setup_locked_target_upgrade.py（新規・4テスト）
- 参照: docs/specs/2026-07-07-iter63-setup-self-heal-design.md／docs/plans/2026-07-07-iter63-setup-self-heal-plan.md（grill-plan 致命3＋要検討1反映済）／hooks/lib/cp-lock.sh（unlock 正本・無改変）
- レビュー方式: 7項目 numbered batch・全項目 実コマンド検証（read-only・repo ツリー不接触の scratchpad ハーネスで機能検証）。bash は /bin/bash＝PATH bash とも 3.2.57（実環境で 3.2 検証済み）。
- レビュー開始時点の未コミット作業（前提として容認・不変で維持）:
  `M bin/setup.sh` / `M docs/STATUS.md` / `?? docs/plans/2026-07-07-iter63-setup-self-heal-plan.md` / `?? docs/specs/2026-07-07-iter63-setup-self-heal-design.md` / `?? tests/test_setup_locked_target_upgrade.py`

## 対照表（plan タスク → 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | 回帰テスト新設（T1-T4・RED 先行） | tests/test_setup_locked_target_upgrade.py | 完了 | plan 確定コードと一致（docstring に日付追記のみ）。4/4 PASS 実測 |
| 2 | selfheal 関数＋main 呼び出し | bin/setup.sh L624-661・L674-676 | 完了 | plan 確定コード逐語。配置=INSTALLED_PATHS 前・Required files 前 |
| 3 | 帰属エラー（explainer＋copy 経路置換） | bin/setup.sh L148-175・L225-234・L261-270 | 完了 | 致命1（祖先遡り）反映済。メッセージに「(or the heal itself failed above)」を追加（plan 文言＋α・後述 Info-1） |
| 4 | GREEN→setup 系→full | — | 部分 | 新テスト 4 PASS・`bash -n` OK・setup 系 8 ファイル 60 PASS を本レビューで実走。full suite は qa フェーズ（B1 drill 後再実走）にて |
| ship | bump 3箇所（致命3） | — | 未（正） | ship フェーズ担当。FRAMEWORK_VERSION=1.23.0 のまま＝diff 混入なしを確認 |

## 検証項目別エビデンス（7項目・action/expected/observed/verdict）

1. **selfheal_unlock_target 正しさ** — action: 関数読解＋S2〜S5 実走（scratchpad target）。expected: set -e 安全・AND ゲート・bash3.2 互換。observed: `local locked` 宣言分離＋`|| true` 受け（rc マスクなし）・`if aegis_cp_unlock`（if 条件は set -e 免除）・全 return 経路 rc0。ゲート実証: 引数不正→heal 前 abort（S2: rc=1・hooks locked のまま）／findings ゼロ→無言（heal 済み target への3回目 install: NOTE なし）／部分 lock→検出・治癒（S5）／大文字 `OFF` は無効化しない＝lowercase-only 慣習どおり（S4）。cp-lock.sh はトップレベル副作用ゼロ（関数定義のみ）＝関数内 source 安全。連想配列・`${var,,}` 不使用、テストは bash 3.2.57 実機で green。verdict: **PASS**（Minor-1 は後述）
2. **explain_unwritable_dst** — action: 関数を sed 逐語抽出し bash 3.2 で6ケース実走。expected: 停止性＋正帰属＋誤帰属なし。observed: (a) locked 既存ファイル→「is not writable」（S1a）／(b) 既存 read-only dir への新規→「directory … is not writable」（S1b）／(c) 深い mkdir -p 失敗→最近傍実在祖先に帰属（S1c: `hooks/lib/emit.sh` 失敗→`hooks` に帰属）／無関係失敗（writable dst／dst=writable ディレクトリ）→ generic ERROR のみ・cp-lock 行なし（S1d/S1e）／相対 path→停止（S1f）。verdict: **PASS**
3. **copy_file/copy_file_force 編集** — action: `git diff bin/setup.sh` 精査＋消費側テスト実走。expected: 成功経路 byte 同一・失敗 rc 同一。observed: diff は mkdir/cp の if 化のみ（SKIP/OVERWRITE/COPY 文言・`.bak` 意味論〔copy_file=abort-on-bak-fail 不変／force=best-effort `|| true` 不変〕・`INSTALLED_PATHS+=`→echo の順序すべて無変更）。旧 set -e 死の rc=cp/mkdir の 1＝新 `exit 1` と同値。upgrade-overwrite テストは効果ベース断言（内容一致・.bak glob）で 60 PASS。verdict: **PASS**
4. **main 配置** — action: 行番号照合＋S2 実走。expected: 検証系ガード後・全 copy 前。observed: 呼び出し=L676。引数解析 L50-71・profile 検証 L73-112・TARGET 正規化 L114-117・DIST-12 guard L119-128 の後、`--- Required files ---`（L683）・copy_hooks・generate_settings の前。invalid profile＋locked target → rc=1・unlock 不発を実測（S2）。target=framework root は L124-128 で heal 到達前に abort（読解）。verdict: **PASS**
5. **テスト品質** — action: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_setup_locked_target_upgrade.py -v`。expected: 仕様 pin＋hermetic。observed: **4 passed (3.93s)**。pin 網羅: rc／NOTE token（`OS-locked`・`next session start`＝再 lock 先送り）／治癒効果（hook 内容=ソース一致・`.bak` glob）／target が unlock のまま（W_OK）／off seam の帰属 token（`cp-lock`・`AEGIS_SETUP_SELFHEAL`・rc≠0・lock 不変）／非 aegis dir perms byte 不変（`stat.S_IMODE == 0o555`）。hermetic: `_run` で `env.pop("AEGIS_SETUP_SELFHEAL")`。ROOTUSER skipif は lock 依存の T1/T3/T4 のみ（T2 は正しく非 skip）＝repo 慣習（test_cp_lock_lib.py）どおり。teardown は finally で `chmod -R u+w`。verdict: **PASS**（Info-3 の pin 欠落は非ブロッキング）
6. **spec/plan 準拠** — action: 設計書 推奨アプローチ 1-4・plan 確定コード・grill-plan 簿記と diff の突合。observed: (1) self-heal AND 発火＋NOTE ✓／(2) 再 lock なし（NOTE で明示）✓／(3) 帰属エラー ✓／(4) off seam（既定 on・lowercase のみ）✓。簿記: 致命1 祖先遡り ✓（S1c 実証）・致命2 ROOTUSER skipif ✓・致命3 bump は ship 担当＝diff 非混入 ✓（FRAMEWORK_VERSION=1.23.0 確認）・要検討1 env pop ✓。未宣言差分: エラー文の「(or the heal itself failed above)」追加（Info-1）・docstring 日付・コメント位置のみ＝機能追加なし。STATUS.md の diff は iteration 63 rollover 簿記（gate reset・refs 差し替え）で正当。verdict: **PASS**
7. **横断影響** — action: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_setup_upgrade_overwrite.py tests/test_setup_distribution.py tests/test_setup_failclosed.py tests/test_setup_baseline.py tests/test_setup_prereq.py tests/test_setup_arg_version.py tests/test_setup_broken_settings.py tests/test_permission_allowlist_install.py -q`＋stdout 断言 grep。observed: **60 passed (45.73s)**。setup stdout の完全一致断言は存在せず（`Setup complete.` は failclosed の否定断言のみ＝NOTE 非干渉。upgrade 系は効果ベース断言）。docs/README に setup 出力の transcript 依存なし（`OS-locked` 言及ゼロ）。verdict: **PASS**

## Stage 1: 仕様準拠

- [x] 計画の全要件が実装されている（推奨アプローチ 1-4・grill-plan 致命1/2＋要検討1。致命3=bump は ship 担当で正しく未着手）
- [x] スコープ外の機能が追加されていない（diff 5 hunks すべて宣言済みユニット。唯一の文言差は Info-1）
- [x] 実装の欠落がない（unlock は cp-lock.sh 正本を source＝第2実装なし。非 aegis dir 不介入は marker ゲート＋T4 で機械 pin）

**Stage 1 判定:** PASS

## Stage 2: コード品質

- [x] set -euo pipefail 下の安全性（`|| true` 受け・if 条件・宣言/代入分離・全経路 rc0 — 実走で確認）
- [x] bash 3.2 互換（/bin/bash 3.2.57 で構文 OK＋全テスト green。連想配列・小文字化展開なし）
- [x] エラーハンドリング（帰属は証拠がある時のみ・generic fallback で誤帰属なし〔S1d/S1e〕・cp 生 stderr は温存）
- [x] テスト品質（仕様 pin 網羅・hermetic・root skip・teardown 復旧。上記項目5）

**Stage 2 判定:** PASS

## Findings（severity / confidence）

- **Minor-1 / confidence 9（実証済み・spec 準拠内の意味論限界・変更不要だが記録）**: 発火ゲート(b)の `aegis_cp_verify` findings は「cp-lock による lock」ではなく「CP path 内の任意の非書込可ファイル」を検出する proxy。cp-lock 以外の理由で 1 ファイルでも非書込可だと、NOTE が「target was OS-locked」と断定表示し perms を u+w に正規化する（本環境で実再現: 下記 Minor-2 起因で、未 lock target への再 install が NOTE を出した→治癒後の3回目 install は無言）。治癒方向は安全側・非 aegis dir は marker ゲートで保護済み・設計書も「部分 lock も治癒」を明示するため仕様内。NOTE 文言を「OS-locked (or partially non-writable)」程度に弱める改善は任意（ship 前でも backlog でも可）。
- **Minor-2 / confidence 10（環境問題・diff 外・要対処）**: framework repo 作業コピーの `scripts/check_status.py` が `-r--r--r--`（git 上は 100644＝clean clone では書込可）。この作業コピーから install すると cp が mode を継承し、**全 install が read-only の check_status.py を同梱→以後の再 install every-time で self-heal NOTE が発火**する（Minor-1 の実トリガー・フレッシュ install の verify rc=1 を実測）。reviewer は read-only 拘束のため未修正。implementer が `chmod u+w scripts/check_status.py` で復旧すべき（tree の git 差分は生じない）。qa の B1 drill 前に直さないと drill ログにノイズが乗る。
- **Info-1 / confidence 10**: explain メッセージが plan 確定文言に「(or the heal itself failed above);」を追加。unlock 部分失敗→WARNING 続行→copy 失敗の経路を正しくカバーする改善で追認妥当（docs で追認推奨）。
- **Info-2 / confidence 9（残余・backlog 候補）**: copy_hooks L524 の `rm -f check-control-plane.sh` は説明つき abort の被覆外。`SELFHEAL=off ∧ locked ∧ 配布物全同一 ∧ 退役 hook 残存`の四重条件でのみ素の set -e 死が残る（heal on 経路は事前 unlock で到達不能）。設計スコープ（死に方1-3=cp/mkdir/.bak）外のため非ブロッキング・Phase 1 バックログへ。
- **Info-3 / confidence 8**: 「marker あり ∧ 未 lock → 無言」の pin テストが不在（T2 は marker なしのみ）。追加する価値はあるが、**Minor-2 を直すまで本作業コピーでは恒常 RED になる**ため、順序は Minor-2 修正→pin 追加。

## 残留リスク

- unlock 窓（upgrade 完了〜次回 session-start）: 設計書どおり受容（layer-2 の脅威モデルは偶発書込み防御・NOTE で可視）。
- agent が framework clone の setup.sh を意図実行して moat を外す経路: 設計書 §セキュリティで受容済み（owner chmod と等価）。security ゲートで明記予定どおり。
- 将来 `aegis_cp_paths` 集合が狭まった場合の取りこぼし: 帰属エラーが安全網（plan リスク節どおり）。

## 総合判定

- 判定: **approve_with_notes**
- notes の中身: Minor-2（環境・repo の check_status.py 444 復旧＝implementer 作業）を qa/B1 drill 前に解消すること。Minor-1/Info-1〜3 は記録・任意改善。
- 次のアクション: Minor-2 解消 → 盲検2次 → qa（B1 実 drill・drill 後 full suite 再実走→record〔pyc 教訓〕） → security → ship（v1.24.0・bump3箇所） → docs（M=deploy skip）

## Claims（judge が機械読取する）

```claims
verdict: approve_with_notes
notes: ["Minor-1: verify-findings proxy により非 cp-lock 起因の非書込可ファイルでも NOTE が『OS-locked』と断定（実再現・治癒方向は安全側・仕様内）", "Minor-2: 作業コピーの scripts/check_status.py が 444（diff 外の環境問題）→ install 同梱で再 install every-time NOTE 発火。qa 前に chmod u+w 要", "Info-1: explain 文言の plan 差分（heal 失敗経路の言及追加）は追認妥当", "Info-2: copy_hooks の rm -f 経路は帰属被覆外（四重条件・backlog）", "Info-3: marker∧未lock→無言 の pin 不在（Minor-2 修正後に追加推奨）"]
```

## tree-clean 証跡（git status --porcelain・レビュー完了時点）

```
 M bin/setup.sh
 M docs/STATUS.md
?? docs/plans/2026-07-07-iter63-setup-self-heal-plan.md
?? docs/qa-reports/iter63-review.md
?? docs/specs/2026-07-07-iter63-setup-self-heal-design.md
?? tests/test_setup_locked_target_upgrade.py
```

開始時点との差分は本レポート（`?? docs/qa-reports/iter63-review.md`）のみ。既存ファイル無変更・git 破壊操作なし・pytest は `PYTHONDONTWRITEBYTECODE=1`＋`-p no:cacheprovider` で cache 書込なし。

<!-- exit-check: Stage 1/2 判定・findings 対応方針記載済み → 盲検2次/qa へ -->

## fix-forward 反映（親セッション・2026-07-07）

- **Minor-2 対応済み**: `chmod u+w scripts/check_status.py`（444→644）。CP 全パスの
  `find ! -perm -u+w` 再走査で他の read-only 残骸ゼロを確認。
- **Info-3 対応済み**: `test_aegis_install_unlocked_stays_silent` 追加（marker∧未lock→
  無言の pin＝AND ゲート第2脚＋配布源 read-only 汚染の canary）。Minor-2 修正後で
  GREEN（5 passed）。
- **Minor-1**: residual 受容（文言 hedge は任意・治癒方向は安全側）。
- **Info-2**: backlog 起票（四重条件コーナー・別 iter）。

## 盲検2次レビュー記録（2026-07-07・独立ディスパッチ・1次レポート未読）

- **判定: approve_with_notes**（Major 0・ブロッカーなし）
- 敵対プローブ: スペース/アポストロフィ入り target・半 lock・marker 有 hooks 消失・
  minimal/full 両 profile・偽 marker＋外部 symlink victim・DIST-12 symlink 迂回試行 —
  すべて破壊できず（TARGET 外/CP 集合外への chmod ゼロを実証）。
- 旧新パリティ: HEAD 版 setup.sh との fresh install 3 profile stdout diff 0行・
  full suite 1076 passed/2 skipped。
- mutant シミュレーション 5/5 catch。**M6（verify ゲート削除）は追加テスト
  `test_aegis_install_unlocked_stays_silent` だけが捕捉**＝plan 原案4本の穴を Info-3
  fix-forward が正確に塞いだことを独立確認（Info-5/確度10）。
- Minor-1（確度6・注記）: `AEGIS_SETUP_SELFHEAL` は小文字 `off` のみ有効（`OFF`/`0`/
  `false` は黙って heal）。AEGIS_NUDGE 同慣習だが、opt-out seam としては doc に一行
  推奨 → **ship フェーズで TO-CLIENT/README に反映予定**。
- Info-1（到達不能エッジ・`/` 遡り誤帰属）・Info-2（偽 marker は verify＋path 集合＋
  symlink 除外で封殺済）・Info-3/4（既存挙動・scope 外）= residual 受容。
- tree-clean: porcelain 開始時と同一集合・プローブ成果物は scratchpad のみ。

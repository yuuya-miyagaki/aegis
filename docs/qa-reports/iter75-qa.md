# iter75 SF-017 MOAT-BYPASS 修正 — QA レポート

## 総合判定: **PASS**

## 対象
commit `5398e72..402fdd9`（初回実装 Task1-7 ＋ fix-forward FF1-8）。moat フック（check-destructive.sh/check-secrets.sh）＋共有 helper（patterns.sh）＋tests。

## 機能対照表

| # | plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|-----------|---------|---------|------|
| 1 | quote/BS 難読化を正規化して ASK | `aegis_dequote_normalize`＋両フック正規化 re-check | `r""m -rf`/`g""it a""dd .e""nv`→ask 実測 | PASS |
| 2 | `${IFS}`/`$IFS` 分割の畳み込み | helper `${IFS}`/`$IFS`→空白 | `rm${IFS}-rf`/`git${IFS}add .env`→ask 実測 | PASS |
| 3 | backslash-newline 行継続 | helper `\<改行>` 除去＋残改行→空白 | `git add \<改行>.env`/`rm \<改行>-rf`→ask 実測 | PASS |
| 4 | broad-stage 難読化（実 .env 存在時 ASK） | check-secrets 二経路トリガ＋FS スキャン再利用 | `git${IFS}add -A`(実 .env)→ask・生→deny・.env 不在→allow 実測 | PASS |
| 5 | commit 難読化（.env staged 時 ASK） | check-secrets commit 二経路＋staged スキャン | `git${IFS}commit`(staged .env)→ask・`git commit -m "msg"`(非staged)→allow 実測 | PASS |
| 6 | 難読化大文字クラス全体 | check-destructive 正規化経路 grep -i | 全 CMD_REGEX（rm/chmod/find/dd/shred/mkfs/git 系）大文字難読化→ask 実測 | PASS |
| 7 | 生形評決不変（回帰保存） | raw 経路 | 生 `rm -rf`→ask・`git add .env`→deny・誤検知なし | PASS |
| 8 | 残余の分離起票 | SF-019/020/021 | brace/param/cmdsub・raw 大文字・git stage が OPEN 起票・test_residual pin | PASS |

「検証対象が存在しない（実装漏れ）」項目なし。

## テストスイート
- `python3 -m pytest`（フルスイート）→ **1341 passed, 2 skipped, 0 failed**（record green・marker:true）
- `tests/test_moat_quote_split.py` 43 ケース（バイパス 6＋回帰 6＋残余 pin 2＋ff 17＋midword 1＋pin 強化）全 GREEN
- `python3 scripts/check_framework_contract.py` → PASS
- `python3 scripts/status_doctor.py --root .` → PASS
- lint/type-check: 該当なし（bash フック・`bash -n` 構文チェック両フック PASS）

## テスト強度ドリル（mutation drill）
**skip 宣言**（`docs/qa-reports/test-strength.drill`）: framework per-task-commit ゆえ qa 承認時の working-tree diff（`git diff HEAD`）が空＝想定どおりの縁ケース（qa-verification skill 147-150）。**代替実証**（手動 mutation 同等）:
- **RED-first TDD**: 各 FF タスクが RED commit（初回 5398e72 で 6 バイパス・FF1 292f4a9 で非rm 大文字含む 7 バイパスが現状 allow を実測してから GREEN 化）。
- **review reviewer-testing の mutation 実測**（scratchpad コピー・本体 tree 不接触・全 killed）: [MA] helper backslash-newline 除去→parity RED／[MB] BROAD_NORM 無効化→F1 broad RED／[MC] :149 NORM 戻し→F3 rm RED／[MD] broad/commit 一律 DENY→誤検知回帰 pin RED／[FF7-mut] :161 grep -i→grep→非rm 大文字 10件 RED。**RED 真正性**: FF7 前 5f03ac0 で非rm 大文字 10件 FAIL を実測。
- **review 3体独立実測**: 1次=CMD_REGEX 全19＋LOWER＋rm／盲検2次=24 パターン＋新軸攻撃（新穴なし）／testing=mutation 10/10 RED・網羅性。

## エビデンス収集チェックリスト
- [x] テストスイート実行・記録（1341 passed・record green）
- [x] `bash -n` 構文チェック（両フック PASS）
- [x] plan 受入条件と突合（判定表 8 項目）
- [x] 各項目に PASS/FAIL 判定
- [x] FAIL 項目なし（ブロッカーなし）

## 残余（既知 OPEN・iter76+）
SF-019（brace/param/cmdsub・Medium）・SF-020（raw 大文字コマンド名＋redirect システムパス・High・iter76 P0 推奨）・SF-021（git stage エイリアス broad 漏れ・High）。いずれも `NORM==CMD` or 静的正規化の射程外で iter75 スコープ外・doc に分離起票済み。

## ブロッカー
なし。

```claims
verdict: approve
tests_pass: true
no_stubs: true
qa_drill: skip (per-task-commit・代替実証は review mutation 10/10 killed＋RED-first TDD)
```

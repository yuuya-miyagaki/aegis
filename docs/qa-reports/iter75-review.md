# iter75 SF-017 MOAT-BYPASS 修正 — review レポート

## 総合判定: **PASS（approve）**

moat 変更ゆえ 2 段グリル（grill-plan/grill-code）＋3体レビュー（1次 opus・盲検2次 fable 独立・reviewer-testing）を実施。review を2回 reject → fix-forward で全穴封鎖 → 再々走で 1次 approve・盲検2次 approve・testing PASS。

## 対象
commit `5398e72..402fdd9`（初回実装 Task1-7 ＋ fix-forward FF1-8）。
- `hooks/lib/patterns.sh`: `aegis_dequote_normalize`（quote/backslash/backslash-newline/`${IFS}`/`$IFS`/残改行・純 bash param 展開）
- `hooks/check-destructive.sh`: 正規化 re-check（全 grep を `grep -i` on NORM）
- `hooks/check-secrets.sh`: staging 検出の単一ソース化・broad/commit 二経路トリガ（raw=deny/norm=ask）・正規化 re-check
- `tests/test_moat_quote_split.py`（43 ケース）・`tests/test_patterns_parity.py`

## 対照表（Task → 実装 → 状態）

| Task | 内容 | commit | 状態 |
|------|------|--------|------|
| 1-5 | 初回実装（RED→helper→destructive→secrets→回帰 pin） | 5398e72..60bd9cb | ✅（各 Stage1 approve） |
| 6-7 | フル green＋docs＋SF-019 起票 | 826f275,66c4d09 | ✅ |
| (grill) | SF-020 起票（大文字 case-fold） | ffb1108 | ✅ |
| FF1-6 | review reject #1 対応（broad/commit 難読化・backslash-newline・難読化大文字 rm・pin 強化） | 292f4a9..6edfbd0 | ✅ |
| (grill) | SF-021 起票（git stage エイリアス） | d0753e2 | ✅ |
| FF7 | review reject #2 対応（難読化大文字クラス全体を grep -i 封鎖） | 9c3d7ea,2d06526 | ✅ |
| FF8 | testing F1 補強＋SF-020 に redirect 大文字追記 | 402fdd9 | ✅ |

## レビュー経緯（独立盲検2次の価値）

- **review reject #1**（初回実装）: 盲検2次(fable)が broad-stage/commit 難読化（`git${IFS}add -A`→実 .env 漏洩チェーン）・backslash-newline を摘発。1次(opus)は見逃し。→ fix-forward。
- **review reject #2**（fix-forward）: 盲検2次＋reviewer-testing が難読化大文字の非rm 全 CMD_REGEX（chmod/find/dd/shred/mkfs/git 系）回避を摘発。1次は `:161` の NORM fold 漏れを見逃し。→ FF7。
- **review 再々走 approve**: 1次(opus)=approve（CMD_REGEX 全19＋LOWER＋rm 実測）／盲検2次(fable 独立)=approve（24 パターン・新穴なし・doc 整合）／reviewer-testing=PASS（mutation 10/10・RED 真正性・midword pin）。

**1次のみでは moat 網羅性を確立できず、独立盲検2次が段階的に盲点を捕捉した**（iter72/74 の系＝乖離が実バグの在処）。

## 封鎖範囲（3体独立実測）
quote(`"`/`'`)・backslash・backslash-newline(行継続)・`${IFS}`/`$IFS`・broad-stage 難読化・commit 難読化・難読化大文字クラス全体（rm/chmod/find/dd/shred/mkfs/git 系＝全 `AEGIS_DESTRUCTIVE_CMD_REGEX`）。生 DENY 不変・`git commit -m "quoted"` 誤検知なし・fail-open 増加なし・関数抽出は挙動保存。

## Finding（severity 分類・全て Low/Info/Minor・マージブロッカーなし）

| # | severity | conf | file | 内容 | 対応 |
|---|----------|------|------|------|------|
| 1次 F-1 | Low | 8 | check-destructive.sh:50 | raw 大文字 redirect システムパス（`>/ETC`）が allow（`etc\|usr\|bin` リテラル非 fold） | SF-020 に追記済み・iter76 併合 |
| testing F1 | Minor | 8 | test_moat_quote_split.py | parametrize が CMD_REGEX 24 中 8 種のみ | FF8 で7カテゴリ追加済み（17 passed） |
| 1次 F-2 | Info | 9 | check-destructive.sh:118 | `echo "chmod -R x"` の raw over-ask（pre-existing・ask 止まり・安全側） | 記録のみ |

## 残余（既知 OPEN・iter76+ 送り・doc に分離起票済み）
- **SF-019**（Medium）: brace/param/cmdsub トークン分割（静的正規化の射程外・構造化 argv iter77 待ち）
- **SF-020**（High・iter76 P0 推奨）: raw 大文字直打ち（コマンド名 `RM -rf`＋redirect システムパス `>/ETC`・`NORM==CMD` で正規化経路外）。盲検2次も「破壊コマンドの唯一の PreToolUse ガードが raw 大文字で無反応＝実害あり」と iter76 P0 消化を推奨。
- **SF-021**（High・iter76）: `git stage` エイリアスが broad 検出器の対象外（動詞網羅漏れ）

## エビデンス
- フルスイート **1341 passed / 2 skipped / 0 failed**
- `check_framework_contract.py` PASS・`status_doctor.py` PASS
- 3体それぞれ独立の scratchpad ハーネスで実測（1次: CMD_REGEX 全19＋LOWER＋rm／盲検2次: 24 パターン＋新軸攻撃／testing: mutation 10/10 RED 化・RED 真正性）
- 封鎖実測（親再現）: F1/F2/F3 難読化→ask・生 broad→deny・誤検知回帰→allow・raw 大文字→allow(SF-020)

## Evidence Checklist
- [x] diff を実読（helper/両フック/両テスト/docs）
- [x] plan/spec 受入条件と突合（fix-forward plan FF1-8・判定表）
- [x] 未カバーエッジ列挙（残余 SF-019/020/021・redirect 大文字）
- [x] 全 finding に severity＋confidence 付与（<7 なし）

```claims
verdict: approve
tests_pass: true
no_stubs: true
second_opinion:
  verdict: approve
  divergence_points: ["難読化 broad/commit を deny でなく ask にする設計（盲検2次は ask 支持）", "SF-020 生大文字を同 iter で塞がず iter76 送り（独立チケット化済みで承認妨げず）"]
```

# iter77 review — moat case-fold（SF-020）＋stage エイリアス（SF-021）封鎖

- 対象: iter77 実装 `ad04973..d4cea18`
- 設計正本: `docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md`
- 実装計画: `docs/plans/2026-07-26-iter77-moat-case-fold-stage-alias-implementation-plan.md`
- 手法: 1次＝4角度 finder（仕様準拠・敵対バイパス・テスト強度・保守性・全 opus・read-only 6拘束）。stall した finder の load-bearing 論点（テスト強度の mutation・敵対の最終集計）は**親（fable）が in-session で実走裁定**（LEARNINGS line40＝小 diff は親直接トレースが速く確実）。2次＝盲検独立（reviewer・fable・fresh context・1次 verdict 非開示）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | commit | 状態 |
|---|------------|------------|--------|------|
| 1 | RED pin 新設＋実測 | tests/test_moat_case_fold_stage_alias.py | a200862 | ✅ 15 pin 赤11/緑4 実測（後述の追加で赤14/緑5） |
| 2 | SF-020 raw 経路 grep -i 化（4サイト） | hooks/check-destructive.sh | 298043f | ✅ D 系 9 pin GREEN |
| 3 | SF-021 `_STAGE_BROAD_RE (add\|stage)`＋文言汎化 | hooks/check-secrets.sh | 1a81bd6 | ✅ S 系 pin GREEN・16/16 |
| 4 | 統合検証（full/moat 非弱体化/record） | —（コミットなし=正） | — | ✅ full 1411 passed/2 skipped・record green・contract/drift/doctor PASS |
| — | grill-code fix-forward | tests | cac9993 | ✅ D-6b 混在ケース／S-5b 大文字×難読化合成 pin |
| — | review テスト強度 fix-forward | tests | ea21045 | ✅ D-7b（fallback :68 検知者不在を封鎖） |
| — | review 盲検2次＋保守性 fix-forward | check-destructive.sh/tests | d4cea18 | ✅ RED カウント訂正＋コメント行番号 drift 除去 |

全タスク実装済み・未着手ゼロ。Task 4 は検証タスク＝コミットなしが正。

## 1次 finder 集計（全 opus・read-only）

| 角度 | 結果 | verdict |
|---|---|---|
| 仕様準拠 | findings 0。Task 1-4 対照表完備・design 不変条件 7 項目全遵守・pin 15/15 1:1 対応・スコープ外変更なし・文言汎化は Task3 条件内・回帰 155 passed 独立裏取り | approve |
| 敵対バイパス | 主張クラス内バイパス **0 件**（65+ 入力を実 hook 実走）。既存残余 2 件を副次発見（F-1 append redirect／F-2 コマンド位置アンカーなし FP＝いずれも小文字形も同挙動＝iter77 独立・fail-safe 方向） | approve |
| テスト強度 | mutation 6/6 に検知者確立（親引き取り実走）。唯一の検知者不在（fallback CMD_REGEX の -i）を D-7b で封鎖・変異再走で FAIL 実証 | approve |
| 保守性 | Critical/Major 0・Minor 4（うち肯定 2）。実質指摘＝SF-020 コメント行番号ハードコード drift（c8）→ d4cea18 で役割名参照に修正 | approve_with_notes |

## 親実走裁定（1次 load-bearing・生 evidence）

### A. テスト強度 mutation（コピー側で差分歯を巻き戻し→検知者を確認）

元 tree 不変（`git status --porcelain` 空）・変異は system temp のコピーのみ。

| 変異（1つだけ巻き戻す） | 検知したテスト | 判定 |
|---|---|---|
| (a) 本体 rm再帰特例の -i 除去 | D-1 / D-2 / D-6 / D-6b | 検知 |
| (b) 本体 CMD_REGEX ループの -i 除去 | D-3 / D-4a / D-4b | 検知 |
| (c) fallback rm再帰 grep の -i 除去 | D-7 | 検知 |
| (d) fallback CMD_REGEX ループの -i 除去 | **検知者不在** → D-7b 追加で封鎖（再走で D-7b が FAIL） | 封鎖済 |
| (e) `(add\|stage)`→`add` 巻き戻し | S-1 / S-2 / S-3 / S-5 / S-5b | 検知 |
| (f) treadmill: -i を `(RM\|rm)` 手動 alternation に置換 | D-6b（混在 `Rm -rF`） | 検知 |

→ 差分歯 mutation 6/6 に検知者。treadmill 型（全大文字は緑のまま混在だけ silent allow に戻す）を D-6b が、fallback 検知者不在を D-7b が封鎖。

### B. 敵対クラス内バイパス探索（実 hook 実走・65+ 入力）

- **SF-020 クラス**（大文字/混在/長flag/redirect大文字/fallback）: `RM -rf`・`Rm -Rf`・`rM --RECURSIVE`・`GIT RESET --HARD`・`GIT PUSH --FORCE`・`GIT STASH DROP`・`CHMOD -R`・`DD ... OF=`・`MKFS.ext4`・`SHRED`・`echo x > /ETC/passwd`・`> /USR/bin`・`DROP TABLE`・fallback 大文字 6 形 … **全て ask**。バイパス 0 件。
- **SF-021 クラス**（stage alias broad・実 .env）: `git stage -A/--all/./-a/./`・`.[!e]*` glob・`GIT STAGE -A`・`git -c x=y stage -A`・`git${IFS}stage -A`・`git "stage" -A` … **全て deny/ask**。対照 `git stagearea`・`git stage README.md`・`git update-index --add`（broad 綴りなし）・`git stash -A` は正しく allow。バイパス 0 件。
- **回帰**: `rm -rf node_modules`・`git add README.md`・`git stage src/main.py`・`git commit -m 'add staging area docs'` … 全て allow 維持。新規誤検知 0 件。

### C. 既存残余の親裏取り（F-1）

`echo x >> /etc/passwd`（**小文字・append**）→ allow、`echo x > /etc/passwd`（単発）→ ask を実走確認。append redirect の穴は `AEGIS_DESTRUCTIVE_CMD_REGEX` の `(^|[^0-9>])>` 負クラスが `>>` の2番目 `>` を弾く構造で、**小文字形も同挙動＝case-fold（SF-020）とは無関係の既存 regex カバレッジ穴**。iter77 が導入した退行ではない。→ 新規 SF-023 として台帳起票（本 iter スコープ外・fail-safe 側）。

## 盲検 第2意見（self-attested・fable・fresh context）

独立に diff＋正本のみから判断（1次 verdict 非開示）。1次を裏取りしつつ **1 件の有用な摘発**:

- **RED カウント drift**（Minor・confidence 8）: テストヘッダの「赤11/緑4」は grill/テスト強度で追加した 3 pin（D-6b/D-7b/S-5b）を書く前の初期数字。現 19 pin を旧実装（ad04973）で実走すると **14 failed / 5 passed**。2次が旧 hooks で再走して測定 → 親が独立に再現裏取り（14/5 一致）→ d4cea18 で「赤14/緑5」に訂正＋経緯註記。
- `git commit -a` の scope 境界（Minor・c6）を「バイパスではなく正しい境界」（`commit -a` は tracked のみ staging・untracked .env は非対象）と裁定＝非 finding。

```claims
verdict: approve_with_notes
tests_pass: true
no_stubs: true
second_opinion:
  reviewer: reviewer(fable)・fresh context・1次 verdict 非開示
  verdict: approve_with_notes
  divergence_points:
    - "RED カウント: 1次は当初の赤11 を額面受理しうる→2次が旧実装再走で 14/5 を測定・親裏取り一致→訂正済(d4cea18)"
    - "git commit -a: バイパス候補に見えるが untracked .env は commit -a の対象外＝正しい scope 境界・非 finding と裁定"
```

## Findings（統合）

| ID | severity | confidence | 内容 | 状態 |
|---|---|---|---|---|
| F-RED | Minor | 8 | テストヘッダ RED カウント drift（赤11→14） | ✅ 修正済 d4cea18 |
| F-CMT | Minor | 8 | SF-020 コメント行番号ハードコード drift リスク | ✅ 修正済 d4cea18（役割名参照化） |
| F-LOWER | Minor | 7 | RAW_LOWER 経路が -i 不要な理由の未記載 | ✅ 修正済 d4cea18 |
| F-1 | Minor | 9 | `>>` append redirect が /etc 等で allow（既存・小文字も同挙動・SF-020 範囲外） | → SF-023 起票（ship 台帳） |
| F-2 | Minor | 8 | コマンド位置アンカーなし substring FP の大文字対称拡張（既存・意図的 widening・fail-safe） | 記録のみ（SF-020 既知残余） |
| F-\s | Minor | 6 | `\s` と `[[:space:]]` 表記混在（既存・挙動同値） | 記録のみ（別 iter 判断） |

Critical/Major: **0 件**。

## Evidence Checklist

- [x] diff を実読（`git diff ad04973..d4cea18`・全 finder＋親）
- [x] plan/spec の受入条件と突合（対照表・不変条件 7 項目）
- [x] 未カバーのエッジケース列挙（mutation (d) 検知者不在→D-7b で封鎖）
- [x] 全 finding に severity/confidence 付与
- [x] 独立実測: 19 pin green・回帰 155-238 passed・contract PASS・mutation 6/6 検知
- [x] read-only 遵守（全 finder＋2次とも tree clean・親の変異はコピー側のみ）

## PASS/FAIL 判定

**PASS（approve_with_notes）** — SF-020/SF-021 は主張クラス内でバイパス 0 件・moat 非弱体化（full 1395→1411 で削除0/failure0）・pin は mutation 6/6 に検知者を持つ強度。notes は全て修正済み（F-RED/F-CMT/F-LOWER）または本 iter スコープ外の既存残余（F-1→SF-023／F-2／F-\s）。

## SF 台帳更新（ship フェーズで反映予定）

- SF-020: **CLOSED-in-review**（raw 大文字 case-fold・redirect システムパス大文字も grep -i で一括封鎖）。残: F-1 append redirect は別クラス→SF-023。
- SF-021: **CLOSED-in-review**（`git stage` broad エイリアス封鎖・update-index 除外の正当性を実走確認）。
- SF-023（新規）: `>>` append redirect が システムパスで allow（Low・既存・case 非依存・fail-safe 側）。

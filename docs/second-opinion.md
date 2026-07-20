# second-opinion — iter75 SF-017 moat 封鎖（3-failure 到達）

> CLAUDE.md 3-failure ルールに基づく状況整理。goal=「SF-017 moat 網羅封鎖（難読化クラス全体）」への reject が通算3回（review×2＋security×1）。

## 何が起きているか

moat フック（check-destructive/secrets）の難読化バイパスを「静的文字列正規化（`aegis_dequote_normalize`）で shell のクォート除去・トークン分割を再現」して封鎖するアプローチ。**独立レビュー（特に fable 盲検2次）のたびに、封鎖したと宣言したクラス内の新変種が露呈**している。

| ラウンド | reject 元 | 摘発された穴 | 対応 |
|---|---|---|---|
| review #1 | 盲検2次 | broad-stage/commit 難読化（漏洩チェーン）・backslash-newline | FF1-6 で封鎖 |
| review #2 | 盲検2次＋testing | 難読化大文字が非rm 全 CMD_REGEX で回避 | FF7 で grep -i 封鎖 |
| security | 盲検2次(reject)＋1次(notes) | **SEC-1**: IFS param-expansion `${IFS:0:1}`／**Finding 1**: SAFE_TARGETS early-exit が `rm -rf${IFS}/x` を swallow | 未対応（本 doc） |

review 3ラウンドは全て「1次 opus が見逃し・盲検2次 fable が摘発」。security も同型（1次=approve_with_notes / 盲検2次=reject）。**独立盲検レビューは機能している**（穴を段階的に発見）が、**「文字列正規化で全難読化を網羅」は終わりが見えない**。

## security 摘発の3穴（実測・runtime 検証済み）

- **SEC-1（High・盲検2次）**: `hooks/lib/patterns.sh:335-336` が literal `${IFS}`/`$IFS` のみ畳む。`${IFS:0:1}`・`${IFS: -1}`・`${IFS/x/y}`・`${IFS#}` は未畳み込み＝全て実行時に空白へ展開。`git${IFS:0:1}add .env`→ALLOW（実 .env staged）＋`git${IFS:0:1}commit`→ALLOW＝silent secret commit chain。IFS 値は常に空白の部分集合ゆえ**安価に畳める・原理的限界でない**。
- **Finding 1（Medium・1次・pre-existing）**: `hooks/check-destructive.sh:84-109` の SAFE_TARGETS 早期 allow（:107）が NORM 再判定（:145）の**前**にあり、`rm -rf${IFS}/x`（flag に密着した `${IFS}`）を sed が strip せず単一 flag トークン扱い→SAFE_ONLY=true→silent allow→NORM 経路未到達。runtime で victim 実削除を確認。iter75 の regression でなく既存穴だが `${IFS}` 封鎖宣言クラス内・未記録。
- **SEC-2/glob（Low）**: `/bin/r? -rf`→ALLOW（glob-to-binary・SF-002/004 の原理的限界・静的に全 glob を列挙不可）。

## 根本分析

- SEC-1・Finding 1 はいずれも「空白注入によるトークン分割」クラス（iter75 が「封鎖」と宣言）。**安価に塞げる**（IFS family は正規表現一撃・SAFE_TARGETS は NORM 前計算）。
- ただし「文字列正規化で shell の全難読化を再現」は本質的にモグラ叩き。空白注入は quote/BS/BS-NL/IFS-family でほぼ尽きるが、word 構築（brace/param-default/cmdsub＝SF-019）は静的正規化の射程外＝構造化 argv（実行イベント/argv 判定）が根治策。
- design doc・SF-019 の既定結論: **「raw shell text を真実の代理にするな＝構造化 argv へ」**。security の2穴はこの結論を再確認している。

## 選択肢（ユーザー判断）

### 道A（FF9 で空白注入クラスを根本封鎖・推奨）
- SEC-1: `aegis_dequote_normalize` に `$IFS`/`${IFS...}` family を正規表現（`sed -E 's/\$\{?IFS[^}]*\}?/ /g'` 相当）で一撃畳み込み＝parameter expansion 変種も全カバー。
- Finding 1: SAFE_TARGETS 判定の前に NORM を計算し、`NORM!=CMD`（難読化実在）なら early-exit を skip（難読化 rm を artifact-only とみなさない）。
- SEC-2: 原理的限界ゆえ SF 起票（記録のみ）。
- **利点**: 空白注入クラスを完全封鎖（モグラ叩きでなく family/構造の一撃）。安価（各数行）。残るは word 構築（SF-019・構造化 argv 待ち）で線引き明確。
- **リスク**: 道A 後の security 再走で更に別クラスの穴が出る可能性（ただし空白注入は尽きる見込み）。

### 道B（構造化 argv〔iter77〕を前倒し）
- raw shell text でなく実行時 argv で判定する根本策。moat の網羅性問題を原理的に解決。
- **利点**: モグラ叩きの終止符。**リスク**: 大規模・iter75 スコープの大幅拡張・別 iter が筋。

### 道C（主張縮小＋残余 SF 化して iter75 クローズ）
- iter75 の封鎖主張を「見出し綴り（quote/BS/BS-NL/literal `${IFS}`/broad/commit/難読化大文字）」に正確に狭め、SEC-1・Finding 1 を残余 SF（iter76 の destructive/secret 網羅 iter で SF-020/021 と併合消化）として起票。
- security は 1次 approve_with_notes を採用しクローズ。
- **利点**: 独立レビューが摘発した穴を誠実に記録しつつ iter75 を確定（既に review/qa approve・push 済み）。**リスク**: silent bypass が iter76 まで残る（deploy blocker ではないが）。

## 推奨

**道A（FF9）**。SEC-1・Finding 1 は安価に塞げ、盲検2次も「原理的限界でない・塞ぐべき」と明言。空白注入クラスを family/構造の一撃で封鎖すれば、残余は word 構築（SF-019＝構造化 argv）に明確化される。ただし **FF9 後の security 再走でまた新穴が出た場合は道C（主張縮小クローズ）に切り替え**、道B（構造化 argv）は iter77 の独立 iter とする（3-failure の本旨＝無限リトライを避ける）。

## IDE chat 推奨
本 doc の選択肢について、必要なら別セッション（IDE chat）で設計相談も可。ただし選択肢は上記3つに集約済み。

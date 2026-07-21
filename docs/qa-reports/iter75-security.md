# iter75 security ゲート — SF-017 fix-forward「FF9」（道A→道C 確定）

> 対象: `hooks/lib/patterns.sh`（`aegis_dequote_normalize`）＋`hooks/check-destructive.sh`（SAFE_TARGETS 前倒し NORM ガード）の FF9 差分。前回 security ゲートの2件（SEC-1 High／Finding 1 Medium）への対応。

## verdict: **approve_with_notes**（deploy blocker なし）

FF9 は主張したクラス — **非空の `${IFS...}` parameter-expansion family（実行時に空白へ展開＝word-split する形）＋ Finding 1（SAFE_TARGETS 早期 allow の難読化 swallow）** — を実封鎖した。1次（security・opus）と盲検2次（fable・独立）が独立に検証し、**主張クラス内の silent-allow バイパスは0件**。両者が摘発した残余は全て「別クラス＝構造化 argv（SF-019）の accepted residual」または「runtime 実行不能（command not found／bad substitution）＝機能的に無害」であり、いずれも FF9 の scope 宣言と矛盾しない。

道A の当初主張（「`${IFS}` family 全体の封鎖」）は **道C で正確化**する: 静的文字列正規化で健全に畳めるのは**非空 IFS 展開**のみ。**空/ゼロ幅 IFS 展開（`${IFS:0:0}`・オフセット超過）と mixed split/glue・param-default ネスト・変数間接・cmdsub は 2ⁿ 展開列挙＝構造化 argv が必要**で、iter77 の根治（SF-019）待ちの residual とする。

## 検証項目（runtime 実測・プローブは hook を subprocess で JSON stdin 起動＝moat 自己ブロック回避）

| # | 検証 | 期待 | 実測 | verdict |
|---|------|------|------|---------|
| 1 | SEC-1 destructive: `rm${IFS:0:1}-rf`/`${IFS: -1}`/`${IFS/x/y}`/`${IFS#}`/`${IFS:-z}` | ask | 全て ask（NORM→`rm -rf`・bash argv も実 `rm -rf`） | ✅ PASS |
| 2 | SEC-1 secrets: `git${IFS:0:1}add .env`（直接／broad `-A`／staged commit） | ask（生は deny 維持） | 全て ask・生 `git add .env`=deny | ✅ PASS |
| 3 | Finding 1: `rm -rf${IFS}/x`・`rm -rf${IFS:0:1}/x`（flag 密着 IFS の SAFE_TARGETS swallow） | ask | 両方 ask（NORM!=CMD で early-exit skip→再帰削除検知） | ✅ PASS |
| 4 | 非回帰: 平文 safe-artifact `rm -rf build`/`node_modules dist`/`./dist` | allow | 全て allow（NORM==CMD ゆえ early-exit 不変） | ✅ PASS |
| 5 | 大文字併用 `RM${IFS}-RF`/`CHMOD${IFS/x/y}-R` | ask | ask（`grep -i` on NORM 経路） | ✅ PASS |
| 6 | 誤検知回帰: `git commit -m "fix STATUS.md"`／`cp "my file.txt" dest/` | allow | allow | ✅ PASS |
| 7 | 性能/fail-open: 多数 `${IFS}`（5000/20000） | timeout(30s)未満で ask | 84ms/157ms で ask（単一 sed O(n)・旧 bash 全置換は ~21s だった） | ✅ PASS |
| 8 | ANSI-C `$'\x20'`/`$'\t'`（非バイパス実証） | allow（実行不能） | allow・bash argv=単一語`rm -rf`→command not found | ✅ PASS（無害） |

## 新規 findings（両レビュー・全て構造化 argv〔SF-019〕residual・deploy blocker なし）

- **F-SEC-B（1次・Medium→Low 較正）**: `aegis_dequote_normalize` の `${IFS...}`→空白畳みは**ゼロ幅 IFS 展開に対し unsound**。`${IFS:0:0}`（空スライス）等は runtime で空展開＝隣接連結（glue）するが、sed は一律に空白へ畳む＝過分割。`rm -${IFS:0:0}rf${IFS}/x`（literal space＋glue-IFS＋split-IFS）→ runtime argv `[-rf] [/tmp/victim]`＝実削除・hook allow。さらに `rm${IFS}-${IFS:0:0}rf${IFS}/x`（全区切りが IFS の mixed split/glue）は **fold-to-space・fold-to-empty のどちらの純形でも非マッチ**＝2ⁿ 展開列挙が必要（実測実証）。**severity 較正**: いずれも `${IFS:0:0}` を意図的に書く必要があり、LLM が事故的に emit する確率は極小（脅威モデル=事故的自己バイパス）。単発ゼロ幅（`rm${IFS:0:0}-rf`）は `rm-rf`=command not found で無害。→ SF-019 に統合。
- **F-SEC-C1（2次・Low-Medium）**: param-default ネスト `rm${Q:-${IFS}}-rf`／secrets `git${Q:-${IFS}}add .env`（temp repo で .env 実 staging を e2e 実証）。単一パス sed が inner `}` で早期終端＝param-default 展開は静的射程外。→ SF-019 param-default クラス（既記載）。
- **F-SEC-C2（2次・Low）**: 変数間接 `x=IFS; rm${!x}-rf`→runtime `rm -rf`。`${!x}` は `${IFS...}` リテラルでない。→ 変数間接 residual（SF catalog 既記載クラス）。

**共通根**: いずれも「raw shell text を静的正規化してもシェルの展開/構築を再現できない」＝SF-004/SF-019 と同じ原理的限界。**全て意図的難読化を要し事故経路で発生しない**（North Star＝知識の乏しい利用者の事故防止から見て severity 低）。iter77 構造化 argv（実行時 argv 判定）で根治予定。

## OWASP（該当のみ）
- **Injection（Command）**: 破壊的コマンドの難読化注入。非空 IFS/quote/BS クラスは ask 化で敷居上げ。意図的難読化（ゼロ幅/mixed/param/cmdsub）は静的限界で threshold-raising 層の範囲外（SF-004 準拠）。
- **Sensitive Data Exposure**: `.env`/認証ファイルの難読化 staging。非空 IFS は ask、生は deny 維持。param-default ネスト等の意図的形は SF-019 residual。
- 他項目（Auth/Misconfig/Deps）: 本差分は該当なし（依存追加ゼロ・認証面変更なし）。

## deploy blocker 判定
**なし**。security skill の deploy blocker 列挙（auth bypass／default creds／hardcoded secret／HTTPS）に非該当。Bash moat は脅威モデル上「敷居を上げる層（threshold-raising）」であり sandbox でない（canonical 脅威モデル・SF-004）。残余は全て意図的難読化＝事故防止スコープ外。

## Evidence Checklist
- [x] secrets/credentials パターンを grep（新規 hardcoded secret なし）
- [x] 外部入力サニタイゼーション確認（hook は stdin JSON・LC_ALL=C byte-wise・sed は不正バイトで非 crash 実証）
- [x] dependency audit: 該当なし（純 bash・依存追加ゼロ）
- [x] 全 finding に severity＋remediation 付与

## 変更範囲・非退行
- full suite 1367 passed / 2 skipped（FF9 前後不変）・framework contract PASS・moat スイート 163 passed。
- 公開契約不変・機能的コマンド判定不変・後方互換。

1次（opus・security agent）は F-SEC-B（ゼロ幅 IFS 展開の unsound fold・mixed split/glue は 2ⁿ 必要）を摘発したが正式 verdict/レポートは turn 上限で未完＝親（session/fable）が finding を独立 runtime 実証のうえ本レポートへ統合し gate 判定した。盲検2次（fable・物理隔離 temp repo で e2e）は verdict=approve・divergence なし。

```claims
verdict: approve_with_notes
reviewer_1st: session-fable-synthesis
notes: 道C確定。主張を非空${IFS}展開＋Finding1に正確化。残余(ゼロ幅/mixed IFS・param-defaultネスト・変数間接・cmdsub)は全てSF-019構造化argv・意図的難読化限定・deploy blockerなし。3-failure事前合意(新穴→道C)準拠。
deploy_blocker: none
second_opinion:
  reviewer: fable-blind-isolated
  verdict: approve
  divergence_points: none
  note: 主張クラス(非空${IFS}/quote/BS)内バイパス0件。silent-allowは全てruntime実行不能(ANSI-C/brace)かSF-019既記載residualのみ。限界を実証付きで正直に文書化。
```

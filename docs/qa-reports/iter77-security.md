# セキュリティレポート — iter77（SF-020 case-fold / SF-021 stage エイリアス）

- 対象: iter77 実装 `ad04973..769ef8c`（check-destructive.sh raw 経路 grep -i 化 4 サイト／check-secrets.sh `_STAGE_BROAD_RE (add|stage)`＋文言汎化／tests 19 pin）
- 手法: 1次＝親（fable）in-session 実走（S1-S6）。2次＝盲検独立（security・fable・fresh context・1次 verdict 非開示・old-vs-new 差分照合という別手法）。
- 脅威モデル: LLM 自己バイパスの敷居上げ・case-insensitive FS（macOS APFS/Windows）前提の moat。同一ユーザー権限内の署名 attestation は範囲外（trust boundary 増えず・roadmap §6）。

## OWASP 該当項目

| 項目 | 該当 | 確認 |
|---|---|---|
| Injection | ✅ | 変更が attacker 制御コマンドを eval/exec する経路を導入していないか（S1） |
| Sensitive Data Exposure | ✅ | diff に secrets 混入・新規ログ出力経路（S5） |
| Vulnerable Dependencies | ✅ | 依存追加なし（pure bash+grep・S6） |
| Broken Auth | n/a | 認証フロー非関与 |
| Security Misconfiguration | n/a | 設定変更なし |

## 1次（親 in-session・S1-S6・全 PASS）

| # | 観点 | 手法 | 結果 |
|---|---|---|---|
| S1 | Injection | diff の `+` 行に eval/exec/`$()`実行の新設を grep＋機能変更の全列挙 | なし（grep フラグ＋regex リテラル＋文言のみ・データ照合） |
| S2 | ReDoS/DoS | 新 regex 形（`(add\|stage)`・`-i`）に大入力（3000×繰り返し・20000 空白/flag）を hook 実走 | 破滅的バックトラックなし・最悪 768ms・timeout 0 |
| S3 | case-fold | LC_ALL=C 下 `grep -i` の畳み範囲を実測（`RM`→`rm` 畳む／U+0130 バイト→`i` 畳まない） | ASCII のみ畳む＝Turkish-I 異常なし・非 ASCII 誤畳みなし |
| S4 | moat 非弱体化 | grep -i は case-sensitive のスーパーセット（match 単調増加）＝deny→allow flip 構造的に不能＋moat suite 実走 | 251 passed/2 skipped/全 green・flip 0 |
| S5 | secrets 露出 | diff の credential/secret パターン grep | 混入なし（ヒットは doc テキスト・ファイル名のみ） |
| S6 | 依存 | diff の import/source/curl/wget/pip/npm | 追加なし |

## 2次（盲検独立・fable・fresh context・old-vs-new 差分照合）

旧 hooks（ad04973 を scratchpad に materialize）と新 hooks を同一入力で実走し、厳格性（allow<ask<deny）が逆行（旧 block→新 lesser＝弱体化）した入力を機械照合:

| バッテリ | 入力数 | 弱体化 | widened(+) | timeout |
|---|---|---|---|---|
| 機能（大文字/混在/obf/回帰） | 45 | **0** | 10 | 0 |
| 差分（old vs new・救済形） | 34 | **0** | 10 | 0 |
| corner A（grep -i × bracket class `[dD]`/`W`） | 14 | **0** | 11 | 0 |
| corner B（stage alias 新面/verb 境界） | 11 | **0** | 3 | 0 |
| corner C（誤 widening 検査） | 6 | **0** | 1 | 0 |
| corner D（fallback truncated JSON） | 4 | **0** | 3 | 0 |
| case-fold 亜種（LC_ALL=C） | 3 | **0** | 0 | 0 |
| ReDoS/DoS | 7 | **0** | — | 0 |

**弱体化 0 / timeout 0 / 最大レイテンシ 239ms。** 全 6 観点を独立否定。2次の新規指摘は corner C の `MYRM -rf` が ask 化（1次 F-2 の大文字対称拡張＝widening・fail-safe・SF-020 既知残余内）1 件のみで、divergence には至らず。

## Findings

新規脆弱性: **0 件**。既存残余（iter77 独立・fail-safe 側・本 iter スコープ外）:

| ID | severity | 内容 | 状態 |
|---|---|---|---|
| SF-023 | Low | `>>` append redirect がシステムパスで allow（case 非依存の既存 regex 穴・`>` 単発は ask 済み・append は truncate より低危険） | OPEN（起票済・次 iter 候補） |
| F-2 | Low | コマンド位置アンカーなし substring FP（`MYRM`/commit メッセージ内言及）の大文字対称拡張 | 記録のみ（意図的 widening・fail-safe） |

いずれも allow→deny を弱める方向でなく moat 非弱体化。deploy blocker（auth 無効化/default creds/HTTPS 未設定/hardcoded secret）該当なし。

## Evidence Checklist

- [x] Grep で secrets/credentials パターン検索（S5・混入 0）
- [x] 外部入力サニタイゼーション確認（S1・grep はデータ照合・eval なし）
- [x] dependency audit（S6・追加 0・pure bash+grep）
- [x] 全 finding に severity＋remediation 付与
- [x] moat 非弱体化を 1次（構造＋251 pin）・2次（old-vs-new 134 入力弱体化 0）の 2 手法で確認
- [x] read-only 遵守（2次: git status 空・全攻撃は system temp・実 .env repo は都度削除）

## Claims（judge が機械読取する）

```claims
verdict: approve
tests_pass: true
no_secrets: true
deps_clean: true
moat_non_weakening: "1次=grep -i スーパーセット構造で deny→allow flip 不能＋moat 251 pin green／2次=old-vs-new 134 入力で弱体化 0・timeout 0・最大 239ms"
new_vulnerabilities: 0
deploy_blocker: none
second_opinion:
  reviewer: security(fable)・fresh context・1次 verdict 非開示・old-vs-new 差分照合
  verdict: approve
  divergence_points:
    - "手法相違（1次=実 hook 65+入力でクラス内バイパス0／2次=old-vs-new 差分で弱体化直接検出0）で同一結論に到達＝頑健性向上・実質 divergence なし"
    - "2次新規: MYRM -rf の ask 化(corner C)は 1次 F-2 の大文字対称拡張＝widening・fail-safe・SF-020 既知残余内で divergence 非該当"
```

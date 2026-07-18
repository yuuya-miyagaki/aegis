# iter72 Security Review — marker count proof（SF-014 完結編）

- 対象: `git diff 1e70fa0..HEAD`（中核 `hooks/lib/marker.sh` Stage 5＋`hooks/lib/patterns.sh` `AEGIS_TEST_COUNT_FAMILIES`・cargo zero-run deny 削除）
- 脅威モデル: 反ガミング moat（テストが≧1件実行された positive proof）を欺く LLM＝`command`（第2引数）と test 出力（stdin）を統制。3 消費者（evidence.sh source／record・drill subprocess）共有。bash 3.2・BSD/GNU grep -E。
- 体制: 1次（opus・in-repo read-only）＋盲検2次（fable・**物理隔離 clone**・1次 verdict 非共有）＋親 verify（本セッション fable）。

## OWASP 該当項目

| # | 項目 | action | verdict |
|---|------|--------|---------|
| 1 | Injection | command/output/exit_code に `$()`/backtick/`;`/改行/NUL/メタ文字を argv 経由注入（44 プローブ）・`10#$num` 算術（octal/巨大数/負） | **PASS**（command injection 0 成功・marker.sh は入力を grep のサブジェクト/算術データにしかせず eval/実行なし・9桁 cap で overflow 封じ） |
| 2 | Sensitive Data Exposure | 差分を secrets/credentials パターンで grep | **PASS**（"token" は regex トークン説明コメントのみ・実 secret 0・reject メッセージにコマンド全文非出力） |
| 3 | Vulnerable Dependencies | 新規 import・依存 manifest/lock 変更 | **PASS**（新規 import は `import re`＝Python 標準ライブラリのみ・依存 manifest 変更 0・bash/grep のみ） |
| 4 | Security Misconfiguration / fail-open | Stage 5 全経路の fail-closed・moat 回帰 | **PASS（fix 後）**（malformed→rc3・host grep 非対応 regex→rc3・cargo deny 削除は count sum に委譲で moat 不変。**ただし下記 F-CRIT-1 を fix-forward**） |

## Findings

### F-CRIT-1（High・盲検2次摘発→security 内 fix-forward で CLOSED）

- **内容**: `aegis_marker_verdict` の全 grep が **UTF-8 locale 下で不正バイトに脆弱**。攻撃者統制の test 出力のサマリ行末に 1 バイト（0xFF）を付けると grep 抽出が UTF-8 LC_CTYPE で破綻し **false-GREEN**（実行 0 件が verdict true）。2 経路: (i) **Stage 5 の `skipped=N` 減算取りこぼし**（all-skip unittest→true・iter72 由来）、(ii) **Stage 4 zero-run veto 取りこぼし**（forged strong + `collected 0 items\xff`→true・**iter71 由来 pre-existing**）。C locale では正しく false。
- **重大度**: High。moat の中核目的（zero-run/all-skip 拒否）を **default locale で 1 バイトが defeat**。Stage 5 header の「arithmetic errors fail CLOSED (true→false only)」不変条件を破る。非敵対（正当 all-skip が偶発バイトで green 記録）でも発火・人手プレビューでも 1 バイトは echo フォージより不可視。
- **再現**: `printf 'Ran 3 tests in 0.01s\nOK (skipped=3)\xff\n' | LC_ALL=en_US.UTF-8 bash -c 'source hooks/lib/patterns.sh; source hooks/lib/marker.sh; aegis_marker_verdict 0 "python3 -m unittest"'` → pre-fix `true`／post-fix `false`（C locale は常に false）。
- **修正（fix-forward）**: 関数冒頭で `local LC_ALL=C LC_CTYPE=C LANG=C; export LC_ALL LC_CTYPE LANG`＝全 5 stage の grep を byte-wise 決定化。全パターンは ASCII＋literal TAB のため byte-wise が正しい。local scope で呼び出し元に非漏洩（実測: fn 後 LC_ALL 復元）・LC_ALL 未設定環境でも機能（実測: LANG-only env でも child grep が C を見る）。
- **pin（非空検証済み）**: `test_stray_byte_all_skip_stays_false_utf8_locale`（Stage5・新規）・`test_stray_byte_zero_run_gate_stays_false_utf8_locale`（Stage4・pre-existing）。pre-fix marker.sh で両者 true 再現を確認（非 vacuous）。
- **見落とし原因**: 既存 50 pin が全て ASCII で stray-byte 経路を一度も踏まなかった（テスト網羅の盲点）。1次（opus）は injection/parse/secrets を PASS としたが locale 経路を見落とし、**盲検2次（物理隔離 clone）が reject で摘発**＝独立性の value 再実証。

### 残余（既知・非修正・文書化済み）

- SF-014 (a) echo フォージ／(b) 素 go all-skip／(c) unittest skip レポータ抑止・SF-015 pytest all-xfail（fail-closed）。いずれも marker 層の出力ベース proof の原理的床・drill が subsume。

## 1次/2次の収束

1次（opus・in-repo）: **approve**（injection 0/44・parse fail-closed・secrets/deps clean）。盲検2次（fable・物理隔離 clone・1次非共有）: **reject**（F-CRIT-1 を単独摘発）。**divergence=F-CRIT-1**。親 verify が F-CRIT-1 を独立再現（UTF-8 で true・C で false）＋pre-existing Stage4 instance も実測→ `LC_ALL=C` fix を適用し両 pin で CLOSED を実証→1次の injection/parse/secrets 評価は fix 後も不変。**収束後の統合 verdict = approve（新規脆弱性は F-CRIT-1 のみ・security 内で CLOSED）**。

## claims

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve
first_review_verdict: approve
second_opinion:
  verdict: reject
  finding: F-CRIT-1（locale 依存 false-GREEN・High）
  resolution: security 内 fix-forward（LC_ALL=C byte-wise）で CLOSED・2 pin 追加
  divergence_points: [F-CRIT-1]
new_vulnerabilities: 1（F-CRIT-1・CLOSED-in-security）
command_injection: 0/44
```

## Verdict

**approve（fix-forward 後）**。盲検2次が摘発した High 級 locale 依存 false-GREEN（F-CRIT-1・iter72 の Stage5 減算＋iter71 由来の Stage4 zero-run veto の両経路）を `LC_ALL=C` byte-wise 決定化で CLOSED し、非空 pin 2 本で回帰保護。injection（0/44）・secrets・deps・parse fail-closed は clean。cargo deny 削除は count sum 委譲で moat 不変。残余は既知 SF-014/SF-015 の marker 層天井。

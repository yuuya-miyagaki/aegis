# iter71 セキュリティレポート — marker positive proof（SF-014 恒久策）

- 対象: HEAD=d7efad4（実装 9dc77b1＋review/qa docs）
- 検証方式: 1次 security agent（opus・物理隔離 clone）＋親 in-session 実測（物理隔離 clone／read-only）。本体 tree read-only（検証後 tracked logic 無変更・docs/architecture-overview.md の M は editor 整形のみ）。
- 変更の核: 反ガミング moat（control-plane）＝`hooks/lib/marker.sh`（bash・record/drill が subprocess 呼び）。

## OWASP 該当項目

| 項目 | 該当 | 結果 |
|------|------|------|
| Injection（command） | ✅ 該当（marker subprocess） | **新規なし**（下記 #1） |
| Sensitive Data Exposure | ✅ 該当（エラー/ログ） | **新規なし**（下記 #3） |
| Security Misconfiguration（fail-open） | ✅ 該当（lib 欠落） | **新規なし・fail-closed**（下記 #2） |
| Vulnerable Dependencies | 該当（新規依存確認） | **追加依存なし**（bash/grep/python3 標準のみ） |
| Broken Authentication | 非該当（認証フローなし） | skip |

## 攻撃面ごとの実測

### #1 command injection（marker subprocess）— SAFE
- action: 物理隔離 clone で marker.sh に悪意ある入力を投入。INJ1（command arg に `; touch CANARY`）・INJ2（command に `$(touch CANARY)`）・INJ3（output/stdin に `$(...)`＋バッククォート）・INJ4（exit_code arg に `0; touch CANARY`）。
- expected: コード実行されない（canary 不生成）。
- observed: 4 ケースとも verdict は返る（marker 判定）が **canary は不生成**（`[ -e CANARY ]` false）。
- 根拠: record/drill は `subprocess.run(["bash","-c",script,"_",lib,exit_code,command], input=output)` で command を **argv 位置引数**（$3）として渡し、marker.sh 内も `printf '%s' "$cmd" | grep -qE "$PATTERN"` で **"$cmd" はクォート済み grep 入力**（パターンではない）。シェル再解釈経路がゼロ。
- verdict: **PASS（新規脆弱性なし）**

### #2 fail-open — SAFE（fail-closed）
- action: marker.sh を存在しないパスに向けて `drill.marker_verdict` を呼ぶ。
- expected: 拒否（DrillError）。
- observed: **DrillError raised**（受理に倒れない）。record は marker DrillError→rc2・ログ非書込／drill は BLOCKED（review/qa で E2E 実測済み・C4/M4）。
- verdict: **PASS**

### #3 secrets/data exposure — SAFE
- action: record 拒否メッセージ・drill BLOCKED 出力・DrillError メッセージを確認。
- observed: メッセージは固定文言（rc/verdict のみ）で、テスト出力全文・環境変数・機微パスを漏らさない。marker verdict は true/false のみ stdout。
- verdict: **PASS**

### #4 evidence-log 汚染（1次 agent 確認）— SAFE
- judge の verdict は `marker_verified`（hook 観測エントリの field・iter67 trust-scan）を読み、record が書く `marker` field は **judge 非消費**の additive 監査 field。`marker:true` を注入しても judge を騙せない（record は positive proof 後にのみ書く・judge は参照しない）。直接 JSONL 改竄は raw-file tamper（別 hook 管轄・スコープ外）。新規 gaming 経路なし。
- verdict: **PASS**

### #5 逐語移動（新規 injection 導入なし）— 確認
- action: 037545c 手前の evidence.sh の Stage1-4 と marker.sh の該当部を diff。
- observed: **IDENTICAL**（逐語移動・新規のシェル評価/展開経路を導入していない）。
- verdict: **PASS**

### #6 dependency audit
- 追加依存なし（bash＋grep＋python3 標準のみ・framework 既存前提）。

## 既知残余の脅威モデル評価（F-A）

unittest/go の all-skip suite が marker true→green（record/judge）になる残余は:
- **脅威モデル**: 「自分の qa gate を欺く LLM」＝自己欺瞞行為が必要。**外部攻撃者の経路ではない**（record/drill は開発者自身が自分の変更を検証する内部ツール）。
- **pre-existing**（marker.sh 逐語移動・iter71 導入でない）・**contained**（drill が subsume＝all-skip baseline は mutant を殺せず FAIL・qa は drill+judge 両層）。
- SF-014 恒久策（passed/failed 実数カウント proof・iter72+）で根治予定。security 観点で**新規脅威ではない**。

## 判定

**security verdict: approve（新規脆弱性 0）**。command injection・fail-open・data exposure・evidence-log 汚染とも新規リスクなし。marker subprocess は argv＋クォートで shell 再解釈経路ゼロ、全破損で fail-closed。既知残余 F-A は自己欺瞞脅威モデル・pre-existing・contained で security ブロックに当たらず SF-014 iter72 へ。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: []
```

## 盲検2次（fresh context・1次 findings 非開示・fable・物理隔離 clone）

独立に **approve_with_notes**（新規脆弱性 0・iter71 は net security 改善）。1次と収束（divergence なし）:
- **command injection**: canary バッテリ 44 calls（`;`/`&&`/`|`/`$(...)`/バッククォート/改行 を command・output・exit_code の3チャネル × marker_verdict/check_no_run_command/_execute の3関数）→ **0 injections succeeded**。Python は `bash -c <固定script> _ lib exit_code command` の位置引数参照のみ＋実行系は `subprocess.run(shlex.split(cmd))` の shell 無し exec。end-to-end でも `record "pytest ; touch CANARY"` は argv トークンゲートで拒否・log 非書込。
- **fail-open**: marker_lib 欠落/空/破損/巨大10MB/空 regex の全経路で DrillError（rc3）または False＝fail-closed。green へ倒れる破綻入力なし。
- **secrets/data exposure**: 拒否メッセージは静的ガイダンスのみ・証拠ログは payload_sha256 のみ・marker エラーの `{exc}` はテスト出力を含まない。
- **judge/evidence-log 偽造**: record の `entry["marker"]=True` は additive で judge 非消費（grep 確認）。judge の src=manual+fp 信頼モデルは iter71 以前から不変・弱化なし。
- **dependency**: 新規 source 2本とも第一者ファイル・third-party 追加ゼロ。
- **既知残余（echo/all-skip→marker true→green）を独立再発見**: 自己欺瞞（外部攻撃者面でない）・record は多層防御で contained・drill は mutation phase 全 survive→DRILL FAIL で別層捕捉。SF-014/iter72 へ scoped。iter71 は zero-run forge 2種を根切りした net 改善。
- 新規の穴なし・security 関連7ファイル独立 clone 実走 376 passed・本体 tree 無変更確認。

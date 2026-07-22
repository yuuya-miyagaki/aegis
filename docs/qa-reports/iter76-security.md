# iter76 security — evidence 整合＋locale 掃討完了

- 対象: iter76 実装 `097c103..7021ce1`（W1=SF-018／W2b=marker Stage 6＋errors alt／W2a+W3=judge washed transparent＋src allowlist）
- 参照: plan／review `docs/qa-reports/iter76-review.md`／qa `docs/qa-reports/iter76-qa.md`
- 手法: 1次＝親 in-session（security PRIMARY role・subagent は慣習／reviewer 群 stall のため LEARNINGS line40＝小 diff は親直接トレース）。2次＝盲検独立（fresh clone・verdict 非開示）。脅威モデル: LLM self-deception（自己欺瞞 green 偽造）・非 framework モードの runtime-state 改竄・非 sandbox。

## 脅威モデルと本 iter の位置づけ

本 iter は「evidence-based completion」の中核約束を守る2偽造経路を塞ぐ:
1. **washed-green**（失敗テストの green 誤認）＝marker Stage 6＋judge W2a／W3
2. **runtime-state fail-open**（不正バイトで唯一の非 framework ガードが素通り）＝SF-018 LC_ALL=C

全変更は「green 認定を狭める／deny を広げる」方向のみ＝新規 fail-open を作らない。

## OWASP 該当項目

| 項目 | 該当 | 確認 |
|---|---|---|
| Injection | ⚠確認 | **S1: 注入面なし**。marker Stage 6 は `grep -aqE "$REGEX"`（データマッチ・eval なし）・judge は `re.compile(r"[;&\|]")`（固定 pattern）。攻撃者統制の出力/cmd は**マッチ対象**であって実行されない。新規 `eval`/`shell=True`/cmdsub なし（既存 `subprocess.run([argv])` は no-shell） |
| Sensitive Data Exposure | ⚠確認 | **S2: secrets なし**（diff grep で AKIA/PRIVATE KEY/password= 等 0件） |
| Security Misconfiguration | ⚠確認 | **S4: fail-open 導入なし**。W1=deny 拡大／W2b=true→false／W2a・W3=green→unverified／errors alt=true→false＝全て締め付け方向 |
| Vulnerable Dependencies | ⚠確認 | **S3: 新規依存なし**（pure bash＋python 標準ライブラリ・追加 import は test の tempfile/unittest のみ） |
| Broken Auth | 非該当 | 認証フロー不接触 |

## security 固有バッテリ（親 in-session 実測）

| # | 検証 | 実測 | 判定 |
|---|---|---|---|
| S1 | injection 面（新規 eval/shell/cmdsub） | なし（grep/re データマッチのみ） | PASS |
| S2 | diff 内 secrets | 0件 | PASS |
| S3 | 新規外部依存 | 0（pure bash＋stdlib） | PASS |
| S4 | fail-open 方向 | 全分岐 green-narrowing/deny-widening | PASS |
| S5 | ReDoS（病的入力） | python helper 0.4ms/100k・grep 37.8ms/200k（線形・DFA・catastrophic backtracking なし） | PASS |
| S6 | moat 非弱体化 | deny 系 moat 174 passed（destructive/secrets/runtime/quote-split 全 green＝iter76 前と同 deny 維持） | PASS |

## review 期の敵対実測の継承（同一脅威の再確認・security 権威判定）

review 1次敵対＋盲検2次＋親 in-session で実走済み（`docs/qa-reports/iter76-review.md` 対照表D・バッテリA/B/C/E/V）:
- washed-green **10 綴り**（A1-6 marker＋V1-4 judge e2e：pytest 1failed／unittest FAILED／go FAIL／jest FAIL-line／抑制／redirect／cmdsub／`&&`）全 **unverified**・本物 green 保全。
- SF-018 byte 封鎖（B1-4：0xFF／0xFE／混在／redirect target）全 **deny**・silent-allow flip 実測。
- record 経路 washing 免疫（no-shell 実行＝構造的防御）。
- errors 語形 divergence（盲検2次）は実証裁定＝脅威モデル内独立到達不能（real pytest errors は exit≠0・洗浄は W2a／fake binary は iter77 天井）＋tight anchor 緩和＝SF-022。

## 既知残余（deploy blocker でない・脅威モデル外/天井）

- **単一コマンド fake binary**（`./pytest` PATH hijack）・**evidence cmd 500字切詰め以降の演算子**＝iter77 attestation の領分（多層防御で穴でないと論証済み・design §実装同期4）。
- **denylist 原理的不完全性**（marker Stage 6 の失敗語彙）＝SF-022・iter77 positive proof で根治。
- いずれも**意図的自己欺瞞 or 脅威モデル外 capability を要し事故経路なし**。deploy blocker なし。

## Findings

**新規脆弱性 0件**（Critical/High/Medium/Low いずれも新規なし）。全変更が fail-closed 方向・注入/secrets/依存/ReDoS 面いずれもクリア・deny 系 moat 非弱体化を実測。

## 盲検2次（security・fable・fresh clone・verdict 非開示）＝approve・A7 corroboration

**verdict: approve**（新規脆弱性なし・Critical/High ゼロ）。独立実走で確認:
- washed-green: honest 経路で green 化ゼロ（marker Stage6／judge W2a+W3・演算子回避〔redirect/cmdsub/`!`〕も exit 非洗浄 or runner_match=False で封鎖）。
- SF-018: 0xFF/0xFE/NUL/UTF-16 BOM 全 deny・`LC_ALL=C` で locale 非依存 fail-closed（親 locale を UTF-8 強制しても上書き）。
- 注入/fail-open/ReDoS（240KB/100K 病的入力・線形）/moat（純加算・削除ゼロ・DESTRUCTIVE 24本健在）＝全クリア。
- read-only 遵守（clone `git status` 空を複数回確認・mutation は clone 外 sec2attack1/sec2root1）。

**A7（Low・非到達・fix-forward で封鎖）**: `FAILED (unexpected successes=1)`+exit0 で marker true を摘発。ただし実 unittest は exit1（2次自身が実測）＝**独立到達不能**（洗浄は W2a／fake は iter77）。SF-022 の denylist 不完全性クラスの一事例で、unittest FAILED バナー語彙は failures/errors/unexpected successes の**有界3種**＝既存 alt を完成（`FAILED \((failures|errors|unexpected successes)=`）して封鎖。pin＝`test_w2b8`。**1次との実質同意**（両者 approve・新規脆弱性0・A7 は非到達残余を有界完成で緩和）。

その他 2次認定の既知天井（単一コマンド fake binary＝iter77／log 直書き＝脅威モデル外／fail-token false-negative＝fail-closed 方向）は 1次と収束。

```claims
tests_pass: true
no_stubs: true
no_new_vulnerabilities: true
deploy_blocker: false
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: ["A7=unittest FAILED バナーの unexpected successes= 語形が fail-token 未収載（marker true）→ 2次自身が実 unittest exit1 で独立到達不能を実測・有界バナー完成で fix-forward 封鎖・SF-022"]
```

## Exit 判定（1次＋2次収束）

**approve**（新規脆弱性0・全分岐 fail-closed・注入/secrets/依存/ReDoS クリア・moat 174 tests 非弱体化・washed-green/SF-018 の主張クラス内バイパス0を 1次 in-session＋2次盲検 fresh の両方で実測・deploy blocker なし）。2次の A7（unittest バナー語彙欠落）は 2次自身が独立到達不能を実測のうえ有界バナー完成で fix-forward 封鎖（SF-022 記録・test_w2b8 pin）。1次/2次とも verdict=approve で実質同意・divergence は A7 の1点のみで非ブロッキング。

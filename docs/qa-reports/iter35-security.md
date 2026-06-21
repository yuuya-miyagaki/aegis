# iteration 35 security gate — セキュリティ証拠（layer-2 immutable moat）

> 対象 diff: `git diff 585573a..HEAD`。設計 rev.2 / review 証拠 docs/qa-reports/iter35-review.md。
> 脅威モデル: 事故防止（非 sandbox）。owner が `chmod +w`/`os.chmod` を前置すれば書ける＝設計上許容。
> 検証の主眼: 「lock 中、CP file の**内容は本当に不変か**」を adversarial に実走で確認する。

## OWASP 該当チェック（非該当はスキップ）

- **Injection（Command）**: cp-lock.sh は `chmod -R a-w "$p"` のみ。`$p`=`${root}/<固定リテラル>`、`root` は
  session-start の `cd … && pwd`＝**絶対パス（先頭 `/`）**。引用符付き＋先頭 `-` 無し＝flag 誤認/glob/語分割
  なし。**injection なし**。
- **Sensitive Data Exposure（secrets）**: diff を secret パターン（AKIA / PRIVATE KEY / api_key=… 等）で
  grep→**ヒット 0**。
- **Security Misconfiguration（lock/permissions）**: 下記 §不変性プローブで検証。
- **Vulnerable Dependencies**: 新規外部依存 **なし**（cp-lock.sh は pure-bash・python/jq 非依存）。
- Broken Auth / XSS / SQLi: 非該当（認証・Web・DB 不在）。

## 不変性プローブ（adversarial・実走・scratch tempdir）

`aegis_cp_lock` 後の locked CP file（`hooks/lib/emit.sh`='orig'）へ各ベクタで書込みを試行:

| ベクタ | 結果 | 機序 |
|---|---|---|
| `truncate -s 0` | **blocked** | truncate() に write 権限要・a-w で EACCES |
| `: > file`（O_TRUNC） | **blocked** | open(O_WRONLY\|O_TRUNC) に write 権限要 |
| `dd of=` | **blocked** | 同上 |
| `tee` | **blocked** | 同上 |
| `python open(w)`（SF-004 形） | **blocked** | 同上 |
| `rm -f` | **blocked** | dir が a-w＝entry 削除に親 dir write 要 |
| `mv over` | **blocked** | 同上（rename 先 dir が a-w） |
| `install -m` | **blocked** | temp 作成→rename に dir write 要 |
| **`hardlink`→write** | **blocked** | **mode は inode に属す**＝hardlink 経由でも同一 a-w で EACCES |

→ **事故クラスの内容改変ベクタは 9/9 すべて syscall で遮断**（file content INTACT）。
特に hardlink は「別 entry から書けるのでは」という直感的バイパスだが、**mode が inode 共有**のため
閉じている。dir lock（`-R`）が create/delete/rename を、file lock が content 改変を担う二重で成立。

## 残余（accepted・非 deploy-blocker）

- **pre-opened FD**: lock **前**に open した FD は lock **後**も書ける（write 権限は open 時に確定）。
  ただし事故シナリオ（既に locked な project session でエージェントがツールで触る）では FD は
  lock 後に fresh open される＝遮断。**`os.chmod` 解錠と同じ『lock の前/外で動く』クラス**で、
  事故ベクタではない。非 sandbox の脅威モデルどおり許容。
- **owner os.chmod/os.chflags 解錠**: 設計どおり許容（敵対は閉じない＝SF 項目 CLOSED にしない）。
- **settings 除外**: `.claude/settings*.json` は layer-2 除外（ハーネスが書く）。layer-1（check-gate /
  check-control-plane / check-skill-gate）が編集を deny 済＝層2 が唯一守るべき事故ベクタを再開しない。

## fail-open 検査

session-start の lock 呼びは `if command -v aegis_cp_lock … ; then … aegis_cp_lock "$ROOT" || CONTEXT+=warn`。
lock 失敗（rc=1）/ lib 欠損 / 非対応 OS では **warn を出して継続**＝「保護済みと誤認して黙る」silent
fail-open は無い（test_lock_failure_warns_not_crashes / test_missing_lib_does_not_crash で固定）。
layer-1 は常時 fail-closed で並存＝lock 失敗でも moat は残る。

## 判定: **approve（deploy-blocker なし）**

事故クラスの内容改変ベクタを syscall で網羅遮断（9/9・hardlink 含む）。残余は脅威モデルが明示的に
許容する「lock の前/外で動く」クラス（pre-open-FD / os.chmod 解錠）のみ＝非 deploy-blocker。
secrets 0・新規依存 0・command injection 無し・fail-open 無し。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["なし（security エージェント独立パスは 24 tool-use 後 infra stall で最終報告未達だが、コーディネータが同等の adversarial プローブ 9 ベクタを実走し immutability を実証。review 期の Review Army 3 specialist も独立済）"]
  agents:
    security: partial（infra stall・24 probes 実走後 rm -rf クリーンアップで停止）— 独立 adversarial 試行
    coordinator_probes: complete — truncate/O_TRUNC/dd/tee/open(w)/rm/mv/install/hardlink/pre-open-FD を実走、9/9 content 改変遮断・pre-open-FD のみ残余（accepted）
  note: deploy-blocker 列挙（auth bypass/default creds/hardcoded secret/HTTPS）には非該当。pre-open-FD と os.chmod 解錠は脅威モデル明示の accepted residual。
```

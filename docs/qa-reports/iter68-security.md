# Security Report — iter68 update-gate `approve --ref` 原子化＋SIGPIPE 耐性＋advisory 降格

- 日付: 2026-07-13
- 対象: git 範囲 `8ab52ed..HEAD`（scripts/update-gate.sh・check_status.py・build-judge-card.py・tests・guidance）
- 体制: 1次=親 in-session（fable・独立 clone で実測）／盲検2次=物理隔離 clone の security エージェント（fresh・1次結論非開示）
- 種別: 防御的セキュリティレビュー（自作フレームワークの gate 完全性検査・単一ユーザ dogfood・脅威モデル=事故的自己バイパス）

## 手続き注記（透明性）

最初にディスパッチした security 1次サブエージェントが read-only 拘束（routing.md Verification delegation 6）に違反し、本体 tree の `docs/architecture-overview.md`（オートフォーマッタ由来の空白整形・意味変更なし）と `docs/qa-reports/test-strength.md`（ドリルランナー上書き）を変更した。**両ファイルは `git checkout` で committed 状態へ復元済み**（tree clean 確認）。evidence-log への observed 追記は untracked かつ全て undecidable（observed・marker_verified=false）で iter67 trust-scan により透明＝gate 判定 tier-1（tests=green）に不影響（judge preview で確認）。当該 run は信頼せず破棄し、1次は親が in-session で全項目を独立 clone 上で再実測した。教訓は LEARNINGS へ記録（検証委譲は物理隔離 clone を標準化）。

## OWASP 該当項目

- **Injection**（該当・重点）／**Sensitive Data Exposure**（該当・軽）／**Security Misconfiguration**（gate 完全性＝該当・重点）。Broken Auth・Vulnerable Deps は非該当（新規依存ゼロ・認証フロー不変）。

## 検査結果（1次・独立 clone 実測・HEAD=d95c2ee）

| # | 攻撃面 | evidence（action/expected/observed） | verdict |
|---|--------|------|---------|
| 1 | --ref evidence 偽装 | 任意の実在 repo ファイルを --ref に渡すと evidence として受理される。**baseline（raw-Edit で current_refs.<gate> を任意実在パスに設定→approve）と同一**＝evidence_integrity は「実在」のみ検査し意味的妥当性は元から見ない。**新規能力ではない**（原子化しただけ・監査面はむしろ update-gate 経由に一本化して向上） | 新規リスクなし |
| 2 | AEGIS_PENDING_REF env 汚染 | `resolve_gate_report` のみが env 参照（tier-2 claims 源）・`compute_facts`（tier-1 fp/tests/secrets/stubs）は env 非参照を実測。env 設定＋`--pre-approve-gate` 単独では STATUS 不変（承認 write は update-gate の sed のみ）。claims は元から self-attested（低信頼）で operator が current_refs 経由で指し先を制御可能＝**既存 tier-2 信頼境界内・gate-bypass なし・tier-1 不接触** | 新規リスクなし |
| 3 | advisory 降格の bypass | approved+空 ref→rc1 FAIL（`EVIDENCE: … is empty`）・approved+ref 不在→rc1 FAIL（`points to missing`）を実測維持。pending+ref→rc0・**stdout 空**・stderr WARNING（TaskCompleted hook の stdout=violation 契約で完了を再ブロックしない）。降格は stale-ref violation のみ除去し、それは writer が reset/na で null 化・approve --ref で原子設定するため実害窓なし | 非退行・新規 bypass なし |
| 4 | injection（--ref） | allowlist `[A-Za-z0-9._/-]`＋先頭`/`拒否＋`..`拒否＋空文字拒否を実測: `a;rm -rf x`／`` a`id` ``／`a"b`／改行入り／`docs/x&.md`／絶対／`..`／空 を**全て状態変更前に exit 1 で拒否**。sed 置換部・YAML 引用に安全に直挿し可能な文字集合に限定。GATE_NAME/ACTION は enum 検証・ACK_REASON は `printf '%s'` でカード追記 | 封鎖確認 |
| 5 | secrets/exposure | 変更 diff に secrets パターンなし（grep）。エラー文言はパスのみ・judge カードに機微情報なし | なし |
| 6 | fail-open | 書込みは明示 `if ! sed`／`if ! mv` で fail-closed（review 4-A 修正・chmod555 回帰テスト付き）。snapshot 失敗・ACK 追記失敗は**状態永続化の後**の best-effort（`|| true`／追記のみ）で、失敗しても gate 値は既に確定済み＝偽承認や状態破壊にならない。trap '' PIPE 下の EPIPE レース（F-1）は review で根絶（早期終了消費者を全量読み/変数キャプチャに置換・実測 0/3000） | fail-closed 確認 |
| 7 | dependencies | 新規依存ゼロ（pure bash＋標準 python） | なし |

## Findings

| # | Severity | 内容 | remediation | 状態 |
|---|----------|------|-------------|------|
| SF-013(a) | Low | sed 範囲終端 `/^[a-z]/` が `---` で閉じず、current_refs が frontmatter 末尾 key の異常 STATUS で body へ leak し得る。**pre-existing**（baseline の reset null 化 sed と同一範囲パターン・canonical STATUS では到達不能） | 範囲終端を frontmatter 境界に閉じる（awk 化 or `/^---$/` 複合）＋異常構造 fixture | OPEN・iter69+ hardening（起票済 docs/security-followups.md SF-013） |
| SF-013(b) | Low | --ref の `-f` 判定が symlink を辿り、repo 内 symlink→repo 外実ファイルが存在チェックを通過し得る。single-user・ref は非実行の証跡・tamper writer 前提で capability 増分なし | realpath の repo 包含チェック（YAGNI 評価と併せ） | OPEN・iter69+（同上） |

Critical/High/Medium: **なし**。新規脆弱性ゼロ。SF-013 の2件はいずれも pre-existing・Low・contained（差分実走で baseline=HEAD を確認）。

## Evidence Checklist

- [x] Grep で secrets/credentials パターンを検索した（diff にヒットなし）
- [x] 外部入力（--ref path）のサニタイゼーションを実測確認した（allowlist 9系列）
- [x] dependency audit（新規依存ゼロを確認）
- [x] 全 finding に severity と remediation を付与した

## Exit Criteria

- OWASP 該当項目確認完了・全 finding severity 付与・本レポート存在・deploy blocker なし（M=deploy skip）

## 判定: **approve**（新規脆弱性0・SF-013 は pre-existing Low を分離起票）

## Claims（judge が機械読取する）

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: []
  evidence: "1次=親 in-session（fable）が独立 clone〔HEAD=d95c2ee〕で7攻撃面を実測（injection 9系列全拒否・env は tier-2 のみ tier-1 不接触・advisory 降格の FAIL 非退行 A/B/C 実測・fail-open 4-A 修正確認）。最初の 1次サブエージェントは read-only 違反で破棄（本体 tree 復元済み・手続き注記参照）。盲検2次=物理隔離 clone の fresh security エージェント（sec2-clone@d95c2ee／baseline@8ab52ed／1次結論非開示）が独立に approve 収束: 中核『env/--ref は gate 決定権ゼロ・tier-1 facts は fs/git から無条件算出・forged all-green claims は 🟡 止まりで 🟢 不可・rc2 ack-needed 止まり』を実証。injection 13 vector 全拒否・fail-open 4-A 修正確認・approved+空/ref不在 FAIL 非退行(a)(b)(c)・secrets/新規依存ゼロ。SF-013 の2件(sed範囲/ symlink)を pre-existing/Low/contained と独立確認（baseline=HEAD 差分実走）。1次との相違点ゼロ。"
```

<!-- 盲検2次 approve 収束・divergence 0 -->


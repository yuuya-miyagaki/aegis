# iteration 41 Batch 1 — Security Review

- date: 2026-06-24
- task: framework / L / 配布正常化（D1-D4）＋整合性 fail-closed 化（I1-I2）
- 脅威モデル: docs/security-followups.md（moat=事故防止・敵対回避は SF-004 受容／gate=人間承認の偽造不能性が強い性質）に照らして較正。

## 監査サーフェス

- 変更が触れる integrity-critical: `hooks/post-status-audit.sh`（gate/mode tamper 検知）、`hooks/lib/safety.sh`（fail-closed helper）、`scripts/check_status.py`（完了evidence）、`scripts/check_framework_contract.py`（drift 検知）、`bin/setup.sh`（配布）。
- secrets / 認可 / 入力検証 / コマンドインジェクション / 新規 untrusted-input 経路の有無を確認。

## findings（severity 付き）

| # | 項目 | 判定 | 根拠 |
|---|------|------|------|
| Q1 | I1 fail-closed の真正性 | PASS | `post-status-audit.sh:23-36` 二段（読取不能／source 失敗）とも `{"decision":"block"}`＋exit0。`safety.sh:60-65` reason は静的（%s/$VAR なし）＝JSON injection 面ゼロ。emit JSON は有効な PostToolUse block として parse 可。 |
| Q2 | fallback が target filter より前 | PASS（過剰遮断・fail-safe） | lib 破損時は全 Edit/Write を block＝厳密に over-block であり exploit 不可（extract-input 自体が壊れた lib のため filter 不能）。 |
| Q3 | I2 の新 fail 経路 | PASS | 唯一の呼び元 check-task-completed.sh は STATUS 不在で手前 early-allow（:95-98）＝正常フロー無影響。frontmatter-None と python3 破損は stdout 有無で曖昧性なく分岐。 |
| Q4 | D3 上書きの悪用/取りこぼし | PASS（Low residual） | `is_framework_owned` で範囲限定・cmp-gate で churn 回避・byte 差で確実に上書き。**Low/受容**: `.bak`/上書きが symlink を辿る＝事前 CP 書込み済（既に game-over）でのみ＝SF-004 と同クラス受容。 |
| Q5 | D2 contract false-negative | PASS | CORE 5 hook を全 command 文字列に対し substring 照合（"created" は "completed" の部分文字列でない＝誤マッチなし）。不在 settings は skip（gitignored・install 時 run_profile_check が別途 warn）。 |
| Q6 | secrets/injection/untrusted-input | PASS | 新規 secret なし。setup.sh の python heredoc は operator 提供のローカルパスのみ補間（tool input ではない）＝信頼水準は従来と同一。D4 は silent data-loss を是正（perms 喪失→警告+.bak）。 |

## 盲検 第2意見（self-attested）

独立 security エージェント（1次 verdict 非共有・diff と脅威モデルのみ）を実走。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["D3 .bak/overwrite が symlink を辿る（Low・SF-004 受容クラス）"]
```

## 判定

**PASS（approve_with_notes）。** 新規脆弱性なし。I1/I2 は fail-open 非対称を正しく閉じ、gate の偽造不能性・moat の事故防止目的を退行させない。Low residual（symlink follow）は脅威モデル上 SF-004 と同クラスで受容（security-followups に記録）。deps 変更なし（bash + python stdlib）。

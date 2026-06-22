# iteration 37 security — moat lifecycle re-lock（framework・M）

> design（正典）: `docs/plans/2026-06-22-iter37-moat-relock-design.md`
> 対象 diff: `git diff d33140e..HEAD`
> 脅威モデル前提: layer-2 moat は**事故防止層**（uid≠root・owner は chmod/STATUS 編集/bash 実行が可能＝敵対 sandbox ではない。iter35 disposition・`docs/security-followups.md:163,166`）。lock 機構自体は iter35 で adversarial 済。本 iteration は**新トリガ（再施錠）**のみを対象に regression/新サーフェスを審査。

## OWASP Top 10（該当項目）

| 項目 | 判定 | 根拠 |
|---|---|---|
| Injection（Command） | ✅ なし | `task_type` は `frontmatter_value`→`"$_AEGIS_TT"` と**クォート**で `aegis_cp_apply` に渡り、内部では `[ "$task_type" = "framework" ]` の文字列等価比較のみ。eval なし・コマンド語分割なし・パス利用なし。実証: `framework; rm …`／バッククォート／`framework foo` を投入→**何も実行されず**全て lock 分岐（厳密リテラル `framework` のみ unlock）。 |
| Sensitive Data Exposure | ✅ なし | 変更コード行に secrets なし（changed-line scan）。chmod 副作用のみ。 |
| Security Misconfiguration | ✅ 強化 | 再施錠トリガ追加でセッション中の unlock 窓を閉じる。default-lock（空/未知 task_type→lock）で fail-safe。settings.json は従来どおり除外。 |
| Vulnerable Dependencies | N/A | 本リポに外部依存 manifest（requirements.txt/package.json）なし＝deps 監査は対象外（unverified=advisory）。 |

## Findings（盲検 security エージェント・adversarial）

| # | finding | severity | confidence | 分類 |
|---|---------|----------|-----------|------|
| F1 | `task_type` データフローに injection なし（クォート文字列等価のみ・eval なし） | — | 10 | residual-risk none |
| F2 | default-lock は fail open しない（sentinel 方向正・`[ -e ]` ガードで欠如時も lock へ落ちる） | — | 10 | residual-risk none |
| F3 | 両 call site の `aegis_cp_apply` 集約は挙動保存（追加は冪等プローブ＝純最適化） | — | 9 | — |
| F4 | gate-tamper 監査の deny は不変（`|| true`・emit なし・snapshot 前配置。tamper 実走で block 継続を確認） | — | 10 | residual-risk none |
| F5 | task_type=framework での unlock は**新能力ではない**（owner は元々 chmod 可）＝意図した lifecycle | — | 9 | accepted |
| F6 | secrets なし・新規依存なし・deploy-blocker クラス（auth bypass/hardcoded secret/default creds/HTTPS）非該当 | — | 10 | — |

deploy-blocker: **なし**。新規 residual risk: **なし**（pre-existing SF-001/004/005 の静的 moat 限界は本トリガ変更の対象外・不変）。

## Evidence Checklist

- [x] secrets/credentials を grep（変更行スキャン）→ 0
- [x] 外部入力（task_type）のサニタイズ確認＝クォート文字列等価のみ・injection 実走で無害を実証
- [x] dependency audit＝対象 manifest なし（N/A・unverified=advisory）
- [x] 全 finding に severity/confidence 付与
- [x] full suite 1038 passed/1 skip・git backstop クリーン・contract PASS（版 1.14.0）

## 盲検 第2意見（self-attested）

1次（security エージェント・上記 F1-F6）verdict を渡さず、独立 holistic `reviewer`（diff/design のみ）が moat セキュリティ regression を独立審査。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: false
second_opinion:
  agent: reviewer (holistic, blind)
  verdict: approve
  confidence: 9
  note: 「Security regression — none。settings.json 除外維持・path-set 不変・layer-1 静的 moat 不変・default-lock は moat を厳密に強化」と独立判定。
```

1次 verdict=approve / 2次 verdict=approve＝一致。divergence なし。注: `deps_clean=false` は本リポに依存 manifest が無いことによる unverified（advisory・--ack で承認可）であり脆弱性検出ではない。

## 判定

**PASS（security gate approvable）**。deploy-blocker ゼロ・新規 residual risk ゼロ・secrets 0・injection 無害実証。deps は manifest 不在の N/A（unverified advisory）。1次・2次 approve 一致。

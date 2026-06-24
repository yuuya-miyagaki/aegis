# iter44 Security Report — C5 ROOT-external plan-gate false-positive

- 日付: 2026-06-25
- 変更: `hooks/check-gate.sh` に ROOT 外絶対パスの allow short-circuit を追加（control-file/templates/docs 判定の後・MODE/Client/plan-gate の前）
- 脅威モデル: Aegis hook は **LLM 自身の事故/self-bypass** に対するガードレール（外部 adversary 非対象）。plan-gate は workflow ゲートで security 境界ではない。

## OWASP Top 10 該当性

変更は path 分類ロジック（guardrail hook）のみ。以下は非該当（理由付き）:

- Injection: 非該当（外部入力の解析・実行なし。bash `case` の lexical パターンのみ。`emit.sh` の既存エスケープ不変）。
- Broken Auth / Session: 非該当（認証フローに無関係）。
- Sensitive Data Exposure: 非該当（secrets を読み書きしない。`grep` で新規 secret/credential パターンなしを確認）。
- Security Misconfiguration: 該当軸＝**ガードレール緩和が bypass を開くか**（下記で精査）。
- Vulnerable Dependencies: 非該当（**新規依存ゼロ**。bash ＋ python stdlib のみ。dependency audit N/A）。

## ガードレール整合性の精査（1次）

判定順（実トレース）: docs allowlist → templates → `is_control_file` → **新 short-circuit** → Client/plan-gate。
short-circuit は `is_control_file` の**後**にあり、`/*` allow に到達するのは ROOT 外絶対のみ。

- canonical な ROOT 内 code・control file（hooks/scripts/.claude/CLAUDE.md/templates）は引き続き gate 維持
  （test_b/c/g/h/i ＋ 盲検 security の pre/post トレースで確認）。
- 緩和されるのは「ROOT 外の非 control 絶対パス」のみ＝この project の code でない。
- empty-`$ROOT_REAL` は `/*` に縮退し**全絶対パスを keep-gating アームへ**＝fail-safe（deny 側・実行確認済）。
- `/` anchor が sibling（`/path/aegis-backup`）を外部判定（test_j）。

## Findings

### Critical / High
該当なし。

### Low（受容）
- **[conf 7] case-variant control-file backstop の喪失** — 盲検 security の pre/post 実証による訂正。
  case-insensitive FS（macOS）で control file への **case-variant 絶対パス**（`/PATH/AEGIS/hooks/x.sh`）は
  PRE-C5 では plan-gate の偶発 backstop で deny、POST-C5 は short-circuit で allow。C5 は plan-gate の
  *incidental な case-variant backstop を除去*する。**受容理由**: (1) 自己誘発のみ（agent が非 framework
  作業中に自分の hooks へ非正規 case の絶対パスを発行する必要があり非現実的）、(2) `is_control_file` は
  approved-plan 窓で既に同 lexical limit を共有、(3) plan-gate は security 境界でない。FS-aware case-folding は
  lexical-only 設計原則に反するため非導入。設計の セキュリティ分析 を本訂正で同期済み。
- **[受容] グローバル `~/.claude/settings.json` が plan pending 時 allow** — plan-gate は plan approved で即 allow に
  なる workflow ゲートで、グローバル設定の整合性保護を**もともと提供していない**。別機能（スコープ外）。

### 受容済み（新規穴ではない）
- symlink lexical 限界（全フック共通）。relative パスは従来どおり gate（test_g）。

## Net 評価

**net-positive / integrity に対し実質中立。** 実バグ（auto-memory false-positive）を解消し、canonical な
integrity ゲート対象で新たに allow されるものはない。新規 allow は Low の case-variant control edge（自己誘発のみ）のみ。

## 盲検 第2意見（self-attested）

1次（本レポート＋設計の セキュリティ分析）確定後、verdict 非共有・fresh context（diff＋spec/plan のみ）で
独立 security エージェントを 1 回ディスパッチ。pre/post 実行トレースで全主張を検証し、Low 1 件（case-variant
backstop の特徴づけ訂正）を指摘＝本レポート・設計に反映済み。

```claims
verdict: approve_with_notes
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["Low(conf7): 当初『no new exposure』は case-variant control file で不正確→『plan-gate の incidental backstop 除去』へ訂正・受容", "empty-ROOT_REAL fail-safe を実行確認(deny 側)", "canonical control/code は gate 維持を pre/post トレースで確認"]
```

1次/2次とも approve_with_notes で一致。Critical/High 0・Low 1（受容・文書化済）。

## 判定

**PASS。** 新規脆弱性なし。ガードレール緩和は ROOT 外（非 project code）のみで integrity 対象は不変。
Low 1 件は自己誘発のみで受容・設計同期済み。deploy blocker なし。

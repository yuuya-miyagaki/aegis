# iter53 セキュリティ — 破壊的コマンド警告の日本語化＋ドリフトガード

- 参照: plan `docs/plans/2026-06-28-destructive-warning-japanese-implementation-plan.md` / spec `docs/specs/2026-06-28-destructive-warning-japanese-design.md`
- 対象: hook の理由文字列（permissionDecisionReason）を英語→日本語化＋ドリフトガード。判定 regex・ask/deny 発火は無改変。

## OWASP 該当項目（該当のみ）

| 項目 | 確認 | 結果 |
|---|---|---|
| Injection / 出力健全性 | reason は開発者が書いた静的文字列。外部入力混入なし。emit.sh が JSON エスケープ。日本語＋全角/半角括弧＋句点＋スラッシュ＋em-dash の全18件を round-trip 検証 | **PASS**（valid JSON 18/18・不正 JSON 0・制御文字なし） |
| Security Misconfiguration（moat） | 検出 regex・ask/deny 発火・safe-targets 例外が無改変。WARN は assign→emit のみで判定分岐に非使用 | **PASS**（REGEX/logic 行 byte-identical・behavioral spot-check 一致） |
| Sensitive Data Exposure | 差分・新文字列に secrets/credentials/トークン混入なし（grep） | **PASS** |
| Vulnerable Dependencies | 新規依存パッケージ・外部コマンド追加なし（テストは stdlib のみ・ドリフトガードは bash source の read-only） | **PASS** |
| Broken Authentication | 該当なし（認証フロー無関与） | n/a |

## moat 不変の実証

- `git diff hooks/lib/patterns.sh`: `AEGIS_DESTRUCTIVE_*_REGEX` 配列・safe-targets 例外・ask/deny 発火行に diff ゼロ。WARN は `emit_ask "[careful] $WARN"`（check-destructive.sh）の引数として渡るのみで条件述語に非使用＝文字列変更で検出は緩まない。
- behavioral spot-check（2次 security agent 実行）: `git push --force`/`DROP TABLE`/`rm -rf /etc`/`mkfs`→`ask`（日本語 reason）、`rm -rf node_modules`/`.env.example`→`allow`。決定不変。
- 抽出失敗フォールバック（check-destructive.sh:49・check-secrets.sh:49-50）の発火条件は無改変＝emit 文字列のみ差分。
- 既存 destructive/secrets/control テスト **88 passed**。

## findings（severity・remediation）

| severity | finding | disposition |
|---|---|---|
| 🟢 Low（情報） | `emit.sh:42` の C0 制御 squash は新 JP reason に no-op（全文字が printable ASCII か ≥U+0080）。出力は有効 JSON | **受容**: 経路を実走確認（18/18 valid）。remediation 不要 |
| 🟢 Low（非セキュリティ） | `tests/test_destructive_warning_language.py:82` のハードコード件数（16）は将来の正当なパターン追加で false RED。真の fail-open リスク（REGEX に対応 WARN 欠落）は隣接の `test_warn_regex_parity` が担保 | **受容**: 別失敗モード（両配列同時縮小）を捕捉する tripwire＝無害。qa 承認済みドリルを churn する価値なし。reviewer-testing も独立指摘し受容済 |

🔴 Critical・🟠 High・🟡 Medium なし。

## verdict

理由文字列のみの日本語化で、判定ロジック（moat）は byte-identical＋behavioral spot-check で不変を実証。injection 経路なし（静的文字列・JSON 健全）・secrets なし・新規依存なし。**approve**。

```claims
verdict: approve
tests_pass: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points:
    - "2次(security agent)は fresh context で moat の byte-diff＋behavioral spot-check（push --force/DROP/rm -rf /etc/mkfs→ask, node_modules/.env.example→allow）を独立実行し決定不変を確認"
    - "2次が全18 reason の JSON round-trip（valid 18/bad 0）と emit.sh エスケープ no-op を独立検証"
    - "2次が secrets/deps clean・フォールバック発火条件無改変を独立確認・ハードコード件数の冗長を指摘（非セキュリティ・受容）"
```

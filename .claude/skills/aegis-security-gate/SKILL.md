---
name: aegis-security-gate
description: "Aegis security phase composite skill: invoke the official security-review skill, then layer aegis OWASP checklist, evidence requirements, and gate contract."
disable-model-invocation: true
user-invocable: false
---

# Aegis Security Gate（合成スキル）

> Claude Code 公式 `security-review` スキルを基盤として呼び出し、その出力に aegis
> 固有の OWASP Top 10 チェックリスト・evidence 要件・gate 契約を重畳する合成スキル。
>
> v0.13.0 (Phase 0b): 公式同名スキルとの衝突を回避するため `security-review` から
> 改名。公式版が網羅する一般的セキュリティレビュー観点は重複説明せず、aegis 固有の
> OWASP 重畳・evidence 要件・gate 連携のみ記述する。

## Step 0: 公式 security-review スキルを呼び出す

```
Skill(skill="security-review")
```

返ってきた findings をベースに、以下の aegis 固有 Step を追加実行する。

## OWASP Top 10 チェックリスト（aegis 固有、簡略版）

変更に該当する項目のみ実施する。全項目を機械的に埋めない。

- [ ] **Injection**: SQL, Command, XSS の入力パスを確認
- [ ] **Broken Authentication**: 認証フロー・セッション管理の変更を確認
- [ ] **Sensitive Data Exposure**: secrets in code, logs, 環境変数を確認
  - 暗号化カラムを返す API: decrypt() / masking 処理が適用されているか確認
  - API レスポンスに暗号文（Base64 / hex 等の非可読文字列）が含まれていないか確認
- [ ] **Security Misconfiguration**: デフォルト設定・CORS・ヘッダーを確認
- [ ] **Vulnerable Dependencies**: 依存パッケージの既知脆弱性を確認

## Evidence Checklist（aegis 固有）

レビュー完了前に以下を全て実施する：

- [ ] Grep で secrets/credentials パターンを検索した
- [ ] 外部入力のサニタイゼーションを確認した
- [ ] dependency audit を実行した（該当する場合）
- [ ] 全 finding に severity と remediation を付与した

## Exit Criteria（aegis 固有）

- OWASP 該当項目の確認完了（非該当は理由付きでスキップ）
- 全 finding に severity 付与済み
- `docs/qa-reports/` にセキュリティレポートが存在する
- deploy blocker があれば STATUS.md に記録済み
- security gate 承認：`bash scripts/update-gate.sh security approve`

## 禁止事項（aegis 固有）

- スキャンなき PASS を出さない
- 「内部用だから安全」で省略しない
- severity 未付与の finding を報告しない

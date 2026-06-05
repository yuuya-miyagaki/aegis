---
name: aegis-review-gate
description: "Aegis review phase composite skill: invoke the official review skill, then layer aegis severity classification, traceability table, and gate contract."
disable-model-invocation: true
user-invocable: false
---

# Aegis Review Gate（合成スキル）

> Claude Code 公式 `review` スキルを基盤として呼び出し、その出力に aegis 固有の
> severity 分類・対照表・evidence checklist を重畳する合成スキル。
>
> v0.13.0 (Phase 0b): 公式同名スキルとの衝突を回避するため `review` から改名。
> 公式版が網羅する一般的コードレビュー観点は重複説明せず、aegis 固有の
> gate 連携・severity 規律・対照表ルールのみ記述する。

## Step 0: 公式 review スキルを呼び出す

```
Skill(skill="review")
```

返ってきた findings をベースに、以下の aegis 固有 Step を追加実行する。

## Severity 分類（aegis 固有）

| Severity | 定義 | 例 |
|----------|------|-----|
| Critical | 動作不正・データ破壊・セキュリティ穴 | 未処理例外、認証バイパス |
| Major | 品質劣化・保守性低下・仕様不整合 | テスト欠落、命名不統一、scope 超過 |
| Minor | 改善提案・コスメティック | コメント追加、リファクタ提案 |

全 finding にいずれかの severity を付与する。未分類の finding は報告しない。

## 対照表（必須出力、aegis 固有）

レビュー開始前に以下の対照表を作成し、レビューレポートに含める：

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|

- plan の全タスクを列挙する（漏れなく）
- 実装ファイルは `git diff --name-only` で取得
- 「未着手」のタスクがあれば FAIL 判定の根拠とする

## Evidence Checklist（aegis 固有）

レビュー完了前に以下を全て実施する：

- [ ] diff を Read/Grep で実読した（chat summary ではなく実ファイル）
- [ ] plan/spec の受入条件と突合した
- [ ] 未カバーのエッジケースを列挙した
- [ ] 全 finding に severity と confidence（1-10）を付与した

## Exit Criteria（aegis 固有）

- 全 finding に severity 付与済み
- PASS/FAIL 判定を明記（理由付き）
- `docs/qa-reports/` にレビューレポートが存在する
- confidence < 7 の finding には注意書きを付与済み
- review gate 承認：`bash scripts/update-gate.sh review approve`

## 禁止事項（aegis 固有）

- evidence なき PASS 判定を出さない
- diff を読まずにレビュー結果を出さない
- severity 未付与の finding を報告しない

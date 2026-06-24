---
name: aegis-brainstorm
description: "Aegis brainstorm phase composite skill: invoke the official brainstorming skill, then layer aegis gate contract (record/spec save, hard gate, STATUS update) on top."
disable-model-invocation: true
user-invocable: false
---

# Aegis Brainstorm（合成スキル）

> Claude Code 公式 `brainstorming` スキルを基盤として呼び出し、その出力を aegis の
> gate 契約（BRAINSTORM-RECORD / SPEC 保存 + gate 承認 + STATUS.md 更新）に
> 落とし込む合成スキル。
>
> v0.13.0 (Phase 0b): 公式同名スキルとの衝突を回避するため `brainstorming` から
> 改名。公式版が網羅する内容（質問グループ化、選択式優先、設計の一括提示、
> Mermaid 図、自己レビュー観点）は本ファイルで重複説明しない。aegis 固有の
> 適用基準・記録パス・gate 遷移のみ記述する。

## Step 0: 公式 brainstorming スキルを呼び出す

最初に Claude Code ビルトイン `brainstorming` スキルを呼び出して、設計判断の探索
プロセスを実行する：

```
Skill(skill="brainstorming")
```

返ってきた合意設計をベースに、以下の Aegis 固有 Step を追加実行する。

## 適用基準（aegis 固有）

| task_type | brainstorm | 理由 |
|---|---|---|
| `feature` | **必須** | 設計なき実装を防止する |
| `refactor` | **必須** | 影響範囲の事前合意が必要 |
| `bugfix` | skip 可 (`n/a`) | 原因特定と修正に集中する |
| `hotfix` | skip 可 (`n/a`) | 緊急対応を優先する |
| `framework` | **必須** | フレームワーク変更は影響範囲が広い |

skip する場合は `gate_approvals.brainstorm` を `n/a` に設定する（`bash scripts/update-gate.sh brainstorm na` 経由のみ。直接編集は禁止）。

## ハードゲート（aegis 固有）

> **適用対象のタスクでは、設計が承認されるまで実装スキル・コード記述・
> プロジェクト scaffold は禁止。** 「シンプルすぎる」は例外にならない。

## Step A: BRAINSTORM-RECORD 保存

公式 brainstorming スキルから得た合意・却下案・スコープ境界・未解決事項を
`docs/specs/YYYY-MM-DD-<topic>-brainstorm-record.md` に保存する：

- テンプレート: `templates/BRAINSTORM-RECORD.template.md`
- 簡潔に、設計ノートと重複する詳細実装説明は書かない

## Step B: SPEC 保存

公式 brainstorming スキルから得た最終設計を
`docs/specs/YYYY-MM-DD-<topic>-design.md` に保存する：

- テンプレート: `templates/SPEC.template.md`
- アーキテクチャ、コンポーネント、データフロー、エラー処理、テスト戦略を含む

## Step C: ユーザーレビューゲート

> 「設計ドキュメントを `<パス>` に保存しました。実装計画に進む前に内容を確認してください。」

ユーザーが変更を求めたら公式 brainstorming スキルから再実行する。承認されたら次へ。

## Step D: plan フェーズへ移行

1. `docs/STATUS.md` の `phase` を `plan` に更新
2. `task_size` を `bash scripts/update-task.sh --size <S|M|L>` で設定（raw Edit は
   post-status-audit が tamper として block する）し、`task_size_rationale` を記録
3. brainstorm gate 承認：`bash scripts/update-gate.sh brainstorm approve`

## コンテキスト予算

- L0 の `docs/STATUS.md` を起点に refs を pull する
- 既存コードの調査は必要最小限
- 記録は Step A で残す（公式 brainstorming スキル出力をそのまま dump しない）

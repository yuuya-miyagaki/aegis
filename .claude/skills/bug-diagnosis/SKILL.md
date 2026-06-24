---
name: bug-diagnosis
description: "Bug diagnosis process replacing brainstorm+plan for bugfix/hotfix tasks."
disable-model-invocation: true
user-invocable: false
---

# バグ診断

> バグ修正の前に、問題を正確に理解する。

## いつ使うか

- task_type = bugfix または hotfix のとき
- brainstorm を n/a にしてよい代わりに、このスキルを実行する
- **本番/運用起因の問題のとき（のみ）**: まず `maintenance` skill（Part B: トリアージ）を読み、重大度分類とルーティングを経てから本診断に入る。トリアージは1回で、本診断に入ったら maintenance には戻らない。解決後は `docs/handover/RUNBOOK.md` の `## インシデント履歴` に追記する。（通常の bugfix/hotfix は従来どおりで maintenance を通さない。）

## Gate 処理

このスキルは brainstorm と plan の代替として機能する。implement に進む前に:

1. `gate_approvals.brainstorm` → `n/a`（理由: bug-diagnosis で代替）
2. `gate_approvals.plan` → `n/a`（理由: 修正方針を Step 4 で決定済み）
3. STATUS.md の `next_action` に修正方針の要約を記録する
4. `task_size`/`task_type` の変更は `bash scripts/update-task.sh`（例: `--type bugfix --size S`）経由で行う（raw Edit は post-status-audit が tamper として block）。`task_size` を設定した場合は `task_size_rationale` に根拠を記録する

## プロセス

### Step 1: 再現確認

- 報告された症状を再現する
- 再現手順と実際の挙動を記録する
- 再現できない場合はユーザーに追加情報を求める

### Step 2: 原因特定

- エラーメッセージ/ログ/スタックトレースを読む
- 仮説を1つ立てる → 検証 → 違えば次の仮説（ReAct）
- 3回失敗ルール適用

### Step 3: 影響範囲

- 同じコードパスを通る他の機能を特定する
- 修正による副作用リスクを評価する

### Step 4: 修正方針決定

- 根本修正 vs 回避策を判断する
- 修正方針をユーザーに報告し承認を得る

### Step 5: implement へ移行

- STATUS.md を更新し implement に進む

## hotfix 簡略パス

task_type = hotfix の場合、上記プロセスを以下に簡略化する:

1. 影響範囲の即時評価（ユーザー影響の重大度）
2. ロールバック vs 前方修正の判断
3. 最小修正の実装（スコープを最小に絞る）
4. review → 本番適用
5. 後日、根本修正を bugfix として起票

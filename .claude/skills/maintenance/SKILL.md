---
name: maintenance
description: "Maintenance lifecycle. Generates the operations RUNBOOK at ship and runs the monitor->triage->route->record loop for production incidents."
disable-model-invocation: true
user-invocable: false
---
# 保守ライフサイクル

> 納品後の「運用・監視・インシデント対応」を担う。Part A は ship 段階で運用 RUNBOOK を生成し、
> Part B は運用中のインシデントをトリアージして既存の修正経路へ流し、記録してループを閉じる。
> 修正実行は新設せず `bug-diagnosis`・bugfix/hotfix を再利用する。
>
> **このスキルは Claude 側の手順書**（`user-invocable: false`）。運用者（非エンジニア）の入口は
> 成果物 `docs/handover/RUNBOOK.md` であり、運用者はこのスキルを起動しない。運用者に必要な情報は
> すべて RUNBOOK に出力する。

## いつ使うか
- **Part A（生成）**: docs フェーズで `ship-and-docs` の ship 段階（Step 2.6）から参照される。製品を運用する人がいる納品物のとき。
- **Part B（運用）**: 運用者から「製品が壊れた」とエスカレーションを受けた開発者が、`task_type=bugfix`（緊急時 `hotfix`）で Dev セッションを開いたとき。`bug-diagnosis` の本番/運用起因ケースから参照される。**主体は Claude**（運用者の一次対応・エスカレーション判断は RUNBOOK が担う）。
- 運用者がいない案件（閲覧専用で監視も更新もしない等）は RUNBOOK を生成せず理由を記録する。

## Part A: RUNBOOK 生成（ship 時）

### Step 1: 対象を決める
`docs/requirements/SCOPE.md`・`PRD.md`・TO-CLIENT の「配備と運用」・STATUS から、運用者の有無とデプロイ先/監視手段/エスカレーション先を判定し、ユーザーに確認する。運用者がいなければ生成せず理由を記録（下記「RUNBOOK が不要なとき」）。

### Step 2: RUNBOOK を記述
`templates/RUNBOOK.template.md` をもとに `docs/handover/RUNBOOK.md` を作成する。監視・トリアージ・エスカレーションを**平易語**（非エンジニアが読める語彙）で記述する。プレースホルダ（`<記入>`）を空のまま残さない。実際の監視インフラ設定（アラート構築等）は促すが必須化しない。**使い方・更新手順は `MANUAL.md` に集約し、RUNBOOK には書かない**（重複させない。RUNBOOK は異常検知と復旧に絞る）。

### Step 3: TO-CLIENT からリンク
`docs/handover/TO-CLIENT.md` の納品サマリーに `docs/handover/RUNBOOK.md` へのリンクを追加する。

### Step 4: 整合確認
`docs-sync` skill を読み、RUNBOOK.md の存在と必須節（監視/インシデント対応（トリアージ）/エスカレーション/インシデント履歴/用語）の充足を確認する。

## Part B: インシデント対応ループ（運用時）

### Step 1: シグナル確認
症状・影響範囲を把握する。`docs/handover/RUNBOOK.md` の `## 監視`・`## インシデント対応（トリアージ）` を読む。

### Step 2: 分類
RUNBOOK のトリアージ基準で重大度（高/中/低）とスコープを判定する。

### Step 3: ルーティング
- 操作者で対応可（RUNBOOK の手順内）→ 実施する。
- 開発が必要 → `task_type = bugfix`（緊急なら `hotfix`）として `bug-diagnosis` skill へ渡す。**トリアージはここで完了。bug-diagnosis の診断本体に入ったら maintenance には戻らない**（読み合いループを作らない）。

### Step 4: 記録
解決後、RUNBOOK の `## インシデント履歴` に 日付/事象/重大度/対応/恒久対策 を追記してループを閉じる。

## RUNBOOK が不要なとき
運用者がいない内部使い捨て等で不要な場合は、生成せず TO-CLIENT もしくは STATUS にその理由を1行記録する（「該当なし」を理由なく済ませない）。

## Red Flags（禁止事項）
- インシデントを履歴に残さず閉じる。
- 重大度判定（トリアージ）を飛ばして対応に入る。
- エスカレーションの線引きが不明なまま放置する。
- テンプレのプレースホルダを空のまま納品する。
- エンジニア用語を平易化せず素のまま使う。
- チャット履歴を成果物のソースにする（仕様/成果物/RUNBOOK が唯一のソース）。

## コンテキスト予算
- Part A: SCOPE/PRD＋TO-CLIENT 配備情報＋RUNBOOK テンプレのみ。
- Part B: RUNBOOK＋当該シグナル情報のみ。
- 過去のチャット履歴は参照しない。

---
name: user-manual
description: "End-user / operator manual generation. Audience-parameterized operation guide for the delivered product."
disable-model-invocation: true
user-invocable: false
---
# 操作マニュアル生成

> 納品物の操作マニュアルを非エンジニアが読める形で作る。docs フェーズで
> `ship-and-docs` skill の ship 段階（Step 2.5）から参照される。読者（利用者/運用者）
> ごとにタスク指向の手順を生成する。

## いつ使うか
- `ship-and-docs` の ship 段階で TO-CLIENT 作成後（Step 2.5）。
- 製品を使う/運用する人がいる納品物のとき。

## 前提条件
- 仕様が確定している（`docs/requirements/SCOPE.md`・`PRD.md`・`ACCEPTANCE.md`）。
- 出荷した機能が把握できている（review/qa 成果物）。

## 手順

### Step 1: 読者を決める
SCOPE/PRD と STATUS の `ui_surface` から該当読者を判定し、ユーザーに確認する:
- **end-user（利用者）**: 製品を使ってタスクを行う最終利用者。閲覧のみの製品（LP 等）にはいない。
- **operator（運用者）**: 発注者側でコンテンツ更新・基本設定を行う担当者。多くの納品物で該当。

確定した読者を、`templates/MANUAL.template.md` をもとに作る `docs/handover/MANUAL.md` の
front-matter `audiences` に宣言し、該当しない読者の章は削除する。front-matter の宣言と
本文の章は1対1に保つ（宣言を消したら章も消す。孤児章を残さない）。

### Step 2: タスクを抽出して手順化
SCOPE/PRD/ACCEPTANCE と出荷機能から、各読者の主要タスクを列挙する。
読者ごとに「〜するには」を**平易語**（非エンジニアが読める語彙）で記述する。
1タスク=1見出し＋番号付きステップ。専門語を使ったら用語章で言い換える。

### Step 3: 図（任意）
`ui_surface: true` かつ UI が存在する場合、`browser-assist`（または `qa-browser`）で
主要画面を撮り、該当手順に `![説明](パス)` で貼る。UI が無い/撮れない場合はプレースホルダを
残し、図不要の理由を1行記す。**図の自動取得は必須ではない。**

### Step 4: つまずいたら・用語
各章の「つまずいたら」（FAQ）と「用語」（平易化）を埋める。空欄を残さない。

### Step 5: TO-CLIENT からリンク
`docs/handover/TO-CLIENT.md` の納品物に `docs/handover/MANUAL.md` へのリンクを追加する。

### Step 6: 整合確認
`docs-sync` skill を読み、MANUAL.md の存在と宣言読者ごとの章充足を確認する。

## マニュアルが不要なとき
使う人も運用者もいない内部使い捨て等で不要な場合は、生成せず TO-CLIENT もしくは
STATUS にその理由を1行記録する（「該当なし」を理由なく済ませない）。

## Red Flags（禁止事項）
- 空の手順章を残す。
- エンジニア用語を平易化せず素のまま使う。
- 宣言した読者の章を欠落させる／宣言を消したのに孤児章を残す。
- 理由なく「マニュアル不要」と宣言する。
- チャット履歴を成果物のソースにする（仕様/成果物が唯一のソース）。

## コンテキスト予算
- SCOPE/PRD/ACCEPTANCE + 出荷機能一覧 + MANUAL テンプレのみ。
- 過去のチャット履歴は参照しない。

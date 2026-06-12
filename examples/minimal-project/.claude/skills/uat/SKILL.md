---
name: uat
description: "UAT execution. Client verifies the built product against ACCEPTANCE criteria and records pass/fail with sign-off before handback."
disable-model-invocation: true
user-invocable: false
---
# UAT（受入）実行

> ACCEPTANCE で定義した受入条件を、ビルド済み製品に対して client が実検証し合否を記録する。
> docs フェーズで `ship-and-docs` の ship 段階から、`dev_ready_for_client` 申請の前に参照される。
> 合否の最終判断は client のサインオフが正本（機械は UAT-RESULTS の存在のみ見る）。

## qa-verification との違い
`qa-verification` は Dev 内部 QA（テスト/lint/build を dev が実行）。UAT は client 視点の受入
（製品が ACCEPTANCE を満たすかを client が判定）。qa の結果は証拠として参照してよいが、
client 視点の確認を省略しない。

## いつ使うか
- `ship-and-docs` の ship 段階で、`dev_ready_for_client` 申請の前。
- `docs/requirements/ACCEPTANCE.md` がある案件のとき。ACCEPTANCE が無い案件は UAT 不要（理由記録）。

## 手順

### Step 1: 受入条件を読む
`docs/requirements/ACCEPTANCE.md` の各 AC とトレーサビリティ（検証方法: 自動テスト/手動確認/レビュー）を読む。

### Step 2: 実検証
ビルド済み製品に対し各 AC を検証する。UI は `browser-assist`（`.claude/skills/browser-assist/SKILL.md`）/`qa-browser` で実画面を確認、自動テストは qa 成果物の結果を参照。各 AC に 期待/実際/合否(✅/❌)/証拠 を記録する。

### Step 3: client サインオフ
結果を client（ユーザー）に提示し合否を確認する。Must の ❌ は bugfix/hotfix へ戻すか、client が理由付きで ack して受容する。

### Step 4: 保存とリンク
`templates/UAT-RESULTS.template.md` をもとに `docs/handover/UAT-RESULTS.md` を作成し、TO-CLIENT の納品サマリーからリンクする。

### Step 5: 整合確認
`.claude/skills/docs-sync/SKILL.md` を Read し、UAT-RESULTS の存在と全 Must-AC の合否・サインオフを確認する。

## UAT が不要なとき
ACCEPTANCE が無い（受入条件未定義の内部タスク等）案件は生成せず、TO-CLIENT もしくは STATUS に理由を1行記録する。

## Red Flags（禁止事項）
- ❌ を残したまま理由なくサインオフする。
- 証拠リンク無しで✅にする。
- ACCEPTANCE の AC を UAT-RESULTS から欠落させる。
- qa-verification（内部QA）の結果をそのまま UAT 合否として流用し、client 視点の確認を省く。
- チャット履歴を成果物のソースにする。

## コンテキスト予算
- ACCEPTANCE＋qa 成果物＋UAT テンプレのみ。過去チャットは参照しない。

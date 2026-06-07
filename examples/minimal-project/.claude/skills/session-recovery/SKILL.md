---
name: session-recovery
description: "Session recovery protocol for context loss, crashes, or work resumption."
disable-model-invocation: true
user-invocable: true
---

# セッション復帰

> コンテキスト切れ・クラッシュ・日をまたいだ作業再開時に、最小コストで状態を復元する。

## native との関係

前回セッションが残っていれば native `/resume` で会話が戻り、それで足りることもある。本 skill は
会話復元や `/rewind`（ファイル undo）とは別で、**会話が無いとき**（新規セッション・コンテキスト圧縮・
クラッシュ）や **STATUS.md に対して状態/partial を検証したいとき**に、`docs/STATUS.md` から
フレームワーク状態（phase/gates/refs/partial）を再構築する。会話＝`/resume`、状態台帳＝本 skill、と
棲み分ける（毎回両方必要というわけではない）。

## いつ使うか

- セッションがコンテキスト上限で圧縮・切断されたとき
- 前回のセッションから時間が空いたとき
- 「何をしていたか分からない」状態になったとき

## 復帰プロトコル

### Step 1: STATUS.md を読む

最初に `docs/STATUS.md` を読む。以下を確認:

- `mode` / `phase`: 現在の位置
- `next_action`: 直前のセッションが残した次のアクション
- `blockers`: 未解決の障害
- `gate_approvals`: どのゲートまで通過したか
- `session_history`: 最新エントリの内容

### Step 1.5: 運用健全性チェック

`python3 scripts/status_doctor.py --root .` を実行し、結果を確認する。

- WARNING: 復帰サマリに含めてユーザーに報告
- FAIL: gate を進めず、FAIL の解消を優先する（例: second-opinion.md の作成）

### Step 2: 現在のフェーズに必要な refs を読む

`current_refs` から、現在のフェーズに関連するドキュメントだけを読む。

| フェーズ | 読むべき refs |
|---|---|
| onboard, discovery | なし（requirements が未作成なら読まない） |
| requirements, scope, acceptance, handover | requirements |
| brainstorm | requirements, docs/LEARNINGS.md |
| plan | requirements, spec, docs/LEARNINGS.md |
| implement | plan, spec |
| review | plan, 変更 diff |
| qa | plan, review |
| security | plan, qa |
| ship | plan, review, qa, security, `docs/handover/TO-CLIENT.md` |
| docs | `docs/handover/TO-CLIENT.md`, `docs/LEARNINGS.md` |

**全 refs を読まない。** 現在のフェーズに必要なものだけ。

### Step 3: git 状態の確認

```bash
git status
git log --oneline -5
```

未コミットの変更、進行中のブランチ、ワークツリーを確認する。

### Step 4: partial artifact の判定

- `current_refs` にないファイルは、存在していても正本として扱わない
- `current_refs` にあるファイルでも、placeholder、未記入セクション、途中書きの
  findings、未承認の evidence があれば partial とみなす
- partial を見つけたら gate を進めず、修正するかユーザーに確認する

### Step 5: 復帰サマリの報告

ユーザーに以下を報告する:

```
復帰状態:
- モード: <mode>
- フェーズ: <phase>
- 次のアクション: <next_action>
- ブロッカー: <blockers or なし>
- 未コミット変更: <あり/なし>
```

ユーザーの確認を待ってから作業を再開する。

### イテレーション復帰（iteration > 1 の場合）

- `docs/LEARNINGS.md` の前回イテレーションで記録された教訓を確認する
- 前回の残留リスク・blockers が解消されているか確認する

### 外部レビュー証拠（external_evidence がある場合）

- `external_evidence` のエントリを確認し、未解決の findings がないか確認する
- current_refs が正式な phase artifacts を持たない場合、external_evidence が
  品質保証の代替根拠となる

## ルール

- STATUS.md の `next_action` を最優先で確認する
- 復帰時に新しいドキュメントを作成しない
- 不明な状態があればユーザーに質問する（推測しない）
- partial artifact を completion evidence として扱わない
- 復帰完了後、`session_history` に復帰エントリを追加する

## コンテキスト予算

- 復帰に使うのは STATUS.md + 現在フェーズの refs（最大2つ）
- 前回のチャット履歴は参照しない（STATUS.md が唯一の状態ソース）

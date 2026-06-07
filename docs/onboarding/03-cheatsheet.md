# aegis 早見表

手元に置いて使う1枚。困ったらまず **`/status`**（今どこ？）と **`/next`**（次なに？）。

---

## スラッシュコマンド（8）

| コマンド | 何をする |
|---|---|
| `/status` | 今のモード・フェーズ・ゲート状況・次アクションをまとめて表示 |
| `/gate` | ゲート一覧を表示し、承認操作の入口になる |
| `/judge` | judge カード（機械が見た事実 vs 申告）を読み取り専用でプレビュー |
| `/next` | 次に何をすべきか・フェーズ遷移を提案 |
| `/recover` | セッションが切れた／日をまたいだ時に状態を復元 |
| `/retro` | これまでの振り返りレポートを生成 |
| `/tutorial` | Dev フローの最短ウォークスルー |
| `/validate` | フレームワークの健全性を階層チェック |

---

## モードとフェーズ

aegis は2つのモードを行き来する。モード間の移動には**ハードゲート**が要る。

```
Client（何を作るか固める）
  onboard → discovery → requirements → scope → acceptance → handover
        │
        └─[ client_ready_for_dev を承認 ]→ Dev へ

Dev（品質を守りながら作る）
  brainstorm → plan → implement → review → qa → security → deploy → ship → docs
        │
        └─[ dev_ready_for_client を承認 ]→ Client へ返す（次の周回）
```

---

## ゲート（8）

承認は**順番**が強制される（前のゲートが未承認だと次は承認できない）。

| ゲート | 意味 |
|---|---|
| `client_ready_for_dev` | Client の成果（要件・受入・引き渡し）が揃い、Dev に入ってよい |
| `brainstorm` | 何を作るか／どう作るかの方針が固まった |
| `plan` | 実装計画ができた（**承認まではコードを書けない**） |
| `review` | レビュー合格（承認時に judge カードが自動生成される） |
| `qa` | 検証合格（承認時に**テスト強度ドリルが自動で走る**。`n/a` 不可） |
| `security` | セキュリティレビュー合格 |
| `deploy` | デプロイ準備完了（小さいタスクは `n/a` でよい） |
| `dev_ready_for_client` | Dev 完了。Client へ返せる（**受入条件があれば UAT 記録が必須**） |

### ゲート操作（`scripts/update-gate.sh`）

```bash
bash scripts/update-gate.sh <gate> approve      # 承認
bash scripts/update-gate.sh <gate> na           # 対象外にする（qa は不可）
bash scripts/update-gate.sh <gate> reset        # pending に戻す
bash scripts/update-gate.sh <gate> approve --ack "理由"   # 🟡（要確認）を理由つきで承認
```

承認時の signal: **🟢=そのまま承認可／🟡=要確認（--ack で承認）／🔴=機械事実と矛盾＝ブロック**。

---

## hook：なぜ止まるか（決定論的ガード）

hook は「お願い」ではなく**仕組み**で止める。代表的なもの:

| hook | いつ | どう止める |
|---|---|---|
| `check-gate` | コード編集時 | plan 未承認／Client モード中は **deny**（編集させない） |
| `check-tdd` | コード編集時（full のみ） | テスト変更が無い実装を **ask**（テスト先行を促す） |
| `check-client-info` | 要件編集時 | `docs/client/context.md` が無いと **deny** |
| `check-destructive` | Bash 実行時 | `rm -r`／`git push -f`／`DROP TABLE` 等を **ask** |
| `check-secrets` | Bash 実行時 | `.env`・鍵の `git add`/commit を **deny** |
| `check-task-created` | タスク作成時 | implement で plan 未承認なら新タスクを **hard stop** |
| `check-task-completed` | タスク完了時 | next_action 未更新／証拠不整合を **差し戻し** |

> deny=禁止／ask=確認を求める／hard stop=処理を止める／差し戻し=やり直しを促す。

---

## タスクサイズ早見

| サイズ | 規模 | ゲート |
|---|---|---|
| S | 1ファイル | review→ship（deploy は省略可） |
| M | 2〜5ファイル | deploy 省略 |
| L | 6ファイル以上 | 全ゲート |

- feature/refactor/framework: `review + qa + security + deploy` が基本。
- bugfix/hotfix: `review` のみ（`brainstorm`/`plan` は `n/a`。`bug-diagnosis` を使う）。

---

## 行き詰まったら

- `/recover` … 状態を復元（STATUS.md から phase/refs/未保存を再構築）。
- `/validate` … 健全性チェック。
- **同じ目標で3回失敗したら** … `docs/second-opinion.md` を書いて手を止め、別の視点（IDE チャット等）に相談する（3回失敗ルール）。

---

参照: コマンド一覧は `.claude/commands/`、ゲート定義は `.claude/rules/state-machine.md`、構造の深掘りは [`../architecture-overview.md`](../architecture-overview.md)。

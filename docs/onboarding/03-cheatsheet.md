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

### 🟡 を ack していい例／ダメな例（K-13 / v1.6.2）

「LLM が大丈夫って言ってるから」を根拠に ack 連打すると、judge カードの
「機械が見た事実」という安全装置を**人間側で無効化**する経路になる
（第6回レビュー JNY-12）。下表を基準に、あなた（オーナー）が事実を
読んで判断できるときだけ ack する。

| 状況 | ack 可否 | 理由 |
| --- | --- | --- |
| **qa**: テスト未記録（marker_verified=false） | ❌ 不可 | テストが実際に走ったかが機械的に未確認。`pytest -v` 等を実行→`record-test-result.py` で記録してから再判定 |
| **review**: 第2意見が未取得 + 規模 S（1 ファイル・差分 30 行未満） | ✅ 可 | state-machine 規約で省略可。影響が局所的 |
| **review**: 第2意見が未取得 + 規模 M / L | ❌ 不可 | 影響範囲が大きい変更は外部視点を取る（IDE chat / `second-opinion.md`） |
| **security**: 漏洩キー目視確認（`grep -rE 'sk-[A-Za-z0-9]{20,}'` 等）未実施 | ❌ 不可 | check-secrets が deny しなくても、自分で確認した記録を `docs/qa-reports/v*-security.md` に残してから ack |
| **deploy**: rollback 手順が `TBD` のまま | ❌ 不可 | 障害時の戻し手順が無いまま deploy は禁止。`RUNBOOK.md` / `DEPLOY-CHECKLIST.md` に具体手順を書く |

**根本ルール**: 判断が付かない 🟡 は止めて `second-opinion.md` を書く。
3 失敗で停止のルール（`CLAUDE.md` 完了条件）と整合する。

> 注: v1.6.1 まではテスト 0 件実行（`pytest -k __NEVER__` 等）も 🟡 で
> ack 可能だったが、v1.6.2 K-1 修正で `collected 0 items` 等を構造的に
> 検出して `marker_verified=false` 直行になるため、本表からは除外。

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

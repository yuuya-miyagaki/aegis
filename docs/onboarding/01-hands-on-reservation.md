# はじめての aegis プロジェクト — 予約管理システム

aegis を**手を動かして1周**体験するハンズオン。題材は社内の**予約管理システム**
（会議室予約・備品予約・カレンダー連携・フロアマップ表示・サービス依頼〔呈茶・アテンド〕）。

> **この本の読み方（大事）**
> aegis は Claude Code の中で動く。ここに書くのは、あなたが Claude と協働するときの**意図する流れ**で、
> 実際の Claude の文言や細部はセッションごとに多少変わる。「打つコマンド」と「なぜそこで止まるか」を
> つかむことが目的。完璧に同じ出力を目指さなくてよい。

## このハンズオンで体験すること

- **Client → Dev → UAT → handover → 保守** を1周する。
- 題材は中規模システムだが、**全体は"設計"し、実際に"作る"のは「会議室予約の重複チェック」1スライスだけ**に絞る。
  残りの機能（備品・カレンダー連携・フロアマップ・サービス依頼）は「次のイテレーション」に回す。
- 各段で、どの**ゲート**で止まり、どの**hook**が効くかを体で覚える。

## 前提

- Claude Code が使えること。
- 手元に `aegis` リポジトリがあること。

---

## 0. 準備

使い捨てのデモプロジェクトを作る。

```bash
# aegis リポジトリの中で実行
bash bin/setup.sh --profile=full --target=../reserve-demo
```

`--profile=full` を使う理由：全 hook・全スキル・`/judge`・`status_doctor` が入った"全部入り"になるから。

次に **git を初期化する（必須）**：

```bash
cd ../reserve-demo
git init && git add -A && git commit -m "scaffold"
```

> なぜ必須か：TDD チェックの hook（`check-tdd`）は「テストを変更したか」を **git の差分**で見る。
> git が無いと、テストを先に書いても hook がそれに気づけず確認を求め続け、TDD の体験が成立しない。

この `reserve-demo` ディレクトリで Claude Code を開き、最初にこう打つ：

```
/status
```

`mode: Client` / `phase: onboard` から始まることを確認する。これが「今どこにいるか」を見る基本動作。

---

## 1. Client モード（何を作るかを固める）

aegis はまず **Client モード**で「作る前の合意」を作る。ここは非エンジニアの主戦場。

Claude にこう頼む：

> 「予約管理システムを作りたい。`client-workflow` に沿って onboard から進めて。」

### onboard / discovery — 背景を固める
Claude（`client-workflow` スキル）が背景・利用者（社員／受付／総務）・困りごとをヒアリングし、
まず `docs/client/context.md` を埋める。

> **体験ポイント①**：context.md が無いまま要件を書こうとすると、`check-client-info` hook が
> 要件の編集を **拒否（deny）** する。だから「誰のため・何のため」を先に固めさせられる。

### requirements — 要件を書く
`docs/requirements/PRD.md` にシステム全体を書く（会議室・備品・カレンダー連携・フロアマップ・
サービス依頼〔呈茶・アテンド〕の5領域）。

### scope — 範囲を絞る
`docs/requirements/SCOPE.md` と `NFR.md` を作る。ここで宣言する：

> 「初回イテレーションは**会議室予約**に絞る。重複予約を防ぐところから作る。」

これが aegis の現実的な進め方（大きいものは小さく切って回す）。

### acceptance — 受入条件を決める
`docs/requirements/ACCEPTANCE.md` に「完成とみなす条件」を書く。例：

- 同一会議室・重複する時間帯の予約は**拒否される**。
- 別室、または時間が重ならない予約は**通る**。

### handover — Dev へ引き渡す
`docs/handover/TO-DEV.md` に、Dev が実装に着手できる形でまとめる。

### モードを移す
`/gate` で状況を確認し、Client の関所を承認する：

```bash
bash scripts/update-gate.sh client_ready_for_dev approve
```

`/status` を見ると **`mode: Dev` / `phase: brainstorm`** に切り替わっている。

> **体験ポイント②**：ここまで Client モードでは、コードを編集しようとしても `check-gate` hook が
> **拒否（deny）** する。「まだ作らせない。先に何を作るか固めろ」という仕組み。

---

## 2. Dev モード（品質を守りながら作る）

### brainstorm — 方針
Claude（`aegis-brainstorm`）と「重複チェックをどう判定するか」を詰める。決まったら承認：

```bash
bash scripts/update-gate.sh brainstorm approve
```

### plan — 実装計画
`docs/plans/` に計画を書く。例：「関数 `is_conflict(existing, new)` を作る。同一会議室で
時間帯が重なれば `True`、そうでなければ `False`」。承認：

```bash
bash scripts/update-gate.sh plan approve
```

> **体験ポイント③**：plan を承認するまで、コードを書こうとすると `check-gate` が **拒否** する。
> 「計画なしに実装するな」という仕組み。

### implement — TDD で作る（言語は Python）
`tdd` スキルに沿って、**テストを先に書く**。例：

- `tests/test_reservation.py`：同一室・重複時間で `True`、別室や非重複で `False` を期待する**失敗テスト**。
- 失敗を確認 → `reservation.py` に `is_conflict()` を実装 → テストが通る（green）。

> **体験ポイント④**：テストを書かずに `reservation.py` を編集しようとすると、`check-tdd` hook が
> **確認を求める（ask）**。先にテストを書いてコミット（git があるので差分が見える）すれば、すんなり進む。
> これが「テスト先行（TDD）」を体で覚える瞬間。

### review — レビュー
`aegis-review-gate` ＋ reviewer エージェントでフレッシュな目で確認し、承認：

```bash
bash scripts/update-gate.sh review approve
```

> **体験ポイント⑤**：承認の瞬間に `build-judge-card.py` が**自動で走り**、judge カード
> （`docs/qa-reports/judge-review.md`）が出る。🟢ならそのまま承認、🟡（要確認）なら理由を添えて：
> `bash scripts/update-gate.sh review approve --ack "確認した理由"`。🔴 は機械事実と矛盾＝ブロック。

### qa — 検証（テスト強度ドリル）
`qa-verification` スキルが、`docs/qa-reports/test-strength.drill`（mutant 入りの仕様）を**作ってくれる**。
あなたは中身を確認するだけでよい（手書きは不要）。承認：

```bash
bash scripts/update-gate.sh qa approve
```

> **体験ポイント⑥**：承認の瞬間に **テスト強度ドリル**（`run-test-strength-drill.py`）が**自動で走る**。
> わざとコードに埋めた欠陥（mutant）をテストが全部捕まえないと、**承認が拒否される**。
> 「テストを書いたフリ」ができない仕組み。なお **qa は `n/a` にできない**（必ずドリルを通す）。

### security — セキュリティ
`aegis-security-gate` で確認し、承認：

```bash
bash scripts/update-gate.sh security approve
```

### deploy / ship — 仕上げ
今回のスライスは小さい（数ファイル）ので **deploy は対象外**にする：

```bash
bash scripts/update-gate.sh deploy na
```

`ship-and-docs` で締める。

> **体験ポイント⑦**：ゲートは**順番が強制**される。例えば brainstorm 未承認のまま plan を承認しようとすると
> 拒否される。関所は飛ばせない。

---

## 3. UAT（受入テスト）

`uat` スキルで、`ACCEPTANCE.md` の条件を1つずつ実際に確かめ、結果を
`docs/handover/UAT-RESULTS.md` に pass/fail ＋ 証拠つきで記録する。

そのうえで Client へ返す関所を承認しようとすると：

```bash
bash scripts/update-gate.sh dev_ready_for_client approve
```

> **体験ポイント⑧**：受入条件（ACCEPTANCE）があるのに UAT-RESULTS をまだ書いていない段階では、
> この承認は **拒否される**（「先に受入テストをやれ」）。UAT を記録してから承認すると通る。

---

## 4. handover（引き渡し）

`ship-and-docs` が、Client 向けの引き渡し一式を作る：

- `docs/handover/TO-CLIENT.md` … 何を作ったかのサマリ。
- `docs/handover/MANUAL.md`（`user-manual` スキル）… 受付／総務など**使う人向けの操作手順**。
- `docs/handover/RUNBOOK.md`（`maintenance` スキル Part A）… 監視・トリアージ・エスカレーションの運用手順。

---

## 5. 保守（本番運用）

ここからが「作って終わりにしない」aegis の真価。本番でこんな不具合が出たとする：

> **「23:00〜翌1:00 のような日をまたぐ予約だと、重複チェックが漏れて二重予約できてしまう」**

`maintenance` スキル Part B に沿って対応する：

1. `bug-diagnosis` で原因を特定（`is_conflict` が日付跨ぎを考慮していない）。
2. **失敗する再現テストを先に追加** → 修正 → green（bugfix）。
   - bugfix は `brainstorm`/`plan` が `n/a`、`review` が必須（早見表のタスク種別を参照）。
3. `RUNBOOK.md` の**インシデント履歴**に「事象・原因・対処・再発防止」を記録。

---

## 6. 次のイテレーション

`dev_ready_for_client` を承認して Client へ返したら、次の周回が始まる：

- 新しいタスクで `phase` は `brainstorm` にリセットされ、Dev のゲートは `pending` に戻り、`iteration` が増える。
- 残りの機能（**備品予約 → カレンダー連携 → フロアマップ → サービス依頼〔呈茶・アテンド〕**）を、
  同じ Client→Dev→UAT→保守 の型で1つずつ回していく。

これで、**中規模システムを"小さく切って・品質を守りながら・保守まで"回す**という aegis の全体像を1周で体験できた。

---

## 困ったとき

- `/recover` … セッションが切れた／日をまたいだら、状態を復元する。
- `/status`・`/next` … 「今どこ？」「次なに？」をいつでも確認。
- 同じ目標で**3回失敗**したら、`docs/second-opinion.md` を書いて手を止め、別の視点に相談する（3回失敗ルール）。

用語に迷ったら → [`03-cheatsheet.md`](03-cheatsheet.md)／人に説明するなら → [`02-explainer.md`](02-explainer.md)

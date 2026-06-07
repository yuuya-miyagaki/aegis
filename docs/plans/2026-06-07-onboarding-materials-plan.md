# aegis オンボーディング教材 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 非エンジニア向けの aegis オンボーディング教材3点（フルサイクル・ハンズオン／説明ペラ／早見表）＋索引を `docs/onboarding/` に作り、README から導線を張る。

**Architecture:** 散文ドキュメント。コードではないので TDD の代わりに「**実体照合**（コマンド/hook/ゲート/skill 名が現行 v1.3.2 と一致するか）」を各タスクの verify ステップに据える。事実の正本は本計画に埋め込み済み＋実ファイルで確認する。reference（README/architecture-overview）とは重複させず、要約＋リンクで済ます。

**Tech Stack:** Markdown（日本語）。検証は `ls` / `grep` / 既存 scripts の存在確認のみ。

---

## 設計書

`docs/plans/2026-06-07-onboarding-materials-design.md` を必ず先に読むこと。

## 正本データ（全タスク共通で参照する事実・v1.3.2）

**スラッシュコマンド（8）**: `/status`(状態サマリ) `/gate`(ゲート一覧・承認) `/judge`(judge カード読取専用) `/next`(次アクション提案) `/recover`(セッション復帰) `/retro`(レトロ生成) `/tutorial`(Dev flow walkthrough) `/validate`(階層評価実行)

**ゲート（8・承認順の前提あり）**: `client_ready_for_dev`(Client→Dev 遷移) → Dev: `brainstorm` → `plan` → `review` → `qa` → `security` → `deploy` → `dev_ready_for_client`(Dev→Client 返却。ACCEPTANCE があれば UAT-RESULTS 存在を要求)

**モード/フェーズ**: Client = `onboard → discovery → requirements → scope → acceptance → handover`／Dev = `brainstorm → plan → implement → review → qa → security → deploy → ship → docs`

**主要 hook と「なぜ止まるか」**:
- `check-gate.sh` (Edit/Write): plan ゲート未承認でコード編集を **deny**／Client モード中の編集を deny
- `check-tdd.sh` (Edit/Write・full のみ): テスト変更なしの実装を **ask**（`AEGIS_TDD_MODE=off` で無効化）
- `check-destructive.sh` (Bash): `rm -r`/`git push -f`/`DROP TABLE` 等を **ask**
- `check-secrets.sh` (Bash): `.env`・鍵の `git add`/commit を **deny**
- `check-task-created.sh` (TaskCreated): phase=implement で plan 未承認なら新タスクを **hard stop**
- `check-task-completed.sh` (TaskCompleted): next_action 未更新／evidence 不整合を **exit 2 差し戻し**

**ゲート操作（`scripts/update-gate.sh <gate> [approve|na|reset]`）**: `approve`(承認)／`na`(対象外)／`reset`(pending に戻す)／🟡 は `approve --ack "理由"` で承認。

**タスクサイズ**: S=1ファイル / M=2-5 / L=6+。feature/refactor/framework は review+qa+security+deploy 必須（S は deploy 省略可、M は deploy 省略）。bugfix/hotfix は review；brainstorm+plan=n/a。

**ハンズオンで使う skill**: client-workflow / aegis-brainstorm / tdd / aegis-review-gate / qa-verification / aegis-security-gate / ship-and-docs / uat / user-manual / maintenance / bug-diagnosis / docs-sync / session-recovery。

**scaffold コマンド**: `bash bin/setup.sh --profile=full --target=<tmp>`（full は全 hook・全 skill・全 agent・status_doctor・judge を配布）。

**題材（予約管理システム）**: 機能領域＝会議室予約／備品予約／カレンダー連携／フロアマップ表示／サービス依頼（呈茶・アテンド）。Dev で建てる1スライス＝**会議室予約の重複チェック**（同一室・時間帯の二重予約を弾く判定）。保守の本番バグ例＝**日跨ぎ予約（23:00–翌1:00 等）で重複検知が漏れる**。

**成果物テンプレが生む artifact**: PRD/SCOPE/NFR/ACCEPTANCE(docs/requirements)、TO-DEV/TO-CLIENT/MANUAL/RUNBOOK/UAT-RESULTS(docs/handover)、PLAN(docs/plans)、SPEC(docs/specs)、REVIEW/QA-REPORT/SECURITY-REVIEW(docs/qa-reports)。

---

## File Structure

- Create: `docs/onboarding/README.md` — 索引（3教材への入口・読む順）
- Create: `docs/onboarding/01-hands-on-reservation.md` — フルサイクル・ハンズオン（中心・最長）
- Create: `docs/onboarding/02-explainer.md` — 非エンジニア向け説明ペラ
- Create: `docs/onboarding/03-cheatsheet.md` — コマンド/ゲート/hook 早見表
- Modify: `README.md` — Quick Start 付近に「はじめに（オンボーディング）」リンク1行

実装順: 早見表(③)→説明ペラ(②)→ハンズオン(①)→索引→README リンク→最終照合。③が事実の backbone なので先に作る。

---

### Task 1: 早見表 `03-cheatsheet.md`

**Files:**
- Create: `docs/onboarding/03-cheatsheet.md`

- [ ] **Step 1: ファイルを作成し、以下の節を日本語で書く**

見出しと内容（上記「正本データ」の値をそのまま使う）:
1. `# aegis 早見表` ＋ 1行イントロ（「困ったら `/status` と `/next`」）。
2. `## スラッシュコマンド` — 8コマンドの表（コマンド｜何をする）。
3. `## モードとフェーズ` — Client / Dev のフェーズ列を矢印で図示。
4. `## ゲート` — 8ゲートの表（ゲート｜意味｜承認順の位置）。`dev_ready_for_client` は「ACCEPTANCE があれば UAT-RESULTS 必須」を注記。
5. `## ゲート操作` — `update-gate.sh <gate> approve|na|reset` と `approve --ack "理由"`（🟡 の時）。前提ゲート未承認だと approve が拒否される旨。
6. `## hook：なぜ止まるか` — 主要 hook（check-gate/check-tdd/check-destructive/check-secrets/check-task-created/check-task-completed）を「いつ・どう止める（deny/ask/hard stop/差し戻し）」の表で。
7. `## タスクサイズ` — S/M/L とゲート省略の早見。
8. `## 行き詰まったら` — `/recover`（復帰）、3回失敗ルール（second-opinion.md）、`/validate`（健全性）。

- [ ] **Step 2: 事実照合**

Run: `cd <repo> && ls .claude/commands/ && ls .claude/skills/ && grep -n "Valid gates" scripts/update-gate.sh`
Expected: コマンド8件・skill 18件・ゲート名一覧が早見表の記述と一致すること。齟齬があれば早見表を実体に合わせる。

- [ ] **Step 3: Commit**

```bash
git add docs/onboarding/03-cheatsheet.md
git commit -m "docs(onboarding): add commands/gates/hooks cheatsheet"
```

---

### Task 2: 説明ペラ `02-explainer.md`

**Files:**
- Create: `docs/onboarding/02-explainer.md`

- [ ] **Step 1: ファイルを作成し、非エンジニア向けに以下を書く**

1. `# aegis をひと言で説明する`。
2. `## ひと言` — 1文ピッチ。例:「**作る前に何を作るか固め、品質チェックを飛ばせない形で、上流から保守まで一貫して AI と作るための運用ルール**」。
3. `## たとえ` — 工事現場の「**監督＋検査官**」: 設計図の承認前に着工させない／各工程の検査に合格しないと次へ進ませない。AI が勝手に手順を飛ばすのを"仕組み"で止める、と説明。
4. `## なぜ価値があるか（3点）` — (a) 上流から固める（要件・スコープ・受入を先に言語化）／(b) 品質ゲートで非スラップ（テスト・レビュー・セキュリティを承認しないと進めない）／(c) 保守まで一貫（手順書 RUNBOOK・UAT まで型がある）。
5. `## ただの「AI 任せ」との違い` — aegis は決定論的 hook（Policy as Code）で「人の確認なしに飛ばす」を**物理的に**止める（お願いベースの指示と違い、無視できない）。例: テスト未承認でコードを書こうとすると hook が deny する。
6. `## 30 秒トーク` — そのまま読める台本（3〜4文）。
7. `## 3 分版の流れ` — ①課題（AI 任せは抜け漏れ/スラップ）→②仕組み（モード＋ゲート＋hook）→③体験（ハンズオンに誘導）。
8. `## 刺さる相手` — 企画・クライアント・非エンジニアで「実物を作りたいが品質と段取りが不安な人」。
9. 末尾に「まず触ってみる → `01-hands-on-reservation.md`」リンク。

- [ ] **Step 2: 事実照合**

Run: `grep -rn "permissionDecision" hooks/check-tdd.sh hooks/check-gate.sh`
Expected: 「テスト未承認/plan 未承認で deny/ask する」という説明が実 hook の挙動（emit_deny/emit_ask）と一致すること。

- [ ] **Step 3: Commit**

```bash
git add docs/onboarding/02-explainer.md
git commit -m "docs(onboarding): add non-engineer explainer one-pager"
```

---

### Task 3: ハンズオン `01-hands-on-reservation.md`

**Files:**
- Create: `docs/onboarding/01-hands-on-reservation.md`

- [ ] **Step 1: 冒頭（狙い・前提・準備）を書く**

1. `# はじめての aegis プロジェクト — 予約管理システム`。
2. `## このハンズオンで体験すること` — Client→Dev→UAT→handover→保守 を1周。題材は中規模予約システムだが、**全体は設計し、実装は「会議室予約の重複チェック」1スライスに絞る**（残りは次イテレーション）と明記。
3. `## 前提` — Claude Code が使えること、`aegis` repo があること。
4. `## 0. 準備` — `bash bin/setup.sh --profile=full --target=../reserve-demo` で scaffold → そのディレクトリで Claude Code を開く → `/status` で現在地（mode=Client, phase=onboard）を確認。「full を使う理由＝全 hook/skill/judge/status_doctor が入る」を1行。

- [ ] **Step 2: Client モード節を書く**

`## 1. Client モード（何を作るか固める）`。各フェーズで「Claude にこう頼む／何が起きる／どの artifact ができる」を記述:
- onboard/discovery: `client-workflow` skill が起動。予約システムの背景・利用者（社員/受付/総務）をヒアリング。
- requirements: `docs/requirements/PRD.md` に5機能領域（会議室・備品・カレンダー連携・フロアマップ・サービス依頼〔呈茶/アテンド〕）を記述。
- scope: `docs/requirements/SCOPE.md` / `NFR.md`。**初回スコープを「会議室予約」に絞る**と宣言（aegis のタスクサイズ運用）。
- acceptance: `docs/requirements/ACCEPTANCE.md` に受入条件（例「同一会議室・重複時間帯の予約は拒否される」）。
- handover: `docs/handover/TO-DEV.md`。
- ゲート: `/gate` で確認 → `bash scripts/update-gate.sh client_ready_for_dev approve` → **mode が Dev に切り替わる**のを `/status` で確認。
- 体験ポイント: 「Client モード中はコード編集が `check-gate.sh` で **deny** される（まだ作らせない）」。

- [ ] **Step 3: Dev モード節を書く**

`## 2. Dev モード（品質ゲートで守りながら作る）`:
- brainstorm: `aegis-brainstorm`。重複チェックの方針を詰め、`bash scripts/update-gate.sh brainstorm approve`。
- plan: `docs/plans/` に実装計画（重複判定関数 `is_conflict(existing, new)` の仕様）。`update-gate.sh plan approve`。**plan 承認まではコードを書けない**（`check-gate.sh` が deny）ことを体験。
- implement: `tdd` skill。**失敗テストを先に書く**（同一室・重複時間で True、別室や非重複で False）。`check-tdd.sh` が「テスト無し実装」を **ask** するのを体験。テスト→実装→green。
- review: `aegis-review-gate` ＋ reviewer agent。`update-gate.sh review approve`（このとき `build-judge-card.py` が走り tri-state カードが出る。🟡 なら `approve --ack "理由"`）。
- qa: `qa-verification`。`update-gate.sh qa approve` で **B1 テスト強度ドリル**（`run-test-strength-drill.py`）が走り、mutant をテストが捕まえないと拒否されるのを体験。
- security: `aegis-security-gate`。`update-gate.sh security approve`。
- ship: `ship-and-docs`。タスクサイズ M なら deploy は省略可（早見表参照）。
- 体験ポイント: 各承認は前提ゲート順を強制（brainstorm 未承認で plan approve は拒否）。

- [ ] **Step 4: UAT・handover・保守・次反復 節を書く**

`## 3. UAT（受入テスト）`: `uat` skill で `ACCEPTANCE.md` を1項目ずつ照合し `docs/handover/UAT-RESULTS.md` に pass/fail＋証拠を記録。`update-gate.sh dev_ready_for_client approve` を試すと、**ACCEPTANCE があるのに UAT-RESULTS が無い段階では拒否**される（先に UAT を書く）ことを体験。

`## 4. handover（引き渡し）`: `ship-and-docs` が `docs/handover/TO-CLIENT.md`、`user-manual` が `MANUAL.md`（受付/総務向け操作手順）、`maintenance` Part A が `RUNBOOK.md`（監視・トリアージ・エスカレーション）を生成。

`## 5. 保守（本番運用）`: 本番バグ「**日跨ぎ予約で重複検知が漏れる**」を題材に、`maintenance` Part B → `bug-diagnosis` → bugfix（失敗テスト追加→修正）→ `RUNBOOK.md` のインシデント履歴に記録。bugfix は brainstorm+plan=n/a・review 必須（早見表参照）。

`## 6. 次のイテレーション`: 備品予約／カレンダー連携／フロアマップ／サービス依頼は次の周回へ。`dev_ready_for_client` 承認後に新タスクで brainstorm にリセット・iteration インクリメント、と説明。

`## 困ったら`: `/recover`（復帰）、`/status`・`/next`、3回失敗で second-opinion。

- [ ] **Step 5: 事実照合（実体と齟齬しないか）**

Run: `cd <repo> && for s in client-workflow aegis-brainstorm tdd aegis-review-gate qa-verification aegis-security-gate ship-and-docs uat user-manual maintenance bug-diagnosis session-recovery; do test -d .claude/skills/$s && echo "$s ok" || echo "$s MISSING"; done && ls scripts/run-test-strength-drill.py scripts/build-judge-card.py scripts/update-gate.sh bin/setup.sh`
Expected: 全 skill が ok・全 script/コマンドが存在。MISSING があればハンズオンの該当箇所を実体に合わせて修正。

- [ ] **Step 6: Commit**

```bash
git add docs/onboarding/01-hands-on-reservation.md
git commit -m "docs(onboarding): add full-cycle hands-on (reservation system)"
```

---

### Task 4: 索引 `docs/onboarding/README.md`

**Files:**
- Create: `docs/onboarding/README.md`

- [ ] **Step 1: 索引を書く**

1. `# aegis オンボーディング`。
2. 1段落: この3点が「使い方を習得する／他者に説明する」ための入口だと述べる。
3. 読む順の表:
   - はじめに説明を掴む → `02-explainer.md`
   - 実際に1周回す → `01-hands-on-reservation.md`
   - 手元参照 → `03-cheatsheet.md`
4. 「深掘りは `../architecture-overview.md`、導入は `../../README.md` の Quick Start」へのリンク。

- [ ] **Step 2: リンク健全性確認**

Run: `cd docs/onboarding && ls` and confirm the 4 files referenced exist (README, 01, 02, 03).
Expected: 4ファイル存在。リンク先のファイル名が一致。

- [ ] **Step 3: Commit**

```bash
git add docs/onboarding/README.md
git commit -m "docs(onboarding): add index"
```

---

### Task 5: README から導線リンク

**Files:**
- Modify: `README.md`（`## Quick Start` 見出しの直前または直後に1行リンクを追加）

- [ ] **Step 1: README に導線を1行足す**

`## Quick Start` セクションの冒頭に、次の1行を追加する（既存文を壊さない）:

```markdown
> 🚀 はじめての方は **[オンボーディング教材](docs/onboarding/README.md)**（説明・ハンズオン・早見表）から。
```

- [ ] **Step 2: 全層 green 確認（README は contract が検証する）**

Run: `python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_reference_drift.py && python3 scripts/run_eval.py --tier 0`
Expected: 全て PASS（README の必須トークン・パスを壊していないこと）。

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: link onboarding materials from README Quick Start"
```

---

### Task 6: 最終照合（全教材 × 実体）

**Files:**（変更なし・確認のみ。齟齬があれば該当ファイルを修正して追加コミット）

- [ ] **Step 1: 教材内のコマンド/ゲート/skill/hook 名が実体に全一致するか grep 照合**

Run:
```bash
cd <repo>
# 教材が言及する skill が全て実在するか
grep -rohE "(aegis-[a-z-]+|client-workflow|tdd|qa-verification|ship-and-docs|uat|user-manual|maintenance|bug-diagnosis|session-recovery|docs-sync)" docs/onboarding/ | sort -u | while read s; do test -d .claude/skills/$s && echo "$s ok" || echo "$s MISSING(or alias)"; done
# 教材が言及するゲート名が update-gate.sh の Valid gates と一致するか
grep -oE "client_ready_for_dev|dev_ready_for_client|brainstorm|plan|review|qa|security|deploy" docs/onboarding/*.md | sort -u
```
Expected: skill は全 ok（MISSING なら誤記＝修正）。ゲート名は8種に収まる。

- [ ] **Step 2: 全層 green 最終確認**

Run: `python3 scripts/run_eval.py --tier 0 && python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_reference_drift.py && python3 scripts/check_status.py --root . --strict`
Expected: 全 PASS（教材追加で既存契約を壊していないこと）。

- [ ] **Step 3: 齟齬があれば修正コミット**

```bash
git add docs/onboarding/
git commit -m "docs(onboarding): align wording with live v1.3.2 surfaces"
```
（齟齬ゼロなら本コミットは不要）

---

## Self-Review

- **Spec coverage**: 設計書の3成果物（①ハンズオン／②説明ペラ／③早見表）＋索引＋README リンク＋正確性担保（実体照合）を、Task 1-6 が全てカバー。フルサイクル（Client→Dev→UAT→handover→保守→次反復）は Task 3 の Step 2-4 が網羅。
- **Placeholder scan**: 各タスクに具体的な節構成・埋め込む正本データ・実行する照合コマンドを明記済み（TBD なし）。散文ゆえコード片の代わりに「節見出し＋入れる事実」を提示。
- **Type/name consistency**: skill 名（aegis-* 改名後）、ゲート8種、コマンド8種、hook 名を全タスクで「正本データ」節の表記に統一。Task 6 で実体 grep 照合し最終担保。
- 注: example/mirror への影響なし（docs/onboarding は framework-repo メタ文書・契約/ミラー対象外）。version 変更なし。

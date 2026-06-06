# B3a 読者パラメータ化マニュアル生成 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 納品物の操作マニュアルを、読者（利用者/運用者）パラメータ化された1テンプレ＋`manual` skill で非エンジニア向けに生成できるようにする（監査能力⑨の充足）。

**Architecture:** 新テンプレ `MANUAL.template.md`（front-matter `audiences` で読者宣言・読者ごとに手順章）と新 pull-based skill `manual`（生成手順）を追加。`ship-and-docs` の ship 段階から参照し（Step 2.5）、`docs-sync` に整合チェックを1項目追加する。hook ゲート/新フェーズ/`current_refs` キーは作らない（advisory）。

**Tech Stack:** Markdown テンプレ／Claude Code skills（`disable-model-invocation: true`）／`check_framework_contract.py`・`check_reference_drift.py`・`test_mirror_identity.py`・`eval_scaffold_smoke.py` による構造的検証。

> **テスト方針（重要）:** B3a は実行コードを持たない（テンプレ＝静的 md、skill＝LLM 向け手順）。よって Python ユニットテストは無い。各タスクの検証は **登録整合チェック（contract / drift / mirror-identity / scaffold-smoke）の green** と内容目視。spec `docs/plans/2026-06-07-v1-b3a-manual-generation-design.md` 参照。

---

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `templates/MANUAL.template.md` | 読者パラメータ化マニュアルテンプレ | 新規 |
| `.claude/skills/manual/SKILL.md` | マニュアル生成手順 | 新規（+example ミラー） |
| `.claude/skills/ship-and-docs/SKILL.md` | ship 段階に Step 2.5 追加 | 改修（+mirror） |
| `.claude/skills/docs-sync/SKILL.md` | 整合チェック1項目追加 | 改修（+mirror） |
| `scripts/check_framework_contract.py` | テンプレ/スキル/example を必須登録 | 改修 |
| `templates/profiles/full.json` | `manual` skill を recommended に登録 | 改修 |
| `CLAUDE.md` | Skills 一覧に `manual` 追加 | 改修 |
| `docs/architecture-overview.md` | §6 スキル表に `manual` 追加（非強制・任意） | 改修 |

> ミラー注: テンプレ（`templates/`）は example にミラーしない（example に templates/ は無い）。`.claude/skills/` 配下は MIRROR_DIRS なので `manual` 新設と `ship-and-docs`/`docs-sync` 改修を `examples/minimal-project/.claude/skills/` へ byte 同一でコピーする。`MANUAL.template.md` は full.json に載せない（full.json はテンプレを列挙しない）。

---

## Task 1: MANUAL.template.md（読者パラメータ化テンプレ）

**Files:**
- Create: `templates/MANUAL.template.md`

- [ ] **Step 1: テンプレを作成**

以下の内容で `templates/MANUAL.template.md` を作成する:

```markdown
---
audiences: [end-user, operator]
product: "<記入>"
release: "<記入>"
date: "<記入>"
---
# <製品名> 操作マニュアル
<!-- 正本: manual skill -->
<!-- exit-check: 宣言読者ごとに手順章あり・図 or 図不要理由・つまずいたら/用語記入済み -->

> このマニュアルは製品を「使う / 運用する」人向けの操作手順です。技術的な完了報告は
> `TO-CLIENT.md` を参照してください。front-matter の `audiences` に該当読者だけを残し、
> 不要な読者章は削除してください（利用者がいない閲覧専用サイトなら end-user 章を削除）。

## エンドユーザー向け
<!-- 製品を日常的に使う最終利用者向け。利用者にタスクが無い製品（例: 閲覧のみの LP）では
     この章を削除し、front-matter の audiences から end-user を外す。 -->

### 対象読者
<記入: 誰のための章か（例「予約システムを使う店舗スタッフ」）>

### 前提
- アクセス方法: <記入: URL / アプリ名>
- 必要なアカウント: <記入>
- 環境: <記入: 対応ブラウザ・端末>

### 操作手順
#### <タスク名>するには
1. <ステップ>
2. <ステップ>

![<画面の説明>](<スクリーンショットのパス>)

<!-- タスクごとにこの「### 〜するには」ブロックを繰り返す。1タスク=1見出し。 -->

### つまずいたら
- <よくある問題>: <対処>

### 用語
- <専門語>: <平易な言い換え>

## 運用者向け
<!-- 製品を運用・更新する発注者側の担当者向け（コンテンツ更新・基本設定）。
     監視・障害対応などの保守手順は別途 runbook（保守フェーズ）に委ねる。 -->

### 対象読者
<記入: 例「サイトのお知らせを更新する広報担当」>

### 前提
- 管理画面: <記入: URL / ログイン情報の入手先>
- 必要な権限: <記入>

### 操作手順
#### <運用タスク>するには
1. <ステップ>
2. <ステップ>

![<画面の説明>](<スクリーンショットのパス>)

### つまずいたら
- <よくある問題>: <対処>

### 用語
- <専門語>: <平易な言い換え>

## 改訂履歴
- <日付>: <変更内容>
```

- [ ] **Step 2: テンプレ群との整合を確認**

Run: `python3 -c "import pathlib; t=pathlib.Path('templates/MANUAL.template.md').read_text(encoding='utf-8'); assert 'audiences:' in t and 'エンドユーザー向け' in t and '運用者向け' in t; print('template OK')"`
Expected: `template OK`

- [ ] **Step 3: コミット**

```bash
git add templates/MANUAL.template.md
git commit -m "feat(b3a): add audience-parameterized MANUAL template"
```

---

## Task 2: manual skill（生成手順）＋ example ミラー

**Files:**
- Create: `.claude/skills/manual/SKILL.md`
- Create (mirror): `examples/minimal-project/.claude/skills/manual/SKILL.md`

- [ ] **Step 1: skill を作成**

以下の内容で `.claude/skills/manual/SKILL.md` を作成する:

```markdown
---
name: manual
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
front-matter `audiences` に宣言し、該当しない読者の章は削除する。

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
- 宣言した読者の章を欠落させる。
- 理由なく「マニュアル不要」と宣言する。
- チャット履歴を成果物のソースにする（仕様/成果物が唯一のソース）。

## コンテキスト予算
- SCOPE/PRD/ACCEPTANCE + 出荷機能一覧 + MANUAL テンプレのみ。
- 過去のチャット履歴は参照しない。
```

- [ ] **Step 2: example へミラー**

```bash
mkdir -p examples/minimal-project/.claude/skills/manual
cp .claude/skills/manual/SKILL.md examples/minimal-project/.claude/skills/manual/SKILL.md
```

- [ ] **Step 3: byte 同一を確認**

Run: `diff -q .claude/skills/manual/SKILL.md examples/minimal-project/.claude/skills/manual/SKILL.md && echo "mirror OK"`
Expected: `mirror OK`

- [ ] **Step 4: コミット**

```bash
git add .claude/skills/manual/SKILL.md examples/minimal-project/.claude/skills/manual/SKILL.md
git commit -m "feat(b3a): add manual-generation skill (+example mirror)"
```

---

## Task 3: ship-and-docs に Step 2.5 を追加

**Files:**
- Modify: `.claude/skills/ship-and-docs/SKILL.md`（`### Step 2: TO-CLIENT 作成` ブロックと `### Step 3: ユーザー確認` の間）
- Modify (mirror): `examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md`

- [ ] **Step 1: Step 2.5 を挿入**

`.claude/skills/ship-and-docs/SKILL.md` の `### Step 3: ユーザー確認` の直前に、次のブロックを挿入する:

```markdown
### Step 2.5: 操作マニュアル作成（該当時）

`manual` skill を読み、製品を使う/運用する人がいる場合は
`templates/MANUAL.template.md` をもとに `docs/handover/MANUAL.md` を作成する。
該当読者（利用者/運用者）ごとに操作手順を記述し、TO-CLIENT の納品物欄からリンクする。
使う人も運用者もいない場合は生成せず、理由を TO-CLIENT に記録する。

```

> 挿入位置の確認: `### Step 3: ユーザー確認` の行をアンカーにし、その直前に上記を入れる。
> Step 3 の「TO-CLIENT の内容をユーザーに提示し、承認を得る」レビューが MANUAL.md も
> 対象になる（マニュアルも納品物の一部として一緒に確認される）。

- [ ] **Step 2: example へミラー**

```bash
cp .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
diff -q .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md && echo "mirror OK"
```
Expected: `mirror OK`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
git commit -m "feat(b3a): ship-and-docs references manual skill (Step 2.5)"
```

---

## Task 4: docs-sync に整合チェックを1項目追加

**Files:**
- Modify: `.claude/skills/docs-sync/SKILL.md`（`## 整合性チェックリスト` の末尾）
- Modify (mirror): `examples/minimal-project/.claude/skills/docs-sync/SKILL.md`

- [ ] **Step 1: チェック項目を追加**

`.claude/skills/docs-sync/SKILL.md` の `## 整合性チェックリスト` の最後の `- [ ]` 行の直後に、次の1行を追加する:

```markdown
- [ ] マニュアルが該当する案件なら `docs/handover/MANUAL.md` が存在し、front-matter の宣言読者ごとに手順章がある（該当なしなら理由が記録されている）
```

- [ ] **Step 2: example へミラー**

```bash
cp .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
diff -q .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md && echo "mirror OK"
```
Expected: `mirror OK`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
git commit -m "feat(b3a): docs-sync verifies MANUAL existence + audience sections"
```

---

## Task 5: 登録（contract・full profile・CLAUDE.md）

**Files:**
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_TEMPLATE_FILES`・`REQUIRED_SKILL_FILES`・`REQUIRED_EXAMPLE_FILES`）
- Modify: `templates/profiles/full.json`（`recommended`）
- Modify: `CLAUDE.md`（Skills 一覧）

- [ ] **Step 1: contract に登録**

`scripts/check_framework_contract.py` を3箇所編集:

`REQUIRED_TEMPLATE_FILES` の末尾要素 `ROOT / "templates/hooks.template.json",` の直前（テンプレ群の最後）に追加:
```python
    ROOT / "templates/MANUAL.template.md",
```

`REQUIRED_SKILL_FILES` の `ROOT / ".claude/skills/browser-assist/SKILL.md",` の直後に追加:
```python
    ROOT / ".claude/skills/manual/SKILL.md",
```

`REQUIRED_EXAMPLE_FILES` の example スキル/エージェント群の中、`reviewer-maintainability.md` 行の直前または `update-gate.sh` 行の直前など example セクション内に追加:
```python
    ROOT / "examples/minimal-project/.claude/skills/manual/SKILL.md",
```

> 注: example の他スキルが REQUIRED_EXAMPLE_FILES に列挙されていない場合（example の .claude/skills は MIRROR_DIRS で網羅されるため個別列挙不要のことがある）、`grep -n "examples/minimal-project/.claude/skills" scripts/check_framework_contract.py` で既存の列挙有無を確認し、**他スキルが列挙されていなければ example 行は追加しない**（ミラー網羅に委ねる）。列挙方式に合わせること。

- [ ] **Step 2: full.json に登録**

`templates/profiles/full.json` の `recommended` 内、`".claude/skills/browser-assist/SKILL.md",` の直後（または skill 群の末尾）に追加:
```json
    ".claude/skills/manual/SKILL.md",
```

- [ ] **Step 3: CLAUDE.md の Skills 一覧に追加**

`CLAUDE.md` の Skills 節（`- deploy, client-workflow, session-recovery, ship-and-docs` の行）を次に変更:
```markdown
- deploy, client-workflow, session-recovery, ship-and-docs, manual
```

- [ ] **Step 4: contract と drift を実行し、要求された追従を行う**

Run: `python3 scripts/check_framework_contract.py --profile=full; python3 scripts/check_reference_drift.py`
Expected: 両方 `PASS`。もし `/judge` 登録時のように「`manual` がドキュメント表に無い」等の警告/失敗が出たら、指示された該当ファイル（README 等）を更新して再実行する（チェックが source of truth）。

- [ ] **Step 5: コミット**

```bash
git add scripts/check_framework_contract.py templates/profiles/full.json CLAUDE.md
git commit -m "feat(b3a): register MANUAL template + manual skill in contract/profile/kernel"
```

---

## Task 6: architecture-overview に反映（非強制・任意）

**Files:**
- Modify: `docs/architecture-overview.md`（§6 スキル表）

- [ ] **Step 1: §6 スキル表に行を追加**

`docs/architecture-overview.md` の §6（`## 6. スキル`）のスキル表に `manual` の行を追加する（対応フェーズ=docs、user-invocable=false）。表の最終行の直後に:
```markdown
| `manual` | docs（ship-and-docs から参照） | false |
```

> 数値カウント（「12 の pull-based スキル」等）は実体（15+）と既に乖離しており drift/contract で強制されていない。本タスクで数値整合まで追わない（既存の stale は B3a の範囲外）。表へ `manual` を載せて発見可能性だけ担保する。

- [ ] **Step 2: コミット**

```bash
git add docs/architecture-overview.md
git commit -m "docs(b3a): list manual skill in architecture overview"
```

---

## Task 7: 統合検証

- [ ] **Step 1: 全検証を green に**

Run（順に）:
- `python3 scripts/check_framework_contract.py --profile=full` → `PASS`
- `python3 scripts/check_framework_contract.py --profile=standard` → `PASS`
- `python3 scripts/check_reference_drift.py` → `PASS`（mirror byte 同一含む）
- `python3 -m unittest tests.test_mirror_identity` → `OK`
- `python3 -m unittest discover -s tests` → `OK`（既存テストの非回帰確認。新規ユニットテストは無い）
- `python3 scripts/eval_scaffold_smoke.py` → `Result: PASS`
- `python3 scripts/check_status.py --root . --strict` → `PASS`

- [ ] **Step 2: 内容目視レビュー**

`templates/MANUAL.template.md` が読者ごとの章（対象読者/前提/操作手順/つまずいたら/用語）を持ち、front-matter `audiences` で出し分けできる構造であることを目視。`manual` SKILL.md の手順が非エンジニア向け平易語と「不要時の理由記録」「Red Flags」を含むことを確認。

- [ ] **Step 3: 証拠コミット（変更があれば）**

```bash
git add -A
git commit -m "test(b3a): full structural verification green"
```
> 変更が無ければ空コミットは作らない（検証結果は実行ログが証拠）。

---

## Self-Review（プラン執筆者チェック・実施済み）

- **spec カバレッジ**: 決定1（読者パラメータ化）=Task1 front-matter＋Task2 Step1 / 決定2（(i)+advisory）=Task3 ship-and-docs 参照・gate なし / 決定3（配置・schema 不変）=Task1 単一ファイル・current_refs 不追加・Task4 docs-sync・TO-CLIENT リンク（Task2 Step5/Task3）/ 決定4（図 c）=Task2 Step3。登録=Task5、docs=Task6、検証=Task7。**未カバーなし**。
- **プレースホルダ**: テンプレ/skill の `<記入>`・`<タスク名>` は**成果物テンプレの記入欄であり計画のプレースホルダではない**（テンプレの設計上の空欄）。計画手順自体に TBD は無い。
- **型/名称整合**: skill 名 `manual`、テンプレ `MANUAL.template.md`、出力 `docs/handover/MANUAL.md`、front-matter キー `audiences`、参照元 `ship-and-docs` Step 2.5、検証元 `docs-sync` は全 Task で一致。
- **既知の留意**: (1) REQUIRED_EXAMPLE_FILES への example 行追加は既存の列挙方式に合わせる（Task5 Step1 注記）。(2) ドキュメント数値カウントの stale は範囲外（Task6 注記）。(3) 新規ユニットテストは無い＝検証は構造チェック＋目視（冒頭テスト方針）。

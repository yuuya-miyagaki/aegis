# B3c 保守ライフサイクル 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 納品後の「運用→監視→トリアージ→修正」の導線を、新テンプレ `RUNBOOK.template.md`＋単一 `maintenance` skill で構造化する（監査能力⑫の充足）。修正実行は既存 `bug-diagnosis`・bugfix/hotfix を再利用する。

**Architecture:** 新テンプレ `RUNBOOK.template.md`（監視/トリアージ/エスカレーション/インシデント履歴/用語）と新 pull-based skill `maintenance`（Part A=ship 時の RUNBOOK 生成／Part B=運用時のトリアージ→ルーティング→記録）を追加。`ship-and-docs` の ship 段階（Step 2.6）と `bug-diagnosis`（本番/運用起因ケース）から参照し、`docs-sync` に整合チェックを1項目、`HANDOVER-TO-CLIENT` テンプレに RUNBOOK リンク行を追加する。新 Mode/フェーズ/ゲート/`current_refs` キーは作らない（advisory）。

**Tech Stack:** Markdown テンプレ／Claude Code skills（`disable-model-invocation: true`）／`check_framework_contract.py`・`check_reference_drift.py`・`test_mirror_identity.py`・`eval_scaffold_smoke.py` による構造的検証。

> **テスト方針（重要）:** B3c は実行コードを持たない（テンプレ＝静的 md、skill＝LLM 向け手順、各 skill 改修＝手順文）。よって Python ユニットテストは無い。各タスクの検証は **登録整合チェック（contract / drift / mirror-identity / scaffold-smoke）の green** と内容目視。spec `docs/plans/2026-06-07-v1-b3c-maintenance-lifecycle-design.md` 参照。

> **依存順の注意:** `maintenance` skill を参照する ship-and-docs（Task 3）・bug-diagnosis（Task 5）は、skill 本体が存在する Task 2 より後に置く（参照 drift を避ける）。lint_names はスキルを双方向検査するため、skill 作成と lint 必須登録（`REQUIRED_SKILL_FILES`＋`REQUIRED_EXAMPLE_SKILL_DIRS`＋`CLAUDE.md ## Skills`）は Task 2 の同一コミットに畳む。`full.json` は lint 非対象なので Task 7 に分離。

---

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `templates/RUNBOOK.template.md` | 運用 RUNBOOK テンプレ（監視/トリアージ/エスカレーション/履歴/用語） | 新規 |
| `.claude/skills/maintenance/SKILL.md` | 保守 skill（Part A 生成・Part B 運用ループ） | 新規（+example ミラー） |
| `.claude/skills/ship-and-docs/SKILL.md` | ship 段階に Step 2.6 追加 | 改修（+mirror） |
| `.claude/skills/docs-sync/SKILL.md` | 整合チェック1項目追加 | 改修（+mirror） |
| `.claude/skills/bug-diagnosis/SKILL.md` | 本番/運用起因の入口に maintenance 参照を1行追加 | 改修（+mirror） |
| `templates/HANDOVER-TO-CLIENT.template.md` | 納品サマリーに RUNBOOK リンク行を追加 | 改修 |
| `scripts/check_framework_contract.py` | テンプレ/スキル/example skill dir を必須登録 | 改修 |
| `templates/profiles/full.json` | `maintenance` skill を recommended に登録 | 改修 |
| `CLAUDE.md` | Skills 一覧に `maintenance` 追加 | 改修 |

> ミラー注: テンプレ（`templates/`）は example にミラーしない（example に templates/ は無い）。`.claude/skills/` 配下は MIRROR_DIRS なので `maintenance` 新設と `ship-and-docs`/`docs-sync`/`bug-diagnosis` 改修を `examples/minimal-project/.claude/skills/` へ byte 同一でコピーする。`RUNBOOK.template.md` は full.json に載せない（full.json はテンプレを列挙しない）。
>
> 出力文書は `docs/handover/RUNBOOK.md`、テンプレは `RUNBOOK.template.md`。生成/運用する skill は `maintenance`。

---

## Task 1: RUNBOOK.template.md 作成＋テンプレ登録

**Files:**
- Create: `templates/RUNBOOK.template.md`
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_TEMPLATE_FILES`）

> テンプレには双方向 lint が無い（`REQUIRED_TEMPLATE_FILES` は存在チェックのみ）。未登録でも contract は落ちないが、同一コミットで登録して整合を保つ。

- [ ] **Step 1: テンプレを作成**

以下の内容で `templates/RUNBOOK.template.md` を作成する:

```markdown
---
product: "<記入>"
release: "<記入>"
date: "<記入>"
environment: "<記入: 本番URL・ホスティング先（例 Vercel / Firebase）>"
owners: "<記入: 運用担当者・エスカレーション先（氏名/連絡先）>"
---
# <製品名> 運用 RUNBOOK
<!-- 正本: maintenance skill -->
<!-- exit-check: 監視/インシデント対応/エスカレーション/インシデント履歴/用語 の節あり・プレースホルダ未記入なし・用語平易化済み -->

> この RUNBOOK は製品を「運用し続ける／壊れたときに直す」ための文書です。
> 使い方・日常運用（コンテンツ更新・基本設定）は `MANUAL.md` を参照してください。
> 運用者がいない案件（閲覧専用で更新も監視もしない等）ではこの文書は不要です。

## 監視
<!-- 何を見れば「正常」と分かるか。運用者が定期的に確認する項目。 -->
| 監視対象 | 正常な状態 / しきい値 | 確認手段 | 頻度 |
|---|---|---|---|
| <記入: 例 サイト表示> | <記入: 例 トップが5秒以内に表示> | <記入: 例 ブラウザで本番URLを開く> | <記入: 例 毎営業日朝> |

## インシデント対応（トリアージ）
<!-- 異常に気づいたとき、まず重大度を見分ける。 -->
- **重大度 高**: <記入: 例 サイト全体が表示されない／予約が一切できない>。初動: <記入>
- **重大度 中**: <記入: 例 一部機能が動かない>。初動: <記入>
- **重大度 低**: <記入: 例 表示崩れなど軽微>。初動: <記入>

**操作者で対応できる範囲**: <記入: 例 コンテンツ差し戻し・再読み込み・キャッシュ削除>
**開発者へエスカレーションする線引き**: <記入: 例 高重大度／操作者手順で復旧しない／データ不整合の疑い>

## エスカレーション
- 連絡先: <記入: 開発担当・連絡方法>
- 目標復旧時間（SLA）: <記入: 例 高=2時間以内に一次対応>
- 開発対応の合図: 高重大度または操作者手順で復旧しない場合、bugfix（緊急時 hotfix）として開発に依頼する。

## インシデント履歴
<!-- 対応したインシデントを追記する。空のまま閉じない。 -->
| 日付 | 事象 | 重大度 | 対応 | 恒久対策 |
|---|---|---|---|---|
| <記入例 2026-01-01> | <記入例 予約ボタンが反応しない> | <中> | <記入例 キャッシュ削除で復旧> | <記入例 hotfix #123 で原因修正> |

## 用語
- <専門語>: <平易な言い換え>
```

- [ ] **Step 2: REQUIRED_TEMPLATE_FILES に登録**

`scripts/check_framework_contract.py` の `REQUIRED_TEMPLATE_FILES` で、`ROOT / "templates/MANUAL.template.md",`（:113）の直後に追加:
```python
    ROOT / "templates/RUNBOOK.template.md",
```

- [ ] **Step 3: 構造と contract を確認**

Run: `python3 -c "import pathlib; t=pathlib.Path('templates/RUNBOOK.template.md').read_text(encoding='utf-8'); assert '## 監視' in t and 'インシデント対応' in t and 'エスカレーション' in t and 'インシデント履歴' in t; print('template OK')"`
Expected: `template OK`

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 4: コミット**

```bash
git add templates/RUNBOOK.template.md scripts/check_framework_contract.py
git commit -m "feat(b3c): add operations RUNBOOK template + register"
```

---

## Task 2: maintenance skill 作成＋lint 必須登録（同一コミット）

**Files:**
- Create: `.claude/skills/maintenance/SKILL.md`
- Create (mirror): `examples/minimal-project/.claude/skills/maintenance/SKILL.md`
- Modify: `scripts/check_framework_contract.py`（`REQUIRED_SKILL_FILES`・`REQUIRED_EXAMPLE_SKILL_DIRS`）
- Modify: `CLAUDE.md`（`## Skills` セクション）

> **重要:** `lint_names` はスキルを双方向検査するため、skill dir 作成と同時に `REQUIRED_SKILL_FILES`・`REQUIRED_EXAMPLE_SKILL_DIRS`・`CLAUDE.md ## Skills` の3箇所へ登録しないと contract が落ちる。**この Task 内（1コミット）で全部済ませる。** `full.json` は lint 非対象なので Task 7 に分離可。

- [ ] **Step 1: skill を作成**

以下の内容で `.claude/skills/maintenance/SKILL.md` を作成する:

```markdown
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

## いつ使うか
- **Part A（生成）**: docs フェーズで `ship-and-docs` の ship 段階（Step 2.6）から参照される。製品を運用する人がいる納品物のとき。
- **Part B（運用）**: 運用中にインシデント/監視シグナルが出たとき。`bug-diagnosis` の本番/運用起因ケースから参照される。
- 運用者がいない案件（閲覧専用で監視も更新もしない等）は RUNBOOK を生成せず理由を記録する。

## Part A: RUNBOOK 生成（ship 時）

### Step 1: 対象を決める
`docs/requirements/SCOPE.md`・`PRD.md`・TO-CLIENT の「配備と運用」・STATUS から、運用者の有無とデプロイ先/監視手段/エスカレーション先を判定し、ユーザーに確認する。運用者がいなければ生成せず理由を記録（下記「RUNBOOK が不要なとき」）。

### Step 2: RUNBOOK を記述
`templates/RUNBOOK.template.md` をもとに `docs/handover/RUNBOOK.md` を作成する。監視・トリアージ・エスカレーションを**平易語**（非エンジニアが読める語彙）で記述する。プレースホルダ（`<記入>`）を空のまま残さない。実際の監視インフラ設定（アラート構築等）は促すが必須化しない。

### Step 3: TO-CLIENT からリンク
`docs/handover/TO-CLIENT.md` の納品サマリーに `docs/handover/RUNBOOK.md` へのリンクを追加する。

### Step 4: 整合確認
`docs-sync` skill を読み、RUNBOOK.md の存在と必須節（監視/インシデント対応/エスカレーション/インシデント履歴/用語）の充足を確認する。

## Part B: インシデント対応ループ（運用時）

### Step 1: シグナル確認
症状・影響範囲を把握する。`docs/handover/RUNBOOK.md` の `## 監視`・`## インシデント対応（トリアージ）` を読む。

### Step 2: 分類
RUNBOOK のトリアージ基準で重大度（高/中/低）とスコープを判定する。

### Step 3: ルーティング
- 操作者で対応可（RUNBOOK の手順内）→ 実施する。
- 開発が必要 → `task_type = bugfix`（緊急なら `hotfix`）として `bug-diagnosis` skill へ渡す。

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
```

- [ ] **Step 2: example へミラー**

```bash
mkdir -p examples/minimal-project/.claude/skills/maintenance
cp .claude/skills/maintenance/SKILL.md examples/minimal-project/.claude/skills/maintenance/SKILL.md
```

- [ ] **Step 3: REQUIRED_SKILL_FILES に登録**

`scripts/check_framework_contract.py` の `REQUIRED_SKILL_FILES` で、`ROOT / ".claude/skills/user-manual/SKILL.md",`（:70）の直後に追加:
```python
    ROOT / ".claude/skills/maintenance/SKILL.md",
```

- [ ] **Step 4: REQUIRED_EXAMPLE_SKILL_DIRS に登録**

同 `scripts/check_framework_contract.py` の `REQUIRED_EXAMPLE_SKILL_DIRS`（:200）で、`"user-manual",`（:207）の直後に追加:
```python
    "maintenance",
```
> `REQUIRED_EXAMPLE_FILES` は触らない（example スキルは SKILL_DIRS で管理される）。

- [ ] **Step 5: CLAUDE.md ## Skills に登録**

`CLAUDE.md` の `## Skills` セクションの行（:61）
```markdown
- deploy, client-workflow, session-recovery, ship-and-docs, user-manual
```
を次に変更:
```markdown
- deploy, client-workflow, session-recovery, ship-and-docs, user-manual, maintenance
```

- [ ] **Step 6: byte 同一と contract を確認**

Run: `diff -q .claude/skills/maintenance/SKILL.md examples/minimal-project/.claude/skills/maintenance/SKILL.md && echo "mirror OK"`
Expected: `mirror OK`

Run: `python3 scripts/check_framework_contract.py --profile=full && python3 scripts/check_reference_drift.py`
Expected: 両方 `PASS`（name-lint 含め green。skill 未登録なら `name-lint: skill 'maintenance' ...` で落ちるので、落ちたら Step 3-5 の登録漏れを確認）。

- [ ] **Step 7: コミット**

```bash
git add .claude/skills/maintenance/SKILL.md examples/minimal-project/.claude/skills/maintenance/SKILL.md scripts/check_framework_contract.py CLAUDE.md
git commit -m "feat(b3c): add maintenance skill + register (contract/example/kernel)"
```

---

## Task 3: ship-and-docs に Step 2.6 を追加

**Files:**
- Modify: `.claude/skills/ship-and-docs/SKILL.md`（`### Step 3: ユーザー確認`（:64）の直前）
- Modify (mirror): `examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md`

- [ ] **Step 1: Step 2.6 を挿入**

`.claude/skills/ship-and-docs/SKILL.md` の `### Step 3: ユーザー確認` の行をアンカーに、その直前に次のブロックを挿入する:

```markdown
### Step 2.6: 運用 RUNBOOK 作成（該当時）

`maintenance` skill（Part A）を読み、製品を運用する人がいる場合は
`templates/RUNBOOK.template.md` をもとに `docs/handover/RUNBOOK.md` を作成する。
監視・トリアージ・エスカレーションを記述し、TO-CLIENT の納品サマリーからリンクする。
運用者がいない場合は生成せず、理由を TO-CLIENT に記録する。

```

> Step 3 の「TO-CLIENT の内容をユーザーに提示し、承認を得る」レビューが RUNBOOK.md も
> 対象になる（RUNBOOK も納品物の一部として一緒に確認される）。

- [ ] **Step 2: example へミラー＋確認**

```bash
cp .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
diff -q .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md && echo "mirror OK"
```
Expected: `mirror OK`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/ship-and-docs/SKILL.md examples/minimal-project/.claude/skills/ship-and-docs/SKILL.md
git commit -m "feat(b3c): ship-and-docs references maintenance skill (Step 2.6)"
```

---

## Task 4: docs-sync に整合チェックを1項目追加

**Files:**
- Modify: `.claude/skills/docs-sync/SKILL.md`（MANUAL 整合行（:25）の直後）
- Modify (mirror): `examples/minimal-project/.claude/skills/docs-sync/SKILL.md`

- [ ] **Step 1: チェック項目を追加**

`.claude/skills/docs-sync/SKILL.md` の MANUAL 整合行
```markdown
- [ ] マニュアルが該当する案件なら `docs/handover/MANUAL.md` が存在し、front-matter の宣言読者と手順章が1対1（宣言ごとに章があり、宣言の無い孤児章も無い）。該当なしなら理由が記録されている
```
の直後に、次の1行を追加する:

```markdown
- [ ] 保守が該当する案件なら `docs/handover/RUNBOOK.md` が存在し、front-matter 宣言と監視/インシデント対応/エスカレーション/インシデント履歴/用語の必須節がある。該当なしなら理由が記録されている
```

- [ ] **Step 2: example へミラー＋確認**

```bash
cp .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
diff -q .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md && echo "mirror OK"
```
Expected: `mirror OK`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/docs-sync/SKILL.md examples/minimal-project/.claude/skills/docs-sync/SKILL.md
git commit -m "feat(b3c): docs-sync verifies RUNBOOK section parity"
```

---

## Task 5: bug-diagnosis に maintenance 参照を追加

**Files:**
- Modify: `.claude/skills/bug-diagnosis/SKILL.md`（`## いつ使うか`（:12）のリスト末尾）
- Modify (mirror): `examples/minimal-project/.claude/skills/bug-diagnosis/SKILL.md`

> bug-diagnosis 本体のゲート処理・ReAct 診断ステップは変更しない。追加は「運用起因なら maintenance を先に通す」という参照1行のみ。

- [ ] **Step 1: いつ使うか に1行追加**

`.claude/skills/bug-diagnosis/SKILL.md` の `## いつ使うか` の最後の項目
```markdown
- brainstorm を n/a にしてよい代わりに、このスキルを実行する
```
の直後に、次の1行を追加する:

```markdown
- **本番/運用起因の問題のとき**: まず `maintenance` skill（Part B: トリアージ）を読み、重大度分類とルーティングを経てから本診断に入る。解決後は `docs/handover/RUNBOOK.md` の `## インシデント履歴` に追記する。
```

- [ ] **Step 2: example へミラー＋確認**

```bash
cp .claude/skills/bug-diagnosis/SKILL.md examples/minimal-project/.claude/skills/bug-diagnosis/SKILL.md
diff -q .claude/skills/bug-diagnosis/SKILL.md examples/minimal-project/.claude/skills/bug-diagnosis/SKILL.md && echo "mirror OK"
```
Expected: `mirror OK`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/bug-diagnosis/SKILL.md examples/minimal-project/.claude/skills/bug-diagnosis/SKILL.md
git commit -m "feat(b3c): bug-diagnosis routes production issues through maintenance"
```

---

## Task 6: HANDOVER-TO-CLIENT テンプレに RUNBOOK 行を追加

**Files:**
- Modify: `templates/HANDOVER-TO-CLIENT.template.md`（納品サマリーの MANUAL 行（:11）の直後）

> このテンプレは example にミラーされない（example に templates/ は無い）。

- [ ] **Step 1: RUNBOOK リンク行を追加**

`templates/HANDOVER-TO-CLIENT.template.md` の行
```markdown
- 操作マニュアル: <記入: docs/handover/MANUAL.md（該当時）／不要なら理由>
```
の直後に、次の1行を追加する:

```markdown
- 運用 RUNBOOK: <記入: docs/handover/RUNBOOK.md（運用者がいる場合）／不要なら理由>
```

- [ ] **Step 2: contract を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 3: コミット**

```bash
git add templates/HANDOVER-TO-CLIENT.template.md
git commit -m "feat(b3c): TO-CLIENT summary links the operations RUNBOOK"
```

---

## Task 7: full.json に maintenance を登録（lint 非対象・単独）

**Files:**
- Modify: `templates/profiles/full.json`（`recommended`）

- [ ] **Step 1: full.json に登録**

`templates/profiles/full.json` の `recommended` 内、`".claude/skills/user-manual/SKILL.md",`（:63）の直後に追加:
```json
    ".claude/skills/maintenance/SKILL.md",
```

- [ ] **Step 2: JSON 妥当性と contract を確認**

Run: `python3 -c "import json; json.load(open('templates/profiles/full.json')); print('full.json valid')"`
Expected: `full.json valid`

Run: `python3 scripts/check_framework_contract.py --profile=full`
Expected: `PASS: aegis contract is aligned`

- [ ] **Step 3: コミット**

```bash
git add templates/profiles/full.json
git commit -m "feat(b3c): add maintenance skill to full profile"
```

---

## Task 8: 統合検証

- [ ] **Step 1: 全検証を green に**

Run（順に）:
- `python3 scripts/check_framework_contract.py --profile=full` → `PASS: aegis contract is aligned`
- `python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project` → `PASS: project contract is aligned (profile: standard)`
- `python3 scripts/check_reference_drift.py` → `PASS: no reference drift detected`（mirror byte 同一含む）
- `python3 -m unittest tests.test_mirror_identity` → `OK`
- `python3 scripts/run_eval.py --tier 0` → `Ran <N> tests` / `OK`（既存テストの非回帰確認。新規ユニットテストは無い）
- `python3 scripts/run_eval.py --tier 2` → `Result: PASS`（minimal/standard scaffold smoke）
- `python3 scripts/check_status.py --root . --strict` → `PASS`

- [ ] **Step 2: 内容目視レビュー**

`templates/RUNBOOK.template.md` が必須節（監視/インシデント対応（トリアージ）/エスカレーション/インシデント履歴/用語）を持ち、運用者がプレースホルダを埋めれば運用できる構造であることを目視。`maintenance` SKILL.md が Part A（生成）/Part B（運用ループ）を分節で持ち、非エンジニア向け平易語・「不要時の理由記録」・「Red Flags」を含み、修正実行を bug-diagnosis/bugfix/hotfix に委ねていることを確認。

- [ ] **Step 3: 証拠コミット（変更があれば）**

```bash
git add -A
git commit -m "test(b3c): full structural verification green"
```
> 変更が無ければ空コミットは作らない（検証結果は実行ログが証拠）。

---

## Self-Review（プラン執筆者チェック・実施済み）

- **spec カバレッジ**: 決定1（軽量・advisory／bug-diagnosis 再利用）=新 Mode/ゲートなし・Task5 で既存経路へルーティング / 決定2（独立 RUNBOOK）=Task1 テンプレ＋Task3 ship-and-docs Step2.6＋Task6 TO-CLIENT リンク＋Task4 docs-sync 検証・current_refs 不追加 / 決定3（履歴記録）=Task1 インシデント履歴節＋Task2 skill Part B Step4 / 決定4（監視具体度）=Task1 プレースホルダ＋Task2 skill Part A Step2 非必須化 / 決定5（1 skill 2パート）=Task2 maintenance 単一 SKILL。登録=Task1/Task2/Task7、検証=Task8。**未カバーなし**。
- **依存順**: maintenance（Task2）→ それを参照する ship-and-docs（Task3）/bug-diagnosis（Task5）の順。lint 双方向登録は Task2 同一コミット。**赤コミットなし**。
- **プレースホルダ**: テンプレ/skill の `<記入>`・`<専門語>` は成果物テンプレの記入欄であり計画の TBD ではない。手順自体に TBD 無し。
- **型/名称整合**: skill 名 `maintenance`（dir/frontmatter name/参照/CLAUDE.md/contract/full.json/REQUIRED_EXAMPLE_SKILL_DIRS で一致）、テンプレ `RUNBOOK.template.md`、出力 `docs/handover/RUNBOOK.md`、参照元 `ship-and-docs` Step 2.6・`bug-diagnosis`、検証元 `docs-sync`、必須節名（監視/インシデント対応（トリアージ）/エスカレーション/インシデント履歴/用語）は全 Task で一致。
- **コミット健全性**: 各 Task のコミット後に contract がすべて green。

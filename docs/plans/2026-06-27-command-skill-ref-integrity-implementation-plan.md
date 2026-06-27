# 実装計画
<!-- 正本: subagent-dev skill -->

> **訂正（grill-plan 2026-06-27）**: brainstorm 時の 3 穴のうち #1(validate)・#2(retro) は **false positive**。
> `setup.sh:resolve_source` が validate.md/retro.md を `templates/commands/` の **scaffold-safe 版**から
> install する（installed validate.md は check_status.py[同梱]のみ必須・check_framework_contract は "if available"
> guard／installed retro.md は retro_report.py 不在時に手動 degrade）。実穴は **#3（update-task.sh）の 1 件のみ**。
> 本計画は縮小版。旧 SPEC/brainstorm-record の #1/#2 記述は当該 doc の訂正注記を参照。

## 目的

- 配布 self-containment 検査を **skill(.md) → script** 層へ拡張し、verbatim install される skill が
  未同梱 script を参照して install 後に inert 化する穴を CI で恒久検知する。
- 実証済の 1 穴を解決: full install で `aegis-brainstorm`/`bug-diagnosis` skill が `update-task.sh` を
  unguarded 参照するが未同梱。加えて standard も `state-machine.md` が update-task.sh を指示するのに未同梱。

## 入力

- 参照設計: `docs/specs/2026-06-27-command-skill-ref-integrity-design.md`（訂正注記付き）
- 参照記録: `docs/specs/2026-06-27-command-skill-ref-integrity-brainstorm-record.md`（訂正注記付き）

## スコープ（縮小確定）

- **やること**:
  1. `update-task.sh` を **standard+full の required** に同梱（required な `update-gate.sh` の sibling＝
     gate/task の tamper 保護 STATUS 変更スクリプト対。proven inert ref: skills[full]・state-machine.md[standard]）。
  2. **skill→script** 参照整合性検査を iter48 の `test_profile_referential_integrity.py` に追加。
  3. README の profile 件数同期（standard required 18→19・full は記載あれば）。
- **やらないこと（YAGNI / 既解決）**:
  - command→script 検査（framework が scaffold-safe `templates/commands/` ＋ "if available" idiom で既解決。
    検査には resolve_source 模倣＋guard 判定が要り高複雑・低 ROI）。
  - validate.md de-ship／retro_report.py・learnings_search.py 同梱（#1/#2 は穴でない）。
  - rules(.md)/CLAUDE.md→script 検査（CLAUDE.md は template remap・別スライス）。

## Deploy Target（必須）

- Hosting/Database/CI: n/a（framework 内部。test + profile manifest(JSON) + README のみ。アプリ deploy 無し）。
- 互換性確認: n/a（deploy 対象外。M で deploy gate は size-exempt）。
- 認証方式: None。

## Git 戦略

- dogfood リポジトリにつき main 直コミット。push は ship フェーズで承認後（`gh auth switch --user yuuya-miyagaki`）。

## ファイル構造（変更マップ）

- 変更: `tests/test_profile_referential_integrity.py` — skill→script 検査を追加。
  - 純関数 `_skill_script_edges(md_text)`: `scripts/<name>.(py|sh)` トークン集合を返す（`scripts/` prefix のみ＝
    hooks/lib は別 prefix で自然に対象外）。
  - `_shipped_scripts_any(profile)`: required∪recommended のうち `scripts/*.(py|sh)`（iter48 の .py 限定版とは別）。
  - 対象 skill doc 集合 `_shipped_skill_docs(profile)`: required∪recommended のうち `.claude/skills/**/*.md`
    全て（SKILL.md ＋ platforms.md 等の asset。skills は verbatim install ＝全 .md が install 実体）。
  - allow-list `INTENTIONAL_UNSHIPPED_SKILL_SCRIPT: dict[str,str]`（fix 後は空。将来 guarded-optional skill ref 用の受け皿）。
  - 結合検査 `test_every_profile_skill_script_ref_is_self_contained`＋抽出単体群。
- 変更: `templates/profiles/full.json` — required に `scripts/update-task.sh` 追加。
- 変更: `templates/profiles/standard.json` — required に `scripts/update-task.sh` 追加。
- 変更: `README.md` — standard required 件数 18→19（＋full 記載あれば）。
- 確認のみ: minimal 不変。regression（標準 suite・contract・scaffold smoke）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 0 | `_skill_script_edges`（純関数） | なし |
| Task 1 | 結合検査（RED 実証） | Task 0 + `_shipped_skill_docs`/`_shipped_scripts_any` |
| Task 2 | 修正済 full/standard JSON（穴解消・GREEN） | Task 1 |
| Task 3 | README + 件数テスト同期 | Task 2 |
| Task 4 | regression 解消・全 suite green | Task 2,3 |

循環なし。

## タスク分解

### タスク 0: 抽出ヘルパー `_skill_script_edges`

**blockedBy:** なし | **モデル:** `inherit` | **ファイル/テスト:** `tests/test_profile_referential_integrity.py`
**意図:** `.md` 本文から `scripts/<name>.(py|sh)` トークン集合を抽出。
**TDD:** 単体（code-fence 内 `bash scripts/update-task.sh` を拾う／inline `scripts/x.py` を拾う／`scripts/` 無し散文は拾わない／参照無しは空集合）→ FAIL → 実装 → PASS。
**受入:** 4 単体 green・install 状態に非依存。
**Deliverable:** [ ] 関数存在 [ ] テストカバー

### タスク 1: 結合検査（RED で 1 穴を実証）

**blockedBy:** Task 0 | **モデル:** `inherit` | **ファイル:** 同上
**意図:** 各 profile で shipped skill→script edges を `_violations(shipped_scripts_any, edges, allow)` 判定。
**TDD:** 現行 manifest（update-task.sh 未同梱）に対し **RED**（full で aegis-brainstorm/bug-diagnosis→update-task.sh が違反）を実測。
**受入:** RED で update-task.sh 穴が列挙される。
**Deliverable:** [ ] 検査存在 [ ] RED 実測ログ

### タスク 2: manifest 修正で GREEN

**blockedBy:** Task 1 | **モデル:** `inherit` | **ファイル:** `templates/profiles/{full,standard}.json`
**意図:** update-task.sh を両 required に追加。
**TDD:** Task 1 検査 GREEN 化。iter48 `.py` 検査は update-task.sh が .sh ＝非対象で不変（緑維持確認）。
**受入:** skill→script 検査 green・iter48 .py 検査 green。
**Deliverable:** [ ] 穴解消 [ ] 両検査 green

### タスク 3: README + 件数テスト同期

**blockedBy:** Task 2 | **モデル:** `inherit` | **ファイル:** `README.md`・（必要時）`tests/test_readme_profile_counts.py`
**意図:** standard required 18→19（full 記載あれば）。
**受入:** `test_readme_profile_counts.py` green。
**Deliverable:** [ ] README 整合 [ ] 件数テスト green

### タスク 4: regression 解消・全 suite green

**blockedBy:** Task 2,3 | **モデル:** `inherit`
**意図:** update-task.sh 追加で壊れる既存テスト（profile moat 登録・件数・install 数）を grep し更新。full suite + contract + scaffold smoke green。
**受入:** full suite green・contract PASS・scaffold smoke PASS。
**Deliverable:** [ ] regression ゼロ [ ] 全 suite green

## 事前準備

- [x] ベースブランチ最新（main・working tree clean）
- [x] 依存: 標準ライブラリ `re` のみ
- [x] 実穴・install-source（skills は verbatim・commands は template remap）確認済

## トレーサビリティ

| 課題 | AC | Task | テスト |
|------|----|------|--------|
| 実穴 skill→update-task.sh (full) | ship update-task.sh (full required) | Task 1,2 | test_profile_referential_integrity.py |
| standard の state-machine.md→update-task.sh inert | ship update-task.sh (standard required) | Task 2 | （検査は skill 範囲・standard 同梱で actionable 化） |
| 抽出健全性 | code-fence/inline 抽出・散文除外 | Task 0 | 同上（単体群） |
| README 同期 | 件数一致 | Task 3 | test_readme_profile_counts.py |

## 自己レビュー

- 仕様カバレッジ: 1 実穴 + skill→script 検査 + README が Task で網羅。
- 曖昧さ: 「shipped scripts」= required∪recommended の scripts/*.(py|sh)。skill 集合も同様に明示。
- 型整合: `_skill_script_edges`→set[str]、`_violations(set,set,dict)` 既存再利用。
- 境界整合: Consumes/Produces 一致・循環なし。

## リスク

- リスク: update-task.sh を standard に入れると README standard 件数が変わり既存テスト破損。
  - 対策: Task 3 で同期（RED→GREEN 実測）。
- リスク: 検査が fix 後 trivially green（allow-list 空）で価値が見えにくい。
  - 対策: TDD で update-task.sh 未同梱時 RED を実測（再発防止＝iter48 と同じ「二度測り」）。
- リスク: standard 同梱が skill→script 検査では非強制（state-machine.md=rules 由来）。
  - 対策: proven inert ref（state-machine.md 実物）を根拠に明記。rules→script 検査は別スライスとして繰延。

## 完了条件

- [ ] skill→script 検査が存在し update-task.sh 穴で RED→修正で GREEN を二重実測
- [ ] iter48 `.py` 検査 green 維持
- [ ] full suite green・contract PASS・scaffold smoke PASS・README 件数一致
- [ ] レビュー(盲検2次)・QA(B1 本物ドリル)・security(盲検2次) 通過

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

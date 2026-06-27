# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- 配布 self-containment 検査の射程を doc（`CLAUDE.md` の install 実体＝`templates/CLAUDE.template.md`／`.claude/rules/*.md` の verbatim）→ `scripts/*` 参照へ拡大する **regression guard** を追加する。grill-premise で実穴ゼロを実証済＝guard-only（honest framing）。

## 入力

- 参照要件: なし（内部 framework iteration・requirements []）
- 参照設計: `docs/specs/2026-06-27-doc-script-ref-integrity-design.md`
- 参照記録: `docs/specs/2026-06-27-doc-script-ref-integrity-brainstorm-record.md`

## Deploy Target（必須）

- Hosting: n/a / Database: n/a / CI/CD: n/a
- 理由: **test-only の framework 内部変更**（production code・hosting・DB・auth 一切なし）。M で deploy は size-exempt（SIZE_ALLOWED_PHASES）。
- next.config `output`: n/a / 認証: None / DEMO_MODE: n/a

## Git 戦略

- main へ直接（既存 iter48/49 と同様の小規模 framework iteration）。1 コミットに集約。

## ファイル構造（変更マップ）

- 変更: `tests/test_profile_referential_integrity.py` — 末尾に「iter50: doc(.md)→script 参照整合性」セクションを追加（helper・allow-list・unit・anchor・本体）。
- 変更（必要時のみ）: `docs/LEARNINGS.md` — guard-only 完了宣言と install-source 解決の教訓を confidence 付きで追記（docs フェーズ）。
- production code・profile JSON・README: **無改変**（新 script 同梱なし＝profile 件数不変）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `_DOC_TEMPLATE_REMAP`, `_doc_install_source` | なし |
| Task 2 | アンカーテスト（コメント耐性 parse） | Task 1 の resolver, Task 4 の surfaces, setup.sh:resolve_source |
| Task 3 | doc edge の単体（**既存 `_skill_script_edges` 再利用・新関数なし**） | 既存 `_skill_script_edges`/`_SKILL_SCRIPT_RE` |
| Task 4 | `_shipped_doc_surfaces` | なし |
| Task 5 | `INTENTIONAL_UNSHIPPED_DOC` ＋ governance テスト | Task 4, 既存 `_skill_script_edges`/`_violations`/`_shipped_scripts_any` |
| Task 6 | 本体 cross-check ＋ RED→GREEN 実証 | Task 1,3,4,5 |

循環なし。各 Consumes は既存 helper か先行 Task の Produces。

## タスク分解

> 全タスク TDD RED-first。本ファイルは test なので「helper の不在/誤りで unit が FAIL→helper 実装で PASS」が RED→GREEN。guard 本体の歯は allow-list トグルで実証（Task 6）。

### タスク 1: doc install-source resolver

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** `tests/test_profile_referential_integrity.py`
**意図:** profile entry の doc を install 実体パスに解決。CLAUDE.md→`templates/CLAUDE.template.md`、rules→verbatim。明示 map で fail-closed。
**TDD:**
- RED: `test_doc_source_claude_is_template`（CLAUDE.md→templates/CLAUDE.template.md）／`test_doc_source_rules_is_verbatim`（.claude/rules/state-machine.md→同パス verbatim）を書き FAIL 確認。
- GREEN: `_DOC_TEMPLATE_REMAP = {"CLAUDE.md": "templates/CLAUDE.template.md"}` ＋ `_doc_install_source(rel)` 実装。
**受入条件:** 両 unit PASS。
**Deliverable:** [ ] resolver 存在 [ ] unit カバー

### タスク 2: アンカーテスト（setup.sh と同期強制）

**blockedBy:** Task 1 | **モデル:** `inherit`
**意図:** `setup.sh:resolve_source` の case を抽出し、全 doc surface で resolver が setup.sh と一致することを assert。drift を**明示 fail**。
**grill-plan ①（致命）反映＝コメント耐性 parse**: 素朴な `"([^"]+)"\)\s+echo...` は setup.sh の `retro.md` のように `)` と `echo` の間にコメント行がある case を取りこぼす。将来 rules remap がコメント付きで追加されると parse が拾えず、`setup_remap.get(rules,rel)=rel(verbatim)` と resolver の verbatim が**偶然一致して PASS＝fail-open**（install 実体とズレた source を読む）。本イテレーションの fail-closed 哲学を裏切るため、`)`〜`echo` 間をコメント耐性にする。
**TDD:**
- RED: `test_doc_resolver_matches_setup_sh`。parse 正規表現 `r'"([^"]+)"\)[^"]*?echo\s+"\$FRAMEWORK_ROOT/([^"]+)"'`（`[^"]*?` は引用符を含まずコメントを飲み込み、次 case の `"label"` を越えない＝case 境界で停止。DOTALL 不要）。`setup_remap` 構築 → `assert "CLAUDE.md" in setup_remap`（parse 健全性の明示 fail）。
- 列挙元（grill-plan ④）: **全 profile の `_shipped_doc_surfaces` の和集合**を回し、各 surface で `_doc_install_source(rel) == ROOT/setup_remap.get(rel, rel)`。加えて `_DOC_TEMPLATE_REMAP` の各 key が実 surface 集合に含まれること（dead 設定禁止）を assert。
- コメント耐性単体（grill-plan ①）: 合成 setup ソース（`)` と `echo` の間にコメント行を挟んだ case）から remap を拾えることを固定する `test_setup_parse_tolerates_comment_between_case_and_echo`。
- GREEN: 実装一致で PASS。
**受入条件:** PASS。setup.sh に rules remap を足す/CLAUDE.md template パス変更/コメント付き remap 追加のいずれでも FAIL する（コメント付き手動 1 回確認）。
**Deliverable:** [ ] アンカー存在 [ ] コメント耐性 parse [ ] 健全性＋dead-key assert

### タスク 3: doc edge 抽出（既存 `_skill_script_edges` を再利用＝YAGNI 反映）

**blockedBy:** なし | **モデル:** `inherit`
**意図:** doc 本文から `scripts/*.(py|sh)` を抽出。grill-plan YAGNI 反映＝新関数を起こさず**既存 `_skill_script_edges`（共有 `_SKILL_SCRIPT_RE`）を直接再利用**。near-duplicate な正規表現ロジックの二重保守を避ける。`_SKILL_SCRIPT_RE` が doc 面も指すことを1コメントで補足。
**TDD:**
- 既存 `_skill_script_edges` の単体は iter49 で担保済。doc 経路の意図確認として `test_doc_edges_picks_check_contract`（CLAUDE.template.md 想定文 `enforced by scripts/check_framework_contract.py` を拾う）を1本だけ追加（共有関数の doc 適用を固定）。
**受入条件:** unit PASS。新規 `_doc_script_edges` 関数は作らない。
**Deliverable:** [ ] 共有関数の doc 適用 unit [ ] 重複関数なし

### タスク 4: `_shipped_doc_surfaces`

**blockedBy:** なし | **モデル:** `inherit`
**意図:** profile entry のうち install-surface doc（`CLAUDE.md` ∪ `.claude/rules/*.md`）を返す。commands/agents/skills は除外。
**TDD:**
- RED: `test_shipped_doc_surfaces_selects_claude_and_rules`（合成 profile で CLAUDE.md と rules のみ選別・commands/agents 除外）を書き FAIL。
- GREEN: 実装。
**受入条件:** unit PASS。
**Deliverable:** [ ] 選別関数存在 [ ] 除外境界 unit

### タスク 5: allow-list ＋ governance

**blockedBy:** Task 3, Task 4 | **モデル:** `inherit`
**意図:** install 実体 CLAUDE.md（template）が参照する `scripts/check_framework_contract.py` を3 profile で理由付き waive。reason 非空＋rot 検知。
**TDD:**
- RED: `test_doc_allowlist_reasons_nonempty`／`test_doc_allowlist_no_stale_or_redundant`（stale=未参照／redundant=同梱済みを禁止。既存 iter48 rot テストと同型）を書き、`INTENTIONAL_UNSHIPPED_DOC` 不在/空で FAIL。
- GREEN: `INTENTIONAL_UNSHIPPED_DOC = {full/standard/minimal: {"scripts/check_framework_contract.py": "<maintainer 専用・install 単体は新版観測不能・**referrer は CLAUDE.md の記述的 provenance（template L41「enforced by …」）であって実行指示でない**。.py 層 allow-list（referrer=status_doctor.py・full のみ）とは referrer/scope が異なる同一 script の別宣言>"}}` を実装。
**grill-plan ③ 反映**: 同一 script が `.py 層`(full のみ)と `doc 層`(3 profile)の2箇所に出るため、両 allow-list 定義の近くに相互参照コメント（referrer が status_doctor.py vs CLAUDE.md と異なる旨）を置き、将来「重複では?」の誤読を防ぐ。
**受入条件:** governance unit PASS。reason に referrer 差を明記。
**Deliverable:** [ ] allow-list 存在 [ ] reason 非空＋rot テスト [ ] cross-ref コメント

### タスク 6: 本体 cross-check ＋ RED→GREEN 実証

**blockedBy:** Task 1-5 | **モデル:** `inherit`
**意図:** 各 profile × 各 shipped doc surface を install 実体で読み、`_violations`（共有純関数）で「同梱 ∨ allow-list」を検査。
**TDD（guard の歯の実証）:**
- RED 実証: `INTENTIONAL_UNSHIPPED_DOC` を**一時的に空**にして本体 `test_every_profile_doc_script_ref_is_self_contained()` を走らせ、CLAUDE.md→check_framework_contract.py が3 profile で違反検出されることを観測（手動・iter48 の「map 除去で二重実測」と同型）。
- GREEN: allow-list を戻して PASS。
- negative-control unit: 合成（shipped=空・edges={scripts/x.py}・allow={}）で違反、allow に理由付きで非違反（共有 `_violations` の既存テストで担保＝重複実装しない）。
- grill-plan ⑤ 反映（qa 方針）: doc 経路固有の自動 negative-control は持たず**共有 `_violations` ＋ resolver/anchor 単体の合成で歯を担保**する方針を qa レポートに明記。qa の B1 drill は本体 `test_every_profile_doc_script_ref_is_self_contained` の coverage を対象に、必要なら doc surface へのダミー参照注入で mutant を立てる。
**受入条件:** 本体 PASS・full suite green・contract PASS。
**Deliverable:** [ ] 本体存在 [ ] RED→GREEN を手動実測 [ ] qa 方針を明記

## 事前準備

- [x] 環境・依存（python3/pytest）あり
- [x] ベースブランチ最新（origin/main=d7192d0、anchor 8d4ea49）
- [x] 対象ファイル（test_profile_referential_integrity.py・setup.sh・CLAUDE.template.md）把握済

## トレーサビリティ

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| (内部 guard) install 実体 doc→script の参照整合 | doc が未同梱 script を参照したら検出 | Task 1-6 | `tests/test_profile_referential_integrity.py` |
| install-source の忠実性 | resolver が setup.sh と同期 | Task 2 | 同上（アンカー） |
| allow-list の劣化防止 | stale/redundant/空 reason を禁止 | Task 5 | 同上（governance） |

要件は内部 guard 1 本。全 Task でカバー。

## 自己レビュー

- 仕様カバレッジ: SPEC のコンポーネント（resolver/アンカー/edge/surface/allow-list/本体）全てに Task 対応。
- 曖昧さ: resolver は「map ヒット=template／else verbatim」で一意。
- 型整合: helper 名は SPEC と一致（`_doc_install_source`/`_doc_script_edges`/`_shipped_doc_surfaces`/`INTENTIONAL_UNSHIPPED_DOC`）。
- 境界整合: Consumes（`_violations`/`_shipped_scripts_any`/`_SKILL_SCRIPT_RE`）は既存実在。

## 設計決定の記録（grill-plan ② — 3年後の再litigate 防止）

- **決定**: `check_framework_contract.py` は doc 層で **allow-list（案X）**。template L41 の参照を消す案Y は**不採用**。
- **理由**: template L41「Agent model/effort is pinned by role tier (enforced by `scripts/check_framework_contract.py`); applies once agents are installed (the full profile)」は**どこで pin が enforce されるかの記述的 provenance**。利用者の理解に資する有用情報で、消すと install 利用者の mental model を削る。allow-list は「非同梱 script の意図的言及」を marking する正しい受け皿（実行指示ではないので dangling instruction ではない）。
- **不採用**: 案Y（template から script 名除去）＝有用情報の損失。ship する案（check_framework_contract.py を install 同梱）も iter48 で却下済（依存閉包 platform_manifest+context_budget を install に引き込まない）。

## リスク

- リスク: アンカーの setup.sh 正規表現が将来の case 整形変更で誤抽出。
- 対策: `assert "CLAUDE.md" in setup_remap` で parse 健全性を明示 fail させる（沈黙劣化を作らない＝本イテレーションの哲学そのもの）。
- リスク: guard-only ゆえ「成果が無い」と誤認。
- 対策: 成果は「全 install surface を1原理で網羅＋maintainer 参照の allow-list 明示化」と honest framing。実穴主張はしない。

## 完了条件

- [ ] 全テスト pass（test file ＋ full suite green）
- [ ] contract PASS
- [ ] 本体 guard の RED→GREEN を手動実測（allow-list トグル）
- [ ] review（必須）／qa（B1 mutation）／security 通過
- [ ] LEARNINGS 追記（confidence 付き）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

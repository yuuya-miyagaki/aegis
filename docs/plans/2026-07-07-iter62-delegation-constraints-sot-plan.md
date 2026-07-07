# 実装計画: iter62 委譲拘束 SoT 標準化（R1 文言層）

> **For agentic workers:** 本計画は aegis の dev フロー（TDD RED-first・単一 feat コミット・
> gate 完走）で実行する。superpowers:executing-plans 相当のインライン実行を想定。

## 目的

- この変更で達成すること: 検証系サブエージェント委譲の標準拘束（6点・核=read-only/tree 変更
  禁止）を `.claude/rules/routing.md` に単一正本で設置し、qa-verification／aegis-review-gate／
  aegis-security-gate／subagent-dev の4経路から参照させ、token-pin で drift を機械封鎖する。
  iter60 事故クラス（検証 subagent の `git checkout docs/*` による親 tree 破壊）の文言層防御
  （全体レビュー R1 修正方向(1)・Phase 0-1）。

## 入力

- 参照要件: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1・§4 Phase 0-1
- 参照設計: docs/specs/2026-07-07-iter62-delegation-constraints-sot-design.md

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（Claude Code 運用フレームワーク＝git リポジトリ配布・デプロイ対象なし）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ対象なし。L サイズのため deploy gate は
  iter54 前例に従い「対象なし宣言＋ゲート前提確認」レポート `docs/qa-reports/iter62-deploy.md`
  で承認する）

### 認証方式

- 認証プロバイダ: None（n/a）
- DEMO_MODE 予定: n/a

## Git 戦略

main 直コミット（aegis 慣行: 実装＋docs＋STATUS を最終1 feat コミット・push 手前停止・
fix-forward は追記コミット）。per-task コミットはしない（gate 簿記が未コミットで進行するため）。

## ファイル構造（変更マップ）

- 変更: `.claude/rules/routing.md` — 「## Verification delegation」節を追加（単一正本・英語）
- 変更: `.claude/skills/qa-verification/SKILL.md` — qa-browser 委譲ルールに6点目（read-only）追加
- 変更: `.claude/skills/aegis-review-gate/SKILL.md` — 盲検2次節に拘束参照を追加
- 変更: `.claude/skills/aegis-security-gate/SKILL.md` — 同上（iter60 事故経路）
- 変更: `.claude/skills/subagent-dev/SKILL.md` — コアルールに5点目（検証系委譲の拘束参照）追加
- テスト: `tests/test_skill_guidance_tokens.py` — `TestVerificationDelegationSoT` クラス追加
- 変更: `scripts/context-budgets.json` — routing.md 70→181・qa-verification 455→459（実測どおり）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | pin テスト（RED） | 確定文言（本計画） |
| Task 2 | routing.md SoT 節 | Task 1 の pin |
| Task 3 | 消費側4ファイルの参照 | Task 1 の pin・Task 2 の節名 |
| Task 4 | budgets.json 更新・budget check PASS | Task 2/3 の実語数 |
| Task 5 | full suite green・contract PASS | Task 1-4 |

循環依存なし。

## 確定文言（正本・実装時にこのまま使用）

### A. routing.md 追加節（「## Subagent continuation」の直後・ファイル末尾）

```markdown
## Verification delegation

Standard constraints for every verification dispatch (review first and
blind-second, security, qa, qa-browser, specialist reviewers). Carry them in
the delegation prompt. 1-5 apply as written to itemized work; 6 is unconditional.

1. Split: bounded batch, numbered items.
2. Completion: no final report until every item has evidence; partial is never final.
3. Resume: continue the same agent (see Subagent continuation).
4. Progress: report per item.
5. Evidence: per item {action, expected, observed, verdict}.
6. Read-only: MUST NOT modify existing files, MUST NOT run
   git checkout/restore/reset/clean/stash; the only allowed writes are new
   evidence artifacts on the assigned path. If the tree gets dirty:
   stop, report, do not touch it.
```

- 注意: 拘束3は既存 pin（`SendMessage` の routing.md 内一意性・iter59）を壊さないため
  `SendMessage` の語を**使わない**（「continue the same agent」＋節参照で表現）。
- pin 核: `## Verification delegation`（一意）／`MUST NOT modify existing files`（否定句・
  行内完結）／`checkout/restore/reset/clean/stash`（連結 token・一意・1コマンド脱落で RED）／
  `stop, report, do not touch it`（行内完結）／`6 is unconditional`。

### B. qa-verification「qa-browser 委譲ルール」5点の直後に追加

```markdown
6. **read-only**: tree 変更禁止＝既存ファイル編集・`git checkout/restore/reset/clean/stash` 実行禁止。書込みは指定パスへの新規 evidence 成果物のみ。汚れたら停止して報告し、自己復旧しない。正本: routing.md「Verification delegation」。
```

### C. aegis-review-gate／aegis-security-gate「盲検 第2意見」第1段落の直後に追加（同文）

```markdown
委譲プロンプトには routing.md「Verification delegation」の6拘束を必ず含める（核＝read-only: tree 変更禁止・`git checkout/restore/reset/clean/stash` 禁止）。
```

### D. subagent-dev「コアルール」4点の直後に追加

```markdown
5. **レビュー/検証系サブエージェント**（Step 3/3.5/4 の reviewer 系）の委譲プロンプトには routing.md「Verification delegation」の6拘束（核＝read-only・tree 変更禁止）を含める
```

### E. budget 実測（2026-07-07・`_budget_word_count` で計測済み）

| ファイル | 現在 | 追加 | 新計 | budget 現行 | 措置 |
|---|---|---|---|---|---|
| routing.md | 70 | +111 | 181 | 70 | **181 へ raise**（追加分ちょうど・iter59 教訓） |
| qa-verification | 449 | +10 | 459 | 455 | **459 へ raise** |
| aegis-review-gate | 252 | +7 | 259 | 278 | 据置（headroom 内） |
| aegis-security-gate | 238 | +7 | 245 | 262 | 据置 |
| subagent-dev | 428 | +9 | 437 | 442 | 据置 |

## タスク分解

### タスク 1: token-pin テスト追加（RED 実証）

**blockedBy:** なし ｜ **モデル:** inherit（インライン実行）
**ファイル:** テスト `tests/test_skill_guidance_tokens.py`
**意図:** SoT と4経路参照の load-bearing token を pin し、md 未編集の現状で RED を実証する。
**TDD:** テスト → FAIL確認 → （Task 2/3 で）実装 → PASS確認

- [ ] Step 1-1: モジュール先頭の読み込み群（`CW`/`QA`/`ROUTING`）の直後に3ファイルを追加:

```python
RG = (ROOT / ".claude" / "skills" / "aegis-review-gate" / "SKILL.md").read_text(encoding="utf-8")
SG = (ROOT / ".claude" / "skills" / "aegis-security-gate" / "SKILL.md").read_text(encoding="utf-8")
SD = (ROOT / ".claude" / "skills" / "subagent-dev" / "SKILL.md").read_text(encoding="utf-8")
```

（既存 `TestSharedMutableResourceRule` はメソッド内で subagent-dev を読む。重複読込は無害だが、
モジュール変数 `SD` へ置換して一元化する）

- [ ] Step 1-2: ファイル末尾（`if __name__` の前）に新クラスを追加:

```python
class TestVerificationDelegationSoT(unittest.TestCase):
    """iter62: 検証系委譲の標準拘束雛形（全体レビュー R1 文言層）。routing.md が単一正本
    （6拘束・6点目 read-only は無条件）、qa-verification／aegis-review-gate／
    aegis-security-gate／subagent-dev の4経路が参照。iter60 事故（security 盲検2次の
    `git checkout docs/*` が親の未コミット gate 簿記を revert）の文言層防御＝
    機械層(patterns.sh)・復旧層(snapshot 退行ガード)は iter61 で封鎖済み。
    短核 token pin（長文完全一致は言い換えで false RED）＋否定句 pin（iter59: 単トークン
    だと NOT 脱落の意味反転を false-PASS）＋一意 count==1（単一削除・重複増殖の両方で RED）。
    正本節の拘束3は SendMessage の語を意図的に使わない（TestSubagentContinuationSoT の
    routing.md 内一意性〔単一削除で RED〕を保全するため。grill-plan 要検討2）。"""

    def test_sot_section_present_and_unique(self):
        self.assertEqual(
            ROUTING.count("## Verification delegation"), 1,
            "検証系委譲拘束の単一正本節が routing.md に1つだけ存在すべき（消失/重複）")

    def test_readonly_negation_phrase_present(self):
        # 否定句で pin（"NOT" 脱落による read-only→書込み許可の意味反転を捕捉）。
        self.assertIn("MUST NOT modify existing files", ROUTING,
                      "6点目 read-only の禁止句（MUST NOT modify existing files）が消えた/反転している")

    def test_banned_git_commands_enumerated(self):
        # 連結 token で pin（1コマンド脱落でも RED）。iter60 事故は checkout、iter61 機械層は
        # restore/stash も封鎖済み＝文言層は同じ集合＋reset/clean を列挙する。
        self.assertEqual(
            ROUTING.count("checkout/restore/reset/clean/stash"), 1,
            "禁止 git コマンド列挙（checkout/restore/reset/clean/stash）が消えた/欠けた/重複した")

    def test_dirty_tree_protocol_present(self):
        self.assertIn("stop, report, do not touch it", ROUTING,
                      "tree 汚染時の停止・報告・自己復旧禁止プロトコルが消えている")

    def test_readonly_is_unconditional(self):
        self.assertIn("6 is unconditional", ROUTING,
                      "6点目 read-only の無条件適用宣言が消えている（1-5 は itemized 作業向け）")

    def test_consumers_reference_sot(self):
        # 4経路すべてが正本節名を参照する（正本改名・節削除・参照落ちの両側検知）。
        for name, text in (("qa-verification", QA), ("aegis-review-gate", RG),
                           ("aegis-security-gate", SG), ("subagent-dev", SD)):
            with self.subTest(consumer=name):
                self.assertIn("Verification delegation", text,
                              f"{name} から委譲拘束 SoT への参照が消えている")

    def test_consumers_carry_readonly_core(self):
        # 参照だけでなく read-only 核（tree 変更禁止）を委譲文言側にも保持する
        # （iter60: 参照先を読まない subagent には届かない＝核はインライン必須）。
        for name, text in (("qa-verification", QA), ("aegis-review-gate", RG),
                           ("aegis-security-gate", SG), ("subagent-dev", SD)):
            with self.subTest(consumer=name):
                self.assertIn("tree 変更禁止", text,
                              f"{name} の委譲文言から read-only 核（tree 変更禁止）が消えている")
```

- [ ] Step 1-3: RED 実証:

```bash
python3 -m pytest tests/test_skill_guidance_tokens.py -v 2>&1 | tail -15
```

期待: `TestVerificationDelegationSoT` の 7 テストが FAIL、既存クラスは全 PASS。

### タスク 2: routing.md に SoT 節を追加

**blockedBy:** Task 1 ｜ **モデル:** inherit
**ファイル:** 対象 `.claude/rules/routing.md`
**意図:** 確定文言 A をファイル末尾（Subagent continuation 節の後）に追加する。

- [ ] Step 2-1: 確定文言 A をそのまま追記（Edit）。
- [ ] Step 2-2: routing 系 pin の GREEN 確認:

```bash
python3 -m pytest tests/test_skill_guidance_tokens.py -k "Continuation or VerificationDelegation" -v 2>&1 | tail -12
```

（grill 致命3: "Routing" を名に含むテストは存在しない＝空マッチで検証意図が偽装されるため除去）

期待: `test_sot_section_present_and_unique`／`test_readonly_negation_phrase_present`／
`test_banned_git_commands_enumerated`／`test_dirty_tree_protocol_present`／
`test_readonly_is_unconditional` が PASS へ。`TestSubagentContinuationSoT` は PASS 維持
（`SendMessage` 一意性不変）。`test_consumers_*` は未 GREEN（Task 3 で解消）。

### タスク 3: 消費側4ファイルへ参照＋核を追加

**blockedBy:** Task 2 ｜ **モデル:** inherit
**ファイル:** 対象 `.claude/skills/qa-verification/SKILL.md`・`.claude/skills/aegis-review-gate/SKILL.md`・`.claude/skills/aegis-security-gate/SKILL.md`・`.claude/skills/subagent-dev/SKILL.md`
**意図:** 確定文言 B/C/D を各所定位置へ追加する。

- [ ] Step 3-1: qa-verification — 「qa-browser 委譲ルール」の item 5（エビデンス）の直後に B を追加。
- [ ] Step 3-2: aegis-review-gate — 「盲検 第2意見」第1段落（…claims ブロックに記録する:）の
      claims コードブロックの後、「注:」段落の前に C を追加。
- [ ] Step 3-3: aegis-security-gate — 同位置に C を追加。
- [ ] Step 3-4: subagent-dev — 「コアルール」item 4 の直後に D を追加。
- [ ] Step 3-5: 全 pin GREEN 確認:

```bash
python3 -m pytest tests/test_skill_guidance_tokens.py -v 2>&1 | tail -8
```

期待: 全テスト PASS（既存クラス含む）。

### タスク 4: context-budgets.json raise＋budget check

**blockedBy:** Task 3 ｜ **モデル:** inherit
**ファイル:** 対象 `scripts/context-budgets.json`
**意図:** 実測どおり routing.md 70→181・qa-verification 455→459 へ raise（追加分ちょうど）。

- [ ] Step 4-1: `".claude/rules/routing.md": 70` → `181`、
      `".claude/skills/qa-verification/SKILL.md": 455` → `459` に Edit。
- [ ] Step 4-2: 実語数と budget の一致確認＋全体 check（grill 致命1: パイプ経由の rc は
      tail の rc になる偽検証＝罠(a)同族。出力は短いので直接実行する）:

```bash
python3 scripts/context_budget.py; echo "rc=$?"
```

期待: FAIL 出力なし・rc=0。

### タスク 5: full suite＋contract 検証

**blockedBy:** Task 4 ｜ **モデル:** inherit
**意図:** 退行ゼロを確認して implement を閉じる（record-test-result はこの後・qa フェーズ手順で）。

- [ ] Step 5-1: `python3 -m pytest tests/ -q 2>&1 | tail -5` — 期待: 全 passed（iter61 時点 1063 passed 相当＋新7）。
- [ ] Step 5-2: `python3 scripts/check_framework_contract.py 2>&1 | tail -5` — 期待: PASS。
- [ ] Step 5-3: `python3 scripts/check_status.py 2>&1 | tail -3` — 期待: PASS。

## External Integrations

n/a（外部連携なし）

## 事前準備

- [x] working tree clean・origin/main 同期済み（rollover 時に確認済み）
- [x] budget 実測済み（確定文言 E 表）

## トレーサビリティ（要件 → Task → Test）

| 要件（R1 修正方向(1)） | Task | テスト |
|------|------|--------------|
| routing.md に標準拘束雛形を単一正本で設置 | Task 2 | `test_sot_section_present_and_unique` ほか routing pin 4本 |
| 6点目 read-only（tree 変更禁止・汚したら報告して触るな） | Task 2 | `test_readonly_negation_phrase_present`・`test_banned_git_commands_enumerated`・`test_dirty_tree_protocol_present`・`test_readonly_is_unconditional` |
| qa-verification 5点＋6点目 | Task 3 | `test_consumers_reference_sot`・`test_consumers_carry_readonly_core`（qa） |
| review/security/subagent-dev から参照 | Task 3 | 同上（各 subTest） |
| token-pin（drift 機械検知） | Task 1 | クラス全体（RED-first で pin 有効性を実証） |
| budget 整合（headroom 0 対応） | Task 4 | `context_budget.py` check rc=0 |

## 自己レビュー

- 仕様カバレッジ: R1 修正方向(1) の全要素（正本・6点目・4経路参照・token-pin）に Task あり
- 曖昧さ: 文言は「確定文言」節で固定（grill-plan が grep 検証可能）
- 型整合: pin 文字列は確定文言からの逐語コピー（Task 1 ⇔ Task 2/3）
- 境界整合: Boundary Map どおり（循環なし）

## リスク

- リスク1: 新節の `SendMessage` 使用が既存 pin の一意性を破壊 → 対策: 確定文言 A は
  `SendMessage` の語を使わない（検証済み・pin `test_continuation_mechanism_present` は assertIn
  だが docstring が一意性を根拠にしており重複させない）。
- リスク2: 連結 token `checkout/restore/reset/clean/stash` が qa-verification 既存文
  （ドリル節等）と衝突・重複 → 対策: count==1 は routing.md のみに適用。消費側は assertIn。
- リスク3: guidance 追加が既存 budget の別ファイルを押し出す → 対策: E 表で実測済み・
  raise は routing/qa の2件のみ・Task 4 で check rc=0 を機械確認。
- リスク4: B1 drill の coverage floor が test/json ハンクで割れる → 対策（grill 要検討1 で精緻化）:
  第一候補=実 drill。md 追加行の mutant（token 削除/`MUST NOT`→`MAY` 反転→pin テスト赤化）＋
  json ハンクの mutant（budget 181→100 等→`test_real_repo_check_is_green` 赤化）。
  `test_command` は `python3 -m pytest tests/test_skill_guidance_tokens.py tests/test_context_budget.py -q`
  の2ファイルスコープ。**skip 切替の閾値＝テストファイル自身のハンクへの mutant が floor に要求された
  場合のみ**（自己参照 mutant は意味が薄い＝iter59/60 前例の skip＋手動 mutation 実証へ・reason 明記）。
- リスク5: C 文言（review/security 同文）は将来独立編集で乖離しうる → 受容: pin は核
  （tree 変更禁止・参照名）のみ縛る設計＝表現乖離は許容範囲。乖離が核に及べば pin が RED。

## 完了条件

- [ ] 全テスト pass（full suite）・contract PASS・budget check PASS
- [ ] grill-code 完了（致命は fix-forward）
- [ ] review（1次＋盲検2次・**委譲プロンプトに本 iter の6拘束を自己適用**）
- [ ] qa（B1 drill 実 mutant または skip＋手動 mutation・claims 付き QA レポート）
- [ ] security（1次＋盲検2次・同自己適用）
- [ ] deploy（L・対象なし宣言レポート `docs/qa-reports/iter62-deploy.md`。**grill 致命2: deploy は
      JUDGE_GATES＝judge が ref の claims を読むため、iter54-deploy.md 形式踏襲＝Deploy Target
      n/a 宣言＋前提ゲート確認＋末尾 claims ブロック（`verdict: approve`）必須**）
- [ ] ship（v1.22.0→v1.23.0・bump 3箇所）
- [ ] docs（LEARNINGS 蒸留・session_history 追記・push 手前停止）

## QA チェックリスト

- [ ] pin 7テストが md 未編集状態で RED だった証跡（Task 1 Step 1-3 の出力）
- [ ] 全 pin GREEN＋既存 pin 退行なし（full suite）
- [ ] budget: routing=181・qa-verification=459 の実測一致・check rc=0
- [ ] 確定文言 A-D が実ファイルに逐語存在（grep）
- [ ] 既存 `SendMessage` pin の一意性維持（routing.md 内 1 回のみ）
- [ ] contract PASS・STATUS 整合

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

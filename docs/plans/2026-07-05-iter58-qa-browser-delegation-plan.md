# iter58 qa-browser 委譲プロンプト標準化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: implement は Aegis の `tdd` / `subagent-dev` skill に従う（RED-first・per-task commit）。Steps はチェックボックス（`- [ ]`）で追跡する。
> **正本**: 設計 = `docs/specs/2026-07-05-iter58-qa-browser-delegation-design.md` / brainstorm = 同 `-brainstorm-record.md`。
> **grill-plan 反映済（2026-07-05）**: 致命1（qa.md 単一正本化）・要検討1(短核pin)・要検討2(一致注記)・要検討3↔5(intro圧縮でheadroom優先)・要検討4(クラス名)を織り込み。

**Goal:** qa→qa-browser の委譲を「≤5 項目・全項目エビデンス充足まで最終報告禁止・SendMessage 再開」を含む標準委譲プロンプト雛形へ昇格し、核心命令の silent 消失を token pin テストで機械検出できるようにする。**委譲 guidance の正本を qa-verification skill に一本化**する（qa.md の重複記述を排除）。

**Architecture:** guidance のみ（hook で決定論強制はしない）。`qa-verification SKILL.md` の「qa-browser 委譲ルール」節を拘束5点の標準委譲プロンプト雛形に置換＝**単一正本**。`qa.md` の「Browser QA」節はこの skill を参照する形へ縮約（重複排除・drift 源除去）。`tests/test_skill_guidance_tokens.py` に load-bearing トークン（完了拘束の短核・`SendMessage`）を追加 pin（決定論トリップワイヤ）。判定・ゲート機構（judge / check_status）には手を入れない。

**Tech Stack:** Markdown skill / agent def（`.claude/skills/qa-verification/SKILL.md`, `.claude/agents/qa.md`）、Python `unittest`（`tests/test_skill_guidance_tokens.py`）、`scripts/context_budget.py`（語数予算ラチェット）。

## Global Constraints

- **語数予算（最重要）**: `.claude/skills/qa-verification/SKILL.md` の budget = **455 words**（`scripts/context-budgets.json`・空白区切りトークン `len(text.split())`）。**改修後も ≤455 を厳守**。budget 引き上げは行わない（tighten-only ラチェットの anti-bloat 趣旨・設計決定「割らない＝表現圧縮」）。**実測目標 = 449（headroom 6）**。`.claude/agents/qa.md` は budget 対象外（`iter_targets` は skills/rules のみ）。
- **headroom を残す（grill 要検討5）**: framework file は後続 review/qa/security の3ゲートが再度触りうる。headroom 0 は1語追加で contract FAIL＝脆い。よって intro boilerplate を圧縮して **headroom 6** を確保する（grill 要検討3「intro 温存」より headroom を優先＝トレードオフの明示判断）。skill 本文を触る step の後は必ず `context_budget.py` を再走。
- **pin は短核・RED-first 実証済（grill 要検討1）**: 完全一致18字の長文 pin は正当な言い換えで false RED を招く。**短核 `最終報告を出さない`（報告抑制）＋ `全項目のエビデンス`（完全性）＋ `SendMessage`（再開）** を pin。3トークンとも現行 skill に不在（grep count 0＝RED-first 成立を実測確認済）。進捗形式 `[n/N done]`・エビデンス brace は軟らかい要素＝**pin しない**（過剰固定回避・設計 §テスト戦略）。
- **pin 文字列の一致・連続（grill 要検討2）**: pin 文字列は skill 本文・テスト assert・本 plan で**バイト一致**。skill 側で pin 部分文字列の**内部に markdown を差し込まない**（現案は `**…**` が phrase 全体を包む＝連続 OK）。skill と test の変更は必ず同時。
- **既存 pin を壊さない**: `TestQaBrowserDelegationGranularity` が `"5 項目程度"` と `"19 項目"` を assert 済。新雛形にも**この2トークンを逐語で残す**。
- **新規ファイルを作らない（YAGNI）**: 雛形は qa-verification skill にインライン。browser-assist へのテンプレ切り出し（Option 3）は descope。
- **判定機構不変**: qa ゲートの judge / `check_status.py` / drill は不変（Option 2 決定論バックストップは descope）。
- **言語**: skill 本文・計画は日本語（既存踏襲）。`qa.md` は英語制御ファイル（既存踏襲）で編集も英語。
- **SemVer**: v1.18.0 → **v1.19.0（MINOR）**。skill guidance の後方互換な追加・公開/運用契約は不変。ship フェーズで bump（contract 定数＋STATUS テンプレ＋live STATUS の3箇所）。
- **規模**: **M**（framework・3ファイル: qa-verification SKILL.md ＋ test_skill_guidance_tokens.py ＋ qa.md）。M framework は review+qa+security 必須・**deploy 自動 exempt**。3ファイルは M（2-5）維持＝`update-task.sh` の size 変更不要。

---

## File Structure

| ファイル | 責務 | 変更 |
|---------|------|------|
| `.claude/skills/qa-verification/SKILL.md` | qa フェーズ手順の**単一正本**。委譲ルール節を標準委譲プロンプト雛形へ | Modify（委譲節 rewrite＋語数相殺2箇所） |
| `.claude/agents/qa.md` | qa エージェント def。Browser QA 節を skill 参照へ縮約（重複排除） | Modify（Browser QA 節 rewrite） |
| `tests/test_skill_guidance_tokens.py` | skill 本文 load-bearing トークンの drift ガード | Modify（クラス名変更＋2 assertion 追加） |

語数相殺（qa-verification 内・footprint はファイル数で数える＝ファイル増やさない）:
- **除去**: 「テストスイート実行手順」節末尾の ```` ``` 確認事項: … ``` ```` コードブロック（−15 tokens・直上の番号手順1-4を重複再掲する冗長）。
- **圧縮**: 先頭 intro blockquote ＋「いつ使うか」節（20→14 tokens・低価値プリアンブル＝headroom 原資）。

## 確定文言A — qa-verification 委譲節 rewrite（実測 52 tokens）

`## qa-browser 委譲ルール` 節（現 66-76 行）を以下で全置換:

```markdown
## qa-browser 委譲ルール

`ui_surface: true` の場合、qa-browser への**標準委譲プロンプト**は以下を満たす:

1. **分割**: 1委譲あたり **5 項目程度**・各項目に連番。実測:19 項目一括で途中停止3回。
2. **完了拘束**: **全項目のエビデンスが揃うまで最終報告を出さない**。途中停止も partial を final と偽らず、完了済/未完の項目番号を示す。
3. **再開**: 停止時は新規委譲でなく **SendMessage** で同一エージェントを継続。
4. **進捗**: 各項目完了ごとに `[n/N done]` を報告。
5. **エビデンス**: 項目ごとに `{操作, 期待, 実測, PASS/FAIL, screenshot/console}`。

返却を QA レポートに統合。SendMessage 再開も不能なら未完項目を blocker に記録（3-failure ルール）。
qa-browser は browser-assist（`.claude/skills/browser-assist/SKILL.md`）を使い、`$B` かPlaywright MCP で検証。
```

- 拘束5点＝設計 §コンポーネント分解と1対1（①分割 ②完了拘束 ③再開 ④進捗 ⑤エビデンス形式）。
- 逐語保持 pin: `5 項目程度` / `19 項目`。新 pin（連続文字列）: `全項目のエビデンス`・`最終報告を出さない`・`SendMessage`。

## 確定文言B — qa-verification intro 圧縮（20→14 tokens）

先頭〜「いつ使うか」を以下で置換:

```markdown
# QA 検証プロセス

> qa agent が QA フェーズで参照。再現・テスト実行・エビデンス収集を標準化し、根拠なき完了を防ぐ。

## いつ使うか

- qa フェーズの検証・テスト実行・エビデンス収集・再現手順の構造化。
```

## 確定文言C — qa-verification 確認事項ブロック除去（−15 tokens）

「## テストスイート実行手順」節の番号手順1-4の直後にある以下フェンスを削除（手順が同内容を既述＝冗長）:

```markdown
```
確認事項:
- テストコマンドが明記されているか
- 全テストが PASS か（FAIL がある場合は原因を記録）
- lint / type-check エラーがないか
```
```

除去後、手順4の下は空行1つを挟んで次節「## 再現手順テンプレート」へ直結。

## 確定文言D — qa.md「Browser QA」節を skill 参照へ縮約（致命1）

`.claude/agents/qa.md` の `## Browser QA (when ui_surface: true)` 節（現 37-51 行）を以下で全置換（英語・制御ファイル）:

```markdown
## Browser QA (when ui_surface: true)

When `STATUS.md` has `ui_surface: true`, delegate browser verification to
the `qa-browser` agent. Structure the delegation using the standard
delegation prompt in the `qa-verification` skill ("qa-browser 委譲ルール":
split into <=5 numbered items, withhold the final report until every item
has evidence, and resume a stalled agent via SendMessage rather than
re-delegating). qa-browser uses gstack `$B` when available, Playwright MCP
otherwise.

The qa-browser agent returns structured evidence (pass/fail results,
screenshot paths, error listings) but does not write files. Incorporate the
returned evidence into the QA report yourself.
```

- 効果: 委譲 guidance の正本が skill に一本化。qa.md は**拘束を再掲せず参照するだけ**なので、独立に drift する余地が消える（新たな token pin は不要＝YAGNI・SoT が singular）。
- 注意: `qa-verification` は**スキル名参照**でファイルパス参照ではない（reference_drift を新たに増やさない）。frontmatter 不変＝model policy 検査に影響なし。

---

## Task 1: 委譲プロンプト標準化 ＋ token pin（RED-first・単一タスク）

**Files:**
- Test: `tests/test_skill_guidance_tokens.py`（クラス改名＋2メソッド追加）
- Modify: `.claude/skills/qa-verification/SKILL.md`（確定文言A/B/C）
- Modify: `.claude/agents/qa.md`（確定文言D）

**Interfaces:**
- Consumes: 既存 `QA = (ROOT / ".claude" / "skills" / "qa-verification" / "SKILL.md").read_text(...)`（テスト冒頭で読込済・追加不要）。
- Produces: なし（テスト＋guidance 本文のみ・他タスク依存なし）。

> **なぜ1タスクか**: token pin テストと skill 本文は同時 landing 必須（committed RED テストは suite を壊す）。語数相殺・qa.md 参照化も委譲標準化の同一 deliverable。RED→GREEN→commit を1タスクに畳む。

- [ ] **Step 1: token pin の failing test を追加＋クラス改名**

`tests/test_skill_guidance_tokens.py` の `class TestQaBrowserDelegationGranularity` を **`class TestQaBrowserDelegation`** に改名（中身の `test_granularity_guidance_present` はそのまま残す）し、以下2メソッドを追加:

```python
    def test_completion_constraint_present(self):
        # 完全性の核＋報告抑制の核を短核で pin（長文完全一致は言い換えで false RED）。
        self.assertIn("全項目のエビデンス", QA,
                      "完了拘束の完全性（全項目のエビデンス充足）が消えている")
        self.assertIn("最終報告を出さない", QA,
                      "完了拘束の報告抑制（最終報告を出さない）が消えている")

    def test_resume_protocol_present(self):
        self.assertIn("SendMessage", QA,
                      "再開プロトコル（SendMessage で同一エージェント継続）が消えている")
```

- [ ] **Step 2: RED を確認（トークンは skill にまだ無い）**

Run: `python3 -m pytest tests/test_skill_guidance_tokens.py::TestQaBrowserDelegation -v`
Expected: `test_completion_constraint_present` と `test_resume_protocol_present` が **FAIL**。`test_granularity_guidance_present` は PASS のまま。
→ **RED-first の一次証拠**（3トークンとも現行 count 0 を実測済）。qa B1 drill でも再掲。

- [ ] **Step 3: qa-verification 委譲節を全置換（確定文言A）**

`.claude/skills/qa-verification/SKILL.md` の `## qa-browser 委譲ルール` 節を確定文言Aで全置換。

- [ ] **Step 4: qa-verification 語数相殺（確定文言B＋C）**

(a) 先頭〜「いつ使うか」を確定文言Bで置換、(b)「テストスイート実行手順」の `確認事項:` フェンスを確定文言Cのとおり削除。

- [ ] **Step 5: qa.md Browser QA 節を skill 参照へ縮約（確定文言D）**

`.claude/agents/qa.md` の `## Browser QA` 節を確定文言Dで全置換。

- [ ] **Step 6: GREEN を確認**

Run: `python3 -m pytest tests/test_skill_guidance_tokens.py -v`
Expected: 全 PASS（`TestQaBrowserDelegation` 3件＋既存 `TestQaRefIsClaimsReport` / `TestTranslationRefTiming` / `TestTemplateTableParity` / `TestSharedMutableResourceRule`）。

- [ ] **Step 7: 語数予算 ≤455 を確認（skill 編集後 必須）**

Run: `python3 scripts/context_budget.py`
Expected: 終了コード 0・FAIL なし。
補助: `python3 -c "print(len(open('.claude/skills/qa-verification/SKILL.md').read().split()))"` → **449**（≤455・headroom 6）。

- [ ] **Step 8: 参照ドリフト・契約を確認**

Run: `python3 scripts/check_framework_contract.py`
Expected: PASS（0 failure）。`browser-assist` パス参照は既存踏襲・qa.md は skill 名参照で新規パス無し。

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/qa-verification/SKILL.md .claude/agents/qa.md tests/test_skill_guidance_tokens.py
git commit -m "feat(iter58): qa-browser 委譲プロンプト標準化（拘束5点・SoT一本化）+ token pin"
```

---

## RED-first の qa B1 drill 代替実証（qa フェーズで使用・手順を固定）

docs/skill 変更＝mutant 対象コードなし → B1 drill は `{"skip":true,"reason":...}`（罠 p）。skip 理由に**手動 mutation 同等の代替実証**を明記する（罠 f の実 drill 不成立のため）。代替実証 = token pin の RED 確認:

1. GREEN 状態から `最終報告を出さない` を skill から一時削除。
2. `python3 -m pytest tests/test_skill_guidance_tokens.py::TestQaBrowserDelegation::test_completion_constraint_present -v` → **FAIL** を確認。
3. 復元 → 再実行で **PASS**（自己修復）。
4. 同手順を `SendMessage`（`test_resume_protocol_present`）でも実施。

qa レポート（claims 付き `docs/qa-reports/*iter58*.md`・罠 g/p）に記録し、`current_refs.qa` はそれを指す。

---

## Self-Review（spec + grill 突合）

- 設計 §推奨アプローチ「委譲ルール節を標準委譲プロンプト雛形へ置換＋token pin」→ Task 1 で充足。✅
- 設計 §コンポーネント分解 拘束5点 → 確定文言A の 1-5 と1対1。✅
- 設計「pin は完了拘束・SendMessage・5・進捗は緩め」→ 短核pin（`全項目のエビデンス`+`最終報告を出さない`+`SendMessage`）＋既存`5 項目程度`維持・進捗/brace 非pin。✅
- 設計 §依存「context_budget を割らない」→ Global Constraints＋Step 7 で ≤455（実測 449・headroom 6）。✅
- 設計 §テスト戦略「RED-first」→ Step 2（RED）→ Step 6（GREEN）＋qa B1 drill 代替実証。✅
- 設計 §移行「v1.18.0→v1.19.0 MINOR」→ Global Constraints に固定・ship で bump。✅
- **grill 致命1（qa.md SoT）** → 確定文言D＋Step 5 で解消。✅
- **grill 要検討1（短核pin）/2（一致・連続）/3↔5（intro圧縮でheadroom優先）/4（クラス改名）** → 全反映。✅
- Placeholder scan: TODO/TBD なし・全 code/文言ブロックは確定文言。✅
- 型/名称整合: 追加テストメソッド名は改名後クラス内で衝突なし・`QA` 変数は既存定義を消費。✅

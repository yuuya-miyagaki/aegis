# iter56 レビューレポート（review ゲート）

- 対象: origin/main..HEAD（iter56・8コミット）
- 仕様正本: docs/specs/2026-07-05-iter56-m2-feedback-design.md
- 実装計画: docs/plans/2026-07-05-iter56-m2-feedback-plan.md
- 1次レビュー方式: 10並列ファインダー（正しさ5角＋reuse/simplification/efficiency/altitude/conventions）
  → 実証検証（実行による反証確認）→ sweep 1体

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | ① check-secrets broad-dot 修正 | hooks/check-secrets.sh・tests/test_secrets_broad_dot_token.py | ✅ 完了 | grill-code 🔴 で境界を否定クラスへ反転（subshell/redirect 封鎖） |
| 2 | ⑥ full 配布整合＋方向4＋install 実在 | templates/profiles/full.json・scripts/check_framework_contract.py・tests/test_scripts_manifest_contract.py・tests/test_full_profile_runnable_scripts.py | ✅ 完了 | 実走で「4本」は数え漏れと判明→ intentional_unshipped 自己記述で解決（設計書に反映済） |
| 3 | ② qa ref 統一＋⑦b claims 雛形 | .claude/skills/qa-verification/SKILL.md・templates/{QA-REPORT,REVIEW,SECURITY-REVIEW}.template.md・tests/test_skill_guidance_tokens.py | ✅ 完了 | 語数 455/455（予算内・guidance token 維持） |
| 4 | ③ verdict 段階化＋⑦a 是正手順 | scripts/build-judge-card.py・tests/test_judge_card.py | ✅ 完了 | 値不正 🟡（grill-plan 致命2）含む |
| 5 | ⑤ spec-delta 肯定1行 | scripts/check_status.py・tests/test_spec_delta_review.py | ✅ 完了 | 判定不変・出力のみ追加 |
| 6 | ④ subagent-dev 共有可変資源 | .claude/skills/subagent-dev/SKILL.md | ✅ 完了 | docs のみ・token pin 追加 |
| 7 | 統合検証 | — | ✅ 完了 | full suite 1314 passed・contract/status/drift/lint PASS |

## Findings（1次・検証済みのみ）

### Critical — 該当なし（grill-code 🔴 1件は review 前に修正済み）

- （修正済・記録）`hooks/check-secrets.sh` — broad-dot 境界のデリミタ列挙 `;&|` が `)` `>` を
  漏らし `(cd sub && git add .)` がすり抜け。**実行で再現確認→否定クラス
  `[^[:alnum:]._/-]` へ反転して封鎖・回帰テスト追加**（コミット dacc6d2）。
  検挙方法＝実地実行（レビュー agent の静的指摘ではなく hook への実入力）。

### Major（本レビューで修正済み）

- `scripts/check_framework_contract.py` — intentional_unshipped の typo キーが
  死蔵除外として沈黙受理されていた（confidence 9）。→ manifest 非一致キーを
  「dead exemption」FAIL に（コミット fc6631e・テスト追加）。
- `templates/*.template.md × build-judge-card.py KNOWN_VERDICTS` — verdict enum の
  2ミラー drift リスク（confidence 8・altitude 指摘）。→ parity テスト
  `test_templates_list_all_known_verdicts` で機械固定（fc6631e）。
- `.claude/skills/qa-verification/SKILL.md` — 語数圧縮で「skip は欠陥ではない・
  撤去しない」の設計判断が消失（confidence 7・removed-behavior 指摘）。→ 復元（fc6631e）。

### Minor（対応済み）

- `tests/test_full_profile_runnable_scripts.py` — importlib 動的ロードは既存 conftest 流儀
  （sys.path＋通常 import）に不一致 → 通常 import へ（fc6631e）。

### 却下した候補（実証で反証・confidence 付き記録）

- 「`_parse_scalar` が `verdict: true` を bool 化し KNOWN_VERDICTS 検査を沈黙通過」→
  **反証**: 実行確認で `1次 verdict 値が不正/未記入: True` 🟡 が発火（not in frozenset は
  bool でも真＝可視）。
- 「second_opinion に verdict 欠落で沈黙」→ **反証**: v2=None は相違 🟡
  （`1次=approve / 2次=None`）が発火。
- 「`iteration: 2`（非引用）を extract_scalar_value が読めない」→ **反証**: 既存テスト
  `test_iteration_2_*` が非引用 frontmatter で GREEN（正規表現は非引用値を扱う）。
- 「`git add .~` 等の2文字目非パス文字ファイルの誤 deny」→ **受容**: 旧 regex でも
  同様に deny（後退ではない）・deny 側＝安全側・実在頻度極小。
- 「STATUS frontmatter が gate 承認で二重パース」→ **受容**: 承認は人間操作頻度・
  実測コスト無視可能（efficiency 指摘として記録のみ）。
- 「秘密テスト helper の重複」→ **受容**: repo 全 secrets テストの既存流儀。
- 「full.json intentional_unshipped と test INTENTIONAL_UNSHIPPED の2レジストリ」→
  **受容**: 用途が異なる（配布契約の除外 vs 依存閉包の除外）・双方に staleness
  トリップワイヤあり。統合は構造リアーキ候補として LEARNINGS へ。

## Evidence Checklist

- [x] diff を実読した（10ファインダー全員＋sweep が `git diff origin/main...HEAD` 実読）
- [x] plan/spec の受入条件と突合した（対照表・全7タスク実装済）
- [x] 未カバーのエッジケースを列挙した（却下候補として記録・実行反証付き）
- [x] 全 finding に severity と confidence を付与した

## 判定

- **PASS**（1次: approve）
- 理由: plan 全タスク実装済・Critical 0（grill-code 検出分は修正済）・Major 3件は
  本レビュー内で fix-forward 済・full suite 1314 passed・決定論検査（contract/status/
  drift/lint/budget）全 PASS。

## 盲検 第2意見（self-attested）

2次レビュアー（reviewer-maintainability 相当・fresh context・1次結論非開示）による
独立レビュー。verdict= approve_with_notes・指摘5件（Major 1・Minor 4）→ **全件解消済み**:

- **Major/8**: 値不正 🟡 検査が second-opinion 分岐内のみ＝qa ゲートで未記入プレース
  ホルダが 🟢 沈黙通過（「claims 未提出 🟡」より後退・仕様⑦b と矛盾）。
  **実測で再現確認→1次 verdict 検証を claims 存在時の常時検査へ昇格＋回帰テスト**。
- Minor/7: qa-verification 語数 455/455（残0語の時限状態）→ 449/455 に削減（残6語）。
- Minor/5: 否定クラスの残穴（`.~x` 等の2文字目非パス文字）のコメント言及なし →
  Known residual としてコメント追記（deny 側＝安全・`--` 回避可）。
- Minor/5: 仕様②(b)（TaskCompleted evidence 受理）の回帰テスト欠落 →
  `test_qa_ref_claims_report_is_accepted` 追加。
- Minor/4: parity テストの assertIn 部分文字列判定（approve ⊂ approve_with_notes で
  自明成立）→ プレースホルダ実パース＋集合一致に強化。

反映後: full suite **1319 passed**・contract/status/drift/lint/budget 全 PASS。

```claims
verdict: approve
tests_green: true
second_opinion:
  verdict: approve_with_notes
  notes: Major 1（qa ゲートの未記入 verdict 沈黙通過）＋Minor 4 — 全件反映済み（1次 verdict 常時検証・budget 余白・残穴コメント・②(b) テスト・parity 集合一致）
```

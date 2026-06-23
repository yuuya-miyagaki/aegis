# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-24

## テーマ

- iteration 41 / 2026-06-24 全力レビュー Batch 1：配布正常化（D1-D4）＋整合性 fail-closed 化（I1-I2）

## コンテキスト

- 現在の状況: framework・L・phase=brainstorm。iter40 完了済（moat 解錠バグ修正・push 済）。
- きっかけ: 2026-06-24 全力レビュー（多エージェント敵対レビュー＋ユーザーレビュー）。要件 = `docs/full-review-2026-06-24-hooks-gates-distribution.md` ＋ `docs/security-followups.md` SF-006。
- 脅威モデル較正: moat（事故防止・敵対回避は SF-004 で受容済み）と gate（人間承認の偽造不能性）は別レイヤ。今回の finding は「moat の事故防止目的を破るか」「gate の偽造不能性を破るか」「ただ壊れているか」で評価。Batch 1 は主に **ただ壊れている（配布）** ＋ **整合性の fail-open（fail-closed 化）**。

## 検討したアプローチ

### アプローチ A: Batch 1 を 1 イテレーション（framework・L）で一括実装【採用】

- 概要: D1-D4＋I1-I2 を 1 つの L タスクとして brainstorm→plan→implement→review→qa→security→deploy→ship。
- 利点: レビュー doc が明示的に 1 batch にまとめている。RC-1（整合性）＋RC-2（配布）の 2 根本原因に対しコヒーレント。1 PR。各 fix は小さく独立。
- 欠点: review/qa/security の検査面が広い。

### アプローチ B: 配布（D1-D4）と整合性（I1-I2）を 2 イテレーションに分割

- 概要: RC-2 を先に、RC-1 を後に。
- 利点: 各 PR が小さい。
- 欠点: 6 件とも小・低リスクで、分割はゲート手続きのオーバーヘッドを倍化するだけ（churn）。レビュー doc の意図に反する。

### アプローチ C: 最小修正のみ（D1+D2 profile 行追加＋I2 の 1 行）

- 概要: 配布の table-stakes と最小 fail-closed だけ。D3/D4/I1 を backlog。
- 利点: 最速。
- 欠点: D3（upgrade が security 修正を届けない）は配布ハザードの核心で先送り不可。I1（audit fail-open）を残すと I3（Batch 2）の前提が崩れる。過小。

## 決定

- 採用アプローチ: **A（一括・framework・L・全ゲート）**。
- 採用理由: 6 件は cohesive・小・低リスク。レビュー doc が 1 batch 指定。分割は churn。
- 不採用理由: B=churn / C=核心（D3・I1）を落とす。

## 主要設計判断（推奨つき・brainstorm で確定、詳細は SPEC）

- **D1（判断 B）**: standard profile に **judge ツールチェーン依存閉包**を追加（builder 1 ファイルでは不足）。`build-judge-card.py` は `run-test-strength-drill.py` を importlib で必須ロード（fallback 無し＝不在ならクラッシュ→gate hard-block）。よって `build-judge-card.py`＋`run-test-strength-drill.py`＋`record-test-result.py`＋`hooks/lib/fingerprint.sh` を追加。
- **D2（判断 C）**: (1) standard.json の `hooks_include`＋`required_hook_scripts` に `check-task-created.sh`/`check-task-completed.sh` を追加。(2) 本リポの active `.claude/settings.local.json` に両 Task hook を配線（**安全確認済**: evidence-log 存在・completion-evidence rc=0・plan-gate hard stop は phase=implement かつ plan 未承認時のみ＝brainstorm/plan では pass-through）。(3) contract に **full self-check で active settings が CORE 強制 hook を登録しているか**を追加。**full の hooks_include 全集合は要求しない**（dogfood は check-tdd/skill-gate/cron-gate 等を意図的に省いた curated subset＝全要求は誤検知）。CORE = 完了強制（Task hooks）＋既配線の gate/audit/control-plane。
- **D3（判断 D・最重要・要ユーザー確認）**: upgrade（version bump 時）に **framework 所有資産**を上書き（`.bak` 退避つき）、**user 所有資産**は保全。分類: framework=`hooks/**`,`scripts/**`,`templates/**`,`.claude/{skills,agents,commands,rules}/**`／user=`docs/**`,`CLAUDE.md`,`.claude/settings*.json`,`.claude/.gate-snapshot`,`.gitignore`。CLAUDE.md は user 寄り（カスタムされうる）＝保全側。security 修正の核心経路 `hooks/`＋`scripts/` は確実に上書き対象。
- **D4（判断 E）**: `setup.sh:272-281` の parse 失敗 `except Exception: existing={}` を、**stderr に明示警告（.bak 退避を案内）**するよう変更。「Setup complete.」前に権限喪失を可視化。abort ではなく警告＋継続（既存ユーザーの再 install を壊さない）。
- **I1（判断 F）**: post-status-audit は **PostToolUse** blocker＝PreToolUse 用 byte-identical fallback は流用不可。`safety.sh` に PostToolUse 版 fail-closed helper を追加し、post-status-audit 専用の PostToolUse fallback block（BEGIN/END）を置く。lib source 失敗で `{"decision":"block"}` を emit（fail-closed）。`test_safety_fallback_identity.py` は「6 PreToolUse hook は byte 同一」を維持しつつ post-status-audit の PostToolUse block を別 canonical として検証。gate/mode tamper（bash のみ）は fail-closed。**task_type tamper は I3=Batch 2** なので I1 では触らない。phase-transition の python3 依存部の advisory 化はレビュー助言だが現状すでに block 寄り＝plan/grill で要確認（既定は現挙動維持＝最小変更）。
- **I2（判断 G）**: `check_status.py:1484` の `--check-completion-evidence` で STATUS 不在 / frontmatter None を violation（exit 1）化。**安全確認済**: 唯一の呼び元 check-task-completed.sh は STATUS 不在時に手前で early-allow（line 95-98）＝この変更は正常フローに影響せず、敵対的「STATUS 削除で完了検査 PASS」だけを塞ぐ。

## スコープ境界

- やること: D1, D2, D3, D4, I1, I2（＋各々の回帰テスト）。
- やらないこと: I3（task_type/size tamper＝Batch 2・I1 が前提）、G1-G3（guard 網羅＝Batch 2）、C1-C4・G4（Backlog）、**check-control-plane.sh の再設計**（明示的に触らない）。

## 未解決事項（plan/grill で詰める）

- D3 の分類境界（特に CLAUDE.md・.claude/rules を上書き対象にするか）→ 既定は保全寄り（CLAUDE.md/rules は…rules は framework 所有だが慎重に）。**ユーザー確認推奨ポイント**。
- I1 の phase-transition advisory 化（レビュー助言 vs 現挙動維持＝最小変更）。
- D2 CORE 強制 hook 集合の正確な定義。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-24-iter41-batch1-distribution-integrity-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

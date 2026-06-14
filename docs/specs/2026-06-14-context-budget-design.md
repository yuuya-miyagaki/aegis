# 決定論的コンテキスト予算チェック（tighten-only ratchet）設計書

- 日付: 2026-06-14
- 種別: feature（自己検査の拡張・決定論ガード）
- 出典: 進化ロードマップ `docs/plans/2026-06-14-aegis-evolution-roadmap.md` の **P1**（比較レビュー §5-3「GSD 式コンテキスト予算」を北極星でトリアージ採用）
- ステータス: 設計（brainstorm 合意済み・grill-plan 未）

## 1. 目的・動機

Aegis の設計原則「thin working context」を、*ポリシー*から*機械的保証*へ格上げする。文脈に載るのに**サイズ予算が無いファイル**を既存の word 予算機構でカバーし、**tighten-only ratchet** で縮小成果を固定して、肥大の静かな進行（creep）を決定論的に封じる。

動機の実証: 本セッションで root `README.md` が 680 行まで肥大し縮約を要した＝このリポジトリは放置すると doc/文脈が膨らむ実例がある。同じ力学は毎セッション/フェーズで*実際にモデルが読む*文脈（CLAUDE.md / SKILL.md / rules）にも働く。文脈肥大はモデルの注意低下（context rot）と毎回のトークン費増を招く。

## 2. 現状（既存機構の正確な把握）

`scripts/check_framework_contract.py` は**既に** word 予算を一部持つ（FAIL 判定）:
- `MAX_CLAUDE_WORDS = 650`: root `CLAUDE.md` / `templates/CLAUDE.template.md` / `examples/minimal-project/CLAUDE.md` の3変種に適用。
- `TEMPLATE_WORD_LIMITS`: `PLAN.template.md`≤400 / `SECURITY-REVIEW.template.md`≤150 / `VERIFICATION.template.md`≤120。
- 共通ヘルパ `word_count(text) = len(text.split())`。

**未カバー（＝本 feature の価値）**:
1. **`.claude/skills/*/SKILL.md` に予算が無い**（phase 文脈の最大面。現状 計 ~77KB・最大 `qa-verification` ~7.3KB）。
2. **`.claude/rules/*.md` に予算が無い**（always-loaded: `state-machine.md` ~1.9KB / `routing.md` ~0.6KB）。
3. **tighten-only ratchet が無い**: 既存は手書き定数で、ファイルが縮んでも予算は自動で締まらず緩み放置。

→ 本 feature は**新システムではなく既存 word 予算の拡張＋ratchet 追加**。`word_count()` を再利用し、単位は **words**（既存と一貫・可読性中立・CJK/markdown でも安定）。

## 3. スコープ

### 対象（v1）
- 各 `.claude/skills/*/SKILL.md`
- 各 `.claude/rules/*.md`

### 非対象（理由）
- **CLAUDE.md / 既存テンプレ**: 既に予算済み＝重複させない（既存定数はそのまま温存。consolidation は §8 future）。
- **STATUS.md**: 動的に育つ state（external_evidence/session_history・既存ローテ規則あり）＝サイズ予算に不向き。
- **agents (`.claude/agents/*.md`)**: subagent 個別コンテキストでメイン文脈と別＝v1 見送り（ロードマップ外）。
- **refs/その他 md**: YAGNI。

## 4. 設計

### 4-1. 予算レジストリ（単一宣言・root 専用・非ミラー）
- 新規データファイル: `scripts/context-budgets.json`（path→max_words のマップ）。
  - 例: `{ ".claude/skills/qa-verification/SKILL.md": 1100, ".claude/rules/state-machine.md": 380, ... }`。
  - root 相対パスをキーにする。
- **default 予算**: registry に未掲載の skill/rule にも適用される既定上限 `DEFAULT_SKILL_WORDS` / `DEFAULT_RULE_WORDS` を持つ。→ **新規 skill を追加しても自動で予算対象**になり、「予算追加し忘れで穴が再発」を防ぐ。
- `platform_manifest.py` と同様 **framework root 専用**。setup.sh では配布しない（下流プロジェクト用の予算ではなく、Aegis 自身の自己検査データ）。mirror 対象にもしない（`MIRROR_DIRS`/`MIRROR_FILES` に追加しない）。

### 4-2. 単一所有モジュール＋チェック（FAIL）
- 新規 `scripts/context_budget.py` を **single owner** とし、対象列挙・registry 読込・word 計測・判定・ratchet をここに集約（checker と tightener でロジック重複させない。`phase-skills.sh`/`secrets-patterns.sh` と同じ single-owner パターン）。公開関数: `load_budgets()` / `iter_targets()` / `check() -> list[failure]` / `tighten()`。
- `check_framework_contract.py` は `context_budget.check()` を **import して呼ぶ**だけ（既存 word 予算と同 family・同 FAIL 意味・CI/make/contract テストで自動発火）。
- ロジック: framework root の各 `.claude/skills/*/SKILL.md` と `.claude/rules/*.md` について、`budget = registry[path] or DEFAULT_*`、`word_count(file) > budget` なら **FAIL**（`"<path> is too large: N words > B"` 形式・既存メッセージに倣う）。`word_count` は既存実装を再利用（import）。
- 対象は **root のみ**（example は byte-identical ミラー＝`check_mirror_identity` が別途同一性を担保するため二重検査不要）。

### 4-3. tighten-only ratchet
- CLI: `python3 scripts/context_budget.py --tighten`（同 single-owner モジュール）。`make tighten-budgets` から呼ぶ。
- 動作: 対象各ファイルについて `current = word_count(file)` を測り、`current < registry[path]`（または default 未満）なら **registry[path] = current に下げて JSON を書き戻す**（縮小を固定）。`current >= 予算` のファイルは変更しない。registry 未掲載ファイルは現値で明示エントリ化。
- **上げる時**: registry JSON を**手編集**するのみ（自動では上げない）。差分が PR/commit に出る＝「本当に増やす価値があるか」を1回考えさせる関所。
- JSON を機械書換対象にしたのは、Python 定数より安全・容易に rewrite できるため。

### 4-4. seed（初期予算）
- 初回導入時、対象各ファイルの registry 値＝ `ceil(current_word_count * 1.1)`（現状＋約10%の余裕）で seed。→ 初日は全 PASS、かつ微修正は予算決定を強いずに通る。以後 `make tighten-budgets` で実測へ締める運用。
- `DEFAULT_SKILL_WORDS` は既存最大 skill の現値＋余裕（例: 現状最大 ~1100 words 程度なら 1300 等）に設定し、新規 skill が常識的サイズなら通るが暴走は止める水準にする（具体値は実装時の実測で確定）。

## 5. 失敗モード・エッジ

- **ファイル間で内容を移すリファクタ**: 移動先が予算超過で FAIL しうる → `make tighten-budgets` 後に移動先 registry を手編集で調整（意図的操作として可視）。
- **新規 skill 追加**: default 予算で自動カバー。常識超なら FAIL＝registry に明示エントリ追加（＋tighten）で対応。
- **registry とファイルの drift**: registry にあるが実在しない path → 無視 or WARN（掃除を促す）。実装で軽く WARN。
- **example ミラー**: root のみ検査。example 差異は `check_mirror_identity` が担保。

## 6. テスト（TDD）

`tests/test_context_budget.py`（新規）:
1. 予算超過の fixture skill/rule → contract が FAIL を返す（RED→GREEN の核）。
2. 予算内 → PASS。
3. registry 未掲載 skill が DEFAULT 超 → FAIL（default ガードの実証）。
4. ratchet: `current < budget` のとき tighten が registry を current へ下げる／`current >= budget` は不変／JSON が妥当に書き戻る。
5. 実リポジトリ全 skills/rules が seed 済み registry で PASS（回帰ゼロ）。

既存スイート（751）＋ contract 全 profile / drift / eval が緑であることを確認。

## 7. 不変条件・非目標

- 既存の CLAUDE.md/テンプレ word 予算は**挙動不変**（温存）。
- hook（実行時 PaC）は**一切変更しない**（本 feature は静的自己検査のみ）。
- 単位は words 固定（bytes/tokens は導入しない）。
- 予算は**サイズの代理**であり質を測らない＝可読性（北極星）を損なわない範囲で運用（seed に余裕・ratchet は強制下げのみ）。

## 8. 将来（v1 では行わない）

- 既存 CLAUDE.md/テンプレ予算の registry への consolidation（単一予算源化）。
- agents への拡張。
- aggregate 予算（always-on 合計や phase ごとの合計上限）。
- token 単位化（tokenizer 依存のため見送り）。

## 9. 成果物

- 新規: `scripts/context_budget.py`（single owner: check＋tighten＋`--tighten` CLI）、`scripts/context-budgets.json`（registry・root 専用・非ミラー）、`make tighten-budgets` ターゲット、`tests/test_context_budget.py`。
- 変更: `scripts/check_framework_contract.py`（`context_budget.check()` を import して呼ぶ）。必要なら `architecture-overview.md` の自己検査一覧を同期。
- 非配布・非ミラー: `context_budget.py`/`context-budgets.json` は setup.sh 配布対象外・`MIRROR_DIRS/FILES` 不追加（Aegis 自身の自己検査データ）。

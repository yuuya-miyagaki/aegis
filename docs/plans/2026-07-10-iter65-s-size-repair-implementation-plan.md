# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: **S サイズ修復（full-review §R2🔴 / §4 Phase 1 項目 1-4）**。
  `hooks/check-gate.sh` を size-aware 化して S の feature/refactor/framework でコード編集を可能にし
  （三者不整合を bash 側へ揃える）、`check_phase_transition` の空リスト穴を封鎖し、
  `SIZE_ALLOWED_PHASES["S"]` に docs を追加して罠 q を根絶する。guidance（state-machine.md 表）も同期。

## 入力

- 参照要件: `docs/full-review-2026-07-06-six-dimensions-evolution.md` §R2 / §4 表 1-4
- 参照設計: `docs/specs/2026-07-10-iter65-s-size-repair-design.md`

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（フレームワーク自身・ローカル hook/script）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ物なし・M のため deploy gate skip）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

main 直接コミット（ドッグフード慣行・per-task commit・push は全ゲート approved 後に
`gh auth switch --user yuuya-miyagaki` で実施）。

## ファイル構造（変更マップ）

- 変更: `hooks/check-gate.sh:237-252` — コード編集ゲートの size-aware 化
  （task_size=S→brainstorm gate／それ以外・未設定→plan gate。pure-bash、`frontmatter_value`/`gate_value` 使用）
- 変更: `scripts/check_status.py:211-215` — `SIZE_ALLOWED_PHASES["S"]` に `"docs"` 追加＋コメント更新
- 変更: `scripts/check_status.py:1336-1350` — `check_phase_transition` 前進遷移で
  `allowed_after_old` 空＝terminal 超過を明示 deny
- 変更: `.claude/rules/state-machine.md:45` — 表 S 列 `impl->review->ship` → `impl->review->ship->docs`
- 新規テスト: `tests/test_check_gate_size_aware.py` — check-gate.sh の size×gate-state behavioral
  ＋drift-guard（ハーネスは `tests/test_check_gate_root_external.py` の scratch-root 方式を踏襲）
- 変更テスト: `tests/test_check_status.py` — S+docs 静的検査 pass・ship→docs transition pass・
  terminal 超過 deny（monkeypatch）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `SIZE_ALLOWED_PHASES["S"]`（docs 含む） | なし |
| Task 2 | terminal 超過 deny（check_phase_transition） | なし（テストは monkeypatch で Task 1 と独立） |
| Task 3 | size-aware check-gate.sh | なし（bash 側は STATUS を直読） |
| Task 4 | drift-guard テスト | Task 1 の集合定義・Task 3 の bash 前提 |
| Task 5 | state-machine.md 表同期＋full suite green | Task 1-4 |

循環依存なし。

## タスク分解

> 各タスク TDD（RED 確認→実装→GREEN→commit）。実装 dispatch は工程別 tiering に従い
> **`implementer` を `model: "opus"`** で起動（grill-code・review 系は fable）。
> **実行順序: Task 1→2 は同一ファイル（check_status.py）変更のため直列**（subagent-dev 並列禁止ルール。
> 順序自体は任意だが直列が要件）。Task 3 は独立。Task 4 は Task 1・3 後、Task 5 は最後。

### タスク 1: SIZE_ALLOWED_PHASES["S"] に docs 追加（Fix 3a）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 対象 `scripts/check_status.py:211-215` / テスト `tests/test_check_status.py`
**意図:** S の terminal を M/L と統一し、罠 q（ship→docs が transition rc0／静的検査 FAIL の割れ）を根絶。
**TDD:** RED: (a) `make_status_md(task_size="S", phase="docs")` の静的検査が pass、
(b) `--check-phase-transition ship docs`（S fixture）が rc0 —— (a) は現行 FAIL するはず。
→ 集合に `"docs"` 追加＋`:209-210` コメント更新 → GREEN。
**受入条件:** S+docs 静的 pass／S の ship→docs transition rc0／既存 S テスト（implement・ship fixture）無回帰。
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 2: check_phase_transition の空リスト穴封鎖（Fix 2）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 対象 `scripts/check_status.py:1336-1350` / テスト `tests/test_check_status.py`
**意図:** 前進遷移で `allowed_after_old` が空（old が size の terminal）のとき検査スキップで rc0 になる穴を、
明示 deny（terminal 専用メッセージ）に置換。Fix 3a 後は dormant だが、将来 size 追加への defense in depth。
**TDD:** RED: `importlib.util.spec_from_file_location` で `scripts/check_status.py` を **in-process import**
し、`SIZE_ALLOWED_PHASES["S"]` を docs 抜きに一時差し替え（try/finally で必ず復元）て
`check_phase_transition("ship", "docs", root)` を直接呼ぶ → rc1 を期待（現行は rc0 素通り＝RED）。
※手法明記の理由（grill-plan 致命2）: `tests/test_check_status.py` の既存ハーネスは subprocess CLI 方式で
monkeypatch が届かず、in-process import の前例も同ファイルに無い。Fix 3a 適用後は実 enum で空リスト状態を
作れない（docs は DEV_PHASE_ORDER 最後尾）ため、dict 差し替えが唯一の検証経路。
→ `if not allowed_after_old: deny` 分岐追加 → GREEN。
**受入条件:** terminal 超過の前進遷移が rc1＋terminal 明示メッセージ／後退・同一遷移は従来どおり rc0。
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 3: check-gate.sh の size-aware 化（Fix 1・本丸）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** 対象 `hooks/check-gate.sh:237-252` / テスト `tests/test_check_gate_size_aware.py`（新規）
**意図:** コード編集を守るゲートを「size フローで implement 直前の承認ゲート」に差し替え。
S→**brainstorm** gate／M・L・未設定・不正値→**plan** gate（保守的デフォルト＝gate を緩めない）。
`approved` OR `n/a` を許容。判定は pure-bash（python 委譲禁止＝fail-open 退行回避）。deny 文言も size を反映。
**TDD:** RED（scratch-root ハーネス）:
(a) S-feature・brainstorm=approved・plan=pending・`src/app.py` Edit → **allow**（現行 deny＝RED 実証）、
(b) S-feature・brainstorm=pending → deny、
(c) S-bugfix・brainstorm=n/a → allow、
(d) M・plan=pending → deny／plan=approved → allow（従来挙動）、
(e) task_size 未設定・plan=pending → deny（後方互換）、
(f) task_size 不正値（例 `XL`）・plan=pending → deny（保守的）、
(g) S・gate_approvals に brainstorm キー欠落 → deny（fail-closed の明示 pin・grill-plan 要検討1）。
→ 実装 → GREEN。
**受入条件:** 上記 7 ケース green（S の deny 文言に brainstorm が含まれることも assert＝fail-visible 品質）。
fixture テンプレは既存 STATUS_TMPL（plan キーのみ）に `task_size`・`brainstorm` を拡張して自前定義。
check-gate.sh ヘッダコメント（:2 の「blocks code edits when plan gate is not approved」）を size-aware 記述へ
更新（R9 型 drift の自家生産防止）。`grep -l task_size tests/` 全ファイルを sweep し、size-blind 挙動
（S でも plan deny）を pin する既存テストがあれば flip。既存 check-gate 系テスト
（root_external / prose_md / case_insensitive / glob_expansion）無回帰。
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 4: drift-guard テスト（bash 複製の機械保全）

**blockedBy:** Task 1, Task 3 | **モデル:** `opus`
**ファイル:** テスト `tests/test_check_gate_size_aware.py`（同ファイルに追記）
**意図:** 「plan を skip する size は S のみ」「S で implement 直前の gate は brainstorm・M/L は plan」
という bash 側前提を python SoT（`SIZE_ALLOWED_PHASES`/`PHASE_REQUIRES_GATES`）から導出して assert。
将来 size 追加や集合変更で check-gate.sh のハードコードが陳腐化したら赤く落ちる
（iter53 REGEX↔WARN parity パターン）。
**TDD:** guard 自体が仕様（現行実装で GREEN が正・集合を一時変異させ RED になることを確認して戻す）。
**受入条件:** `{s | "plan" ∉ phases}` == `{"S"}`／S の implement 直前 gate 列 == `["brainstorm"]`／
M・L == `["brainstorm", "plan"]` を assert。
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

### タスク 5: state-machine.md 表同期＋full suite

**blockedBy:** Task 1-4 | **モデル:** `opus`
**ファイル:** 対象 `.claude/rules/state-machine.md:45`
**意図:** S 列を `impl->review->ship->docs` へ更新し R9 型 guidance↔enforcement drift を残さない。
**TDD:** 表は静的検査（contract/budget）対象 — full suite で契約 green を確認。
**受入条件:** full suite pass（budget 含む）・porcelain クリーン（意図した変更のみ）。
**Deliverable:** [ ] 機能が存在し動作 [ ] テストがカバー

## External Integrations

n/a（外部連携なし）

## 事前準備

- [x] 対象ファイル・行範囲を実地確認済み（brainstorm 時 grounding）
- [x] 既存テストハーネス確認済み（scratch-root 方式・transition CLI 方式）
- [x] ベースは main（origin/main=26de7f6 と同期済み・作業ツリーは docs/STATUS.md のみ変更中）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| R2: S でコード編集可能（bash 側 size 対応） | Task 3 TDD (a)-(f) | Task 3 | `tests/test_check_gate_size_aware.py` |
| R2 併発: transition 空リスト穴封鎖 | Task 2 RED | Task 2 | `tests/test_check_status.py` |
| R2: S terminal に docs（罠 q 消滅） | Task 1 RED (a)(b) | Task 1 | `tests/test_check_status.py` |
| bash 複製の陳腐化防止（設計判断） | Task 4 assert 3 点 | Task 4 | `tests/test_check_gate_size_aware.py` |
| guidance 同期（R9 型 drift 防止） | Task 5 | Task 5 | full suite（contract/budget） |

全要件がいずれかの Task でカバー済み。

## 自己レビュー

- 仕様カバレッジ: §R2 の修正方向 3 点＋設計ノート追加 2 点（drift-guard・doc 同期）を全て Task 化 ✓
- 曖昧さ検出: 「S 以外」の定義を明示（M・L・未設定・不正値→plan＝保守的） ✓
- 型の整合性: bash は文字列比較のみ・python は既存集合演算のみ・新インターフェースなし ✓
- 境界整合性: Task 4 の Consumes（集合定義・bash 前提）は Task 1/3 の Produces に一致 ✓

## リスク

- リスク1: check-gate.sh は moat hook — バグは「過剰 allow（ゲート弱体化）」か「過剰 deny（全編集不能）」に直結。
  - 対策: 両方向の RED-first テスト（S-pending deny 維持・M 従来挙動維持・未設定/不正値は保守側）＋
    既存 check-gate 系 4 テストで無回帰確認＋grill-code（fable）＋review/security gate。
- リスク2: `SIZE_ALLOWED_PHASES` 変更が思わぬ消費者（deploy-ready・judge 等）に波及。
  - 対策: 消費箇所は grounding で列挙済み（静的検査/transition/deploy-ready/judge/strict-gate）。
    strict-gate と dev_ready_for_client は `task_size != "S"` ガード済で docs 追加の影響なし。full suite で検証。
- リスク3（grill-plan 致命1で確定）: S の brainstorm gate 化で**新しい迂回面**が開く — M/L タスクが
  brainstorm 承認後・plan 未承認の時点で `update-task.sh --size S` に降格すると、plan 儀式を飛ばして
  コード編集が合法化される（brainstorm∈S で phase 整合の静的検査は green・既存 rationale が非空なら
  rationale-FAIL :668-675 も発火しない＝空欄のみ検知の既知限界）。
  - 立場: **fail-visible として受容**（受容案採用）。根拠:
    (i) brainstorm はユーザー承認必須のハードゲートで、無承認コーディングは依然不能、
    (ii) update-task.sh 実行はトランスクリプト・git diff・.gate-snapshot に可視、
    (iii) 誤ラベル S の rationale 検査が空欄のみ検知なのは正本 §R2 の設計受容範囲。
    強化案（update-task.sh に M/L→S 降格×plan pending の WARNING 1 行）は footprint を
    6 ファイル=L に押し上げるため本反復では見送り、docs フェーズで LEARNINGS 起票し次反復候補へ送る。

## 完了条件

- [ ] 全テスト pass（full suite・新規含む）
- [ ] レビュー完了（grill-code→review 1次＋盲検2次）
- [ ] Task 3 の RED 実証記録（S-feature allow が現行 deny であること）
- [ ] porcelain に意図した変更のみ
- [ ] docs フェーズ: LEARNINGS 91/93（「framework-M が唯一クリーン」暗記受容）を iter65 修復済みへ更新＋
      リスク3 残存迂回（S 降格×plan pending・強化案見送り）の LEARNINGS 起票＋full-review §R2 クローズ追記

## QA チェックリスト（ui_surface: true の場合）

n/a（ui_surface: false）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

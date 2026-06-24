# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- `hooks/check-gate.sh` が ROOT 外の絶対パス（auto-memory 等）にも plan-gate を適用して
  false-positive deny する不具合（full-review C5）を、ROOT 外絶対パスの allow short-circuit で解消する。
  保護対象（project code・control file・templates・docs）は不変に保つ。

## 入力

- 参照要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（C5）
- 参照設計: `docs/specs/2026-06-25-iter44-root-external-plan-gate-design.md`

## Deploy Target（必須）

### プラットフォーム

- Hosting: **n/a**（framework＝hook ロジック修正。アプリのデプロイ先なし）
- Database: n/a
- CI/CD: n/a（「デプロイ」= main への commit。task_size=M で deploy ゲートは size routing で exempt）

### 互換性確認

- next.config `output` 設定: n/a（Next.js プロジェクトではない）
- 上記がデプロイ先と互換であることを確認: Yes（該当なし）

### 認証方式

- 認証プロバイダ: None（framework 内部）
- DEMO_MODE 予定: n/a

## Git 戦略

- main へ直接 commit（framework のドッグフード運用。prior iter41-43 と同じ）。push は別途 yuuya-miyagaki。

## ファイル構造（変更マップ）

- 変更: `hooks/check-gate.sh`（現 line 130-140 の `is_control_file` ブロック直後、line 142 の `MODE=` 直前に
  ROOT 外絶対パスの allow short-circuit を ~8 行追加）
- テスト: `tests/test_check_gate_root_external.py`（新規）— 6 ケース（下記）

### 挿入位置の意図（grill-plan #1: 意識的決定）

short-circuit は `MODE=`（line 142）・Client-mode deny（line 147）・plan-gate（line 153）の**すべての前**に置く。
これは無自覚な副作用ではなく**意図的決定**: plan-gate も Client-mode deny も「**この project の code** を
編集させない」ためのゲート。ROOT 外絶対パスは定義上 project の code ではない（auto-memory 等の
cross-cutting ツール）ので、**plan-gate も Client-mode deny も適用対象外**とするのが正しい。auto-memory は
モード非依存で動くべき（Client モードでも記憶は書ける必要がある）。control-file/templates/docs 保護は
この short-circuit より前段で完結しており不変。security report に本決定の根拠を残す。

### 補足（grill-plan #4・#6）

- Edit/Write の `file_path` は常に絶対 → 実 target は絶対前提。case の `/*` 相対非マッチ分岐は**防御的**
  （実運用では dead）。test は絶対パスで書く。
- ROOT は `SCRIPT_DIR/..` ＝ project root（dogfood では framework=project、配布形態では user project）。
  どちらでも「ROOT 外 = project 外」が成立。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | check-gate.sh の external short-circuit + 新規テスト | 既存 `$ROOT`/`$ROOT_REAL`・既存 harness（test_control_plane_allowlist 流用） |

循環なし。Consumes はすべて既存。

## タスク分解

### タスク 1: ROOT 外絶対パス short-circuit ＋ RED-first テスト

**blockedBy:** なし | **モデル:** in-session（コーディネーター直接実装。1 hook + 1 test の小変更）
**ファイル:** 対象 `hooks/check-gate.sh` / テスト `tests/test_check_gate_root_external.py`
**意図:** control-file 判定後・MODE/Client/plan-gate 判定の前で、`$ROOT/*`・`$ROOT_REAL/*` 以外の絶対パスを
`emit_allow` する。相対パスは case 非マッチで従来どおり gate（防御的維持）。
**TDD（テストは 6 ケース・RED は厳密 assert）:**
1. `tests/test_check_gate_root_external.py` を書く（hook を temp root に copy・libs symlink・
   STATUS は mode/plan/task_type をケースごとに設定）。
   - test_a: Dev・plan=pending・絶対 ROOT 外 → **allow**（**修正前は deny ＝ RED**）
   - test_b: Dev・plan=pending・絶対 ROOT 内 `f"{root}/src/main.py"` → deny（回帰）
   - test_c: control file `f"{root}/hooks/x.sh"`（task_type=feature）→ deny（回帰）
   - test_d: `f"{root}/docs/foo.md"` → allow（回帰）
   - test_e（#1）: **Client mode・絶対 ROOT 外 → allow**（外部は mode 非依存で許可）
   - test_f（#1）: **Client mode・絶対 ROOT 内 `src/x.py` → deny**（Client の code ロック維持）
   - （#3）test_b は可能なら論理 ROOT と物理 ROOT_REAL の両形で叩き、`$ROOT_REAL/*` アームを実踏。
2. **RED の厳密 assert**: test_a は `if out:` ガードを使わず、allow を厳密 assert
   （`emit_allow` 実出力を `hooks/lib/emit.sh` で確認し、`{}` or `permissionDecision != deny` を明示 assert）。
   修正前に test_a が **deny で必ず FAIL** することを実測（RED 成立確認）。
3. check-gate.sh に short-circuit を追加。
4. 全 6 test GREEN ＋ 既存 full suite GREEN を確認。
**受入条件:** 新規 6 test PASS・既存 full suite PASS・`bash -n hooks/check-gate.sh` OK・
RED 成立を実測済・Client-mode 相互作用を security report に文書化。
**Deliverable:** [ ] short-circuit が存在し動作 [ ] 6 test がカバー [ ] RED 実測 [ ] Client-mode 決定を文書化

## 事前準備

- [x] 環境: 追加の API キー・外部サービス不要
- [x] 依存: 追加パッケージなし（python3 + bash のみ）
- [x] ベースブランチ: main 最新（origin/main=93fc166 と一致）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| C5 | Dev・ROOT 外絶対パスは plan-gate 対象外（allow） | Task 1 | `tests/test_check_gate_root_external.py::test_a` |
| C5（回帰） | Dev・ROOT 内は plan-gate 維持（deny） | Task 1 | `::test_b` |
| C5（回帰） | control file 保護は不変（deny） | Task 1 | `::test_c` |
| C5（回帰） | docs allowlist は不変（allow） | Task 1 | `::test_d` |
| C5（#1） | Client mode・ROOT 外は許可（mode 非依存） | Task 1 | `::test_e` |
| C5（#1 回帰） | Client mode・ROOT 内は code ロック維持（deny） | Task 1 | `::test_f` |

## 自己レビュー

- 仕様カバレッジ: C5 の修正点＋回帰＋Client-mode 相互作用を全て test 化（6 ケース）。✓
- 曖昧さ: 「ROOT 外」を「絶対かつ `$ROOT/*`・`$ROOT_REAL/*` 非マッチ」と一意定義。相対は対象外と明記。✓
- 型整合: bash case パターンのみ。新規シンボルなし。✓
- 境界整合: Consumes（$ROOT/$ROOT_REAL/harness）は既存。✓

## リスク

- リスク R1: short-circuit が control-file 判定より前に入ると外部 .claude を誤通過。
  - 対策: 必ず `is_control_file` ブロックの**後**に配置（設計で固定）。test_c が回帰検知。
- リスク R2: 相対パスを誤って allow 化すると project code が plan-gate を逃れる。
  - 対策: case の `/*` arm は絶対パスのみ。相対は非マッチで従来 gate。test_b（絶対内）＋設計表で担保。
- リスク R3: `$ROOT_REAL`≠`$ROOT`（symlink workdir）で ROOT 内が誤って外部判定。
  - 対策: case に両方（`"$ROOT"/*`・`"$ROOT_REAL"/*`）を列挙。test_b で両形を実踏（#3）。
- リスク R4（grill-plan #5・受容）: case-insensitive FS（macOS）で大文字小文字ゆらぎの ROOT 内絶対パスが
  外部判定され plan-gate を逃れうる。ただし `is_control_file` も同じ case-sensitive lexical 限界を既に持ち、
  **C5 が新設する穴ではなく既存クラス**。plan-gate は security 境界でない。security report に受容明記。

## 完了条件

- [ ] 新規 6 test pass・既存 full suite pass（record-test-result green）
- [ ] RED 成立を実測（test_a が修正前に deny で FAIL）
- [ ] grill-code 指摘ゼロ
- [ ] Client-mode 相互作用（#1）を security report に文書化
- [ ] review / qa / security ゲート approved（deploy は M で exempt）
- [ ] LEARNINGS 追記

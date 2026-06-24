# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- `task_type` / `task_size` を tamper-evidence の対象に加える（I3 / SF-006）。snapshot に両フィールドを取り込み、post-status-audit で raw Edit による変更を block し、変更は authorized write-path（新 `scripts/update-task.sh`）経由のみ可能にする。脅威モデルは **LLM の自己バイパス**（外部 adversary 対策ではない）。

## 入力

- 参照要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（I3 / SF-006 / RC-1）
- 参照設計: `docs/specs/2026-06-24-iter43-task-tamper-evidence-design.md`

## Deploy Target（framework タスク）

### プラットフォーム

- Hosting: n/a（フレームワーク内部変更。デプロイ＝main への commit/push）
- Database: n/a
- CI/CD: n/a（main commit がデプロイ実体）

### 互換性確認

- next.config `output` 設定: n/a（Web アプリではない）
- デプロイ先互換: Yes（main ブランチへの commit＝従来どおり）

### 認証方式

- 認証プロバイダ: None（フレームワーク）
- DEMO_MODE 予定: n/a

## Git 戦略

- main 直コミット（フレームワーク運用の従来方針）。push は `gh auth switch --user yuuya-miyagaki` 後に実行。

## ファイル構造（変更マップ）

- 新規: `hooks/lib/snapshot.sh` — `aegis_write_snapshot <root>`（STATUS→snapshot のアトミック書込み・gate_approvals/phase/mode/**task_type/task_size**）
- 新規: `scripts/update-task.sh` — task_type/task_size の authorized writer（enum 検証・STATUS+snapshot 更新・gate-update ロック共有・type 変更時 aegis_cp_apply）
- 変更: `hooks/session-start.sh:33-40` — inline snapshot 書込みを `aegis_write_snapshot` 呼出に置換
- 変更: `hooks/post-status-audit.sh:83-86,108-175` — (i) task_type/task_size tamper 検知ループ追加 (ii) inline snapshot 書込みを helper に置換 (iii) `aegis_cp_apply` を tamper チェック後へ移動
- 変更: `scripts/update-gate.sh:329-336` — inline snapshot 書込みを helper に置換
- 変更: `CLAUDE.md` — task_type/task_size 変更は update-task.sh 経由のみ（Operating Contract / Completion Rule 近傍）
- 変更: `.claude/rules/state-machine.md` — rollover 手順を update-task.sh 経由に
- 変更: `.claude/skills/aegis-brainstorm/SKILL.md:70-74` — Step D の task_size 設定を update-task.sh 経由に
- 変更: `scripts/check_framework_contract.py:146` — REQUIRED_HOOK_FILES に snapshot.sh 追加（Task 6）
- テスト: `tests/` — update-task.sh 単体／post-status-audit tamper 結合／snapshot スキーマ／cp_apply 順序（既存テストファイルに追記 or 新規）
- ※ session-recovery skill は read-only 復帰で task を書かないため対象外（Task 5 で grep 確認）

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `aegis_write_snapshot` (hooks/lib/snapshot.sh) | frontmatter.sh |
| Task 2 | refactored writers (session-start/update-gate/post-status-audit) | Task 1 |
| Task 3 | `scripts/update-task.sh` | Task 1（snapshot helper）, cp-lock.sh |
| Task 4 | post-status-audit tamper 検知＋cp_apply 移動 | Task 1, Task 2 |
| Task 5 | docs/skills 更新 | Task 3（コマンド名確定後） |
| Task 6 | contract 登録・配布保証 | Task 1 |

循環なし。Consumes は全て先行 Produces にある。

## タスク分解

### タスク 1: snapshot 共有ヘルパ

**blockedBy:** なし | **モデル:** `sonnet`
**ファイル:** 対象 `hooks/lib/snapshot.sh` / テスト `tests/test_snapshot_helper.py`（新規 or 既存に追記）
**意図:** snapshot 書込みを単一関数化し task_type/task_size を含める（iter37「単一関数＋複数発火点」）。
**TDD:** テスト（snapshot に gate_approvals/phase/mode/task_type/task_size が含まれ、アトミック tmp→mv）→ FAIL → 実装 → PASS → commit
**受入条件:** `aegis_write_snapshot <root>` が STATUS から5要素を読み `.claude/.gate-snapshot` に書く。task_size が null/空でも壊れない（行は出すが値が空＝移行猶予と整合）。失敗時は既存 snapshot を残す（非破壊・tmp→mv）。
**per-consumer 不在時挙動（grill 要検討5）:** post-status-audit は `aegis_require_lib_block` で **fail-closed**（snapshot.sh はコア infra）。session-start / update-gate / update-task は **defensive source**（不在なら明示エラーで非0 or 警告、die させない）。
**Deliverable:** [ ] 関数が存在し動作 [ ] テストがカバー

### タスク 2: 既存 3 writer を helper へ移行

**blockedBy:** Task 1 | **モデル:** `sonnet`
**ファイル:** 対象 `hooks/session-start.sh` `hooks/post-status-audit.sh`（snapshot 書込み部のみ） `scripts/update-gate.sh` / テスト 既存 snapshot 関連テスト＋scaffold
**意図:** 3 経路の inline snapshot 書込みを `aegis_write_snapshot` 呼出に置換し、ドリフトを排除。
**着手前（grill 致命5）:** snapshot **出力**を assert するテストを全列挙してから refactor。確認済み対象＝`tests/test_snapshot_atomic.py`・`tests/test_snapshot_consumer_policy.py`・`tests/test_hook_output_schema.py:498` 周辺（他の test_*.py は snapshot を**入力として構築**するだけで writer 出力は assert しない）。新形式（+task_type/+task_size 行）に更新。
**byte-compat:** helper は gate_approvals/phase/mode 抽出を現行の `sed -n '/^gate_approvals:/,/^[a-z]/{...}'` と**同一**にし、task_type/task_size 行を mode の後に append。`gate_value`/`frontmatter_value` は key 読みで順序非依存。
**TDD:** 各 writer 実行後 snapshot に task_type/task_size 行が出ることをテスト（RED）→ 置換 → PASS
**受入条件:** session-start / update-gate / post-status-audit 全経路の snapshot に task フィールドが入る。**test scaffold（TempProjectWithHooks 等）に snapshot.sh を追加**（trap f）。per-consumer 不在時挙動＝Task 1 の規定どおり（post-status-audit は fail-closed、他は defensive）。
**Deliverable:** [ ] 3 writer が helper 使用 [ ] scaffold 更新 [ ] 出力 assert テスト全更新 [ ] テスト緑

### タスク 3: update-task.sh（authorized writer）

**blockedBy:** Task 1 | **モデル:** `sonnet`
**ファイル:** 対象 `scripts/update-task.sh` / テスト `tests/test_update_task.py`（新規）
**意図:** task_type/task_size を STATUS+snapshot にアトミック反映する唯一の authorized path。
**enum 正本（grill 致命3）:** bash 側にハードコードし `# MUST mirror check_status.py ALLOWED_TASK_TYPES / ALLOWED_TASK_SIZES` コメントを付す（update-gate.sh の VALID_GATES と同方針）。enum の contract 自動照合は**入れない**（YAGNI・コメントで最低線）。
**sed アンカー（grill 要検討3）:** `^task_type:` / `^task_size:` のアンカー必須（`task_size_rationale` を巻き込まない）。値は unquoted（framework / L）。
**書込み順序（grill 致命2／検証反映）:** STATUS 書込み → snapshot 書込み → 最後に `aegis_cp_apply`。※`.gate-snapshot` と `docs/` は moat 施錠対象外（`test_cp_lock_lib.py:66,104` で確認済）＝permission 上は順序自由だが、cp_apply は副作用なので最後に置く。
**ロック共有（grill 要検討1）:** update-gate.sh と同一ロックディレクトリ `.claude/.gate-update.lock.d` を bounded mkdir-retry で取得（STATUS 全書込みの相互排他）。orphan-reclaim の正本は update-gate.sh＝複製しない。orphan 残存時は fail-closed（再実行＝update-gate と同 UX）。同一フロー内で両者が互いのロック保持中に呼ばれることはない（別 Bash 呼出・ネスト無し）＝deadlock なし。
**TDD:** テスト（`--type framework`/`--size M` で STATUS+snapshot 一致更新／enum 不正拒否／引数なし usage 非0／type 変更で aegis_cp_apply 実行＝moat 状態切替／ロック共有で直列化）→ FAIL → 実装 → PASS
**受入条件:** enum 検証のみ（shrink 禁止・phase 連動は入れない＝YAGNI）。Bash 経由のため post-status-audit を自然バイパス。cp-lock.sh 不在環境でも壊れない（`command -v aegis_cp_apply` ガード）。
**Deliverable:** [ ] スクリプト動作 [ ] enum 拒否 [ ] cp_apply 連動 [ ] ロック共有 [ ] テストがカバー

### タスク 4: post-status-audit tamper 検知＋cp_apply 移動

**blockedBy:** Task 1, Task 2 | **モデル:** `opus`
**ファイル:** 対象 `hooks/post-status-audit.sh` / テスト `tests/test_post_status_audit*.py`
**意図:** raw Edit による task_type/task_size 変更を block。改竄編集が moat を解錠する前に block するため cp_apply を後段へ移動。
**着手前（grill 致命4）:** session-start.sh の moat 再適用経路（session-start が STATUS から cp_apply するか）を確認する。**cross-session re-bless 残存**＝改竄値はディスク STATUS に残り、次回 session-start が snapshot を STATUS から再生成し moat を再適用すれば事実上 bless される。これは gate tamper と**同一クラスの既存性質**（tamper-evidence であって proof ではない）。「当該セッション内で解錠前に block」までが本 fix の達成範囲＝コメント＆SPEC に明記し「move で tamper-proof になった」と誤読されないようにする。
**TDD:** テスト（raw `task_size:L→S` を block＝RED／raw `task_type:framework→bugfix` を block＝RED／update-task 経由は後続編集で非 block＝GREEN／改竄時 cp_apply 到達前 block＝当該セッションで moat 維持／旧形式 snapshot は移行猶予で非 block）→ FAIL → 実装 → PASS
**受入条件:** gate ループと同方針（snapshot != STATUS かつ snapshot 側非空で block）。cp_apply は tamper チェック後・snapshot 再生成直前。block メッセージは `[task-tamper] ...`。
**Deliverable:** [ ] tamper block 動作 [ ] cp_apply 順序 [ ] 移行猶予 [ ] re-bless 残存を明記 [ ] テストがカバー

### タスク 5: ワークフロー docs/skills 更新

**blockedBy:** Task 3 | **モデル:** `sonnet`
**ファイル:** 対象 `CLAUDE.md` `.claude/rules/state-machine.md` `.claude/skills/aegis-brainstorm/SKILL.md`（＋実 task 編集を指示する doc が他にあれば）
**意図:** task_type/task_size の変更は update-task.sh 経由のみ、を明文化し rollover/brainstorm 手順を更新。
**スコープ（grill 要検討2）:** 実際に task_type/task_size の Edit を指示している doc だけを対象にする。`grep -rn 'task_type\|task_size' .claude/ CLAUDE.md` で確認し、**session-recovery（read-only 復帰＝task を書かない）は対象外**と判断（不要な churn 回避）。確認の結果ヒットすれば追加。
**TDD:** doc のため自動テストなし。contract（check_framework_contract）が PASS することを確認。
**受入条件:** rollover（state-machine）と aegis-brainstorm Step D が update-task.sh を参照。CLAUDE.md に authorized-path を1–2行で記載。
**Deliverable:** [ ] docs 更新 [ ] contract PASS

### タスク 6: 新 lib の配布・契約登録

**blockedBy:** Task 1 | **モデル:** `sonnet`
**ファイル:** 対象 `scripts/check_framework_contract.py:146`（REQUIRED_HOOK_FILES）/ テスト contract self-check ＋ scaffold smoke
**意図:** `snapshot.sh` をコア lib として契約に登録し install 経路で配布されることを保証（F6/v1.3.2 の教訓）。
**確認済み:** `bin/setup.sh:372` の `for lib in hooks/lib/*.sh` が**全 lib を無条件 force-copy**＝setup.sh の編集は不要（minimal/standard でも配布される）。profile 別 lib manifest は存在しない（profile は setup.sh 内）。
**TDD:** contract が `snapshot.sh` の REQUIRED 登録で PASS。scaffold smoke（install 後に hook 実発火）で `.claude/.gate-snapshot` が生成されることを確認。
**受入条件:** `REQUIRED_HOOK_FILES` に `hooks/lib/snapshot.sh` を追加（F6 ライフサポート理由をコメント）。
**Deliverable:** [ ] contract 登録 [ ] install で配布確認

## 事前準備

- [x] STATUS は iteration 43・phase=plan・brainstorm approved
- [x] 設計ノート確定
- [ ] ベースブランチ最新（iter42 push 済・origin/main=e87174e）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件 | AC | Task | テストファイル |
|------|----|------|--------------|
| I3 (task_type/size tamper-evidence) | raw Edit を block | Task 4 | tests/test_post_status_audit*.py |
| I3 authorized-path | update-task.sh 経由変更 | Task 3 | tests/test_update_task.py |
| I3 snapshot 取込 | snapshot に task_type/size | Task 1,2 | tests/test_snapshot_helper.py |
| SF-006 moat 整合 | 改竄が解錠前に block | Task 4 | tests/test_post_status_audit*.py |
| RC-1（非対称解消） | 全 writer 一貫 | Task 2 | scaffold + 各 writer test |
| F6（配布保証） | 新 lib が install で配布 | Task 6 | contract self-check + scaffold smoke |

## 自己レビュー

- 仕様カバレッジ: I3 の3要素（authorized-path / snapshot 取込 / tamper 検知）＋cp_apply 順序＋docs を全タスクで被覆。
- 曖昧さ: 「authorized」＝Bash 経由実行で post-status-audit を通らない＝gate と同じ仕組み。
- 型整合: snapshot フィールド名 `task_type`/`task_size` は STATUS frontmatter と一致。
- 境界整合: Task 2/4 は Task 1 の helper を Consume、Task 5 は Task 3 のコマンド名を Consume。

## リスク

- リスク: 既存 3 writer の refactor で snapshot 形式テストが破損。
  - 対策: Task 2 で形式テストを新形式に同時更新。各 writer 出力をテストで固定。
- リスク: cp_apply 移動が moat の再施錠タイミングを変え iter37/40 の挙動を壊す。
  - 対策: 「正当編集では末尾で idempotent 再施錠／改竄編集では block 前に到達しない」をテストで固定。cp-lock.sh 本体（find -exec chmod）は不変。
- リスク: chicken-and-egg（Task 4 後に task_size を変えられない）。
  - 対策: 本 iteration は task_size=L 固定で実装完了まで変更不要。phase 遷移は task 編集ではない。将来の rollover は update-task.sh 経由（Task 5 で文書化）。
- リスク: full suite で scratch 経路の fail-closed 赤化（trap f）。
  - 対策: Task 2 で test scaffold に snapshot.sh を追加。
- リスク: cross-session re-bless（改竄値が次回 session-start で snapshot に再生成される）。
  - 対策（受容）: gate tamper と同一クラスの既存性質＝tamper-evidence であって proof ではない。当該セッション内で「解錠前 block」までが本 fix の範囲。SPEC/コメントに明記し誤読を防ぐ。
- リスク: 新 lib `snapshot.sh` が install で配布されず post-status-audit が fail-closed で全編集 block。
  - 対策: Task 6 で contract 登録＋scaffold smoke。setup.sh は全 lib 無条件 copy（確認済）。

## 完了条件

- [ ] 全テスト pass（full suite green・record green）
- [ ] レビュー完了（L＝review+qa+security+deploy 全 gate）
- [ ] contract PASS / status_doctor PASS
- [ ] `git status --porcelain` クリーン（moat の mode-flip なし）
- [ ] bash -n 全変更 hook/script

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

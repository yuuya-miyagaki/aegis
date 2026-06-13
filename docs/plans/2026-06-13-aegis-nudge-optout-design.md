# 設計: AEGIS_NUDGE opt-out（P2-a / v1.7.0）

- 日付: 2026-06-13
- 対象: v1.6.3（HEAD `44482d5`）
- 出典: 第7回全力レビュー `docs/full-review-2026-06-13-context-futureproof.md` §2 P2 / §3 / F1
- フェーズ: brainstorm（設計確定済み）→ plan（writing-plans）→ grill-plan → 実装 → grill-code

---

## 0. 目的

レビュー §3「enforce outcomes, delegate paths」を一歩進める。gates・エビデンスログ・永続 state が moat（決定論層）であり、session-start の phase HINT 説教は「やり方(path)の指示」＝賢いモデルには摩擦。**enforcement を一切削らずに、phase 説教だけを opt-out 可能にする。**

将来耐性の局所化: モデルが賢くなるほど説教は摩擦、決定論的禁止は価値が上がる。説教を切り離せる構造にしておく。

---

## 1. スコープ（確定）

- **対象は session-start の常時オン nudge のみ。** skill/agent の合理化テーブルは対象外。
  - 理由: 合理化テーブルは静的 markdown で env では切れず、profile 別の terse/verbose 二重化が必要になり M1（example ミラー 520K の複製税）の教訓に反する。かつオンデマンドロード＝毎ターン予算に乗らない。
  - skill/agent テーブルは「将来も基本いじらない」を非ゴールとして明記。

---

## 2. 機構とデータフロー（確定）

### 2.1 env 変数 `AEGIS_NUDGE`
- session-start.sh が `${AEGIS_NUDGE:-}` を読む。
- **小文字 `off` のみ off。** 未設定・その他の値・不正は **on**（fail-safe＝ガイド多めが安全側）。
- 判定型は既存 `AEGIS_TDD_MODE` と同一: `if [ "${AEGIS_NUDGE:-}" = "off" ]`。

### 2.2 session-start.sh の改修点
- HINT 計算（現 L134-175 の `case "$PHASE"`）は据え置き可。
- **HINT 追記（現 L176-178）を nudge ON 時のみ実行**するよう条件化。off のとき `CONTEXT="${CONTEXT} | ${HINT}"` をスキップ。
- 他の注入行は一切変更しない。

### 2.3 profile 連動（setup.sh）
- `generate_settings()` で settings.local.json を生成する際、**minimal/standard プロファイルのとき `"env": {"AEGIS_NUDGE": "off"}` を注入**。full は注入しない（既定 on）。
- 既存 env キーは merge して保全（K-8 の「hooks 以外の top-level キーを保全」ロジックに追従）。AEGIS_NUDGE 以外の env をユーザーが持っていても壊さない。

### 2.4 前提（実証済み）
- **settings.json の `env` 値はフックのプロセス環境に伝播する**（Claude Code 公式: env は全セッションに適用、spawn されるプロセス＝フックが継承）。→ profile 連動機構は成立。
- shell env と settings env の優先順位は**未文書化**。実装時に実測して docs に注記する。
  - full は settings に env が無いため shell が唯一の源＝per-session 上書きは確実に効く。
  - minimal/standard で一時的に on へ戻す方向は、shell 優先 or settings 編集（優先順位の実測結果に従って記述）。

### 2.5 却下した代替案
- **マーカーファイル方式**（`.claude/.aegis-nudge-off` を setup.sh が置き session-start が読む）。settings-env が実証で効くため新規 state ファイルは不要＝YAGNI で却下。

---

## 3. off で消す/残すの境界（確定）

### 消す（純粋な phase 説教）
- `session-start.sh` の phase HINT（現 L134-178）のみ。
  - 例: implement期 `TDD必須: テストを先に書け / エビデンスなき完了なし`、plan期 `Boundary Map必須 / TDD必須`、review期 `Review Army...` 等。

### 残す（無条件・off でも注入）
- `[Aegis] mode/phase/size | next | gates:` の状態シグナル
- second-opinion BLOCKER / failure_tracking（3回失敗ルール）BLOCKER・WARNING＝エスカレーション強制
- stuck 検知 WARNING（同一 phase 停滞）
- `必読skill(Readで読み込んで従う): ...` のパス＝disable-model-invocation skill の**唯一の起動経路**
- 保守期 maintenance skill パス
- learnings/blockers の project data エンベロープ
- health 警告・CLAUDE_CODE_SUBAGENT_MODEL 警告・AEGIS_TDD_MODE 警告＝安全 advisory
- locale `ドキュメントは日本語`＝ユーザー設定

---

## 4. off 時の advisory は出さない（確定）

- `AEGIS_TDD_MODE=off` は session-start で**警告を出す**（off＝テスト無し本番編集を黙認＝危険）。
- `AEGIS_NUDGE=off` は**警告を出さない**。
  - 理由: nudge off は「ガイドが減る」だけで安全性は不変＝benign。毎セッション警告すると「ノイズを減らす」目的を自壊する。minimal/standard では profile 既定＝想定挙動なので「黙って off」が正しい。

---

## 5. テスト（TDD）

### 5.1 hook 出力（`tests/test_hook_output_schema.py`、AEGIS_TDD_MODE 既存テストと同型）
- `AEGIS_NUDGE` 未設定 + phase=implement → 出力に `TDD必須`（HINT 在）。
- `AEGIS_NUDGE=off` + phase=implement → HINT 説教**不在**、かつ `phase=implement`・`gates:`（あれば）・`必読skill` は**在**（enforcement 残存を実証）。
- `AEGIS_NUDGE=on` / 不正値 → HINT 在（fail-safe）。

### 5.2 setup.sh / scaffold（`scripts/eval_scaffold_smoke.py` 拡張）
- minimal install → settings.local.json に `env.AEGIS_NUDGE=off`。
- standard install → 同上。
- full install → `env.AEGIS_NUDGE` 無し（または env 自体なし）。

### 5.3 example ミラー（M1 lockstep）
- `examples/minimal-project/.claude/settings.local.json` は minimal 既定＝off を反映する必要。drift / contract が緑になるよう同期する。**この同期漏れが起きやすい点を grill-plan で重点監査。**

---

## 6. ドキュメント・版数

- `CLAUDE.md`（L17 付近、TDD 行の隣）: AEGIS_NUDGE と profile 既定を1文追記。
- `README.md`: profiles 節に「nudge 既定（full=on / minimal・standard=off）＋ `AEGIS_NUDGE=off` 上書き（小文字 off のみ）」を追記。
- `docs/architecture-overview.md`: session-start.sh 行に nudge gating を注記。
- framework_version → **1.7.0**（新規 opt-out 機能＋profile 既定の挙動変更＝minor bump。STATUS.md note の「K-14/15/16 は v1.7 へ」とも整合）。
  - **版数ズレの疑い**: 現状 `templates/STATUS.template.md` と `scripts/check_framework_contract.py` の定数が `1.6.2`、`docs/STATUS.md` が `1.6.3`。実装時に実体を確認し整合させる（contract が比較する対象を特定してから bump）。

---

## 7. 検証フロー（合意フロー）

設計確定 → 設計書 commit → writing-plans で実装計画 → **grill-plan**（致命前提を着手前に実証反映）→ TDD 実装 → **grill-code**（仕様乖離・隠れバグ・エッジ・セキュリティ）。

---

## 8. SemVer / 後方互換

- opt-out（gated）機能の追加＝後方互換。既存 install は再 install しない限り挙動不変。
- minimal/standard の既定変更（nudge off）は再 install 時のみ反映＝破壊的ではない。
- → minor bump v1.7.0 が妥当。

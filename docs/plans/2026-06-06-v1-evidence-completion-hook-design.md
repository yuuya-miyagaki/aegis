# evidence 完了強制化（TaskCompleted）設計書

> Phase R 再配分の最終項目。散文の Completion Rule（CLAUDE.md）を、TaskCompleted イベントで決定論的に裏取りする。

**版:** v0.12.6 想定 / **日付:** 2026-06-06 / **mode:** Dev / **task_type:** framework

---

## 1. 目的

CLAUDE.md の Completion Rule は「成果物が実在／検査実行 or 明示スキップ／STATUS が active refs を指す／blockers 記録／evidence ベース要約」を**散文で**要求するだけで、強制力がない。これを「保証＝決定論的強制 / 手順＝モデル委譲 / 揮発値＝隔離」の triage に従い、**保証層の hook 強制へ格上げ**する。

スコープは「STATUS.md が evidence について嘘をついていないか」の裏取りに限定する。red→green の自動検証や成果物の中身評価は非スコープ。

## 2. 方針判断（採用と却下）

- **トリガ方式 = (B) 既存 `check-task-completed.sh` を拡張**（採用）。却下: (A) 新規 Stop hook（Stop は毎ターン発火し誤爆構造が大きい・旧確定案 `check-completion.sh` の弱点）、(C) 両方（二重化で複雑）。TaskCompleted は「タスク完了マーク時」発火で、トリガとして意味的に正しい。
- **検査の二層化**：
  - **層1 整合性**：宣言済み ref がファイルとして実在するか。対象は **scalar ref 全部**（`plan / spec / review / qa / security / deploy / translation`）。誤爆ゼロ（宣言と実体の食い違いは常にバグ）。
  - **層2 結合**：`approved` ゲートに対応 ref が非 null か。対象は evidence 成果物を持つ **`review / qa / security / deploy`** ＋ **`plan`**。
- **`requirements` は対象外**（YAGNI）。YAML リストで bash/正規表現パースのコストが高く、Client モード専用で Dev のフレームワーク作業ではほぼ空。
- **バイパス無し**（YAGNI）。整合性検査に正当な回避需要が乏しい。既存の `next_action` 空チェックもバイパス無しで運用できている。痛みが出てから追加する。
- **実装の置き場 = `check_status.py`**（hook 内 bash ではなく）。理由は §3。

## 3. アーキテクチャ

強制ロジックは依存ゼロパーサ `scripts/check_status.py` 側に置き、`check-task-completed.sh` から呼ぶ。

- `check_status.py` は既に block スコープのパーサ `extract_approval_map`（`gate_approvals:` 専用）と `extract_current_refs`（`current_refs:` 専用）を持ち、**同名キー衝突（`gate_approvals.review` vs `current_refs.review`）を解決済み**。これを再利用する。
- session-start.sh が `python3 "${ROOT}/scripts/check_status.py" --root "$ROOT" --check-status-health 2>&1 || true` で health 警告を取得する**既存パターン**に倣う。

データフロー:

```
TaskCompleted 発火
  → check-task-completed.sh
      → payload 正規化（python3, 既存）
      → STATUS.md 不在/payload 壊れ → emit_allow（既存 fail-safe）
      → 既存: next_action 空/null → exit 2 差し戻し（維持）
      → 新規: python3 check_status.py --check-completion-evidence
          → check_completion_evidence(root) が違反メッセージ列を print（exit 常に 0）
      → 違反あり → stderr に集約連結して exit 2（差し戻し）
      → 違反なし → emit_allow
```

## 4. コンポーネント / 触るファイル

| ファイル | 変更 |
|---|---|
| `scripts/check_status.py` | `check_completion_evidence(root) -> list[str]` 追加・argparse に `--check-completion-evidence` 追加 |
| `examples/minimal-project/scripts/check_status.py` | 上と同期（root と sync 必須） |
| `hooks/check-task-completed.sh` | 新フラグ呼び出しを配線（既存 next_action チェックの後） |
| `examples/minimal-project/hooks/check-task-completed.sh` | **IDENTICAL 同一 Edit**（現状 root と完全一致） |
| `tests/test_check_status.py` | `check_completion_evidence` の Python unit テスト群 |
| `tests/test_hook_output_schema.py`（or task-event テスト） | hook レベル（違反→exit2 / clean→allow） |
| `scripts/check_framework_contract.py` | `FRAMEWORK_VERSION = "0.12.6"` |
| `templates/STATUS.template.md` | `framework_version: "0.12.6"`（contract が sync を FAIL 強制） |

## 5. 検査ロジック詳細

入力 = `docs/STATUS.md` frontmatter。`approval_map` と `current_refs` をパースして違反を集約。

- **層1 整合性**：`ref ∈ {plan, spec, review, qa, security, deploy, translation}` について、`current_refs[ref]` が「非 null・非空の文字列」なら `root` 配下でパス解決し、**実在しなければ違反**。
  - メッセージ例: `current_refs.qa が存在しないファイルを指す: docs/qa-reports/qa-foo.md`
- **層2 結合**：`gate ∈ {review, qa, security, deploy, plan}` について、`approval_map[gate] == "approved"` なら `current_refs[gate]` が**非 null・非空必須**。null なら違反。
  - メッセージ例: `qa ゲートは approved だが current_refs.qa が null（evidence 未宣言）`
- **既存**：`next_action` 空/null → 差し戻し（hook 側 bash で維持）。
- `requirements`（リスト）は対象外。`translation` は層1のみ（ゲート無し）。`spec` は層1のみ（spec ゲート無し）。

> 注: 層1は「非 null なのに実体無し」を、層2は「approved なのに ref null」を突く。両者は相補的で、片方だけでは漏れる（層1は null を見ない／層2は実在を見ない）。

## 6. エラー処理 / フェイルセーフ / 誤爆回避

- **python3 不在** → `python3 check_status.py ... || true` で pass-through（fail-open）。これは hard deny でなく **exit 2 差し戻し**（モデルが修正できる軽い押し戻し）なので、`emit.sh` の「deny/block は python 非依存」要件の対象外。既存 SUBJECT 抽出の fail-safe と整合。
- **STATUS.md 不在 / frontmatter 壊れ** → `check_completion_evidence` は `[]` を返す（誤爆させない）。hook は既に STATUS 不在で early `emit_allow`。
- **誤爆構造**：brainstorm/implement 中はゲート pending・ref null なので層1/層2とも違反ゼロ＝**ルーティンの TodoWrite 完了は素通り**。発火は review 以降のゲートが approved になる開発後期に限定される。
- **AEGIS_ROOT_OVERRIDE**：既存 hook と同様、テスト fixture が実 aegis 状態から隔離できるよう ROOT override を尊重。

## 7. テスト

- **Python unit（`test_check_status.py`）**：
  - clean（全ゲート pending・全 ref null）→ `[]`
  - 各ゲート approved ＋ 対応 ref null → 層2 違反（review/qa/security/deploy/plan を個別に）
  - 非 null ref が実在ファイル → `[]` / 不在 → 層1 違反（各 scalar ref を個別に）
  - `requirements` リスト非空 → 無視（違反なし）
  - frontmatter 欠落 / 壊れ → `[]`（fail-safe）
  - 複数違反 → 集約して全件返す
- **hook レベル（`test_hook_output_schema.py`）**：TaskCompleted payload ＋ 違反 STATUS fixture → exit 2 ＋ stderr に reason / clean STATUS → `emit_allow`。
- **回帰**：全テスト緑・contract（version 0.12.6 sync）・drift 0・root/example IDENTICAL 維持。

## 8. footgun（実装時の注意）

- `check-task-completed.sh` は root/example が **IDENTICAL** → 同一 Edit を両方に。
- `check_status.py` は root/example 両方に存在 → 関数＋フラグ追加を両方へミラー（contract が sync を見る可能性）。
- version 0.12.5 → 0.12.6 は `check_framework_contract.py` と `templates/STATUS.template.md` を対で（contract が version sync を FAIL 強制）。

## 9. 非スコープ

- Stop/SubagentStop hook の新設（旧確定案 `check-completion.sh`）。
- red→green の自動検証、成果物の中身評価。
- `requirements` リストの実在検査。
- バイパス env var。
- blockers/residual-risk 記録や「evidence ベース要約」の自動判定（人間/モデル判断に委ねる）。

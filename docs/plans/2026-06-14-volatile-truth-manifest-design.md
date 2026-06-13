# 設計確定：volatile-truth マニフェスト（v1.8.0）

- 日付: 2026-06-14
- 対象: aegis（HEAD `1ef4c46` / v1.7.2）
- 出典: 第7回全力レビュー `docs/full-review-2026-06-13-context-futureproof.md` §2 P2「volatile-truth マニフェスト復活」/ §3 将来方向
- task_type: framework / task_size: L（新規 script + tests + checker 2 本改修 + version + docs ＝ 6+ ファイル）
- フロー: brainstorm（本書）→ writing-plans → grill-plan → TDD 実装 → grill-code

---

## 0. 目的と非目的

プラットフォーム結合値（CC の hook event 名 / tool 名 / model id / hook 出力 schema）を単一マニフェストに隔離し、「追従トレッドミルの税」を 1 箇所へ集約する。M1（example ミラー自動生成）で実証した「**生成と検証が同一マニフェストを import ＝原理的に乖離不能**」パターンの横展開。

**非目的（YAGNI ガード）**:
- emit.sh の改廃（schema 定義の移設）。emit.sh は pure-bash 単一ソースのまま不可侵。
- JSON 化（既存マニフェストは全て python 定数＝慣行に合わせる）。
- 新 CI エントリポイント / 新ミラー同期面の追加。
- プラットフォーム実体の能動探索（内部から不可能）。

---

## 1. 設計判断（確定事項）

### 判断 A：マニフェストの「仕事」
ハーネス内部から CC の実体（実際の tool 名 / event 名 / 有効 model id）は機械取得できない＝現実乖離の自動検出は原理的に不可能。よって役割を 2 層に分ける:

- **機械強制できる範囲（内部整合）**: 散在リテラルを 1 マニフェストから import / drift 検査で束ねる。
- **機械強制できない範囲（現実整合）**: 各値クラスに「最後にプラットフォーム実体と突合した日付（検証日）」を持たせ、人手の定期再確認を可視化する。

これにより過去セカンドオピニオン（R1「manifest は declarative mirror＝第3同期先になりうる」/ J-1「seed manifest は実消費者が出来てから」）が警告した「沈黙する第3ミラー」を回避する。実 import 消費者があり、現実検証は人手だと明示するため。

### 判断 B：スコープと扱いの強度
| 値クラス | 強度 | 内容 |
|---|---|---|
| model id / effort | 強制（import） | lineage alias / deprecated / opus-only effort / version-pin 禁止 ＋ 検証日。`check_framework_contract.py` が import して照合 |
| hook event 名 | 強制（drift 検査） | 既知 event 集合 ＋ 検証日。template.json の全 event ∈ 既知集合 |
| tool 名 | 軽（レジストリ＋検証日） | 既知 tool/MCP-tool レジストリ。matcher トークン照合は best-effort（WARN） |
| hook 出力 schema | 検証日のみ | 「CC 契約と最後に突合した日」を記録するだけ。emit.sh のフィールド名は移さない |

レビューの「schema 検証日」は **スキーマ定義の移設ではなく日付の記録**で満たす（emit.sh の純度を守る）。

### 判断 C：format・配置・drift 検査の置き場
python モジュール単一ソース ＋ 既存 checker 再利用（アプローチ1）。M1 前例と同型。新エントリポイント・新 CI 面ゼロ。

---

## 2. アーキテクチャ

```
scripts/platform_manifest.py  (原子 + 検証日 / root 専用・非ミラー)
   ├─ import →  scripts/check_framework_contract.py   … model/effort を照合（FAIL）
   ├─ import →  scripts/check_reference_drift.py       … event 集合 drift（FAIL）/ tool レジストリ（WARN）
   └─ import →  tests/test_platform_manifest.py        … 不変条件 + staleness advisory（WARN）

emit.sh は不可侵（schema は検証日のみ記録）
```

`check_framework_contract.py` と `check_reference_drift.py` は MIRROR 対象外（framework repo 専用）。よってこれらが import する `platform_manifest.py` も root 専用で済み、`MIRROR_FILES` への追加は不要（M1 で grill-plan が指摘した MIRROR_FILES 非対称の罠を最初から回避）。

---

## 3. コンポーネント（マニフェスト構造）

```python
# scripts/platform_manifest.py — プラットフォーム真実の原子のみ

ALLOWED_MODELS    = frozenset({"opus", "sonnet", "inherit"})  # lineage alias + inherit
FORBIDDEN_MODELS  = frozenset({"haiku"})                       # 明示的に不使用
EFFORT_LEVELS     = frozenset({"high", "xhigh", "max"})
OPUS_ONLY_EFFORTS = frozenset({"xhigh", "max"})
# version-pin 禁止: 英字 alias のみ許容（数字や `claude-` 接頭辞を含む id は不可）

KNOWN_HOOK_EVENTS = frozenset({
    "SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "PreCompact", "Stop", "SubagentStop", "UserPromptSubmit", "Notification",
    "TaskCreated", "TaskCompleted",
})  # CC が提供する有効 event の既知集合（template の event はこの部分集合）

KNOWN_TOOL_NAMES = frozenset({
    "Bash", "Edit", "Write", "NotebookEdit", "Skill", "Task", "CronCreate",
    "mcp__claude_ai_Vercel__deploy_to_vercel",
    # … template.json の matcher が参照する tool/MCP-tool を網羅
})  # matcher が参照しうる既知レジストリ（best-effort）

PLATFORM_VERIFIED = {                # 人手で実体と突合した日（YYYY-MM-DD）
    "models": "2026-06-14",
    "hook_events": "2026-06-14",
    "tool_names": "2026-06-14",
    "hook_output_schema": "2026-06-14",
}
STALENESS_DAYS = 180                 # 超過で advisory（grill-plan で調整可）
```

**設計分離の肝**: マニフェストは「どの値が存在し・どの状態か」だけを持つ。「どの agent がどの tier か」は aegis 設計判断なので `MODEL_EFFORT_POLICY`（`check_framework_contract.py`）側に残し、その値をマニフェストに照合する。aegis 設計をプラットフォームマニフェストへ過剰流入させない。

---

## 4. データフロー（消費の仕方）

- **check_framework_contract.py**: 原子を import。`check_model_effort_policy()` 内で各 agent の `(model, effort)` を以下で検証:
  1. `model ∈ ALLOWED_MODELS`
  2. `model ∉ FORBIDDEN_MODELS`
  3. version-pin でない（英字 alias のみ）
  4. `effort ∈ EFFORT_LEVELS`
  5. `effort ∈ OPUS_ONLY_EFFORTS ⇒ model == "opus"`

  既存のインライン `_OPUS_ONLY_EFFORTS` 等をマニフェスト import に置換（挙動同値）。`MODEL_EFFORT_POLICY`（tier 割当）はそのまま残す。

- **check_reference_drift.py**: `KNOWN_HOOK_EVENTS` / `KNOWN_TOOL_NAMES` を import。
  - template.json の全 `event_name` ∈ `KNOWN_HOOK_EVENTS`（外れたら **FAIL**＝renamed/typo 検出）。
  - matcher を `|` で分割しトークン抽出、`KNOWN_TOOL_NAMES` 外は **WARN**（regex 曖昧性ゆえ best-effort）。

- **staleness**: `today - PLATFORM_VERIFIED[k] > STALENESS_DAYS` で **WARN**（非ブロック）。

---

## 5. エラー方針（fail 設計）

| 検査 | 失敗時 | 理由 |
|---|---|---|
| model/effort 違反 | FAIL | hard contract（既存挙動踏襲） |
| event 集合 drift | FAIL | 未知 event ＝ 実破壊 |
| tool レジストリ外 | WARN | matcher regex の曖昧性 |
| 検証日 staleness | WARN | 時間経過で CI を壊さない |
| マニフェスト import 失敗 | FAIL-closed | checker が ImportError で停止＝決定論 moat 一貫 |

---

## 6. テスト（TDD）

- `tests/test_platform_manifest.py`（新規）: 必須キー存在・型（frozenset）・`ALLOWED ∩ FORBIDDEN == ∅`・`OPUS_ONLY ⊆ EFFORT_LEVELS`・検証日が ISO 日付として解釈可・staleness 閾値ロジック（古い日付→advisory／新しい→無し）。
- `test_check_framework_contract`（拡張）: `model=haiku`→FAIL／`effort=max,model=sonnet`→FAIL／version-pin id→FAIL／正規組合せ→PASS。
- `test_check_reference_drift`（拡張）: 偽 event 名 template→FAIL／未知 tool matcher→WARN／clean→PASS。
- 既存テスト全件 green 維持 ＋ contract（全 profile）/ drift / scaffold-smoke / PoC 全 PASS を回帰確認。
- ミラー非対称が起きないこと（`platform_manifest.py` を import するのは非ミラー checker のみ）を確認。

---

## 7. docs・版

- CLAUDE.md「Model Policy」: tier 割当（設計）は残し、許容 model/effort 集合の出典を `scripts/platform_manifest.py` に一本化と明記（散文での値の再重複を避ける）。
- 版: 機能追加 ＝ **v1.8.0**。版数 stamp 4 箇所（contract 定数 / template STATUS / example STATUS / 本体 STATUS）統一。
- gates: review + qa + security + deploy 全て（framework / L）。

---

## 8. スコープガード（YAGNI 再掲）

emit.sh 不可侵 ／ schema は日付のみ ／ tool は registry + WARN ／ JSON 化しない ／ 新 CI エントリ無し ／ 新ミラー面無し。

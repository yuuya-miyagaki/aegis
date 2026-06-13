# Design: context budget の原則化（Phase R 第2手）

> 作成日: 2026-06-06 / 対象モデル: Opus 4.8 / 起点: future-proof 再アーキ §3 DELEGATE「context 予算 → 数値撤廃、原則は残す」＋ Round 1 grill ⑤（数値撤廃はコスト価値後退 → observability へ・P2・"後続"）

## 1. 背景と狙い

future-proof 再アーキの三層 triage（保証＝決定論強制 / 手順＝モデルに委ねる / 揮発値＝1箇所隔離）を **context budget** に適用する。routing 原則化（`869231b`・v0.12.3）に続く **Phase R の第2手**。

常時ロードの CLAUDE.md `## Context Budget Policy` には、希少コンテキスト時代の前提だった **hard 数値「同時に開く doc は最大3つ」** が残っている。Opus 4.8 + 1M context では「どれだけ読むか」はモデルが判断すべき手順であり、固定上限はむしろ最適読みを妨げうる。この数値だけを撤廃し、判断をモデルに委ねる。

## 2. 現状の triage

| 要素 | 性質 | 処置 |
|---|---|---|
| **L0-L3 タクソノミー**（L0 always-on / L1 phase refs / L2 task files / L3 on-demand） | reference / 共有語彙 | **維持**。複数スキルが「このファイルは L2 として扱う」と自己分類に使用（browser-assist / integration-assist 等）。撤廃すると語彙が orphan 化し blast radius 拡大。 |
| **「max three docs at once（同時3つまで）」** | 手順 / 固定上限 | **撤廃**。grill ⑤ が問題視した本体。CLAUDE.md と aegis-brainstorm SKILL.md に**二重定義**（routing の 5+/3+ と同型）。 |
| STATUS 起点・pull-based・chat より repo 優先・遷移時要約・pause 前 STATUS 更新 | **原則（保証寄り）** | **維持**。 |

### スコープ確定（ブレスト決定）

- **text のみ原則化**: hard 数値を撤廃し質的原則へ。新規機構（Read 計数 hook 等）は作らない。grill ⑤ の「observability（Read 回数・doc サイズ計測）」は、実測された過剰読みの証拠が無い現状では YAGNI とし、必要になった時点で別設計にする。
- **L0-L3 は語彙として残す**: 撤廃するのは「3」という数値のみ。

### 制約

- `## Context Budget Policy` 見出しは `check_framework_contract.py` の `REQUIRED_CLAUDE_HEADINGS` で**存在必須** → 見出しは維持、本文は contract も drift も内容検証しないため変更安全。
- CLAUDE.md は `MAX_CLAUDE_WORDS = 650` 制約あり（contract 強制）。本変更は語数が**減る**のみで安全。
- agent 12本の `## Context Budget` 節は既に役割特化の質的記述（例: planner「open only requirements + spec + STATUS.md」）で L0-L3 数値も「3」も持たない → **変更不要**。

## 3. 決定事項

1. CLAUDE.md（root + example）の「max three docs at once」を質的原則へ置換。
2. aegis-brainstorm SKILL.md（root + example）の「最大 3 つまで」を同方向へ整合（二重定義の解消）。
3. L0-L3 タクソノミーは語彙として維持、スキルの「L2」自己分類も不変。
4. version `0.12.3` → `0.12.4`（patch）。Phase R の text 変更・挙動変化は数値1個の撤廃のみ。

## 4. 変更内容（最終形）

### diff 1: CLAUDE.md（root + example、該当1行のみ）

```diff
 ## Context Budget Policy

 L0 `CLAUDE.md`+`STATUS.md` (always-on), L1 phase refs, L2 task files, L3 on-demand.

-- Prefer repo files over chat history. Pull-based; max three docs at once.
+- Prefer repo files over chat history. Pull-based.
 - Summarize at phase transitions. Update `docs/STATUS.md` before pauses.
```

**置換句を足さない理由（grill DRY 指摘）**: Session Start §2「Read only `current_refs` relevant to the task」§3「Pull extra docs only when a dependency appears」が既に「必要なものだけ pull」の意図を担う。常時ロードの CLAUDE.md に同義を二度書かないため、数値のみ撤廃し置換句は加えない。

### diff 2: aegis-brainstorm SKILL.md（root + example、行77）

```diff
 ## コンテキスト予算

-- L0 の `docs/STATUS.md` に加え、同時に開く refs は最大 3 つまで
+- L0 の `docs/STATUS.md` を起点に refs を pull する
 - 既存コードの調査は必要最小限
```

STATUS 起点・pull-based の意図は残し「最大 3 つ」の数値だけ撤廃。「必要最小限」は次 bullet が担うため再掲しない。

## 5. 変更ファイル

| ファイル | 変更 |
|---|---|
| `CLAUDE.md` | diff 1 |
| `examples/minimal-project/CLAUDE.md` | diff 1（root と同一） |
| `.claude/skills/aegis-brainstorm/SKILL.md` | diff 2 |
| `examples/minimal-project/.claude/skills/aegis-brainstorm/SKILL.md` | diff 2（root と同一） |
| `scripts/check_framework_contract.py:17` | `FRAMEWORK_VERSION = "0.12.4"` |
| `templates/STATUS.template.md:3` | `framework_version: "0.12.4"` |
| `docs/plans/2026-06-06-v1-context-budget-principle-design.md` | 本書（新規） |

> **⚠ 実装上の footgun（grill 致命指摘）**: routing と違い **example CLAUDE.md は root と全体非同一**（`## Project Overrides`：pnpm・mock search index を持つ）。実装は **該当1行のみの Edit**で行い、**root の全文を example へコピーしない**（override が消える）。対象4行はいずれも各ファイル内で一意（grep count=1）なので行 Edit は安全。

## 6. 挙動変化

- **唯一の挙動変化**: 「同時に開ける doc 数」が hard 上限3でなくモデル判断になる。intent（STATUS 起点・最小限・repo 優先）は文言で維持されるため過剰読みには振れにくい。
- L0-L3 語彙・スキルの L2 自己分類・agent の Context Budget 節は不変。

## 7. Verification（完了条件・全て緑が必須）

```bash
cd aegis
python3 -m unittest discover -s tests -q      # 既存183テスト緑維持
python3 scripts/check_reference_drift.py       # version #7（templates ↔ FRAMEWORK_VERSION）
python3 scripts/check_framework_contract.py    # 見出し存続 / word budget≤650 / version sync
```

- contract: `## Context Budget Policy` 見出し存続、CLAUDE.md（root+example）の word count ≤ 650、`FRAMEWORK_VERSION` ↔ `STATUS.template.md` 一致。
- drift #7: `framework_version` in templates ↔ `FRAMEWORK_VERSION` 一致。

## 8. 完了後 bookkeeping（マージ後に実施）

- memory `aegis-rearchitecture-direction.md`: context budget 原則化を完了として追記（Phase R 第2手・v0.12.4）。
- 再アーキ設計 §3 DELEGATE「context 予算」行と §11 チェックリスト「CLAUDE.md から固定 context 数値撤廃」を消化済みに反映。
- 実装計画を docs/plans に commit（design/plan retention 規約に従う）。
- 直前の routing 同様、まとめて push。

## 9. リスク

| # | リスク | 対応 |
|---|---|---|
| R1 | 数値撤廃で過剰読み（コスト後退） | grill ⑤ の懸念。質的原則（STATUS 起点・最小限・repo 優先＋Session Start §2-3）を文言で維持。**observability を作らないため過剰読みの自動検知は無い**。trigger は人間がセッションの重さ・コストで体感的に気づいた時で、その時点で observability を別設計（YAGNI 解除） |
| R2 | word budget 超過 | 本変更は語数減のみ。contract が ≤650 を FAIL 強制で担保 |
| R3 | version sync 漏れ | contract version sync が FAIL 強制で捕捉 |
| R4 | example が root と乖離 | 同一内容で書き換え、4ファイルすべてを変更対象に明記 |
| R5 | スキルの「L2」参照が orphan 化 | L0-L3 語彙を維持するため発生しない |

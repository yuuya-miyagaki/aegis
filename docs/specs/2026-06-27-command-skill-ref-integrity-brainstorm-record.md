# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

> **訂正（grill-plan 2026-06-27）**: 本記録の「確認した 3 穴」のうち **#1(validate)・#2(retro) は false positive** と判明。
> grill-premise が dogfood の `.claude/commands/*.md` を読んだが、install 実体は `setup.sh:resolve_source` 経由で
> `templates/commands/` の scaffold-safe 版（graceful degrade）。実穴は **#3（skill→update-task.sh）の 1 件のみ**。
> 教訓: 配布検査の前提は **install 実体（resolve_source の source）** を読め。dogfood コピーは別物。
> 確定スコープは `docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md` を正とする。

## 日付

- 2026-06-27（iteration 49）

## テーマ

- 配布 self-containment の射程拡大 — command(.md)・skill(.md) → script の参照整合性検査。
  iter48 で導入した `.py → .py` 参照整合性（`tests/test_profile_referential_integrity.py`）を、
  command 定義と skill が参照する script へ拡張する。

## コンテキスト

- 現在の状況: iter48 で各 profile の shipped `.py` 依存辺を ast 自動抽出し「同梱 ∨ 理由付き
  INTENTIONAL_UNSHIPPED」を検査する機構を導入済み。ただし command(.md)→script・skill 散文参照は
  iter48 が**明示的に射程外**とした（test ファイル冒頭 docstring の bound 記述）。
- きっかけ: iter49 テーマ候補 (b) を grill-premise で一次情報精査。`setup.sh` の実コピー挙動と
  3 profile manifest を突き合わせ、**3 クラスの実 inert 参照**を実証した（投機ではない）。

## 検証した一次情報（grill-premise）

- `setup.sh` の install-set: `required ∪ recommended` を**選択コピー**（bin/setup.sh:508-519）。
  `hooks/lib/*.sh` のみ**wholesale コピー**（copy_hooks, bin/setup.sh:386）。`hooks/<name>` は
  `hooks_include` 経由。→ command/skill→`scripts/*` 参照は `required∪recommended` に対して解決する。
  `hooks/lib/*` 参照は常に存在するので検査対象外。
- 確認した 3 穴（既存テストは全て見逃し＝`.py` 限定走査のため）:
  1. `commands/validate.md`（standard+full 同梱）→ `run_eval.py` + `check_framework_contract.py`（未同梱）
  2. `commands/retro.md`（full 同梱）→ `retro_report.py`（未同梱）
  3. skills `aegis-brainstorm`・`bug-diagnosis`（full 同梱）→ `update-task.sh`（未同梱）
- 3 script は全てリポジトリに**存在**（同梱漏れであって機能欠落ではない）。
- `skill → template` は full 同梱 skill で**穴ゼロ**を実証（射程から除外）。

## 検討したアプローチ

### アプローチ A: iter48 機構を command/skill→script に拡張 ＋ 3 穴を per-finding 解決（採用）

- 概要: 既存 `test_profile_referential_integrity.py` に `.md`→`scripts/*.{py,sh}` 抽出を追加し、
  同じ allow-list / rot 検知で検査。3 穴を性質ごとに解決（ship / de-ship）。
- 利点: 既存機構の低リスク拡張・再発防止が CI に載る・North Star（堅牢な配布）整合・保守可能。
- 欠点: 抽出に散文 false positive の余地（→ allow-list で吸収）。README 件数同期が要る。

### アプローチ B: 検査機構を作らず 3 穴の manifest 修正だけ（最小）

- 概要: validate.md/retro.md/update-task.sh まわりの manifest を直して終わり。
- 利点: 変更最小。
- 欠点: 再発防止ゼロ。将来 command/script が増減したとき同型ドリフトを誰も捕まえない。

### アプローチ C: 汎用 reference linter（command→skill→template→asset 全網羅）

- 概要: あらゆる framework 内部参照を 1 つの汎用検査で網羅。
- 利点: 完全。
- 欠点: YAGNI。skill→template は穴ゼロ実証済で投資対効果が低い。複雑さが保守可能域を超える。

## 決定

- 採用アプローチ: **A**。
- 採用理由: 既存機構の自然な再利用で再発防止を CI 化でき、複雑さが作者保守可能域に収まる。
  発見 3 穴という具体的正当化があり投機実装でない。
- 不採用理由: B=再発防止が無く同型 drift を放置。C=YAGNI（穴ゼロ領域への過剰投資）。

## 発見 3 穴の解決方針（ユーザー承認済）

| 穴 | 参照元(profile) | 解決 | 理由 |
|---|---|---|---|
| #3 `update-task.sh` | skills aegis-brainstorm/bug-diagnosis (full) | standard+full に **ship** | gate routing(S/M/L) の中核＝client 必須。deps(snapshot=wholesale, frontmatter=manifest) 充足 |
| #2 `retro_report.py` | retro.md (full) | full に **ship** | `/retro` は LEARNINGS+STATUS を読む＝client 有用。de-ship より ship が筋 |
| #1 `run_eval.py`+`check_framework_contract.py` | validate.md (standard+full) | validate.md を **de-ship** | `/validate` は framework 自体の tiered eval＝maintainer 専用。inert command 残置より除去が誠実・iter48 の maintainer-only 据置と整合 |

- 非対称（retro=ship・validate=de-ship）はユーザーが明示承認。

## スコープ境界

- やること:
  - command(.md)・skill(.md) → `scripts/*.{py,sh}` 参照整合性検査（`hooks/lib/*` 除外）
  - 3 穴解決: `update-task.sh` を standard+full に同梱、`retro_report.py` を full に同梱、
    `validate.md` を standard+full から除去
  - README の profile 件数同期（`test_readme_profile_counts.py`）
- やらないこと:
  - skill→template（穴ゼロ実証済）／command→skill 相互参照（現状充足）／severity 区別
  - `run_eval.py`・`check_framework_contract.py` の同梱（maintainer-only 据置）

## 未解決事項

- `retro_report.py` / `update-task.sh` が未同梱 script を芋づるで import しないか（→ plan で検証）。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-27-command-skill-ref-integrity-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

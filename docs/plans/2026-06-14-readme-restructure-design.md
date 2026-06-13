# README 縮約・再構成 設計書（docs-only・版据え置き）

- 日付: 2026-06-14
- 種別: docs-only リファクタ（コード挙動ゼロ変更）
- 出典タスク: 第7回全力レビュー §2 後続「README(44KB) 縮約・再構成」（本人合意済み）

## 1. 目的

README.md（現 680 行 / 41KB）を、初見の読者が「何か・なぜ・どう始めるか」へ最短で到達できる長さに縮約し、版間アップグレード履歴を専用ドキュメントへ分離する。情報は削除せず**移設（無損失）**を基本とする。

## 2. 現状分析

| 区分 | 行範囲 | 評価 |
|------|--------|------|
| Intro / Design Priorities / Philosophy | 1–40 | 密・保持 |
| Repository Structure / Core Model | 41–72 | 密・保持 |
| **Native Feature Mapping（委譲マップ）** | 73–92 | **load-bearing（B4）・保持** |
| Quick Start（automated/manual/commands/hooks） | 94–148 | 密・保持 |
| Validation | 149–174 | load-bearing（必須 token）・保持 |
| **Migration（v0.5.0→v1.6.0・26版）** | **175–632** | **458 行＝全体の約67%＝肥大の主因。移設対象** |
| Extensions | 633–647 | load-bearing（eval）・保持 |
| Relationship to v7 / Versioning / Language | 649–680 | 密・保持 |

**結論: 肥大は Migration セクションのみ。それ以外は密かつ多くが load-bearing。縮約の本体は Migration の分離。**

## 3. 不変条件（壊してはいけない＝機械検査あり）

実コードで確認済み（`scripts/` 参照）:

1. **contract（FAIL）** `check_framework_contract.py:687-694`
   - README が token `python3 scripts/check_framework_contract.py` と `python3 scripts/check_status.py --root .` を**部分一致で含む**こと（現状は行160・172に存在）。
   - README に `/Users/` 等のマシン固有絶対パスを**含まない**こと。
2. **drift（WARN）** `check_reference_drift.py`
   - slash コマンド表 `| `/name` | …`（現 8 行）が `.claude/commands/*.md` と双方向一致（`check_commands_in_readme`）。
   - 「N bounded specialist roles / N agents」の N が実 agent 数と一致（`check_readme_counts`）。現状「12」。
3. **eval（FAIL）** `eval_scenario.py:55-95`
   - `## Extensions` セクション（次の `## ` までを正規表現抽出）に "manual opt-in" 文言と setup.sh 非同梱文言の両方を含む。
4. **（非機械・方針）** Native Feature Mapping の委譲マップは B4 で「load-bearing surface＝削除せず文書化」と確定済み。**保持**。

`README` を参照するテスト（`test_secrets_pattern_*`, `test_hook_output_schema`）は **"README.md" を git-add のサンプル名としてしか使わず内容非依存**＝制約にならない。

## 4. 方針

### 4-1. 縮約（本体）
- Migration セクション全体（175–632）を新規 **`docs/MIGRATION-HISTORY.md`** へ**逐語移設**（無損失）。命名は姉妹ファイル `docs/MIGRATION-FROM-v7.md` に倣う。
- README の `## Migration` は短いポインタ節（数行）に置換: SemVer 準拠の一文＋`docs/MIGRATION-HISTORY.md` への導線＋`Stability & Versioning` 節への相互参照。

### 4-2. 再構成（軽微・安全側）
- README 上部（Repository Structure の直前あたり）に簡潔な **`## Documentation`** ドキュメントマップ節を新設し、主要ドキュメントへの導線を集約:
  - オンボーディング教材 `docs/onboarding/README.md`
  - アーキ全体像 `docs/architecture-overview.md`
  - アップグレード履歴 `docs/MIGRATION-HISTORY.md`
  - v7 からの移行 `docs/MIGRATION-FROM-v7.md`
  - 教訓 `docs/LEARNINGS.md`
- 他セクションの順序・本文は据え置き（YAGNI＝過剰な再編はしない）。

### 4-3. 想定結果
- README 680 → 約 230 行（≈66% 減）。情報は移設のみで消失ゼロ。

## 5. スコープ外（意図的）

- **Migration の陳腐化是正**: README の Migration は v1.6.0 止まりだが現行は v1.8.0。欠落版（v1.7.0/.1/.2・v1.8.0）の注記**追記はしない**（変更内容の再構成＝別タスク・捏造リスク）。`MIGRATION-HISTORY.md` 冒頭に「v1.6.0 まで・以降は git log/STATUS 参照」と明記し、起床後の判断に委ねる。
- aegis 自身の STATUS/ゲート ceremony は回さない（flake 修正と同様、通常の git 作業として扱う。STATUS.md は触らない＝post-status-audit 誤発火回避）。

## 6. 実装手順

1. **移設元の退避**: `sed -n '175,632p' README.md > /tmp/old-migration.txt`（移設前スナップショット）。
2. **`docs/MIGRATION-HISTORY.md` 新規作成**: 先頭に h1 `# Migration History` ＋陳腐化注記（下記 §8-D の確定文面）。続けて旧 175–632 の本文を貼り、各版見出しを `### From X to Y` → `## From X to Y` に**1段昇格**（h1 を新設したため階層整合）。`## Migration` 見出し行（175）自体は移さない。
3. **README の 176–632 を短い Migration ポインタ節へ置換**（§8-C の文面）。`## Migration` 見出しは残す。
4. **README に `## Documentation` 節を追加**（§8-A の位置・§8-B の最小構成）。
5. **Validation 節（149–174）は本文非改変**＝不可侵。token 2 本（`python3 scripts/check_framework_contract.py` / `python3 scripts/check_status.py --root .`）と「`/Users/` 絶対パス不在」を保つ。再構成のついでにリワードしない。
6. 検証（§7）。

## 7. 検証計画（grill-code 時に実走）

- **無損失性（機械確認）**: 新 `MIGRATION-HISTORY.md` から版本文を抽出し `sed 's/^## From/### From/'` で見出しを旧形へ戻し、`/tmp/old-migration.txt` と `diff` → **非見出し行が完全一致**（＝本文欠落ゼロ）を確認。
- **事前 grep（実装直前）**: ①`grep -rn 'README.*#\|README.md#' . --include='*.md'`＝README 内アンカーへの incoming 参照ゼロ（root直下/examples/onboarding 含む） ②旧 Migration（175–632）内に `| `/name` |` 行・`N agents`/`N ... roles` 表現・必須 token が無いこと（あれば移設で drift/contract が動くので個別対応）。
- `python3 -m pytest tests/ -q` 全件 green（回帰ゼロ）。
- `python3 scripts/check_framework_contract.py`（root + 必要 profile）→ token/絶対パス FAIL なし。
- `python3 scripts/check_reference_drift.py` → command 表・counts・mirror の新規 WARN/FAIL なし。
- `python3 scripts/run_eval.py --tier 1`（eval Extensions）→ FAIL なし。
- README の outgoing リンク＋新規 doc リンクの実在を grep で確認（リンク切れゼロ）。

## 8. 確定事項（grill-plan 反映済み）

- **8-A `## Documentation` 配置**: `## Core Model` の直後・`## Native Feature Mapping` の直前（概念→読書導線→機能対応→Quick Start の流れ）。
- **8-B `## Documentation` 最小構成（YAGNI）**: onboarding / architecture-overview / MIGRATION-HISTORY の3点に絞る（過剰な純増を避ける）。Quick Start 行96の onboarding 呼び出しは「初学者向け目立つ導線」として残す＝意図的な軽微重複。
- **8-C Migration ポインタ文面（最小）**: SemVer 準拠の一文＋`docs/MIGRATION-HISTORY.md` への導線＋`Stability & Versioning` 節への相互参照。
- **8-D MIGRATION-HISTORY 陳腐化注記**: 「本書は v0.5.0→v1.6.0 のアップグレード注記を収録。v1.7.0 以降は未収録＝`git log` と `docs/STATUS.md` を参照」。

## 9. mirror / make example（確認結果＝対象外）

`check_reference_drift.py` の `MIRROR_DIRS`={.claude/agents,rules,skills,commands, hooks}・`MIRROR_FILES`=特定 scripts のみ。**`README.md` も `docs/` も mirror 対象外**＝root README 改変・`docs/MIGRATION-HISTORY.md` 新設・`docs/plans/` への本設計書追加のいずれも mirror identity drift を起こさず、`make example` は不要。`examples/minimal-project/README.md`（39 行・独立・counts は #9 で別途検査）は本作業で触れない。

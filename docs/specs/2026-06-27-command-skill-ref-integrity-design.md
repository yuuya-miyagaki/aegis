# 設計ノート
<!-- 正本: brainstorming skill -->

> **訂正（grill-plan 2026-06-27）**: 下記の「3 穴」のうち **#1(validate)・#2(retro) は false positive**。
> `setup.sh:resolve_source` が validate.md/retro.md を `templates/commands/` の scaffold-safe 版から install し、
> installed 版は graceful degrade する（validate=check_status.py のみ必須・check_framework_contract は "if available"／
> retro=retro_report.py 不在時に手動要約）。実穴は **#3（skill→update-task.sh）の 1 件のみ**。
> 確定スコープは縮小版の実装計画 `docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md` を正とする
> （skill→script 検査のみ＋update-task.sh を standard+full に同梱／command→script・validate de-ship・retro_report 同梱は破棄）。
> 以下の本文は brainstorm 当時の記録として残すが、#1/#2 関連は無効。

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-27-command-skill-ref-integrity-brainstorm-record.md`
- 要件: 内部 framework iteration（client 製品の要件定義は無し）。前提は brainstorm-record で
  一次情報により実証済（3 穴 + setup.sh install-set 挙動）。

## 問題整理

- 背景: iter48 は profile 配布の参照整合性を `.py → .py` 依存辺に限って検査し、command(.md)→script・
  skill→script を明示的に射程外とした。その結果、shipped な command/skill が未同梱 script を参照して
  install 後に inert 化する穴を CI が捕まえられない。一次調査で 3 穴を実証。
- 判断が必要な論点: 各穴の解決方式（ship / de-ship / allow-list）。→ 決定済（ship×2・de-ship×1）。
- 制約条件:
  - `setup.sh` install-set: `required∪recommended`=選択コピー、`hooks/lib/*`=wholesale。
  - iter48 機構（`_shipped_scripts`・`_violations`・INTENTIONAL_UNSHIPPED・rot 検知）を再利用する。
  - maintainer-only（`run_eval.py`・`check_framework_contract.py`）は iter48 据置で非同梱維持。

## 推奨アプローチ

- 採用方針: `tests/test_profile_referential_integrity.py` に `.md`→`scripts/*.{py,sh}` の辺抽出を追加し、
  既存の violation 検査・allow-list・rot 検知を流用。manifest を 3 穴に合わせて修正。
- 採用理由: 既存純関数（`_violations`）と allow-list 哲学をそのまま再利用でき、新規アーキ不要。
- 検討した代替案と不採用理由: 最小 manifest 修正（B）＝再発防止なし。汎用 linter（C）＝YAGNI。

## コンポーネント分解

- 分割方針: 抽出（純関数）／shipped 判定（既存再利用を拡張）／violation 検査（既存再利用）／manifest 修正。
- 各ユニットの責務:
  - ユニット A `_md_script_edges(md_text)`: `.md` 本文から `scripts/<name>.(py|sh)` トークン集合を返す。
    `hooks/lib/` 配下参照は除外（wholesale で常に存在するため）。
  - ユニット B shipped 判定: 既存 `_shipped_scripts(profile)`（=required∪recommended）を流用。
    対象 `.md` の集合は「その profile が同梱する `.claude/commands/*.md` と
    `.claude/skills/**/SKILL.md`」（required∪recommended から抽出）。
  - ユニット C violation 検査: 既存 `_violations(shipped, edges, allowlist)` を再利用。
    command/skill 用 allow-list（`INTENTIONAL_UNSHIPPED_MD` など）＋ rot 検知。
  - ユニット D manifest 修正: `full.json`（+update-task.sh, +retro_report.py, −validate.md）／
    `standard.json`（+update-task.sh, −validate.md）／README 件数同期。

## インターフェース定義

- `_md_script_edges(md_text: str) -> set[str]`: 入力=`.md` 本文、出力=`{"scripts/x.py", ...}`（hooks/lib 除外）。
- 既存 `_violations(shipped: set[str], edges: set[str], allowlist: dict[str,str]) -> list[str]` を再利用。
- 公開テスト: `test_every_profile_md_ref_is_self_contained`（結合）＋抽出純関数の単体群。

## データフロー / 構造

- 入力: 3 profile JSON。
- 処理: 各 profile で shipped(.md) を列挙 → 各 `.md` を読む → `_md_script_edges` で辺抽出 →
  shipped(scripts) と allow-list に対し `_violations` 判定。
- 出力: 違反リスト（空＝self-contained）。

## 依存関係

- 依存方向: テスト → profile JSON / `.md` ファイル（読み取りのみ）。循環なし。
- 本番コードの変更は manifest JSON（データ）と README（docs）のみ。新規ランタイム依存ゼロ。
- 外部依存: なし（標準ライブラリ `re` のみ）。

## エラーハンドリング

- 想定失敗: 散文中の script 言及が false-positive 辺になる。
  - 対応: 該当辺を理由付き allow-list（INTENTIONAL_UNSHIPPED_MD）で吸収。空 reason は禁止（既存検査流用）。
- 死んだ allow-list エントリ: rot 検知（既存 `test_no_stale_or_redundant_allowlist_entries` と同型）で検出。
- エラー伝播: テスト assert メッセージに「どの profile のどの `.md` がどの script を参照して未同梱か」を明示。

## テスト戦略

- 単体（`_md_script_edges`）:
  - code-fence 内の `python3 scripts/x.py` を拾う／inline code の `scripts/x.sh` を拾う
  - `hooks/lib/foo.sh` 参照は除外する（negative control）
  - 存在しない script トークンも拾う（純関数・install 状態に非依存）
- 結合: 全 profile で command/skill→script が self-contained（本検査）。
- エッジケース:
  - `validate.md` de-ship 後、standard/full が referentially self-contained になる
  - `update-task.sh`/`retro_report.py` 同梱で #2/#3 穴が解消する
  - README profile 件数が manifest と一致（`test_readme_profile_counts.py`）
- 手動確認: full+standard install e2e で参照先 script の存在を assert（または `/retro`・update-task の起動可能性）。
- TDD: 3 穴を install 後 inert と実証する RED → manifest 修正＋検査追加で GREEN（iter48 と同じ二重実測）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

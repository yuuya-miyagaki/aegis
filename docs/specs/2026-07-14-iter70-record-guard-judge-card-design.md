# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: docs/specs/2026-07-14-iter70-record-guard-judge-card-brainstorm-record.md
- 要件: なし（framework 自己改善・動機正本 = docs/full-review-2026-07-06-six-dimensions-evolution.md §R6 罠 n・§R10 gate F6・test #3）

## 問題整理

- 背景:
  - **罠 n**: `record-test-result.py` は引数を無検証で実行・記録する。引数事故（typo・クォート欠落・no-run フラグ）でも実行され、(a) runner 非該当 cmd は judge に不可視なエントリとして記録され「記録したのに unverified」の混乱を生む、(b) `pytest --collect-only` 等の no-run コマンドは src=manual の decidable green として記録され、テストを 1 件も実行せずに judge を green にできる（SF-014 と同クラスの manual 経路・observed 経路は evidence.sh が NO_RUN で防御済みという非対称）。
  - **gate F6**: `audit_deps` は依存 manifest が存在しない repo（aegis 自身を含む依存ゼロ repo）で恒久 `'unverified'` を返し、security ゲート毎回 🟡 → 無意味 ack の踏み車。
  - **test #3**: judge カードの `- テスト: green` はどのコマンドの green か（単一ファイル green か full suite green か）を表示しない＝fail-visible の欠け。
- 判断が必要な論点: 検証の正規化パイプラインをどこから取るか／no-manifest と unverified の境界／判定と表示の走査一元化。
- 制約条件: 判定意味論の変更は (2) の 🟡→info のみに限定。read_test_result の公開シグネチャ不変（ピンテスト ~30 箇所）。単一ソース原則（iter69 教訓 conf8）。fail-closed / fail-visible 維持。

## 推奨アプローチ

- 採用方針: brainstorm record の (1)A + (2)A + (3)A。
- 採用理由: 単一ソース消費（judge の照合ヘルパ・drill の check_no_run_command・audit_deps 内の manifest 知識）で正規化ドリフトを構造的に排除。判定への影響を最小化。
- 検討した代替案と不採用理由: brainstorm record 参照（独自再実装＝ドリフト温床／clean 丸め＝fail-visible 違反／tuple 返し＝消費者破壊／render 再走査＝判定と表示の乖離）。

## コンポーネント分解

- 分割方針: 3 サブ項目とも既存 2 スクリプト内の局所変更。新規ファイルはテストのみ。
- 各ユニットの責務:
  - ユニット A（build-judge-card.py・照合ヘルパ抽出）: `_norm_cmd_match(cmd, pats, strips) -> bool`（`\n`→`;`→DQ/SQ マスク→runner regex any-match）を read_test_result のループから抽出し、`runner_cmd_matches(root, cmd) -> bool | None` を公開（None = patterns/strips 読込不能）。read_test_result は同ヘルパを内部消費（挙動不変）。
  - ユニット B（record-test-result.py・事前検証）: main() で **_execute より前**に (i) `judge.runner_cmd_matches(root, args.command[:500])` — None → fail-closed エラー rc2、False → usage エラー rc2（remediation: `python3 scripts/record-test-result.py "python3 -m pytest -q"` を提示）、 (ii) `drill.check_no_run_command(args.command, patterns_lib=root/"hooks/lib/patterns.sh")` — DrillError → メッセージ表示 rc2。いずれの拒否でもログ書込み・コマンド実行なし。
  - ユニット C（build-judge-card.py・audit_deps 第4状態）: python manifest なし∧`package.json` なし → `'no-manifest'`。`package.json` あり lockfile なし → `'unverified'` 維持（manifest 実在・監査不能）。compute_verdict: `deps == 'no-manifest'` → `info.append("依存 manifest なし（依存ゼロ repo）— 監査対象なし")`（🟡 にしない）。render_card は従来どおり `- 依存監査: no-manifest` を表示。
  - ユニット D（build-judge-card.py・tests スコープ表示）: `read_test_result_detail(root) -> dict`（keys: `tests`, `cmd`, `src`, `ts`; 未決定時は cmd/src/ts = None）を新設し read_test_result を wrapper 化。collect_facts が `tests_cmd`/`tests_src`/`tests_ts` を facts へ追加（判定エントリが決めた場合のみ非 None）。render_card は tests 行を `- テスト: green（判定源: src=manual / cmd=python3 -m pytest -q / ts=2026-07-14T…Z）` 形式へ（detail 欠落時は従来表示）。

## インターフェース定義

- ユニット間の契約:
  - B → A: `runner_cmd_matches(root: Path, cmd: str) -> bool | None`。True=記録可 / False=usage エラー / None=検証不能（fail-closed）。
  - B → drill: `check_no_run_command(cmd, patterns_lib=root/"hooks/lib/patterns.sh")`。例外 DrillError=拒否。record と judge が**同じ target-root の patterns.sh** を読む（drill 既定の FRAMEWORK_ROOT 相対でなく root 相対を明示）。
  - D → render_card: facts 追加キーは optional（`facts.get(...)`）。build() の except パス（デフォルト facts）はキー欠落のまま通る。
- 公開 API:
  - `read_test_result(root) -> str`: **不変**（'green'/'red'/'unverified'）。
  - `read_test_result_detail(root) -> dict`: 新設。
  - `audit_deps(root) -> str`: 返り値集合に `'no-manifest'` 追加（消費者は compute_verdict / render_card のみ）。
  - `record-test-result.py` CLI: 非 runner・no-run・検証不能で rc2 / ログ不変。従来成功経路は rc0 で不変。

## データフロー / 構造

- 入力: CLI 引数 command（record）／evidence-log + patterns.sh + manifest ファイル群（judge）。
- 処理: record = 検証（runner 照合 → NO_RUN）→ 実行 → 記録。judge = 走査（detail 化）→ facts → verdict → card。
- 出力: evidence-log エントリ（従来 schema 不変）／judge カード（tests 行にスコープ・deps に no-manifest）。

## 依存関係

- 依存方向: record-test-result → {build-judge-card, run-test-strength-drill}（既存 importlib ロードを流用・新規依存なし）。循環なし。
- 外部依存: なし（stdlib のみ・patterns.sh は既存 bash-source 経由）。

## エラーハンドリング

- 想定失敗:
  - patterns.sh 不在／regex 読込不能（record 事前検証時）→ **fail-closed**: rc2・記録なし（judge が判定不能なエントリを増やしても無意味なため）。
  - shlex 解析不能なクォート → check_no_run_command が DrillError（fail-closed・iter69 実装）→ rc2。
  - audit_deps のツール不在/timeout → `'unverified'` 維持（従来どおり 🟡）。
  - evidence cmd に改行・バッククォート・500 字長 → 表示サニタイズ（`\r\n`→`;`・バッククォート→`'`・120 字で `…` 切詰）＝judge カードへの偽見出し注入を遮断。
- エラー伝播の方針: record は検証エラーを stderr メッセージ＋rc2 で即終了（部分書込みなし）。judge は従来どおり例外を 🟡 に丸める（build() の except パス不変・新規 facts キーは .get で欠落許容）。

## セキュリティ考慮（判定影響の明示）

- (1) は受理集合の**縮小のみ**（新たな green 経路を作らない）。manual 経路の no-run 偽装（SF-014 の manual 版）を書込み前に遮断＝net 改善。denylist の原理的不完全性（LEARNINGS line148）は残存＝positive proof は iter71+ の別トラック。
- (2) deps は従来から advisory-only（never blocks・compute_verdict コメント）。降格は ack 儀式の除去のみでブロック力不変。manifest 削除による監査回避は diff/review ゲートで可視（残存考慮として security レポートに記載）。
- (3) 判定意味論の変更ゼロ。カード注入はサニタイズで遮断。

## テスト戦略

- 単体:
  - record: 非 runner cmd（`ls -la`）→ rc2・ログ不生成／runner+no-run（`pytest --collect-only`）→ rc2／クォート偽装（`pytest "--collect-only"`）→ rc2（shlex 正規化の回帰）／patterns.sh 不在 root → rc2 fail-closed／正当 runner → rc0・src=manual エントリ記録（既存挙動の回帰ピン）。
  - judge detail: 決定 green/red エントリ → detail に cmd/src/ts／unverified（決定なし・fp stale）→ detail None／read_test_result wrapper が従来文字列を返す（既存 ~30 ピンテストが回帰網）。
  - audit_deps: manifest ゼロ tmp repo → 'no-manifest'／package.json のみ（lock なし）→ 'unverified'／compute_verdict: no-manifest → info・yellow 空／カードに `依存監査: no-manifest` 表示。
  - render_card: サニタイズ（改行入り cmd が 1 行化・`##` 見出し注入不能・120 字切詰）／facts キー欠落（except パス相当）で crash しない。
- 結合: 実 repo fixture（symlink hooks/lib・test_test_runner_realness.py の fixture 流儀）で record → judge の一気通貫（記録した green が card にスコープ付きで出る）。
- エッジケース: cmd 500 字境界・CRLF・空 command・`--root` 相対パス。
- 手動確認: 本 repo で `/judge` プレビュー・security ゲートの deps 行が info 化すること（E2E は qa フェーズで実測）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-14-iter70-record-guard-judge-card-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

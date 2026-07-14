# 設計ノート — iter69: B1 drill 強化（NO_RUN 拒否＋mutant 構文検証＋コメントラン floor 除外＋since baseline）
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-14-iter69-drill-hardening-brainstorm-record.md`
- 要件: docs/full-review-2026-07-06-six-dimensions-evolution.md §4 Phase 1「1-5」（R4・R6 罠 l,f）／LEARNINGS:76（since 起票）・LEARNINGS:136（コメントラン起票）

## 問題整理

- 背景: B1 drill の看板「偽造不能」に対し、(R4) test_command が実はテストを実行しない（`--collect-only` 等）＋構文破壊 mutant の組で **no-run PASS フォージ**が成立する。また (罠 l) 純コメント/docstring 孤立ハンクが floor を不成立にし、(罠 f) per-task コミット運用で diff HEAD が空になり、いずれも sanctioned skip への逃げを強制している。
- 判断が必要な論点: ① NO_RUN regex の消費方法（意味論ドリフトなしで single source を守る）② 構文検証の対象言語と帰責 ③ floor 除外が gaming 面積を増やさないか ④ since を承認時経路（固定 argv）へどう届けるか。
- 制約条件: 承認時経路 `check_status.py::run_qa_drill` は runner を `--root/--spec/--report` 固定で起動（無改修が望ましい）。judge は report から `verdict:` を regex 抽出（`build-judge-card.py:477`）。patterns.sh が regex の single source（変更禁止）。drill の哲学＝inconclusive は全て fail-closed。

## 推奨アプローチ

- 採用方針: 4 サブ機能すべてを `scripts/run-test-strength-drill.py` 内に閉じて実装。`since` は `.drill` spec の optional key。NO_RUN は bash+grep subprocess で evidence.sh と同一エンジン評価。
- 採用理由: 承認時経路・judge・patterns.sh を一切触らずに R4／罠 l／罠 f を根治できる。全 pre-check は baseline 実行前に fail-closed で完結。
- 検討した代替案と不採用理由: brainstorm 記録参照（B=部分実装は起票済み罠を先送り／C=Python re 翻訳は `[[:space:]]` の silent mis-match リスク）。

## コンポーネント分解

- 分割方針: 既存の「parse → 反ガミング → baseline → mutant loop → report」パイプラインに、独立な pre-check とデータ供給関数を挿す。各サブ機能は単独でテスト可能な純関数寄りヘルパーにする。
- 各ユニットの責務:
  - `parse_spec`（既存拡張）: optional key `since` の形状検証（存在時: 非空文字列。それ以外は従来どおり）。
  - `check_no_run_command(cmd, patterns_lib=None)`（新規）: patterns.sh を source し `printf %s "$cmd" | grep -qE "$AEGIS_TEST_NO_RUN_FLAG_REGEX"` を単一 bash subprocess で実行。match（rc0）→ DrillError「no-run コマンドはテスト強度を証明しない」。rc1=通過。regex 未定義／patterns.sh 不在／grep エラー（rc≥2）／subprocess 失敗 → DrillError（fail-closed）。**patterns.sh の解決は `--root` 相対でなくスクリプト位置相対**（`scripts/../hooks/lib/patterns.sh`・update-task.sh の ROOT 解決と同型）: drill の `--root` は検証対象プロジェクト（scratch clone や temp repo）を指すことがあり、root 相対だと「patterns.sh の無い scratch repo で全 drill が block」（既存 E2E テスト全滅）か fail-open かの二択になる。framework install では scripts/ と hooks/ が兄弟のため解決は常に成立。`patterns_lib` 引数はテスト用 fixture 注入口。
  - `resolve_since_ref(root, since)`（新規）: `git rev-parse --verify -q <since>^{commit}` ＋ `git merge-base --is-ancestor <since> HEAD` を検証し、フル sha を返す。いずれか失敗 → DrillError（存在しない ref／HEAD の祖先でない ref は監査不能）。
  - `syntax_check_mutants(root, mutants)`（新規）: mutant 適用後の全文をメモリ上に構成し、`.py`→`compile()` builtin（py_compile 同等の構文検査・temp file 不要）／`.sh`・`.bash`→`bash -n`（stdin 経由・temp file 不要）で構文検証。**precondition**: 元ファイルが parse 不能なら当該ファイルの mutant は検証 skip（帰責不能・baseline red が別途受け止める）。ファイル不在・行範囲外・original 不一致の mutant も pre-pass では skip（apply_mutant の既存エラー経路が後段で受け止める＝メッセージ正本を二重化しない）。違反 mutant を全件列挙して DrillError（「構文破壊 mutant は assert の強さを証明しない — 意味を変え構文を保つ mutant に書き換えよ」）。未知拡張子は対象外。
  - `non_coverable_lines(root, rel)`（新規）: 対象ファイルの「空行＋行コメント（`.py`/`.sh`/`.bash`→`#`、`.js`/`.ts`/`.jsx`/`.tsx`/`.mjs`/`.cjs`→`//`）＋py docstring（AST: Module/ClassDef/FunctionDef/AsyncFunctionDef の body[0] が Constant str の行範囲）」の行番号集合を返す。読取不能・AST parse 失敗は空集合（除外なし＝厳格側に劣化）。
  - `anti_gaming_violations(..., exempt_lines=None)`（既存拡張）: floor ループで、ラン内の全行が exempt に含まれるランを skip。`None` 時は従来挙動（既存単体テスト無傷）。検査 (a)（mutant は追加行上）は不変。
  - `write_report(..., since=...)`（既存拡張）: 機械ブロックに `since: <実際に diff した ref>` 行を常時追加（HEAD／empty-tree／spec 指定 ref）。
  - `run_drill`（既存拡張・配線）: parse → NO_RUN check → ref 決定（since 優先、なければ resolve_diff_ref）→ added lines → exempt 計算（coverage 対象ファイルのみ）→ 反ガミング → mutant 構文検証 → baseline → mutant loop → report。除外したランの件数を stdout に明示（透明化）。

## インターフェース定義

- ユニット間の契約:
  - parse_spec → run_drill: dict（`since` は optional str）。
  - check_no_run_command / resolve_since_ref / syntax_check_mutants: 失敗は全て DrillError（既存の fail-closed 経路に乗る）。
  - non_coverable_lines → run_drill → anti_gaming_violations: `dict[str, set[int]]`（coverage 対象ファイルのみ計算＝I/O 有界）。
- 公開 API（CLI/spec 契約）:
  - `.drill` spec: `{"test_command", "timeout_seconds", "mutants", "since"?}` — `since` 追加は後方互換（省略時は従来挙動）。
  - report 機械ブロック: `verdict/mutants_total/mutants_caught/baseline/survived` に `since:` を追加（judge は verdict のみ抽出のため安全。SKIP ブロックは不変）。

## データフロー / 構造

- 入力: `.drill` spec・working tree・git 履歴・patterns.sh（read-only）。
- 処理: 上記 run_drill 配線。全 pre-check は baseline 実行前（テスト実行コストを浪費しない）。
- 出力: 従来どおり exit 0/1 ＋ report。新規に `since:` 行と floor 除外件数の stdout 表示。

## 依存関係

- 依存方向: run-test-strength-drill.py → patterns.sh（bash source・read-only）／git。循環なし。
- 外部依存: bash・grep・git（いずれも既存前提）。py_compile は stdlib。

## エラーハンドリング

- 想定失敗: patterns.sh 不在／regex 未定義／grep 実行不能／since ref 不在・非 ancestor／mutant 構文破壊／temp file I/O 失敗。
- 対応: すべて DrillError → 既存の「DRILL BLOCKED (fail-closed)」経路で verdict=FAIL・exit 1。**新機能に fail-open 分岐は作らない**（唯一の緩和方向＝floor 除外は、除外計算の失敗時に「除外しない＝厳格化」へ劣化）。
- エラー伝播の方針: 既存 DrillError 集約に統一（新例外型は作らない）。

## セキュリティ考察（gate 機構への影響）

- **NO_RUN**: single source（patterns.sh）を同一エンジン（grep -E）で消費＝evidence.sh との意味論ドリフトゼロ。R4 のフォージ経路（collect-only＋構文破壊）は NO_RUN 拒否と構文検証の**二重**で閉塞。
- **floor 除外**: コメント行に置いた mutant は必ず survived→FAIL のため、除外は「充足不可能な要求の削除」であり偽造面積を増やさない。混在ラン（コード行を含む）は floor 維持。
- **since**: diff 範囲を広げる方向のみ（committed-this-iteration を追加扱い）。ref の恣意選択（弱テスト部分だけを diff に載せる）は理論上残るが、非 ancestor 拒否＋report `since:` 明記＋レビュー人手で緩和（R6 の「軽減可」分類どおり）。省略時の挙動は完全不変。

## テスト戦略

- 単体: `check_no_run_command`（match/クリーン/regex 未定義/patterns.sh 不在）／`resolve_since_ref`（正常/不在 ref/非 ancestor）／`syntax_check_mutants`（py 破壊/sh 破壊/構文保存 mutant 通過/元ファイル parse 不能 skip/未知拡張子 skip）／`non_coverable_lines`（行コメント・空行・docstring・混在・parse 失敗）／`anti_gaming_violations` exempt 分岐（全除外ラン skip/混在ラン維持/None 従来挙動）。
- 結合（E2E・scratch repo）: ① `--collect-only` spec → BLOCKED ② 構文破壊 mutant → BLOCKED（spec エラー列挙）③ コメントのみハンクを含む diff が mutant なしで floor 通過→PASS ④ committed 変更＋`since` で PASS（従来は added zero）⑤ 非 ancestor since → BLOCKED ⑥ report に `since:` 行。
- エッジケース: shebang のみのラン（`#`扱い＝除外）／CRLF／`since: HEAD`（diff 空→mutant が置けず反ガミング違反＝フォージ不能）／docstring と code の混在ラン（floor 維持）。
- 手動確認: 本反復の実 diff で drill を実走（qa フェーズの実環境 E2E）。
- 既存ピン更新: report 形状ピン（`test_pass_report_shape` 等）に `since:` 行を反映。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-14-iter69-drill-hardening-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

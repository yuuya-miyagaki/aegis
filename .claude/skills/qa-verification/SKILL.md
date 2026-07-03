---
name: qa-verification
description: "QA phase verification: reproduce reported behavior, run test suites, generate evidence."
disable-model-invocation: true
user-invocable: false
---

# QA 検証プロセス

> qa agent が QA フェーズで参照する。再現・テスト実行・エビデンス収集の
> 手順を標準化し、根拠なき完了を防止する。

## いつ使うか

- qa フェーズで検証を実施するとき
- テスト実行とエビデンス収集が必要なとき
- 再現手順を構造化する必要があるとき

## テストスイート実行手順

1. プロジェクトの `CLAUDE.md` または `README.md` からテストコマンドを読む
2. テストを実行し、結果を記録する
3. lint / type-check / build も実行する（該当する場合）
4. 全結果を QA レポートに記載する

```
確認事項:
- テストコマンドが明記されているか
- 全テストが PASS か（FAIL がある場合は原因を記録）
- lint / type-check エラーがないか
```

## 再現手順テンプレート

検証対象の振る舞いごとに以下を記録する:

```
### 検証項目: <項目名>
- 前提条件: <セットアップ手順>
- 操作: <実行した操作>
- 期待結果: <plan/spec の受入条件>
- 実際結果: <観測された結果>
- 判定: PASS / FAIL
```

## エビデンス収集チェックリスト

QA レポート完了前に以下を全て実施する:

- [ ] テストスイートを実行し結果を記録した
- [ ] lint / type-check / build を実行した（該当する場合）
- [ ] plan の受入条件と突合した
- [ ] 各検証項目に PASS / FAIL 判定を付与した
- [ ] FAIL 項目にはブロッカーとして原因を記録した

## 機能対照表（必須出力）

QA 開始前に以下を作成:

| # | 要件/plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|

- requirements + plan の機能リストから全項目を列挙
- 「検証対象」が存在しない = 実装漏れ → implement へ差し戻し

## qa-browser 委譲ルール

`STATUS.md` の `ui_surface: true` の場合:

1. ブラウザ検証が必要な項目を特定する
2. qa-browser エージェントに委譲する（ページ、操作、期待動作を指定）
3. 返却されたエビデンスを QA レポートに統合する
4. **委譲粒度**: 長尺検証は1委譲あたり**5 項目程度**に分割（実測:19 項目一括で途中停止3回）。

qa-browser は browser-assist スキル（`.claude/skills/browser-assist/SKILL.md`）を使用。
`$B` 利用可能時はブラウザ自動操作、未インストール時は Playwright MCP で検証。

## plan 事前チェックリスト

plan に `## QA チェックリスト` が定義されている場合:
1. そのリストを baseline として QA チェック項目に採用する
2. QA 実行中に発見した不足項目は追加で起票できる（plan に縛られない）
3. 追加項目には「plan 外追加」と明記する

## テスト強度ドリル（mutation drill・必須）

qa ゲート承認の前に実施する。承認時にハーネス（`pre_approve_gate`）が
**同じドリルを実走**して合否を決めるため、合格しない限り承認は拒否される
（偽造・古い結果は通らない）。合否はハーネスが決め、あなたは説明するだけ。

### コードを変更したタスクの手順

1. **変更コードを読む**: `git diff HEAD`（追跡分）と `git status`（新規ファイル）で
   今回の追加行（`+`）を把握する。
2. **mutant を選定**: 各「変更ハンク（連続した追加行のかたまり）」に**最低1個**、
   「テストが守ると主張する振る舞い」を壊す mutant を置く（比較反転・境界±1・
   条件否定・早期 return 等）。mutant は必ず**追加行**の上に置く（文脈行は不可）。
3. **入力仕様を書く**: `docs/qa-reports/test-strength.drill` に JSON で記録:

   ```json
   {
     "test_command": "<関連テストだけを走らせる最小コマンド>",
     "timeout_seconds": 60,
     "mutants": [
       {"file": "src/discount.py", "line": 12,
        "original": "    if total >= 100:", "mutated": "    if total > 100:"}
     ]
   }
   ```

   - `original` は対象行の**現在の中身と完全一致**させる（行ズレ防止）。
   - `test_command` は**関連テストにスコープ**し（承認のたび実走するため軽く）、
     かつ**冪等**にする（2回続けてクリーンに走る形。さもないと flaky 判定で blocked）。
   - シェル機能（パイプ・リダイレクト・`&&`）は使えない（単一コマンド＋引数のみ）。
4. **プレビュー実走**してユーザーに見せる前に結果を確認:

   ```bash
   python3 scripts/run-test-strength-drill.py --root . \
     --spec docs/qa-reports/test-strength.drill \
     --report docs/qa-reports/test-strength.md
   ```
5. **平易な日本語へ翻訳**して提示する（合否はハーネス決定。説明は合否を動かさない）:
   - 合格✅例:「『割引計算』にわざとバグ（`>=`→`>`）を入れたらテスト〇〇が
     気づいて赤くなりました。このテストは意味があります。」
   - 不合格⚠️例:「バグを入れてもテストは緑のまま＝この部分は取りこぼします。
     **やること: 100 円ちょうどのケースのテストを追加してください。**」
6. `current_refs.qa` を `docs/qa-reports/test-strength.md` にする。
7. **コードを変更したら `.drill` を作り直す**（行番号がずれると承認時に弾かれる）。
8. ドリル中は対象ファイルを開く watch テストや自動保存エディタを止める
   （ハーネスは並行編集を検知すると安全のため承認を中止する）。

### テスト対象コードが無いタスク（スキップ宣言）

ドキュメント・設定・文言のみの変更など、mutant を作れないタスクは、
**スキップを明示**した `.drill` を書く（qa は update-gate.sh で n/a にできないため、
証拠ファイル側で宣言する）:

```json
{"skip": true, "reason": "ドキュメントのみの変更でテスト対象コードなし"}
```

> **skip スペックは手順4のプレビューを実行しない**: standalone runner は
> `test_command` 必須で skip を解釈できず `verdict: FAIL` になる。skip 解釈は
> 承認時の `check_status.py::run_qa_drill` のみ（`verdict: SKIP`）。`.drill` を置いたら
> プレビューせず `update-gate.sh qa approve` に委ねる。

理由はユーザーが見る証拠に残る。安易なスキップは避け、コードがあるなら必ずドリルする。
ただし **framework 自体の改修などコードを per-task でコミット済みのタスク**は、qa 承認時の
working-tree diff（`git diff HEAD`）が空＝mutant を置く追加行が無く skip になるのは
*想定どおりの縁ケース（欠陥ではない・撤去しない）*。この場合は skip 理由に**手動 mutation
同等の代替実証**（RED-first TDD・対象テストへの一時変異→赤化確認・canonical fixture
パリティ等）を明記する。ドリルの本来のターゲット＝*未コミットのプロダクトコード*では従来
どおり機能する。
スキップ時もハーネスがレポートを生成するので、`current_refs.qa` を
`docs/qa-reports/test-strength.md` にすること（さもないと完了時に証拠不足で弾かれる）。

> 前提: このドリルは git リポジトリ（とコミット履歴）を必要とする。git 未初期化なら
> `git init && git add -A && git commit` を先に行う（初回コミット前でも動くが、git は必須）。

## QA レポート出力

- `docs/qa-reports/` に `QA-REPORT.template.md` を使用して配置
- 全検証項目の判定一覧を含める
- ブロッカーがあれば STATUS.md に記録

## 禁止事項

- エビデンスなき PASS を出さない
- テストを実行せずに「前回と同じ」で省略しない
- FAIL 項目を隠さない
- 検証範囲を勝手に縮小しない

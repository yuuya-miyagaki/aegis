---
name: qa-verification
description: "QA phase verification: reproduce reported behavior, run test suites, generate evidence."
disable-model-invocation: true
user-invocable: false
---

# QA 検証プロセス

> qa agent が QA フェーズで参照。再現・テスト実行・エビデンス収集を標準化し、根拠なき完了を防ぐ。

## いつ使うか

- qa フェーズの検証・テスト実行・エビデンス収集・再現手順の構造化。

## テストスイート実行手順

1. プロジェクトの `CLAUDE.md` または `README.md` からテストコマンドを読む
2. テストを実行し、結果を記録する
3. lint / type-check / build も実行する（該当する場合）
4. 全結果を QA レポートに記載する

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
- [ ] lint/type-check/build を実行した（該当する場合）
- [ ] plan の受入条件と突合した
- [ ] 各検証項目に PASS/FAIL 判定を付与した
- [ ] FAIL 項目にはブロッカーとして原因を記録した

> **手動記録の green は positive proof 必須（iter71）**: `scripts/record-test-result.py`
> は green（exit 0）に marker verdict を必須化。0 件実行の偽 green（`unittest discover`
> パターン不一致・`npm test`→`true`・pytest `-q`）は **rc2 拒否・ログ非書込**。red は
> 従来どおり記録。受理 green には additive な `"marker": true`（judge 非消費の監査）。

## 機能対照表（必須出力）

QA 開始前に以下を作成:

| # | 要件/plan の機能 | 検証対象 | 検証方法 | 判定 |
|---|----------------|---------|---------|------|

- requirements + plan の機能リストから全項目を列挙
- 「検証対象」が存在しない = 実装漏れ → implement へ差し戻し

## qa-browser 委譲ルール

`ui_surface: true` の場合、qa-browser への**標準委譲プロンプト**は以下を満たす:

1. **分割**: 1委譲あたり **5 項目程度**・各項目に連番。実測:19 項目一括で途中停止3回。
2. **完了拘束**: **全項目のエビデンスが揃うまで最終報告を出さない**。途中停止も partial を final と偽らず、完了済/未完の項目番号を示す。
3. **再開**: 停止時は新規委譲でなく **SendMessage** で同一エージェントを継続。
4. **進捗**: 各項目完了ごとに `[n/N done]` を報告。
5. **エビデンス**: 項目ごとに `{操作, 期待, 実測, PASS/FAIL, screenshot/console}`。
6. **read-only**: tree 変更禁止＝既存ファイル編集・`git checkout/restore/reset/clean/stash` 実行禁止。書込みは指定パスへの新規 evidence 成果物のみ。汚れたら停止して報告し、自己復旧しない。正本: routing.md「Verification delegation」。

返却を QA レポートに統合。SendMessage 再開も不能なら未完項目を blocker に記録（3-failure ルール）。
qa-browser は browser-assist（`.claude/skills/browser-assist/SKILL.md`）を使い、`$B` かPlaywright MCP で検証。

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
   - `test_command` は**関連テストにスコープ**し（承認のたび実走するため軽く）・
     **冪等**にし（2回続けてクリーンに走る形・さもないと flaky で blocked）・**実ランナー
     必須**（positive proof・iter71＝baseline 出力にサマリ marker〔pytest `===== N passed
     =====`／unittest `Ran N`+`OK`／jest／vitest／go／cargo〕が要る）。**pytest は `-q` 不可**
     （marker 非出力）。`grep`／`true` 等の非ランナーは `DRILL BLOCKED (baseline no-test-proof)`。
   - シェル機能（パイプ・リダイレクト・`&&`）は使えない（単一コマンド＋引数のみ）。no-runフラグ（`--collect-only`等）も承認時に拒否（patterns.shのNO_RUN）。mutantは構文を保って意味を変える（構文破壊は`.py`compile・`.sh`bash-n検査でspecエラー）。コミット済み反復はキー`"since":"<基点sha>"`で基点以降のcommitted変更を対象化（基点はHEAD祖先必須・reportに記録）。コメント・空行・docstringだけのハンクはcoverage-floorから自動除外。
4. **プレビュー実走**してユーザーに見せる前に結果を確認:

   ```bash
   python3 scripts/run-test-strength-drill.py --root . \
     --spec docs/qa-reports/test-strength.drill \
     --report docs/qa-reports/test-strength.md
   ```
5. **平易な日本語へ翻訳**して提示（合否はハーネス決定。説明は合否を動かさない）:
   ✅例「わざとバグ（`>=`→`>`）を入れたらテスト〇〇が赤くなった＝このテストは有効」／
   ⚠️例「バグを入れても緑のまま＝取りこぼし。**やること: 100円ちょうどのテストを追加**」
6. claims 付き QA レポート（下記）を書き、`current_refs.qa` はそれを指す
   （judge が読むのは ref先の claims のみ・test-strength.md は固定パス証拠として自動参照）。
7. **コードを変更したら `.drill` を作り直す**（行番号がずれると承認時に弾かれる）。
8. ドリル中は watch テスト・自動保存エディタを止める（並行編集検知で承認中止になる）。

### テスト対象コードが無いタスク（スキップ宣言）

**diffが空になっただけの反復はskipでなく`"since"`**（基点sha指定）。skipは「テスト対象コード自体が無い」場合に限る。mutant を作れないタスク（ドキュメント・設定・文言のみの変更など）は
**スキップを明示**した `.drill` を書く（qa は update-gate.sh で n/a 不可＝証拠側で宣言）:

```json
{"skip": true, "reason": "ドキュメントのみの変更でテスト対象コードなし"}
```

> **skip スペックは手順4のプレビューを実行しない**: standalone runner は
> `test_command` 必須で skip を解釈できず `verdict: FAIL` になる。skip 解釈は
> 承認時の `check_status.py::run_qa_drill` のみ（`verdict: SKIP`）。`.drill`設置後は
> プレビューせず `update-gate.sh qa approve --ref <QAレポート>`へ。

理由はユーザーが見る証拠に残る。安易なスキップは避け、コードがあるなら必ずドリルする。
ただし **framework 改修などコードを per-task でコミット済みのタスク**は、qa 承認時の
working-tree diff（`git diff HEAD`）が空＝skip になるのは*想定どおりの縁ケース（欠陥ではない・撤去しない）*。
skip 理由に**手動 mutation 同等の代替実証**（RED-first TDD・一時変異→赤化確認等）を明記する。
スキップ時も手順6と同じ claims 付き QA レポートを ref にすること（実在ファイルなら受理）。

> 前提: このドリルは git リポジトリ（とコミット履歴）を必要とする。git 未初期化なら
> `git init && git add -A && git commit` を先に行う（初回コミット前でも動くが、git は必須）。

## QA レポート出力

- `docs/qa-reports/` に `QA-REPORT.template.md` を使用して配置
- 判定一覧と ```claims ブロック（雛形の `verdict` を記入）を含める
- ブロッカーがあれば STATUS.md に記録

## 禁止事項

- エビデンスなき PASS を出さない
- テストを実行せずに「前回と同じ」で省略しない
- FAIL 項目を隠さない
- 検証範囲を勝手に縮小しない

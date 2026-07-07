# レビュー記録
<!-- 正本: reviewer agent -->

## 対象

- 変更内容: iter61 — iter60 事故クラス（検証サブエージェントの tree 破壊）の機械防御。(1) destructive patterns に git checkout <pathspec>/restore/stash 系9エントリ追加、(2) session-start の snapshot 再生成を gate 退行検知つき条件化（復旧アンカー温存）。
- 対象ファイル: hooks/lib/patterns.sh・hooks/lib/snapshot.sh・hooks/session-start.sh・tests/test_check_destructive_coverage.py・tests/test_snapshot_writers.py・tests/test_destructive_warning_language.py（配列長 pin のみ）
- 参照計画: docs/plans/2026-07-07-iter61-incident-class-machine-defense-plan.md（Rev.4）

## Stage 1: 仕様準拠

計画の全要件と diff を照合する。Stage 1 が PASS でなければ Stage 2 に進まない。

- [x] 計画の全要件が実装されている（挙動マトリクス ask 側・allow 側とも実フック起動で全行一致。Rev.2 確定文言 A/B/C は実行行 byte 一致＝grill-code 検証。Rev.3/4 fix-forward 反映済み）
- [x] スコープ外の機能が追加されていない（既存 16 パターン/WARN は無削除・無変更＝弱体化なし・盲検2次確認）
- [x] 実装の欠落がない（snapshot ガードの fail-open 方向・正規 rollover 無誤検知・sed injection 封鎖すべて実装済み）

**Findings:**

- grill-code M-1/M-2（`checkout -f/--force`・`restore --source/--worktree/-W` 素通り）→ Rev.3 fix-forward でパターン追加・封鎖済み
- 盲検2次 M-1（先頭グロブ `git checkout *` 素通り）→ Rev.4 fix-forward で glob prefix optional 化・封鎖済み（ask テスト3形追加）
- 盲検2次 m-3（正規 reset 後の無警告 pin なし）→ Rev.4 でテスト追加済み

**Stage 1 判定:** PASS

## Stage 2: コード品質

Stage 1 PASS の場合のみ実施する。

- [x] 命名が一貫して明確である（`aegis_snapshot_gate_regression` は既存 `aegis_write_snapshot` の命名系に整合）
- [x] コード構造とモジュール分割が適切である（snapshot 形式の知識は snapshot.sh 単一所有を維持・session-start は呼ぶだけ。パターンは patterns.sh 単一ソース＝check-destructive/check-cron-gate の2消費者が自動追随）
- [x] テスト品質（全テストが実フック起動・mutation 10体で全 RED＝tautology なし〔grill-code MU1-10〕・ask 22形/allow 14形＋独自プローブ約30形）
- [x] エラーハンドリングが適切である（ガードは advisory 層 fail-open＝snapshot/STATUS 不在・破損で現行動作へ倒れ session を brick しない。post-status-audit の fail-closed source 経路は 191 passed で無影響確認）

**Findings:**

- なし（Minor バックログ: REGEX↔WARN 順序 pin・敵対 snapshot 行数上限・fd≥10 誤爆 — plan 残余リストに記録済み）

**Stage 2 判定:** PASS

## 残留リスク

- `git checkout <単一bareパス>`（glob/スラッシュ/複数引数/`--`/force なし）はブランチ切替と構文上区別不能＝非対象。iter62 の委譲文言層で被覆予定。
- approved→n/a 方向・逆方向（pending→approved）の revert はガードのスコープ外（earned→pending の後退のみ検知＝復旧アンカー保全という目的に整合）。
- mid-session laundering（Bash revert 後に親が update-gate 実行）は session 境界防御の外＝plan 残余に明記。
- 変数間接・quote 難読化・`-C` 以外のグローバルフラグは SF-004 受容クラス（既存パターン群と同一の限界）。

## 総合判定

- 判定: approved
- 次のアクション: B1 drill（未コミット diff の実 mutation）→ qa → security → 単一コミット → ゲート承認 → ship v1.22.0

## Claims（judge が機械読取する）

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  notes: 盲検2次（独立文脈・read-only 拘束委譲）。Major 1件=先頭グロブ checkout 素通り→Rev.4 fix-forward で封鎖・ask テスト3形で pin。Minor 3件=restore 短形式フラグ連鎖の境界文書化（plan 残余へ追記済み）/approved→n/a 方向の非検知（残余へ追記済み）/正規 reset 無警告の pin テスト（追加済み）。Info: 復旧ループ E2E 実証＝警告文の全主張が実挙動一致・既存 enforcement の後退なし・REGEX/WARN 24/24 index 整合。
```

<!-- exit-check: Stage 1/2 判定・findings 対応済み → qa へ -->

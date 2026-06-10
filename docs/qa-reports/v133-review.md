# v1.3.3 P1 fix-forward — review エビデンス（2026-06-10）

対象: P1-1（check-control-plane の transcript_path 衝突）・P1-2（check-gate のパス glob 衝突）の修正
出典: docs/evolution-review-2026-06-10.md §4
方式: 2段グリル実装段（grill-code）。独立サブエージェントが `git diff` を読み取り専用で精査し、/tmp フィクスチャで新旧 hook を実発火比較。

## レビュー結果（ラウンド1）

判定: **条件付き GO**。指摘と対応:

| ID | 指摘 | 対応 |
|----|------|------|
| P1-A | 非正規形パスで fail-open 回帰（実証）: control-plane で `../hooks/`・絶対パス `$ROOT/hooks/`・`$(pwd)/hooks/` が旧 deny→新 allow に反転。check-gate で `foo/../hooks/`・`././hooks/`・`$ROOT/./hooks/` が同様。レビュアー意見=絶対パス残余リスクは**非許容**（モデルは絶対パスを主経路で使う） | **修正済み**。control-plane: CONTROL_PLANE に dot-dot 再進入・`/./`・`$(...)/`・`$VAR/` の deny-eligible 形を追加＋`$ROOT`/`$ROOT_REAL` 固定文字列照合（`cmd_mentions_control_plane`）。check-gate: 純 bash の `normalize_target`（`./`・`../` の字句解決）＋ルート照合 |
| P2-A | macOS 物理パス不一致（/tmp vs /private/tmp、symlink workdir）で check-gate fail-open（実証） | **修正済み**。両 hook に `ROOT_REAL="$(cd "$ROOT" && pwd -P)"` を導入し論理/物理の両形を照合 |
| P2-B | バイパス形のテスト不在 | **修正済み**。レビュアーの再現形そのものを 12 テスト追加（deny 固定 11 + 他プロジェクト hooks/ allow 1）。修正前に RED 11 件を確認 |
| P3-A | `! printf \| grep -qE` の pipefail+SIGPIPE 理論バグ（64KB 超 CMD） | **見送り（既存・回帰でない）**。旧版にも同型あり。evolution review P3 系と合わせて次バッチで対応 |

## レビューで問題なしと確認された観点

- エラー時挙動: python3 不在・壊れた JSON・空 command の全経路で許可側に倒れない（fail-closed 維持、python3 不在スタブで実証）
- 仕様判断: ネスト `.claude/`・ネスト CLAUDE.md の許可化は妥当（プロジェクト所有物）。control-plane 側の `.claude/` 無境界維持は保守的方向の非対称で問題なし
- 回帰シール: smoke B-4/B-5 は旧 hook で確実に FAIL することを実発火で実証
- ミラー同期: cmp で byte 同一

## 残余リスク（記録）

- check-gate: プロジェクト内 symlink が hooks/ を指す場合は字句正規化で解決不能（ファイルシステム非アクセスの設計上の限界）
- control-plane: スクリプト内で文字列結合により制御プレーンパスを構築する形（例: `"hoo"+"ks/"`）は静的検査の原理的限界（旧版でも不検出）
- check-gate: file_path が論理形・ROOT が物理形という逆方向の不一致は未解決（pwd -P は ROOT 側のみ正規化。Claude Code の file_path は通常絶対・物理で実害シナリオ未確認）

判定: 条件（P1-A/P2-A 修正＋テスト固定）充足。**GO**。

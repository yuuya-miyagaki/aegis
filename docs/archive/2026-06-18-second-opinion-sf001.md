# Second Opinion 依頼: SF-001 control-plane moat の網羅性（iteration 32）

> 3-failure 規律（CLAUDE.md）の発動。盲検レビュー 3 ラウンドで毎回**新規 Critical**（いずれも
> pre-existing）が出て、reactive な形別パッチが収束していない。設計判断を仰ぐ。

## ゴール
`hooks/check-control-plane.sh`（非 framework タスクで Bash コマンドの control-plane 書込みを deny する moat）が、**シェルが control-plane パスに再構成する全ての形**を捕捉するようにする＝SF-001 を潰す。

## これまでの経過（review phase の fix-forward）

| # | クラス | 状態 | 修正 |
|---|---|---|---|
| F-1 | 絶対 root パス bare-dir `rm -rf ${ROOT}/hooks` | **CLOSED** | R1（ec7587e） |
| F-2 | ANSI-C `rm -rf $'hook\x73'` | **CLOSED** | R1（ec7587e） |
| F-3 | パス正規化 `.//hooks`・`/./hooks`・`x/../hooks`・`$PWD/hooks` | **CLOSED** | R2 path-resolution 再設計（e0d21d8） |
| F-4 | **cmdsub 経由 bare-dir** `rm -rf $(pwd)/hooks`・`` `pwd`/hooks ``・`$(echo hooks)/lib` | **OPEN** | 未 |

- 各ラウンド: 1 次 break-attempt（reviewer）が実走で Critical を検出 → fix-forward。F-1/F-2/F-3 は実走で閉鎖確認済み・回帰ゼロ・full suite 872 passed/1 skip・REDTEAM 18/18+5/5。
- F-4 は **pre-existing**（変更前 8f8eb2d でも同一 allow）。`$(pwd)/hooks/`（末尾スラッシュ）は deny だが bare 形が allow。

## systemic な診断
moat は**コマンド文字列を静的に検査**して CP 書込みを判定する。シェルの再構成（クォート/エスケープ/ANSI-C/変数展開/パス正規化/コマンド置換）は面が広い。**静的に解決可能なクラスは path-resolution で網羅的に閉じた**（F-1/F-2/F-3 ＝ quote/backslash/ANSI-C/bare/abs/normalize/$PWD）。残るのは**静的に解決不能**な本質的限界:

- **コマンド置換 `$(...)`/`` `...` ``（F-4）**: 出力はコマンドを実行しないと不明。
  - `$(pwd)`/`` `pwd` `` は**唯一の現実的攻撃**（cwd を得る既知手段）で、`pwd` は副作用ゼロ＝ROOT へ安全に展開でき**閉鎖可能**。
  - `$(echo hooks)/lib` 等の任意 cmdsub は**原理的に解決不能**（`$(echo hooks)` を書ける者は `hooks` を直接書けるが、それは今や捕捉される）。
- **任意の外部変数 `$FOO/hooks`**: 値不明。代入を伴えば既存 `cmd_var_built_write` が ASK。純粋な外部 env 由来は解決不能。
- **glob `rm -rf hooks*`**: `SF-002` として記録済（別クラス）。
- symlink: ROOT_REAL で部分的に対応済。

## 選択肢

- **(A) 解決可能面で収束 ＋ 本質的残余を明示受容（推奨）**: `$(pwd)`/`` `pwd` `` を ROOT 展開して F-4 の現実的ベクタを閉じ、**任意 cmdsub/任意 $VAR/glob は「実行しないと解決できない静的解析の限界」として受容**し SF-002/SF-003 に durable 記録（accepted residual）。併せて**網羅的な敵対テスト行列**（全再構成機構を列挙）を作り、再レビューが「発見」でなく「確認」になるようにする。→ 現実的・収束する。
- **(B) cmdsub の保守的 catch-all**: cmdsub を含むコマンドが CP ディレクトリ名を path 位置に含むなら一律 deny。F-4 を完全に閉じるが、cmdsub を伴う正当な `src/hooks` 参照等を誤 deny（FP 増）＝独自設計＋TDD が要る。
- **(C) 外部レビュー（IDE chat / 人間）**: moat の網羅性と「どこまでで十分か」の基準を独立に確認してから決める。

## 推奨
**(A)**。理由: 解決可能面は既に網羅的に閉じており、残余は形別パッチで潰せる「穴」ではなく**実行を要する原理的限界**。これ以上の reactive パッチは収束しない一方、`$(pwd)` の quick-win で現実的ベクタは消える。本質的残余を**明示的に受容・記録**し、敵対テスト行列で closure を実証するのが筋。完全な動的サンドボックスを moat に求めるのは scope 過大（YAGNI）。

## 次のアクション（ユーザー判断待ち）
- (A)/(B)/(C) のいずれで進めるか。
- (C) を選ぶ場合は IDE chat 等で本ファイル＋`hooks/check-control-plane.sh`＋`docs/specs/2026-06-18-sf-001-cp-token-bypass-design.md` を独立レビュー推奨。
- 現状コードは strict 改善（F-1/F-2/F-3 閉鎖・回帰ゼロ・未 push）＝review gate 未承認のまま保持。

# Security Follow-ups（未消化のセキュリティ課題・durable）

> 後で必ず潰すと決めた未対応のセキュリティ課題を、消えない形で残すトラッカー。
> per-iteration の qa-reports と違い、解決まで root に残す。解決したら「状態」を
> CLOSED にし、対応コミット/ゲートを記す。

## OPEN

### SF-001: control-plane フックのクォート/エスケープ トークン分割バイパス（Critical・pre-existing）

- **発見**: iteration 31 / Batch1 review ゲートの盲検 break-attempt レビュー（reviewer ＋ reviewer-maintainability が独立に検出）。2026-06-16。
- **種別**: **pre-existing**（変更前 8f8eb2d でも同一挙動＝allow を実測確認。Batch1 が導入した後退では**ない**。Batch1 の orig-vs-new 比較は control-plane 書込みで後退ゼロ）。
- **重大度**: Critical（フル moat 崩壊。非 framework タスクのエージェントが control-plane ファイルへ任意内容を書ける）。
- **再現（task_type=feature の install で `{}`=allow になる。非分割形は全て deny）**:
  ```
  cp safe.txt hooks""/lib/emit.sh            # 空クォートで hooks を分割
  cp safe.txt "ho""oks/lib/emit.sh"          # 隣接クォート連結
  cp safe.txt 'hoo'ks/lib/emit.sh            # シングルクォート
  cp safe.txt hooks"/"lib/emit.sh            # スラッシュを分割
  cp safe.txt hooks\/lib/emit.sh             # バックスラッシュ エスケープ
  echo evil > "hoo""ks/lib/emit.sh"          # リダイレクト形（チェック b も回避）
  cp evil "STAT"US.md                        # STATUS.md / CLAUDE.md / .claude/ も同様
  echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh
  find . -name x -exec cp {} "hoo"ks/lib/emit.sh \;
  # 同クラス（trailing-slash 無しの bare ディレクトリ operand。CP 正規表現は `hooks/` を要求するため bare `hooks` を取りこぼす）:
  find hooks -type f -exec rm {} +            # hooks/ 配下を削除（find hooks/ は deny）
  rm -rf hooks                                # rm -rf hooks/ は deny
  cp evil hooks                              # ディレクトリ hooks へコピー
  ```
- **根本原因**: `hooks/check-control-plane.sh` の判定（正規表現＋`mask_quoted` のクォート span マスク）は、シェルの**クォート除去＋隣接トークン連結＋パス解決**（word splitting）を再現していない。判定は**リテラル `hooks/`|`scripts/`|… 部分文字列**に一致するだけなので、シェルが control-plane パスに解決するが当該リテラルを含まない全ての形を取りこぼす: クォート分割（`hooks""/`）・バックスラッシュ（`hooks\/`）・**trailing-slash 無しの bare operand（`find hooks`/`rm -rf hooks`/`cp x hooks`）**。`hooks""/lib` はシェルでは語 `hooks/lib` だが生にもマスク後にもリテラル `hooks/` が無く一致しない。
- **iteration 31 security ゲートでの確認**: 1 次（security エージェント）＋盲検 2 次が独立に、上記全形を orig(8f8eb2d) vs new HEAD で実走し **両者とも allow＝完全に pre-existing**（Batch1 後退ゼロ）と確認。security skill の deploy blocker 列挙（auth bypass/default creds/hardcoded secret/HTTPS）には非該当のため **deploy blocker ではなく Critical 残存リスク**として繰延承認。
- **なぜ安易に直せないか**: 「クォート除去＋連結」を素朴に適用すると、`git commit -m "update STATUS.md handling"` のような**クォート内メッセージ救済（OBS-006）を再び壊す**（語の値に `STATUS.md` 部分文字列が現れる）。正しくは「シェル忠実なトークン化 → 各語をクォート除去して**語の値**を得る → その語が**書込み先**の control-plane パスか判定」。重い新プリミティブで、セキュリティ境界ゆえ独立した設計＋TDD＋盲検レビューが必要。
- **修正方針（暫定・非確定）**: コマンドを語単位にトークン化（python の `shlex` 等＝抽出と同様に python 優先＋bash fail-closed フォールバック）し、各語の literal value を再構成してから control-plane 判定。リダイレクト先・write コマンドの宛先語に限定して deny。`git commit -m`/`echo`/`printf` のメッセージ語は「語全体がパスでない」ため救済を維持。
- **状態**: **OPEN**（iteration 32 で対応中）。iteration 31 では Batch1（後退ゼロ）を先行し、本件は最優先の専用タスクとして後続で消化する（ユーザー合意 2026-06-16）。修正計画＝`docs/plans/2026-06-18-sf-001-cp-token-bypass-implementation-plan.md`、設計＝`docs/specs/2026-06-18-sf-001-cp-token-bypass-design.md`。

### SF-002: control-plane フックの glob メタ文字 bare-dir バイパス（High・pre-existing）

- **発見**: iteration 32 / SF-001 修正計画の grill-plan（自己グリル）。2026-06-18。
- **種別**: **pre-existing**（SF-001 と同じく既存 moat も素通り。SF-001 修正でも**意図的にスコープ外**）。
- **重大度**: High（bare-dir 破壊と同等の効果。`rm -rf hooks*` で hooks/ を削除可能）。
- **再現（task_type=feature で allow になる）**:
  ```
  rm -rf hooks*        # 末尾 glob。語が厳密 `hooks` でも `hooks/` でもない
  rm -rf hook?         # ? glob
  rm -rf [h]ooks       # 文字クラス glob
  cp evil scripts*     # 同クラス
  ```
- **根本原因**: control-plane 判定（SF-001 の token-aware augment 後も）は語の literal value で CP を判定する。glob メタ文字（`* ? [`）を含む語はシェルが実行時にファイル名展開して CP パスに解決するが、判定時点の語は `hooks*` 等で、`CONTROL_PLANE` 正規表現にも bare-name 厳密一致にも当たらない。shlex も glob を展開しない。
- **修正方針（暫定・非確定）**: bare-name 検出の右境界に glob メタ文字（`*?[`）を許容するか、glob を含む CP 接頭辞語を fail-closed 扱いにする。SF-001 と同じくセキュリティ境界ゆえ独立 TDD＋盲検が要る。
- **状態**: **OPEN**。SF-001（列挙3クラス）を先行し、本件は別タスクで消化（スコープを膨らませない）。

## CLOSED

（なし）

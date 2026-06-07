# F6 修正計画: setup.sh が hook lib を install せず moat 全死

> 監査: `docs/functional-integrity-audit-report-2026-06-07.md` Finding 6（P1）
> 種別: bugfix（framework）/ 設計判断なし → brainstorm 不要・TDD 必須

## 問題（実証済）

`bin/setup.sh` の `copy_hooks()`（L191-209）は `hooks/lib/extract-input.sh` **だけ**を明示コピーする。
2026-06-05 Foundation 改修で新設された `hooks/lib/emit.sh`（全16 hook が source する単一出力源）と
`hooks/lib/patterns.sh`（check-destructive が source）を**コピーしない**。

結果、hooks を含む全 profile（minimal=session-start のみ／standard／full）で install すると、各 hook が
`source .../lib/emit.sh` の行で `No such file or directory` → `set -euo pipefail` で **exit 1**。
PreToolUse の exit 1 は非ブロッキング扱い＝**決定論 PaC enforcement（moat）が silent に fail-open**。

なぜ既存検査が見逃したか: `eval_scaffold_smoke.py`（tier2）は setup.sh を実走するが、検証は
`check_framework_contract`（ファイル存在）のみで **hook を一度も実行しない**。emit.sh はどの profile の
`required` にも無いので不在でも PASS。→ install 経路が「走るか」を無検査。

## 修正方針（2点・1コミット）

### (A) 本体修正: `copy_hooks` を hooks/lib/*.sh 全コピーに
- L204 の「extract-input.sh だけ」を、`hooks/lib/` 配下の `*.sh` を**全て**コピーする形に置換。
- 理由: emit.sh は全 hook が必要・patterns.sh も将来 hook が source しうる小さな共有ヘルパ。
  「installする hookが source する lib を解析して選別コピー」より、**全 lib コピー**が単純・堅牢・future-proof。
- 既存の「`hooks_include` が空なら何もしない」ガードは維持（hook を入れない profile に lib を撒かない）。

### (B) 回帰防止（構造対策・恒久）: scaffold smoke に hook 実行検証を追加
`eval_scaffold_smoke.py` に `verify_hooks_runnable(target, profile) -> (ok, detail)` を新設し、
**contract PASS 後**に呼ぶ（結線を明示）。失敗時 `run_scaffold_test` が `("FAIL", detail)` を返す。

- **B-1** standard scaffold: `check-gate.sh` を docs パス入力で発火 → **exit code 0 かつ stdout == `{}`**
  （emit_allow の固定出力＝emit.sh を実行で証明）。check-gate は allowlist `*/docs/*` で早期 allow するため
  STATUS の中身に依存せず、非 git temp でも走る。
- **B-2** full scaffold（別 temp）: `check-destructive.sh` を `rm -rf /` で発火 →
  **stdout の permissionDecision == `ask`**（patterns.sh も実行で証明。かつ「framework repo としてしか
  検証されていなかった full」を scaffold として初検証。コメントの "full は tier1" 制約は contract 検証の
  話で hook 発火には掛からない）。check-destructive は `git rev-parse ... || pwd` で非 git でも走る。
- **B-3**（補助）hooks を含む profile で `hooks/lib/emit.sh` と `hooks/lib/patterns.sh` の存在を assert。
- **判定方針**: exit code ＋ stdout 固定値で判定する。**stderr の `No such file` 文字列一致には依存しない**
  （OS/ロケール依存で脆いため）。
- minimal も `session-start.sh`（emit.sh を source）を1つ install する＝F6 影響下。この事実を test コメントに
  残し、未来の改変が minimal を「hook 無し」と誤解しないようにする。

これにより「install 先で hook が走る」を契約化。F6 の再発を恒久的に塞ぐ。

### copy 実装の注意
- `for f in hooks/lib/*.sh` のマッチ0件リテラル掴みは、既存 `copy_file` の「source 不在は SKIP」で無害化
  されるが、ガードに依存する旨をコメントに残す。
- **なぜ選別コピーでなく全コピーか**: emit.sh は全 hook が source、patterns.sh も将来 hook が source しうる
  小さな共有ヘルパ。「installする hook が source する lib を解析して選別」は複雑で壊れやすい。全コピーが
  単純・堅牢・future-proof。3年後にこれを「選別最適化」して再び壊さないための判断根拠として明記。

## TDD 手順

1. **RED**: (B) の smoke 強化を先に書く（emit.sh 存在 assert ＋ check-gate 発火）。現状の setup.sh では
   emit.sh 不在で **FAIL** することを確認（`run_eval.py --tier 2` が赤）。
2. **GREEN**: (A) の copy_hooks 修正を入れ、tier2 が緑に戻ることを確認。
3. 既存 296 tests・tier0/1・contract(full/standard)・drift・--strict が緑のままを確認。

## 影響範囲・非影響

- 変更: `bin/setup.sh`（copy_hooks）, `scripts/eval_scaffold_smoke.py`（smoke 強化）。
- **ミラー不要**: setup.sh と eval_scaffold_smoke は MIRROR_DIRS/FILES 対象外（example に複製されない）。
- **version**: 本 fix 単独では bump しない。F3-F5 と合わせ fix フェーズ末に patch（1.3.1→1.3.2）で版締め。
- example/minimal-project は元から lib 完備のため無変更。
- **aegis 自身の STATUS/ゲート方針**: 本監査の fix フェーズは複数 finding を連続修正するため、aegis 自身の
  STATUS.md 更新（phase/gates）は **fix フェーズ末の版締めでまとめて実施**し、個別 fix では aegis の gate
  machine を回さない。各 fix は bugfix 相当で、内部2段グリル（grill-plan→grill-code）が review 代替。
  この方針宣言自体が「黙って触らない」ための自己整合の担保。

## 完了条件

- tier2 が「scaffold→hook 発火」で緑。RED→GREEN を実ログで提示。
- `setup.sh --profile=full --target=<tmp>` 実 install で任意 hook が emit を返す（手動再確認）。
- Layer 0 全 green 維持。grill-code 通過。

## スコープ外（次の fix で）

- F3（resolve_source に retro.md→example 変種マップ）= 同じ setup.sh だが別 finding。本 fix を緑にした後、
  同じ smoke 基盤で `/retro` graceful を assert して着手。

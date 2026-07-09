# レビュー記録
<!-- 正本: reviewer agent -->

## 対象

- 変更内容: iter64 — fingerprint tree-hash 化（全体レビュー §2 R6 根1・§4 Phase 1「1-1」）＋ setup.sh OR marker 厳格化（iter63 LOW-1）。v1.24.0→v1.25.0 予定。
  1. `hooks/lib/fingerprint.sh`: ハッシュ入力の `head:<HEAD-sha>` 行を「非 docs/.claude の committed tree-hash」`tree:<sha>`（`git ls-tree -r HEAD` を docs/・.claude/ 除外→sha256）に置換。docs-only コミットで fp が無効化する罠 r を根絶しつつ、コード変更コミットは blob sha 経由で fp が動く＝silent-green 防止を完全保存。
  2. `bin/setup.sh`: `selfheal_unlock_target` の身元判定を `.aegis-install-version` OR `hooks/lib/cp-lock.sh` から **stamp 単独要求**へ厳格化（LOW-1）。
- 対象ファイル: hooks/lib/fingerprint.sh（+26/-10）・bin/setup.sh（+10/-4）・tests/test_fingerprint_lib.py（新規2＋docstring）・tests/test_setup_locked_target_upgrade.py（新規1）・docs/STATUS.md（フェーズ簿記）
- 参照: docs/specs/2026-07-08-iter64-fingerprint-tree-hash-design.md／docs/plans/2026-07-08-iter64-fingerprint-tree-hash-plan.md（grill-plan 致命1〔escaping〕＋要検討 反映済）／scripts/build-judge-card.py・hooks/lib/evidence.sh（consumer・無改変）
- レビュー方式: 1次（reviewer・9項目 numbered batch・実 git 挙動検証）＋テスト強度（reviewer-testing・mutant 実証）＋盲検2次（reviewer-maintainability・1次 verdict 非共有・独立）。全委譲に routing.md「Verification delegation」6拘束（read-only・tree 変更禁止）付与。
- レビュー開始時点の未コミット作業（前提として容認・不変で維持）:
  `M bin/setup.sh` / `M docs/STATUS.md` / `M hooks/lib/fingerprint.sh` / `M tests/test_fingerprint_lib.py` / `?? tests/test_setup_locked_target_upgrade.py`（既存）/ `?? docs/specs/…design.md` / `?? docs/plans/…plan.md`

## 対照表（plan タスク → 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1a | fingerprint RED テスト×2（docs-only 不感・aclaude 誤除外回帰） | tests/test_fingerprint_lib.py | 完了 | RED 実証（docs_only は旧 head:sha で FAIL）。resembling は新実装の escaping 退行ガード（mutant flip で歯を実証） |
| 1b | fingerprint.sh tree-hash 化（head:→tree:・char-class 除外） | hooks/lib/fingerprint.sh | 完了 | プロトタイプで既存15 PASS 実証済／char-class `[.]claude/` で誤除外封鎖 |
| 2a | setup RED テスト×1（stamp 無し→self-heal 不発） | tests/test_setup_locked_target_upgrade.py | 完了 | RED 実証（旧 OR ゲートで rc0＋OS-locked） |
| 2b | setup.sh OR marker→stamp 単独 | bin/setup.sh L642-647・コメント L628-634 | 完了 | 既存5テスト維持 |
| 3 | 対象スイート→full | — | 完了 | fingerprint 17・setup 6・**full 1079 passed/2 skipped**（本セッション実走） |
| ship | bump 3箇所（v1.25.0 MINOR） | — | 未（正） | ship フェーズ担当。FRAMEWORK_VERSION=1.24.0 のまま＝diff 非混入 |

## レビュー運用メモ（ハーネス事象）

本セッションの委譲サブエージェントは harness の Plan Mode 境界に阻まれ Bash 実行が制限された（reviewer-testing は明示的に「items 2/3 は自分の実証でない」と誠実に留保、reviewer 1次は最終 verdict が turn/budget 途中で切断）。iter63 前例（検証委譲がインフラ故障で詰まったら 1次を in-session 引き取り）に倣い、**mutant/coverage/挙動の実証はコーディネータが in-session で網羅**（tool-call evidence は本セッション transcript に記録）。盲検2次（reviewer-maintainability）は独立静的読解＋一部実 repo 検証で clean な verdict を返した。

## 検証項目別エビデンス

### 1次（in-session・reviewer 委譲は date-ordering を裏付け）
1. **spec 準拠** — action: diff と設計書突合。expected: head:→tree: 置換・ref は HEAD/empty-tree 維持。observed: 逐語一致。verdict: PASS
2. **silent-green 不変条件（E1 moat 核）** — action: プロトタイプで既存15テスト実走＋mutant 注入（scratch コピー）。expected: code コミットで fp 変化・意図せぬ除外なし。observed: 既存15 PASS／`tree:` 定数化 mutant で `test_new_commit_changes_fp_even_when_tree_clean`＋`resembling` が RED／bare-dot mutant で `resembling` RED。verdict: PASS
3. **罠 r 修正** — action: 一時 repo で docs-only コミット前後の fp 比較。expected: 不変。observed: 一致（145795…＝docs-only／code コミットで相違）。verdict: PASS
4. **token 契約不変** — action: 実 repo で `bash hooks/lib/fingerprint.sh .`。observed: 64-hex・rc0（`set -euo pipefail` 下でも）。verdict: PASS
5. **consumer 透過** — action: `grep -rn "head:" scripts/ hooks/ tests/`。observed: `head:` は fingerprint.sh のみ（変更前）。build-judge-card.py/evidence.sh は 64-hex 不透明比較のみ・fp 値ハードコードは全 suite ゼロ。移行は既存 record→unverified の fail-closed。verdict: PASS
6. **除外パターン** — action: escape_check 実演＋mutant。observed: char-class `[.]claude/` は `.claude/` のみ除外・`aclaude/`/`xdocs/` 保持。bare-dot mutant は `aclaude/` 誤除外＝`resembling` RED。root 直下 `docs` ファイルは末尾スラッシュ要件で非除外（新テスト `test_root_file_named_docs_is_not_excluded`＋slash-drop mutant で RED 実証）。verdict: PASS
7. **bash 安全性** — action: `bash -c 'set -euo pipefail; source …; fingerprint_worktree .'`＋`bash -n`。observed: rc0・64-hex・構文 OK。`committed` は常に代入・grep 空マッチ rc1 は `|| true` 受け。verdict: PASS
8. **OR marker** — action: git 履歴で stamp/cp-lock 導入日確認＋setup 6テスト実走。observed: stamp `66e59e8`(2026-06-13)＜cp-lock `1e46e4d`(2026-06-21)＝lockable install は必ず stamp 保有。既存5＋新1 PASS。旧 OR ゲートで新テスト RED（tautology でない）。verdict: PASS
9. **性能** — action: 実 repo 10x タイミング。observed: 96ms→121ms/回（+25ms・ls-tree 459 files メタデータのみ）。fingerprint は evidence.sh:241 の hot-path 最適化で常時計算されない。verdict: PASS（許容トレードオフ）

### テスト強度（reviewer-testing）
- item 1（自己 tool-call 実証）: `pytest tests/test_fingerprint_lib.py tests/test_setup_locked_target_upgrade.py -q` → **23 passed**・無回帰。verdict: PASS
- items 2/3（coordinator in-session 実証）: mutant 2(a/b/c) 全 RED・coverage 空白（committed=""非alias・root `docs`ファイル包含・ls-tree 失敗→error）全て安全。static 所見は全て Minor/confidence 6＝実証で「未テストの安全分岐」と確定（うち root-`docs` は新テストで pin）。

### 盲検2次（reviewer-maintainability・独立・approve_with_notes）
- 1: head:→tree: は silent-green を新設しない（committed 成分が code コミットで動く／docs-only で不変）と読解＋一時 repo で実証（docs-only 前後 fp 一致・code 変更で相違）。
- 2: char-class `[.]` は妥当（`aclaude/` 誤除外の罠を回避・実証済）。
- 3: stamp 単独ガードの日付論拠は妥当（cp-lock は stamp の subset）。
- 4: 命名・コメント一貫・スコープ超過なし・fp 契約不変・consumer 無改修。root `docs`ファイル境界も確認済（正しく非除外）。
- divergence: (Minor c6) 除外の非対称〔docs 素文字列 vs .claude の`[.]`〕にコメント一言 → **fix-forward で反映済**（「docs/ は正規表現メタ文字なし」を明記）。(Minor c5) 移行のオペレータ告知が diff 外 → ship note で対応（下記）。

## Stage 1: 仕様準拠
- [x] 計画の全タスクが実装（1a/1b/2a/2b/3。ship の bump は ship 担当で正しく未着手＝FRAMEWORK_VERSION=1.24.0 のまま diff 非混入）
- [x] スコープ外の追加なし（fp トークン契約・rc=0 不変、consumer 無改修、テストは焦点限定）
- [x] 実装欠落なし（silent-green 不変条件を mutant で機械 pin＝docs-only 不感／code 変化／誤除外封鎖）

**Stage 1 判定: PASS**

## Stage 2: コード品質
- [x] `set -euo pipefail`/bash 3.2 安全（`|| true` 受け・宣言/代入分離・全経路 rc0・実走確認）
- [x] エラーハンドリング（ls-tree/diff 失敗→error fail-closed・空 listing を clean-tree hash に alias しない）
- [x] 可読性（char-class の罠を実例付きコメントで明示・除外の非対称も fix-forward で説明追加）
- [x] テスト強度（新規3本＝docs-only 不感／aclaude 誤除外回帰／root-docs ファイル／without-stamp、全て mutant flip で歯を実証）

**Stage 2 判定: PASS**

## 判定

**approve_with_notes**（Critical/Major 0・Minor 2〔両方 fix-forward or ship で対応〕）。fix-forward 反映済: (1) 除外非対称コメント補足、(2) root-`docs`ファイル回帰テスト追加。ship 対応: 移行のオペレータ告知を TO-CLIENT/ship note に明記。full suite 再実走は qa フェーズ（B1 drill 後 record）。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "除外パターンの非対称（docs/=素文字列, .claude/=char-class [.]）にコメント補足推奨（Minor c6）→ fix-forward 反映済"
    - "fp 移行のオペレータ告知が diff 外・ship note で要確認（Minor c5・ship スコープ）"
```

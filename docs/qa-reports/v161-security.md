# v1.6.1 security エビデンス（2026-06-13）

## 位置づけ

第5回全力レビュー（`docs/full-review-2026-06-12.md`）で **PoC 実証された Critical 7 件 + Should fix 2 件** を fix-forward した v1.6.1 patch リリースの security エビデンス。決定論 moat の中核（emit.sh 上書き経路・テスト緑色偽装・client gate 内容無検査・SessionStart resume 欠落・`.env` 多重バリアント・arch-overview 公開契約の嘘）を対象とする。grill-code 独立 2 本（A 攻撃面・B 仕様乖離・保守性）の指摘もすべて反映。

## 修正サマリ（commit 順）

| # | 修正 | 出典 | 防御強度の方向 |
|---|------|------|---------------|
| 1 | `hooks/lib/secrets-patterns.sh` 新設 | C-9 Task 0 | 単一所有化（4 形式重複の解消） |
| 2 | `check-secrets.sh` を lib 経由化 | C-9 Task 6 | リテラル列挙除去 |
| 3 | `git --git-dir=` / `-C` / `stage` / `update-index` を deny | S-3 Task 7 | 攻撃面拡張 |
| 4 | control-plane 変数展開バイパス封鎖（9 PoC） | C-1 Task 1 | fail-closed（ask に倒す） |
| 5 | SessionStart matcher に `resume` 追加 | C-4 Task 4 | silent fail 解消 |
| 6 | `phase-skills.sh` + `secrets-patterns.sh` を REQUIRED 登録 | S-11 Task 8 | F6 同型死角の封鎖 |
| 7 | arch-overview drift 訂正＋契約テスト | C-5/C-6 Task 5 | 公開契約の正確性 |
| 8 | test-marker 必須化（marker_verified スキーマ） | C-2 Task 2 | 偽装封鎖（schema migration） |
| 9 | client_ready_for_dev に sentinel+200B 検査 | C-3 Task 3 | touch バイパス封鎖（双方向） |
| 10 | 3 段 marker peephole（強い単独/弱いペア/no-run flag） | grill-code A-Crit-2 / B-Critical | C-2 強化（OK/test result 単独 forge 封鎖） |
| 11 | WRITE_OP 拡張（ln/curl/wget/rsync/chmod 等） | grill-code A-Crit-1 | C-1 強化（漏れた書込み utility） |
| 12 | git add var-built filename 検出＋git commit GIT_PRE_OPTS | grill-code A-Crit-4 / A-S4 | S-3 強化＋commit 経路統一 |

## PoC 9 件の再走（v1.6.1 適用後）

すべて `/tmp/aegis-verify` の scaffold install で実走確認。

| PoC | 期待 | v1.6.0 実測 | v1.6.1 実測 |
|-----|------|-------------|-------------|
| `D=ho; D=${D}oks; echo evil > $D/lib/emit.sh` | deny/ask | **{} allow（破れた）** | ✅ ask |
| `echo evil > "${HOOKS_DIR:-hooks}/lib/emit.sh"` | deny | **{} allow** | ✅ deny |
| `D=h; D=${D}ooks; ln -sf /tmp/x $D/lib/emit.sh` | ask | **{} allow** | ✅ ask（A-Crit-1 修正後） |
| `D=h; D=${D}ooks; chmod 000 $D/lib/emit.sh` | ask | **{} allow** | ✅ ask |
| `pytest --version` → judge card | unverified | **テスト: green** | ✅ unverified |
| `pytest --version && echo OK` → judge card | unverified | **green** | ✅ unverified（A-Crit-2 修正後） |
| `touch docs/{requirements,handover,translation}/*` → gate approve | deny | **approve（破れた）** | ✅ deny |
| `git --git-dir=.git --work-tree=. add .env` | deny | **{} allow** | ✅ deny |
| `F=.env; git add $F` | ask | **{} allow** | ✅ ask（A-Crit-4 修正後） |
| `git -C /tmp commit -m wip`（staged .env） | deny | **{} allow** | ✅ deny（A-S4 修正後） |

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| C-1 var-built write 検知 + parameter expansion default | fail-closed（ask + deny） | リテラル match なしの変数構築でも intercept。ask で誤検知を user 承認で逃がす設計 ✅ |
| C-2 marker_verified スキーマ + 3 段ゲート | fail-closed（schema migration） | v1.6.0 entry を強制 unverified、no-run flag + 強弱 marker peephole で `pytest --version && echo OK` クラスの forge を封鎖 ✅ |
| C-3 sentinel + 200B 双方向検査 | fail-closed | gate approve 時と完了時の bilateral pin。template に sentinel 埋込、ユーザがコピペで通常運用しても壊れない ✅ |
| C-4 SessionStart resume | silent fail 解消 | `--resume` 復帰でも STATUS.md 注入と evidence ローテが必ず発火 ✅ |
| C-5/C-6 arch-overview drift 訂正＋数値契約テスト | doc 正確性 | 数値の手書き drift を CI で必ず気づける。v1.7 で auto-generate に移行予定 |
| C-9 secrets-patterns.sh 単一所有化 | 保守性＋単一所有 | 新規 credential 種別追加が 1 ファイルで済む。F6 同型 fail-open のリスクを REQUIRED 登録で封鎖 ✅ |
| S-3 git バリアント 4 + var-built + commit GIT_PRE_OPTS | 攻撃面拡張 | `--git-dir=` / `-C` / `-c key=val` / `stage` / `update-index` + 変数構築 + commit verb 全て統一 prefix で網羅 ✅ |
| S-11 lib REQUIRED 登録 | F6 同型死角の封鎖 | 新規 lib 追加時のテストで必ず登録漏れに気づける ✅ |

## 受容済みリスク（v1.6.1 時点の意図的トレードオフ）

1. **`git stash push .env`**: 誤検知頻発（個人開発で .env を一時退避する正当用途）のため deny しない。stash 経由の意図的漏洩は v1.6.2 以降で限定 deny を検討
2. **`eval`／`alias`／`cat .env > config` 経由の漏洩**: 構造的に regex では塞げない（v1.5.2 受容済みと同じ系統）
3. **Task 1 cmd_var_built_write の誤検知**: `OUT=/tmp/x; echo y > $OUT` クラスの正当用途で ask が出る。ask は user 承認で逃がせる＝productivity への影響は許容範囲
4. **Task 2 marker regex の false-negative（マイナーランナー）**: meson test / ctest / phpunit / rspec 等は marker 集合外なので `unverified` 化。`record-test-result.py`（信頼ランナー）経由を案内
5. **Task 5 の数値契約テスト brittleness**: 自然文中の数値を grep するためコメント追加で偽陽性可能性。v1.7 で `<!-- count:* -->` sentinel 方式または auto-generation に移行する宣言
6. **grill-code B-S1 残：`AEGIS_HIGH_RISK_CASE_GLOB` 文字列形と `..._ARR` 配列形の 2 重定義**: 配列形が単一 consumer、文字列形は documentation 用途。v1.6.2 で文字列形削除を検討
7. **grill-code A-S1 残：`cmd_var_built_write` の false-positive**: 「var-built TARGET が CP 接頭辞断片を含む場合のみ ask」への絞り込みは v1.7（refactor）
8. **grill-code A-S2 残：sentinel 位置が無拘束**: 「末尾 N 行内」の追加 invariant は v1.6.2 検討
9. **grill-code A-S3 残：`SECOND_OPINION_GATES` に qa 不在**: 単一所有設計の余地は v1.7 で扱う

すべて fail-open ではなく fail-safer（unverified／ask）方向。green 偽装や deny 緩和には繋がらない。

## 残余リスク

新規の fail-open 方向の残余なし。本バッチは追加・強化のみで deny/block 系の緩和ゼロ。

## 検証

- **既存 + 新規テスト 592 + 件 PASS**（既存 508 → 新規 84 件追加）
- contract 本体 + example PASS
- drift 12 チェック PASS
- scaffold smoke 3 プロファイル PASS（minimal / standard / full）
- `check_status --strict` PASS
- grill-code 独立 2 本（A: 攻撃面 / B: 仕様乖離・保守性）の Critical 4 件すべて修正・残 Should fix は明示的に受容

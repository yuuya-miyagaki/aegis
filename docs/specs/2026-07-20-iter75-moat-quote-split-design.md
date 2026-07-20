# 設計ノート — iter75 SF-017 MOAT-BYPASS 修正（moat quote-split 一般化）

## 入力
- 修正対象の欠陥＝SF-017（Critical・OPEN）: `check-destructive.sh`（rm 等の ASK）／`check-secrets.sh`（`.env` 等の DENY）が空クォート トークン分割で回避。`g""it a""dd .e""nv` は bash で `git add .env` だが DENY→ALLOW（親再現済み・HEAD 77566ed）。
- 正本: `docs/full-review-2026-07-19-dual-codex-fable.md` §4.1・`docs/security-followups.md` SF-017。

## 問題整理
- 両フックは抽出済み CMD を**生文字列のまま** grep する。bash のクォート除去＋隣接連結を再現しないため、`r""m`/`r\m`/`"rm"` や `.e""nv` を取りこぼす。
- SF-001（iter32-35）は同クラスを control-plane 側で閉じたが、その防御は destructive/secrets に**未伝播**。
- フレームワークはフル tokenizer を意図的に退役させ、`_obfuscated_unlock_on_cp`（strip-and-grep 正規化＋難読化 ASK）を採用済み。iter75 はこれに一貫させる。

## 推奨アプローチ
純 bash の「クォート/バックスラッシュ除去による正規化形」を共有 helper 化し、両フックが生形＋正規化形の両方で既存検出を実行。正規化形でのみ一致（＝難読化実在）なら ASK。CP コードは不変。

## コンポーネント分解
1. **`hooks/lib/patterns.sh`（helper 追加）**
   ```sh
   # クォート/バックスラッシュ/${IFS} を除去・畳み込んだ正規化形を返す
   # （純 bash・parser なし）。_obfuscated_unlock_on_cp と同一手法の拡張。
   # C locale 前提（呼び出し側が export 済み）。
   # スコープ: 安価に文字列畳み込みできる難読化のみ（下記スコープ参照）。
   aegis_dequote_normalize() {
     local c=$1
     c=${c//\\/}              # backslash 除去
     c=${c//\"/}              # 二重クォート除去
     c=${c//\'/}              # 単一クォート除去
     c=${c//'${IFS}'/ }       # ${IFS} → 空白（トークン分割の同一クラス）
     c=${c//'$IFS'/ }         # $IFS  → 空白
     printf '%s' "$c"
   }
   ```
   > **grill-plan で実証（2026-07-20）**: クォート/バックスラッシュのみだと `git${IFS}add .env`
   > が正規化後も ALLOW＝Critical secret-staging が残る。よって `${IFS}`/`$IFS` を必須で畳む。
2. **`hooks/check-destructive.sh`（消費）**: 既存の生 CMD 判定は不変。生で不一致のとき `NORM=$(aegis_dequote_normalize "$CMD")` を計算し、`[ "$NORM" != "$CMD" ]`（難読化実在）かつ NORM が破壊パターン（`AEGIS_DESTRUCTIVE_CMD_REGEX`／`_LOWER_REGEX`）に一致 → `emit_ask`。
3. **`hooks/check-secrets.sh`（消費）**: 既存の生 CMD 判定は不変。生で不一致のとき正規化形（＋既存と同じ小文字畳み込み `RAW_LC` 相当）に既存 secret 検出（`.env`＋git-add 系文脈・`.env.example` 除外）を適用し、難読化実在かつ一致 → `emit_ask`（DENY でなく）。

## スコープ（grill-plan 反映・2026-07-20）
- **閉じる（iter75）**: 安価に文字列畳み込みできる難読化＝クォート（`"`/`'`）・バックスラッシュ・`${IFS}`・`$IFS`。実証済みの `r""m`/`g""it a""dd .e""nv`/`git${IFS}add .env`/`rm${IFS}-rf` を捕捉。
- **閉じない（新規 SF-019 起票・iter75 残余）**: brace 展開 `{r,x}m`/`r{,}m`・param-default `${x:-rm}`・expansion-split `h${X:-ooks}`・cmdsub `$(...)`/backtick。理由: これらは静的文字列畳み込みでは解決できず、SF-001 が control-plane で採った専用リゾルバ（フレームワークが destructive/secrets には未伝播）か、ロードマップ iter77 の**構造化 argv（実行イベント/argv 判定）**でしか原理的に塞げない。**実証**: `r{,}m -rf`/`g{,}it add .env` は現状 ALLOW（grill_verify）で、クォート/BS/${IFS} 畳み込みでは非到達。SF-019 に severity・到達性・修正方向を記録。
- 判断根拠: レビュー正本の結論「raw shell text を真実の代理にするな＝構造化 argv へ」。iter75 は安価な層で Critical の主要綴りを閉じ、残余の原理的天井を**実証つきで**次段（構造化 argv）に送る。

## インターフェース定義
- `aegis_dequote_normalize <cmd>` → stdout に正規化文字列。副作用なし・冪等でない（1回適用）。
- 呼び出し規約: 生形判定を先に通し（従来評決を保存）、miss した場合のみ正規化パスへ。`NORM == CMD`（畳み込む難読化が無い）ならスキップ（＝従来と完全一致）。
- **check-secrets の staging 検出は単一ソース化**: 高リスク cred／`.env` staging の regex を変数（`_STAGE_HIGHRISK_RE`/`_STAGE_ENV_RE`）に一度だけ定義し、既存 raw チェック（deny・従来メッセージ）と正規化チェック（ask）の**両方が同じ変数を参照**（grill 致命2＝regex 再掲 drift の回避）。

## データフロー
```
INPUT(JSON) → extract_command → CMD
  ├ 生 CMD で既存検出 → 一致: 従来評決（destructive ASK / secrets DENY）★不変
  └ 不一致 → NORM=normalize(CMD)
        └ NORM != CMD かつ NORM が一致 → ASK（新規・silent→visible）
        └ それ以外 → emit_allow（従来）
```

## 判定表
| 入力 | 生一致 | 正規化のみ一致 | 評決 |
|---|---|---|---|
| `rm -rf /x` | ○ | — | ASK（従来） |
| `git add .env` | ○ | — | DENY（従来） |
| `r""m -rf /x` / `r\m -rf` / `"rm" -rf` | × | ○ | **ASK**（新規） |
| `g""it a""dd .e""nv` | × | ○ | **ASK**（新規） |
| `rm -rf "$DIR"` | ○ | — | ASK（生経路・不変） |
| `git commit -m "git add .env"` | × | ○ | ASK（誤検知・非ブロック・許容） |
| `g""it a""dd .e""nv.example` | × | ×（安全形除外） | ALLOW |

## 依存関係
- `patterns.sh` は両フックが既に source 済み。`LC_ALL=C` は両フックが冒頭で export 済み＝正規化は byte-wise。
- CP（`check-runtime-state.sh`）・SF-001 資産には非依存・非改修。

## エラーハンドリング
- 正規化は純 bash param 展開＝失敗経路なし（fail-open を増やさない）。
- 抽出失敗（CMD 空）時は既存のフォールバック（fail-closed）を維持。正規化パスは CMD 非空時のみ。

## テスト戦略（TDD）
- **RED（現状 ALLOW を実証してから）**: `r""m -rf`・`r\m -rf`・`"rm" -rf`・`g""it a""dd .e""nv`・`.e""nv` 変種 → ASK を assert。
- **回帰 pin**: 平文 `rm -rf`=ASK／`git add .env`=DENY 不変、`rm -rf "$X"` は生経路、`.env.example` 難読化は ALLOW、正常クォート（`cp "my file" dest`・`git commit -m "fix STATUS.md"`）を誤 ASK/DENY しない。
- **単体**: `aegis_dequote_normalize` の入出力（`NORM==CMD` の非難読化スキップ含む）。
- 既存 `tests/test_check_destructive_coverage.py`・secrets 系・`test_patterns_parity.py` に追加。

## 次のステップ
plan（実装計画）→ grill-plan → implement（opus dispatch）→ grill-code → review+qa+security。

## 実装済み（2026-07-20）

- commit 範囲: 5398e72（Task1 RED 6件実証）→ 9ccf295（Task2 helper）→ 3171949（Task3 destructive）→ a763653（Task4 secrets）→ 60bd9cb（Task5 回帰 pin）。
- `tests/test_moat_quote_split.py` 14/14 GREEN（バイパス 6・回帰 6・SF-019 残余 pin 2）。
- 実装時逸脱（Task4・Stage1 レビューで accept）: check-secrets.sh は patterns.sh を未 source だったため source 追加。ただし fail-closed（aegis_require_lib）でなく optional source＋`command -v` ガード（欠落時は二次補強 ASK のみ無効化・一次 deny 不変）。根拠: 一次防御は secrets-patterns.sh（fail-closed）由来で不変・copy_hooks が hooks/lib/*.sh を glob 全配布ゆえ欠落 install は正常経路で到達不能・HOOK_LIB_DEPS 契約（patterns.sh を check-secrets の fail-close 対象に含めない）と整合。
- SF-017 の quote/BS/${IFS} 綴りは封鎖。brace/param-default/cmdsub は SF-019 として残余起票（Task7）。
- grill-code 副産物: 大文字 case-fold 非対称を SF-020 起票（ffb1108・当初は raw/難読化ともに iter76 送り）。ANSI-C `$'\t'` は実測で無害（クォート内で非分割）と反証。

## fix-forward（2026-07-20・review reject 対応）

初回実装（5398e72..66c4d09）の review で **盲検2次(fable・独立)が2つの High バイパスを摘発**（1次 opus は見逃し＝乖離が実バグの在処）:
- **F1**: broad-stage/commit 難読化（`git${IFS}add -A`→実 .env silent staging→`git${IFS}commit`→commit backstop 回避→漏洩チェーン完成）。正規化 re-check が明示ファイル名検出器のみで broad-stage(:196)/commit(:270) 検出器を NORM に再適用していなかった。
- **F2**: backslash-newline 行継続（`git add \<NL>.env`→実行時 `git add .env`・helper が改行を残し grep 行分割で miss）。
reviewer-testing が **F3**（難読化大文字 `R""M -RF` の destructive 素通り＝:149 が NORM でなく NORM_LOWER を使い忘れ）・**F4**（弱い pin＝メッセージ非検証）を検出。いずれも SF-017 が「封鎖」と宣言した quote/${IFS}/backslash クラス**内**の穴（SF-019/020 の deferred クラスではない）。ユーザー裁定＝**道1（iter75 で塞ぐ・網羅性徹底）**。

- commit: `292f4a9`(FF1 RED 7件)→`23a8b61`(FF2 helper backslash-newline/残改行)→`b5e5390`(FF3 broad/commit スキャン再利用)→`5f03ac0`(FF4 難読化大文字 rm)→`0d3d95d`(FF5 pin 強化)→`9c3d7ea`(FF7 難読化大文字クラス全体を grep -i 化)。**review 再走で盲検2次＋reviewer-testing が FF4 の残穴〔非rm 全 CMD_REGEX が NORM fold 漏れ〕を摘発→FF7 で根本封鎖**。
- **helper 拡張**: backslash-newline(行継続)除去＋残改行/タブ→空白（順序: BS-NL を裸 BS 除去より前・bash 3.2.57 実測）。
- **broad-stage/commit**: FS/staged スキャンを `_aegis_broad_secret_kind`/`_aegis_staged_secret_kind` に関数抽出し NORM でも再利用（raw=deny/norm=ask）。**当初「難読化→ASK 一律(スキャン省略)」案は grill-plan で `git commit -m "quoted"` の誤検知爆発が判明し撤回**→スキャン再利用で誤検知なし。
- **難読化大文字**: destructive 正規化経路の**全 grep を `grep -i`（case-insensitive）on NORM 化**（FF4 で rm/LOWER、FF7 で CMD_REGEX 全19パターン＝chmod/find/dd/shred/mkfs/git 系）。`NORM_LOWER` 案は `chmod -R` の `R` リテラルが小文字化で壊れ捕捉不可のため不採（実測）。raw 大文字(`RM -rf`・NORM==CMD)は正規化経路外＝SF-020 に限定据置。
- **封鎖範囲**: quote・backslash・backslash-newline・`${IFS}`/`$IFS`・broad-stage 難読化・commit 難読化・難読化大文字クラス全体（rm/chmod/find/dd/shred/mkfs/git 系）。`tests/test_moat_quote_split.py` **36/36 GREEN**（初回14＋ff 10＋pin 強化1＋FF7 非rm 大文字10＋midword 1）。
- **封鎖実測（fix-forward 後）**: F1/F2/F3 難読化→ask・生 broad(`git add -A`,実 .env)→deny・`git commit -m ".."`(.env 非staged)→allow(誤検知なし)・raw `RM -rf`→allow(SF-020)。
- 残余: SF-019（brace/param/cmdsub・構造化 argv 待ち）・SF-020（raw 大文字直打ちに限定）・unicode 全角/ANSI-C（SF-016 カテゴリ＝無害）。

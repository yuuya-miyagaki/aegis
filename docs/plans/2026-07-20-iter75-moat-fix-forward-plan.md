# iter75 SF-017 fix-forward 実装計画（review reject 対応）

> **For agentic workers:** TDD 厳守（RED→GREEN）。per-task commit。実装は opus dispatch（session=fable）。CP コード（check-runtime-state.sh）は触らない。元計画＝`docs/plans/2026-07-20-iter75-moat-quote-split-implementation-plan.md`。

**契機:** iter75 review の**盲検2次（fable・独立）が reject**。1次（opus）が見逃した2つの High バイパスを実測検出。reviewer-testing も難読化大文字（Major）を検出。いずれも SF-017 が「封鎖」と宣言した quote/${IFS}/backslash クラス**内**の穴（SF-019/020 の deferred クラスではない）。ユーザー裁定＝**道1（iter75 で塞ぐ・網羅性徹底）**。

## 塞ぐ対象（review 実測 evidence 付き）

| ID | 穴 | 実測（現状） | 検出 |
|----|----|----|----|
| F1 | broad-stage/commit 難読化 | `git${IFS}add -A`→allow（生 `git add -A`=deny）・`git${IFS}commit`→allow | 盲検2次 High/conf10 |
| F2 | backslash-newline 行継続 | `git add \<NL>.env`→allow・`rm \<NL>-rf`→allow（実行時は実コマンド再構成） | 盲検2次 High/conf10 |
| F3 | 難読化大文字（destructive） | `R""M -RF`/`RM${IFS}-rf`→allow（secrets 側は NORM_LC で対称・穴なし） | reviewer-testing/1次 Major/conf8 |
| F4 | 弱い pin | `test_rm_rf_quoted_var_asks_via_raw` がメッセージ非検証で生経路削除を検知不能 | reviewer-testing/1次 Major/conf8 |

## 設計方針（fable 確定・grill-plan で叩く論点を明記）

### F1 — broad-stage/commit 検出器を正規化経路に配線
- `check-secrets.sh:196` の broad-stage トリガ regex を `_STAGE_BROAD_RE` に、`:270` の commit トリガ regex を `_STAGE_COMMIT_RE` に**変数化**（単一ソース化＝grill 致命2 の drift 回避と一貫。raw と正規化が同一検出器）。
- 正規化 re-check（`:346-357`）に、NORM_LC に対する `_STAGE_BROAD_RE`／`_STAGE_COMMIT_RE` の grep を追加。マッチ→**emit_ask**。
- **設計判断（grill 論点1）**: 難読化 broad-stage/commit は **FS/staged スキャンを省略し ASK 一律**。理由: (a) 正規化経路は一貫して DENY でなく ASK（command 位置非解釈）。(b) `git${IFS}add -A` を書くこと自体が異常＝実 .env の有無に関わらず確認対象。(c) ASK でユーザーが止められ silent 性が消える＝漏洩チェーン切断（moat の目的達成）。(d) find/git-diff の重い再走を難読化検出時に避ける。過剰 ASK は非ブロック・安全側。
- **grill-plan 反映（非対称の明示・2026-07-20）**: 「生 broad=DENY（実 .env 存在時）／難読化 broad=ASK」の非対称は**既存の明示 .env 経路と同一**（生 `git add .env`=DENY／難読化=ASK）で意図的。残余として「難読化 broad + 実 .env 存在が ASK 止まり（DENY でない）」を記録し、将来 DENY 化（正規化経路から FS スキャン再利用）の余地を pin する。
- **grill-plan 反映（実装注意・致命1・2026-07-20）**: `_STAGE_BROAD_RE`/`_STAGE_COMMIT_RE` は **`GIT_PRE_OPTS` 定義後**（既存 `_STAGE_HIGHRISK_RE`/`_STAGE_ENV_RE` と同一ブロック :152-154）に定義。secrets-patterns.sh 単体には `GIT_PRE_OPTS` が無い（実測 UNDEF）＝定義順を誤ると空展開で regex 破損。正規化経路は broad regex を **`NORM_LC`（小文字化済み）** に適用（`git add -A`→`-a` fold 前提。実測: 生 `-A` 大文字は broad regex `-a` に非マッチ／`git add .` は fold 不要でマッチ）。

### F2 — helper で backslash-newline を畳む
- `hooks/lib/patterns.sh` の `aegis_dequote_normalize` を修正。**順序が要**（backslash 単独除去より前に backslash-newline を除去）:
  ```sh
  c=${c//\\$'\n'/}         # backslash-newline（行継続）除去 ← 最初
  c=${c//\\/}              # 残り backslash 除去
  c=${c//\"/}
  c=${c//\'/}
  c=${c//'${IFS}'/ }
  c=${c//'$IFS'/ }
  c=${c//$'\n'/ }          # 残る改行を空白へ（複数行の単一行化＝行指向 grep 対策）
  c=${c//$'\t'/ }          # 残るタブも空白へ
  ```
- **設計判断（grill 論点2）**: 「残る改行を空白へ」は backslash なしの改行（`git add<NL>.env`＝bash では別コマンド・無害）も畳み過剰 ASK を生むが安全側（heredoc 内 .env 言及の誤 ASK は既存の明示経路でも起きる既知性質＝新規リスクなし）。
- **grill-plan 実測済み（2026-07-20・/bin/bash 3.2.57）**: 改訂 helper は全ケース正しく動作（`git add \<NL>.env`→`git add .env`・`rm \<NL>-rf`→`rm -rf`・`gi\<NL>t add`→`git add`〔語中継続〕・`a<NL>b`→`a b`・既存綴り不変・rc=0/stderr なし）。`$'\n'`/`$'\t'` param 展開と置換順序は健全＝懸念解消。
- **タブ処理（`c=${c//$'\t'/ }`）は raw 経路（`\s`/`[[:space:]]`）でカバー済みゆえ厳密には冗長**。改行を空白化するならタブもという対称性・ANSI-C 展開との一貫で残す（必須でないことを明記＝3年後の混乱防止）。

### F3 — destructive 難読化大文字
- `check-destructive.sh:149` の再帰削除 grep を `$NORM` → **`$NORM_LOWER`**。`R""M -RF`→NORM=`RM -RF`→NORM_LOWER=`rm -rf`→ASK。
- `:161` の CMD_REGEX ループは `$NORM`（生）のまま（raw 経路 :135 が生 `$CMD` ゆえ対称保持）。
- **raw 大文字（`RM -rf` 直打ち・NORM==CMD）は正規化経路に入らない**＝SF-020（別 iter）据え置き。iter75 は難読化大文字のみ拾う。SF-020 の記述をこの分離に更新。
- **分離基準（grill-plan 反映）**: `NORM != CMD`（難読化実在）なら iter75 の正規化経路が担当・`NORM == CMD`（難読化なし＝生大文字直打ち）は SF-020。実測: `R""M -RF`→NORM=`RM -RF`≠CMD→NORM_LOWER=`rm -rf`→ASK／`RM -rf`→NORM==CMD→skip→SF-020。

### F4 — 弱い pin 強化
- `_run` ヘルパーにメッセージ本文取得を追加（or 別 helper）、`test_rm_rf_quoted_var_asks_via_raw` に「WARN が『難読化された』プレフィクスを**含まない**（＝生経路）」assert を追加。生経路削除→正規化経路フォールスルーで flip する強い pin にする。

---

### Task FF1: RED — F1/F2/F3 の現状 allow を実証
**Create/Modify:** `tests/test_moat_quote_split.py`（追記）
- F1: `git${IFS}add -A`→ask 期待・`g""it a""dd -A`→ask 期待・`git${IFS}commit`→ask 期待（実 .env が repo に無くても難読化 broad/commit は ask）。
- F2: `git add \<NL>.env`（Python で `'git add \\\n.env'`）→ask・`rm \<NL>-rf /tmp/x`→ask。
- F3: `R""M -RF /tmp/x`→ask・`RM${IFS}-rf /tmp/x`→ask。
- 実測で現状 allow を確認（RED）。commit。

### Task FF2: helper backslash-newline（F2 GREEN 化の一部）
**Modify:** `hooks/lib/patterns.sh`・`tests/test_patterns_parity.py`
- helper を上記順序で修正。parity 単体に `norm('git add \\\n.env')=='git add .env'`・`norm('rm \\\n-rf')=='rm -rf'`・`norm('a\nb')=='a b'` を追記（RED→GREEN）。既存 parity 全 PASS 維持。commit。

### Task FF3: check-secrets 単一ソース化＋正規化 broad/commit（F1 GREEN 化）
**Modify:** `hooks/check-secrets.sh`
- `:196`/`:270` のトリガ regex を `_STAGE_BROAD_RE`/`_STAGE_COMMIT_RE` に変数化（挙動保存：既存 secrets 系テスト全 PASS 確認）。
- 正規化 re-check に NORM_LC での両 grep 追加→emit_ask。
- FF1 の F1 テストが GREEN。生 broad/commit の DENY 不変を確認。commit。

### Task FF4: check-destructive 難読化大文字（F3 GREEN 化）
**Modify:** `hooks/check-destructive.sh`
- `:149` を `$NORM_LOWER` に。FF1 の F3 テスト GREEN。既存 destructive 回帰全 PASS（平文・safe artifact 不変）。commit。

### Task FF5: 弱い pin 強化（F4）
**Modify:** `tests/test_moat_quote_split.py`
- `_run` 拡張 or メッセージ取得 helper 追加。`test_rm_rf_quoted_var_asks_via_raw` にプレフィクス非含有 assert。commit。

### Task FF6: 回帰・フルスイート・docs 更新
- フルスイート green（既知 flaky 除く）・contract・doctor PASS。
- バイパス封鎖の最終実証（F1/F2/F3 の親再現）。
- `docs/specs/2026-07-20-iter75-moat-quote-split-design.md`・`docs/security-followups.md`（SF-017 封鎖範囲を実態に・SF-020 を raw 大文字に限定）・STATUS を更新。
- unicode fullwidth（`ｒｍ`）は SF-016 カテゴリ（bash 非コマンド＝無害）として security-followups.md に一言記録（pin 不要）。
- commit。

## 完了後
grill-code（再）→ review 再走（1次＋盲検2次・moat 変更ゆえ必須）→ qa → security → ship → docs。

## Self-Review
- review reject の F1/F2 と Major F3/F4 を全カバー。
- grill 論点: (1) 正規化 broad/commit を ASK 一律にする判断（FS スキャン省略）。(2) helper の残改行→空白の過剰 ASK 受容と bash 3.2 param 展開。(3) F3 で raw 大文字を SF-020 据え置きにする分離の妥当性。

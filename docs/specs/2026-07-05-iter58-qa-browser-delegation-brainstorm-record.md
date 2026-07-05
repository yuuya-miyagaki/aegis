# BRAINSTORM-RECORD — iter58 qa-browser 委譲プロンプト標準化
<!-- 正本: brainstorming skill -->

## 入力

- iter56 ドッグフード M2 backlog の「候補外・記録のみ」＝retro Try#2:
  「qa-browser の途中停止の根治は未達（5項目分割＋SendMessage 再開で運用としては確立。
  『全項目完了まで最終報告を出さない』拘束の skill 昇格＝委譲プロンプト改善として別途）」
  （`docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md:117-118`）。
- 一次観測: ui_surface QA で qa-browser サブエージェントが長尺バッチで途中停止（19項目一括で3回停止）。
  一次情報は yoga-tsukinowa-lp 側 DOGFOOD-M2-LOG（別リポ・本イテレーションでは参照しない）。
- 現状: `qa-verification SKILL.md` の「qa-browser 委譲ルール」に「1委譲5項目程度に分割」は
  iter56 で追加済み。残るは「途中停止させない拘束」＋再開プロトコルの標準化。

## 合意した設計

- スコープ = **純プロンプト標準化（guidance のみ）**（ユーザー決定 2026-07-05・「おすすめ」= Option 1）。
- `qa-verification SKILL.md` の委譲ルールを**標準委譲プロンプト雛形**に置換。拘束5点:
  ①項目 ≤5・連番 ②全項目にエビデンスが揃うまで最終報告禁止（partial を final と偽らない）
  ③途中停止は新規委譲でなく SendMessage で同一エージェント継続 ④項目単位の `[n/N done]` 進捗
  ⑤エビデンス形式 `{項目,操作,期待,実測,PASS/FAIL,screenshot/console}`。
- 定置先 = qa-verification skill インライン（新テンプレファイルは作らない＝YAGNI）。
- 決定論トリップワイヤ = `tests/test_skill_guidance_tokens.py`（iter56 で qa-verification を対象化済）に
  load-bearing トークンを pin（核心命令の silent 消失を機械検出＝P3 skill 挙動圧力テストの流儀）。

## 却下・descope した案

- **Option 2（guidance＋決定論的完了バックストップ）**: qa 検証項目チェックリスト artifact ＋
  「全項目エビデンス充足まで qa ゲート不可」の機械検査。→ **descope**（M+・qa ゲート機構＝judge/
  check_status に手を入れる・「軽量」の意図に反する。実消費が増えたら再検討）。
- **Option 3（browser-assist へテンプレ切り出し）**: 委譲プロンプトを汎用テンプレ化し integration 等からも参照。
  → **descope**（YAGNI・現状 qa-browser のみが消費者。再利用需要が出てから切り出す）。

## スコープ境界

- 対象 = qa-browser への**委譲プロンプト**の標準化のみ。
- 非対象 = browser-assist の $B/Playwright 操作挙動（不変）・qa ゲート機構（judge/check_status 不変）・
  qa-browser 停止の**技術的**根治（プロンプト規律で運用対処・3-failure ルールに従う）。

## 未解決事項（plan / grill-plan で詰める）

- token pin の粒度（完了拘束フレーズは必須 pin・進捗形式は緩め、の線引き）。
- 語数予算（context_budget）を割らないための表現圧縮。
- 規模想定 = M（qa-verification SKILL.md ＋ test_skill_guidance_tokens.py の2ファイル・framework・moat 非該当）。

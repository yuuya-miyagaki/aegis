# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-22

## テーマ

- iter76: evidence 整合＋locale 掃討完了（roadmap §5 P0）— washed-green/src allowlist（§4.2・SF-012）＋ SF-018（LOCALE-1）

## コンテキスト

- 現在の状況: iter75（SF-017 moat quote-split 一般化）クローズ・v1.31.2。二重網羅レビュー正本 `docs/full-review-2026-07-19-dual-codex-fable.md` §5 が iter76＝「evidence 整合＋locale 掃討完了」を P0 指定。完了条件＝「`pytest; true`/fake-output が green 不可・runtime-state の byte crash 消滅・設計正本訂正」。
- きっかけ: §4.2 EVIDENCE-FORGE（High〜Critical・親再現済み）＝exit 洗浄（`; true`/`|| echo`/`| tee`）で失敗 run が judge green 化。§4.3 LOCALE-1（Medium・親再現済み）＝`check-runtime-state.sh` が不正 UTF-8 バイトで tr crash→fail-open（iter73 の完全性主張の反証）。SF-012 に修正方向が既に明文化済み（(a) exit=0×failed-token 矛盾で marker 無効化・(b) src allowlist＝終端🟡）。
- 併合判断の宿題: STATUS next_action が SF-020（destructive raw 大文字 case-fold・High）・SF-021（`git stage` エイリアス・High）を iter76 併合候補として持ち越し。

## 検討したアプローチ

### アプローチ A: roadmap 準拠 3 点セット（W1+W2+W3・M）【採用】

- 概要: iter76 を roadmap どおり evidence 整合＋locale に限定。W1=SF-018（`check-runtime-state.sh` に `LC_ALL=C`＝iter73 同型・3本目）、W2=washed-green 封鎖（judge: observed cmd のクォート外シェル演算子 `[;&|]` 検出→undecidable 化＋marker.sh: exit=0×failed>0 の矛盾軸→verdict false）、W3=SF-012(b) src allowlist（`manual`/`observed` 以外→終端🟡）。SF-020/021 は次 iter（S・broad/destructive 網羅対称化）へ順送り。
- 利点: roadmap P0 完了条件と 1:1 対応。単一テーマ＝review/security の焦点保全（iter75 教訓）。src 3 ファイル＋tests＝M で deploy gate 不要。新規 regex ゼロ（既存 count families・quoted-span マスクの再利用）＝「regex を足さない」原則整合。
- 欠点: SF-020/021（High×2）の解消がもう 1 iteration 遅れる（ただし発火は「raw 大文字直打ち」「`git stage` 直打ち」＝意図的綴りで事故経路は薄い）。

### アプローチ B: SF-020/021 併合（W1〜W5・L）

- 概要: A に加えて check-destructive.sh（raw CMD_LC 化＋redirect 大文字パス）と check-secrets.sh（`(add|stage)`）を同一 iter で消化。
- 利点: High×2 を最速でクローズ。iteration プロセス（brainstorm→…→security）1 周分のオーバーヘッド節約。
- 欠点: src 5 ファイル＋tests＝L 化（deploy gate 追加・全フェーズ必須）。evidence 整合と moat 網羅の 2 テーマ混在＝盲検レビューの主張が曖昧化・review 表面積が拡大（iter75 は「焦点保全」を理由に reject 分を分離してクローズした直後）。roadmap のテーマ分割原則に反する。

### アプローチ C: 最小修正（W1+W2a のみ・S）

- 概要: crash 修復とシェル演算子 undecidable 化だけ入れ、矛盾軸（W2b）と src allowlist（W3）は後回し。
- 利点: 最小 diff。
- 欠点: roadmap 完了条件「fake-output が green 不可」に未達（compound 形 fake は W2a で落ちるが、W3 なしでは unknown-src forge が残り、SF-012 が OPEN のまま次に持ち越し）。W2b/W3 は各数行＝分割の節約が実質ない。

## 決定

- 採用アプローチ: A（roadmap 準拠 3 点セット・M）
- 採用理由: P0 完了条件との 1:1 対応・単一テーマによる盲検レビュー焦点保全・M サイジング（deploy 不要）・「regex を足さず既存 primitive 再利用」の原則整合。SF-012 の既記載修正方向をそのまま実装に落とせる＝設計リスク最小。
- 不採用理由: B は L 化とテーマ混在のコストが High×2 の早期クローズ利益を上回る（両 SF は意図的綴り限定で事故経路が薄く、S effort で次 iter 即消化可能）。C は完了条件未達で iter76 を「完了」と主張できない。

## スコープ境界

- やること:
  - W1: `hooks/check-runtime-state.sh` の入力読取直後に `export LC_ALL=C LC_CTYPE=C LANG=C`（iter73 と同型・destructive/secrets に続く 3 本目）＋ `tests/test_hook_locale_byte.py` に crash-regression pin（旧=rc1 crash 赤/新=rc0 decision 緑）＋ iter73 設計正本（`docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md`）の「runtime-state は同型不成立」誤記述の訂正。
  - W2a: `scripts/build-judge-card.py` `read_test_result` の undecidable 述語拡張＝src=observed で cmd にクォート外シェル演算子（`;` `|` `&`・改行→`;` 正規化後・quoted-span は既存 strips で Q マスク済み）を含む場合は marker_verified に関わらず undecidable（ok→transparent / fail→終端🟡＝trust-scan 意味論不変）。
  - W2b: `hooks/lib/marker.sh` stage 5 拡張＝検出済み count family の failed 合計 >0 かつ exit_code==0 → verdict false（zero-run gate と同型の整合軸・SF-012(a) の記載どおり）。実失敗 run（rc≠0）は非該当＝red 判定の非退行を pin。
  - W3: `read_test_result` の src allowlist＝`src not in ("manual","observed")` → 終端 unverified🟡（SF-012(b) の記載どおり・fail-visible）。
  - 旧赤/新緑 differential pin（roadmap ship 条件）: `pytest; true`・`pytest || echo done`・`pytest | tee`（fail run）・compound fake-runner・unknown-src・0xFF crash の各ベクタ。
- やらないこと:
  - SF-020/021（次 iter で S 消化・roadmap の attestation 前に挟む）。
  - SF-019（構造化 argv・iter77 系）・pytest execution attestation 本体（iter77）。
  - evidence.sh writer 側での wash 検査（reader＝judge を単一信頼権威とする・diff 最小化。marker.sh の矛盾軸は writer/record/drill 3 消費者共通で入る）。
  - 新規 regex/denylist の追加（既存 count families・マスクパイプラインの再利用のみ）。〔2026-07-22 実装同期: fail-token 整合軸 1 本（`AEGIS_TEST_FAIL_TOKEN_REGEX`）のみ追加に訂正——count families は unittest の failed を単離抽出できないと plan 時に判明。moat denylist の増殖ではなく SF-012(a) 記載の修正方向。詳細は design の §実装同期〕
  - record-test-result.py の変更（shell なし実行＝実行系防御が既に washed 形を構造的に無効化・iter70 検証済み。judge との非対称は by-design と設計ノートに明記）。

## 未解決事項

- 残余（既知天井・iter77 送り）: 単一コマンド fake binary（`./pytest`・PATH hijack）は静的検査の射程外＝attestation（iter77）の領分。`test_residual_*` pin で固定し将来 flip を強制する。
- W2a の `&&` blanket 扱い（`cd x && pytest` の観測 green も undecidable 化＝record-test-result での正式記録に誘導）: 精密な「最終コマンド位置」解析は複雑化に見合わないため blanket を推奨。plan の grill-plan で再確認。
- evidence.sh の exitCode 欠落パス（ec=""）×failed>0 は現状維持（wash 検査 W2a が被覆・矛盾軸は exit==0 確定時のみ発火）。plan で fail-visible 側に倒す価値を再評価。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

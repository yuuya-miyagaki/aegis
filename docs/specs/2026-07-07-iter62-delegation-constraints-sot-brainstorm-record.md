# ブレインストーミング記録

## 日付

- 2026-07-07

## テーマ

- iter62: 委譲拘束 SoT 標準化（全体レビュー 2026-07-06 §2 R1 文言層・Phase 0-1 残り）

## コンテキスト

- 現在の状況: iter61/v1.22.0 で R1 の機械層（patterns.sh 9パターン）＋復旧層（snapshot 退行ガード）は封鎖済み。
  残るは文言層＝`.claude/` 内に検証系委譲の tree 変更禁止拘束が grep 0 件（R1 実証）。
  iter60 事故（security 盲検2次の `git checkout docs/*` で親の gate 簿記 revert）の再発防御が
  委譲文言レベルで存在しない。
- きっかけ: 全体レビュー正本 `docs/full-review-2026-07-06-six-dimensions-evolution.md` §2 R1 修正方向(1)・§4 Phase 0-1。

## 検討したアプローチ

### アプローチ A: routing.md 単一正本＋4消費側参照＋token-pin（採用）

- 概要: `.claude/rules/routing.md` に「## Verification delegation」節＝検証系委譲の標準6拘束
  （qa-verification 5点の一般化＋6点目 read-only/tree 変更禁止）を単一正本で設置。
  qa-verification／aegis-review-gate／aegis-security-gate／subagent-dev は参照＋核1行のみ。
  `tests/test_skill_guidance_tokens.py` の token-pin で正本と参照の silent 消失を機械封鎖。
- 利点: SoT＝修正が全ディスパッチ経路へ伝播／iter59（SendMessage SoT）と同型で先例あり／
  pin により drift 決定論検知。
- 欠点: routing.md budget（70・headroom 0）の raise が必要（＝budgets.json 編集）。

### アプローチ B: 各スキルに6点をフル複製（不採用）

- 概要: 4ファイルそれぞれに6拘束の全文を書く。
- 利点: 参照の間接性がなくファイル単体で自己完結。
- 欠点: SoT なし＝ドリフト再発（R1 の指摘構造そのもの）。reviewer.md:56 の汎用文言が
  「存在したのに事故を防げなかった」実証があり、複製文言の増殖は防御にならない。

### アプローチ C: 雛形を budget-exclude で計数除外（不採用）

- 概要: routing.md の雛形を `aegis:budget-exclude` マーカーで包み budget 据置。
- 利点: budgets.json の raise 不要。
- 欠点: 除外には region==content 完全一致 pin が必要（CLAUDE.md Context Budget Policy）＝
  prose 雛形の完全一致 pin は正当な言い換えで false RED（iter58/59 教訓）。
  濫用ガード（len==1・allowlist トリップワイヤ）の改修も増える。
  drift-pin 済 100% load-bearing prose は「追加分ちょうどの raise」が正当（iter59 教訓核）。

## 合意事項（スコープ境界）

- routing.md に英語・簡潔な6拘束雛形（Subagent continuation 節の後）。6点目 read-only は無条件。
- 消費側4ファイルは参照＋核1行（qa-verification は6点目として明記）。
- token-pin: 否定句（`MUST NOT` を含む句）で pin（意味反転 false-PASS 防止・iter59 教訓）＋一意性。
- budget: routing.md は追加分ちょうど raise。他ファイルは headroom 内なら据置。
- バージョン v1.22.0→v1.23.0（MINOR）。
- 非スコープ: サブエージェント status enum（DONE/BLOCKED 等）は Phase 3-3（YAGNI）。
  SubagentStart hook 注入（将来項目）。機械層/復旧層の追加変更（iter61 完了済み）。

## 未解決事項

- B1 drill を実 mutant（md 追加行の token 削除/否定反転→pin テスト赤化）で回すか、
  floor が test/json ハンクで block した場合に iter59/60 前例（skip＋手動 mutation 実証）へ
  切り替えるか → qa フェーズで diff 実態を見て判断（plan に両経路を記載）。

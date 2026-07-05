# BRAINSTORM-RECORD — iter59 サブエージェント継続（SendMessage）の SoT 定義
<!-- 正本: brainstorming skill -->

## 入力

- iter58 review 盲検2次 note1（`docs/qa-reports/iter58-review.md`・TO-CLIENT に起票）:
  `SendMessage` が iter58 追加の qa.md/qa-verification にのみ出現・機構定義が正本ファイルに無い＝dangling。
- iter56 M2 ドッグフードで「5項目分割＋SendMessage 再開は運用として確立」＝機構は実証済（ただし aegis 哲学では
  ハーネス非強制の運用 guidance）。iter58 security 2次も「maxTurns＋3-failure で有界・無限再開リスクなし」を確認。

## 合意した設計

- スコープ = `SendMessage`（サブエージェント継続）を **routing.md に単一正本として定義**（ユーザー決定 2026-07-06）。
- 定義（英語・routing.md の言語）: 「Resume a stalled subagent via SendMessage (same agent, context preserved),
  not a fresh re-dispatch. Guidance, not harness-enforced; bounded by each agent's maxTurns and the 3-failure rule.」
- principle を1文化して bump を最小化＋`context-budgets.json` の routing.md budget を 75→90 に引き上げ。
- 継続定義を `test_skill_guidance_tokens.py` で token pin（iter58 の tripwire 哲学継承）。
- qa-verification は不変（既存 SendMessage 用法が routing.md 定義で裏打ちされ dangling 解消・headroom 6 を守る）。

## 却下・descope した案

- **subagent-dev に定義**: headroom 14 で budget を触らず済むが、subagent-dev は implement 駆動開発の skill＝
  qa→qa-browser 継続とは文脈がややズレる。routing.md（サブエージェント機構の正本）が右文脈。→ **却下**。
- **最小スコープ（qa-verification 性質注記のみ）**: SoT 別ファイル化を見送り qa-verification に「運用 guidance・
  非強制」注記だけ。dangling の『定義なし』は解消しきれず・qa-verification headroom 6 も tight。→ **却下**。
- **budget ratchet policy 先行**: 全 guidance ファイルが floor 近い（routing 7/subagent-dev 14/state-machine 0）＝
  ラチェットに成長余地がない、を先に主題化する案。有意義だが本 iter の目的（note1 解消）から逸れる。→ **descope**（別イテレーション候補として記録）。

## 却下した「routing.md 圧縮」案（実測で不能と判明）

- 当初ユーザーは「routing.md を圧縮して追加」を選択したが、実測で **agent 列挙が `check_reference_drift #1` により
  agents/ と双方向 mirror で drift-pin**＝削除すると FAIL。principle 以外に圧縮余地なし（~5トークン）で継続定義（~28）に
  全く届かない＝**圧縮パスが存在しない**ことが判明。→ ユーザー再判断で **budget 引き上げ**へ切替（下記正当化）。

## スコープ境界

- 対象 = routing.md への継続定義追加＋budget 更新＋token pin。
- 非対象 = qa-verification/qa.md の SendMessage 用法（不変）・agent roster（drift-pin・不変）・
  SendMessage の技術的実装（ハーネス側・aegis は運用 guidance として扱う）・budget ratchet policy 全体見直し（別イテレーション）。

## 未解決事項（plan / grill-plan で詰める）

- token pin の粒度（`SendMessage`＋`harness-enforced` 核の線引き・iter58 の「presence 保証／全出現削除で RED」教訓を反映）。
- budget bump の正確値（75→90 か・principle 圧縮量との兼ね合い）と、正当化の LEARNINGS 記録文言。
- 規模想定 = M（routing.md ＋ context-budgets.json ＋ test の3ファイル・framework・moat 非該当）。

## 予算引き上げの正当化（この iter の核心的設計判断）

- iter58 は budget-raise を却下（圧縮可能な冗長があった）。iter59 は routing.md が100% load-bearing
  （roster=drift-pin・rule 必須）で**圧縮不能**＝「圧縮回避の bump」でなく「pinned ファイルへの正当追加の受容」。
  この区別を LEARNINGS に残し、ラチェットの anti-bloat 趣旨（不要な bloat 阻止）は守る。

# iter59 セキュリティレポート（security ゲート）

- 対象: iter59・実装 commit `b2c2851`＋review fix-forward `89fb52f`（サブエージェント継続 SendMessage の SoT 定義・guidance のみ）
- 仕様: `docs/specs/2026-07-06-iter59-subagent-continuation-sot-design.md`
- 性質: `.claude/rules/routing.md`（rule guidance）＋`context-budgets.json`（語数予算）＋token pin テストのみ。**moat 非該当・hook/判定/enforcement コード不変**（設計明記）。

## 脅威モデルとスコープ

本イテレーションはサブエージェント継続（SendMessage）の運用 guidance を routing.md に SoT 定義し、budget を引き上げ、継続定義を token pin する変更。実行時の権限・信頼境界・moat（OS-lock/control-plane）・deny/ask 判定・destructive-command ガードには一切触れない。したがってセキュリティ上の主眼は「**後退（保護の弱体化・秘密混入・偽装強制）が無いか**」の確認。

## 検査結果（実測）

| 観点 | 結果 | 根拠 |
|------|------|------|
| Secrets / credential 露出 | ✅ なし | diff の追加行に password/secret/token=/api_key/private-key/bearer パターン 0（`git diff b2c2851~1 89fb52f \| grep -inE ...`） |
| moat / enforcement 後退 | ✅ なし | 変更ファイルは routing.md・context-budgets.json・test の3つのみ。`hooks/`・`check-runtime-state`・`update-gate`・`setup.sh` 等の enforcement/moat コードは不変（`git diff --name-only` で確認） |
| 偽装強制（guidance→強制の誤認） | ✅ なし | 継続節は明示的に "**Guidance, not harness-enforced**" と宣言＝ハーネス保証と誤認させない。むしろ pin を `not harness-enforced` 句へ強化し「非強制」の反転（強制と偽る文言）を機械検出（fix-forward 89fb52f） |
| 無限再開 / 資源枯渇 | ✅ 有界 | 継続節が "bounded by each agent's `maxTurns` and the 3-failure rule" と明記＝maxTurns（各 agent frontmatter・qa=30/qa-browser=20 等）＋3-failure ルール（CLAUDE.md Operating Contract）で停止。無限ループの新設なし（iter58 security 2次も同結論） |
| Injection / 入力検証 | 該当なし | token pin は静的文字列 assertion（外部入力なし）・budget は整数リテラル。実行系・パーサ・外部入力パスの追加なし |
| 予算引き上げ (75→90) の含意 | ✅ 無害 | context 語数予算は「肥大化防止のラチェット」で保護機構ではない。引き上げは routing.md への正当な rule 追加分に限定＝いかなる deny/ask/moat も無効化しない |
| Vulnerable dependencies | 該当なし | 依存マニフェスト（requirements/package.json 等）の変更なし |

## OWASP Top 10（該当項目のみ）

- **Injection**: 非該当（実行系・外部入力なし）。
- **Broken Authentication**: 非該当（認証フロー不変）。
- **Sensitive Data Exposure**: secrets grep 0。
- **Security Misconfiguration**: budget 変更は保護設定ではない（無害）。
- **Vulnerable Dependencies**: 依存変更なし。

## deploy blocker

なし（M framework で deploy 自動 exempt）。

## 判定

**PASS（1次）。** guidance のみ・moat/enforcement コード不変・secrets 0・偽装強制なし・継続は maxTurns＋3-failure で有界・依存変更なし。セキュリティ後退は検出されず。

## 盲検 第2意見（self-attested）

fresh context の general-purpose エージェントに diff（b2c2851~1..89fb52f）＋spec＋plan のみを渡し、1次結論を非開示で独立2次セキュリティレビューを1回ディスパッチ（5論点: secrets 露出／moat 後退／無限再開／injection／budget 含意）。

**2次 verdict = approve（findings ゼロ）。** 5論点すべて後退なしと独立確認。実走 PASS（contract/drift/pytest 11 passed/context_budget exit0）＋`maxTurns`/3-failure の実在（全 agent＋implementer/qa-verification/status_doctor.py で grep ヒット）を確認し、継続 guidance の有界性が既存 enforcement レイヤに接地していることを検証。fix-forward の `not harness-enforced` 句 pin は「後退どころか防御を1段追加」と評価。1点の divergence＝headroom-0 の運用メモ（セキュリティ影響なし・plan/LEARNINGS に co-bump ルールとして予約済）。

```claims
verdict: approve
tests_green: true
no_stubs: true
second_opinion:
  verdict: approve
  notes: 5論点（secrets 露出/moat 後退/無限再開/injection/budget 含意）を独立精査し全て後退なし。変更3ファイルに hook/deny/guard/lock/gate/enforce 系ゼロ・secrets 0・contract/drift/pytest(11)/context_budget 全 PASS。継続は guidance（非強制）で maxTurns＋3-failure（実在を grep 確認）に接地し無限再開の余地なし。fix-forward の 'not harness-enforced' 句 pin は保護を1段追加と評価。1次と一致（approve）。
  divergence_points: ["routing.md budget が実語数と完全一致（90=90・headroom 0）＝次 iter で routing.md 加筆時は同時 bump 必須（設計意図どおり・セキュリティ影響なし・運用メモ）"]
```

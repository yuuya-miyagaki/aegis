# iter58 セキュリティレポート（security ゲート）

- 対象: iter58・commit 8de3f8a（qa-browser 委譲プロンプト標準化・guidance のみ）
- 仕様: `docs/specs/2026-07-05-iter58-qa-browser-delegation-design.md`
- 性質: skill/agent の Markdown ＋ token pin テストのみ。**moat 非該当・hook/判定コード不変**（設計明記）。

## 脅威モデルとスコープ

本イテレーションは qa→qa-browser の**委譲プロンプト guidance** の標準化と token pin の追加。
実行時の権限・信頼境界・moat（control-plane lock）・deny/ask 判定には一切触れない。
したがってセキュリティ上の主眼は「**後退（保護の弱体化・秘密混入）が無いか**」の確認。

## 検査結果（実測）

| 観点 | 結果 | 根拠 |
|------|------|------|
| 秘密情報の混入 | ✅ なし | judge `scan_secrets` = 0件。diff は自然言語 guidance＋テストのみ・鍵/トークン/認証情報なし |
| moat/保護コードの改変 | ✅ なし | 変更は `.claude/skills/qa-verification/SKILL.md`・`.claude/agents/qa.md`・`tests/test_skill_guidance_tokens.py` の3ファイルのみ。`hooks/`・`scripts/`・control-plane lock・deny/ask 判定は不変（`git diff HEAD~1 --name-only` で確認） |
| セキュリティ guidance の後退 | ✅ なし | 削除した「確認事項ブロック」は番号手順1-4の逐語重複（セキュリティ指示を含まない）。intro 圧縮は boilerplate のみ。qa.md の禁止事項・境界は不変 |
| qa.md 縮約による検査弱体化 | ✅ なし | Browser QA 委譲は skill 参照へ縮約したが、参照先 skill の委譲ルールは**より詳細**（拘束5点）。console/network エラー確認等の検証指示は qa-browser.md（Browser Checks 節）に不変で存在 |
| token pin の悪用可能性 | ✅ なし | pin は「核心命令の存在」を assert するのみ（読み取り専用の文字列一致）。セキュリティ検査をすり抜けさせる副作用なし。短核 pin で false RED を抑制・presence 保証で silent 消失を検出 |
| 新拘束のリスク（無限再開・漏洩経路） | ✅ なし | SendMessage 再開は既存の subagent 機構・回数は 3-failure ルール（CLAUDE.md・goal 単位）で上限管理。完了拘束は「報告抑制」で外部送信を増やさない |
| 依存監査 | 🟡 unverified（ack 対象） | dependency manifest（package.json/requirements.txt 等）の変更ゼロ＝**依存ゼロ**。audit 対象が無く unverified。脆弱性の実体なし |

## 決定論検査

- tests: green（現 HEAD 8de3f8a・manual green）／ stubs: 0件 ／ secrets: 0件
- full suite: 1050 passed / 2 skipped ／ check_framework_contract: PASS ／ context_budget: exit 0

## 判定

- **PASS（1次: approve）**。deps🟡 は依存ゼロ（manifest 不変）につき ack。
- セキュリティ後退・秘密混入・moat 改変のいずれも無し。guidance のみの後方互換な追加。

## 盲検 第2意見（self-attested）

2次レビュアー（general-purpose・fresh context・1次結論非開示）に diff＋spec のみを渡し、秘密混入・
moat/保護コード改変・セキュリティ guidance 後退・qa.md 縮約による検査弱体化・token pin の偽陽性/偽陰性・
新拘束（完了拘束/SendMessage 再開）のリスクの6軸で独立精査。**verdict= approve・divergence なし**。

独立に実測確認した事実（1次と一致）:
- moat/保護コード不変（変更7ファイルは Markdown＋テスト1本のみ・hooks/scripts/control-plane/gate 判定に grep 0件・contract EXIT 0）。
- 秘密情報 0件（鍵/トークン/認証/顧客情報パターン走査）。
- 削除「確認事項ブロック」は存置「エビデンス収集チェックリスト」に完全被覆・旧 skill に secret/PII 指示は元々なし＝後退なし。
- qa.md から console/network 明示 bullet が消えたが、browser 側セキュリティ検査（console error・4xx/5xx）の**正本は委譲先 qa-browser.md**（Browser Checks 節）で不変＝弱体化なし・むしろ SoT 一本化で二重管理ドリフト減。
- token pin は全5トークンで削除→RED 化を実測（vacuous でない）・判定ロジックに触れない。
- SendMessage 再開は `qa` maxTurns:30／`qa-browser` maxTurns:20 ＋ 3-failure ルールで多重有界・新規外部送信経路なし。完了拘束は完了偽装を減らす方向でプラス。

非ブロッキング補足（2次・修正不要）: 将来 qa-browser.md の Browser Checks 節を編集する際は、そこが
ブラウザ側セキュリティ検査（console error / 4xx-5xx）の唯一正本である点に留意（本 iter 範囲外）。

```claims
verdict: approve
tests_green: true
no_stubs: true
second_opinion:
  verdict: approve
  notes: 6軸（秘密混入/moat 改変/guidance 後退/qa.md 縮約/token pin 偽陽陰性/新拘束リスク）を独立精査し全て後退なしと確認。moat/保護コード不変・contract PASS・secrets 0・削除ブロックは存置チェックリストで被覆・browser 検査は qa-browser.md が正本・pin は全5トークンで RED 実証・SendMessage 再開は maxTurns＋3-failure で有界。1次と完全一致。
  divergence_points: []
```

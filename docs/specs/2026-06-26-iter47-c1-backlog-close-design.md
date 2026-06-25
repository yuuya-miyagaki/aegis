# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-26-iter47-c1-backlog-close-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（backlog C1）

## 問題整理

- 背景: full-review backlog の最後の残項目 C1 を triage。grill-premise＋コード確認で C1 は現状到達不能（first-path-only は複数パス tool が無く・matcher は現行 write-tool 全カバー＋stale_keys 機構あり）と確定。実コード修正なし。
- 判断が必要な論点: なし（verdict 確定）。配置＝既存 `security-followups.md`（SF-007/008 と同じ tracker）。
- 制約条件: コードを書かない。脅威モデル（self-bypass）外や既存機構と重複する防御を足さない（YAGNI）。

## 推奨アプローチ

- 採用: `security-followups.md` に **SF-009（C1・forward-looking robustness / accepted residual）** を追記。`## 調査済み・非該当（NOT-A-VULN / by-design）` 節へ。あわせて **full-review backlog を triaged-complete としてクローズ**（backlog 行更新＋C1 finding pointer）。
- 採用理由: SF-007/008 と同じ durable tracker に集約・既存様式に整合。
- 代替案と不採用理由: 防御コード追加＝存在しない入力への YAGNI／matcher 動的列挙＝stale_keys と重複。

## コンポーネント分解（ファイル変更マップ）

- 変更: `docs/security-followups.md` — SF-009（C1 disposition）を追記。`## 調査済み・非該当` 節冒頭 or SF-008 の後。
- 変更: `docs/full-review-2026-06-24-...md` — backlog 行を triaged-complete に更新（C1→SF-009 pointer）＋C1 finding(:65) に closure pointer。
- テスト: なし（docs-only）。

## インターフェース定義 / データフロー

- 該当なし（ドキュメント変更・公開 API/関数なし）。SF-009 は既存 SF 様式（発見・種別・重大度・根拠・状態）に揃える。

## 依存関係

- `security-followups.md`（正本）→ full-review doc がそこへ pointer。循環なし。

## エラーハンドリング

- 想定失敗: C1 を「修正した」と誤読／「将来も絶対安全」と過大主張。
- 対応: SF-009 を「forward-looking・現状到達不能・将来 multi-path tool 追加時に再評価」と明記。matcher は stale_keys 機構が catch する旨を書く。

## テスト戦略

- 単体/結合: なし（docs-only・production code 追加なし）。
- 手動確認: status_doctor PASS / framework contract PASS（ref 整合）/ review ゲート（doc 明瞭性・C1 verdict の正確性・過大主張なし）。
- size=S のため qa（B1 drill）/security/deploy は SIZE_ALLOWED_PHASES で免除。

## 次のステップ

- [ ] size=S のため plan フェーズは免除（SIZE_ALLOWED_PHASES["S"]={brainstorm,implement,review,ship}）→ implement へ直接遷移。

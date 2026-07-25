# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-26

## テーマ

- iter77 スコープ決定: SF-020（destructive raw 大文字 case-fold）＋SF-021（git stage エイリアス）封鎖 vs pytest execution attestation

## コンテキスト

- 現在の状況: iter76 完全クローズ（v1.31.3・全ゲート approved・未 push）。iter77 rollover 済（全 dev ゲート pending・iteration 77・phase brainstorm）。
- きっかけ: roadmap §5（`docs/full-review-2026-07-19-dual-codex-fable.md`）は iter77=pytest execution attestation（P0/P1・M・1〜2 iter）を予定。一方、台帳 `docs/security-followups.md` に **High・OPEN・silent allow の SF-020/SF-021** が iter75→76 と2回繰延のまま残存。

## 検討したアプローチ

### アプローチ A: SF-020＋SF-021 先行（iter77・S/M）

- 概要: 両 High を単独 iter で即封鎖。attestation は iter78 で M フル集中。
- 利点: 露出中の最重大リスクを最短で消す。SF-021 は `git stage` が git 公式エイリアスゆえ**注入なしの無邪気なモデルでも到達し得る**＝台帳中最も到達性の高い OPEN 穴。SF-020 は作者実機（macOS APFS）で `RM -rf` silent allow。iter76 brainstorm の「次 iter へ分離」記録とも整合。attestation の遅延は実質 1 iter 未満。
- 欠点: roadmap §5 の順序と1つずれる（attestation が iter78 へ）。

### アプローチ B: attestation 先行（iter77〜78・M）

- 概要: roadmap 通り pytest execution attestation を先にやる。
- 利点: 「テスト出力＝真実」の原理天井（本命 P0）を最速で塞ぐ。
- 欠点: 根治対象の現況は SF-022=Low（iter76 緩和済・脅威モデル内独立到達不能を実証）・SF-014=Major級非ブロッキング。対して High 2件が**3度目の繰延**で 1〜2 iter 分開いたままになる＝框架自身の重大度台帳と逆順。

### アプローチ C: 併合（1 iter で両方）

- 概要: SF-020/021 と attestation を同一 iter に混載。
- 利点: 総所要 iter 数が最小に見える。
- 欠点: S+M=L 化・テーマ混在で review/qa/security の焦点が割れる。iter76 brainstorm が同じ理由で明示的に却下した構成。

## 決定

- 採用アプローチ: **A（SF-020＋SF-021 先行）**（ユーザー承認 2026-07-26・AskUserQuestion）
- 採用理由: 重大度実態（High・OPEN・silent allow ×2 vs Low緩和済/非ブロッキング）とコスト（S vs M 1〜2 iter）の比で先行クローズが優位。SF-021 は事故到達（非敵対）経路すらある。
- 不採用理由: B=重大度逆順・3度目繰延。C=iter76 で却下済みのテーマ混在。

## スコープ境界

- やること: SF-020 残存分（raw 大文字直打ち: 破壊コマンド名＋redirect システムパス `/ETC` 等）の封鎖／SF-021（`_STAGE_BROAD_RE` の `add`→`(add|stage)` 拡張＋事実誤認コメント訂正）／両者の合成ケース（`GIT STAGE -A`）／TDD 旧赤・新緑の回帰 pin／moat 非弱体化確認。
- やらないこと: `git update-index` の追補（stage と異なり低レベル別挙動・台帳認定済み）／ANSI-C quoting・全角コマンドクラス（実測で無害と実証済み・pin 不要）／SF-019 構造化 argv・pytest execution attestation（→iter78）／denylist への新語彙追加。

## 未解決事項

- safe-target 早期 allow と大文字の交差（`RM -rf node_modules` を allow 維持か ask か）: plan の RED フェーズで実測して決定（どちらも安全側）。
- check-destructive.sh の raw grep サイト全列挙（:68 INPUT / :145 CMD / 再帰削除 grep 等）: plan で網羅列挙し漏れなく `-i` 化。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

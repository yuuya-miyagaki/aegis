# v1.5.1 grill 残余修正バッチ — review エビデンス（2026-06-11）

対象: grill 🟢残余 5 件（T1〜T5）＋版数 1.5.1（v1.5.0..HEAD、12 commits、27+ files）
出典: docs/specs/2026-06-11-grill-residual-fixes-design.md、docs/plans/2026-06-11-grill-residual-fixes-implementation-plan.md
方式: 2段グリル実装段（grill-code）。独立サブエージェント 2 本（A=既定モデル／B=sonnet）で差分全体を file:line 裏取り・再現コマンド付きで精査。

> 工程ノート: B は最初の 2 回が API ポリシーフィルタの誤反応（敵対的レビュー文言＋
> deny パターン読込の組合せと推定）で中断し、文言を中立化した sonnet 再実行で完走。
> A/B は互いの所見を見ていない（独立性維持）。

## レビュー結果

- **A**: 🔴0・🟡1・🟢5 → 条件付きマージ可（🟡-1 修正で可）
- **B**: 🔴0・🟡0・🟢1 → マージ可

修正条件は同セッションで充足済み（commit `4c52528`）。

| ID | 指摘 | 対応 |
|----|------|------|
| A 🟡-1 | `_AEGIS_TR_PRE` の `[;&|(]` クラスに裸の `(` が含まれ、クォート内グループ正規表現に衝突。`grep -E "(pytest|unittest)" missing.txt`（不一致時 rc=1）が test 実行と分類され、直前の実 green を覆す false-RED（judge 直呼びで `'red'` を実証）。T1 が潰したはずのクラスの残存 | **修正済み**（4c52528）。アンカーを `(^|[;&|]) *\(? *` に変更し、`(` は文字列先頭／`;&|` 区切り直後のみ有効。`(pytest)`・`cd app && (vitest run)` は一致維持、`grep -E "(pytest|…)"`・`grep "(vitest"` は不一致を fixture で固定（RED→GREEN） |
| A 🟢-1 | extract-input.sh の fidelity ルーティングクラスに `\/` 欠落（grep 経路がリテラル 2 文字で返す）。標準エンコーダ（json.dumps / JSON.stringify）は `\/` を出さず実到達なし、deny 系 hook は python3-first で独立 | コメントで除外理由を明記（4c52528） |
| A 🟢-2 | claim-mv 後 undo 前に contender がクラッシュすると pid なしロックが残留し回収対象外（fail-closed）。手動削除案内が受け皿 | 残余として v151-security.md に記録 |
| A 🟢-3 | ロック待機 10×0.2s=2s は update-gate 1 実行より短く、実競合の敗者は常に rc=1 終了（15 回レース実証）。「Retry shortly」案内どおり正しく fail | 残余として記録（自動リトライは非目標） |
| A 🟢-4 | `if ...; then pytest; fi`・`time`/`bash -c` 形は分類不一致（unverified=fail-closed 方向）。wrapper 形は README 記載済みだが then 形が未記載 | README Migration に制御構文形を追記（4c52528） |
| A 🟢-5 | `kill -0` の EPERM（他ユーザー所有 live を dead 誤判定） | 設計書 §T4 受容リスクに記録済み＝確認済み扱い |
| B 🟢-1 | 計画書の変更ファイルマップに `hooks/lib/extract-input.sh`（計画逸脱分）が未掲載 | マップに逸脱注記付きで追記（4c52528） |

## 仕様との整合性（両レビュー一致）

- T1〜T5 の全実装が設計書どおり。T5 の `-fprint0/-fprintf/-fls` 封鎖は設計 §T5(b) 記載済みで過剰実装ではない
- **計画逸脱 1 件（extract-input.sh の python3 fidelity ルーティング `\\[\\nrtbfu"]`）は両レビューが「正当かつ必要」と判定**: grep 経路は JSON の `\n` エスケープをリテラル 2 文字で返すため、改行入りコマンドが正規化契約に到達しない（計画の前提が誤り）。escaped-quote＋改行入りコマンドの e2e（実改行で記録→green 分類）で実証済み。python3 失敗時の grep フォールバックは記録系 fail-open として設計整合
- ミラー同一性: 変更 7 ファイル全て cmp でバイト同一（両レビュー実測）
- 版数整合 5 ファイル＋architecture-overview 履歴行＋README Migration: 確認済み
- テスト実効性: fixture 単一ソース（patterns.sh を source）で grep/re 両エンジン照合、構造テスト（ロック順序）・反転 fixture により各修正の revert は RED になる（バイパス green なし）

## 判定

**マージ可**（A の条件は充足済み、Critical 0）。最終状態: 461 tests OK・contract full/standard・drift・smoke・--strict 全 PASS（v151-qa.md 参照）。

# 納品サマリー — iteration 31 / Batch1（v1.11.0）

> 本タスクは Aegis フレームワーク自身の改善（ドッグフード由来）。「client」＝フレームワーク保守者。

## 何を作ったか（Batch1: 配布ブロッカー＝control-plane フック精度 + git baseline）

スタジオ・ナギ予約LP で v1.10.0 を Client→Dev 一周ドッグフードして見つかったハーネス自身の摩擦（OBS-001〜022）のうち、**配布ブロッカー 6 タスク**を修正:

1. **OBS-017** `bin/setup.sh` が新規 install に baseline commit（fresh のみ・既存リポ no-op）→ 初回 review ゲートが framework 由来 stub 🔴 を出さない。
2. **OBS-017** judge の stub 走査から control-plane dir を除外（自己マッチ封鎖）・secret 走査は全走査維持。
3. **OBS-018** 証拠記録スクリプトを control-plane allowlist 追加。
4. **OBS-017** bare `git add <dir>` staging を deny→ask（catch-22 解消）。
5. **OBS-003** 全 read-only パイプを allow。
6. **OBS-006** 書込み先 path のみ deny（mask＋redirect＋no-write コマンドのアロウリスト・cmdsub/改行は fail-closed）。

主要設計判断: write-target 判定は「**安全コマンドのアロウリスト**（echo/printf/git commit）」で行い、write ユーティリティのブロックリストは使わない（列挙漏れで漏れるため）。改行は `;` に正規化。

## 変更ファイル

- コード: `bin/setup.sh` / `scripts/build-judge-card.py` / `hooks/check-control-plane.sh`（＋ミラー `examples/minimal-project/`）。
- テスト: `tests/test_setup_baseline.py`（新）/ `test_judge_card.py` / `test_control_plane_allowlist.py`（新・40 ケース）。
- 版: 1.10.0→1.11.0（contract/template/example/live STATUS）。
- コミット: 52dff43〜6d1b938 ＋ review fix 76112bc/8f85a5b ＋ evidence/版。

## テスト・QA・セキュリティ結果（証拠参照）

- **review**（`docs/qa-reports/iter31-batch1-review.md`）: 3 ラウンド盲検 break-attempt。Batch1 由来 Critical 2 件（write-util ブロックリスト穴・改行バイパス）検出→修正。orig vs new で control-plane 書込み後退ゼロ実証。
- **qa**（`docs/qa-reports/iter31-batch1-qa.md`）: 機能対照表 全 PASS。B1 mutation drill は committed-code 構造制約で skip 宣言＋手動 4-mutant 実証（4/4 CAUGHT）。
- **security**（`docs/qa-reports/iter31-batch1-security.md`）: 1次（security）＋盲検2次とも approve_with_notes。新規 WRITE バイパス ゼロ・secret カバレッジ維持・fail-closed 堅持。
- **deploy**（`docs/qa-reports/iter31-batch1-deploy-checklist.md`）: 配布整合・後方互換確認、deploy blocker なし。
- 機械検査: full suite 830 passed/1 skip・REDTEAM 18/18＋5/5・contract 全 profile・drift・mirror・scaffold smoke・distribution 全 PASS。

## 残留リスク・既知の制限

- **SF-001（Critical・pre-existing・deploy blocker 非該当）**: control-plane 判定がシェルの word-splitting/パス解決を再現せずリテラル `hooks/` 一致に依存＝quote 分割（`hooks""/`）・backslash（`hooks\/`）・bare-dir（`find hooks -exec rm`）で moat バイパス。**変更前 8f8eb2d でも同一挙動＝Batch1 後退ではない。** `docs/security-followups.md` SF-001 に durable 記録＝**最優先 follow-up**（繰延合意）。
- 残実装: Batch2（skill/契約/配布整合 5）＋Batch3（Client 書込み 2）＋X.1/X.2 は iteration 32 へ。

## 運用上の注意

- 既存 install は `bin/setup.sh` 再実行で改善版 hook に更新される。setup baseline commit は加算的（既存リポ no-op）。
- ロールバック: Batch1 コミットの revert で完全復元（状態移行なし）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- **MANUAL: 生成せず** — エンドユーザー製品ではなくフレームワーク（利用者＝保守者自身）。
- **RUNBOOK: 生成せず** — 運用者なし（CI 相当は contract/drift の機械検査）。
- **UAT: 生成せず** — `docs/requirements/ACCEPTANCE.md` 不在（受入基準なし）。

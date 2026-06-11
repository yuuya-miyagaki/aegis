# v1.5.2 残余全消化バッチ — review エビデンス（2026-06-11）

対象: v151-security.md 記録の残余リスク 5 系統（T1〜T5）＋版数 1.5.2（v1.5.1..HEAD、9 commits）
出典: docs/specs/2026-06-11-v152-residual-elimination-design.md、docs/plans/2026-06-11-v152-residual-elimination-implementation-plan.md
方式: 2段グリル実装段（grill-code）。独立サブエージェント 2 本（A/B とも opus・互いの所見を見ない）で差分全体を file:line 裏取り・PoC 付きで精査。

## レビュー結果

- **A**: 🔴0・🟡1・🟢3 → 条件付きマージ可（🟡 J1 修正で可）
- **B**: 🔴0・🟡0・🟢3 → マージ可

修正条件は同セッションで充足済み（commit `b79184a`）。

| ID | 指摘 | 対応 |
|----|------|------|
| A 🟡 J1 | マスクの「Q 置換」を production 消費者からピン留めするテストが不在。`build-judge-card.py` の `sp.sub("Q", cmd)` を `sp.sub("", cmd)`（削除）へ変異させても全 58 テストが GREEN のまま通り、`'"echo" pytest'` 注入で silent-green 成立（PoC 実証付き）。v1.5.1 grill A red-1 と同型の再混入余地 | **修正済み**（b79184a）。`test_mask_is_substitution_not_deletion` を新設: `'"echo" pytest'`（ok）のみを evidence 注入し `unverified` を直接 assert。削除変異下で RED・正実装で GREEN を両方向実走で証明（mutation killer） |
| A 🟢 J2 | O_EXCL 採用の age-gate コメントが「どの操作が dir mtime を refresh するか」「テストが touch -t で年齢を偽装する接触順序」を暗黙にしている | コメントに明示（b79184a）: mkdir 自体・pid 書込・claim 作成/削除が各々 mtime を reset、テストはエントリ追加**後**に touch -t |
| A 🟢 J3 | 待機 50 ループの構造ピン（`for _ in {1..50}; do` の文字列一致）が同値リファクタで RED になる脆さ | **不採用（理由付き記録）**: 構造ピンの RED は可視的な fail-closed であり silent ではない。挙動契約は `test_live_contention_both_succeed`（10s 窓内の両成功）が併存し、構造＋挙動の二重ピンは v1.5.1 のロック順序テストと同方針 |
| A 🟢 J4 | `-mmin +1` の floor 切り上げ（実効 >2 分）の裏取り | レビュー側で BSD/GNU 共通動作を実証済み＝指摘なし（確認のみ） |
| B 🟢 G-1 | STRIP パターン本数を将来変える際、`build-judge-card.py` の `len(strips) != 2` ガードの同時更新を忘れる余地 | patterns.sh の STRIP コメントにリマインダ 1 文を追記（b79184a）。テスト側も `assertEqual(len, 2)` で本数を契約化済み |
| B 🟢 G-2 | orphan-claim 復元 / dead-pid 回収の `kill -0` は PID 再利用に脆弱 | 受容済み残余として v152-security.md に記録（単一ユーザー運用前提・設計書どおり） |
| B 🟢 G-3 | `_claim`/`_claimer` がループ外スコープにリーク（スクリプト直下のため `local` 不可） | 記録のみ（同スクリプト内に再利用変数なし・実害なし） |

## レビューの検証メソッド（両者の独立実証）

- **B**: T1a/T1b/T2/T4a/T4b の各実装を一時 revert → 該当テストが RED に倒れることを実証（自己複製テストでないことの確認）。マスク後コマンドへのプロモーション攻撃（`Q pytest`／`foo=Q pytest`／`Q; pytest`／`Qpytest`）を sed + grep -E / python re 両エンジンで実走し green 偽装ベクトルなし。deny 系 hook 3 本に `AEGIS_TR_STRIP` 参照ゼロ＋`git reset --hard HEAD` の従来 ask 維持を実走確認。`( set -C; > )` の noclobber 原子性を bash 3.2 実機確認
- **A**: 実装ミューテーション探索で J1 を検出（削除変異の素通し＋forge 成立 PoC）。`((vitest))`／12+ クォート組合せ／多段 env 代入／wrapper 形での silent-green 探索 → production の Q 置換下で全て期待どおり。evidence-log raw fidelity（マスクは reader 側のみ）・trap 二重設定なし・JSON escape クラス `\\[\\nrtbfu"/]` の spec 全カバーを確認
- 両者: ミラー 5 ファイル diff で byte 同一を実測

## 仕様との整合性（両レビュー一致）

- T1〜T5 の全実装が設計書どおり（マスク=置換・deny 不波及・fail-closed への倒し・O_EXCL 採用の年齢ゲート・待機 10s）
- T5 の light ゲート競合挙動変化（敗者も自己取得して rc=0）は設計書記載の意図的変更。heavy ゲート（qa/security の事前承認要求）は rc=1 維持
- 受容済み残余（PID 再利用・SIGSTOP >2 分横断・混在クォート横断）は設計書側で明示済み

## 判定

**マージ可**（A の条件 J1 は b79184a で充足、Critical 0）。最終状態: 479 tests OK・contract full/standard・drift・smoke・--strict 全 PASS（v152-qa.md 参照）。

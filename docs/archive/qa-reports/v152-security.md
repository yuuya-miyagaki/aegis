# v1.5.2 残余全消化バッチ — security エビデンス（2026-06-11）

## 位置づけ

v151-security.md「残余リスク（今回記録）」5 系統の解消バッチ。**v151 記録の残余は本バッチで全て対処済み**:
クォート内ランナー言及の false-RED（T1）、入れ子サブシェル `((pytest))` 不分類（T2）、
`\/` エスケープの fast-path 非ルーティング（T3）、claim-mv 窓の pid なしロック残留（T4）、
ロック待機 2s の実競合敗者 rc=1（T5）。

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| T1: クォート span の Q 置換マスク（分類前処理） | 誤判定根治（fail-closed 維持） | `grep -E "(unittest\|pytest)" f`（rc≠0）等のクォート内言及がランナー分類へ到達しない＝false-RED 根治。**置換であって削除ではない**（削除は `'"echo" pytest'`→`' pytest'` の green 偽装経路）。mutation-killer テスト（b79184a）が production 消費者で置換を直接ピン留め ✅ |
| T1 境界: マスクは分類専用 | fail-open 防止の契約化 | deny 系 hook 3 本（check-destructive / check-control-plane / check-secrets）への波及は quote-wrapping バイパス＝fail-open になるため禁止。`TestMaskScopeBoundary` が参照ゼロを契約化、grill B が `git reset --hard HEAD` の従来 ask 維持を実走確認 ✅ |
| T1 ガード: `len(strips) != 2 → unverified` | fail-closed | patterns.sh 破損・旧版時は判定不能へ倒す（green/red を返さない）。STRIP 本数変更時の同時更新リマインダをコメント契約化 ✅ |
| T2: 入れ子 `(` アンカー `(\( *)*` | 分類精度（fail-closed 方向） | `((pytest))`・`( (vitest run))` を分類、`grep "(pytest x`（不正クォート）は不一致維持。アンカーはマスク不能な不正入力への defense-in-depth ✅ |
| T3: `\/` の fidelity ルーティング | 強化（記録忠実度） | ルーティングクラスを `\\[\\nrtbfu"/]` に拡張し JSON spec の全 escape をカバー。deny 系は python3-first で独立・影響なし ✅ |
| T4a: 孤児 claim 復元（dead claimer 限定 mv） | 可用性＋fail-closed | claim-mv 後 undo 前クラッシュの残留を、claimer 死亡確認後にのみ `mv claim → pid` で復元。live claimer・非数値は不介入 ✅ |
| T4b: pid なしロックの O_EXCL 採用 | 可用性＋原子性 | 年齢ゲート（`-mmin +1`＝実効 >2 分、BSD/GNU 共通）通過後に `set -C`（noclobber）で原子採用＝kernel が単一勝者を選ぶ。**削除はしない**（check-then-act の rm は新 live 勝者のロック破壊、grill-plan A red-2 で再現済み）。既存の空/garbage pid は構造的に採用不能＝手動削除のまま fail-closed ✅ |
| T5: 待機窓 50×0.2s=10s | 可用性（意図的仕様変更） | light ゲートの実競合で敗者が待機後に自己取得し両者 rc=0（15 回ドリルで gate 値整合・torn write ゼロ）。heavy ゲート（qa/security の前提ゲート未承認）は従来どおり rc=1 ✅ |

## 受容済みリスク（設計上の明示トレードオフ、今回記録）

- **混在クォートの横断マスク**: `echo 'a"b'; pytest "x"` は DQ→SQ の固定順マスクで `"…"` span が `'` を跨ぎ、実 pytest がマスクに巻き込まれて不分類＝unverified 方向（green 偽装には使えない）。fixture `("echo 'a\"b'; pytest \"x\"", False)` で挙動を固定・文書化。回復は実テスト再実行か record-test-result.py
- **SIGSTOP >2 分の病的窓**: 元の保持者が mkdir→pid 書込の間で SIGSTOP され 2 分超停止すると、O_EXCL 採用者と交差し得る（単一ユーザー運用で実発生は病的ケースのみ。設計書 §T4 記載）
- **PID 再利用**: `kill -0` の生死判定は PID 再利用に脆弱（grill B G-2。単一ユーザー運用前提・設計書どおり）
- `kill -0` の EPERM dead 誤判定（v1.5.1 から継続、単一ユーザー運用前提）
- wrapper/制御構文形（`time pytest`・`if …; then pytest; fi`）の不分類＝unverified 方向（v1.5.1 から継続、README Migration 記載）

## 残余リスク

新規の fail-open 方向の残余なし。上記受容済みリスクはいずれも unverified／可用性方向（green 偽装・deny バイパスには使えない）。

## 検証

- green 偽装探索: grill A がミューテーション＋12+ クォート組合せ・多段 env 代入・wrapper 形で、grill B がプロモーション攻撃（`Q pytest`／`Q; pytest` 等）と revert 検証で、それぞれ独立に「偽装ベクトルなし」を実証
- バイパス回帰: deny 系 13 形（v1.3.3）＋T5a/T5b（v1.5.1）の deny/allow は既存テストで維持（479 tests OK に包含）
- 479 tests OK / contract full+standard PASS / drift PASS / scaffold smoke 3 プロファイル PASS / check_status --strict PASS

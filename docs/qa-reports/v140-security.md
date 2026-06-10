# v1.4.0 fix batch — security エビデンス（2026-06-10）

## 脅威モデル

本バッチの security 観点は2軸: (1) moat hook の防御強度を落とさないこと（過剰 deny の解消や可用性修正が deny→allow 反転を生まない）、(2) silent fail-open 経路の封鎖（F6 教訓の継続）。

## 防御強度の変化点と評価

| 変更 | 方向 | 評価 |
|------|------|------|
| check-secrets: PEM/SSH 鍵・credentials.json・service-account.json の staging deny＋broad staging（`git add -A`/`.`）時のリポジトリ走査 | 強化 | 新規 deny 形。安全変種（.env.example 等）は維持 ✅ |
| check-deploy-gate / mcp: RC 契約（0=allow / 2＋`ASK:`=ask / その他=deny）。RC=2 でもマーカー無しは deny | 強化 | interpreter 故障が ask に化けない。size-skip（S/M）は無検査 allow→ask へ是正 ✅ |
| check-control-plane: WRITE_INDICATORS 語境界化 | 可用性 | 誤 deny の解消。緩和方向の変化は語の右境界のみで、deny→allow 反転形はテストで不検出 ✅ |
| check-task-completed: python3 不在＝差し戻し（exit 2）化 | 強化 | 完了証跡を検証できない状態で完了を認証しない（fail-closed）✅ |
| update-gate: mkdir 排他ロック＋単一パス書込 | 強化 | 並行更新による STATUS 破損・中間状態観測を排除。stale lock は fail-closed＋手動除去ガイダンス ✅ |
| hooks 参照 `"${CLAUDE_PROJECT_DIR:-.}"` 化（grill 🟡-2） | 強化 | 変数未設定→exit 127→moat 全 hook silent fail-open の経路を封鎖。cwd 相対へのフォールバックは v1.3.3 以前と同等の保証水準 ✅ |
| fail-open/closed ポリシー表（docs/hook-failure-policy.md） | 可視化 | 16 hook の宣言をテストが実発火突合。「宣言なき fail-open」の構造的排除 ✅ |

## 残余リスク（記録）

- CLAUDE_PROJECT_DIR フォールバックの cwd 相対形は、サブディレクトリ起動時に hook 不在→ runtime の非ブロッキングエラー（v1.3.3 以前と同じ水準。正規経路は常に変数設定済み）
- check-control-plane: `truncate -s` / `dd of=` のシェル形は WRITE_INDICATORS 外（既存残穴、v1.3.3 以前から不検出。次バッチ候補として grill 🟢 に記録）
- stale lock の自動回収なし（fail-closed 側なので防御は劣化しない）

## 検証

- 全 hook の python3 遮断実発火が宣言（moat=fail-closed / advisory=fail-open）と一致: test_failure_policy.py PASS
- 未設定 CLAUDE_PROJECT_DIR での hook 実発火で block 判定を確認（fail-open しない）
- 389 tests OK / contract PASS / drift PASS / scaffold smoke 3 プロファイル PASS（v140-qa.md 参照）

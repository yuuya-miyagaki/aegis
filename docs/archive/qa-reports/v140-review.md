# v1.4.0 fix batch — review エビデンス（2026-06-10）

対象: 進化レビュー P2-1〜P2-6・P3-1〜P3-6・K-2・fail-open/closed ポリシー表・B1 ドリル恒久修正（T0〜T16、b815d22..HEAD）
出典: docs/evolution-review-2026-06-10.md §4/§6、計画 docs/plans/2026-06-10-v140-fix-batch-implementation-plan.md
方式: 2段グリル実装段（grill-code）。差分全体（17 commits, 49 files, +2592/−142）を file:line 裏取り付きで精査。

## レビュー結果

判定: **マージ可**（Critical ゼロ）。🟡 2件は同セッションで修正済み:

| ID | 指摘 | 対応 |
|----|------|------|
| 🟡-1 | tests/test_mirror_identity.py が fixture 専用で実リポジトリの mirror 状態を未検証。T16 で scripts/ ミラー2件の drift が 383 tests GREEN をすり抜け、リリース証跡採取時の check_reference_drift.py で初検出 | **修正済み**（f18ebb7）。`check_mirror_identity(ROOT)` を実リポジトリへ適用するテストを追加。ミラー摂動で RED を実証→復元で GREEN |
| 🟡-2 | hooks.template.json の `"$CLAUDE_PROJECT_DIR"/hooks/` 形は変数未設定時に `bash ""/hooks/x.sh`→exit 127→moat 全 hook が silent fail-open（F6 と同型）。example settings.json は cwd 相対のまま残存 | **修正済み**（7e7d6af, c3e007a）。`"${CLAUDE_PROJECT_DIR:-.}"` フォールバック形へ統一（template 16 + example 16 コマンド）。形式は test_hook_required_coverage の新テスト 5 件で固定。未設定環境での実発火を実証（block 判定が返る＝hook 生存）。contract validator の参照解決も両形対応（`script_rel_from_command` ヘルパー） |

🟢（任意・未対応で記録）:

- check-deploy-gate.sh:58 の `2>&1` で stderr 警告が ask 文面に混入し得る（ASK 検出自体は行頭一致で安全）
- update-gate.sh の CURRENT 読みがロック前（TOCTOU）— 書込は直列化済みで表示ログのみ影響
- kill -9 での stale lock は fail-closed 固着（手動除去ガイダンスあり）。PID 自動回収は将来候補
- check-control-plane WRITE_INDICATORS の左境界なし（誤 deny 方向＝保守的で許容）と `truncate`/`dd` シェル形の既存残穴

## 仕様との整合性

計画 T0〜T16 全項目に対応実装を確認（対応表は会話レビュー参照）。仕様外の追加は T7/T8 テスト fixture の scripts symlink（deny がファイル不在の偶然で通っていた潜在欠陥の是正）のみで、必要と判断。

## よく書けている点

- docs/hook-failure-policy.md ＋ test_failure_policy.py: 宣言表をテストがパースし python3 遮断下で実発火突合（表の陳腐化＝即 FAIL の self-verifying doc）
- check-deploy-gate.sh:61 の RC=2＋ASK マーカー二重判定: interpreter 故障が ask に化けない
- update-gate.sh:214-222 の単一パス書込: gate 値と ref null 化が 1 write、並行読者が中間状態を観測しない

# Hook Failure Policy（fail-open / fail-closed 宣言）

宣言の単一ソース。`tests/test_failure_policy.py` が本表をパースし、
各 hook を python3 遮断環境で実発火して宣言と突合する（表の陳腐化＝テスト FAIL）。

- **moat** = ゲート・破壊防止・秘密・完了強制。依存（python3）不在時は fail-closed。
- **advisory** = 可視化・補助。依存不在時は fail-open（セッションを止めない）。
- 入力パース失敗時は全 hook allow（入力不明では誤 deny を避ける）。
- 依存=なし の hook は pure-bash 宣言: python3 遮断下でも通常判定が機能すること。

| hook | 分類 | python3 依存 | python3 不在時 | 入力パース失敗時 |
| --- | --- | --- | --- | --- |
| check-gate.sh | moat | なし | 通常判定 | allow |
| check-tdd.sh | moat | なし | 通常判定 | allow |
| check-client-info.sh | moat | なし | 通常判定 | allow |
| check-destructive.sh | moat | なし | 通常判定 | allow |
| check-secrets.sh | moat | なし | 通常判定 | allow |
| check-deploy-gate.sh | moat | あり | deny | allow |
| check-deploy-mcp-gate.sh | moat | あり | deny | —（※2） |
| check-skill-gate.sh | moat | あり | ask | allow |
| check-cron-gate.sh | moat | あり | ask | allow |
| check-control-plane.sh | moat | あり | deny（raw fallback） | —（※1） |
| check-task-created.sh | moat | あり | hard stop（placeholder subject で判定続行） | allow |
| check-task-completed.sh | moat | あり | 差し戻し（exit 2） | allow |
| post-bash.sh | advisory | なし | 通常動作 | allow |
| post-bash-observe.sh | advisory | なし | 通常動作 | allow |
| post-status-audit.sh | advisory | あり | allow | allow |
| pre-compact.sh | advisory | なし | 通常動作 | allow（※3） |
| session-start.sh | advisory | あり | allow（劣化表示） | allow |

※1 check-control-plane は入力パース失敗時に raw input へフォールバックし、
control plane 言及があれば deny（fail-closed）。言及がなければ allow。

※2 check-deploy-mcp-gate は stdin を参照しない（matcher 登録で対象 MCP tool に
限定済みのため）。「入力パース失敗」という状態が存在せず、判定は常に
`check_status.py --check-deploy-ready` の結果に従う。

※3 pre-compact の stale 判定は入力非依存（STATUS.md の mtime のみ参照）。
パース失敗でも鮮度判定はそのまま機能する＝STATUS が新しければ allow。

## size-skip（task_size S/M の deploy）

`check_status.py --check-deploy-ready` は S/M（deploy フェーズなし）のとき
RC=2＋stdout 先頭 `ASK:` を返し、check-deploy-gate / check-deploy-mcp-gate は
これを **ask**（人間確認）にマップする（観察4: skip＝無検査許可の是正）。
RC=2 でも `ASK:` マーカーが無い出力は deny に倒す（interpreter 異常系の混同防止）。

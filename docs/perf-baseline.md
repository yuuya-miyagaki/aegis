# Hook Performance Baseline

Hook 起動 latency の実測値と、ここから導出する `timeout` 値の根拠。

## 計測方法

- scaffold: クリーン install (`bin/setup.sh --profile=full --target=/tmp/perf-test`)
- payload: `{"tool_name":"Bash","tool_input":{"command":"ls -la"}}`
- 10 回平均 (cold + warm 混在)
- 環境: macOS Darwin 25.0.0, bash 3.2, python3 3.9.6
- 計測日: 2026-06-13 (v1.6.2)

## 実測値（10 回平均 ms/call）

| Hook | 実測 (ms) | 90 パーセンタイル × 安全係数 5 (ms) | 割当 timeout (s) |
| --- | --- | --- | --- |
| check-control-plane.sh | 49.2 | ~250 | **30** |
| check-secrets.sh | 32.6 | ~165 | **60** ※find 想定 |
| check-destructive.sh | 43.7 | ~220 | **30** |
| check-gate.sh | 43.8 | ~220 | **30** |
| check-task-completed.sh | 41.5 | ~210 | **30** |
| check-task-created.sh | 41.1 | ~210 | **30** |

## 割当 timeout の判断

- **下限 5s / 上限 60s** という第6回 Phase A 検討範囲の上限・下限内
- **30s 既定**: 実測の **100 倍以上**の余裕。10 万ファイル monorepo / network mount / CI で I/O 遅延が出てもブロックしない設計
- **check-secrets.sh のみ 60s**: `find $ROOT -name '.env*'` が支配的な経路。大規模 monorepo（10 万 file 想定）で 30s 不足のリスクを避ける
- **判断ルール**: 「ベース計測 × 1000 倍 を上限の目安にし、 60s を超えるなら設計を見直す」

## 観測値（参考）

- bash 起動 baseline ≒ 30ms (空 hook の bash 起動コスト)
- 各 hook の lib source（emit.sh + extract-input.sh + secrets-patterns.sh）累積 ≒ 15-20ms
- python3 fallback 経路（extract-input.sh）≒ 60ms 加算

## 将来の更新条件

次のいずれかが発生したらこの表を再計測すること：

1. 新規 deny / advisory hook の追加
2. `hooks/lib/*.sh` の同等性関数（emit / extract-input / patterns）の本質変更
3. profile 構成変更（minimal/standard/full の hook 数差）
4. python3 互換層の刷新

## 関連 Task

- K-6 (v1.6.2 Task 3): hook timeout 宣言 — 本表で割当 timeout を決定
- K-14 (v1.7): PostToolUse Bash 400ms/call の fingerprint cache — PERF-1 で別計測

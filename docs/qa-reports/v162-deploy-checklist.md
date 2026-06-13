# v1.6.2 deploy チェックリスト（2026-06-13）

## デプロイ形態

aegis はフレームワーク本体（distribution）。CI/CD やランタイムサービスはない。「deploy」は **tag 付与＋origin push** を指す。

## デプロイ対象

| 項目 | 状態 |
| --- | --- |
| `FRAMEWORK_VERSION` | `scripts/check_framework_contract.py:17` → `"1.6.2"` |
| `templates/STATUS.template.md:3` | `framework_version: "1.6.2"` |
| `docs/STATUS.md:3` | `framework_version: "1.6.2"` |
| `examples/minimal-project/docs/STATUS.md:3` | `framework_version: "1.6.2"` |
| tag | **`v1.6.2`** を `HEAD`（本リリースの最後の commit）に打つ |

## 事前検査

| 検査 | 結果 |
| --- | --- |
| `python3 scripts/check_framework_contract.py --profile=full --strict` | PASS |
| `python3 scripts/check_reference_drift.py` | PASS |
| `python3 scripts/eval_scaffold_smoke.py` | PASS |
| `python3 -m unittest discover tests -p "test_*.py"` | OK 683（skipped=1） |
| `bash tests/poc/v162-redteam-rerun.sh` | 18/18 PASS |
| `git status` クリーン | 確認（commit `4897c6b` 後） |

## Notable behavior change（v1.6.1 → v1.6.2）

ユーザに事前周知すべき挙動変化（patch だが behavioral change）：

1. **`bin/setup.sh` を既存 `.claude/settings.local.json` がある target で再実行すると `settings.local.json.bak.<unix-ts>` が作られる**（K-8 / DIST-01）
   - 以前は無条件上書きしていた → ユーザの `permissions.allow` 等が消えていた
   - v1.6.2 からは hooks 以外の top-level key（permissions / env / 未知 key）は保存され、ファイル全体は `.bak.<ts>` で退避される
   - 必要に応じて `.bak.<ts>` から手動で復元できる

2. **`bin/setup.sh` 実行で `python3` を smoke run（`python3 -c 'print("ok")'`）し、失敗で abort**（K-10 / DIST-03）
   - 偽 python3 stub（exit 127）を PATH 先頭に置いた状態で setup を走らせていた極めて稀なシナリオで挙動変化
   - 正常な python3 環境では影響なし

3. **`--target=<framework_root>` で framework 自身に install しようとすると abort**（DIST-12 前倒し）
   - 通常の利用では発生しない

4. **`.claude/.aegis-install-version` が install 時に書かれる**（K-11 / DIST-04）
   - 新規ファイル。既存 `.gitignore` に追加推奨（profile によって setup.sh が自動追加するかは別途検討）

## tag / push 手順

```bash
cd /Users/miyagakiyuuya/Desktop/personal/superpowers-gstack-antigravitykit-urtorapowers/aegis

# 1. 最終確認
python3 scripts/check_framework_contract.py --profile=full --strict
python3 scripts/check_reference_drift.py
bash tests/poc/v162-redteam-rerun.sh   # 18/18 PASS であること

# 2. tag を打つ
git tag -a v1.6.2 -m "v1.6.2 — full-review fix-forward (K-1〜K-13 + grill-code Critical)"

# 3. push（main + tag）
git push origin main
git push origin v1.6.2
```

## ロールバック手順

万一の場合：

```bash
# tag を削除
git tag -d v1.6.2
git push --delete origin v1.6.2

# main を 2ac5eb6（v1.6.1 リリース時点）に戻す
git reset --hard 2ac5eb6
git push --force-with-lease origin main
```

ただし v1.6.2 の影響は **配布物（setup.sh / hook / lib）と framework_version 表示のみ**で、既存ユーザの runtime には ROAD-back のリスクは低い（v1.6.1 設定で生成された install は v1.6.2 lib にアップグレードしないと壊れない）。

## 結論

🟡 マージ可（ack で承認）。v1.6.2 リリースの artifact 整合性は契約 + drift + smoke + 18 PoC で確認済み。

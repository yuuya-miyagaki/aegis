# v1.6.2 security エビデンス（2026-06-13）

## 位置づけ

第6回全力レビュー（`docs/full-review-2026-06-13.md`）の **🔴 Critical 16 件** のうち、**機械側 moat 関連の K-1〜K-7 + 配布パス K-8〜K-11** を fix-forward した v1.6.2 patch リリースの security エビデンス。grill-plan / grill-code 独立 2 本の指摘もすべて反映済み。

## Critical 修正サマリ

| # | Finding | 攻撃 PoC（防御前） | v1.6.2 防御 | Commit |
| --- | --- | --- | --- | --- |
| K-1 | REDTEAM-01 | `echo "===== 3 passed ====="; pytest -k __NEVER__` で judge 🟢 | 3 軸独立判定（出力 zero-run / pytest exit 5 / プロローグ欠落）で `marker_verified=false` | `cd51ded` + `4897c6b` |
| K-2 | REDTEAM-02 | `> "$(echo hooks)/lib/emit.sh"` → emit.sh 上書き | Path B（全 redirect の write-target で cmdsub 検出）+ Path C（printf -v / read / eval / declare / local 代替 assignment） | `4a27870` + `4897c6b` |
| K-3 | REDTEAM-03 | `F=.env; git add "${F}"` で `.env` ステージ | クォート任意化（`["'\\]?` を変数参照前に許可） | `4a27870` |
| K-4 | REDTEAM-04 | `$(echo git) add .env` で git 検出 regex を完全迂回 | cmdsub/backtick + word-boundary `.env`/AEGIS_HIGH_RISK_RE → ASK（safe variant 事前 strip） | `4a27870` |
| K-5 | F-01 | `hooks/lib/emit.sh` 欠落で全 deny hook が exit 1 + 空 stdout → Claude Code fail-open | `hooks/lib/safety.sh` + 全 deny hook 冒頭の SHA256 一致 fallback ブロックで明示 deny | `f56fd8b` |
| K-6 | F-02 | hook timeout 未宣言 → native 既定打ち切りで exit 124/137 → fail-open | `templates/hooks.template.json` の全 PreToolUse hook に timeout（30s 既定 / check-secrets 60s、`docs/perf-baseline.md` で根拠） | `f56fd8b` |
| K-7 | F-03 | snapshot 部分書き込みでタンパー検出 `[ -n "$OLD_PHASE" ]` ガード bypass | atomic 化（tmp → mv 3 箇所同時） + consumer policy（snapshot 不在 = 初回 allowance + audit-skip.log、欠落フィールド = `emit_block`） | `f56fd8b` |
| K-8 | DIST-01 | `bin/setup.sh` が `settings.local.json` を無条件上書き → permissions.allow 等消失 | hooks 以外の全 top-level key を保存（`permissions` / `env` / 未知 key）+ `.bak.<ts>` 退避 | `66e59e8` |
| K-9 | DIST-02 | upgrade で旧 `hooks/lib/emit.sh` が `SKIP (exists)` 残留 → exit 127 fail-open（F6 同型 2 例目） | `copy_file_force` で framework-owned libs を強制上書き | `66e59e8` |
| K-10 | DIST-03 | python3 不在で `parse_json_array` が無音失敗 → "Setup complete." EXIT=0 / 0 ファイル install | setup 冒頭で `_aegis_require_cmd python3` + smoke run（`python3 -c 'print("ok")'`）で exit 127 stub を弾く | `66e59e8` |
| K-11 | DIST-04 | framework_version stamp 不在で版差分が見えない | install 時に `.claude/.aegis-install-version` を書き、`status_doctor` D5 で差分検出（注: 🟡 — install 先で `check_framework_contract.py` 不在のため真の drift 検出は v1.7 で改善予定） | `66e59e8` |
| K-12 | JNY-07 | full profile が PRD/SCOPE/NFR を配らず `client_ready_for_dev` は要求 | `scripts/_artifact_template_map.py` 単一所有 + 17 テンプレを full profile recommended に追加 + parity test 4 件 | `bd3f117` |
| K-13 | JNY-12 | 🟡 ack 判断基準が cheatsheet に無く、人間側で moat 無効化 | `docs/onboarding/03-cheatsheet.md` に 「ack していい例／ダメな例」4 行表 | `bd3f117` |

## 同時消化（v1.7 計画から前倒し）

| # | 対象 | 理由 | Commit |
| --- | --- | --- | --- |
| S-1 / REDTEAM-05 | `secrets-patterns.sh` / `phase-skills.sh` の profile required 不在 | F6 / K-5 と同 surface のため一気に消化 | `f56fd8b` |
| DIST-12 | `--target=<framework_root>` 自己 install | setup.sh 冒頭の引数検証同一場所 | `66e59e8` |

## 追加 PoC ハーネス

`tests/poc/v162-redteam-rerun.sh` で **18/18 PASS**:

- REDTEAM-01（K-1 forge）
- REDTEAM-01b（K-1 head+tail 抽出: 大規模 verbose 出力でプロローグ保持）
- REDTEAM-02（K-2 cmdsub / 代替 assignment 6 種）
- REDTEAM-02b（K-2 多段 redirect bypass 3 種、grill-code Critical 1）
- REDTEAM-03（K-3 quoted var 3 種）
- REDTEAM-04（K-4 cmdsub-built git 3 種）
- F-01（K-5 lib 欠落で fail-closed）

## grill-code レビュー反映

| 重大度 | 指摘 | 対処 |
| --- | --- | --- |
| 🔴 Critical 1 | `check-control-plane.sh:121-127` Path B が 1 番目の `>` のみ走査 | `grep -oE '>>?[[:space:]]*[^\|&;]*'` で全 redirect 走査に修正、新規テスト 3 件 |
| 🔴 Critical 2 | `evidence.sh` output tail 4 KiB のみ→大規模 pytest でプロローグ欠落 | head[:4096] + tail[-4096:] の二箇所抽出に修正、新規テスト 1 件（8KiB+ fixture） |
| 🟡 3 | `status_doctor d5` が install 先で dead-code | v1.6.3 / v1.7 で profile に `check_framework_contract.py` 追加 or stamp 比較ロジック改善 |
| 🟡 4 | `settings.local.json` shallow merge | 現状 framework は nested default を持たないため実害なし、v1.7 で deep merge |
| 🟡 5 | PoC harness が grill 派生をカバーしていなかった | 修正コミットで REDTEAM-01b / 02b 追加（18/18 PASS） |
| 🟢 6-8 | cheatsheet 「30 行」数値 / K-4 read-only ASK / safety.sh set+e | v1.7 nice-to-have で対処 |

## 受容済み残余

- 🟡 K-11 D5 dead-code（v1.7 で本格対処）
- 🟡 K-8 shallow merge（framework が nested default を導入するまで実害なし）
- pre-existing flake `test_python3_absent_advisory_hooks_do_not_crash`（順序依存、v1.6.1 でも発生、v1.7 で根本対処）

## 結論

🟡 マージ可（ack で承認）。Critical 16 件中 13 件（K-1〜K-13）+ grill-code Critical 2 件をすべて修正。残 K-14〜K-16（パフォーマンス / README 導線）は v1.7 へ送り。

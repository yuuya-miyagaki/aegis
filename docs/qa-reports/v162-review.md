# v1.6.2 review エビデンス（2026-06-13）

## レビュー実施

第6回全力レビュー（`docs/full-review-2026-06-13.md`、Phase A 敵対バイパス再 PoC + Phase C1〜C5 未踏軸 並列 6 サブエージェント）の結果と grill-plan + grill-code 独立 2 本を経て、v1.6.2 にすべての Critical を反映済み。本ファイルは review-gate の根拠を集約する。

## レビュー履歴

### 1. 全力レビュー（6 軸並列）

- charter: `docs/full-review-charter-2026-06-13.md`
- レポート: `docs/full-review-2026-06-13.md`
- Phase A（v1.6.1 修正 13 コミットの red-team 再 PoC）+ Phase C1〜C5（障害モード／パフォーマンス／配布パス／競合比較／非エンジニア E2E ジャーニー）の 6 サブエージェント並列で **🔴 Critical 16 件 + 🟡 Should fix 23 件 + 🟢 Nice 12 件** を抽出
- 結論: 「修正後マージ → v1.7 で構造強化」

### 2. plan 作成と grill-plan

- 計画書: `docs/plans/2026-06-13-v162-improvement-plan.md`
- 7 task（K-1〜K-13 を機能群でまとめ、Task 1 → 2 → 3 → 4 → 5 → 6 → 7 の依存順）
- grill-plan で **致命 5 件 + 要検討 5 件 + YAGNI 3 件** を抽出し計画 v2 に反映済み
  - 致命 1: K-1 zero-run 単軸検出は `2>/dev/null` で迂回可 → 3 軸独立判定（出力 / exit_code / プロローグ）
  - 致命 2: safety.sh 自身が profile required に未登録（REDTEAM-05 / S-1 再発）→ 同時消化
  - 致命 3: ミラー同期義務の暗黙化 → Section 0.1 で明示
  - 致命 4: K-12 stem 抽出マッピング破綻 → 明示 ARTIFACT_TO_TEMPLATE dict
  - 致命 5: safety.sh fallback 6 hook 重複 drift → SHA256 一致契約

### 3. 実装（7 task + 9 コミット）

| Task | コミット | 主な成果 | 新規テスト |
| --- | --- | --- | --- |
| Task 1 (K-1) | `cd51ded` | 3 軸独立判定（出力 / pytest exit 5 / プロローグ欠落） | `test_test_marker_zero_run.py` 11 件 |
| Task 2 (K-2/3/4) | `4a27870` | cmdsub / quoted-var / 代替 assignment を fail-closed | `test_secrets_quoted_var_and_cmdsub.py` 16 件 + 既存 13 件追加 |
| Task 3 (K-5/6/7) + S-1 前倒し | `f56fd8b` | safety.sh + identity 契約 + atomic snapshot + consumer policy + timeout 宣言 + profile required 登録 | 6 ファイル / 20 件 |
| Task 4 (K-8/9/11) + DIST-12 前倒し | `66e59e8` | settings.local.json key 保存 + lib 強制上書き + framework_version stamp + framework_root self-install abort | `test_setup_distribution.py` 9 件 |
| Task 5 (K-10) | `66e59e8` | python3 prereq + smoke run abort | `test_setup_prereq.py` 2 件 |
| Task 6 (K-12) | `bd3f117` | ARTIFACT_TO_TEMPLATE 明示 dict + full profile に 17 テンプレ追加 + deny メッセージ強化 | `test_profile_checker_parity.py` 4 件 |
| Task 7 (K-13) | `bd3f117` | cheatsheet に 🟡 ack 判断例 4 行 | docs のみ |

### 4. grill-code（実装レビュー）

- 5 コミット差分 4811 insertions を実走 PoC 込みで審査
- 🔴 Critical 2 件 + 🟡 3 件 + 🟢 3 件抽出
- Critical 修正:
  - Critical 1: `check-control-plane.sh` Path B が最初の `>` のみ走査 → 全 redirect 走査に修正（コミット `4897c6b`）
  - Critical 2: `evidence.sh` が output tail 4 KiB のみ → head+tail 二箇所抽出に修正（同コミット）
- 🟡 3 件（K-11 d5 が install 先で dead-code 等）は v1.6.3 / v1.7 送り

## 行動レビュー

不要（v1.6.0 で実施した行動レビュー観点 P1〜P4 は v1.6.1 / v1.6.2 で構造的に塞ぎ済み）。v1.6.2 の機械側／配布パス／UX の改善はテスト + PoC で十分検証されている。

## 残課題（v1.7 で対応）

- K-14（PERF-1）: PostToolUse Bash 400ms/call の fingerprint cache
- K-15（PERF-2）: update_gate_lock テスト 88s sleep の monkeypatched poller 化
- K-16: README トップ 200 行の専門語 + setup 出力末尾「次の一手」
- grill-code 🟡 3: status_doctor d5 dead-code、settings shallow merge、PoC harness の追加カバレッジ
- S-2〜S-23（🟡 級）: 第5/6 回レビューの残余
- T3: `bin/aegis-doctor` 集約コマンド

## 結論

🟡 マージ可（ack で承認）。

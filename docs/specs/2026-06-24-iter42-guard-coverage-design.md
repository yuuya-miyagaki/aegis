# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-24-iter42-guard-coverage-brainstorm-record.md`
- 要件: `docs/full-review-2026-06-24-hooks-gates-distribution.md`（G1/G2/G3）

## 問題整理

- 背景: guard hook（事故防止）の取りこぼし。check-cron-gate は inline パターンで patterns.sh と drift し、G1 で破壊パターンを足しても cron に届かない。check-secrets は `git -C` で staged-diff scan が空振り。
- 制約: 既存挙動を退行させない（特に deploy-gate の DEPLOY_RE）。bash 3.2 安全。check-control-plane 不変。framework_version 1.14.0 据置。
- 脅威モデル: emit_ask（確認）ベースの事故防止。敵対的間接（var/interpreter）は SF-004 受容。

## 推奨アプローチ（finding 別）

### G1 — 破壊パターン追加（patterns.sh）
- `AEGIS_DESTRUCTIVE_CMD_REGEX` と `AEGIS_DESTRUCTIVE_CMD_WARN` に同 index で追加:
  - `(^|[^a-zA-Z])dd[[:space:]].*[[:space:]]of=` — "dd writes directly to a device/file (overwrite)"
  - `chmod[[:space:]]+(-[a-zA-Z]*[[:space:]]+)*-R|chmod[[:space:]]+-R` → 簡潔に `chmod[[:space:]]+-?-?[a-zA-Z]*R` は過剰。確定: `chmod[[:space:]]+(-[a-zA-Z]*R|-R)` — "recursive chmod (-R) changes permissions on a whole tree"
  - `(^|[^a-zA-Z])mkfs(\.|[[:space:]]|$)` — "mkfs formats a filesystem (destroys data)"
  - `(^|[^a-zA-Z])shred([[:space:]]|$)` — "shred securely wipes files (unrecoverable)"
  - `>[[:space:]]*/(etc|usr|bin|sbin|boot|sys|lib|dev)(/|[[:space:]]|$)` — "truncating a system path via redirect"
- `check-destructive.sh` は `${!AEGIS_DESTRUCTIVE_CMD_REGEX[@]}` を iterate するのでコード変更不要。
- 誤検知対策: chmod の `-R` は短/長混在に強い形。truncate は `>>`（append）と区別＝単一 `>` のみ（regex は `>` 1 個。`>>` は `> >`... 実際は `>>` も `>` を含む＝要注意）。**確定**: append を除外するため `[^>]>[[:space:]]*/(etc|...)` か行頭 `>`。実装時に `>>` 非該当を test で固定。

### G3 — deploy/destructive を single-source 化
- `patterns.sh` に `AEGIS_DEPLOY_REGEX="..."`（現 check-deploy-gate.sh:62 の DEPLOY_RE を**逐語移設**）。
- `check-deploy-gate.sh`: `DEPLOY_RE` を削除し `source patterns.sh` → `"$AEGIS_DEPLOY_REGEX"` を使用（挙動 byte 等価）。
- `check-cron-gate.sh`: `source patterns.sh`。inline `DANGER_RE` を撤去し、prompt に対して (a) `AEGIS_DEPLOY_REGEX`、(b) `AEGIS_DESTRUCTIVE_LOWER_REGEX`（lower-cased prompt に対し iterate）、(c) `AEGIS_DESTRUCTIVE_CMD_REGEX`（raw prompt に iterate）、(d) `rm -r` 特例 を順に grep。いずれか hit で emit_ask。G1 の新破壊パターンが自動波及。
  - 注: cron は emit_ask（現状維持）。deploy 半分の拡張（wrangler 等）は改善方向。

### G2 — check-secrets が git -C/--git-dir を尊重
- commit 検査（:160-170）の前で CMD から git ディレクトリ指定を抽出:
  - `-C <path>`（位置引数）/ `--git-dir=<path>` / `--git-dir <path>`。
  - 抽出ヘルパー（bash 関数）で `GIT_DIR_ARGS=(-C "<path>")` 等を組み立て、`git "${GIT_DIR_ARGS[@]}" diff --cached --name-only` で実行。
  - 抽出失敗時は現挙動（CWD で実行）にフォールバック。

## コンポーネント分解

- patterns.sh: データ追加（G1）＋新 `AEGIS_DEPLOY_REGEX`（G3）。
- check-deploy-gate.sh: DEPLOY_RE 参照を patterns.sh へ（G3・挙動保存）。
- check-cron-gate.sh: patterns.sh import＋合成判定（G1+G3）。
- check-secrets.sh: git -C 抽出（G2・独立）。

## インターフェース定義

- `AEGIS_DEPLOY_REGEX`（string・grep -E パターン）。
- check-secrets: `_aegis_extract_git_dir_args "$CMD"` → `GIT_DIR_ARGS` 配列（空可）。

## 依存関係

- G1 → G3（cron が patterns import すると G1 が自動波及）。G2 独立。循環なし。
- 外部依存: なし（bash + grep）。

## エラーハンドリング

- guard はすべて emit_ask（確認）or emit_allow＝fail-safe。check-secrets は既存どおり emit_deny（secret）／emit_ask。
- git -C 抽出失敗 → CWD フォールバック（現挙動・退行なし）。

## テスト戦略

- G1: check-destructive を実起動（run_hook 同型）。dd of=/chmod -R/mkfs/shred/`> /etc/hosts` で emit_ask、無害コマンド（`echo`, `chmod 644 f`, `>> log`, `cat`）で emit_allow。`>>`（append）が非該当を固定。
- G3 deploy: check-deploy-gate が AEGIS_DEPLOY_REGEX 移設後も現 DEPLOY_RE と同判定（vercel deploy / vercel --prod / firebase deploy / 非該当 `vercel env` / `rg deploy`）。
- G3 cron: check-cron-gate が dd/chmod -R を含む prompt で emit_ask（G1 波及）・deploy prompt で emit_ask・無害 prompt で allow・python3 不在で fail-closed ask（現挙動維持）。
- G2: temp git repo を作り `git -C <repo> commit` で .env staged → emit_deny（修正前は allow）。CWD 直 commit の現挙動が不変。
- 結合: full suite green・contract full PASS・status_doctor PASS・`bash -n` 全 hook。

## 次のステップ

- [ ] 実装計画 → `docs/plans/2026-06-24-iter42-guard-coverage-plan.md`（PLAN.template.md）
- 本設計を PLAN の参照設計に記載
<!-- exit-check: 全セクション記入・自己レビュー完了 -->

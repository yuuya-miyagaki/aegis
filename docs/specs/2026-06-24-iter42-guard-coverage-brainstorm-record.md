# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-24

## テーマ

- iteration 42 / 2026-06-24 全力レビュー Batch 2 のうち **G1-G3 guard 網羅**（I3 は iter43 へ繰延）

## コンテキスト

- 現在の状況: framework・L・phase=brainstorm。iter41（配布+整合性 Batch 1）完了・commit 済（push はユーザー）。
- きっかけ: `docs/full-review-2026-06-24-hooks-gates-distribution.md` の 🟡 guard 網羅（G1-G3）＝事故防止スコープの取りこぼし。
- ユーザー判断: 「推奨で進めて。慎重に。できるだけ自動で」＝I3（設計フォークあり）を iter43 に分離し、G1-G3 を先行する推奨を承認。

## 検討したアプローチ

### アプローチ A: G1-G3 を 1 イテレーション・I3 は iter43【採用】

- 概要: guard 完全性（事故防止）を一括。I3（authorized-path＝ワークフロー変更）は別途。
- 利点: G1-G3 は一貫テーマ・低リスク・ワークフロー非変更。I3 の設計フォークを混ぜない＝レビュー面が小さい。
- 欠点: なし（review doc の Batch 2 を I3 と分けるだけ）。

### アプローチ B: Batch 2 全部（I3+G1-G3）を一括

- 欠点: I3 は rollover の task_type/size 編集（Edit 経由）をブロックする＝authorized-path 機構と workflow 移行が要る設計フォーク。G1-G3 と混ぜると巨大で読みづらい L になる。不採用。

### アプローチ C: G1 のみ

- 欠点: cron-gate の inline DANGER_RE が G1 の新パターンを取りこぼし続ける（drift）。G3 single-source とセットにしないと G1 の価値が cron に届かない。過小。

## 決定

- 採用: **A（G1-G3・I3 繰延）**。
- 理由: 事故防止の取りこぼし埋めは一貫・低リスク。single-source 化（G3）で G1 が cron にも自動波及＝drift 解消。

## 主要設計判断

- **G1**: `patterns.sh` の `AEGIS_DESTRUCTIVE_CMD_REGEX` に追加: `dd ... of=`／`chmod -R`／`mkfs`／`shred`／system-path への truncate redirect（`> /etc|usr|bin|sbin|boot|sys|lib|dev/...`）。`check-destructive.sh` は配列を自動 iterate＝コード変更不要。判定は emit_ask（deny でなく確認）＝事故防止。
- **G3（single-source）**: `patterns.sh` に `AEGIS_DEPLOY_REGEX`（現 check-deploy-gate.sh の DEPLOY_RE を**挙動保存**で移設）を追加。`check-deploy-gate.sh` は同変数を参照。`check-cron-gate.sh` は patterns.sh を source し inline `DANGER_RE` を `AEGIS_DESTRUCTIVE_CMD_REGEX`＋`AEGIS_DESTRUCTIVE_LOWER_REGEX`＋`AEGIS_DEPLOY_REGEX` の合成に置換＝G1 の新破壊パターン＋full deploy セットが cron にも波及。
- **G2**: `check-secrets.sh` の commit 検査（`git diff --cached`）が hook の CWD で走る＝`git -C <repo> commit` だと別 repo を見て検出ゼロ。CMD から `-C <path>`／`--git-dir=<path>` を抽出し `git -C <path> diff --cached` で実行。
- **out-of-scope（脅威モデル整合・文書化）**:
  - `git push <remote>` をデプロイ判定 → 通常リモート更新と区別不能（review が MCP push を同理由で除外済み）＝追わない。
  - `V=vercel; $V deploy` 変数間接 → SF-004（interpreter 間接）クラス＝事故では起きない・受容済み。
  - `> /etc/...` 以外の任意 `>` truncate → 広すぎ（全ファイル書込みに警告）＝system-path に限定。

## スコープ境界

- やること: G1（破壊パターン追加）・G2（secrets git -C）・G3（deploy/cron single-source 化）＋回帰テスト。
- やらないこと: I3（iter43）／git-push-deploy／var-indirection／generic truncate／check-control-plane 再設計。

## 未解決事項（plan/grill で詰める）

- AEGIS_DEPLOY_REGEX 移設が deploy-gate の現挙動を byte 等価に保つか（特に `vercel` bare-flags ケース）。
- cron-gate を patterns.sh import に切り替えた際、現 DANGER_RE が拾えていたものを取りこぼさないか（deploy サブセットの拡張は改善方向だが要確認）。
- system-path truncate regex の誤検知（`>>` append との区別・`2>` 等のリダイレクト演算子）。

## 次のステップ

- [x] 設計ノート → `docs/specs/2026-06-24-iter42-guard-coverage-design.md`
<!-- exit-check: アプローチ決定・スコープ明確 -->

# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-brainstorm-record.md`
- 要件: なし（framework 自己改善・正本は `docs/security-followups.md` SF-020/SF-021）

## 問題整理

- 背景: (1) SF-020 — `check-destructive.sh` の raw 経路（`NORM==CMD`）が破壊語 regex を生 grep しており、case-insensitive FS（macOS APFS/Windows）で `RM -rf /tmp/x` や `echo x > /ETC/passwd` が **silent allow**。難読化経路（`NORM!=CMD`）は iter75 FF7 で `grep -i` on NORM 化済み＝raw 直打ちのみ残存。(2) SF-021 — `check-secrets.sh:169` の `_STAGE_BROAD_RE` が `add` 固定で、完全エイリアス `git stage -A/.` が実 .env 存在下でも **silent allow**（生でも通る＝難読化以前）。
- 判断が必要な論点: raw 経路の case-fold 機構（grep -i vs 入力小文字化 vs regex 書換え）。
- 制約条件: 既存 deny 系 moat（174 pin）非弱体化／正常形（`git commit -m "…"` 救済・safe-artifact 除外）非退行／iter73 の LC_ALL=C byte-wise 方針と非衝突／denylist 新語彙を足さない（LEARNINGS conf9）。

## 推奨アプローチ

- 採用方針: **SF-020 = raw 経路の破壊語 grep を全サイト `grep -iqE` 化**（iter75 FF7 と同一方式・呼び出し側のみ変更、regex SSOT `patterns.sh` は不変更）。**SF-021 = `_STAGE_BROAD_RE` の `add` → `(add|stage)`** ＋事実誤認コメント（「stage は broad 綴りを持たない」）の訂正。
- 採用理由: (1) `check-destructive.sh:158-162` に実証済みの根拠がある — `AEGIS_DESTRUCTIVE_CMD_REGEX` は大文字リテラル（`chmod` の `-[a-zA-Z]*R` 等）を含み、入力小文字化（CMD_LC/NORM_LOWER）は捕捉を壊す。`grep -i` は widening（ask 増）方向のみ＝moat では安全側。(2) redirect システムパス（`patterns.sh:50` の `etc|usr|bin…` 小文字リテラル）は同配列を grep する呼び出し側の `-i` 化で自動封鎖＝個別対応不要。(3) `_STAGE_BROAD_RE` は `CMD_LC`/`NORM_LC`（小文字化済み）に照合されるため、`(add|stage)` 拡張だけで `GIT STAGE -A`（SF-020×021 合成）も同時に閉じる。
- 検討した代替案と不採用理由: (a) CMD_LC 化で secrets と対称化 — 大文字リテラル regex を壊す（iter75 実測反例・:158 コメント）。(b) regex 側を `[rR][mM]` 等に書換え — 全 pattern 改写で差分巨大・SSOT 可読性毀損・語彙追加のたび同じ穴が再発。(c) `git update-index` も追補 — stage と異なり低レベルで挙動が別・台帳が「stage のみ完全同義」と認定済み＝YAGNI。

## コンポーネント分解

- 分割方針: フック2ファイルを独立に修正（相互依存なし）。regex SSOT は不変更。
- 各ユニットの責務:
  - ユニット A（`hooks/check-destructive.sh`）: raw 経路の破壊語判定 grep サイト（`$INPUT` 前段 hit・`$CMD` 本判定・再帰削除 grep 等、plan で全列挙）を `grep -iqE` 化。NORM 経路（既に `-i`）と対称になる。
  - ユニット B（`hooks/check-secrets.sh`）: `_STAGE_BROAD_RE` を `(add|stage)` 拡張。二経路トリガ（raw=deny/norm=ask）は既存構造をそのまま流用。コメント訂正。

## インターフェース定義

- ユニット間の契約: なし（独立）。両者とも PreToolUse hook の既存入出力契約（stdin JSON → allow=`{}` / ask / deny JSON）を不変更。
- 公開 API: 変更なし（呼び出し側の grep フラグと regex 文字列のみ）。

## データフロー / 構造

- 入力: PreToolUse stdin JSON（Bash コマンド文字列）。
- 処理: 既存フローのまま。変更点は (A) raw 破壊語照合が case-insensitive になる、(B) broad-stage 照合の動詞集合が {add, stage} になる、のみ。
- 出力: `RM -rf /tmp/x`→ask、`echo x > /ETC/passwd`→小文字形と同一判定、`git stage -A`(実 .env)→deny、`git${IFS}stage -A`→ask、`GIT STAGE -A`→deny。正常形は不変。

## 依存関係

- 依存方向: check-destructive.sh / check-secrets.sh → hooks/lib/patterns.sh（読み取りのみ・変更なし）。循環なし。
- 外部依存: なし（pure bash + grep。LC_ALL=C 下の `grep -i` は ASCII fold のみ＝iter73 byte-wise 方針と非衝突・locale crash クラス無縁）。

## エラーハンドリング

- 想定失敗: `grep -i` 化による正常形の過剰 ask（誤検知）。
- 対応: NORM 経路は iter75 以降 `grep -i` 運用済みで誤検知実績なし。正常形回帰 pin（`git commit -m "…STATUS.md…"` 救済・`rm -rf node_modules` allow・`git stagearea`→allow）で機械的に固定。
- エラー伝播の方針: 既存の fail-closed 方針（required-lib 欠落=deny）を変更しない。

## テスト戦略

- 単体（TDD・旧実装で赤→新実装で緑を各 pin で確認）:
  - SF-020: `RM -rf /tmp/x`→ask／`echo x > /ETC/passwd`→小文字 `/etc` 形と同一判定／`chmod -R` 系の既存捕捉不変（大文字リテラル regex が `-i` 下でも機能）。
  - SF-021: `git stage -A`(実 .env)→deny／`git stage .`→deny／`git${IFS}stage -A`→ask（norm 経路）／`git stagearea xyz`→allow（誤マッチ回避）。
  - 合成: `GIT STAGE -A`(実 .env)→deny。
- 結合: moat 非弱体化スイート（deny 系 174 pin）green／full suite green。
- エッジケース: safe-target 交差（`RM -rf node_modules`）— RED フェーズ実測で allow 維持 or ask を決定し pin（どちらも安全側・record に判断を記録）／`git add -A` deny 不変／SF-016 C-locale 非衝突。
- 手動確認: フック単体呼び出しの pre/post 生出力を review evidence として記録（iter75/76 と同形式）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-26-iter77-moat-case-fold-stage-alias-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

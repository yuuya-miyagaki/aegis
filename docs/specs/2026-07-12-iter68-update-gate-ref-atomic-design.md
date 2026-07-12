# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: docs/specs/2026-07-12-iter68-update-gate-ref-atomic-brainstorm-record.md
- 要件: なし（framework 自己改善・動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §R6/§4 Phase 1 表 1-3）

## 問題整理

- 背景: ゲート値（`gate_approvals.<gate>`）と evidence ref（`current_refs.<gate>`）が別書込みのため、どちらの順でも contract 赤の窓が開く（pending+ref=stale FAIL／approved+空=FAIL）。加えて update-gate.sh は approve 時に**状態書込みより前に** judge カード全文を stdout へ流し、pipe 早期クローズ（`| head`）で SIGPIPE 死＝状態未変更（罠 a）。operator は「record→ref→承認を連続・pipe は tail」という操作列の暗記を強制されてきた（LEARNINGS conf9×2＋conf8・iter35/43/64/65 で被弾）。
- 判断が必要な論点: (1) 原子化の書込み単位、(2) SIGPIPE 不変条件の立て方（trap vs 並べ替え vs 両方）、(3) pending/n/a+ref 降格の適用点（共有関数 vs 呼び出し側個別）、(4) na の ref 扱い、(5) SF-011/012 の相乗り可否。
- 制約条件: update-gate.sh は tamper-evident な唯一の gate writer（raw Edit は post-status-audit が block）。bash 3.2（macOS）互換。既存の lock プロトコル・pre-approve 判定（check_status.py --pre-approve-gate）・ACK 機構・B2 judge-card push の意味論は不変。C-2/K-1/fp backstop 等 judge 側は不接触。

## 推奨アプローチ

- 採用方針: writer 原子化（`approve --ref`）＋状態書込み先行（trap '' PIPE 併用）＋pending/n/a+ref の advisory 降格のフルセット（brainstorm record アプローチ A）。
- 採用理由: 赤い窓の存在自体を消し、SIGPIPE 下でも「状態変更前=何も主張しない／変更後=出力欠けのみ」の fail-safe 不変条件が立つ。降格は共有関数1点で contract と完了検査に一貫波及。
- 検討した代替案と不採用理由: 降格のみ（approved+空窓と2ステップ暗記が残存）／trap のみ（set -e 下で EPIPE abort に化けるだけ）— record 参照。

## コンポーネント分解

- 分割方針: 書込み系（bash writer）と判定系（python contract）を別ユニットとして疎結合のまま、それぞれ最小 diff で変更。ゲート→ref 対応表は既存の二重定義（python `GATE_REF_MAPPING` ↔ bash `get_ref_key`）を追加なしで使う。
- 各ユニットの責務:
  - ユニット A（scripts/update-gate.sh）: 引数解析の flag loop 化（`--ack <reason>`・`--ref <path>`）／--ref 検証／ゲート値＋ref の単一パス sed 書込み／approve 経路の並べ替え（検証→書込み→ACK 追記→snapshot→best-effort 出力）／`trap '' PIPE`／na の ref null 化。
  - ユニット B（scripts/check_status.py）: `evidence_integrity_violations` の pending/n/a+ref 分岐を violations から printed WARNING へ降格／`pre_approve_gate` の ADVISORY 文言を `approve --ref` 推奨へ更新。
  - ユニット C（tests/）: 既存ピン更新＋新規テスト（下記テスト戦略）。
  - ユニット D（guidance）: CLAUDE.md 完了規則の文言・.claude/commands/gate.md・gate 系 skill（aegis-review-gate/aegis-security-gate/qa-verification/ship-and-docs/deploy）の approve 手順を `approve --ref <evidence>` 正順へ同期。

## インターフェース定義

- 公開 API（CLI・後方互換は加算のみ）:
  - `bash scripts/update-gate.sh <gate> approve [--ref <repo相対path>] [--ack "<reason>"]`
    - `--ref` は approve 専用。対象 gate が ref key を持たない（brainstorm/dev_ready_for_client）→ usage エラー・状態不変。
    - path は repo 相対必須（先頭 `/` 拒否）・`$ROOT/<path>` が通常ファイルとして実在しなければエラー・状態不変。
    - 既に approved の gate へ --ref → 現行どおり「No change needed」で exit 0＋「ref は変更していない」旨を明示（ref 差し替えはスコープ外）。
  - `na` / `reset` に `--ref` → usage エラー。
  - `na` は reset と同様に対応 ref を null 化（同一 sed 単一パス）。
- ユニット間の契約:
  - A → STATUS.md: gate 値と ref 値を**1回の TMP 書込み＋mv**で反映（並行 reader が中間状態を観測しない）。ref 値は既存表記に合わせ `"<path>"`（二重引用符）で書く。reset/na の null は非引用 `null`。
  - B → 呼び出し側: `evidence_integrity_violations` の返り値（violations）から pending/n/a+ref を除去し、代わりに `WARNING:` を stdout に print。approved+空 ref／ref 先ファイル不在／requirements 不在／client artifact 不整合は violations のまま（FAIL 維持）。呼び出し側2箇所（validate_status_file・--check-completion-evidence）は無改修で一貫波及。

## データフロー / 構造

- 入力: CLI 引数（gate/action/flags）、docs/STATUS.md frontmatter、judge 前提（check_status --pre-approve-gate の tri-state）。
- 処理（approve の新順序）:
  1. 引数解析・validate（gate/action/--ref 検証）
  2. lock 取得→CURRENT 読取（既存不変）
  3. pre-approve 判定（🔴=exit1 状態不変／🟡=--ack 必須）
  4. **sed 単一パス書込み**（gate=approved ＋ --ref 指定時は ref="path"）→ mv
  5. ACK 追記（--ack 時・judge カードファイルへ）
  6. snapshot 書込み（既存 aegis_write_snapshot）
  7. best-effort 出力（[gate-approve] 行・B2 judge-card push・現況表示）＝report 関数を `|| true` で呼ぶ
- 出力: STATUS.md（原子更新）・.gate-snapshot・stdout レポート（欠けても状態に影響しない）。
- SIGPIPE 不変条件: `trap '' PIPE` を冒頭に置き、(a) 書込み前に pipe が閉じた場合＝EPIPE で検証出力が fail→set -e で exit（状態不変・承認主張ゼロ）、(b) 書込み後＝report が fail しても `|| true` で exit 0（状態整合・出力欠けのみ）。「承認を主張する出力は必ず状態永続化の後」をテストで固定する。

## 依存関係

- 依存方向: update-gate.sh → check_status.py（pre-approve 委譲・既存）→ hooks/lib（frontmatter.sh/snapshot.sh・既存）。循環なし。
- 外部依存: なし（pure bash＋既存 python。新規依存ゼロ）。
- 二重定義の parity: bash `get_ref_key` ↔ python `GATE_REF_MAPPING` は既存。drift guard が未整備なら安価な parity テストを plan で検討（iter53/65 型）。

## エラーハンドリング

- 想定失敗と対応:
  - --ref パス不在／絶対パス／ref key 無し gate／approve 以外への --ref → usage エラー exit 1・**状態不変**（lock 取得前に検証できるものは前で）。
  - sed/mv 失敗 → set -e で abort・TMP 残置なし（既存 `${STATUS_FILE}.tmp.$$` 方式踏襲）・gate/ref とも旧値のまま（部分書込みなし）。
  - 書込み後の出力失敗（EPIPE 等）→ `|| true` で握り exit 0（状態は既に整合）。ACK 追記は stdout でなくファイル追記なので EPIPE 非該当・書込み直後（report より前）に置き「承認されたのに ACK 未記録」を防ぐ。
- エラー伝播の方針: 状態変更前の失敗は非ゼロ exit で伝播（fail-closed）。状態変更後は出力系のみ best-effort（fail-open だが状態に不影響）。

## テスト戦略

- 単体（bash・scratch repo fixture＝test_update_gate_lock.py の型を踏襲）:
  - `approve --ref`: 実行後 gate=approved **かつ** ref="path" が同時に立ち、直後の `check_status --root` が rc 0（窓なしの観測的証明）。
  - --ref 検証系: 不在パス／絶対パス／brainstorm への --ref ／`reset --ref`・`na --ref` → いずれも exit 1＋STATUS 不変（gate も ref も旧値）。
  - `na` の ref null 化と `reset` の既存挙動非退行。
  - 既 approved への `approve --ref` → exit 0・ref 不変・明示メッセージ。
- 結合（SIGPIPE E2E＝罠 a の再現固定）:
  - `bash update-gate.sh <gate> approve --ref <path> | head -c 1` 相当で pipe を早期クローズ → **STATUS 上 gate=approved・ref 設定済み**を事後 assert（旧実装ならここで pending のまま＝RED になることを TDD RED で確認）。
  - 出力順序: 成功時 stdout で `[gate-approve]` 行が judge カード push より前かつ、書込み失敗を注入（STATUS を読取専用化等）した場合に承認主張出力が一切出ないこと。
- python 側:
  - 既存ピン `test_pending_gate_with_ref_is_stale_violation`（tests/test_check_status.py:2172）→ 「violation ではなく WARNING・rc 0」へ書き換え。
  - approved+空 ref FAIL・ref 不在 FAIL の非退行ピン。n/a+ref も WARNING（対称）。
  - --check-completion-evidence 経由でも pending+ref が rc 0＋WARNING（TaskCompleted hook 波及の直接証明）。
- エッジケース: path に sed 特殊文字（`&`・`|`）を含む場合のエスケープ／client_ready_for_dev→translation の --ref 経路／lock 競合下の --ref（既存 lock テストの非退行）。
- 手動確認: 実フローで `record green → approve --ref docs/qa-reports/iter68-review.md` の2手が contract 赤ゼロで通ること（qa フェーズの実環境 E2E で記録）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-12-iter68-update-gate-ref-atomic-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

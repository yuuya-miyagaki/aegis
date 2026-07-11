# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: docs/specs/2026-07-12-iter66-sf010-parser-unification-brainstorm-record.md
- 要件: なし（framework 反復・動機正本は docs/security-followups.md SF-010）

## 問題整理

- 背景: STATUS.md frontmatter の読取が bash 4 読点（frontmatter_value / gate_value / snapshot 生成 / check-gate インライン）と python 3 関数（extract_scalar_value / extract_approval_map / extract_frontmatter）でそれぞれ微妙に異なる意味論を持つ。iter65 で task_size が gate 判定に昇格したことで、この不統一が初めて gate-bypass（SF-010）と audit-evading な enforcement 割れ（F-1）に転化した。
- 判断が必要な論点: (1) migration-grace をどこまで絞るか (2) スコープ化を library 級にするか読点限定にするか (3) 二重実装を統合するか温存するか。
- 制約条件: hook は pure-bash fail-closed を維持（python 委譲は fail-open 退行＝iter65 却下済み）。呼出契約「absent → 空 stdout＋rc0」は不変（9 hook ファイルの消費側を無改修に保つ）。bash 3.2（macOS 既定）互換。

## 推奨アプローチ

- 採用方針: 「**frontmatter 内の最初の値**」を単一意味論として bash/python の全読点に適用し、migration-grace は「真の旧フォーマット snapshot」限定に絞る。二重実装は温存し、parity drift-guard テストで意味論一致を機械的にピンする。
- 採用理由: 同根（読取意味論の不統一）の機構的根治。読点単位の穴塞ぎ（b9c95f7 型）の反復を止める。全変更が fail-closed 方向（allow が増える変更ゼロ）。
- 検討した代替案と不採用理由: 読点限定スコープ化＝モグラ叩き再発（BRAINSTORM-RECORD アプローチ B）／grace 絞りのみ＝F-1 残置・トラッカー宣言違反（同 C）／単一パーサ統合＝fail-open 退行（iter65 却下済み）。

## コンポーネント分解

- 分割方針: 読取 library（意味論の単一ソース）→ 生成系（snapshot）→ 判定系（audit）→ python 検査系 → parity guard の 5 ユニット。各 Fix は独立にテスト可能・独立にコミット可能。
- 各ユニットの責務:
  - **Fix ① audit grace 絞り込み**（hooks/post-status-audit.sh・SF-010 本丸）: task field tamper 判定を「`OLD_TF != NEW_TF` かつ（`OLD_TF` 非空 **または** snapshot に `task_type:` 行が存在）なら block」へ。grace は「旧値空 かつ snapshot に task_type 行なし」＝真の旧フォーマット（pre-iter43）のみ。
  - **Fix ② frontmatter_value スコープ化**（hooks/lib/frontmatter.sh）: 先頭行 `---` → `read_frontmatter` 出力内 first-match のみ。`---` 開始だが未終端 → 空（fail-closed）。`---` 非開始（bare `.gate-snapshot`）→ 従来の whole-file。契約（absent→空+rc0・クォート剥がし）は不変。
  - **Fix ③ snapshot 生成スコープ化**（hooks/lib/snapshot.sh）: phase/mode/task_type/task_size の whole-file `grep -m1` 4 行と gate_approvals ブロックの whole-file `sed` を frontmatter スコープ読み（②＋`frontmatter_section`）へ置換。監査 baseline 側の本文毒込みを封鎖。
  - **Fix ④ gate_value fallback 厳格化**（hooks/lib/frontmatter.sh・F-2）: `raw_section` fallback を「`---` frontmatter を持たないファイル」限定に。`---` ありで gate_approvals 節なし → 空＝下流 not-approved（fail-closed）。
  - **Fix ⑤ python 意味論同期**（scripts/check_status.py）: `extract_scalar_value` を行順 first-match の 1-pass（マッチ後クォート剥がし）へ（F-1 根治）。`extract_approval_map` を重複キー先勝ちへ（bash `grep -m1` と一致）。
  - **付随 dedup**（hooks/check-gate.sh）: b9c95f7 のインライン frontmatter スコープ読みを ② の `frontmatter_value` 呼び出しへ戻す（意味論の単一ソース化）。

## インターフェース定義

- ユニット間の契約:
  - `frontmatter_value <file> <key>` → stdout: スカラー値（クォート剥がし済）／absent・malformed → 空 stdout＋rc0。**新規保証**: `---` 付きファイルでは本文行は不可視。
  - `gate_value <file> <gate>` → stdout: gate 値。**新規保証**: `---` 付きファイルで frontmatter に節が無ければ空（本文 fallback しない）。
  - `aegis_write_snapshot <root>` → snapshot 内容は STATUS.md の **frontmatter 由来のみ**（新規保証）。
  - python `extract_scalar_value(frontmatter, key)` / `extract_approval_map(frontmatter)` → bash 読点と**同一の値**を返す（parity guard で機械保証）。
- 公開 API: 変更なし（関数シグネチャ・rc 規約すべて既存踏襲）。

## データフロー / 構造

- 入力: docs/STATUS.md（`---` 区切り frontmatter）／.claude/.gate-snapshot（bare frontmatter 形式）。
- 処理: 読取（②④⑤）→ snapshot 生成（③）→ tamper 判定（①）。
- 出力: emit_block（tamper 時）／snapshot ファイル／check_status.py の検査結果。
- 攻撃面の変化: 本文 spoof 行・frontmatter 内重複キー・未終端 frontmatter のいずれでも、enforcement（bash）と検査（python）が同じ値を読む＝割れによる audit-evasion が構造的に消滅。

## 依存関係

- 依存方向: post-status-audit.sh / check-gate.sh / snapshot.sh → frontmatter.sh（一方向・循環なし）。check_status.py は独立（parity はテストで束縛）。
- 外部依存: なし（pure bash + awk/grep/sed・python3 stdlib re のみ・現状維持）。

## エラーハンドリング

- 想定失敗: 未終端 frontmatter／snapshot 欠落／キー欠落／重複キー／本文 spoof 行。
- 対応: すべて「空を返す→消費側が not-approved/deny 扱い」に収束（fail-closed）。Fix ① は snapshot 欠落時（＝task_type 行なし）grace 側に倒れるが、live セッションでは session-start が snapshot を必ず再生成し、`.claude/` への Bash 書込みは check-runtime-state.sh が block するため、snapshot 削除による窓開けは脅威モデル外（SF-006 較正と同じ境界）として設計ノートに明記。
- エラー伝播の方針: 読取層は rc0＋空（既存契約）。判定層（audit）のみ emit_block で明示 deny。

## テスト戦略

- 単体（TDD RED-first）:
  - T1 SF-010 再現: snapshot に task_type あり・task_size なし（empty-baseline）→ STATUS raw-Edit で `task_size: S` 追加 → **block**（現行は素通り＝RED から開始）。
  - T2 grace 温存: snapshot に task_type 行なし（真の旧フォーマット）→ 同編集が grace（block されない）。
  - T3 正規経路無影響: update-task.sh 経由の変更（snapshot 原子更新込み）が block されない。
  - T4 自己防衛: task_type を raw-Edit で除去 → 既存判定（OLD 非空・値相違)で block（grace を開けられない）。
- 結合: 既存 full suite（1096 passed / 2 skipped 基準）＋scaffold smoke。既知 flaky `test_update_gate_lock` は回帰判定から除外（full-review R10 test#8）。
- エッジケース（parity drift-guard・iter53/65 型）: 敵対 fixture 表 —（a）frontmatter 内重複キー（b）引用形+非引用形混在（F-1 再現）（c）本文 spoof 行（d）gate_approvals 節欠落（F-2 再現）（e）bare snapshot（f）未終端 frontmatter — 各 fixture について bash 読点（bash -c ハーネス）と python 読点の返値一致をアサート。将来どちらかが drift したら赤。
- 手動確認: なし（全て自動化・ドリル対象は qa フェーズで B1 判断）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-07-12-iter66-sf010-parser-unification-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

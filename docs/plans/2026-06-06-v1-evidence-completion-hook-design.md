# evidence 完了強制化（TaskCompleted）設計書

> Phase R 再配分の最終項目。`validate_status_file` が既に持つ gate-ref 整合性＋ref 実在の不変条件を、**TaskCompleted イベントでも強制**する（既存ロジックの再利用＝新規実装しない）。

**版:** v0.12.6 想定 / **日付:** 2026-06-06（grill-plan 反映改訂） / **mode:** Dev / **task_type:** framework

---

## 1. 目的

CLAUDE.md の Completion Rule は「成果物が実在／STATUS が active refs を指す」等を散文で要求するだけで強制力がない。`check_status.py` の `validate_status_file` は既にこの一部（gate-ref 整合性・ref 実在）を **FAILURE として検査**するが、それが走るのは `check_framework_contract.py`（CI/手動）と `/status` だけで、**per-action の hook では走っていない**（`post-status-audit.sh` は gate 改竄と phase 遷移の監視のみ）。

結果として「STATUS を不整合に編集 → タスク完了申告」しても contract を手で回すまで誰も止めない実ギャップがある。これを「保証＝決定論的強制」の triage に従い、**完了申告時にも同じ不変条件を強制**する。

## 2. 方針判断（採用と却下）

- **トリガ = (B) 既存 `check-task-completed.sh` を拡張**（採用）。却下: (A) 新規 Stop hook（毎ターン発火で誤爆構造が大きい）、(C) 両方（複雑）。
- **中身は新規実装せず `validate_status_file` のロジックを再利用**（grill-plan 反映）。`546-586` の gate-ref 整合性＋ref 実在ロジックをヘルパ `evidence_integrity_violations()` に切り出し、`validate_status_file` と新フラグの両方が呼ぶ。3箇所重複の `gate_ref_mapping` をモジュール定数 `GATE_REF_MAPPING` に統一。
  - 却下: 当初の `check_completion_evidence` 新規二層実装＋`COMPLETION_*` 定数。→ `validate_status_file` の完全再実装になり drift 源を増やすため棄却。
- **検査スコープ = `validate_status_file` の gate-ref＋実在サブセットを丸ごと**：
  - approved ゲート → 対応 ref 非空（canonical `GATE_REF_MAPPING`、`client_ready_for_dev→translation` 含む）
  - pending/n/a ゲート → 対応 ref が**残っていない**（逆 stale チェック）
  - scalar ref（plan/spec/review/qa/security/deploy/translation）非 null → ファイル実在
  - requirements リスト → 各ファイル実在
- **バイパス無し**（YAGNI・整合性に正当な回避需要が乏しい）。
- **`pre_approve_gate` の DEPRECATION→`REF_CHECK_ERROR_VERSION="0.13.0"` ハードニングとの関係**: あちらは**承認時**の gate-ref チェック、本件は**完了時**。相補的（完了時チェックは `/gate` を経由しない STATUS 直接編集による不整合も捕捉する）。重複ではなく別レイヤ。§9 参照。

## 3. アーキテクチャ

`scripts/check_status.py` に手を入れ（root/example IDENTICAL）、`check-task-completed.sh` から呼ぶ。

- 新モジュール定数 `GATE_REF_MAPPING`（`validate_status_file:547`・`pre_approve_gate:747` の重複インラインを置換）。
- 新ヘルパ `evidence_integrity_violations(refs, approvals, root) -> list[str]`（path 接頭辞**無し**の違反文字列を返す・`try/except` で **never raises** を実コード保証）。
  - `validate_status_file` は従来の `546-586` を `for m in evidence_integrity_violations(...): failures.append(f"{path} {m}")` に置換 → **出力メッセージ不変・既存テスト緑のまま**。
- 新 CLI フラグ `--check-completion-evidence`：STATUS をパースしヘルパを呼び `EVIDENCE: {v}` を print（終了コード常に0・missing/malformed は無出力＝fail-safe）。session-start の `--check-status-health` と同パターン。

データフロー:

```
TaskCompleted 発火
  → check-task-completed.sh
      → payload 正規化（python3, 既存）
      → STATUS.md 不在/payload 壊れ → emit_allow（既存 fail-safe）
      → 既存: next_action 空/null → exit 2 差し戻し（維持）
      → 新規: python3 "${DEFAULT_ROOT}/scripts/check_status.py" --root "$ROOT" --check-completion-evidence
          → evidence_integrity_violations() の結果を EVIDENCE: 行で print
      → 出力あり → stderr に集約して exit 2（差し戻し）
      → 出力なし → emit_allow
```

## 4. コンポーネント / 触るファイル

| ファイル | 変更 |
|---|---|
| `scripts/check_status.py` | `GATE_REF_MAPPING` 定数・`evidence_integrity_violations()` 抽出・`validate_status_file`/`pre_approve_gate` を定数参照に置換・`--check-completion-evidence` フラグ |
| `examples/minimal-project/scripts/check_status.py` | 上と IDENTICAL 同期 |
| `hooks/check-task-completed.sh` | フラグ呼び出しを配線（next_action 分岐の後） |
| `examples/minimal-project/hooks/check-task-completed.sh` | IDENTICAL 同一 Edit |
| `CLAUDE.md` ＋ `examples/minimal-project/CLAUDE.md` | Completion Rule 節に enforcement を明文化（致命1） |
| `tests/test_check_status.py` | `--check-completion-evidence` フラグの CLI テスト群（再利用ヘルパを exercise） |
| `tests/test_hook_output_schema.py` | hook レベル（違反→exit2 / clean→allow） |
| `scripts/check_framework_contract.py` ＋ `templates/STATUS.template.md` | version 0.12.5 → 0.12.6 |

## 5. 検査ロジック（再利用するヘルパの中身）

`evidence_integrity_violations(refs, approvals, root)` は `validate_status_file:546-586` と同一ロジック（path 接頭辞のみ呼び出し側で付与）:

- **gate-ref 整合性**（`GATE_REF_MAPPING` を反復）:
  - approved かつ ref 空（None/"null"/[]）→ `gate 'X' is approved but current_refs.Y is empty`
  - pending/n/a かつ ref 有り → `gate 'X' is 'pending' but current_refs.Y still has a value (stale ref: ...)`
- **ref 実在**: scalar ref（plan/spec/review/qa/security/deploy/translation）が非 null 文字列なら `root/ref` が実在必須。無ければ `points to missing X ref: ...`
- **requirements**: リスト各要素も `root/elem` 実在必須。
- 全体を `try/except Exception: return []` で包み never raises を保証。

## 6. エラー処理 / フェイルセーフ / 誤爆回避

- **python3 不在** → hook 側 `|| true` で pass-through（fail-open）。hard deny でなく soft 差し戻しなので許容（既存 SUBJECT 抽出と同じ）。
- **STATUS.md 不在 / frontmatter 壊れ** → フラグハンドラが無出力で return 0。ヘルパも `try/except` で `[]`。
- **誤爆構造**: brainstorm/implement 中はゲート pending・ref null なので gate-ref 整合性は違反ゼロ＝ルーティンの TodoWrite 完了は素通り。発火は review 以降のゲート approved・ref 設定後に限定。
- **逆 stale チェックの注意**: pending ゲートに ref を残すと違反になる。これは `validate_status_file` が既に強制している不変条件であり、`update-gate.sh reset` が ref を null 化する設計と整合済み（新規リスクではない）。

## 7. テスト

- **CLI フラグ（`test_check_status.py`）**: clean（全 pending・全 null）→ 無出力／approved+null ref → 違反／approved+実在 ref → 無出力／approved+不在ファイル → 違反／pending+ref 有り → stale 違反／requirements 不在 → 違反・実在 → 無出力／STATUS 不在 → 無出力。
- **hook レベル（`test_hook_output_schema.py`）**: 違反 STATUS → exit2＋stderr に reason／clean → emit_allow。
- **回帰**: `validate_status_file` の既存テストが緑のまま（メッセージ不変）・全テスト・contract（0.12.6 sync）・drift・root/example IDENTICAL。

## 8. footgun（実装時の注意）

- `check_status.py` と `check-task-completed.sh` は root/example **IDENTICAL** → 両方に同一変更。
- hook はスクリプトを `${DEFAULT_ROOT}/scripts/check_status.py`、検査対象を `--root "$ROOT"` で渡す（`AEGIS_ROOT_OVERRIDE` 尊重）。
- ヘルパ抽出は**メッセージ不変**が必須（既存 `validate_status_file` テストを壊さない）。
- `validate_status_file:546-586` の置換と `pre_approve_gate:747` の定数化を**両方**やる（DRY 完遂・片方残すと drift）。
- `check_status.py` 出力規約は英語（`HEALTH:`/`FAIL:`/`EVIDENCE:`）。hook の差し戻し枠は日本語（既存どおり）。
- **ドッグフード自己ブロック**: 実装セッションで aegis hooks が有効な場合、配線後は実装者自身の TaskCompleted も検査対象。実装中の live `docs/STATUS.md` を整合に保つこと（現状 plan pending・spec 実在で安全。後続 bookkeeping で plan approved＋plan ref 実在にしても整合維持）。

## 9. 非スコープ

- Stop/SubagentStop hook の新設（旧確定案 `check-completion.sh`）。
- `pre_approve_gate` の `REF_CHECK_ERROR_VERSION` ハードニング（別件・承認時レイヤ。本件は完了時レイヤで相補的）。
- red→green 自動検証・成果物の中身評価。
- バイパス env var。

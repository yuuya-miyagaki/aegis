# 実装計画: 監査 fix-forward 優先度3（A9-A15）

> 起点: `docs/audit-report-2026-06-06.md` 優先度3（完了/承認 enforcement の堅牢化・dead weight 整理＝M1-M9＋nits）。
> 方針: fix-forward。TDD（failing test 先行）、全テスト green 維持。自己 grill-plan 済み（末尾）。push はユーザー承認後。

## スコープと設計判断

| 項目 | 対象 | 種別 | 決定 |
|---|---|---|---|
| A9 (M1) | `check_status.py` `--check-completion-evidence` | exit-code 連動 | 違反時 `return 1`（clean/missing は 0）。hook は `\|\| true`＋stdout 依存で非破壊。テストに rc assert 追加 |
| A10 (M2) | `check_status.py:33,761-776` | stale 約束整理 | **hard 化は却下**（`TestPreApproveGateMapping` が ref 無し承認を rc=0 期待・実運用も承認後 ref 付与）。`REF_CHECK_ERROR_VERSION` と「v0.13.0 で hard ERROR」文言を削除し、approval=advisory／completion=enforcement(A9) と明記 |
| A11 (M3) | `check_status.py:527-534` | 整合性 | strict task type＋`task_size=S`（qa/security 免除）で rationale 欠落を **WARNING→FAIL**。非 strict/非 S は WARNING 維持。実 STATUS は M＋rationale 有で無影響 |
| A12 (M4) | `deploy/SKILL.md` `ship-and-docs/SKILL.md`（root+example） | 指示統一 | gate 変更を `bash scripts/update-gate.sh <gate> approve` 経由に（既存 review/security/brainstorm skill と同形）。skills は byte-identical → example 同期＋**A5 mirror に `.claude/skills` 追加**して同期を強制 |
| A13 (M6) | `templates/profiles/standard.json` | 矛盾解消 | recommended から `check-tdd.sh` 除去（README「TDD は full のみ」と整合）。**hooks_include への security hook 登録は非スコープ**（lib 依存と standard の挙動変化＝別判断、優先度4 候補） |
| A14 (M7) | `scripts/restart_summary.py` | dead code | **削除**＋`docs/architecture-overview.md` の2参照除去。/recover 配線は /retro 同様の scaffold 依存を生むため不採用（profiles 未収録）。テスト・コード参照ゼロを確認済 |
| A15 (M5) | `check-secrets.sh:44`（root+example） | 大文字小文字 | `.env` deny grep を `-i` 化（`git add .ENV` を捕捉）。M9: `evidence_integrity_violations:458` の `except` を空配列でなく**合成 violation 返し**（fail-closed・never-raises 契約維持・false-green を可視化）。**M8（PLACEHOLDER_PATTERN）は見送り**＝marker 規約化は全テンプレ変更で invasive・現状は潜在 false-FAIL（実バグ未発現） |

## テスト先行
- A9: `TestCheckCompletionEvidence` の違反系に `rc==1` assert 追加、clean/missing は `rc==0` 維持。
- A11: strict+S+rationale 欠落で validate_status_file が FAIL を返す／rationale 有で通る／非 strict S は WARNING 止まりを assert。
- A15(M5): `check-secrets.sh` に `git add .ENV` → deny の hook テスト追加。M9: `evidence_integrity_violations` に例外時 fallback の単体テスト（root を壊して例外誘発 or monkeypatch）。
- A10/A12/A13/A14: 挙動でなく文言/構成変更。A10 は「stale 文言が出ない」assert で代替可。A12/A13/A14 は契約（drift/contract/scaffold smoke）と mirror で守る。

## 順序
1. A9+A10+A11+M9（check_status.py＋tests）→ 2. A15/M5（secrets＋test）→ 3. A12（skills root+example）＋A5 mirror 拡張 → 4. A13（standard.json）→ 5. A14（削除）→ 全検証＋grill-code。

## リスク
- R1: A11 を FAIL 化で実 STATUS や example fixture が落ちる → 実 STATUS は M+rationale で無影響、test fixture は S 使用箇所を grep して確認。
- R2: A5 mirror に skills 追加で既存 skill drift を検出 → `diff -rq` で現状 ALL IDENTICAL 確認済、A12 編集を両側同期すれば green。
- R3: A13 で check-tdd 除去 → scaffold smoke(tier2) と contract standard が recommended=WARNING のため緑維持のはず。実 scaffold で確認。
- R4: A14 削除で参照切れ → architecture-overview.md の2行除去で解消。import/テスト無しを確認済。

## 検証（完了条件）
- 新規 test red→green。全テスト＋eval tier0-3＋contract full/standard＋drift（mirror に skills 込み）＋status strict 全 green。
- 実 scaffold（full/standard）で smoke。grill-code 後にユーザー承認で commit/push。

## grill-plan 反映（自己グリル catch）
- A10 hard-error は既存テスト/運用を壊す＋completion で既に enforce → **advisory 整理に格下げ**。
- A14 /recover 配線は **/retro と同じ scaffold 依存バグを再生産** → 削除（YAGNI）。
- A13 hooks_include 登録は lib 依存不明＋standard セキュリティ姿勢の挙動変化 → **check-tdd 除去のみ**に限定（矛盾の核だけ潰す）。
- M8 は invasive・潜在バグ → **本バッチ見送り**（明示）。
- M9 は「narrow」でなく **fail-closed 合成 violation**（never-raises を保ちつつ false-green を消す）。
- A12 で **A5 mirror を skills へ拡張**＝編集の同期漏れを構造で防ぐ（A5 の設計を一段強化）。

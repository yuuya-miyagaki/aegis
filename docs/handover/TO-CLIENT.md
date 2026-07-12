# 納品サマリー — iteration 66（v1.26.1）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.26.1（iter66・**PATCH**＝既存 moat の穴を塞ぐ security fix＋内部パーサ統一・公開契約不変・後方互換）
- 日付: 2026-07-12
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/qa/security 一次=opus・親verify/盲検2次/判定=fable）
- 操作マニュアル: 不要（保守者操作に新規ステップなし。挙動変化＝下記「運用上の注意」に記載）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（SF-010 封鎖＋frontmatter 読取意味論統一）

**背景**: iter65 で検出された SF-010＝`task_size` の empty-baseline 窓（未設定＝fresh scaffold / rollover 直後〜brainstorm Step D 前が正規状態）で `docs/STATUS.md` frontmatter を raw-Edit し `task_size: S` を注入すると、`post-status-audit.sh` の migration-grace（`[ -n "$OLD" ]`）が tamper 検知をスキップし plan 儀式を bypass できた。size-aware 化（iter65）で `task_size` が gate 判定に昇格して初めて gate-bypass に転化した moat 回帰。併せて bash（whole-file grep）と python（frontmatter-scope）のパーサ二重実装 drift（F-1/F-2＋(i)(iii)）を統一。

- **Fix ①（本丸）: migration-grace を「真の旧フォーマット snapshot」限定に絞る**（`post-status-audit.sh`）。task field loop は snapshot に `task_type` 行があれば（現行フォーマット）空→値も block、gate loop は snapshot に `gate_approvals:` 節があれば gate 行欠落への空→値も block。grace が残るのは pre-iter43 の真の旧フォーマット（task_type 行なし／gate_approvals 節なし）のみ。正規経路（update-task.sh/update-gate.sh）は snapshot を原子更新するため無影響。
- **Fix ②: `frontmatter_value` を library 級スコープ化**（`hooks/lib/frontmatter.sh`）。`---` ありファイルは frontmatter 内 first-match のみ（本文行の spoof が不可視）・未終端 frontmatter は空 fail-closed・bare ファイル（`.gate-snapshot`）は whole-file 読みを温存。consumer 契約（absent→空+rc0）不変。
- **Fix ③: snapshot 生成を frontmatter スコープ化**（`hooks/lib/snapshot.sh`）＝baseline 毒込み封鎖＋`task_size` 欠落時に最終 grep rc1 で regen が silent fail していた潜在バグを修復＋`gate_approvals:` 必須ガード（gate 節なし baseline の永続 grace 窓を防止）。
- **Fix ④: `gate_value` の本文 fallback を `---` 無しファイル限定に**（F-2）。frontmatter を持つ STATUS では本文の `gate_approvals` ブロックが gate 判定を駆動しない。
- **Fix ⑤: python パーサを bash に意味論同期**（`scripts/check_status.py`）。`extract_scalar_value` を行順 first-match 化（F-1・引用形優先で `key: "S"` が先行 `key: M` を上書きする audit-evading な python=S/bash=M 割れを消去）＋`extract_approval_map` を先勝ち化（重複キーの後勝ち→先勝ち・bash `grep -m1` に一致）。
- **dedup**: `check-gate.sh` の `task_size` 読みを iter65 のインライン scoped 読みから Fix ② の `frontmatter_value` へ集約（読取意味論の単一ソース化・挙動不変）。
- **parity drift-guard**: bash↔python パーサの意味論が drift したら赤く落ちる新規テスト（fixture a-k）。

## 変更ファイル

- `hooks/lib/frontmatter.sh`（frontmatter_value スコープ化・gate_value 本文 fallback 厳格化・値正規化 _strip_scalar・gate_value 行頭 2-space アンカー）
- `hooks/lib/snapshot.sh`（生成スコープ化・regen バグ修復・gate 節ガード）
- `hooks/post-status-audit.sh`（migration-grace 絞り込み＝task fields＋gate loop）
- `scripts/check_status.py`（extract_scalar_value first-match・extract_approval_map 先勝ち）
- `hooks/check-gate.sh`（task_size 読みを frontmatter_value へ dedup）
- `tests/`（test_frontmatter_lib.py・test_snapshot_helper.py・test_snapshot_writers.py・test_post_status_audit_task_tamper.py・test_check_status_parsers.py〔新規〕・test_parser_parity_driftguard.py〔新規〕）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.26.0→1.26.1）

## 証拠

- 設計: `docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md`／計画: `docs/plans/2026-07-12-iter66-sf010-parser-unification-implementation-plan.md`
- review: `docs/qa-reports/iter66-review.md`（1次4角度 finder=opus→親verify=fable・盲検2次=fable approve 収束・Major×4 fix-forward 6148a60）
- qa: `docs/qa-reports/iter66-qa.md`（機能対照表 12件PASS・fresh変異 M1-M5 全kill〔計14テスト〕・SF-010 閉塞 4ケース hook 直接発火再実測・**full suite 1138 passed/2 skipped**）
- security: `docs/qa-reports/iter66-security.md`（1次 opus＋盲検2次 fable 収束 approve・新規脆弱性0・SF-010 消化実測・SF-011 起票）

## テスト・QA・セキュリティ要約

- **テスト**: full suite 1138 passed / 2 skipped（環境条件つき既知 skip＝case-insensitive FS・shellcheck 不在）。contract PASS。B1 drill は per-task コミット済みで skip（sanctioned 縁ケース・iter64 conf7）＋qa 一次 fresh 変異 M1-M5 全 kill（計14テスト・scratch clone 内）＋SF-010 閉塞を pytest 非経由の hook 直接発火で 4 ケース独立再実測。
- **review**: Major×4（bash 値正規化を python に一致／gate_value 行頭 2-space アンカー／parity fixture g-k 追加）を fix-forward `6148a60`。
- **security**: 新規 injection/secrets/data-exposure/緩め bypass なし（1次 opus＋盲検2次 fable が実フック実測）。全変更 fail-closed 方向。SF-010 の (i)(ii)(iii) を消化。

## 残留リスク・既知の制限事項

- **SF-010（Medium・iter66 で封鎖・docs で CLOSED 化予定）**: 本反復で本丸（Fix ①）＋(i) 重複キー先勝ち乖離（Fix ⑤）＋(ii) 引用形優先（Fix ⑤ first-match）＋(iii) gate_value 本文 fallback（Fix ④）を消化。canonical size 注入・gate 行欠落注入とも BLOCK、真の旧フォーマット grace 温存、正規経路無影響を hook 直接発火で実測。
- **SF-011（Low・OPEN・新規起票）**: bash `read_frontmatter`（終端 `^---[[:space:]]*$`・末尾スペース許容）と python `extract_frontmatter`（strict `\A---\n...\n---\n`）の終端デリミタ許容差。frontmatter 途中に `--- ` を挿入し後続に `task_size: S` を隠すと python `check_phase_transition` だけが読み phase-skip を数字上許容し得る。**pre-existing**（baseline deb4a8a=HEAD で同挙動・この diff の回帰ではない）かつ **3層 contained**（check-gate は bash empty→plan gate→deny／gate 承認は update-gate.sh 必須／`--strict`/contract の PyYAML cross-check が reject＝"done" 洗浄不能）で実害到達なし。次反復 hardening（read_frontmatter 終端 strict 化 or parity fixture 追加）。詳細 `docs/security-followups.md` SF-011。
- **flaky（回帰外）**: `test_update_gate_lock.py::test_lock_held_blocks_noop_approve`（lock 待ちタイミング・full-review R10 test#8 既知）。本 diff は update-gate/lock/snapshot 不接触。

## 運用上の注意

- **tamper-evidence の穴が塞がった**: `task_size` empty-baseline 窓での raw-Edit 注入が tamper audit で block されるようになった（fail-closed 方向のみ・正規 `update-task.sh`/`update-gate.sh` 経路は無影響）。
- **frontmatter 読取が本文 spoof に強くなった**: STATUS の本文に `task_size:`/`gate_approvals:` 行を書いても gate/audit 判定は frontmatter のみを見る。bash と python のパーサが同じ値を読むよう統一（duplicate キーは先勝ち・引用形は行順優先）。
- **未 push**: 実装コミット済み・**push 手前で停止**（push は `gh auth switch --user yuuya-miyagaki`）。

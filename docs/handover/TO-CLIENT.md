# 納品サマリー — iteration 65（v1.26.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.26.0（iter65・MINOR＝S サイズフローの挙動改善・後方互換）
- 日付: 2026-07-12
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/security 判定・盲検2次=fable）
- 操作マニュアル: 不要（保守者操作に新規ステップなし。挙動変化＝下記「運用上の注意」に記載）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（full-review 2026-07-06 §R2🔴 / §4 Phase 1 項目 1-4「S サイズ修復」）

**背景**: S サイズ（1ファイル級）は feature/refactor/framework でコード編集が構造的に不能だった。
`hooks/check-gate.sh` が `task_size` を参照せずコード編集を無条件で **plan gate** 承認要求するが、S の
フェーズ集合に plan は存在せず、strict task type は plan を n/a 化もできない。結果、全タスクが M 儀式へ逃避
（過剰オーバーヘッドの主因）。rule 文書「skipped phases exempt their gates」・python 実装は S を免除済みで、
**bash hook だけが未実装の三者不整合**を bash 側へ揃えた。

- **Fix 1（本丸）: `hooks/check-gate.sh` を size-aware 化**。コード編集ゲートを「size フローで implement 直前の
  承認ゲート」に差替え＝`task_size=S`→**brainstorm gate**／それ以外（M/L/未設定/不正値）→**plan gate**（保守的
  デフォルト・gate を緩めない）。判定は **pure-bash**（`read_frontmatter`/`gate_value`。python 委譲は fail-open
  退行のため不採用）。`approved` OR `n/a` を許容＝bugfix/hotfix も自然通過。`task_size` は **frontmatter スコープ
  読み**（本文行の spoof を防止）。
- **Fix 2: `check_phase_transition` の terminal 空リスト穴を明示 deny 化**。前進遷移で `allowed_after_old` が空
  （old が size の terminal）だと隣接検査を素通りする穴を封鎖（Fix 3a 後は dormant だが将来 size 追加への
  defense in depth）。
- **Fix 3a: `SIZE_ALLOWED_PHASES["S"]` に `docs` 追加**。S の terminal を M/L と統一し、ship→docs が「transition
  検査 rc0／静的検査 FAIL」に割れる罠 q を根絶。docs は gate 強制されない（`dev_ready_for_client` は phase==docs
  を要求しない）ため純加算的で新儀式は増えない。
- **drift-guard テスト**: bash 側の size→gate ハードコードが python SoT（`SIZE_ALLOWED_PHASES`/
  `PHASE_REQUIRES_GATES`）から drift したら赤く落ちる parity guard（iter53 REGEX↔WARN パターン）。
- **guidance 同期**: `.claude/rules/state-machine.md` 表・`docs/architecture-overview.md` 姉妹表の S 列を
  `impl→review→ship→docs` に統一（R9 型 guidance↔enforcement drift 防止）。

## 変更ファイル

- `hooks/check-gate.sh`（size-aware gate＋frontmatter スコープ読み）
- `scripts/check_status.py`（SIZE_ALLOWED_PHASES[S]+docs・Fix 2 terminal deny）
- `tests/test_check_gate_size_aware.py`（新規・8論理ケース＋drift-guard）
- `tests/test_check_status.py`（Fix2/3a テスト）
- `.claude/rules/state-machine.md`・`docs/architecture-overview.md`（表同期）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.25.0→1.26.0）

## 証拠

- 設計: `docs/specs/2026-07-10-iter65-s-size-repair-design.md`／計画: `docs/plans/2026-07-10-iter65-s-size-repair-implementation-plan.md`
- review: `docs/qa-reports/iter65-review.md`（1次4角度 finder→親verify・盲検2次 approve_with_notes 収束・Major3件 fix-forward）
- qa: `docs/qa-reports/iter65-qa.md`（機能対照表7件PASS・fresh変異 M1-M4 全kill・**full suite 1096 passed/2 skipped**）
- security: `docs/qa-reports/iter65-security.md`（1次+盲検2次 approve_with_notes・injection/secrets なし・SF-010 residual ack）

## テスト・QA・セキュリティ要約

- **テスト**: full suite 1096 passed / 2 skipped（環境条件つき既知 skip）。B1 drill は per-task コミット済みで skip
  （sanctioned 縁ケース）＋qa 一次 fresh 確認変異 M1-M4 全 kill＋review 変異分析 check-gate 7/7・check_status 3/3 kill。
- **review**: Major 3件（本文 spoof 封鎖 / else 分岐 n/a 許容ピン / 姉妹表同期）を fix-forward。
- **security**: diff 起因の新規 injection/secrets/data-exposure/緩め bypass なし（両者実フック実測）。fail-closed 保存。

## 残留リスク・既知の制限事項

- **SF-010（Medium・OPEN・accepted residual）**: `task_size` empty-baseline（未設定窓＝fresh scaffold / rollover
  直後〜brainstorm Step D 前）で frontmatter を raw-Edit して `task_size: S` を注入すると、`post-status-audit.sh`
  の migration-grace（`[ -n "$OLD_TF" ]`）が tamper 検知をスキップし plan 儀式を bypass できる。**ユーザー承認の
  もと次反復（iter66）に分離**。severity Medium（end-state は authorized な `update-task.sh --size S`＝RISK-3 で
  既に到達可能かつ受容済みで、SF-010 の capability 増分は監査ログ行の有無のみ＝新 capability 非解錠。brainstorm
  ハードゲート必須・完全可視）。F-1/F-2 パーサ二重実装 drift も同スコープ。詳細 `docs/security-followups.md` SF-010。
- **flaky（回帰外）**: `test_update_gate_lock.py::test_lock_held_blocks_noop_approve` が full-suite 負荷下で稀に
  fail（lock 待ちタイミング・full-review R10 test#8 既知）。本 diff は update-gate/lock/snapshot 不接触。

## 運用上の注意

- **S サイズが実用可能に**: これまで S は feature/refactor でコード編集不能（全タスク M へ逃避）だったが、
  1ファイル級の変更は S（brainstorm→implement→review→ship→docs・qa/security/deploy 免除）で回せる。
  S 誤ラベルは `task_size_rationale` 必須（strict type の空欄は静的検査 FAIL）で抑止。
- **S も docs terminal**: S タスクも ship→docs（LEARNINGS 更新）へ進める。docs は強制ではない（ship 完了も可）。
- **未 push**: 実装コミット済み・**push 手前で停止**（push は `gh auth switch --user yuuya-miyagaki`）。

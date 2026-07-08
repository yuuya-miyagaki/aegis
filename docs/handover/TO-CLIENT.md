# 納品サマリー — iteration 63（v1.24.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.24.0（iter63・MINOR＝後方互換の新能力）
- 日付: 2026-07-08
- 担当者: aegis dev フロー（security 1次は in-session・盲検2次は多エージェント）
- 操作マニュアル: 不要（installer 内部の自己修復＝保守者の操作手順に新規ステップなし。挙動変化は本サマリに記載）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲

- 完了: `bin/setup.sh` の self-heal unlock（full-review 2026-07-06 **R3**＝正規 upgrade 手順が OS-lock 済み install で死ぬ問題の解消）。
  1. **self-heal unlock**（`selfheal_unlock_target()`・全 copy 前に発火）: cp-lock（moat layer-2）が非 framework task_type のセッション開始時に安定 control-plane を `chmod a-w` するため、status_doctor が案内する正規 upgrade 手順（`bin/setup.sh` 再実行）が「一度でも使われた install」で `cp: Permission denied` により途中死し、混在版（mixed-version）の木を残していた。これを、**(a) aegis install マーカー かつ (b) 実 lock 検出（`aegis_cp_verify`）** の AND ゲートでのみ発火する一時 unlock で解消。対象は cp-lock 正本の CP path 集合に限定（任意 dir を触らない・symlink 非追従）。再 lock は意図的に行わず、target の次回 session-start が task_type に応じて復元（NOTE 2行で unlock 窓を可視化）。
  2. **帰属エラー**（`explain_unwritable_dst()`・`copy_file`/`copy_file_force` の mkdir/cp を `if ! …; then explain; exit 1` 型へ）: `set -e` の無説明即死を、原因（dst or 最近傍実在祖先 dir の non-writable）を帰属し remediation（env を外して再実行／手動 unlock）を示す明示 abort に置換。無関係な失敗は誤帰属せず generic ERROR のみ。
  3. **opt-out は fail-closed**: `AEGIS_SETUP_SELFHEAL=off`（小文字・AEGIS_NUDGE 慣習）は heal を無効化する＝機能を**減らす**方向のみで、locked target は帰属エラーで fail-closed。バイパス lever にならない。
  4. **回帰テスト新設**（`tests/test_setup_locked_target_upgrade.py`・4本）: T1 locked-upgrade self-heal（stale 化→lock→再 install=rc0・ソース一致・`.bak`・NOTE・unlock 維持）／T2 fresh install 無副作用／T3 opt-out fail-closed／T4 非 aegis dir 不介入（perms byte 不変）。ROOTUSER は lock 依存 T1/T3/T4 を skip（repo 慣習）。

## 証拠

- 実装計画: docs/plans/2026-07-07-iter63-setup-self-heal-plan.md（grill-plan 致命3=祖先遡り/ROOTUSER skip/bump3箇所目 反映）
- 設計: docs/specs/2026-07-07-iter63-setup-self-heal-design.md（推奨アプローチ1-4・セキュリティ考慮 受容残余）
- レビュー: docs/qa-reports/iter63-review.md（1次 approve_with_notes〔7項目 action/expected/observed/verdict〕＋盲検2次 approve_with_notes・Major 0・full 1076 passed/2 skipped）
- QA: docs/qa-reports/iter63-qa.md（**B1 実 drill 7/7 caught**〔初回生存1→テスト強化で封鎖＝drill 実効性実証〕・full suite drill 後再実走 recorded green〔pyc 教訓〕）
- セキュリティ: docs/qa-reports/iter63-security.md（1次 approve〔in-session・6節 実 evidence・Findings HIGH/MEDIUM/LOW 0〕＋盲検2次 approve_with_notes・docs/qa-reports/iter63-security-2nd.md）。🟡 依存監査 N/A＋approve_with_notes notes を ack 承認（judge-security.md）。
- 動機の正本: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R3・§4 Phase 0-3

## 既知のギャップ

- **unlock 窓（受容残余 (a)）**: setup 完了〜次回 session-start まで target CP が writable。通常の framework-mode セッションと等価な露出で、実行者＝upgrade を行う owner 自身。NOTE 出力で可視・監査可能。
- **session 内 setup 実行によるバイパス（受容残余 (b)）**: エージェントが target セッション内で framework clone の setup.sh を走らせて moat を外す経路は layer-2 脅威モデル（偶発書込み防御）の scope 外＝owner の `chmod u+w` 常時可能と等価。
- **marker leg の OR（LOW-1・1次＋盲検2次が独立に同定）**: 発火 (a) は `.aegis-install-version` **or** `hooks/lib/cp-lock.sh` の OR。非 aegis dir でも後者を持ち かつ CP 名 dir を read-only にして実 lock 検出も満たすと `chmod u+w` されうるが、影響は owner 書込み復元のみ（昇格/chown/setuid/symlink 追従なし）。fingerprint 厳格化（tree-hash 等）は **Phase 1 罠根切り**（full-review §2 R6）で別途対処。

## 配備と運用

- 環境: Claude Code ネイティブ。変更は `bin/setup.sh`（installer）のみ＝新規 script/hook なし・公開契約（scripts-manifest / hook 集合）変更なし。
- アクセス: 変更なし。
- 監視: なし。unlock 発火時は setup 出力に NOTE 2行（「target was OS-locked … restored for this upgrade」／「lock re-engages at the target's next session start」）。

## 次の推奨アクション

- 実装 + docs + STATUS を 1 コミット → **push 手前で停止しユーザー確認**（push = gh auth switch --user yuuya-miyagaki）。
- 以降: full-review §4 **Phase 1（罠の根切り）**: fingerprint tree-hash 化（本 iter の OR marker LOW-1 も解消）・judge skip-and-continue・S サイズ修復・approve --ref 原子化・drill NO_RUN 拒否＋**pyc キャッシュ恒久対策**〔iter62 起票〕。→ Phase 2 純化 → Phase 3 plugin/CI。

# 納品サマリー — iteration 68（v1.27.0）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.27.0（iter68・**MINOR**＝`approve --ref` 後方互換 CLI 追加＋pending/n/a+ref を FAIL→advisory 緩和。公開契約は後方互換〔既存 `approve` 不変・緩和方向〕）
- 日付: 2026-07-13
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/qa 一次=opus・security 1次=親 in-session fable・親verify/盲検2次=fable）
- 操作マニュアル: 不要（むしろ従来必要だった「record→ref→承認を中断なく連続」規律が1コマンドに畳まれ**不要化**＝下記「運用上の注意」）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（update-gate `approve --ref` 原子化＝全体レビュー §4 Phase 1 項目 1-3）

**背景**: ゲート承認値（`gate_approvals.<gate>`）と evidence ref（`current_refs.<gate>`）は別ステップでしか書けず、どちらの順でも `check_framework_contract` が赤くなる窓が開いた（ref 先置き→pending+ref=stale FAIL／approve 先→approved+空=FAIL）。加えて approve 時に judge カード全文を**状態書込みより前に** stdout へ流すため、`| head` 等の pipe 早期クローズで SIGPIPE 死＝gate 未承認のまま出力だけ欠ける罠があった（全体レビュー R6 罠 a,b,c・LEARNINGS ref-window 軸＝iter35/43/64/65 で被弾）。

- **(1) `approve --ref <path>` 原子書込み**: ゲート値と ref を**単一 sed パス（TMP+mv）**で同時確定＝赤窓が構造的に消滅。`--ref` は repo 相対・`..` 拒否・文字 allowlist `[A-Za-z0-9._/-]`・空文字拒否・実在ファイル必須で検証（不正入力は状態変更前に exit 1）。既存の `approve`（ref なし）は不変。
- **(2) SIGPIPE fail-safe**: `trap` PIPE 無視＋approve 経路を「検証→**状態書込み**→ACK 追記→snapshot→best-effort 出力」に並べ替え。承認を主張する出力は必ず状態永続化の後。書込みは明示 `if ! sed` / `if ! mv` で fail-closed（`&&` リストの set -e 免除による偽成功を封鎖）。
- **(3) pending/n/a+ref を advisory 降格**: `evidence_integrity_violations` の「pending/n/a gate に ref 残置」を FAIL→**stderr WARNING**（stdout は violation 専用チャネル＝TaskCompleted hook の契約を維持）。approved+空 ref・ref 実在検査・client artifact 検査は**FAIL 維持**（無緩和）。na も reset 同様に ref を null 化。
- **(4) judge 統合**: judge（`build-judge-card`）が `AEGIS_PENDING_REF`（update-gate が実在検証済みで同一書込みに確定する path）を claims 源として尊重＝原子 approve の judge gate が常時 🟡+ack に落ちるのを回避。tier-1 facts（fp/tests/secrets/stubs）は不接触。

## 変更ファイル

- `scripts/update-gate.sh`（flag parser・--ref 検証・単一 sed 三態・trap・書込み先行・fail-closed・print_report）
- `scripts/check_status.py`（pending/n/a+ref を stderr advisory 降格・`AEGIS_PENDING_REF` で空 ref ADVISORY 抑止）
- `scripts/build-judge-card.py`（`AEGIS_PENDING_REF` を claims 源として尊重・1分岐）
- `hooks/check-task-completed.sh`（stdout=violation / stderr=advisory のチャネル契約コメント）
- `tests/`: `test_update_gate_ref_atomic.py`（新規20本）・`test_check_status.py`（advisory 降格へ書換＋追加）・`test_judge_card.py`（env override 2本）・`test_skill_guidance_tokens.py`（意味論更新）
- guidance: `.claude/commands/gate.md`・`CLAUDE.md`（完了規則1文）・skill 6枚・onboarding 2枚（approve --ref 正順へ同期）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.26.2→1.27.0）

## 証拠

- 設計: `docs/specs/2026-07-12-iter68-update-gate-ref-atomic-design.md`（＋brainstorm-record）／計画: `docs/plans/2026-07-12-iter68-update-gate-ref-atomic-implementation-plan.md`（grill-plan 反映記録付き）
- レビュー: `docs/qa-reports/iter68-review.md`（1次4角度＋盲検2次・PASS。Major 4件〔F-1 EPIPE レース／T-1 変異穴／T-2 fixture 代表性／盲検2次 4-A fail-open〕全て fix-forward 済み・実測検証付き）
- QA: `docs/qa-reports/iter68-qa.md`（fresh 変異 M1-M6 全 KILLED〔独立 clone〕・full suite 1173 passed/2 skipped・実環境 E2E＝本 iter 機能で review gate を原子承認）
- セキュリティ: `docs/qa-reports/iter68-security.md`（1次 in-session＋盲検2次 物理隔離 clone とも approve・新規脆弱性0・env/--ref は tier-1 不接触・injection 全拒否・fail-open 4-A 修正確認）

## テスト・QA・セキュリティ結果の要約

- full suite: **1173 passed / 2 skipped**（record green・以降 docs のみ＝fp 不変）／`check_framework_contract` PASS
- 変異検証: qa の fresh 変異 M1-M6 全 KILLED＋review テスト強度の (a)-(i) 9種＝原子性・順序・fail-closed・advisory 降格・judge env を多層でピン
- 敵対検証: F-1（trap PIPE 無視下の grep 早期終了 × frontmatter_section printf の EPIPE レース）を親が単離再現 **58/3000**→修正後 **0/3000**（早期終了消費者を全量読み/変数キャプチャ+case に置換）

## 残留リスク・既知の制限事項

- **SF-013**（OPEN・Low・pre-existing・contained・iter69+ hardening）: (a) update-gate の sed 範囲終端 `/^[a-z]/` が `---` で閉じない（canonical STATUS では到達不能）／(b) `--ref` の `-f` が symlink を辿る（ref は非実行の証跡・tamper writer 前提で capability 増分なし）。いずれも baseline 8ab52ed=HEAD の差分実走で pre-existing 実証済み。
- 繰延（iter69/70 スイープ）: client_ready_for_dev の `--ref` 実行経路テスト（重量 fixture）・SF-011/SF-012（既存 backlog）。
- 既知 flaky: `test_update_gate_lock`（lock 待ちタイミング・本 diff 不接触＝回帰外・本 run 全 green）。

## 運用上の注意点

- **ゲート承認の推奨形が変わった**: `bash scripts/update-gate.sh <gate> approve --ref <evidence-path>` で承認と evidence ref 設定を1コマンドに。従来の「record green→ref を raw-Edit→中断なく approve」の暗記規律は不要（原子化で赤窓が消えたため）。既存の `approve`（ref なし）も引き続き動作。
- pending/n/a gate に ref が残っていても contract は赤くならず advisory WARNING（stderr）になった。ただし approved gate の ref 欠落・ref 先ファイル不在は従来どおり完了時に FAIL。

## 手続き上の注記（プロセス透明性）

security 1次に最初ディスパッチしたサブエージェントが read-only 拘束に違反し本体 tree を汚した（オートフォーマッタ由来の空白整形・意味変更なし＋ドリル成果物上書き）。両ファイルは committed 状態へ復元し、当該 run は破棄、1次は親が独立 clone 上で全項目再実測した（詳細は iter68-security.md 手続き注記）。教訓は検証委譲の物理隔離 clone 標準化として LEARNINGS へ記録。

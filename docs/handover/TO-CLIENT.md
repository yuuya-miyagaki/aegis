# 納品サマリー — iteration 67（v1.26.2）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 納品サマリー

- リリース / ビルド: aegis v1.26.2（iter67・**PATCH**＝judge の gate 判定 fix・公開契約不変・後方互換）
- 日付: 2026-07-12
- 担当者: aegis dev フロー（工程別モデル tiering: 疑う=Fable 5／書く=Opus 4.8。実装=implementer opus・review/qa/security 一次=opus・親verify/盲検2次/判定=fable）
- 操作マニュアル: 不要（保守者操作に新規ステップなし。むしろ従来必要だった手順規律が1つ不要化＝下記「運用上の注意」）
- 運用 RUNBOOK: 不要（新規運用手順なし）
- UAT 結果: 不要（ACCEPTANCE 未定義の framework イテレーション）

## 実装範囲（judge test-fact 判定堅牢化＝trust-scan）

**背景**: gate 承認時に走る judge の tier-1 test-fact（`scripts/build-judge-card.py::read_test_result`）は evidence-log を新しい順に走査し、**最初の** test-runner マッチエントリで green/red/unverified を確定していた。そのエントリが「observed かつ marker 未検証（＝観測者が本物のテストサマリを確認できなかった）」で status=ok だと、直下に fp 一致の trusted green があっても `unverified`（🟡）を返した。結果、record green の後に件数確認の生 `pytest --collect-only` や `pytest | tail` を1回走らせるだけで gate が 🟡 降格し、ack 儀式または再 record が必要になった（iter64/65/66 で3回顕在化＝LEARNINGS conf9 line137）。

- **trust-scan（本丸）**: 走査中、undecidable（observed かつ `marker_verified≠true`）かつ status=ok のエントリを「green も red も証明できない＝情報ゼロ」として**透明**（skip して走査継続）にし、最新の decidable エントリ（`src="manual"`、または observed で `marker_verified=true`）が判定を下す。`build-judge-card.py::read_test_result` の走査ループに1分岐を挿入（fp 検査の直前）＋docstring を trust-scan 意味論に同期。
- **不変（C-2/K-1/fp backstop 無緩和）**: undecidable-fail（status=fail）は従来どおり終端 `unverified`（runner 形の失敗信号を保持）・decidable の fp 不一致は終端 `unverified`（stale green を蘇生しない）・decidable エントリゼロは `unverified`（silent-green の下限）。
- **副産物＝厳格化**: decidable red を後続の no-run コマンドで red→🟡 に「洗浄」する経路が閉じた（透明化で red が保持される）。

## 変更ファイル

- `scripts/build-judge-card.py`（`read_test_result` に undecidable-ok 透明化1分岐＋docstring 同期）
- `tests/test_test_runner_realness.py`（`TestReadTestResultTrustScan` 系列テスト11件〔計画10＋fix-forward の3段系列〕新規）
- `tests/test_judge_card.py`（既存ピン `test_newest_stale_does_not_fall_back_to_older_fresh` の理由コメントに decidable 限定子を追記・アサーション不変）
- `docs/architecture-overview.md`（judge 記述を trust-scan 意味論に同期・1文）
- version bump: `check_framework_contract.py`／`docs/STATUS.md`／`templates/STATUS.template.md`（1.26.1→1.26.2）

## 証拠

- 設計: `docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md`（＋brainstorm-record）／計画: `docs/plans/2026-07-12-iter67-judge-test-fact-robustness-implementation-plan.md`
- review: `docs/qa-reports/iter67-review.md`（1次4角度〔仕様/敵対/テスト強度/保守性〕finder=opus→親verify=fable・盲検2次=fable・approve 系収束・fix-forward 2件 70ace79/0739a79）
- qa: `docs/qa-reports/iter67-qa.md`（機能対照表 8件PASS・fresh変異 M1-M5 全kill＋grill 変異2種・**実環境 E2E 差分＝同一 evidence-log で OLD(d2c4dd6)=unverified／NEW=green**・scoped 99 passed）
- security: `docs/qa-reports/iter67-security.md`（1次 opus＋盲検2次 fable 収束 approve・新規脆弱性0・gate-bypass 4攻撃面 differential 実走・SF-012 起票）

## テスト・QA・セキュリティ要約

- **テスト**: 対象2ファイル 99 passed・full suite green（record-test-result・v1.26.2 tree で実証）・contract PASS。B1 drill は per-task コミット済みで sanctioned skip（iter64 conf7）＋fresh 変異 M1-M5 全 kill（独立 scratch clone・scoped 99 テスト）。
- **review**: Minor を fix-forward 2件（3段系列ピン追加・docstring の Decidable 定義を実挙動に正確化＋LEARNINGS 導線＋guidance に undecidable-fail 終端補記）。
- **security**: 新規 injection/secrets/data-exposure/gate-bypass なし（differential harness で baseline vs HEAD 実走）。red 可視性はむしろ厳格化。検出2件はいずれも pre-existing（差分実走で OLD=NEW 確定）＝SF-012 起票。

## 残留リスク・既知の制限事項

- **SF-012（Low・OPEN・pre-existing・新規起票）**: evidence 信頼判定の hardening 2件 — (a) washed-green（`pytest; true` の exit 洗浄＋pass-marker regex が `1 failed, 2 passed` にもマッチ→decidable green）、(b) unknown-src decidable-by-default（src 欠如/異値が decidable 扱い）。いずれも 1次/2次が differential 実走で **baseline d2c4dd6 と同挙動＝本 iter の回帰でない**を確定。実 writer は observed/manual のみ発行・任意 log 書込みは脅威モデル外・(a) の発火には明示的 exit 洗浄（自己欺瞞）が必要＝contained。iter68 hardening 候補（writer 側の marker/status 整合軸＋reader 側 src allowlist）。詳細 `docs/security-followups.md` SF-012。
- **SF-011（Low・OPEN・pre-existing）**: frontmatter 終端デリミタ差（iter66 起票・未着手）。
- **flaky（回帰外）**: `test_update_gate_lock`（lock 待ちタイミング・full-review R10 test#8 既知）。本 iter の全 run で顕在化せず・本 diff は update-gate/lock 不接触。
- deps: N/A（外部依存パッケージなし・pip/npm マニフェスト不在＝judge の deps は unverified🟡 で ack）。
- 公開契約: **不変**（`read_test_result` の戻り値集合〔green/red/unverified〕・呼出側〔collect_facts〕・observer 契約〔evidence.sh〕・token 契約・skill boot-path 全て変更なし）。SemVer PATCH 妥当。

## 運用上の注意（挙動変化）

- **gate 承認時の judge が「件数確認の生 pytest ノイズ」で 🟡 降格しなくなった**。record green（`record-test-result.py`）の後に `pytest --collect-only` 等を走らせても、直近の trusted green が判定を保つ。従来必要だった「件数確認は record の前に・締めは必ず record-test-result」という手順規律（LEARNINGS conf9 line137 の test-fact 軸）は、この fix で機構的に不要化された。ただし **record→ref→承認の間に生 pytest を挟まない運用自体は ref-window の contract 不変条件（別軸・未解決）のため引き続き推奨**。
- **decidable red は no-run コマンドで隠せなくなった**（厳格化）。テストが実際に赤い状態で承認しようとすると、その後に collect-only 等を走らせても judge は red を保持する。
- **未 push**: 実装コミット済み・**push 手前で停止**（push は `gh auth switch --user yuuya-miyagaki`）。

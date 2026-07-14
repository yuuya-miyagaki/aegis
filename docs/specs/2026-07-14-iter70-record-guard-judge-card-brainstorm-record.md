# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-14（iteration 70）

## テーマ

- Phase 1 最終項目 1-6: (1) record-test-result 引数事前検証〔R6 罠 n〕 (2) deps 無 manifest info 降格〔gate F6〕 (3) judge カード tests スコープ表示〔test #3〕

## コンテキスト

- 現在の状況: Phase 1「罠の根切り」は 1-1〜1-5 完了（iter64/67/68/65/69）。残り 1-6 の 3 サブ項目で Phase 1 完遂。
- きっかけ: docs/full-review-2026-07-06-six-dimensions-evolution.md §R6（罠 n）・§R10 gate F6・test #3。
- 自走モードのため、決定はユーザー質問でなく「推奨＋根拠」を本記録に残す方式（過去 iter と同運用）。

## 検討したアプローチ

### サブ項目 (1) record-test-result 引数事前検証

#### アプローチ A: judge 単一ソースヘルパ抽出＋drill.check_no_run_command 再利用（採用）

- 概要: build-judge-card.py の read_test_result 内にある正規化＋runner-regex 照合を関数抽出し、record-test-result.py が**実行前・記録前**に (a) runner 照合（judge と同一パイプライン: `[:500]` 切詰→`\n`→`;`→DQ/SQ マスク→AEGIS_TEST_RUNNER_REGEX） (b) `drill.check_no_run_command`（shlex 正規化・fail-closed、iter69 実装）を呼ぶ。非該当は usage エラー（rc≠0・ログ書込みなし）。patterns 読込不能も fail-closed エラー。
- 利点: 検査系＝消費系の正規化が構造的に一致（iter69 教訓 conf8「サニタイズは実行系と同じ正規化で」）。NO_RUN も iter69 の shlex 正規化済み実装をそのまま消費＝ドリフトゼロ。判定不能エントリの発生源（引数事故）を書込み前に遮断。
- 欠点: build-judge-card.py に軽微なリファクタが入る（read_test_result の照合部を共有ヘルパへ）。

#### アプローチ B: record-test-result 内で patterns.sh を独自ロードして照合

- 概要: record 側に regex ロード＋照合を再実装。
- 利点: judge のリファクタ不要。
- 欠点: 第2の実装＝正規化ドリフトの温床（iter69 で Critical を生んだ構造そのもの）。却下。

#### アプローチ C: runner-regex のみ検証（NO_RUN 検査なし）

- 概要: 最小実装。full-review の文言（AEGIS_TEST_RUNNER_REGEX で事前検証）に限定。
- 利点: 差分最小。
- 欠点: `pytest --collect-only` の手動記録が decidable green として judge を欺ける穴が残る（SF-014 と同クラス・manual 経路）。NO_RUN 再利用は数行なので割に合わない。却下。

### サブ項目 (2) deps 無 manifest info 降格

#### アプローチ A: audit_deps に第4状態 'no-manifest' を追加（採用）

- 概要: requirements.txt/lock も package.json も無い場合のみ `'no-manifest'` を返し、compute_verdict は 🟡 でなく info 行（「依存 manifest なし＝監査対象なし」）。package.json あり lockfile なし＝**unverified 維持**（manifest 実在・監査不能は実 🟡）。ツール不在/timeout も unverified 維持。
- 利点: 依存ゼロ repo の毎 iteration 無意味 ack（踏み車）を解消しつつ、fail-visible 維持（カードに状態は表示）。deps は元々 advisory-only（never blocks）なのでブロック力の低下はゼロ。
- 欠点: audit_deps の返り値集合が広がる（消費者は compute_verdict と render_card のみ・影響局所）。

#### アプローチ B: compute_verdict 側で manifest 有無を再チェック

- 概要: audit_deps は不変、判定側で分岐。
- 欠点: manifest 知識が 2 関数へ二重化＝ドリフト。却下。

#### アプローチ C: no-manifest を 'clean' に丸める

- 概要: 監査対象なし＝clean 扱い。
- 欠点: 監査していないのに clean は嘘（fail-visible 違反・カードから状態が消える）。却下。

### サブ項目 (3) judge カード tests スコープ表示

#### アプローチ A: read_test_result_detail 抽出＋互換 wrapper（採用）

- 概要: 走査本体を `read_test_result_detail(root) -> dict`（tests/cmd/src/ts）に抽出し、既存 `read_test_result` は互換 wrapper として文字列を返す。collect_facts が detail を facts（tests_cmd/tests_src/tests_ts）へ載せ、render_card が決定エントリのスコープを表示。cmd は表示前にサニタイズ（改行→`;`・バッククォート除去・120 字切詰）＝カード注入（偽見出し）防止。
- 利点: 判定と表示が同一走査＝乖離なし。既存 read_test_result のピンテスト（~30 箇所）・evidence.sh との契約は不変。判定意味論の変更ゼロ（表示のみ）。
- 欠点: facts のキーが 3 つ増える（except パスは .get で欠落許容）。

#### アプローチ B: read_test_result の返り値を tuple に変更

- 欠点: ピンテスト・importlib 消費者を一斉破壊。却下。

#### アプローチ C: render_card が evidence-log を再走査

- 欠点: 判定に使ったエントリと表示エントリが乖離しうる（別走査＝別結果）。却下。

## 決定

- 採用アプローチ: (1)A + (2)A + (3)A
- 採用理由: いずれも「単一ソース消費・fail-visible 維持・判定意味論の最小変更」を満たす。iter69 教訓（正規化不整合・denylist の限界）と整合。
- 不採用理由: 各項の欠点欄のとおり（ドリフト温床・fail-visible 違反・消費者破壊）。

## スコープ境界

- やること: 上記 3 サブ項目＋回帰テスト（新規 tests/test_record_test_result.py・test_judge_card.py 追記）。
- やらないこと: SF-011/012/013/014 本体（positive N-tests-executed proof は iter71+）、observed（evidence.sh）経路の変更、AEGIS_TEST_RUNNER_REGEX 自体の拡張、fingerprint 機構、runner regex の bash/python パリティ機構変更。

## 未解決事項

- なし（判定への影響: (1) 記録の事前拒否＝厳格化のみ、(2) 🟡→info は advisory 内の降格でブロック力不変、(3) 表示のみ）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-14-iter70-record-guard-judge-card-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

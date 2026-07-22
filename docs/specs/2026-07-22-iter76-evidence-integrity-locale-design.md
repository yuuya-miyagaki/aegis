# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-22-iter76-evidence-integrity-locale-brainstorm-record.md`
- 要件: なし（framework 自己改善）。動機正本＝`docs/full-review-2026-07-19-dual-codex-fable.md` §4.2/§4.3/§5 iter76 行・`docs/security-followups.md` SF-012/SF-018

## 問題整理

- 背景: judge の green 判定は「status==ok（exit code 由来）×marker_verified（≥1 test 実行の証明）」だが、exit code は shell 演算子で洗浄可能（`pytest -q; true` → status=ok・出力の `1 failed` サマリは marker=true）＝**失敗 run が decidable green 化**（§4.2・親再現済み）。`|| echo`/`; true` は pipefail 非依存の無条件 exit0 で**事故的到達が現実的**。また `check-runtime-state.sh` は不正 UTF-8 バイト入力で `tr` が crash し fail-open（§4.3・iter73 掃討の未適用 3 本目）。unknown-src エントリが decidable-by-default に落ちる穴（SF-012(b)）も同じ reader に残存。
- 判断が必要な論点: (1) wash 検出を writer（evidence.sh）/reader（judge）どちらに置くか → reader 単一権威。(2) washed エントリの意味論 → 既存 trust-scan の undecidable に合流（ok=transparent/fail=終端🟡）。(3) unknown-src → 終端🟡（fail-visible）。(4) SF-020/021 併合 → 見送り（brainstorm 記録参照）。
- 制約条件: 「regex/denylist を足さない」（roadmap 原則）・「旧赤/新緑」回帰 pin が ship 条件・moat の allow/deny 挙動は W1 の crash 修復以外不変（green 認定の締め付けのみ）・trust-scan（iter67）の透明化意味論を壊さない。

## 推奨アプローチ

- 採用方針: 3 点セット。W1=SF-018 の `LC_ALL=C` 同型修正（+設計正本訂正+crash pin）。W2=washed-green 封鎖 2 軸（W2a: judge 側 undecidable 述語拡張＝observed cmd のクォート外シェル演算子検出／W2b: marker.sh stage5 の exit0×failed>0 矛盾軸）。W3=SF-012(b) src allowlist（終端🟡）。
- 採用理由: SF-012 に既記載の修正方向をそのまま実装＝設計リスク最小。全変更が「green 認定の締め付け」方向のみ＝fail-open を作らない。既存 primitive（quoted-span マスク・trust-scan）の再利用が中心で、新規 pattern は fail-token 整合軸 1 本のみ（`AEGIS_TEST_FAIL_TOKEN_REGEX`・SF-012(a) が自ら規定する修正方向＝moat denylist の増殖ではない。当初の「count families 再利用で新規 regex ゼロ」は plan 時精査で撤回——EXEC は passed+failed 混合和で unittest の failed を単離抽出できない。§実装同期 参照）。
- 検討した代替案と不採用理由: (a) cmd の精密解析（最終コマンド位置で exit 信頼性を判定）＝bash 文法の再実装に近く「conservative lexer に留める」原則違反、blanket が安全側で単純。(b) writer 側（evidence.sh）にも wash 検査＝信頼判定の権威が 2 箇所に割れ drift リスク、reader 1 点で十分。(c) 全部を marker 側で吸収（failed>0 で無条件 false）＝**実 red（rc≠0）を undecidable-fail→🟡 に降格させ red シグナルを失う**ため不可（red は red のまま残す）。

## コンポーネント分解

- 分割方針: 変更 3 ファイル＝それぞれ独立した 1 責務。相互依存なし（順不同で実装可・TDD は W1→W2b→W2a→W3 順を推奨）。
- 各ユニットの責務:
  - ユニット W1 `hooks/check-runtime-state.sh`: 入力読取（`INPUT=$(cat)`）直後に `export LC_ALL=C LC_CTYPE=C LANG=C` を張り、以降の tr/grep をバイト決定論化（iter73 の destructive/secrets と同型・3 本目で掃討完了）。
  - ユニット W2b `hooks/lib/marker.sh`: Stage 6（green 矛盾 veto）を追加＝出力に非ゼロ failure 証拠（`AEGIS_TEST_FAIL_TOKEN_REGEX`・patterns.sh 単一ソース）**かつ** exit_code==0 → verdict "false"。exit_code 非 0/欠落（""）は現状維持。rc3 ガードは 8 ソース化。3 消費者（evidence.sh/record/drill）に自動波及。（当初案の「stage 5 count families から failed 合計を算出」は plan 時精査で fail-token regex 方式へ精密化＝§実装同期）
  - ユニット W2a+W3 `scripts/build-judge-card.py` `read_test_result`: (W2a) undecidable 述語を「src==observed かつ（marker≠true **または** cmd にクォート外 `[;&|]`）」に拡張。演算子検出は既存パイプライン（改行→`;` 正規化＋strips で quoted-span→Q マスク）を通した文字列への正規表現 1 本＝`_norm_cmd_match` と同一の正規化を共有。(W3) 走査冒頭で `src not in ("manual","observed")` → 終端 unverified🟡。

## インターフェース定義

- ユニット間の契約:
  - marker.sh → evidence.sh/record/drill: `aegis_marker_verdict <exit_code> <cmd>`（stdin=出力テキスト）→ "true"/"false"・rc3=評価不能。**シグネチャ不変**（内部 stage5 の判定強化のみ）。
  - build-judge-card.py → 各 gate 判定: `read_test_result(root)` → `{"tests": green|red|unverified, ...}`。**戻り値スキーマ不変**（unverified に落ちる条件が 2 つ増えるのみ）。
- 公開 API: 変更なし（evidence log スキーマ・record CLI・judge カード形式すべて不変＝PATCH 候補）。

## データフロー / 構造

- 入力: evidence-log エントリ（src/cmd/status/fp/marker_verified）・hook payload（cmd/output/exitCode）。
- 処理: [writer] observed 記録は不変 → [marker] exit0×failed>0 なら false → [reader/judge] src allowlist → runner 照合 → undecidable 判定（marker≠true ∨ washed-cmd）→ trust-scan（ok=transparent/fail=終端）→ fp 照合 → green/red。
- 出力: judge カード tests 行（green/red/unverified🟡）。

## 依存関係

- 依存方向: build-judge-card.py → patterns.sh（既存・読取のみ）／marker.sh → patterns.sh（既存）。循環なし。
- 外部依存: なし（pure bash＋python 標準ライブラリのみ・新規依存ゼロ）。

## エラーハンドリング

- 想定失敗: (1) 不正バイト入力 → W1 後は C locale でバイト決定論処理＝crash 消滅・decision 出力保証。(2) exitCode 欠落（ec=""）×failed>0 → 矛盾軸は発火しない（W2a の wash 検査が被覆・過剰 false 化を避ける）。(3) 将来の src 追加（iter77 `attested` 予定）→ allowlist に未収載だと終端🟡＝**fail-visible**（silent green 化しない・追加は同 iter で allowlist 更新をコメントで強制）。
- 対応: 全新規分岐は「green を作らない」方向のみ。unverified🟡 は ack 可能＝運用停止しない。
- エラー伝播の方針: 既存どおり（judge は例外を unverified に落とす fail-closed・hook は emit 経由で decision 出力）。

## テスト戦略

- 単体（旧赤/新緑 differential pin＝roadmap ship 条件・各ベクタで「HEAD 直前実装なら green/新実装で非 green」を固定）:
  - `pytest -q; true`（1 failed 出力・exit0）→ 旧: decidable green ／ 新: undecidable-ok（transparent）＝green 不可
  - `pytest || echo done`・`pytest | tee log.txt`（fail run）→ 同上
  - compound fake-runner（`pytest-not-installed || printf <偽サマリ>`）→ W2a で undecidable
  - unknown-src（`src:"forged"`・status ok・fp 一致）→ 旧: green ／ 新: 終端🟡
  - 0xFF 混入 payload → check-runtime-state 旧: rc1 crash ／ 新: rc0＋decision 出力（`tests/test_hook_locale_byte.py` に pin・iter73 の 2 本と同型）
- 結合（非退行）: clean 経路の green 維持（record manual green／observed 単一コマンド marker=true green）・実 red（rc≠0・failed>0）の red 維持（W2b が red を🟡に降格させないことを明示 pin）・trust-scan 既存テスト（透明化/終端）全 green・`_norm_cmd_match` パリティテスト不変。
- エッジケース: クォート内演算子（`pytest -k "a|b"`）→ Q マスクで非検出＝decidable 維持／多行コマンド→改行正規化で `;` 検出＝undecidable／`&&` 単独（`cd x && pytest` の passing run）→ blanket で undecidable（record への誘導・意図的挙動として pin）／exitCode 欠落＋failed>0 → marker 現状維持。
- 残余 pin: 単一コマンド fake binary（`./pytest` 型）は green 可能なまま＝`test_residual_*` として固定し iter77 attestation で flip を強制。
- 手動確認: B1 drill（挙動変更 hunk へ mutant: W1 の LC_ALL 行削除／W2a 述語反転／W2b 条件反転／W3 allowlist 除去→各 pin が RED 化することを実測）。full suite green を record-test-result で記録。

## 次のステップ

- [x] 実装計画を作成する → `docs/plans/2026-07-22-iter76-evidence-integrity-locale-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること
<!-- exit-check: 全セクション記入・自己レビュー完了 → plan へ -->

## 実装同期（2026-07-22・plan/implement 時の精密化・dated 追記）

設計から実装までに確定した差分 3 点。設計の主構造（3 点セット・fail-closed 方向のみ・trust-scan 意味論不変）は不変。

1. **W2b の実装形**: 「count families から failed 合計を算出」→ **fail-token 整合 regex 1 本**（`AEGIS_TEST_FAIL_TOKEN_REGEX`・非ゼロ failed／FAILED バナー／FAIL 行アンカー）へ精密化。理由＝count families の EXEC は `[0-9]+ (passed|failed)` 混合和で unittest（`Ran N tests`）の failed を単離できない。SF-012(a) が自ら規定する形（fail トークン×exit=0）そのもの。誤発火は fail-closed 方向のみ（count-family M-2 と同じ受容クラス・cargo `0 failed` は非ゼロアンカーで除外＝pin 済み）。
2. **SF-018 の実 fail-open は 2 モード**（Task 1/親裁定で実測確定）: (a) tr crash（rc=1・77566ed 親再現）に加え、本機実測は (b) **silent allow**（rc=0 `{}`・バイトが UTF-8 locale 下の抽出/grep を汚染し runtime-state 検出が pattern-miss）。(b) は stderr 信号すら無い分 (a) より悪い。`LC_ALL=C` は両モードを封鎖（RS1=silent-allow differential pin・`tests/test_hook_locale_byte.py::TestRuntimeStateByteSafety`）。
3. **意図された既存テスト flip は 2 件**（いずれも「失敗 run を exit 0 で流す washed fixture」を honest exit へ）: `test_marker_lib.py::test_unittest_failed_with_skips_true`・`test_evidence_hooks.py::test_observed_failure_certifies_red`（`bash_payload` に optional `exit_code` 追加・default 0 で他 fixture 非退行）。

実装 commit 系列: 9898153（RED 10/8）→ 0d73d09/d3875e6（W1）→ 2c47cf6（W2b）→ c73afcf（W2a+W3）。

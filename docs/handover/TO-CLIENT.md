<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->
# 納品サマリー — iteration 78（v1.32.0・pytest execution attestation）

## 何を作ったか

テストが本当に green かを判定する evidence 層の根拠を、**「テスト出力テキストの解析」から「テスト実行イベントの構造化証跡」へ一本化**した。これまで pytest の green は出力に `===== N passed =====` 等の marker が出たかで判定していたが、出力は偽造できる（fake 出力・`; true` での exit 洗浄・0 件実行）。SF-014/SF-022 が実証したこの原理天井を、**実行そのものを positive proof する attestation** で根治した。

- **新 CLI `scripts/attest-test-run.py`**: pytest を **shell を介さず argv で直接起動**（`; true` 等の exit 洗浄が構造的に不能）し、専用プラグイン `scripts/aegis_attest_plugin.py` を注入。プラグインが吐く構造化イベント（各テストの setup/call/teardown 結果・sessionfinish の exit code）と、プロセスの**実 exit code（kernel の waitpid 由来）**を突合して verdict を決める。**子プロセスの stdout/stderr は一切パースしない**ため、偽の出力では green を作れない。
- **judge の green を attested に限定**: pytest family の green は `src:"attested"` のエントリだけが証明できる。従来の観測（observed）／手動（manual）記録の pytest 'ok' は透明化（green を証明できない）。非 pytest ランナー（jest/go/cargo/unittest 等）は従来どおり marker 経路（今回の射程外・roadmap 行78 以降）。
- **record は pytest を attest へ誘導**: `record-test-result.py` は pytest コマンドを rc2 で拒否し attest-test-run.py を案内（経路の一本化）。

## 主要な設計判断

1. **出力を読まず、イベント＋kernel exit code で判定**: green 条件は `exit==0 ∧ executed≥1 ∧ failed=errors=collection_errors=0`。`executed` は call フェーズの passed+failed+xfailed+xpassed（skip 除外）＝all-xfail suite も「実行された」と数える（SF-015 の偽陰性を attested 経路で解消）。
2. **load-bearing 不変＝「本物の red は green にできない」**: 被テストコードがプラグインを差し替え／偽イベントを注入しても、失敗 suite の実 exit code（非0）は in-process コードが偽造できず、sessionfinish 突合で必ず red に落ちる。実走で確認済み。
3. **argv spawn（shell なし）＋依存ゼロ**: python3 stdlib のみ。外部依存を増やさない。
4. **MINOR bump**: 新 CLI と judge 挙動変更＝公開契約の追加。

## 変更ファイル

- `scripts/attest-test-run.py`（新規）— attestor 本体（検証→argv spawn→イベント/exit 突合→`src:"attested"` 記録）。
- `scripts/aegis_attest_plugin.py`（新規）— pytest プラグイン（イベント忠実書出のみ・判定しない・env 未設定なら no-op）。
- `scripts/build-judge-card.py` — src allowlist に `attested`・pytest family green を attested 限定・**read-time counts 検証**（`counts.executed≥1` fail-closed）・cmd 正規化を `_mask_cmd` に単一ソース化。
- `scripts/record-test-result.py` — pytest family を rc2 で attest 誘導。
- `hooks/lib/scripts-manifest.tsv`／`templates/profiles/full.json` — 新規2スクリプトの分類・配布登録。`hooks/lib/evidence.sh` — schema コメント（3 writer）追記。`.claude/skills/qa-verification/SKILL.md` — attest 手順追記。
- テスト: `tests/test_attest_execution.py`（新規・34 pin）＋契約更新 pin（judge/record/realness 24 箇所・削除0）。
- ドキュメント: `docs/specs/2026-07-28-iter78-*`、`docs/plans/2026-07-28-iter78-*`、`docs/qa-reports/iter78-{review,qa,security}.md`、`docs/security-followups.md`（SF-024 新設）、`docs/LEARNINGS.md`。

## テスト・QA・security 結果

- **full suite: 1447 passed / 2 skipped**（`src:"attested"` 記録・green・現コード fingerprint 一致）。**ドッグフード attest**＝本体 suite 自身を attest-test-run.py で実走し `attested: green`・executed=1447・judge 判定源が `src=attested` になることを実測。framework contract / reference drift / status doctor / context budget PASS。
- **review**: approve_with_notes（`docs/qa-reports/iter78-review.md`）。1次4角度（仕様準拠/敵対/テスト強度/保守性）＋盲検2次。敵対7クラス実走で**新規バイパス0**。テスト強度 mutation で **`sessionfinish != rc` 突合の検知者不在（M3 gap）を摘発→pin 追加で封鎖**。fix-forward: read-time counts 検証・M3 pin・_mask_cmd 単一ソース化。盲検2次エージェントがハード stall したため独立検証を親 in-session で回収（drift/counts 堅牢/rotation/plugin 例外 全安全）。
- **qa**: approve（`docs/qa-reports/iter78-qa.md`）。機能対照 11/11 PASS。テスト強度 drill は per-task commit 済み＝`since:a5ef438` で DRILL BLOCKED（新規テストファイル・config・redirect ハンクが coverage floor 対象＝framework 混在 diff の構造的不成立）を実測のうえ sanctioned skip＋差分 RED 14件・production 判断点 mutation 7/7 検知者・敵対 0-bypass の代替実証。
- **security**: approve（`docs/qa-reports/iter78-security.md`）。1次（親 in-session S1-S6）＋盲検2次とも**新規脆弱性0**。shell なし argv spawn／env-prefix・shell-op・`-p` 抑止 rc2／プラグイン shadowing でも実 red は green 化不能（kernel exit code が moat）／secrets 0／stdlib のみ依存0／ReDoS 線形（入力 cmd[:500] 有界）／deny 系フック全不変（judge 変更は厳格化方向）。

## SemVer

v1.31.4 → **v1.32.0 MINOR**（新 CLI `attest-test-run.py`＋judge の green 判定挙動変更＝公開契約の追加。pytest の green 記録経路が record→attest に変わる後方非互換要素を含むため PATCH でなく MINOR。evidence-log スキーマは上位互換〔attested は新 src・counts/exit は additive〕）。

## 残留リスク・既知の制限（脅威モデル内で意図的に受容）

- **SF-024（in-process event 偽造＋attested 手書き・Low・OPEN・accepted residual）**: 被テスト suite の conftest が attestation の event ファイルに偽の passing イベントを追記すれば、all-skip/all-pass suite の実行数を水増しして attested green を作れる（実 writer 経由）。また evidence-log に手書きした `src:"attested"` は fingerprint 一致だけで green（既存の非 pytest manual/observed 手書き天井と同クラス）。**ただし本物の失敗 suite は green にできない**（kernel exit code が moat）。いずれも同一ユーザー権限内の OS-limit（別ユーザー/コンテナ境界でしか閉じられず roadmap §6 が対象外と明示）で、**drill が subsume**（all-skip は marker false で BLOCKED）。iter78 は accidental な偽 green（`; true`・`-q`・all-skip・collect-only・fake 出力）を全封鎖した net 改善で、残るは故意の自己欺瞞のみ。緩和として read-time counts 検証を追加済み。
- **非 pytest ランナー**は marker 経路のまま（jest/go/cargo/unittest…）。roadmap 行78 以降で扱う。
- **B1 drill の attestation 統合**（roadmap 行78）は次 iteration へ分離。

## 操作マニュアル / 運用 RUNBOOK / UAT

いずれも**該当なし**（生成せず）: 本 iteration は Aegis フレームワーク自身の内部改善（開発者向けツールの evidence-integrity 強化）で、外部クライアント・非エンジニア利用者・運用者・監視対象が存在しない。`docs/requirements/ACCEPTANCE.md` も無い。開発者に必要な情報は本 TO-CLIENT と `docs/qa-reports/iter78-*.md`・`docs/security-followups.md`（SF-024）・設計正本に集約。

## 運用上の注意

- **pytest の green 記録は今後 `python3 scripts/attest-test-run.py "<pytest コマンド>"` のみ**（green/red とも・`-q` 可）。`record-test-result.py` に pytest を渡すと rc2 で attest へ誘導される。qa-verification skill にも明記済み。
- 挙動変化は evidence 判定の**厳格化のみ**: pytest の green は attested でしか証明できなくなった（従来の観測/手動 pytest 'ok' は透明化）。非 pytest ランナーの判定は不変。
- attestation は「テストが実際に実行され pass/fail した」ことを構造で保証するが、悪意ある conftest による event 偽造（SF-024）は同一ユーザー権限では原理的に残る＝**本物の red を green にはできない**が、all-skip を実行済みに見せる偽陽性は drill 層で捕捉する運用。

## 次のアクション

`dev_ready_for_client` ゲート承認で iter78 完全クローズ（全 dev ゲート approved・deploy は M size routing で自動除外）。未 push（iter76/77/78 分が origin/main 未反映）。

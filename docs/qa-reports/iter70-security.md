# iter70 セキュリティレポート — record 引数事前検証＋audit_deps no-manifest＋judge カードスコープ

## 対象

- 変更: scripts/record-test-result.py（引数事前検証・shell なし実行）／scripts/build-judge-card.py（audit_deps no-manifest・read_test_result_detail・_sanitize_card_field）／tests／docs/security-followups.md。commit 37ec449..HEAD（b32deb0 まで）。
- 種別: framework の qa gate 証拠機構（control-plane）。ui_surface: false。

## OWASP 該当項目の確認（1次＝親 in-session harness＋盲検2次＝fable 物理隔離 clone）

| # | 項目 | 手法 | 結果 |
|---|------|------|------|
| Injection（Command） | record の shell なし実行を迂回して payload を **code 実行**できるか | canary battery 8種（`;`/`&&`/`\|`/`$()`/backtick/`>`/env/改行）を 1次・2次それぞれ独立実測 | **新規脆弱性なし**。canary 一度も生成されず。clean 分離形（`&&`/`\|`/env）は rc2 早期拒否・連結/置換形（`$()`/backtick/`>`/改行）は shlex（shell なし）で不活性な literal 引数化＝code 実行不成立。pre-existing の shell-less 設計＋iter70 多層防御で二重遮断 |
| Sensitive Data Exposure | judge カードの cmd/src/ts 表示で secret が漏れるか | secret 入り test command をカード描画 | **Low 残余（非ブロッキング）**。cmd 前方 120 字内の secret はカード（docs/qa-reports/judge-*.md）に表示されうる。ただし evidence-log（.claude/evidence-log.jsonl）は iter70 以前から cmd 全体を平文保存＝**同一信頼境界・新規越境なし**。回避は「test command に secret を書かない」運用。将来 `_sanitize_card_field` への secret マスキング追加は任意改善 |
| Security Misconfiguration（信号後退） | 実依存 repo が no-manifest（info・🟢寄り）に落ち security 信号が弱まるか | 16 種＋盲検2次が更に 14 エコシステムを PoC | **問題なし（2段 fix-forward 済み）**。敵対2次 Major 回帰（lockfile 単独・.NET・conda・Deno・CocoaPods 等）を b32deb0 で閉塞。盲検2次が実証した追加 14 種（Haskell/sbt/Clojure/Julia/R/Perl/vcpkg/conan/meson/bazel 等）も security 内で fix-forward（UNAUDITABLE_MANIFESTS＋`*.cabal` glob 追加）。全て unverified 維持を回帰テストで固定。no-manifest は依存宣言ゼロの repo のみ。**なお no-manifest は audit_deps 最終行のみ返り、auditable manifest は先に監査＝実脆弱性は隠蔽不能**（overall も deps は red 非寄与） |
| fail-closed 一貫性 | patterns.sh 欠落・不正クォート・空・fp 不一致で fail-open（誤記録/緑）に倒れるか | 異常系 4 経路 | **問題なし**。全て rc2/unverified・evidence-log 書込み前に return・fail-open 経路なし |
| Sensitive Data（diff） | 変更行に credential/key 混入 | grep + 目視 | **なし**（検出は test fixture のダミー `--token=` と既存 SECRET_PATTERN 定義のみ） |
| Vulnerable Dependencies | 本変更の新規依存 | — | **N/A**。stdlib（shlex/subprocess/re/pathlib）のみ・新規サードパーティ依存なし。aegis repo 自体は依存 manifest を持たない |

## 1次（親 in-session harness）要旨

- command injection canary 8種で code 実行ゼロ（canary 未生成）を実測。`;`/`&&`/`|`/env は rc2、`$()`/backtick/`>`/改行は shell なし実行で不活性引数化。
- 変更行に secrets なし。
- カード cmd 表示は Low 残余（evidence-log と同一露出）。

## 盲検2次（fable・物理隔離 clone sec70-isolated・1次 verdict 非開示）

- **verdict: approve_with_notes**。独立に command injection 19 ケース（`;`/`&&`/`|`/`&`/`$()`/backtick/`>`/`>>`/`2>&1`/改行/quoted/brace/subshell/env）で canary 未生成＝code 実行不成立を実測（実 pytest 8.4.2 でも `$(touch CANARY)` が red・canary 未生成を確認）／audit_deps 23+ 種で unverified 維持を独立確認／fail-closed 4 経路／sanitize を CR/LF/U+2028/U+2029/NEL/VT/FF/# で `## 総合` spoof 全不成立／secrets なし／依存 N/A。
- **finding ③（Low・非ブロッキング・security 内で fix-forward 済み）**: 未収載 14 エコシステム（Haskell/sbt/Clojure/Julia/R/Perl/Dart-lock/vcpkg/conan/meson/bazel）が no-manifest に落ちる視認性低下を実証。severity 限定の根拠も実証（no-manifest は最終行のみ・auditable manifest 先行監査で実脆弱性隠蔽不能・deps は red 非寄与＝🟡→info の視認性差のみ）。→ 実証済み gap を UNAUDITABLE_MANIFESTS＋`*.cabal` glob へ追加し閉塞（回帰テスト `test_more_ecosystems_stay_unverified`/`test_globbed_manifests_stay_unverified`）。
- **finding ②（Low・Informational）**: judge カードの cmd 表示は secret 入り test command（`-k "sk-live-…"` 等）を 120 字窓で逐語表示しうる。env 前置 secret（`SECRET=… pytest`）は step2 で拒否。evidence-log（cmd[:500] 平文保存）と同一 trust zone・カードは狭窓＝新規越境でない。将来 `_sanitize_card_field` への secret マスキングは任意改善。
- 結論「iter70 は security posture を後退させず、むしろ record の攻撃面を縮小」。

## pre-existing 既知事項（iter70 起因でない・確認のみ）

- **zero-test forge（SF-014 クラス）**: `unittest discover -p <nomatch>`（exit 0）や `npm test`→空スクリプトは runner 該当かつ0テストで green 記録可能。denylist の原理的限界＝positive N-tests-executed proof が根治（SF-014・iter71+）。iter70 は record の accept 集合を縮小する net 改善で本穴を新規化していない（baseline 37ec449 差分実測）。record docstring・SF-014 に明記済み。

## deploy blocker

なし。

## 判定

**PASS（approve）**。新規脆弱性ゼロ。command injection は shell なし実行＋多層防御で二重遮断、audit_deps 信号後退は iter70 内で修正済み、fail-closed 一貫、secrets 混入・新規依存なし。1次・2次とも OK 系 verdict で収束。カード cmd 平文表示は evidence-log と同一露出の Low 残余で非ブロッキング（将来 `_sanitize_card_field` マスキングは任意改善）。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["なし（1次 approve／2次 a_w_n はカード cmd 平文表示 Low 残余の notes 起因・両者 OK 系で実質収束）"]
```

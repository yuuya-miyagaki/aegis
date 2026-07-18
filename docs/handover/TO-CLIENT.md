# 納品サマリー — iteration 73（v1.31.1・locale/byte 掃討・deny 側フック byte-wise 決定化）

<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->

> 本タスクは Aegis フレームワーク自身の改修。「client」＝フレームワーク保守者。

## 何を作ったか

deny 側 moat フック 2 本（`check-destructive.sh`・`check-secrets.sh`）を **byte-wise（C locale）決定化**し、不正 UTF-8 バイトを含む stdin での **`tr` クラッシュ→fail-open** を封鎖しました。iter72 の marker.sh 修正（F-CRIT-1・LC_ALL=C）と同型の locale 依存が deny 側に残っていた件の掃討です。

- **各フックの `INPUT=$(cat)` 直後に `export LC_ALL=C LC_CTYPE=C LANG=C` を追加**（`CMD=$(extract_command)` の前）。これでフック全体（抽出の grep/sed fast-path・`tr` 小文字化・全 grep）が byte-wise になり、不正 UTF-8 バイトでの `tr: Illegal byte sequence` クラッシュ（`set -euo pipefail` で rc=1・判定 JSON なし→fail-open）を封鎖します。判定ロジックは無改修。

## 主要な設計判断

- **位置づけ＝defensive robustness hardening（reachable fail-open ではない）**: クラッシュは不正バイトでのみ発生し、モデルが emit する `tool_input.command` は常に valid UTF-8（Unicode→必ず valid UTF-8）＝**脅威モデル内では到達不能**（SF-009 と同カテゴリ・実証済み）。それでも直すのは (1) 制御フックは任意 stdin でクラッシュしない堅牢性契約〔クラッシュはフック自身の raw fail-safe fallback を迂回する第3の未定義状態〕(2) iter72 との一貫性 (3) stderr ノイズ除去 (4) forward-looking（非モデル呼出し/将来変更）。
- **抽出「前」配置＋PEP 540**: 当初「抽出後」に置く設計だったが、実装で `extract_command` の grep fast-path 自体が UTF-8 下で不正バイトのコマンドを空にドロップする（→fallback が deny を ask に格下げ）ことが判明し、抽出「前」へ修正。C locale が python3 抽出を壊さないことは PEP 540 UTF-8 Mode で担保（valid 多バイト抽出の byte 一致を実測）。
- **スコープ 2 フック限定**: `check-runtime-state`/`check-deploy-gate` は同型不成立（python3 抽出でバイト→空 CMD or tr 前に BSD grep で非クラッシュ）を実測し設計に恒久記録。
- **crash-safe trap は不採用（YAGNI）**: フック契約を trap で強化する構造変更は別テーマ・将来 SF 候補。

## 変更ファイル

- 変更 `hooks/check-destructive.sh`（`export LC_ALL=C LC_CTYPE=C LANG=C` を抽出前に追加＋rationale コメント）
- 変更 `hooks/check-secrets.sh`（同上）
- 新規 `tests/test_hook_locale_byte.py`（10 pin: crash 回帰4＋i18n2＋ASCII baseline2＋受容 residual2）
- docs: 設計/計画/brainstorm-record・`docs/security-followups.md`（SF-016 起票）・qa-reports（review/qa/security）・版上げ3箇所（STATUS/template/check_framework_contract.py）

## テスト・QA・セキュリティ結果（証拠参照）

- **実装**: TDD RED 先行（Task1 RED＝crash 4 ケースが rc=1・stdout 空の fail-open crash を実測・commit 677b71a）→ per-task GREEN（`docs/plans/2026-07-18-iter73-locale-byte-sweep-implementation-plan.md`）
- **review**（`docs/qa-reports/iter73-review.md`）: 1次（opus・多角＋security-narrowing 17 プローブ＋差分）=approve findings なし／specialist（reviewer-testing）=Major F-T1（destructive pin 非対称）→fix-forward で main-path msg アサート化／盲検2次（fable・blind）=approve_with_notes・Major F-B1（Unicode 空白 narrowing＋誤コメント）→親verify 実測で**非 exploitable 決着**（bash IFS は ASCII のみ→非コマンド）→誤コメント訂正＋residual pin＋SF-016 起票で CLOSED-in-review
- **qa**（`docs/qa-reports/iter73-qa.md`）: 対照表 7 項目 PASS・drill skip（framework per-task-commit）＋**手動 mutation バッテリー M1-M4 全 killed**（export C→UTF-8 で両フック crash 回帰＋residual pin RED・配置 mutation・全削除とも catch）・掃討完全性（runtime-state/deploy-gate 非該当）再確認
- **security**（`docs/qa-reports/iter73-security.md`）: 1次（opus）=approve findings なし（OWASP 該当全 PASS・56-case で narrowing miss ゼロ・PEP 540 は PYTHONUTF8=0 でも fail-safe）／盲検2次（fable・物理隔離 clone）=approve_with_notes（SF-016 を独立に非 exploitable 実証・実 repo で secret 検出健在・invalid-byte fail-open が pre=CRASH→post=deny で CLOSED を実測）。**divergence は verdict ラベルのみで実体収束**・deploy blocker なし・新規依存/secrets 0
- **full suite**: 1302 passed / 2 skipped / 0 failed・record green（marker:true）・`check_framework_contract.py` PASS

## 運用上の注意点（保守者向け）

- **deny 側フックは任意 stdin でクラッシュしなくなりました**: 不正 UTF-8 バイトを含むコマンドでも rc=0＋正判定（ask/deny/allow）を返す（従来は `tr: Illegal byte sequence` で rc=1・判定なし）。
- **日本語パス等の valid 多バイトは従来どおり**（`rm -rf ~/日本語`→ask・`git add テスト/.env`→deny）。i18n 挙動は不変。
- **フックは C locale で全体が動く**: 追加した `LC_ALL=C` はフックプロセス内のみ（呼び出し元へ非漏洩）。将来これらのフックに下流 python3 呼び出しを足す場合は PEP 540 UTF-8 Mode 前提を再評価（設計コメントに警告あり）。

## 残留リスク・既知の制限

- **SF-016（新規起票・非 exploitable・accepted residual・pin 済み）**: C locale が `[[:space:]]`/`\s` を ASCII のみに狭め、Unicode 空白区切り（NBSP/U+3000 等）の moat マッチが pre(UTF-8)=warn/deny → post(C)=allow に narrowing。ただし bash は ASCII blank でのみ word-split するため `git<NBSP>add`/`rm<NBSP>-rf` は非存在トークン（command not found）＝削除/ステージング不実行＝機能的に無害。re-widen は非コマンドへの spurious マッチ＋C-locale 決定性矛盾で不採。`tests/test_hook_locale_byte.py` で pin（将来 re-widen 時に flip して revisit を強制）。
- **PEP 540 依存**: C locale 下の python3 抽出 fidelity は CPython 3.7+ の UTF-8 Mode に依存。無効環境では valid 多バイトの一部抽出が劣化しうるが、fallback が byte-wise grep で deny/ask 側に倒れる＝fail-safe（実測）。
- **iter73+ トラック**: SF-014 恒久策（execution attestation）／SF-011/012/013/015（いずれも Low・pre-existing）。

## 版

v1.31.0 → **v1.31.1 PATCH**（堅牢性バグ修正＝invalid-byte fail-open crash の封鎖・機能的コマンドの判定挙動は不変・公開契約不変・後方互換。SF-016 の narrowing は非機能入力のみ）。

## 操作マニュアル / 運用 RUNBOOK / UAT

- 操作マニュアル: 不要（framework 自己改善・利用者向け新規操作なし。運用注意点は本書「運用上の注意点」に集約）
- 運用 RUNBOOK: 不要（新規サービス/監視対象なし）
- UAT: 不要（`docs/requirements/ACCEPTANCE.md` なし・framework 内部改修）

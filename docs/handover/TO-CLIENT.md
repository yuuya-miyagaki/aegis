<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->
# 納品サマリー — iteration 76（v1.31.3・evidence 整合＋locale 掃討完了）

## 何を作ったか

「evidence-based completion」（＝テストが通ったという**証拠**でのみ完了を認める）の中核を守る2つの偽造経路を封鎖した。roadmap §5 iter76（P0）の完了条件を満たす。

- **washed-green（SF-012）**: 失敗したテストを exit code 洗浄（`pytest -q; true`／`|| true`／`| tee`）や偽出力で judge に「green」と誤認させる経路。`;`/`&&` は pipefail 非依存で無条件 exit0＝非エンジニア/AI が事故的に書く典型ゆえ実害が高い。
- **SF-018（LOCALE-1）**: `check-runtime-state.sh`（非 framework モードで docs/STATUS.md・gate 値等の改竄を止める**唯一の**PreToolUse ガード）が不正 UTF-8 バイト入力で fail-open する穴。

## 主要な設計判断

1. **判定の締め付けのみ（fail-closed 一方向）**: 全変更は「green 認定を狭める／deny を広げる」方向のみで、新しい fail-open を一切作らない。実 red（exit≠0）は red のまま（🟡 に誤降格しない）。
2. **reader を信頼判定の単一権威に**: washed 検査は judge（reader）1点に置き、writer（evidence.sh）には検査を足さない（権威分裂＝drift を回避）。marker の矛盾 veto は 3消費者（evidence.sh/record/drill）共通コアに1回だけ入れる。
3. **regex を足し続けない原則＋有界語彙の完成**: 失敗トークンの denylist は原理的に不完全（＝iter77 の positive proof＝実行イベント attestation が根治）。今回は pytest の `errors` timing-tail と unittest FAILED バナーの**有界3語彙**（failures/errors/unexpected successes）を tight anchor で完成させるに留め、無限の語彙追加はしない（SF-022）。
4. **SF-018 は2モード fail-open を封鎖**: 実測で (a) `tr` crash（rc=1）と (b) **silent allow**（rc=0・バイト汚染で pattern-miss＝より悪い）の2経路を確認。`INPUT=$(cat)` 直後の `export LC_ALL=C LC_CTYPE=C LANG=C`（iter73 の destructive/secrets と同型・3本目）で両モードを byte-wise に封鎖し locale 掃討を完了。

## 変更ファイル

- `hooks/check-runtime-state.sh` — 入力読取直後に `LC_ALL=C`（byte-safety・SF-018）。
- `hooks/lib/marker.sh` — Stage 6「green 矛盾 veto」（exit0×失敗証拠→false）＋rc3 ガードを8ソース化。
- `hooks/lib/patterns.sh` — `AEGIS_TEST_FAIL_TOKEN_REGEX` 新設（`failed`／`FAILED (failures|errors|unexpected successes)=`／`--- FAIL:`／`FAIL<TAB>`／`N errors in <digit>`）。
- `scripts/build-judge-card.py` — src allowlist（manual/observed 以外→終端🟡）＋observed-ok の複合コマンド transparent skip（`_cmd_has_shell_operators`）。
- テスト: `tests/test_{hook_locale_byte,marker_lib,judge_card,evidence_hooks}.py`（RS1-4／W2b-1〜8／W2a-1〜5／W3-1〜3／helper・旧赤/新緑 differential pin）。
- ドキュメント: `docs/security-followups.md`（SF-022 新設）、iter73 設計正本の訂正、`docs/qa-reports/iter76-{review,qa,security}.md`（新規）、`docs/LEARNINGS.md`。

## テスト・QA・security 結果

- **full suite: 1395 passed / 2 skipped**（trusted-runner 記録・green・現コード fingerprint 一致）。framework contract PASS・deny 系 moat スイート 174 passed（非弱体化）。
- **review**: approved（`docs/qa-reports/iter76-review.md`）。1次4角度（仕様準拠/敵対/テスト強度/保守性）＋盲検2次。盲検2次が `errors` 語形の見落としを摘発→実証裁定（脅威モデル内独立到達不能）＋tight anchor で緩和。
- **qa**: approved（`docs/qa-reports/iter76-qa.md`）。B1 drill は per-task commit 済み＝`since` 案で DRILL BLOCKED を実測のうえ sanctioned skip＋6軸 mutation 代替実証。E2E 3項目（SF-018 deny／washed false-true／未知src unverified）メイン tree PASS。
- **security**: approved（`docs/qa-reports/iter76-security.md`）。1次（親 in-session）＋盲検2次とも **新規脆弱性0**。注入/secrets/依存/ReDoS クリア・moat 174 tests 非弱体化。盲検2次が unittest `unexpected successes=` バナー欠落（A7）を摘発→有界バナー完成で封鎖。washed-green **10綴り**＋SF-018 **4バイト**の主張クラス内バイパス0を両者が実測。

## SemVer

v1.31.2 → **v1.31.3 PATCH**（既存 evidence-integrity/runtime-state moat の穴を塞ぐ security/robustness fix＝挙動変化は「偽造 green の締め付け」と「不正バイトの fail-open 封鎖」のみ・公開契約〔CLI/evidence-log スキーマ/judge カード形式〕不変・後方互換。iter66/iter75 の PATCH と同カテゴリ）。

## 残留リスク・既知の制限（脅威モデル内で意図的に受容）

- **SF-022（denylist 原理的不完全性・iter77 根治予定）**: marker Stage 6 の失敗語彙 denylist は列挙式ゆえ原理的に不完全。今回 pytest `errors`・unittest 有界バナーは封鎖したが、任意の偽造出力は網羅できない。**ただし脅威モデル内で独立到達不能**を実証済み（実 runner は失敗時 exit≠0・exit0 washing は judge W2a が捕捉・単一コマンド fake binary は下記天井）。根治は iter77 の execution attestation（argv spawn＋structured event で「N tests executed」を positive proof・src=attested のみ decisive green）。回帰 pin＝`test_w2b7_*`／`test_w2b8`／`test_residual_*`。
- **単一コマンド fake binary**（`./pytest` 型 PATH hijack）・**evidence cmd 500字切詰め以降の演算子**＝iter77 attestation の領分。多層防御（W2a=500字以内／marker=出力に失敗証拠必要）で穴でないと論証済み。
- **SF-019（構造化 argv 待ち・iter77）／SF-020（raw 大文字 case-fold・次 iter S）／SF-021（`git stage` エイリアス・次 iter S）**: 本 iter の射程外（テーマ分離＝盲検レビューの焦点保全）。iter75 TO-CLIENT で「iter76 併合候補」としていたが、L 化・テーマ混在回避のため次 iter へ再分離した。
- evidence-log.jsonl への直接書込みは脅威モデル外（それが可能なら src:manual green を直接書ける＝capability 増分なし）。

## 操作マニュアル / 運用 RUNBOOK / UAT

いずれも**該当なし**（生成せず）: 本 iteration は Aegis フレームワーク自身の内部改善（開発者向けツールの moat/evidence 強化）で、外部クライアント・非エンジニア利用者・運用者・監視対象が存在しない。`docs/requirements/ACCEPTANCE.md` も無い（framework 自己改善に受入基準の外部合意なし）。開発者に必要な情報はすべて本 TO-CLIENT と `docs/qa-reports/iter76-*.md`・`docs/security-followups.md`（SF-022）に集約。

## 運用上の注意

- 挙動変化は**証拠判定の締め付けのみ**: 失敗テストを exit 洗浄した run が green と認められなくなった（🟡 unverified 化＝正しく再記録を促す）。正直な green run の判定は不変。
- SF-018 修正で、不正バイトを含む Bash コマンドでも runtime-state ガードが crash せず正しく deny/allow を返す。

## 次のアクション

`dev_ready_for_client` ゲートはユーザー承認が必要（本セッションでは未承認のまま残置）。内容を確認のうえ承認を。

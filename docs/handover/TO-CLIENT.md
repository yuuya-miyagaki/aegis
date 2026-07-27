<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->
# 納品サマリー — iteration 77（v1.31.4・moat case-fold＋stage エイリアス封鎖）

## 何を作ったか

破壊的コマンド／秘密漏洩を止める moat（PreToolUse hook）に残っていた **2 つの silent allow 穴（両 High・OPEN）** を封鎖した。どちらも「その1形だけ検出器をすり抜けて、警告なしにコマンドが通る」＝moat が最も嫌う失敗モード。

- **SF-020（case-fold 穴）**: `check-destructive.sh` の raw 経路（コマンド抽出後・fallback）が破壊コマンド名を大小同一視せず、**case-insensitive FS（macOS APFS／Windows デフォルト）で `RM -rf` や `echo x > /ETC/passwd` が silent allow**。case-insensitive FS では `/bin/rm` が `RM` で実際に起動するため実バイパス。
- **SF-021（stage エイリアス穴）**: `check-secrets.sh` の broad-stage 検出器が `git add` しか見ておらず、**その完全エイリアス `git stage -A/.` が repo 内の実 .env ごと silent broad staging**。難読化以前に生でも通る＝より基本的な穴。

## 主要な設計判断

1. **case-fold は呼び出し側 `grep -i` のみ（iter75 FF7 と同方式）**: raw 経路の grep 4 サイトを `grep -qE`→`grep -iqE` にし、既に `-i` 化済みの難読化（NORM）経路と対称化。**regex 本体（`patterns.sh` の SSOT）は不変更**。入力小文字化（CMD_LC/NORM_LOWER）を採らないのは、`AEGIS_DESTRUCTIVE_CMD_REGEX` が大文字リテラル（`chmod -R` の `R`、`git branch -[dD]`）を含み、事前 lower 化すると捕捉を壊すため（iter75 実測）。
2. **safe-artifact 例外は大文字へ広げない（allow 例外の非弱体化）**: `rm -rf node_modules` 等を許す SAFE_TARGETS の sed は意図的に fold しない。帰結として大文字 `RM -rf node_modules` は ask に落ちる（allow 例外を広げると moat 弱体化のため）。
3. **broad 検出だけ `(add|stage)`（`update-index` を混ぜない）**: `git update-index` は `-A/--all/.` の broad 綴りを持たない別 plumbing コマンドで、混ぜると非実在綴りを許容する。明示 .env 経路（`_STAGE_ENV_RE`）は従来どおり `update-index` を含む全 verb を対象に維持（`git update-index --add .env` は依然 deny）。
4. **厳格化のみ（monotone widening）**: `grep -i` は case-sensitive のスーパーセット・`(add|stage)` は `add` のスーパーセット＝どちらも「以前 block していた入力は全て block のまま／新たに拾うだけ」。**deny→allow への反転（moat 弱体化）は構造的に不能**で、これを security 2次が old-vs-new 差分照合で機械的に裏取り（弱体化 0）。

## 変更ファイル

- `hooks/check-destructive.sh` — raw 経路 grep 4 サイト（fallback CMD_REGEX ループ／fallback rm 再帰／本体 rm 再帰特例／本体 CMD_REGEX ループ）を `grep -iqE` 化＋SF-020 コメント（行番号でなく役割名参照）。
- `hooks/check-secrets.sh` — `_STAGE_BROAD_RE` の verb を `add`→`(add|stage)`＋事実誤認コメント訂正＋deny/ask 文言を verb 非依存に汎化。
- テスト: `tests/test_moat_case_fold_stage_alias.py`（新規・19 pin＝D-1〜D-7b／S-1〜S-7・旧赤/新緑 differential）。
- ドキュメント: `docs/security-followups.md`（SF-020/021 CLOSED-in-review・SF-023 新設）、`docs/qa-reports/iter77-{review,qa,security}.md`（新規）、`docs/LEARNINGS.md`。

## テスト・QA・security 結果

- **full suite: 1411 passed / 2 skipped**（trusted-runner 記録・green・現コード fingerprint 一致＝iter76 の 1395 全 green 維持＋iter77 新規 16。削除 0・failure 0）。framework contract / reference drift / status doctor PASS。deny 系 moat 非弱体化。
- **review**: approved with notes（`docs/qa-reports/iter77-review.md`）。1次4角度（仕様準拠/敵対/テスト強度/保守性・全 opus）＋盲検2次（fable）。**主張クラス内バイパス 0 件**（敵対 finder が 65+ 入力を実 hook 実走）。差分歯 **mutation 6/6 に検知者確立**（fallback CMD_REGEX の検知者不在を摘発→D-7b pin で封鎖・再走で FAIL 実証）。盲検2次が RED カウントの記録ずれ（赤11→実測14）を摘発→訂正。
- **qa**: approved（`docs/qa-reports/iter77-qa.md`）。テスト強度 drill は per-task commit 済み＝`since:ad04973` 案で DRILL BLOCKED（emit_deny 文言行＋新規テスト全体が coverage floor 対象＝framework 混在 diff の構造的不成立）を実測のうえ sanctioned skip＋mutation 6/6・14 RED・敵対 0-bypass の代替実証。
- **security**: approved（`docs/qa-reports/iter77-security.md`）。1次（親 in-session S1-S6）＋盲検2次（fable・old-vs-new 差分照合という別手法）とも **新規脆弱性 0**。injection なし／ReDoS なし（最悪 239-768ms・timeout 0）／LC_ALL=C 下 `grep -i` は ASCII のみ畳む（Turkish-I 異常なし）／moat 非弱体化を 2 手法で確認／secrets 混入 0／依存追加 0。

## SemVer

v1.31.3 → **v1.31.4 PATCH**（既存 destructive/secrets moat の silent allow 穴を塞ぐ security fix＝挙動変化は「大文字破壊コマンドと `git stage` broad staging を新たに ask/deny する」締め付けのみ・公開契約〔CLI/evidence-log スキーマ/judge カード形式〕不変・後方互換。iter75/iter76 の PATCH と同カテゴリ）。

## 残留リスク・既知の制限（脅威モデル内で意図的に受容）

- **SF-023（`>>` append redirect・Low・OPEN・次 iter 候補）**: `echo x >> /etc/passwd`（システムパスへの追記）が allow。redirect パターンの左コンテキスト負クラス `(^|[^0-9>])>` が `>>` の 2 番目 `>` を弾く既存 regex カバレッジ穴で、**小文字形も同挙動＝case-fold（SF-020）とは無関係**（iter77 が導入した退行ではない）。`>` 単発（truncate）は既に ask 済みで、append は truncate より低危険＝fail-safe 側。iter77 の敵対 finder が副次発見・親が裏取り。
- **F-2（substring FP の大文字対称拡張・記録のみ）**: コマンド位置アンカーなしの既存 FP（commit メッセージ内の `RM -rf` 言及等が ask 化）が `grep -i` で大文字綴りへ対称に広がった。小文字形も既に ask＝意図的 widening・fail-safe（ユーザーが可逆）。
- **SF-019（構造化 argv 待ち）／SF-022（marker denylist 不完全性）／pytest execution attestation**: 本 iter の射程外。roadmap §5 iter78（attestation）が「テスト出力＝真実」の原理天井を塞ぐ本命。

## 操作マニュアル / 運用 RUNBOOK / UAT

いずれも**該当なし**（生成せず）: 本 iteration は Aegis フレームワーク自身の内部改善（開発者向けツールの moat 強化）で、外部クライアント・非エンジニア利用者・運用者・監視対象が存在しない。`docs/requirements/ACCEPTANCE.md` も無い（framework 自己改善に受入基準の外部合意なし）。開発者に必要な情報はすべて本 TO-CLIENT と `docs/qa-reports/iter77-*.md`・`docs/security-followups.md`（SF-020/021/023）に集約。

## 運用上の注意

- 挙動変化は**判定の締め付けのみ**: (1) case-insensitive FS で大文字破壊コマンド（`RM -rf`・`GIT RESET --HARD`・`CHMOD -R`・`> /ETC/`）が警告（ask）されるようになった。(2) `git stage -A/.`（＝`git add -A/.` のエイリアス）が repo に .env/認証ファイルがある場合に deny されるようになった。正常形（`rm -rf node_modules`・個別 `git stage README.md`・`git add README.md`・commit メッセージ）の判定は不変。
- 大文字 `RM -rf node_modules` は（小文字と違い）ask になる。これは仕様（大文字化という難読化自体が確認対象・safe-artifact 例外を大文字へ広げない設計判断）。

## 次のアクション

`dev_ready_for_client` ゲートはユーザー承認が必要。内容を確認のうえ承認を。

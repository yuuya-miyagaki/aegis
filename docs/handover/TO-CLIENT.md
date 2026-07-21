<!-- 正本: ship-and-docs skill -->
<!-- exit-check: TO-CLIENT 完成・証拠参照済み・既知ギャップ記載済み → docs へ -->
# 納品サマリー — iteration 75（v1.31.2・SF-017 fix-forward「FF9」＝moat 難読化バイパスの空白注入クラス封鎖）

## 何を作ったか

破壊的コマンド / secret-staging を検出する2つの PreToolUse moat フック（`check-destructive.sh` / `check-secrets.sh`）の**難読化バイパス**を、iter75 の fix-forward「FF9」で追加封鎖した。前回 security ゲートで摘発された2件に対応:

- **SEC-1（High）**: 共有正規化 helper `aegis_dequote_normalize` が literal `${IFS}`/`$IFS` しか畳まず、`${IFS:0:1}`・`${IFS: -1}`・`${IFS/x/y}`・`${IFS#}`・`${IFS:-x}` 等の **parameter-expansion 変種**が未畳み込み → `git${IFS:0:1}add .env`＋commit で secret staging を silent 通過していた。
- **Finding 1（Medium・pre-existing）**: `check-destructive.sh` の SAFE_TARGETS 早期 allow が `rm -rf${IFS}/x`（flag 密着 `${IFS}`）を単一 flag トークン扱いで swallow → silent 再帰削除。

## 主要な設計判断

1. **非空 `${IFS...}` family を単一 sed で畳む**（`s/\$\{IFS[^}]*\}/ /g`・非貪欲・O(n)）。IFS 由来の展開値は shell 仕様上つねに空白の部分集合ゆえ「空白へ畳む」のが保守側（実バイパス捕捉・非バイパス変種は無害な false-ASK・MISS なし）。bash の `${c//…}` 全置換は多数一致で O(n²)＝5000 件 ~21s だが sed は ~40ms（hook timeout=fail-open 回避）。
2. **SAFE_TARGETS 早期 allow を NORM!=CMD（難読化実在）時に skip**。難読化された rm を「artifact-only」とみなさず、下流の再帰削除検知に委ねる。平文の safe-artifact 削除（`rm -rf build` 等）は NORM==CMD ゆえ挙動不変。
3. **道C による主張の正確化**: 静的文字列正規化で**健全に**畳めるのは**非空 IFS 展開**のみ。security 再走で判明した「空/ゼロ幅 IFS 展開（`${IFS:0:0}`）・mixed split/glue・param-default ネスト・変数間接・cmdsub」は 2ⁿ 展開列挙＝**構造化 argv（SF-019）でしか根治できない**残余として正確に分離（iter77 根治予定）。全て意図的難読化を要し事故経路で発生しない（脅威モデル外）。

## 変更ファイル

- `hooks/lib/patterns.sh` — `aegis_dequote_normalize`: `${IFS...}` family＋`$IFS` を単一 sed 畳み込み（改行/タブ畳みを sed 前へ移動）。
- `hooks/check-destructive.sh` — `NORM` を SAFE_TARGETS 判定前で計算し early-exit を `NORM==CMD` ガード。
- `tests/test_moat_quote_split.py` — FF9 の RED→GREEN テスト＋残余 pin（67 ケース）。
- ドキュメント: `docs/security-followups.md`（SF-017 封鎖範囲・道C 正確化／SF-019 拡張）、`docs/qa-reports/iter75-security.md`（新規）、`docs/LEARNINGS.md`。

## テスト・QA・security 結果

- **full suite: 1367 passed / 2 skipped**（trusted-runner 記録・green・現コード fingerprint 一致）。framework contract PASS・moat スイート 163 passed。
- **review**: approved（`docs/qa-reports/iter75-review.md`）。
- **qa**: approved（`docs/qa-reports/iter75-qa.md`）。
- **security**: **approve_with_notes**（`docs/qa-reports/iter75-security.md`）。1次(opus)＋盲検2次(fable) が独立検証。**主張クラス（非空 `${IFS}`/quote/BS）内バイパス0件**を両者が確認、divergence なし。**deploy blocker なし**（Bash moat は脅威モデル上「敷居を上げる層」）。

## SemVer

v1.31.1 → **v1.31.2 PATCH**（既存 moat feature の難読化バイパス封鎖＝挙動変化は難読化入力のみ・機能的コマンドの判定不変・公開契約不変・後方互換。iter73 の locale/byte 掃討と同カテゴリ）。

## 残留リスク・既知の制限（脅威モデル内で意図的に受容）

- **SF-019（構造化 argv 待ち・iter77 根治予定）**: brace 展開・param-default（ネスト含む）・cmdsub・変数間接・**ゼロ幅/mixed IFS 展開**は静的文字列正規化の射程外。いずれも意図的難読化を要し、LLM が事故的に emit する経路ではない（North Star＝事故防止から severity 低）。回帰 pin＝`tests/test_moat_quote_split.py::test_ff9_residual_*` / `test_residual_*`（将来の argv 判定で flip→revisit を強制）。
- **SF-020（raw 大文字直打ち・iter76）／SF-021（`git stage` エイリアス・iter76）**: iter75 diff とは独立の既存穴（本 fix で導入も解消もしない）。
- Bash moat は **sandbox ではなく threshold-raising 層**（canonical 脅威モデル・SF-004）。敵対的・意図的難読化の無限回避は範囲外。

## 運用上の注意

- 挙動変化は**難読化コマンドのみ**（`${IFS}`・quote-split 等が ASK/DENY を出すようになった）。通常のコマンド（`rm -rf build`・`git commit -m "…"` 等）の判定は不変。
- 正規化は呼び出し側 `LC_ALL=C` 前提（byte-wise・不正バイトで sed が crash しないことを iter73 で実証済み）。

## 次のアクション

`dev_ready_for_client` ゲートはユーザー承認が必要（本セッションでは未承認のまま残置）。内容を確認のうえ承認を。

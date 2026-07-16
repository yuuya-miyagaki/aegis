# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-16（iteration 72）

## テーマ

- SF-014 恒久策の完結編: marker positive proof を「出力マーカーの**マッチ**」から「passed/failed の**実数カウント**（skip 除外・executed ≧ 1）」へ強化し、残余 F-A（all-skip suite の偽 green）を封鎖する。

## コンテキスト

- 現在の状況: iter71 で `hooks/lib/marker.sh`（4段検証: NO_RUN flag → STRONG marker → WEAK pair → zero-run gate）を共有 lib 化し、record（green 記録前 verdict 必須）と drill（baseline no-test-proof BLOCKED）へ適用済み。zero-run フォージ（`unittest discover -p nomatch`／`npm test`→`true`）は CLOSED。
- きっかけ: iter71 review 敵対2次＋親 verify が実証した残余 F-A — marker は出力**一致**ベースのため、**(a) all-skip suite**（unittest `Ran N tests ... OK (skipped=N)`＝skip を Ran に数える／go 全 `t.Skip()` でも `ok pkg dur`）が marker=true → 偽 green。pytest（`N skipped in`）と cargo（`0 passed`）は既に正しく false（moat pin 済み）。恒久策は SF-014 に「passed/failed の実数カウントを要求する positive proof（skip 数を実行数から除外）＝iter72+」と明記済み。
- **本 brainstorm での実証 2 件**（2026-07-16 実測）:
  1. **cargo 偽陰性バグ（pre-existing・新発見）**: doc-tests セクションが空の現実的な cargo 出力（unit 5 passed ＋ doc-tests `running 0 tests`→`test result: ok. 0 passed`）を現行 `aegis_marker_verdict` に入力すると **false**。zero-run Axis 1 の `test result: (ok|FAILED)\. 0 passed` が doc-test 行にマッチするため。doc-test を持たない crate（ごく一般的）の**実在の green run が record/drill で拒否される**。行単位 deny の構造的限界であり、カウント**合計**方式が原理的に修正する。
  2. **unittest all-skip / 混在の実出力形状**: `python3 -m unittest` 実行で all-skip=`Ran 2 tests in 0.000s\n\nOK (skipped=2)`（rc=0）・混在=`OK (skipped=1)`（Ran 2・executed=1）を採取。減算式 `executed = Ran_N − Σskipped` の入力形状を確認。

## 検討したアプローチ

### アプローチ A: marker.sh に Stage 5「count proof」を追加（count データは patterns.sh・採用）

- 概要: 4段検証を維持したまま Stage 5 を追加。count 抽出可能なランナー族（unittest/pytest/jest/vitest/cargo/go-verbose）の**サマリが出力に存在する場合**、executed 実数（unittest: `Ran N` − Σ`skipped=K`／pytest: Σ(passed+failed)／jest: passed+failed／cargo: **全 `test result:` 行の合計** Σ(passed+failed)／go `-v`: `--- PASS:|--- FAIL:` 行数）≧1 を要求。count 族が一つも検出できない出力（素の `go test` の `ok pkg dur` のみ等）は従来 4 段 verdict のまま（残余として文書化・pin）。cargo の zero-run 行 deny はカウント合計に委譲（偽陰性修正）。
- 利点: (1) F-A の実証済み主形（unittest all-skip）を根治し、go `-v` 時も封鎖。(2) cargo 偽陰性（実在バグ）を同一機構で修正。(3) verdict インターフェース（stdin/true/false/rc3）不変＝3 消費者（evidence.sh/record/drill）無改修。(4) パターンは patterns.sh 単一ソース＋parity 契約下。
- 欠点: 素の `go test`（count 非搭載出力）の all-skip は残る（出力ベース proof の床）。echo フォージ（残余 b）はカウントでも閉じない（数字ごと偽装可能）。

### アプローチ B: 実行系 attestation（runner プラグイン / `-json` 出力の強制）

- 概要: `go test -json`／`pytest --json-report`／`cargo --format json` 等の機械可読出力を要求し、実行イベントを直接数える。
- 利点: 出力偽装への耐性が regex より高い。go の素出力問題も解消。
- 欠点: ランナーごとの統合実装＝footprint 激増・新規依存（pytest プラグイン等）・**ユーザーの test コマンド契約を全ランナーで変える**（North Star の「知識の乏しい人」に運用負担転嫁）。attestation 型は audit_deps positive proof（iter73 分離済み）と同じ機構クラス＝そちらのトラックで検討すべき。YAGNI。

### アプローチ C: zero-run denylist の skip パターン列挙拡張

- 概要: `OK (skipped=N)` 等を zero-run regex に追加。
- 欠点: **N==K（全部 skip）を純 regex では表現できない**（`OK (skipped=2)` は Ran 5 なら正当）＝算術が必要な時点で列挙 deny は原理的に不成立。SF-014 の教訓（denylist 不完全性・conf9）の轍そのもの。即却下。

## 決定

- 採用アプローチ: **A**
- 採用理由: 恒久策として SF-014 に明記された方式そのもの。インターフェース不変で 3 消費者無改修・footprint 最小。実証済みの主形（unittest all-skip）を封鎖しつつ、設計調査で発見した cargo 実害バグ（偽陰性）も同一原理で修正できる。
- 不採用理由: B は attestation クラス＝iter73 の audit_deps positive proof トラックと同機構であり分離起票済み（テーマ純度・iter71 判断踏襲）。C は算術を要する条件を列挙で書けず原理的に不成立。

## スコープ境界

- やること:
  - `hooks/lib/patterns.sh`: count 抽出用パターンデータ追加（grep-E ∩ python-re 共通部分集合・parity fixtures 追加）。cargo zero-run 行 deny のカウント委譲。
  - `hooks/lib/marker.sh`: Stage 5 count proof（族検出→per-族算術→executed ≧ 1）。
  - `scripts/record-test-result.py`: docstring 残余記述の更新（(a)-unittest CLOSED・go 素出力残余・echo 残余維持）＋拒否メッセージに skip 由来の説明追記。
  - テスト: `tests/test_marker_lib.py`（residual pin の反転=unittest all-skip false 化・go `-v` all-skip false・境界 N−K=1 true・cargo doc-tests 混在 true=偽陰性修正 pin・実 fixture ベース）＋`tests/test_patterns_parity.py`（新パターンの両エンジン parity）。
  - docs: SF-014 更新（(a)-unittest CLOSED・go 素出力=残余として明示）・LEARNINGS。
- やらないこと:
  - echo フォージ（残余 b）の追跡（出力ベース proof の原理的床・drill subsume ＋人手プレビューで contained・文書化維持）。
  - 素の `go test`（count 非搭載出力）の all-skip 封鎖（`-v` 強制は全 go ユーザーの UX 退行＞自己欺瞞脅威の残余利得。drill が subsume。iter73+ attestation で根治候補）。
  - audit_deps positive proof（iter73 分離済み・attestation 型・機構別）。
  - mocha 等の未対応ランナーへの marker 対応拡張（YAGNI・iter71 判断踏襲）。
  - evidence.sh / drill / judge の呼び出し側変更（verdict インターフェース不変）。

## 未解決事項

- vitest の `Test Files N passed` と `Tests N passed` の関係（全 skip ファイルが Test Files 行でどう数えられるか）は手元に vitest 実環境がなく未実証 → 実装時は「`Tests N passed` 行があれば count に使い、なければ `Test Files N passed` N≧1 を従来どおり受理（残余として文書化）」の保守側に倒す。plan で確定。
- go/cargo はローカル未インストール → E2E は実出力形状の captured fixture（iter71 review F-A の実測形状＋Rust/Go 公式出力仕様）を bash 関数に直接入力して検証。fixture の形状根拠を設計書に明記。

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-07-16-iter72-count-proof-design.md`
- テンプレート名: `SPEC.template.md`
<!-- exit-check: アプローチ決定・スコープ明確 → design note へ -->

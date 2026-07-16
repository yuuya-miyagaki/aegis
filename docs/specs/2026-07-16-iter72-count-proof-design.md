# 設計ノート — iter72: marker positive proof のカウント化（SF-014 恒久策 完結編）
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-07-16-iter72-count-proof-brainstorm-record.md`
- 要件: なし（framework 自己改善・動機正本は `docs/security-followups.md` SF-014 / LEARNINGS line148 conf9）

## 問題整理

- 背景: iter71 の marker positive proof（4段検証）は出力マーカーの**一致**を証拠とするため、「skip されたテストも実行済みに数えるランナー」の all-skip suite が marker=true になる（残余 F-A・iter71 review で実証・pre-existing）。
- 判断が必要な論点:
  1. カウントをどこで・どう抽出するか（族検出・算術・境界）
  2. count 非搭載出力（素の `go test`）の扱い
  3. cargo の zero-run 行 deny が実在 green run を拒否する偽陰性（本 brainstorm で実証）の修正方法
- 制約条件:
  - verdict インターフェース（stdin=全文, stdout="true"/"false", rc3=評価不能）と 3 消費者（evidence.sh source / record・drill subprocess）は**不変**
  - patterns.sh のパターンは grep-E ∩ python-re 共通部分集合（`\b`・`[[:` 禁止・bracket 内は literal TAB）＋ parity テスト対象
  - bash 3.2 互換（macOS）・外部依存追加なし
  - 既存 moat pin（M2-M11・TestWeakPairBoundary・pytest/cargo の all-skip false pin）を退行させない

## 推奨アプローチ

- 採用方針: `aegis_marker_verdict` に **Stage 5「count proof」** を追加する。Stage 1-4 を通過した出力に対し、count 抽出可能なランナー族のサマリが**検出された場合のみ**、その族の算術で executed（実行された test body 数）を計算し、**いずれかの検出族で executed ≧ 1** を要求する。どの count 族も検出されない出力（素の go `ok pkg dur` のみ等）は従来 verdict を維持（残余として pin・文書化）。
- 採用理由: SF-014 明記の恒久策そのもの。インターフェース不変で消費者無改修。実証済み主形（unittest all-skip）を封鎖し、cargo 偽陰性も同一原理（行 deny→合計算術）で修正。
- 検討した代替案と不採用理由: BRAINSTORM-RECORD 参照（B=attestation は iter73 の audit_deps トラックと同機構クラス・YAGNI／C=skip 列挙 denylist は N==K の算術を regex で書けず原理的に不成立）。

### 単調性の不変条件（レビュー観点）

- **Stage 5 は verdict を true→false 方向にしか変えない**（純粋な追加条件）。
- 唯一の意図的 false→true は **cargo zero-run 行 deny の削除**（`test result: (ok|FAILED)\. 0 passed` を `AEGIS_TEST_ZERO_RUN_REGEX` から除去し、cargo 族のカウント合計に委譲）。これは実証済み偽陰性（doc-tests 空セクションで実在 green が false）の修正であり、all-ignored 全滅ケースは Stage 5 の Σ=0 → false が引き続き拒否する（既存 moat pin `test_cargo_all_ignored_false_moat_pin` を**変更せず**通過することで機構交換を黒箱ピン）。

## コンポーネント分解

- 分割方針: パターンデータは patterns.sh（単一ソース）、算術ロジックは marker.sh（単一実装）。消費者は触らない。
- 各ユニットの責務:
  - ユニット A `hooks/lib/patterns.sh`: count 族の定義データ `AEGIS_TEST_COUNT_FAMILIES`（後述）＋cargo zero-run 行の削除。
  - ユニット B `hooks/lib/marker.sh`: Stage 5 実装（族検出→抽出→算術→判定）＋rc3 guard への count 配列追加。
  - ユニット C `scripts/record-test-result.py`: docstring の残余記述更新＋green 拒否メッセージへ skip 起因の説明追記（コード動作は不変）。
  - ユニット D テスト: `tests/test_marker_lib.py`（pin 反転＋新 fixture）・`tests/test_patterns_parity.py`（新配列の parity）。

## インターフェース定義

- `aegis_marker_verdict <exit_code> <command>`: **シグネチャ・戻り値契約とも不変**。
- 新データ（patterns.sh）:

```
# 各エントリ: NAME|||DETECT|||EXEC|||MODE|||MINUS
#   DETECT: この族のサマリ行検出 regex（行にマッチしたら族「検出」）
#   EXEC:   executed の抽出 regex（MODE=sum: マッチ文字列中の数値を合計 /
#           MODE=lines: マッチ行数を数える）
#   MINUS:  減算 regex（sum のみ・空可。マッチ中の数値合計を EXEC から引く）
AEGIS_TEST_COUNT_FAMILIES=(
  'unittest|||(^|\n)Ran [0-9]+ tests? in|||Ran [0-9]+ tests?|||sum|||skipped=[0-9]+'
  'pytest|||={3,} .* in [0-9.]+s|||[0-9]+ (passed|failed)|||sum|||'
  'jest|||(^|\n)Tests:[ 	]|||[0-9]+ (passed|failed)|||sum|||'
  'vitest|||(^|\n)Tests[ 	]+[0-9]+ passed|||[0-9]+ (passed|failed)|||sum|||'
  'cargo|||(^|\n)test result: (ok|FAILED)\.|||[0-9]+ (passed|failed)|||sum|||'
  'go-verbose|||(^|\n)--- (PASS|FAIL|SKIP):|||(^|\n)--- (PASS|FAIL):|||lines|||'
)
```

  - 抽出スコープ: pytest/jest/vitest/cargo は **DETECT 該当行に限定**して EXEC を適用（jest の `5 passed` と pytest の `5 passed` の混線防止）。unittest の MINUS（`skipped=K`）は `OK (skipped=K)` 行にあり `Ran` 行にないため**全文スコープ**（誤過剰減算は fail-closed 方向で許容・後述）。go-verbose は行数カウント。
  - `|||` 区切り・literal TAB は既存 PAIRS/marker 配列の規約踏襲。

## データフロー / 構造

- 入力: verdict への stdin 全文（record/drill は FULL、evidence.sh は head+tail window — 従来どおり呼び出し側の責務）。
- 処理（Stage 5・Stage 4 通過後）:
  1. 各族の DETECT を grep -E で試行。検出 0 族 → **Stage 5 適用不能 → 従来 verdict（true）を返す**。
  2. 検出された各族について executed を計算:
     - `sum`: DETECT 該当行（unittest は全文）から `grep -oE EXEC` → 数値抽出 → Σ。MINUS があれば全文から `grep -oE MINUS` → Σ を減算。負値は 0 に clamp。
     - `lines`: `grep -cE EXEC`（行数）。
  3. **いずれかの検出族で executed ≧ 1 → true。全検出族が 0 → false。**
- 出力: "true"/"false"（従来どおり）。

### 判定規則の根拠（ANY 採用）

- 実運用では 1 コマンド=1 ランナー=1 族。複数族が同時検出されるのは出力偽装（echo 類・残余 b）か、テストがサブプロセスのランナー出力を再掲するネスト事故のみ。ALL 規則はネスト事故で実在 green を誤拒否するリスクがあり、ANY 規則が誤る（false→true）のは出力統制済み＝残余 b の前提下に限られる。よって ANY。
- Stage 5 の抽出は出力テキストのヒューリスティックであり、誤差の方向を設計で固定する: 過剰減算・族誤検出は **false 側（fail-closed・摩擦）**、過剰加算は出力統制（残余 b）下でのみ under-strict。

## ランナー別の封鎖状態（本設計適用後）

| ランナー | all-skip の verdict | 機構 | 備考 |
|---|---|---|---|
| unittest | **false（本反復で CLOSE）** | `Ran N` − Σ`skipped=K` = 0 | 実測 fixture: `Ran 2 tests ... OK (skipped=2)` |
| pytest | false（既存 moat pin 維持） | サマリに `N passed/failed` なし（Stage 2） | `N skipped in` 形 |
| cargo | false（既存 moat pin 維持・機構は Stage 5 に交換） | Σ(passed+failed)=0 | 併せて doc-tests 空の偽陰性を修正（true 化） |
| jest/vitest | false（既存動作維持＋count 防衛追加） | `Tests:` 行の passed+failed=0 | 全 skip は `N skipped, N total`＝Stage 2 で従来から false |
| go `-v` | **false（本反復で CLOSE）** | `--- PASS:|--- FAIL:` 行数 = 0（`--- SKIP:` のみ） | verbose 出力がある場合のみ |
| go（素） | **true（残余・pin 継続）** | count 族未検出 → Stage 5 適用不能 | `ok pkg dur` は all-skip と実 run が byte 同形（iter71 実測）。`-v` 強制は全 go ユーザーの UX 退行＞残余利得（drill が subsume・自己欺瞞脅威）。iter73+ attestation で根治候補 |
| echo フォージ（残余 b） | true（残余・文書化維持） | 出力ベース proof の原理的床 | 数字ごと偽装可能。drill subsume＋人手プレビューで contained |

## 依存関係

- 新規外部依存なし（bash 3.2 / BSD・GNU grep -E / 既存構成のみ）。
- patterns.sh ⇔ marker.sh は同 dir 配布（setup.sh copy_hooks 済み・iter71 deploy で検証済み）。バージョン不整合は rc3 guard が fail-closed（count 配列を guard 対象に追加。marker.sh 冒頭コメントの「ALL SIX」を「ALL SEVEN」へ更新——guard と同一変更で更新する規約は既存コメントに明記済み）。

## エラー処理

- count 配列が空/未定義（旧 patterns.sh と混載）→ rc3（評価不能・全消費者が NOT verified 扱い＝既存契約）。
- 数値抽出結果が空（DETECT 検出済みだが EXEC 不一致）→ その族 executed=0（fail-closed）。
- 負値（MINUS > EXEC）→ 0 clamp（fail-closed）。

## テスト戦略

- 単体（`tests/test_marker_lib.py`）:
  - **pin 反転**: `test_unittest_all_skip_true_known_residual` → `..._false_closed`（実測 fixture `Ran 2 tests in 0.000s\n\nOK (skipped=2)` → false）
  - **境界**: `OK (skipped=1)`・Ran 2（executed=1・実測 fixture）→ true
  - **偽陰性修正 pin**: cargo unit 5 passed ＋ doc-tests `0 passed` の現実形状 → true（本 brainstorm で false を実証済みの入力）
  - **既存 moat pin 無変更で通過**: cargo all-ignored → false／pytest all-skip → false／M2-M11／TestWeakPairBoundary
  - **go**: 素 `ok pkg dur` → true（残余 pin・コメント更新）／`-v` all-skip（`--- SKIP:` のみ）→ false／`-v` 正常 → true
  - **jest**: `Tests: 2 skipped, 3 passed, 5 total` → true
  - **rc3**: count 配列を欠いた patterns.sh → rc3
- parity（`tests/test_patterns_parity.py`）: `AEGIS_TEST_COUNT_FAMILIES` の DETECT/EXEC/MINUS を両エンジン（grep -E / python re）コンパイル＋fixture 判定一致に追加。TAB/space 両形。
- E2E（qa フェーズ）: unittest 実 run（all-skip / 混在）→ record rc2 / green を実測。go/cargo はローカル未インストールのため captured fixture を verdict 関数へ直接入力（形状根拠: iter71 review F-A 実測＋公式出力仕様）。record 経由の full suite green 記録。
- fixture の実出力根拠: unittest 2 形状は 2026-07-16 実測採取済み（BRAINSTORM-RECORD 参照）。

## リスクと残余

- **残余（意図的に閉じない）**: go 素出力 all-skip／echo フォージ（b）。いずれも SF-014 バケットで文書化継続・drill subsume で contained。SF-014 の「(a) all-skip」は unittest（＋go `-v`）分を CLOSED に更新。
- **evidence.sh の window clip**: 巨大 go `-v` 出力で head+tail window から `--- PASS:` が欠け `--- SKIP:` だけ残ると observed 経路が過剰 false になりうる（record/drill は全文なので影響なし）。摩擦方向のみ・稀・許容（設計上のトレードオフとして記録）。
- **pytest 偽陰性の非退行**: `={3,} .* in [0-9.]+s` DETECT は実 pytest サマリ形（`===== 3 passed in 0.42s =====`）に一致し、既存 M2 が黒箱ピン。

## plan 時追補（2026-07-16・実証に基づく設計精密化）

1. **jest 偽陰性（新発見・実証済み）**: 実 jest はサマリ順序が `failed, skipped, todo, passed, total` のため、skipped/todo が 1 件でもあると現行 STRONG marker `Tests:[ 	]+([0-9]+ failed,[ 	]+)?[0-9]+ passed` の隣接要求が破れ **false**（`Tests:       2 skipped, 3 passed, 5 total` で grep 不一致・marker.sh verdict=false を実測）。修正: 中間セグメントを許容する `Tests:[ 	]+([0-9]+ [a-z]+,[ 	]+)*[0-9]+ passed` へ緩和。緩和は STRONG の受理側拡大だが、攻撃者は厳格形をそのまま echo できたため forge 価値は不変（緩和で開く攻撃なし）。all-skip jest は `passed` セグメント自体が出ないため引き続き false＋Stage 5 count が二重防衛。
2. **vitest インデント疑義**: 実 vitest のサマリ（` Test Files  1 passed (1)` / `      Tests  2 passed (2)`）は行頭インデントされ、現行 `(^|\n)Test Files` アンカーに不一致の可能性（ローカルに vitest なし・未実証）。修正: アンカーに `[ 	]*` を許容（STRONG・zero-run・count DETECT とも）。同じく受理側拡大のみで forge 価値不変。qa フェーズで `npx vitest` 実行を試行し実証（不可なら fixture 根拠を記録）。
3. **cargo zero-run 行 deny 削除の安全性論証**（grill 観点の先回り）: 削除で開くのは「echo で pair を偽造＋実 cargo zero-run を併走させる」ハイブリッド forge のみ。だが**実 cargo を走らせず echo だけにすれば今日でも true**（cargo には pytest の prologue/exit5 に相当する第2軸がなく、pure-echo は現行でも素通り）。つまり攻撃者は実 run を省くだけで deny を回避できており、当該 deny の限界防御価値は「不合理に実 zero-run を併走させる攻撃者」に対してのみ。一方で偽陰性コスト（doc-tests 空の全 crate の実 green 拒否）は全正当ユーザーに恒常発生。ゆえに削除＋count 委譲が正。pytest の zero-run 系 deny（prologue/exit5 と重層）は全維持。
4. **go -v の親テスト nuance**: サブテスト全 skip でも親 `t.Run` ホルダーは `--- PASS:` を出す（親 body は実行されている）ため、-v 封鎖の対象は「トップレベル全 `t.Skip()`」形（iter71 F-A の実証形）。残余として test コメントに記録。

## footprint / task_size

- 変更ファイル: `hooks/lib/patterns.sh`・`hooks/lib/marker.sh`・`scripts/record-test-result.py`（docstring/メッセージのみ）・`tests/test_marker_lib.py`・`tests/test_patterns_parity.py` ＝ **5 ファイル → M（2-5）**。
- control-plane（反ガミング moat）変更のため **review＋qa＋security 必須**・M のため **deploy skip**（iter69 前例: patterns.sh/drill 変更で M）。

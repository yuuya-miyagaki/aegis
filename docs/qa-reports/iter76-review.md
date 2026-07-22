# iter76 review — evidence 整合＋locale 掃討完了

- 対象: iter76 実装 `097c103..ef81bd3`（W1=SF-018 LC_ALL／W2b=marker Stage 6 矛盾 veto／W2a+W3=judge washed transparent＋src allowlist）
- 設計正本: `docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md`（§実装同期 含む）
- 実装計画: `docs/plans/2026-07-22-iter76-evidence-integrity-locale-implementation-plan.md`
- 手法: 1次＝4角度 finder（仕様準拠・敵対/セキュリティ・テスト強度・保守性・opus・物理隔離 clone・read-only 6拘束）。stall した finder の load-bearing 論点は**親（fable）が in-session で実走裁定**（LEARNINGS line40＝小 diff は親直接トレースが速く確実・盲検2次のみ fresh 委譲）。2次＝盲検独立（fable・fresh・verdict 非開示）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | commit | 状態 |
|---|------------|------------|--------|------|
| 1 | RED differential pin | tests ×3 | 9898153 | ✅ 10 RED/8 PASS 実測 |
| 2 | W1 SF-018 LC_ALL | check-runtime-state.sh | 0d73d09/d3875e6 | ✅ RS1 silent-allow→deny flip |
| 3 | W2b marker Stage 6 | marker.sh/patterns.sh | 2c47cf6 | ✅ exit0×失敗証拠→false |
| 4 | W2a+W3 judge | build-judge-card.py | c73afcf | ✅ washed transparent＋src allowlist |
| 5 | 設計正本訂正＋record green | docs/specs ×2 | e115e82 | ✅ dated 訂正・full green |
| — | grill-code fix-forward | patterns.sh/tests | dc8ffd8 | ✅ [[:space:]]→literal TAB＋W2b-6 |
| — | 1次review fix-forward | tests/build-judge-card.py | ef81bd3 | ✅ W2b-6b TAB 実バイト pin＋F-3 相互参照 |

全タスク実装済み・未着手ゼロ。

## 親実走裁定（1次 load-bearing・生 evidence）

隔離 clone `iter76-rev`（HEAD=41462a4）＋親 scratch mutation。

### A. washed-green バッテリ（marker.sh・exit=0 で失敗を green 化できるか）

| 攻撃 | 入力（exit=0） | verdict | 判定 |
|---|---|---|---|
| A1 pytest 1failed | `===== 1 failed, 2 passed =====` | **false** | 封鎖 |
| A2 unittest FAILED | `Ran 3… / FAILED (failures=1)` | **false** | 封鎖 |
| A3 go FAIL | `FAIL\tgithub.com/x/y` | **false** | 封鎖 |
| A4 jest FAIL-line | `FAIL src/a.test.ts` | **false** | 封鎖 |
| A5 抑制+washed | 空出力（summary marker 無） | **false** | marker 不成立で封鎖 |
| A6 本物 green | `3 passed` | **true** | 正常（非退行） |

→ washed-green 経路 **バイパス 0件**・本物 green は保全。

**追加変種（1次敵対 finder が旗を立てた綴りを親が judge e2e で実証・全 unverified）**:

| 変種 | marker_verified | judge |
|---|---|---|
| V1 `pytest -q > out.txt; true`（失敗出力可視） | False | unverified |
| V2 同（出力ファイル化で観測空） | False | unverified |
| V3 `pytest -q $(printf ';') true`（cmdsub 区切り） | False | unverified |
| V4 `pytest -q && true` | False | unverified |

→ redirect・cmdsub・`&&` いずれも Stage 6（失敗証拠×exit0）＋judge W2a（演算子検出）の二重で封鎖。

### B. SF-018 バイトバッテリ（0xFF 以外でも silent-allow に落ちないか）

| 攻撃（STATUS 書込み・非 framework） | decision | 判定 |
|---|---|---|
| B1 0xFE + STATUS write | **deny** | 封鎖 |
| B2 0xFF0xFE + STATUS write | **deny** | 封鎖 |
| B3 末尾 0xFF コメント + write | **deny** | 封鎖 |
| B4 byte + .claude read + STATUS write | **deny** | 封鎖 |

→ 0xFF 以外・混在バイト・別経路（redirect target）でも fail-open **0件**。

### C. record 経路の washed 非対称（敵対 finder の追跡論点を親が確定）

`drill._execute`（run-test-strength-drill.py:546）は **shell を介さず** `subprocess.run(shlex.split(cmd))` で実行。含意:
- `pytest -q; true`（`;` 前空白なし）は shlex で `-q;` が1トークン→shell-op ガード（record-test-result.py:120）はすり抜けるが、`; true` が pytest への無効引数になりランナー error/fail→**red 記録**（washing 不成立）。実測: `record "python3 -m pytest -q; true"` → `recorded: red`。
- `pytest || echo done`（空白あり）は `||` が単独トークン→shell-op ガードで **_reject**。

→ record（manual src）経路は **no-shell 実行が構造的防御**＝washed-green 免疫。observed 経路は Stage 6（marker）＋judge W2a で被覆。両経路とも閉。

### D. differential 歯の mutation 実測（テスト強度）

| pin | mutant | baseline | mutant 結果 | 歯 |
|---|---|---|---|---|
| W3-2（terminal が古い green を遮る） | src allowlist `return unverified`→`continue` | unverified | **green** | あり（RED 化） |
| W2a-2（transparent が古い green を生かす） | washed skip `continue`→`return unverified` | green | **unverified** | あり（RED 化） |
| W2b-6b（fail-token literal TAB） | regex TAB→space degrade | false | **true** | あり（M10 罠を捕捉） |

→ 非対称（terminal↔transparent）は両方 pin・TAB 実バイト経路も回帰保護あり。

## 1次 findings（severity 付き・confidence）

### 保守性（reviewer-maintainability・最終報告受領）

- **F-1（Minor・conf8）→ 修正済み**: W2b-6 の fixture が `FAIL`+space で literal TAB バイトを検証せず、エディタ正規化（iter71 M10）で go の `FAIL\tpkg` 経路が壊れても緑のまま。→ `test_w2b6b_fail_line_tab_byte_with_exit0_is_false` を追加（TAB→space degrade で RED 化を実証・ef81bd3）。
- **F-2（ポジティブ・conf9）**: 判定権威は一元化（wash 検査＝judge 1点／marker＝3消費者共通・writer evidence.sh は untouched）。権威分裂なし。
- **F-3（Minor・conf6）→ 対応済み**: record の shlex トークンガードと judge regex が同一脅威（shell-op washing）の別実装で相互参照なし。→ `_cmd_has_shell_operators` docstring に sibling defense 相互参照コメントを追加（ef81bd3）。
- **F-4（Minor・conf7）→ accept-as-is**: src allowlist が inline tuple（named constant でない）。docstring とコード内コメントで二重文書化済み・外部参照なし・single-owner 意図は保持＝実害小につき現状維持（review note）。
- **F-5（ポジティブ・conf9）**: single-source 整合（FAIL_TOKEN_REGEX は patterns.sh 単一・marker.sh 2箇所消費）・rc3 ガード「ALL EIGHT」が実8チェックと一致（W2b-5 で実測裏付け）・コメント正確（`\n`→literal n degrade・空 exit_code skip）。

### 仕様準拠（reviewer・トレーサビリティ確定）

全完了条件（`pytest; true`/`|| echo`/`| tee`/fake-output/unknown-src が green 不可・runtime-state byte crash 消滅・設計正本訂正・旧赤/新緑 pin）が実 assert で裏取り済み。W2b-6/6b は既存 branch の coverage pin＝in-scope（scope creep でない）。

### 仕様準拠（reviewer・4角度目・承認後に最終報告到着＝corroboration）

verdict **approve・findings 0件**（Critical/Major/Minor いずれも0）。全4 production 変更が計画のファイル/位置/意味論に一致・差分 pin が pre-fix コードに対し実測成立・full green・contract PASS・設計逸脱は全て dated 記録を独立確認。唯一の note は plan baseline 見積り（1367 passed）が実測（1394）と stale＝**実装計画スナップショット規約どおり**（正確な現数は本 QA/レポート側・非該当）。review 承認判断を事後裏付け。

### テスト強度（親裁定＝上表 D）・敵対/セキュリティ（親裁定＝上表 A/B/C）

Critical 0・新規バイパス 0。既知天井（単一コマンド fake binary＝PATH hijack・log 直書き）は iter77 attestation 領分／脅威モデル外＝**新規穴でない**（design §残余・test_residual 相当は iter77 で flip 強制）。

## 検証サマリ

- full suite: 1391 passed / 2 skipped（record green・trusted runner）
- 影響テスト（6ファイル）: 189 passed
- contract: PASS
- メイン repo tree: clean（review clone・stray worktree は除去済み）

## 盲検2次（reviewer-maintainability・fable・fresh・verdict 非開示）＝divergence 1件

**verdict: approve_with_notes**（Critical/Major 0・washed-green 代表攻撃と SF-018 byte 封鎖を独立実走で確認）。

**divergence（1次の見落としを2次が摘発・盲検の価値）**: `AEGIS_TEST_FAIL_TOKEN_REGEX` が pytest の **`errors` 語形**（`1 passed, 2 errors in`）を非対象。1次バッテリは `failed`/`FAILED`/`FAIL` を叩いたが `errors` を叩いていなかった。

**親裁定（実証してから限界主張）**:
- E1（marker 単体）: `1 passed, 2 errors`+exit0 → pre-fix **true**／E2（judge e2e・演算子なし単一 cmd）→ pre-fix **green**＝**合成到達可能**。
- real 到達性: 本物単一 pytest errors は **exit 2**＝status=fail。observed で status=ok にするには演算子洗浄（→W2a 捕捉）か fake binary（→iter77 天井）が必要＝**脅威モデル内で独立到達不能**。
- **緩和（fix-forward）**: tight anchor `[1-9][0-9]* errors? in [0-9]`（pytest timing tail 限定・benign 非マッチを実測）を第5 alt に追加＝共通コア消費者（record/drill）でも errors washed を veto。pin＝`test_w2b7_*`＋`test_w2b7b`（過剰マッチ防止）。残余（denylist 原理的不完全性）は SF-022 に記録し iter77 attestation で根治。
- E1 再実測（fix 後）→ **false**（flip 確認）。

その他 2次 findings は 1次と収束（manual/observed の W2a 非対称＝設計意図・evidence-log 直書きは脅威モデル外／複雑さ North Star 許容／differential 歯・rc3 8ソースを独立確認）＝Critical/Major 0。

```claims
tests_pass: true
no_stubs: true
scope_creep: false
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["AEGIS_TEST_FAIL_TOKEN_REGEX が pytest errors 語形を非対象（1次見落とし）→ 親裁定: 脅威モデル内独立到達不能を実証・tight anchor で緩和・SF-022 記録・iter77 で根治"]
```

## Exit 判定（1次＋2次収束）

**approve**（Critical/Major 0・1次/2次とも washed-green/SF-018 の主張クラス内バイパス 0件を独立実走で確認・differential 歯を mutation 実測）。盲検2次の divergence（errors 語形）は親が実証裁定＝脅威モデル内独立到達不能を確認のうえ tight anchor で fix-forward 緩和・SF-022 に残余記録・iter77 attestation で根治。保守性 finding（F-1 TAB 実バイト・F-3 相互参照）も fix-forward 済み。1次/2次の verdict は実質同意（approve / approve_with_notes＝notes は全て fix-forward 済みまたは SF 記録で対応）。

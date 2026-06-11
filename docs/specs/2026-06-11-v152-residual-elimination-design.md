# v1.5.2 残余リスク全消化バッチ — 設計書（2026-06-11）

## 背景と目的

v1.5.1 で記録した新規残余（docs/qa-reports/v151-security.md「残余リスク」5 件）を全て解消する。
ユーザー判断により、設計上「文書化済み／非目標」とした 2 件（`\/` fast-path 非ルーティング・
ロック待機 2s の敗者 rc=1）もスコープに含める（待機窓拡大の方向で対処、自動リトライは引き続き非目標）。

| 残余（v151-security.md） | 本バッチの対処 |
|--------------------------|----------------|
| クォート内 `;&\|` quote-blindness（`grep -E "(unittest\|pytest)" f` の `\|runner` 形・`grep "foo; pytest" f` 形の false-RED） | T1: クォートマスク正規化 |
| 入れ子サブシェル `((pytest))` の分類不一致 | T2: アンカー拡張 |
| `\/` エスケープの fast-path 非ルーティング | T3: ルーティングクラスに `/` 追加 |
| claim-mv 後 undo 前クラッシュの pid なしロック残留 | T4: ロック自己修復 |
| ロック待機 2s は実競合で常に敗者 rc=1 | T5: 待機窓拡大（10s） |

方針: 全て可用性／誤判定緩和の方向。**deny 系の防御強度は一切変えない**（明示非目標）。
green 偽装に使える変更はゼロ（分類変化は unverified=fail-closed 方向のみ）。

## T1: クォートマスク正規化（分類パイプライン第 2 正規化段）

### 契約

テストランナー分類の照合直前パイプラインを次に固定する（消費者 2 系統で同一）:

```
raw command → 改行正規化（\n → ;）→ クォート span の不活性トークン置換（"…"/'…' → Q、二重→単一の順）→ AEGIS_TEST_RUNNER_REGEX 照合
```

**置換であって削除ではない**（grill-plan A 🔴-1）: span を空文字に削除すると
`"echo" pytest`（実行されるのは echo、rc=0）が ` pytest` に縮退して後続引数が
コマンド位置に**昇格**し、新たな green 偽装経路になる。不活性トークン `Q` への
置換なら `Q pytest` となり、`Q` はランナーでもラッパーでもないため不一致＝
v1.5.1 の挙動を維持する。`Q` は `=` を含まないため env 代入正規表現にも
吸収されない（`FOO="bar" pytest` → `FOO=Q pytest` は env 経由で正しく一致）。

### マスクパターン（patterns.sh 単一所有）

```bash
# 二重引用符 span（バックスラッシュエスケープ対応）
AEGIS_TR_STRIP_DQ='"(\\.|[^"\\])*"'
# 単一引用符 span（shell の単一引用符内にエスケープは存在しない）
AEGIS_TR_STRIP_SQ="'[^']*'"
```

- 適用順は**二重→単一に固定**（規約）。検証済み fixtures 上では両順で結果同一であり
  （grill-plan B 🟡-2）、順序は安全根拠ではなく parity fixtures でピン留めする規約。
  混在クォートが互いを横断する形は順序によらず受容残余（後述）
- 両パターンとも BSD/GNU `sed -E` と Python `re` で同一挙動の ERE サブセット
  （ブラケット内 `\\` は両者でリテラル backslash、`\\.` は backslash+任意 1 字）。
  grill-plan A/B が両エンジン同一性を 12 形で実測確認済み
- エスケープ対応の実効: `grep "a\" ; pytest" f` は `\"` を `\\.` が吸収し span 全体がマスクされる
  （naive `"[^"]*"` では `; pytest` が露出して false-RED が残る）

### 消費者

| 消費者 | 実装 |
|--------|------|
| hooks/post-bash.sh | 既存 `tr '\n' ';'` の後に `sed -E "s/${AEGIS_TR_STRIP_DQ}/Q/g" \| sed -E "s/${AEGIS_TR_STRIP_SQ}/Q/g"`（パターンに `/` を含まないため s/// デリミタ安全、置換文字列 `Q` に sed 特殊文字なし） |
| scripts/build-judge-card.py | 既存 `.replace("\n", ";")` の後に `re.sub(DQ, "Q", s)` → `re.sub(SQ, "Q", s)`。パターンは `_test_runner_patterns()`（build-judge-card.py:110-114）と同じ bash-source `printf` サブプロセス経路で `AEGIS_TR_STRIP_DQ`/`AEGIS_TR_STRIP_SQ` を取得（grill-plan B 🟢-1 のピン留め） |

### スコープ境界（明示）

- **マスクは分類判定のみ**。evidence-log に記録するコマンドは raw のまま（fidelity 契約・payload_sha は不変）
- **deny 系（check-destructive.sh / check-control-plane.sh / check-secrets.sh）には適用しない**。
  deny 側のマスクは「クォートで包めば deny を回避できる」fail-open になるため明示非目標
- 既存のコマンド位置アンカー（v1.5.1 `_AEGIS_TR_PRE`）は **defense-in-depth としてそのまま残す**
  （閉じ忘れクォート等、マスクが効かない不正形の受け皿）

### 挙動変化（README Migration 記載）

| 形 | v1.5.1 | v1.5.2 | 方向 |
|----|--------|--------|------|
| `grep -E "(unittest\|pytest)" f`（rc≠0） | `\|pytest` が一致 → false-RED | 不一致（`grep -E Q f`） | false-RED 解消 |
| `grep "foo; pytest" missing.txt`（rc≠0） | クォート内 `;` で一致 → false-RED | 不一致（`grep Q missing.txt`） | false-RED 解消 |
| `pytest "tests/foo bar"` | 一致 | 一致（`pytest Q`、先頭ランナー残存） | 不変 |
| `npx "vitest"`・`"pytest" -x` | 不一致（`"` がアンカー外） | 不一致（`npx Q`・`Q -x`） | 不変=unverified（新規に受容記録） |
| `"echo" pytest`（rc=0） | 不一致 | 不一致（`Q pytest`） | 不変。**削除方式なら一致化＝green 偽装**（grill A 🔴-1 で封鎖） |
| `echo ""; pytest` | 一致 | 一致（`echo Q; pytest`） | 不変（正しい） |
| `echo 'a"b'; pytest "x"`（pytest 実行形） | 一致 | 不一致（DQ span が `'` を横断消費） | 新規受容: 混在クォート横断は unverified=fail-closed 方向（grill A 🟡-2、fixtures＋v152-security.md に記録） |

## T2: アンカー拡張（入れ子 `(`）

`_AEGIS_TR_PRE` の `\(? *` を `(\( *)*` に変更（コマンド位置の `(` を 0 個以上許容）:

```bash
_AEGIS_TR_PRE='(^|[;&|]) *(\( *)*([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*((npx|bunx) +|(uv|poetry|pipenv) +run +)?'
```

- `((pytest))`・`( (vitest run))` が分類されるようになる（unverified 縮小、green 偽装には使えない）
- クォート起源の `(`（`grep -E "(pytest|…)"` 等）は T1 マスク後に到達しないため、
  v1.5.1 grill 🟡-1 の安全性は T1 と独立に維持される（マスク不能な不正形はアンカーが受け皿）
- v1.5.1 にアンカー根拠として書いた patterns.sh:60-65 のコメント（`(` 非クラス・
  `((pytest))` accepted miss）は T1/T2 で陳腐化するため同時に書き換える（grill A 🟢-2）

## T3: `\/` fidelity ルーティング

hooks/lib/extract-input.sh のルーティングクラスに `/` を追加:

```bash
grep -q '\\[\\nrtbfu"]'   →   grep -q '\\[\\nrtbfu"/]'
```

- `\/` を含むペイロードも python3 fidelity 経路に乗る（grep 経路のリテラル 2 文字化を完全回避）
- v1.5.1 で「標準エンコーダ非生成のため意図的除外」としたコメントを「完全性のため包含」に更新
- deny 系（check-control-plane）は python3-first で独立・無影響（従来どおり）

## T4: ロック自己修復（update-gate.sh 待機ループ内、いずれも fail-closed 維持）

### (a) 孤児 claim 復元

claim-mv プロトコル上、`pid.claim.<claimer-pid>` と `pid` は同時に存在しない
（claim は pid の atomic mv でのみ生成される）。よって claim が残留している＝
claimer が undo/完了前に死んだ、が確定できる場合は復元してよい:

```
LOCK_DIR 内に pid.claim.* が存在
  AND ファイル名末尾の claimer-pid が純数値
  AND kill -0 claimer-pid が失敗（dead）
  AND pid ファイル不在
→ mv claim → pid（失敗は無視＝並行復元との競合は片方が勝てばよい）
→ 以後は既存の dead-pid 回収路に合流（中身の元保持者 pid で回収判定）
```

claimer が live の場合・pid が非数値の場合は不介入（fail-closed）。

### (b) pid なしロックの age-gated 採用（adoption）

mkdir 直後〜pid 書込前のクラッシュ（kill -9 等、trap 不発）で残る「pid なしロック」は、
**回収（rmdir）せず、O_EXCL（noclobber）で自分の pid を原子的に作成して引き取る**:

```
pid ファイル不在
  AND claim ファイル不在（(a) の処理対象でない）
  AND LOCK_DIR の mtime が経過（find "$LOCK_DIR" -maxdepth 0 -mmin +1 2>/dev/null が非空）
→ ( set -C; printf '%s' "$$" > "$LOCK_DIR/pid" ) 2>/dev/null
  成功 = その場でロック保有者（LOCK_OK=true・trap 設定・ループ脱出）／失敗 = 待機継続
```

- **rm→rmdir 方式は不採用**（grill A 🔴-2）: age 判定と削除が非原子（check-then-act）で、
  判定後に別 contender の回収→新勝者の取得が挟まると生きた pid を削除しロックを破壊する
  （/tmp 再現済み）。mv-dir 退避案も検査〜undo 間に同型の残窓がある。O_EXCL create は
  単一システムコールで所有が決まり、check-then-act 窓そのものが存在しない
- 複数 contender が同時に採用を試みても勝者は 1 人（O_EXCL）。敗者は以後 live pid を
  観測して待機（fail-closed）
- age gate: `-mmin +1` は POSIX 規定の floor(age/60) 比較のため**実効 2 分超**（grill B 🟡-1）。
  BSD/GNU find 共通（`stat -f/-c` 分岐を回避）。dir mtime はエントリ追加で更新されるため
  取得直後・claim 活動中の dir は必ず若い。find は dir 消失時 rc≠0＋stderr のため
  `2>/dev/null` を明記（grill A 🟢-1）
- **空 pid・garbage pid（非数値）は従来どおり不介入**＝手動削除案内（fail-closed 維持。
  空 pid はファイルが存在するため O_EXCL が失敗し、構造的に採用対象外）
- 採用成功後は通常保有と同一の trap（pid 削除→rmdir）で解放される

### 新規受容リスク（記録）

SIGSTOP 等で mkdir→pid 書込の間が 2 分超停止する病的形では、採用者の pid を
元保持者の printf が上書きし、相互に保有を誤認し得る（極小窓 × 病的停止の合成。
単一ユーザー運用前提で受容、v152-security.md に記録）。

## T5: 待機窓拡大

待機ループを 10 回 → **50 回**（×0.2s = 計 10s）に拡大:

```bash
for _ in {1..50}; do   # bash 3.2 互換のブレース範囲
```

- 通常実行（reset・軽量 approve 等、数秒以内）を確実に超えるため、実競合の敗者は勝者完了後に自力取得できる
- **スコープ注記**（grill A 🟡-1）: qa/security の pre-approve は B1 ドリル実走
  （check_status.py:982-985、分オーダー）と judge の audit_deps（build-judge-card.py:218-233、
  timeout 120s）を**ロック内**で実行するため、重ゲート競合の敗者は依然 rc=1 になり得る
  （「Retry shortly」案内どおり正しく fail）。README の可用性記述もこのスコープで書く
- claim プロトコル・エラーメッセージ・rc 契約（取得不能時 rc=1）は不変。自動リトライ（プロセス再実行）は引き続き非目標
- **既存テストの期待値変更**: v1.5.1 レース drill の「実競合の敗者は常に rc=1」は
  「敗者も勝者完了後に逐次成功する」に更新（意図的な仕様変更）。live 競合 drill は
  高速パス（reset 等）に固定して flake を排除する

## テスト戦略（TDD、タスクごと RED→GREEN→ミラー同期→コミット）

| 対象 | テスト |
|------|--------|
| T1 parity | test_patterns_parity.py のハーネスを「正規化（\n→; ＋クォートマスク）込みパイプライン」に拡張し、sed -E／re.sub の両経路で fixtures 照合。新 fixtures: quoted-group False／`grep "foo; pytest" f` False／escaped-quote 形 False／`pytest "a b"` True／`npx "vitest"` False／**`"echo" pytest` False（昇格封鎖の反転 fixture＝削除方式に revert すると RED）**／`echo ""; pytest` True／混在横断 `echo 'a"b'; pytest "x"` False（受容の固定） |
| T1 e2e | judge card e2e: 実 green の後に `grep -E "(unittest\|pytest)" missing.txt`（rc≠0）を観測しても verdict green 維持 |
| T1 境界 | deny 系にマスクが波及していないこと（check-control-plane の quoted 形 deny が不変であることを既存テストで担保・必要なら固定 fixture 追加） |
| T2 | fixtures: `((pytest))` True／`( (vitest run))` True／既存全 fixtures 不変 |
| T3 | `\/` 入りペイロードが python3 経路で fidelity 保持されることの hook 実発火テスト |
| T4 | 単体: 孤児 claim（claimer dead）復元／claimer live 不介入／pid なし dir の age-gate 採用（`touch -t` で旧 mtime 偽装）・若い dir 不採用／空 pid・garbage pid 不介入／採用後の trap 解放。レース: dead-pid drill 15 回再走（単独勝者・torn write ゼロ維持）＋**採用競合 drill（複数 contender 同時採用で勝者 1 人）** |
| T5 | 構造テスト（ループ回数 50）＋ live 競合 drill（高速パス固定）: 2 contender 同時起動で**両方成功**（敗者が 10s 内に取得） |
| 回帰 | 全 461+ tests／contract full+standard／drift（ミラー byte 同一）／scaffold smoke／check_status --strict |

## 変更ファイルマップ

| 種別 | ファイル | 対応タスク |
|------|---------|-----------|
| lib | hooks/lib/patterns.sh（STRIP パターン追加＋_AEGIS_TR_PRE 拡張＋v1.5.1 アンカー根拠コメントの書換） | T1, T2 |
| hook | hooks/post-bash.sh（分類前のマスク段） | T1 |
| script | scripts/build-judge-card.py（分類前のマスク段） | T1 |
| lib | hooks/lib/extract-input.sh（ルーティングクラス `/`） | T3 |
| script | scripts/update-gate.sh（自己修復＋待機窓） | T4, T5 |
| mirror | examples/minimal-project/ 配下の上記 5 ファイル（byte 同一） | 全 |
| tests | test_patterns_parity.py／judge e2e／extract-input／update-gate lock 系 | 全 |
| docs | README.md（Migration: From v1.5.1 to v1.5.2）／docs/architecture-overview.md（履歴行） | — |
| version | check_framework_contract.py／STATUS.template.md／example STATUS／docs/STATUS.md＝"1.5.2" | — |

規模: L（12 ファイル前後＋テスト）。

## SemVer 判定

patch（1.5.1 → 1.5.2）。運用契約（ゲート遷移・judge tri-state・hook 構成・配布物）への変更なし。
内容は誤判定緩和（false-RED 根治）・可用性向上（ロック自己修復・待機窓）・分類忠実度（`\/`）のみ。
分類の挙動変化（quoted ランナー語の非分類化）は unverified=fail-closed 方向で README Migration に記載。

## grill-plan 反映記録（2026-06-11、独立 2 本: A=既定モデル／B=sonnet）

両者とも「条件付き着手可」。指摘と反映:

| ID | 指摘（要旨） | 反映 |
|----|------------|------|
| A 🔴-1 | クォート span の「削除」は `"echo" pytest` で後続引数がコマンド位置に昇格＝新規 green 偽装経路（sed/re 両エンジンで実証） | 削除→**不活性トークン `Q` 置換**に設計変更。反転 fixture で revert を RED 化 |
| A 🔴-2 | T4(b) rm→rmdir は check-then-act で、競合時に生きた勝者の pid を削除しロック破壊（/tmp 再現済み） | 回収方式を廃し **O_EXCL（noclobber）採用方式**に設計変更（A 提案の mv-dir 退避は検査〜undo 間に同型残窓があるため不採用） |
| A 🟡-1 | qa/security の pre-approve は B1 ドリル＋audit_deps をロック内実行＝分オーダーで、10s 窓でも敗者 rc=1 があり得る | T5 にスコープ注記。live 競合 drill は高速パス固定、README 記述もスコープ |
| A 🟡-2 | 混在クォート横断 `echo 'a"b'; pytest "x"` が新規 false-negative（fail-closed 方向） | 挙動変化表＋受容残余＋fixture に追加 |
| A 🟢-1 | find は dir 消失時に rc≠0＋stderr ノイズ | 擬似コードに `2>/dev/null` 明記 |
| A 🟢-2 | patterns.sh:60-65 の v1.5.1 コメントが T1/T2 で陳腐化 | T2 節＋ファイルマップに書換を明記 |
| B 🟡-1 | `-mmin +1` は POSIX floor(age/60) 比較で実効 2 分超（「60s 超」は誤記） | age gate 記述を「実効 2 分超」に修正 |
| B 🟡-2 | DQ→SQ 順の根拠「it's 形」は不正確（両順で結果同一） | 順序を「fixtures でピン留めする規約」に改記 |
| B 🟢-1 | build-judge-card.py の STRIP 変数取得経路が未明示 | `_test_runner_patterns()` と同じ bash-source printf サブプロセス経路と明記 |

確認済み（両者）: マスクパターンの両エンジン同一性（12 形実測）、消費者 2 系統の挿入位置、
T2 既存 fixtures 無回帰、T3 ブラケット表現、T4(a) claim/pid 排他の前提成立、
bash 3.2 `{1..50}`・BSD find `-mmin`・`touch -t` の dir mtime 偽装、ミラー 5 ファイル存在、SemVer patch 妥当。

## 工程

定着フロー: 本設計書 → **grill-plan（独立サブエージェント 2 本）** → 指摘反映 → 実装計画
（docs/plans/2026-06-11-v152-residual-elimination-implementation-plan.md）→ plan ゲート →
TDD 実装（T1〜T5＋版数） → **grill-code（独立 2 本）** → テスト記録 → 4 ゲート --ack 承認
（証跡 docs/qa-reports/v152-*.md）→ session_history 追記 → tag v1.5.2。origin push はユーザー判断。

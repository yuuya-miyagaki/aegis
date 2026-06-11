# v1.5.2 残余リスク全消化バッチ — 設計書（2026-06-11）

## 背景と目的

v1.5.1 で記録した新規残余（docs/qa-reports/v151-security.md「残余リスク」5 件）を全て解消する。
ユーザー判断により、設計上「文書化済み／非目標」とした 2 件（`\/` fast-path 非ルーティング・
ロック待機 2s の敗者 rc=1）もスコープに含める（待機窓拡大の方向で対処、自動リトライは引き続き非目標）。

| 残余（v151-security.md） | 本バッチの対処 |
|--------------------------|----------------|
| クォート内 `;&\|` quote-blindness（`grep -E "(unittest\|pytest)" f` の `\|runner` 形・`grep "foo; pytest" f` 形の false-RED） | T1: クォート除去正規化 |
| 入れ子サブシェル `((pytest))` の分類不一致 | T2: アンカー拡張 |
| `\/` エスケープの fast-path 非ルーティング | T3: ルーティングクラスに `/` 追加 |
| claim-mv 後 undo 前クラッシュの pid なしロック残留 | T4: ロック自己修復 |
| ロック待機 2s は実競合で常に敗者 rc=1 | T5: 待機窓拡大（10s） |

方針: 全て可用性／誤判定緩和の方向。**deny 系の防御強度は一切変えない**（明示非目標）。
green 偽装に使える変更はゼロ（分類変化は unverified=fail-closed 方向のみ）。

## T1: クォート除去正規化（分類パイプライン第 2 正規化段）

### 契約

テストランナー分類の照合直前パイプラインを次に固定する（消費者 2 系統で同一）:

```
raw command → 改行正規化（\n → ;）→ クォート区間除去（二重→単一の順）→ AEGIS_TEST_RUNNER_REGEX 照合
```

### 除去パターン（patterns.sh 単一所有）

```bash
# 二重引用符 span（バックスラッシュエスケープ対応）
AEGIS_TR_STRIP_DQ='"(\\.|[^"\\])*"'
# 単一引用符 span（shell の単一引用符内にエスケープは存在しない）
AEGIS_TR_STRIP_SQ="'[^']*'"
```

- 適用順は**二重→単一**。`echo "it's fine"; pytest` で `'` 片割れが誤 span を作らないため
- 両パターンとも BSD/GNU `sed -E` と Python `re` で同一挙動の ERE サブセット
  （ブラケット内 `\\` は両者でリテラル backslash、`\\.` は backslash+任意 1 字）。
  parity fixtures で実測固定する
- エスケープ対応の実効: `grep "a\" ; pytest" f` は `\"` を `\\.` が吸収し span 全体が除去される
  （naive `"[^"]*"` では `; pytest` が露出して false-RED が残る）

### 消費者

| 消費者 | 実装 |
|--------|------|
| hooks/post-bash.sh | 既存 `tr '\n' ';'` の後に `sed -E "s/${AEGIS_TR_STRIP_DQ}//g" \| sed -E "s/${AEGIS_TR_STRIP_SQ}//g"`（パターンに `/` を含まないため s/// デリミタ安全） |
| scripts/build-judge-card.py | 既存 `.replace("\n", ";")` の後に `re.sub(DQ, "", s)` → `re.sub(SQ, "", s)`。パターンは AEGIS_TEST_RUNNER_REGEX と同一の patterns.sh 取り込み経路で取得 |

### スコープ境界（明示）

- **除去は分類判定のみ**。evidence-log に記録するコマンドは raw のまま（fidelity 契約・payload_sha は不変）
- **deny 系（check-destructive.sh / check-control-plane.sh / check-secrets.sh）には適用しない**。
  deny 側の除去は「クォートで包めば deny を回避できる」fail-open になるため明示非目標
- 既存のコマンド位置アンカー（v1.5.1 `_AEGIS_TR_PRE`）は **defense-in-depth としてそのまま残す**
  （閉じ忘れクォート等、除去が効かない不正形の受け皿）

### 挙動変化（README Migration 記載）

| 形 | v1.5.1 | v1.5.2 | 方向 |
|----|--------|--------|------|
| `grep -E "(unittest\|pytest)" f`（rc≠0） | `\|pytest` が一致 → false-RED | 不一致 | false-RED 解消 |
| `grep "foo; pytest" missing.txt`（rc≠0） | クォート内 `;` で一致 → false-RED | 不一致 | false-RED 解消 |
| `pytest "tests/foo bar"` | 一致 | 一致（先頭ランナー残存） | 不変 |
| `npx "vitest"`・`"pytest" -x` | 不一致（`"` がアンカー外） | 不一致（除去後も wrapper 残骸のみ） | 不変=unverified（新規に受容記録） |
| `echo ""; pytest` | 一致 | 一致 | 不変（正しい） |

## T2: アンカー拡張（入れ子 `(`）

`_AEGIS_TR_PRE` の `\(? *` を `(\( *)*` に変更（コマンド位置の `(` を 0 個以上許容）:

```bash
_AEGIS_TR_PRE='(^|[;&|]) *(\( *)*([A-Za-z_][A-Za-z0-9_]*=[^ ]* +)*((npx|bunx) +|(uv|poetry|pipenv) +run +)?'
```

- `((pytest))`・`( (vitest run))` が分類されるようになる（unverified 縮小、green 偽装には使えない）
- クォート起源の `(`（`grep -E "(pytest|…)"` 等）は T1 除去後に到達しないため、
  v1.5.1 grill 🟡-1 の安全性は T1 と独立に維持される（除去不能な不正形はアンカーが受け皿）

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

### (b) pid なし／空 pid ロックの age-gated 回収

mkdir 直後〜pid 書込前のクラッシュ（kill -9 等、trap 不発）で残る「pid なしロック」と、
書込失敗で残り得る「空 pid ロック」を回収する:

```
pid ファイルが不在または空（-s が偽）
  AND claim ファイル不在（(a) の処理対象でない）
  AND LOCK_DIR の mtime が 60 秒超経過（find "$LOCK_DIR" -maxdepth 0 -mmin +1 が非空）
→ rm -f pid（空ファイルの場合）→ rmdir（atomic、非空なら失敗＝安全）
```

- age gate（60s 超）が正常取得中の mkdir→pid 書込の瞬間窓を保護する
  （dir mtime はエントリ追加で更新されるため、取得直後の dir は必ず若い）
- `-mmin` は BSD/GNU find 共通（`stat -f/-c` の分岐を回避）
- **garbage pid（非数値・非空）は従来どおり不回収**＝手動削除案内（fail-closed 維持）
- 待機ループは 0.2s 間隔のため、回収成立後は同一ループ内で mkdir 再試行に到達する

### 新規受容リスク（記録）

SIGSTOP 等で mkdir→pid 書込の間が 60 秒超停止する病的形では誤回収し得る
（極小窓 × 病的停止の合成。単一ユーザー運用前提で受容、v152-security.md に記録）。

## T5: 待機窓拡大

待機ループを 10 回 → **50 回**（×0.2s = 計 10s）に拡大:

```bash
for _ in {1..50}; do   # bash 3.2 互換のブレース範囲
```

- update-gate 1 実行（通常 1〜2s）を確実に超えるため、実競合の敗者は勝者完了後に自力取得できる
- claim プロトコル・エラーメッセージ・rc 契約（取得不能時 rc=1）は不変。自動リトライ（プロセス再実行）は引き続き非目標
- **既存テストの期待値変更**: v1.5.1 レース drill の「実競合の敗者は常に rc=1」は
  「敗者も勝者完了後に逐次成功する」に更新（意図的な仕様変更）

## テスト戦略（TDD、タスクごと RED→GREEN→ミラー同期→コミット）

| 対象 | テスト |
|------|--------|
| T1 parity | test_patterns_parity.py のハーネスを「正規化（\n→; ＋クォート除去）込みパイプライン」に拡張し、sed -E／re.sub の両経路で fixtures 照合。新 fixtures: quoted-group False／`grep "foo; pytest" f` False／escaped-quote 形 False／`pytest "a b"` True／`npx "vitest"` False／`echo ""; pytest` True |
| T1 e2e | judge card e2e: 実 green の後に `grep -E "(unittest\|pytest)" missing.txt`（rc≠0）を観測しても verdict green 維持 |
| T1 境界 | deny 系に除去が波及していないこと（check-control-plane の quoted 形 deny が不変であることを既存テストで担保・必要なら固定 fixture 追加） |
| T2 | fixtures: `((pytest))` True／`( (vitest run))` True／既存全 fixtures 不変 |
| T3 | `\/` 入りペイロードが python3 経路で fidelity 保持されることの hook 実発火テスト |
| T4 | 単体: 孤児 claim（claimer dead）復元→回収／claimer live 不介入／pid なし dir の age-gate（`touch -t` で旧 mtime 偽装）回収・若い dir 不回収／空 pid 同様／garbage pid 不回収（既存）。レース: dead-pid drill 15 回再走（単独勝者・torn write ゼロ維持） |
| T5 | 構造テスト（ループ回数 50）＋ live 競合 drill: 2 contender 同時起動で**両方成功**（敗者が 10s 内に取得） |
| 回帰 | 全 461+ tests／contract full+standard／drift（ミラー byte 同一）／scaffold smoke／check_status --strict |

## 変更ファイルマップ

| 種別 | ファイル | 対応タスク |
|------|---------|-----------|
| lib | hooks/lib/patterns.sh（STRIP パターン追加＋_AEGIS_TR_PRE 拡張） | T1, T2 |
| hook | hooks/post-bash.sh(分類前の除去段) | T1 |
| script | scripts/build-judge-card.py（分類前の除去段） | T1 |
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

## 工程

定着フロー: 本設計書 → **grill-plan（独立サブエージェント 2 本）** → 指摘反映 → 実装計画
（docs/plans/2026-06-11-v152-residual-elimination-implementation-plan.md）→ plan ゲート →
TDD 実装（T1〜T5＋版数） → **grill-code（独立 2 本）** → テスト記録 → 4 ゲート --ack 承認
（証跡 docs/qa-reports/v152-*.md）→ session_history 追記 → tag v1.5.2。origin push はユーザー判断。

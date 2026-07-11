# iter65 review レポート — S サイズ修復（R2🔴）

- 対象: `git diff 26de7f6..HEAD`（S サイズ修復 Fix 1/2/3a＋テスト＋guidance 同期）
- 仕様正本: `docs/specs/2026-07-10-iter65-s-size-repair-design.md` ／ 計画 `docs/plans/2026-07-10-iter65-s-size-repair-implementation-plan.md`
- 手法: 1次＝4角度 finder 並列（bash 堅牢性=opus / gate 迂回=opus / テスト強度=opus / 仕様準拠=opus）→ 親（fable）verify・fix-forward。全 finder は read-only 6拘束下・fixture は mktemp のみ・repo tree 非破壊。
- full suite: **1096 passed / 2 skipped**（環境条件つき既知 skip・review fix-forward 反映後の bh2jsw80d 緑実行 exit=0）。
- **flaky 観測（透明性）**: `tests/test_update_gate_lock.py::test_lock_held_blocks_noop_approve` が full-suite 負荷下の1実行で1回 fail→別 full 実行(bh2jsw80d)で pass・単独3/3 pass・ファイル17/17 pass。full-review R10 test#8 で既知のハードコード lock 待ちタイミング脆弱性。本 diff は update-gate.sh/lock/snapshot 不接触（`git diff --name-only 26de7f6..HEAD` で確認）＝回帰ではない。qa/security に申し送り（env 化での安定化は別バックログ）。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| Task 1 | `SIZE_ALLOWED_PHASES["S"]` に docs 追加（Fix 3a） | `scripts/check_status.py:211-215` | 完了 | RED-first 静的検査テスト＋ship→docs 遷移ピン |
| Task 2 | `check_phase_transition` 空リスト穴封鎖（Fix 2） | `scripts/check_status.py:1346-1358` | 完了 | in-process import RED・実 enum では dormant（defense in depth） |
| Task 3 | check-gate.sh size-aware 化（Fix 1・本丸） | `hooks/check-gate.sh:250-278` | 完了 | 7→8 ケース（(a)-(i)）・pure-bash・fail-closed |
| Task 4 | drift-guard | `tests/test_check_gate_size_aware.py::TestSizeGateDriftGuard` | 完了 | assert 3 点・歯の証明済み |
| Task 5 | state-machine.md 表同期＋full suite | `.claude/rules/state-machine.md:45` | 完了 | 姉妹表 architecture-overview.md も同期（下記 F4） |

## Findings（severity・confidence 付き）

### Major（すべて処置済み）

1. **[gate 迂回] gate-bypass: task_size spoof で plan 儀式 bypass**（confidence 9）
   - 経路(a) 本文 spoof（`frontmatter_value` whole-file grep が本文 `task_size: S` を拾う）→ **fix-forward `b9c95f7`**（check-gate の task_size 読取を `read_frontmatter` 経由の frontmatter スコープに是正・回帰ピン(i) 追加）。
   - 経路(b) frontmatter 直接 raw-Edit × `post-status-audit.sh:210` migration-grace（empty-baseline で tamper skip）→ **SF-010 起票・次反復（iter66）分離**（ユーザー承認済み）。**security gate で residual ack 予定**。発火前提: empty-baseline 窓＋意図的 raw-Edit＝自傷経路。旧実装(26de7f6)では両経路 deny＝この diff の回帰面（親で独立再現・CONFIRMED）。
2. **[テスト強度] else 分岐の `plan=n/a` 許容が無テスト**（confidence 8）
   - bugfix/hotfix は M/L でも plan=n/a になるため、n/a 許容削除の変異が全テスト生存（false-deny 回帰を検知不能）→ **fix-forward `89264c7`**（ケース(h) bugfix・M・plan=n/a→allow 追加・変異で歯を確認）。
3. **[仕様準拠] 姉妹表 architecture-overview.md:225 の新規 guidance drift**（confidence 8）
   - state-machine.md のみ `->docs` 同期し、以前完全一致だった architecture-overview.md が新規 drift 化（currency テストが size-flow 行を未 pin）→ **fix-forward `ef1cd9b`**（姉妹表同期＋check-gate 既存コメント2箇所の size-aware 表現化）。

### Minor（accepted / 追跡）

- **[bash 堅牢性] 正規化器の非対称**（confidence 8）: `frontmatter_value`（double-quote のみ除去）vs python `extract_scalar_value`（single/double＋strip）。差は全方向 over-gate（安全）側・正規 writer は bare 値のみ書くため実害経路なし。security 申し送り。
- **[gate 迂回] gate_approvals 重複キーの先勝ち(bash)/後勝ち(python) 乖離**（confidence 7）: 単体では緩まないが監査と gate の値乖離を作れる。SF-010 の parser drift 統一検討に同梱（次反復）。
- **[仕様準拠] check-gate.sh の既存コメント2箇所**（confidence 6）: size-aware 化後に「plan gate」表現がやや不正確 → `ef1cd9b` で「size-aware implement gate」表現に更新済み。

### PASS（緩み・退行の不在を実証した項目）

- bash: `set -euo pipefail` 安全性・値形バリエーションで緩む方向なし・先行5経路非改変・printf format-string/JSON 破壊なし・M/L/未設定の byte-exact 保存。
- gate 迂回: リスク3 受容根拠(i)(ii)(iii) 事実正・frontmatter 破損時 fail-closed 維持・strict type の brainstorm=n/a は authorized 経路で閉鎖・Fix 2 terminal deny は実 enum で誤 deny 到達不能（dormant 防御）。
- テスト強度: check-gate 変異 7/7 kill・check_status Fix2/3a 変異 3/3 kill・in-process テスト相互汚染なし・RED-first 5本実証。

## Evidence Checklist

- [x] diff を Read/Grep で実読（4 finder＋親の独立再現）
- [x] plan/spec の受入条件と突合（対照表）
- [x] 未カバーのエッジケースを列挙（→ ケース(h)(i) 追加で解消・SF-010 追跡）
- [x] 全 finding に severity と confidence 付与

## 判定

**PASS（条件: SF-010 を security gate で residual ack）**。

- 1次で検出した Major 3件は (a)`b9c95f7`／テスト強度`89264c7`／仕様準拠`ef1cd9b` で fix-forward 済み。
- 残る Major の一部（経路(b)＝SF-010）はユーザー承認のもと次反復分離＋security residual ack。empty-baseline 窓＋意図的 raw-Edit の自傷経路で、経路(a) 封鎖により accessible surface は閉じている。
- Minor は accepted（安全方向）／SF-010 同梱（parser drift）／修正済み。

```claims
tests_pass: true
no_stubs: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "結論レベルの割れなし（1次・2次とも approve_with_notes に収束）"
    - "2次が SF-010 未収載の split を補足: F-1 extract_scalar_value 引用形優先で task_size に audit-evading な python/bash 割れ（→ SF-010 スコープに追記済み）"
    - "2次が F-2 gate_value 本文フォールバック（gate_approvals 節欠落時）を SF-010 修正対象に含めよと指摘（→ 追記済み）"
```

## 盲検2次（self-attested）

- **ディスパッチ**: reviewer（model=fable）・1次 verdict/コメント非開示（fresh context）・diff と spec/plan のみ・6拘束（read-only・fixture は mktemp）。
- **結果**: **approve_with_notes**（1次と収束）。6観点すべて PASS。緩和変異 4/4 検知・fail-closed 網羅・920 tests green を独立実測。
- **notes（承認条件・非ブロック）**:
  1. SF-010 の residual ack を security gate で必ず実施（task_size が gate 判定に昇格した以上、empty-baseline 窓は本 diff の残存リスク面）。
  2. 次反復 SF-010 スコープに F-1（extract_scalar_value 引用形優先）・F-2（gate_value 本文フォールバック）を含める → **本レポート提出時に SF-010 へ追記済み**。
- **独立再現**: 1次 fix-forward（b9c95f7 等）の有効性を独立に実測確認。結論レベルの割れは検出せず。

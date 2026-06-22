# iteration 39 review — check-gate.sh テスト分離バグ修正（framework・M・test-only）

> plan: `docs/plans/2026-06-22-iter39-test-isolation-plan.md`
> 対象 diff: `git diff HEAD`（`tests/test_failure_policy.py` のみが substantive・他は plan/STATUS）

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 状態 |
|---|------------|------------|------|
| 1 | `check-gate.sh` を `_scenarios()` から外し理由コメントを残す | `tests/test_failure_policy.py` | 完了 |
| 2 | 専用メソッド `test_python3_absent_check_gate_reads_scratch_status`（temp-root copy・lib copy・両極 approved→allow／pending→deny） | `tests/test_failure_policy.py` | 完了 |

未着手タスク: なし。本番 hook（`check-gate.sh`）は不変（test-only スコープ厳守）。

## Severity 分類

### Critical / Major
該当なし。

### Minor（盲検2次 reviewer-testing 由来・いずれも非アクション）
- (a) `import shutil` がメソッド内＝冗長との指摘（confidence 7）→ **誤指摘**。`shutil` はモジュール先頭に import されておらず、`setUp` の import は関数ローカル。よってメソッド内 import は**必須**（除去すると NameError）。既存の control-plane 専用メソッド（`test_failure_policy.py:201`）も同型にメソッド内 import＝**file の確立パターン**。現状維持。
- (b) `row` 変数名（confidence 8）→ ループの `row = self.table.get(hook)` と同じ命名で一貫。policy 表の `py_absent='通常判定'` 宣言を固定する意図的アサートで有用。現状維持。

## 検証（独立確認込み）

- **分離の実証（核心・盲検2次 conf9 一致）**: 新メソッドは temp-root COPY を発火し `ROOT=scratch`。**両極**で scratch の plan に追従＝plan:approved→allow／plan:pending→deny を固定。現 live STATUS は plan:approved のため、もし実 STATUS を読んでいれば pending 極で allow になり **FAIL**＝この負極が load-bearing な回帰ガード（バグを確実に捕捉）。
- **lib セット完全性（2次 conf9）**: check-gate.sh の source/require は safety.sh・extract-input.sh・emit.sh・frontmatter.sh の 4 本のみ（実読確認）。全て copy 済＝safety-fallback-deny に落ちず実 allow/deny ロジックに到達。
- **copy vs symlink**: copy2（独立 inode）＝iter36 Bug A（os.chmod の symlink 追従）回避。cleanup は setUp の `addCleanup(rmtree, ignore_errors)` が `self.tmp` 配下を網羅。leak なし。
- full suite: **1038 passed / 1 skipped**（record-test-result **green**・fingerprint-bound）。`check_framework_contract.py` PASS（版 1.14.0）。
- moat: framework につき解錠（emit.sh 644 復元確認）。`git status --porcelain` は意図変更のみ（mode-flip なし）。

## Evidence Checklist

- [x] diff を実読（test_failure_policy.py の loop 除外＋専用メソッド）
- [x] plan の受入条件と突合（両極アサート・lib セット・copy 方式）
- [x] エッジケース（実 STATUS 非依存・safety-fallback 回避・cleanup）
- [x] 全 finding に severity・confidence 付与

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff＋context のみ）`reviewer-testing` を独立ディスパッチ。check-gate.sh の source 行・live STATUS 状態・両極アサートを独立検証。

```claims
verdict: approve_with_notes
tests_pass: true
no_stubs: true
second_opinion:
  agent: reviewer-testing
  verdict: approve_with_notes
  confidence: 9
  note: 両極（pending→deny）が live-STATUS 非依存の load-bearing 回帰ガードと独立確認。lib 4本セット完全・copy 方式正当・cleanup 網羅。Minor 2件（import shutil 配置＝実は必須の誤指摘／row 命名）は非ブロッカー。
```

1次 verdict=approve_with_notes（Minor 2件は非アクションと判断）／2次=approve_with_notes＝**一致**。divergence なし。

## 判定

**PASS（review gate approvable・🟢 見込み）**。Critical/Major ゼロ。Minor 2件（いずれも非アクション・現状維持）。1次・2次とも approve_with_notes 一致。tests green（fingerprint-bound）・contract PASS。

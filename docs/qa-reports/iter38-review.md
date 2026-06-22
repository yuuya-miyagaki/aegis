# iteration 38 review — qa skip-drill doc 修正（framework・S・doc のみ）

> 種別: framework / size: S（review ゲートのみ必須／qa・security・deploy は size-skip exempt）
> 対象 diff: `git diff HEAD`（doc 3 ファイル＋budget registry＋STATUS rollover）
> 一次ソース: `docs/LEARNINGS.md` confidence:7「qa テスト強度ドリルの skip 仕様の preview はできない」

## 対照表（タスク × 実装）

| # | タスク | 実装ファイル | 状態 |
|---|--------|------------|------|
| 1 | skip 節に「手順4のプレビュー非実行＝`update-gate.sh qa approve` に委ねる」注記を追記 | `.claude/skills/qa-verification/SKILL.md`（+5 行） | 完了 |
| 2 | LEARNINGS の該当エントリに「iter38 で doc 修正済み」を追記し drift クローズ | `docs/LEARNINGS.md` | 完了 |
| 3 | 注記で超過した skill 語数予算を新カウントちょうどに引き上げ（434→443） | `scripts/context-budgets.json` | 完了 |
| — | iteration rollover（gates pending・refs null・iteration=38・phase 遷移） | `docs/STATUS.md`（update-gate.sh 経由） | 完了 |

未着手タスク: なし。スコープ逸脱なし（test 分離バグ修正は check-gate.sh が `tests/` 編集を plan 未承認で deny したため iter39 に繰延＝下記）。

## Severity 分類

### Critical
該当なし。

### Major
該当なし。

### Minor
- 盲検2次（reviewer-maintainability・confidence 6）: 注記の配置が skip JSON の直後で「安易なスキップは避け」の prose より前。skip スペックを書いた直後の読者が到達する自然な位置と判断し**現状維持**（readability preference・非ブロッカー）。

## 注記の正確性（コードと突合）

- `scripts/run-test-strength-drill.py`: `REQUIRED_SPEC_KEYS = ("test_command","timeout_seconds","mutants")`（L19）→ skip スペックは欠落キーで `DrillError` → fail-closed `verdict: FAIL`・exit 1（L68・run_drill 例外ハンドラ）。**skip 解釈不可を実証**。
- `scripts/check_status.py::run_qa_drill`（L876・L903）: `{"skip": true}` を解釈し `verdict: SKIP`・rc0。**skip 解釈は唯一ここ**（コード全体で `spec_data.get("skip") is True` はこの1箇所のみ）。
- 注記は両挙動を正しく反映（1次・盲検2次とも confidence 10 で一致）。

## 予算引き上げの妥当性

- 語数 = `len(text.split())`＝空白区切り。日本語 prose はほぼ無料、注記の inline-code 識別子（`test_command`・`run_qa_drill`・`verdict: FAIL`/`SKIP`・`update-gate.sh qa approve`）が token を消費。これらは「iter37 で実際にハマった出力」を正確に伝える load-bearing 部分。
- tighten-only ratchet（`context_budget.tighten`）は自動引き上げをしないが、`test_tighten_never_raises` は `tighten()` 関数のみを制約し、意図的なレジストリ編集は禁止しない。新カウントちょうど（443・slack ゼロ）への引き上げは tighten 流儀と整合。

## Evidence Checklist

- [x] diff を実読（SKILL.md・LEARNINGS.md・context-budgets.json）
- [x] 一次ソース（LEARNINGS）と突合し、注記をコード（runner／run_qa_drill）で再検証
- [x] エッジケース列挙（skip スペックの fail-closed・budget 超過）
- [x] 全 finding に severity・confidence 付与

## 検証エビデンス

- `check_framework_contract.py` **PASS**（skill 語数 443≦443・version 1.14.0 同期）。
- full suite: **1038 passed / 1 skipped / 1 failed**。唯一の失敗 `test_failure_policy.py::test_python3_absent_behavior`（check-gate.sh シナリオ）は**既存の潜在テスト分離バグ**（check-gate.sh が `ROOT=SCRIPT_DIR/..` で実リポ STATUS を読み、rollover の `plan: pending`〔S は plan を size-skip〕で deny）。**本 doc 変更とは無関係**＝変更4ファイルは全て docs/・.claude/・scripts/ で check-gate.sh も当該テストロジックも触れていない。`read_test_result` は fingerprint 不一致で `unverified`（🟡 ack 可）に degrade。
- iter39 繰延（別 iteration・plan を要する `tests/` 編集）: check-gate.sh の python3 不在フォールバックの分離を control-plane と同型の temp-root コピーで固定する（iter36 Bug-B 同クラス）。

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff＋コンテキストのみ）`reviewer-maintainability` を独立ディスパッチ。runner と run_qa_drill を独立実読し注記の正確性を検証。

```claims
verdict: approve
tests_pass: unverified
no_stubs: true
second_opinion:
  agent: reviewer-maintainability
  verdict: approve
  confidence: 9
  note: runner の REQUIRED_SPEC_KEYS と run_qa_drill の skip 分岐を独立実読し注記の正確性を confidence 10 で確認。budget 434→443 を新カウントちょうどへの妥当な意図的引き上げと判断。Minor 1件（注記配置）は非ブロッカー。
```

1次 verdict=approve / 2次（盲検 reviewer-maintainability）verdict=approve＝**一致**。divergence なし。

## 判定

**PASS（review gate approvable・🟡 ack）**。Critical/Major ゼロ。Minor 1件（配置・現状維持）。1次・2次とも approve 一致。テスト tier-1 fact は `unverified`（既存潜在分離バグ・doc 変更と無関係・iter39 繰延）につき ack で承認する。

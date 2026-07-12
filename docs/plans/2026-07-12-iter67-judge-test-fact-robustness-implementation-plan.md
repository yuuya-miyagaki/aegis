# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: judge tier-1 test-fact（`read_test_result`）を
  trust-scan 化し、(a) record green 後の生 pytest ノイズ1回で 🟡 降格する罠
  （iter64/65/66 で3回顕在化）の根切り、(b) decidable red の後に no-run コマンド
  を走らせて red→🟡 に洗浄できる経路の封鎖（厳格化）。C-2/K-1/fp backstop の
  防御は一切緩めない。

## 入力

- 参照要件: なし（framework 内部改修・retro 合意 改善#1）
- 参照設計: `docs/specs/2026-07-12-iter67-judge-test-fact-robustness-design.md`

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: n/a（フレームワーク内部・配布物は setup.sh 経由）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: n/a（web デプロイなし）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

Project Overrides 未定義・過去反復の実績に合わせ main 直コミット
（per-task commit・push はユーザー指示待ち）。

## ファイル構造（変更マップ）

- 変更: `scripts/build-judge-card.py:195-240`（`read_test_result`）—
  走査ループに undecidable-ok 透明化を1分岐挿入＋docstring を trust-scan
  意味論に同期
- テスト: `tests/test_test_runner_realness.py` — 新クラス
  `TestReadTestResultTrustScan`（系列テスト・既存 `_scratch_repo` ハーネス再利用）
- 変更: `docs/architecture-overview.md:215` — 「judge が現コードと一致する最新の
  テスト実行を照合」→「最新の**検証可能な**（decidable）テスト実行を照合
  （marker 未検証の observed-ok エントリは透明）」の1文同期

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | 系列テスト（RED 3+/pin 複数） | 既存 `_scratch_repo`/`_fp` ハーネス |
| Task 2 | trust-scan 実装＋docstring | Task 1 のテスト（green 化対象） |
| Task 3 | guidance 1文同期 | Task 2 の確定意味論 |

循環依存なし。

## タスク分解

### タスク 1: 系列テスト新設（TDD RED）

**blockedBy:** なし | **モデル:** `opus`（dispatch・書く工程）
**ファイル:** テスト `tests/test_test_runner_realness.py`
**意図:** trust-scan の全判定マトリクスを系列（複数エントリ）テストで固定する。
既存クラス `TestReadTestResultSchemaMigration` の `_scratch_repo`/`_fp` を再利用
する新クラス `TestReadTestResultTrustScan` を追加（setUpClass 同型・
`_write_entries(root, entries)` ヘルパー＝リスト順＝古→新で1行ずつ append）。

**テストケース（エントリはファイル内で古→新の順・fp は実 fingerprint、
STALE は `"a"*64`）:**

| # | 系列（古→新） | 期待 | 現行 | 名前案 |
|---|---|---|---|---|
| 1 | manual ok fp / observed ok mv=False fp（cmd に `--collect-only`） | green | unverified=**RED** | `test_trusted_green_survives_noise_ok_entry` |
| 2 | observed ok mv=True fp / observed ok mv=False fp | green | **RED** | `test_marker_verified_green_survives_noise_ok_entry` |
| 3 | observed fail mv=True fp / observed ok mv=False fp | red | **RED** | `test_decidable_red_cannot_be_laundered_by_noise_ok_entry` |
| 4 | manual ok fp / observed **fail** mv=False fp | unverified | pass=pin | `test_undecidable_fail_stays_terminal_unverified` |
| 5 | manual ok **STALE** / observed ok mv=False fp | unverified | pass=pin | `test_transparency_does_not_resurrect_stale_green` |
| 6 | manual ok fp / observed ok fp（marker_verified キー無し=v1.6.0） | green | **RED** | `test_v160_ok_entry_is_transparent_in_sequence` |
| 7 | manual ok fp / observed fail mv=True fp | red | pass=pin | `test_newest_decidable_red_still_wins` |
| 8 | observed ok mv=False fp ×2（decidable ゼロ） | unverified | pass=pin | `test_noise_only_log_stays_unverified` |
| 9 | manual ok fp を `.1`（rotated）へ / observed ok mv=False fp を current へ | green | **RED** | `test_transparency_spans_rotated_log` |
| 10 | manual ok fp / observed ok mv=False **STALE** | green | **RED** | `test_transparency_precedes_fp_check` |

**TDD:** テスト追加 → `python3 -m pytest tests/test_test_runner_realness.py -q` で
#1/2/3/6/9/10 が FAIL・#4/5/7/8 が PASS を確認 → コミット（RED コミット）
**受入条件:** 上記 FAIL/PASS 分布が実測どおり＋**既存系列ピン
`tests/test_judge_card.py::test_newest_stale_does_not_fall_back_to_older_fresh`
（decidable-stale 終端＝`_ev_line` は marker_verified=True デフォルト）が
無修正のまま存在すること**（本計画のケース10=undecidable-ok stale 透明と
共存する — 遡り禁止は「最新の decidable が stale」の場合に限られる）
**Deliverable:** [x] 10 ケースが存在 [x] RED/pin 分布確認記録

### タスク 2: trust-scan 実装＋docstring 同期

**blockedBy:** Task 1 | **モデル:** `opus`（dispatch・書く工程）
**ファイル:** 対象 `scripts/build-judge-card.py`（`read_test_result` のみ）
**意図:** 走査ループに undecidable-ok 透明化を挿入。確定文言（実装は意味を保てば
体裁調整可・検査順序は変更不可）:

```python
        # trust-scan (iter67): an observed entry whose marker was NOT
        # verified can certify neither green nor red (C-2) — with status
        # "ok" it is pure noise (--collect-only counts, piped/truncated
        # output), so it is TRANSPARENT: skip it and keep scanning for the
        # newest decidable entry. A fail-status undecidable stays terminal
        # (something runner-shaped failed — keep the 🟡 re-record signal).
        # Without this, one noise entry after a trusted green demotes the
        # gate to unverified (iter64/65/66), and one --collect-only after a
        # decidable red launders red into an ack-able 🟡.
        undecidable = (d.get("src") == "observed"
                       and d.get("marker_verified") is not True)
        if undecidable and d.get("status") == "ok":
            continue
        if (d.get("fp") or "") != current:
            return "unverified"
        # C-2: marker_verified gate for observed entries.
        if undecidable:
            return "unverified"
        return "green" if d.get("status") == "ok" else "red"
```

docstring 更新: 「The newest test-runner entry decides」→「The newest
**decidable** test-runner entry decides（decidable = src:"manual" または
marker_verified:true。observed で marker 未検証かつ status:ok は透明＝skip、
status:fail は終端 unverified）」。v1.6.0 スキーマ注記も「ok エントリは系列中
透明・fail エントリは終端 unverified」に同期。

併せて `tests/test_judge_card.py::test_newest_stale_does_not_fall_back_to_older_fresh`
の理由コメントに限定子を1行追記する（「最新エントリが decide する」→「最新の
**decidable** エントリが decide する（undecidable-ok は iter67 trust-scan で
透明）」）— アサーション・fixture は一切変更しない（コメントのみ）。

**TDD:** Task 1 の RED 6件が green 化・pin 4件が green 維持 →
`python3 -m pytest tests/test_test_runner_realness.py tests/test_judge_card.py -q`
→ full suite → コミット
**受入条件:** 対象2ファイルのテスト全 pass（既存系列ピン含む）＋full suite で
新規 fail なし
**Deliverable:** [x] trust-scan 動作 [x] docstring が実装と一致

### タスク 3: guidance 1文同期

**blockedBy:** Task 2 | **モデル:** in-session（1文・dispatch 不要）
**ファイル:** 対象 `docs/architecture-overview.md:215` 付近
**意図:** 「judge が現コードと一致する最新のテスト実行を照合する」を「judge が
現コードと一致する最新の**検証可能な**テスト実行（manual または marker 検証済み
observed。marker 未検証の observed-ok はノイズとして透明）を照合する」に更新。
**TDD:** n/a（ドキュメント1文・budget 影響を `python3 scripts/context_budget.py`
で確認）
**受入条件:** 文言が実装意味論と一致・budget red なし
**Deliverable:** [x] guidance が drift していない

## External Integrations

なし。

## 事前準備

- [x] 対象コード読解済（`read_test_result`・`evidence.sh`・patterns）
- [x] 既存ピンとの衝突確認済（grill-plan 実測）: 単一エントリピン5件
  （test_test_runner_realness.py）は系列外＝不変。**系列ピンは1件既存**＝
  `test_judge_card.py::test_newest_stale_does_not_fall_back_to_older_fresh`
  （decidable-stale 終端）— marker_verified=True デフォルトのため本変更後も
  生存（パッチ適用コピーで実測確認済）
- [x] **判定マトリクス実測済（grill-plan）**: 現行コードで「現行」列 10/10 一致・
  確定文言パッチ適用コピーで「期待」列 10/10 一致
- [x] ベース=main e0b14c5（クリーン）

## トレーサビリティ（要件 → AC → Task → Test）

| 要件（設計テスト戦略 #） | AC | Task | テスト |
|------|----|------|--------------|
| 罠の根切り（設計 1,2,6,9） | green 復帰 | Task 1/2 | ケース 1,2,6,9 |
| red 洗浄封鎖（設計 3） | red 再浮上 | Task 1/2 | ケース 3 |
| 保守ピン（設計 4） | unverified 維持 | Task 1/2 | ケース 4 |
| fp backstop（設計 5） | unverified 維持 | Task 1/2 | ケース 5 |
| 既存意味論保存（設計 7） | red 維持 | Task 1/2 | ケース 7＋既存ピン5件 |
| decidable ゼロ（設計エッジ） | unverified | Task 1/2 | ケース 8 |
| 透明化の検査順序（設計 注） | fp 検査より前 | Task 1/2 | ケース 10 |
| guidance 同期 | 文言一致 | Task 3 | 目視＋docs-sync |

## 自己レビュー

- 仕様カバレッジ: 設計の判定マトリクス全行がケース 1-10 でカバー
- 曖昧さ検出: 「透明化は fp 検査より前」を確定文言＋ケース10で一意化
- 型の整合性: 戻り値集合 "green"/"red"/"unverified" 不変・呼出側変更なし
- 境界整合性: Task 2 は Task 1 のテストを消費・Task 3 は Task 2 の意味論を消費

## リスク

- リスク: exit 0 に洗浄された marker-less 実失敗（`pytest | tail` の SIGPIPE 等）
  を trusted green が透過する
  - 対策: 設計で受容済（現行でもその失敗は red にならず 🟡。green を返すのは
    fp 一致の trusted green 実在時のみ＝fp backstop がケース5/10で機械ピン）
- リスク: 系列テストが実 fingerprint 計算に依存し環境で flaky 化
  - 対策: 既存 `_scratch_repo` ハーネス同型（git init 済み一時 repo・決定論）。
    既知 flaky=test_update_gate_lock は本 diff 不接触＝回帰外
- リスク: docstring と実装の drift
  - 対策: Task 2 の受入条件に「docstring が実装と一致」を含める（review 1次で照合）

## 完了条件

- [ ] 全テスト pass（full suite・record-test-result で締め）
- [ ] レビュー完了（1次＋盲検2次）
- [ ] ケース 1,2,3,6,9,10 の RED→GREEN 遷移が git 履歴で追跡可能

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

# QA — iteration 31 / Batch1（control-plane フック精度 + git baseline）

## 機能対照表（plan 受入条件 × 検証 × 判定）

| # | plan の機能 | 検証方法 | 判定 |
|---|---|---|---|
| 1.1 | 新規 install に baseline commit / 既存リポは no-op / scoped add | `test_setup_baseline.py`(3)＋scaffold smoke 3 profile | PASS |
| 1.2 | judge stub 走査のみ CP 除外・secret は全走査維持 | `test_judge_card.py`(55)＝stub除外/app検出維持/secret-in-script検出 | PASS |
| 1.3 | 証拠スクリプト allowlist（no-chain 維持） | `test_control_plane_allowlist.py` bare allow / chain・redirect deny | PASS |
| 1.4 | bare `git add <dir>`→ask / `-A`/`-f`/chain/apply deny | 同上 TestBareGitAddStaging | PASS |
| 1.5 | read-only パイプ allow / write セグメント deny | 同上 TestReadOnlyPipeline（最終セグメント fail-open 回帰含む） | PASS |
| 1.6 | 書込み先 path のみ deny（mask＋redirect＋allowlist・cmdsub fail-closed） | 同上 TestWriteTargetVsMention＋var_expansion＋REDTEAM | PASS |

実装漏れなし（全機能に検証対象が存在）。

## テストスイート

- full suite **830 passed / 1 skipped**（既知 flake 非発火）。
- moat 回帰: `test_control_plane_allowlist`(40) / `test_control_plane_var_expansion` / `test_patterns_parity` / `test_secrets_*` 緑。
- REDTEAM PoC **18/18 ＋ 5/5**。
- contract 全 profile（minimal/standard/full）/ drift / mirror identity / scaffold smoke（3 profile）全 PASS。
- lint/type/build: 本リポは pytest＋bash の静的契約（contract/drift）が CI 相当。別途 lint/build 工程なし＝N/A。

## テスト強度ドリル（mutation）

**LIVE ドリルは構造制約により SKIP 宣言**（`docs/qa-reports/test-strength.drill`）。理由: Batch1 コードはタスク単位でコミット済み→qa 承認時の working-tree diff（`git diff HEAD`）が空＝『追加(+)行上の mutant』を置けない。soft-reset しても coverage floor（全追加ハンクに mutant 必須）が framework 混在 diff で不成立（iteration30 と同型・LEARNINGS:37）。

**代替＝手動 mutation 実証（4/4 CAUGHT）**: 設計した 4 mutant を実ファイルに一時適用→対象テスト実走→赤化を確認→revert（git clean 確認済）:

| mutant | 注入箇所 | 対象テスト | 結果 |
|---|---|---|---|
| `tr ';;'`→`'  '`（改行正規化破壊） | `hooks/check-control-plane.sh:282` | `test_newline_separated_writer_after_echo_denied` | **CAUGHT(赤)** |
| allowlist に `cp` 注入（write-target 緩和破壊） | `hooks/check-control-plane.sh:188` | `test_quoted_cp_destination_of_write_util_denied` | **CAUGHT(赤)** |
| `STUB_NONCODE` から `scripts/` 除去 | `scripts/build-judge-card.py:54` | `test_control_plane_changes_are_not_scanned_for_stubs` | **CAUGHT(赤)** |
| setup no-op `HEAD`→`HEADXX` | `bin/setup.sh:375` | `test_existing_repo_with_history_is_noop` | **CAUGHT(赤)** |

加えて全 6 タスクが TDD（実装前 RED 実証）で実装され、3 ラウンド盲検 break-attempt レビューが Batch1 由来 Critical 2 件を検出→修正＝固定 mutation 集合より網羅的に「テストの実効性」を検証済み。

## 判定

**PASS** — 全機能 PASS・実装漏れなし・テストの実効性を 4 mutant 実証（全 CAUGHT）＋ TDD RED-GREEN ＋盲検レビューで確認。ブロッカーなし。残存リスク SF-001（pre-existing・繰延）は `docs/security-followups.md`。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve
  divergence_points: ["B1 LIVE ドリルは committed-code/coverage-floor 構造制約で SKIP 宣言。独立検証は手動 4-mutant 実証(4/4 CAUGHT)＋3ラウンド盲検 break-attempt レビューで代替"]
```

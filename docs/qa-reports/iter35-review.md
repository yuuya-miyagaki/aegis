# iteration 35 review gate — レビュー証拠

> feature/framework イテレーション（案A immutable moat・layer-2 OS lock）。
> 計画: `docs/plans/2026-06-21-aegis-iteration35-immutable-moat.md`（grill-plan 反映版）。
> 設計: `docs/specs/2026-06-21-immutable-moat-design.md`（rev.2）。
> 対象 diff: `git diff 585573a..HEAD`（実装コミット 1e46e4d / a2d3cad / 5565418 / 8c86333 / 3e50314 / 649689b / d2c4fc8）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 |
|---|------------|------------|------|
| Task0 | cp-lock.sh（aegis_cp_paths 単一所有 / lock / unlock） | hooks/lib/cp-lock.sh / tests/test_cp_lock_lib.py | done |
| Task1 | session-start で task_type 連動 lock/unlock（fail-warn） | hooks/session-start.sh / tests/test_session_start_cp_lock.py | done |
| Task2 | layer-1 の chmod-unlock/rename deny 回帰固定（production 無改修） | tests/test_control_plane_chmod_unlock.py | done |
| Task3 | lock 下の形非依存阻止 実証（defense-in-depth 証拠） | tests/test_cp_lock_sf_catalog.py | done |
| Task4 | contract 登録 + 版 1.13.0 + README/architecture + SF disposition | scripts/check_framework_contract.py / templates/STATUS.template.md / docs/STATUS.md / README.md / docs/architecture-overview.md / docs/security-followups.md / tests/test_cp_lock_contract.py | done |
| grill/review fix | 空 root ガード + drift guard + rc=1 warn coverage + CP_DIRS↔cp-lock 相互リンク | hooks/lib/cp-lock.sh / hooks/check-control-plane.sh / tests/test_cp_lock_lib.py / tests/test_session_start_cp_lock.py | done |

未着手タスク: なし。lifecycle re-lock / chflags uchg / NFS skip は計画どおり繰延・不採用（scope 外・diff 混入なし）。

## 正直な価値の射程（grill-plan で確定・本実装の前提）

layer-2 は**事故ケース限定の独立 syscall 保険**（脆い layer-1 の未発見バイパスに対する多層化）。
**敵対 SF-004 は閉じない**（owner は a-w 下でも `os.chmod` 解錠でき、敵対者は同じ interpreter で回避可）。
よって SF-001〜005 は CLOSED にせず disposition 追記のみ。普通の事故は既に layer-1 が Bash も Edit/Write も deny 済。

## Findings（severity / confidence）

### 🔴 Critical
該当なし。

### 🟡 Should fix
該当なし（grill-code 時点でもゼロ）。

### 🟢 / 解消済み（Review Army → fix-forward）
- reviewer-maintainability（conf 9・**critical 指摘**）: CP path-set の drift risk（`aegis_cp_paths` と `check-control-plane.sh` の `CP_DIRS` が機械的に結ばれず silent drift しうる）→ **解消**: `check-control-plane.sh:65` に相互リンク DRIFT NOTE 追加＋`test_cp_lock_paths_cover_expected_roots` で canonical roots を pin（d2c4fc8）。
- reviewer-testing（conf 8・verdict NO）: rc=1 部分失敗 / fail-soft warn 経路が未テスト → **解消**: `test_lock_failure_warns_not_crashes`（lib present で lock rc=1 → session-start は exit0＋warn）追加（d2c4fc8）。※コード自体は `chmod ... || rc=1` で rc=1 を正しく返す＝テスト網羅の穴でありコード欠陥ではない。
- reviewer-performance（conf 8・yes-with-followup）: ローカル SSD 120 ファイル ≈5ms＝許容。**follow-up（別 iteration・非ブロッカー）**: NFS/SMB/FUSE で 200-2000ms/session 増の可能性→ネットワーク FS 検出 skip を将来追加（計画 残課題に記録）。
- grill-code 🟢（解消済）: 空 root ガード（649689b）・scripts/ も lock 対象の assertion（649689b）。

## Evidence checklist
- [x] diff を実読した（self grill-code 全観点 ＋ Review Army 3 specialist が実ファイル走査）
- [x] plan の受入条件と突合（対照表・全タスク done・grill 反映版に忠実）
- [x] 未カバーのエッジケース列挙→潰した（rc=1 warn / drift / 空 root / runtime-state 除外 / settings 除外）
- [x] 全 finding に severity + confidence 付与
- [x] 各タスク TDD RED→GREEN を個別確認（Task0/1: 機能欠如で RED 実証 / Task2/3: 既存挙動 pin で初回 GREEN＝設計前提の実証）

## 多層検証（machine facts）
- full suite: **1025 passed / 1 skipped**（pytest tests/・205s）
- contract: `check_framework_contract.py` **PASS**（aegis contract is aligned）
- 版 1.13.0 同期: check_framework_contract.py / templates/STATUS.template.md / docs/STATUS.md（3 箇所一致）
- arch-overview currency: `test_arch_overview_currency.py` **PASS**（lib/ 本数 11 == on-disk）
- layer-2 実挙動: lock 下で echo>/cp/rm/`python3 -c open(w)`(SF-004)/quote-split が全て EACCES（CP INTACT）を実走実証（test_cp_lock_lib / test_cp_lock_sf_catalog）
- fail-soft: cp-lock 欠損・lock rc=1 とも session-start は exit0＋warn（layer-1 維持）を実証
- layer-1 回帰: control-plane 198 tests PASS（CP_DIRS コメント追加は inert）

## 判定: **PASS**（Critical/Should-fix ゼロ・全タスク done・Review Army 全指摘 fix-forward 済・多層緑）

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["なし（3 specialist の指摘は全て fix-forward で解消・残は NFS perf follow-up＝非ブロッカー）"]
  agents:
    reviewer_performance: complete — yes-with-followup（ローカル ≈5ms 許容 / NFS follow-up を記録）
    reviewer_testing: complete — rc=1 gap 指摘→fix-forward（test_lock_failure_warns_not_crashes 追加で解消）
    reviewer_maintainability: complete — approve-with-notes・drift risk 指摘→fix-forward（相互リンク＋drift guard test で解消）
  note: 初回 testing/maintainability は infra stall で部分応答→再起動で完走。全指摘を本 iteration 内で潰した。
```

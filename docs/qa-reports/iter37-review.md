# iteration 37 review — moat lifecycle re-lock（framework・M）

> design（正典）: `docs/plans/2026-06-22-iter37-moat-relock-design.md`
> plan: `docs/plans/2026-06-22-iter37-moat-relock-plan.md`
> 対象 diff: `git diff d33140e..HEAD`（実装＋テスト＋version＋hardening）

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 状態 |
|---|------------|------------|------|
| T1 | `aegis_cp_apply` 共有関数（framework→unlock/他→lock・sentinel プローブ・default-lock・空root rc1） | `hooks/lib/cp-lock.sh`・`tests/test_cp_lock_lib.py`(+5) | 完了 |
| T2 | session-start のインライン判定を `aegis_cp_apply` に置換（挙動保存） | `hooks/session-start.sh`・`tests/test_session_start_injection.py`(+2) | 完了 |
| T3 | post-status-audit 起動テストの分離ハードニング（symlink→copy＋回帰ガード） | `tests/test_phase_skill_injection.py` | 完了（triage で唯一の破壊ケースと確認） |
| T4 | post-status-audit から再施錠を発火（source＋STATUS存在後・snapshot前・非致命・emit非干渉） | `hooks/post-status-audit.sh`・`tests/test_cp_relock_integration.py`(新規) | 完了 |
| T5 | framework_version 1.13.0→1.14.0（owner＋template＋STATUS 同期） | `scripts/check_framework_contract.py`・`templates/STATUS.template.md`・`docs/STATUS.md` | 完了 |
| — | full-suite 発覚の期待値同期（版ピン・cp_apply スタブ） | `tests/test_cp_lock_contract.py`・`tests/test_session_start_cp_lock.py` | 完了 |
| — | Review Army note 反映（sentinel 不変条件コメント・absent-lib テスト） | `hooks/lib/cp-lock.sh`・`tests/test_cp_relock_integration.py` | 完了 |

未着手タスク: なし。スコープ逸脱なし（(b) クラッシュ窓・PreToolUse 毎ツール・settings.json lock は YAGNI どおり未着手）。

## Severity 分類

### Critical
該当なし。

### Major
該当なし。

### Minor
- grill-code 🟢×3（accept・by-design/最適化）: cp-lock.sh の partial-lock は次回 apply で収束（hooks が最初に処理されるため）／post-status-audit の task_type 二重パースは phase 遷移時のみで軽微／冪等 no-op の chmod skip は最適化で状態検証で十分。
- Review Army note×2（**closed**・confidence 7）: maintainability=sentinel が aegis_cp_paths メンバーである不変条件をコメント明記（commit 24ef323）／testing=post-status-audit が cp-lock.sh 不在でもクラッシュしない統合テスト追加（commit 24ef323）。

## Evidence Checklist

- [x] diff を実読（hooks 3本＋cp-lock.sh＋テスト）
- [x] design/plan の受入条件と突合（①〜④全タスク・version・分離ハードニング）
- [x] エッジケース列挙（partial-lock／cp-lock 不在／空 task_type／空 root／root・windows skip）
- [x] 全 finding に severity・confidence 付与

## 検証エビデンス

- full suite: **1038 passed / 1 skipped**（absent-lib テスト追加後）。record-test-result green（fingerprint-bound）。
- 実 `scripts/check_status.py` mode **644 維持**（pre/post 計測）。
- **git backstop（grill-plan #2）**: full suite 後 `git status --porcelain` **クリーン**＝tracked file の mode flip ゼロ（exec ビット検出で repo 破壊を catch・破壊なしを実証）。
- `check_framework_contract.py` PASS（version 1.14.0 同期）・`status_doctor.py` PASS。
- TDD: T1/T4 は RED→GREEN 実証、T3 回帰ガードは symlink で RED 実証、T2 は baseline-GREEN→refactor→GREEN（挙動保存）。
- レビュー: grill-code（🔴0🟡0🟢3）＋Review Army 3レンズ（performance approve／testing・maintainability approve_with_notes＝note 2件 closed）＋盲検 holistic reviewer approve（conf9・全 post-status-audit 起動テストを列挙し分離完全性を独立確認）。

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff/design/plan のみ）`reviewer` を独立ディスパッチ。

```claims
verdict: approve
tests_pass: true
no_stubs: true
second_opinion:
  agent: reviewer
  verdict: approve
  confidence: 9
  note: aegis_cp_apply 論理・post-status-audit 非干渉・session-start 挙動保存・分離完全性・moat 無退行を独立検証。全 post-status-audit 起動 10 テストを列挙し test_phase_skill_injection のみ該当（修正済）と確認。
```

1次（grill-code🔴0🟡0＋Review Army note closed）verdict=approve / 2次（盲検 reviewer）verdict=approve＝一致。divergence なし。

## 判定

**PASS（review gate approvable・🟢）**。Critical/Major ゼロ。Minor（grill-code 🟢×3 accept・Review Army note×2 closed）。1次・2次とも approve 一致。

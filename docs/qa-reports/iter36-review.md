# iteration 36 review — テスト分離バグ修正（bugfix・S・framework）

> plan: `docs/plans/2026-06-22-iter36-cp-lock-symlink-fix.md`
> 対象 diff: `git diff b9ff522..HEAD`（Bug A・committed）＋ working tree（Bug B・回帰ガード）
> review は実 diff を Read で実読し、plan の受入条件と突合した。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| A | Bug A: `_scaffold` の symlink→copy（mode-flip 根絶） | `tests/test_phase_skills_lib.py`・`tests/test_session_start_injection.py` | 完了 | 両 session-start scaffold とも `shutil.copy2` 化 |
| A' | Bug A 回帰ガード（scaffold が非 symlink） | `tests/test_phase_skills_lib.py:111`・`tests/test_session_start_injection.py`（新規・対称化） | 完了 | 2 scaffold 両方に対称ガード（grill-code 🟡#1 で対称化） |
| B | Bug B: deploy-gate test の実 STATUS 依存を排除 | `tests/test_hook_output_schema.py:374` | 完了 | `AEGIS_ROOT_OVERRIDE` で scratch 固定＋vacuous `if out:` 撤去で非 vacuous 化 |

未着手タスク: なし。スコープ逸脱（framework 本体コードの改変）: なし（cp-lock は無罪につき不変）。

## Severity 分類

### Critical
該当なし。full suite 1027 passed / 1 skipped・実 `scripts/check_status.py` mode 644 維持・`check_framework_contract` PASS。

### Major
該当なし。

### Minor
- `tests/test_hook_output_schema.py:1429,1508` — 同クラスの latent symlink（`scripts/` 丸ごと symlink）。**現状は安全**: 当該クラスは `session-start.sh` を起動せず（`check-deploy-ready` 直叩き）cp_lock が発火しない＋`rmtree(ignore_errors=True)` で resetperms 経路自体が抑止される。confidence 6。**iter36 承認スコープ（A+B）外＝follow-up 記録**（LEARNINGS）。本 diff の動作には影響なし。

## Evidence Checklist

- [x] diff を Read/Grep で実読（chat summary ではなく実ファイル）
- [x] plan/spec の受入条件と突合（symlink→copy・回帰ガード・AEGIS_ROOT_OVERRIDE pin）
- [x] 未カバーのエッジケースを列挙（latent symlink Finding 4／全 test-suite の `symlink_to` を grep 走査し、leak 三条件＝symlink＋scratch lock＋unlockless cleanup を満たすのは session-start scaffold のみと確認）
- [x] 全 finding に severity と confidence 付与

## 根本原因と修正の妥当性

- 機序: symlink + session-start の cp_lock（`chmod a-w`）+ `TemporaryDirectory` cleanup の `resetperms` onerror が `os.chmod`（symlink 追従）→ 実ファイルを 0o700 化。
- 修正: scaffold を copy 化＝cleanup の chmod がコピーに当たり実ファイル不変。cp-lock の lock 動作は正しいので不変（直接プローブで cp-lock 無罪を確証済み）。
- 第3の symlink 候補 `test_phase_skill_injection.py:61` は `post-status-audit.sh` を走らせる（session-start でない＝cp_lock 不発火）ため leak しない。full suite 後 mode 644 の実測と整合＝残 leak 0。

## 検証エビデンス

- `python3 -m pytest tests/ -q` → 1027 passed, 1 skipped（mode pre/post とも `-rw-r--r--`＝644）
- `python3 scripts/check_framework_contract.py` → PASS
- Bug B 単体: GREEN（`AEGIS_ROOT_OVERRIDE` あり deny）／RED 実証（override 無し時 full suite で `ask != deny`）
- 回帰ガード RED 実証: symlink 化した scratch で `is_symlink()==True` → `assertFalse` 失敗を確認

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff と plan のみ）`reviewer-testing` を独立ディスパッチ。

```claims
verdict: approve_with_notes
tests: green
scope: A+B test-isolation only; framework code unchanged
second_opinion:
  agent: reviewer-testing
  verdict: approve_with_notes
  note: Finding4 latent scripts symlink at test_hook_output_schema 1429/1508 — same class, currently safe (no cp_lock), follow-up only
```

1次（本レポート）verdict=approve_with_notes / 2次（reviewer-testing 盲検）verdict=approve_with_notes＝一致。
2次の confidence: bugA_fix 9・regression_guards 9・bugB_fix 9・finding4_latent 6。
divergence は実質なし（2次が指摘した Finding 4 は 1次 Minor と同クラス・同結論＝現状安全の follow-up）。

## 判定

**PASS（review gate approvable・🟢）**。Critical/Major ゼロ。Minor 1 件は本 diff 外の latent（現状安全）で follow-up 記録。1次・2次とも approve 系で一致。

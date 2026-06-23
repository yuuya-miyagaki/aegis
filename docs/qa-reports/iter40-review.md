# iteration 40 review — moat 自動解錠バグ修正（framework・S・cp-lock.sh）

> 対象 diff: `git diff HEAD -- hooks/lib/cp-lock.sh`（本体）＋ docs/LEARNINGS.md・docs/STATUS.md（簿記）
> 一次ソース: iter39 発見の LEARNINGS（moat 自動解錠不発）＝iter40 で根本特定＋修正

## 対照表（タスク × 実装）

| # | タスク | 実装ファイル | 状態 |
|---|--------|------------|------|
| 1 | `aegis_cp_lock`/`aegis_cp_unlock` の `chmod -R` を `find "$p" -exec chmod {} +` に変更（hook サンドボックスで完全再帰） | `hooks/lib/cp-lock.sh` | 完了 |
| 2 | ヘッダに find 採用理由＋「`chmod -R` へ差し戻し禁止」を明記／`aegis_cp_apply` の stale "chmod -R" 文言を是正 | `hooks/lib/cp-lock.sh` | 完了 |
| 3 | LEARNINGS 更新（conf6→conf9＝根本特定＋修正） | `docs/LEARNINGS.md` | 完了 |

未着手: なし。sentinel は完全再帰下で正確なので変更不要（YAGNI）。本番ロジック挙動は通常環境で不変。

## 根本原因（bash -x で確証）

post-status-audit は STATUS 編集で発火し `aegis_cp_apply <root> framework`→`aegis_cp_unlock`→`chmod -R u+w hooks` まで実行していた（＝「hook が unlock を発火しない」仮説は反証）。真因は **Claude Code の hook サンドボックスで `chmod -R <dir>` がトップ階層 CP ディレクトリのみ変更しネストファイルに再帰しない**（同じ `chmod -R` を Bash ツールで呼ぶと完全再帰＝環境差）。→ dir 解錠/nested 施錠の desync を dir-only sentinel が「解錠済」と誤認し no-op 固定。

## Severity 分類

### Critical / Major
該当なし。

### Minor（盲検2次 由来・対応済/非アクション）
- (a) `aegis_cp_apply` コメントの stale "chmod -R" 文言（conf7）→ **是正済**（"redundant recursive chmod" に修正）。
- (b) `find` の nonexistent-path rc=1（conf8）→ `aegis_cp_paths` が `[ -e ]` でゲート＝発火せず・`2>/dev/null || rc=1`＋非致命契約で吸収＝非アクション。

## 検証（独立確認込み）

- **修正の実証（核心）**: lock（find-based）→ STATUS 編集で hook 発火 → **完全解錠**（dir=700・emit.sh=644・check_status.py=644・.claude/rules=700）を再現確認＝旧 `chmod -R` では dir のみ解錠だった bug を解消。
- **挙動等価（盲検2次 conf9）**: `find "$p" -exec chmod <mode> {} +` ＝ `chmod -R` を nested/単一ファイル(CLAUDE.md)/空 dir/space 入りパス/symlink で実測一致。CP パスは実 dir/file のみ・`aegis_cp_paths` が `[ -e ]` ゲート。
- **セキュリティ無退行（盲検2次 conf9）**: lock は `a-w`（全 write 除去・read/exec 保持）／unlock は `u+w` のみ（group/other 不変）＝moat 保証不変。既存 `test_lock_blocks_all_write_forms`／`test_unlock_restores_writability` が nested ファイルの flip を assert＝再帰バグを直接被覆。
- `bash -n` PASS・`test_cp_lock_lib.py`＋`test_cp_lock_contract.py` 15 passed・full suite 1038 passed/1 skip・record green・contract PASS（版 1.14.0）。
- moat: framework につき解錠維持・`git status` は意図変更のみ（mode-flip なし）。

## Evidence Checklist

- [x] diff を実読（cp-lock.sh 全体）
- [x] brainstorm 設計（find-based・sentinel 据置）と突合
- [x] エッジケース（単一ファイル CP パス・nonexistent・symlink・set -e）を独立確認
- [x] 全 finding に severity・confidence 付与

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff＋context のみ）`security` エージェントを独立ディスパッチ。挙動等価・セキュリティ無退行・既存テスト被覆・エッジケースを実機検証。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
second_opinion:
  agent: security
  verdict: approve
  confidence: 9
  note: find -exec ≡ chmod -R を nested/単一ファイル/空/space/symlink で実測一致。lock=a-w・unlock=u+w のみでセキュリティ無退行。test_lock_blocks_all_write_forms/test_unlock_restores_writability が nested flip を被覆＝再帰バグ直撃。Minor 2件（stale 文言＝是正済／nonexistent rc は [ -e ] ゲートで不発）。secrets/stubs なし。
```

1次 verdict=approve（Minor(a) 是正済・(b) 非アクション）／2次=approve＝**一致**。divergence なし。

## 判定

**PASS（review gate approvable・🟢 見込み）**。Critical/Major ゼロ。Minor 2件（是正済/非アクション）。1次・2次とも approve 一致。tests green・contract PASS。framework S につき review のみ必須・セキュリティ含意は本レビューで網羅（無退行確認）。

# 案A immutable moat — 設計（iteration 35）

> brainstorm/discovery は 2026-06-21 の throwaway PoC スパイクで完了（結果は
> `docs/security-followups.md` 「案A PoC findings」）。本書はその実装設計。

## 目的

事故防止スコープにおいて、control-plane への誤書込み防御を **静的コマンド解析
（`hooks/check-control-plane.sh`）から OS/FS レベルの書込み保護へ置換** する。OS は
コマンド文字列を解釈せず syscall で強制するため、SF-001〜005（quote-split / brace /
interpreter `python3 -c` / extglob …）を**形非依存でまとめて閉じる**。

## スコープと非スコープ

- **置換対象**: 非 framework タスク中の CP 誤書込み防御（`check-control-plane.sh` の役割）。
- **非スコープ（不変）**: `check-destructive`（破壊コマンド警告）/ `check-secrets` /
  `check-gate`（plan 未承認時の編集ブロック・gate/path 保護）/ deploy gate 群 /
  fail-closed fallback。これらは OS lock と直交で維持。
- **脅威モデル**: 事故防止（非 sandbox）。エージェントが `chmod +w` を前置すれば書ける＝
  許容（事故は chmod を前置しない）。adversary 対策は本設計の目的ではない。

## アーキテクチャ（lock state は task_type 連動・session 単位）

中核の洞察: **lock 状態は STATUS の `task_type` から session-start で決まる**。

| task_type | 安定 CP の状態 | 根拠 |
|---|---|---|
| `feature` / `refactor` / `bugfix` / `hotfix`（プロジェクト作業） | **LOCKED**（`chmod -R a-w`） | エージェントは framework コードを触らない＝誤書込み遮断 |
| `framework`（framework 自体の開発） | **UNLOCKED**（`chmod -R u+w`） | framework コードの編集が正当な作業 |

task_type は session 内で原則不変なので、**session-start で 1 回 lock/unlock を決めれば足り、
mid-session の re-lock は不要**（task_type が変わる稀なケースは次 session-start で再計算）。

## コンポーネント（File Structure）

- `hooks/lib/cp-lock.sh`（新規）— `aegis_cp_paths`（lock 対象列挙）/ `aegis_cp_lock` /
  `aegis_cp_unlock`。pure-bash・bash 3.2 安全・冪等。
- `hooks/session-start.sh`（改修）— 末尾で task_type を読み、`cp-lock.sh` を呼んで lock/unlock。
- `scripts/platform_manifest.py` or 新規 manifest — **安定 CP セット**（lock 対象）の単一所有。
- 退役: `hooks/check-control-plane.sh` ＋ `hooks/lib/`（control-plane 専用ヘルパ）＋
  `tests/test_control_plane_*.py` ＋ SF-001〜005 の OPEN 項目（CLOSED 化）。**段階的**:
  まず OS lock を追加し緑を確認 → 旧静的 moat を削除（同一 iteration 内の別 task）。

## 安定 CP セット（lock 対象）と除外

**LOCK（chmod a-w）**: `hooks/*.sh`・`hooks/lib/*.sh`・`scripts/*.py`・`scripts/*.sh`・
`CLAUDE.md`・`.claude/rules/`・`.claude/skills/`・`.claude/commands/`・`templates/`・
`.claude/agents/`。

**除外（常に writable・framework が実行時に書く runtime-state）**: `docs/STATUS.md`・
`.claude/.gate-snapshot`・`.claude/evidence-log.jsonl*`・`.claude/.audit-skip.log`・
`.claude/.task-event-debug.log`・`.claude/settings*.json`・`docs/`（STATUS 以外の成果物）・
`.claude/.aegis-install-version`。

> 旧静的 moat は code と runtime-state を混在判定していた。OS lock は両者を**物理的に分離**
> でき、むしろ綺麗（STATUS.md は update-gate.sh が常時書くので必ず除外）。

## プラットフォーム

- **主機構: `chmod -R a-w`** — cross-platform・root 不要・owner 可逆（事故防止に最適）。
- **macOS 硬化（任意）: `chflags uchg`** — owner の `chmod +w` も封じる。`uname` で macOS 検出時のみ追加。`nouchg` を unlock 経路に。
- **`chattr +i`（Linux）は不採用**（root 必要）。Linux は `chmod` のみ。

## Error handling / fail 方針

- lock 失敗（chmod が一部 path で失敗）→ session-start で **warn**（block しない・session-start は injection 用）。OS lock は「層」であり、`check-gate` 等の fail-closed は別途維持。
- unlock 失敗 → framework タスクで CP 編集が EACCES になる → ユーザーに可視（明確なエラー）。
- re-lock 堅牢性 → default は LOCKED。framework session 終了後に project session が始まれば session-start が再 lock。crash 窓は「framework session 中に crash → CP unlocked のまま」だが、次 session-start で再 lock＝窓は限定的。

## テスト戦略（TDD）

- `tests/test_cp_lock_lib.py` — `aegis_cp_lock` 後に scratch CP へ `echo>`/`cp`/`rm`/
  **`python3 -c open(w)`** が全て EACCES（file INTACT）。`aegis_cp_unlock` 後に書込み可。
- runtime-state 除外: lock 中も `docs/STATUS.md`・`.gate-snapshot`・`evidence-log` が writable。
- session-start 連動: task_type=feature → CP locked / task_type=framework → unlocked。
- macOS: `chflags uchg` 分岐（platform skip guard）。
- 退役後の回帰: 旧 control-plane テスト削除と引き換えに、OS lock テストが同等の「誤書込み遮断」を担保。

## SemVer / 移行

- hook セット変更（`check-control-plane.sh` 退役・`cp-lock` 追加）＝**hook 出力スキーマと
  profile の public contract に触れる可能性** → **MAJOR バンプ候補（2.0.0）**。実装時に確定。
- 移行ガイド: 既存 install へ「control-plane hook → OS lock」への移行手順を `docs/` に。

## 未確定（実装計画で詰める）

1. lock/unlock を session-start に置くか、専用 lifecycle hook にするか（phase 遷移時の再計算要否）。
2. 安定 CP セットの単一所有を platform_manifest に相乗りさせるか新規 manifest か。
3. 旧 moat 退役を同 iteration の後半 task にするか、別 iteration に分けるか（リスク分散）。

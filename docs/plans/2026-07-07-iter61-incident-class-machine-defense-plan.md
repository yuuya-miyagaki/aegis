# iter61 iter60 事故クラスの機械防御（destructive patterns 拡張＋snapshot 退行ガード）実装計画

> 出典: docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1（機械層・復旧層）・§4 Phase 0-1/0-2
> 文言層（routing.md 委譲拘束雛形）は iter62 に分離。setup self-heal は iter63。
> Rev.2: grill-plan（条件付き GO）の致命3件＋要検討 1/2/3/6/7/8 を反映済み。

## Global Constraints

- footprint 5 ファイル（M）: `hooks/lib/patterns.sh`・`hooks/lib/snapshot.sh`・`hooks/session-start.sh`・`tests/test_check_destructive_coverage.py`・`tests/test_snapshot_writers.py`
- moat 該当（enforcement データ＋tamper-evidence 復旧アンカー）。deny でなく **ask**（事故防止スコープ）
- RED-first・**実装は単一コミット・ただし B1 drill 完了まで未コミット保持**（罠 f）
- 破壊 WARN・operator 向け警告は日本語必須（iter53 pin と整合）・WARN 配列は REGEX 配列と index 対
- 誤爆許容基準: `git checkout <単一ブランチ>`（**リダイレクト付き含む**）/ `-b` / `--track` / `checkout -` / `stash list|show|pop|apply` / `restore --staged <path>` は ask しない
- snapshot ガードは advisory 層 = fail-open 方向は「現行動作（再生成）」。session を brick しない

## 設計判断（brainstorm＋grill 確定）

1. `git checkout <branch>` と `<pathspec>` は構文上区別不能 → 確実な部分集合のみ捕捉: glob 文字（ref 規則で禁止）・**末尾スラッシュ**（ref 規則で禁止・grill 要検討2）・複数引数形・**` -- ` 形（grill 致命3-1）**。単一 bare パス単独のみ残余。
2. `git restore <bare-pathspec>` は常にファイル破棄 → catch-all（`--staged` は dash 始まりで除外）。
3. `git stash` 破壊系: bare／push/save／**フラグ付き bare（`-u`/`--all` 等・grill 致命3-2）**／drop/clear。list/show/pop/apply/branch は allow。
4. 全新パターンに `(-C\s+\S+\s+)?` を許容（grill 要検討1: 絶対パス運用を強制された検証サブエージェントこそ `-C` を使う）。既存パターン群（reset --hard 等）の `-C` 未対応は既存受容クラスとして据え置き（残余に明記）。
5. snapshot 退行ガード: earned 値（approved/n-a）→ pending の後退を検知したら温存＋警告。gate 名は `[a-z_]` のみ許可（**sed regex 注入封鎖・grill 要検討6**）。parse 不能・不在 → 現行動作。

## 確定文言A — patterns.sh 追加（AEGIS_DESTRUCTIVE_CMD_REGEX 末尾に6エントリ・WARN も同順）

```bash
  'git\s+(-C\s+\S+\s+)?restore\s+[^-[:space:]]'
  'git\s+(-C\s+\S+\s+)?checkout\s+[^-][^;&|[:space:]]*([*?]|/($|[[:space:];&|]))'
  'git\s+(-C\s+\S+\s+)?checkout\s+[^-][^;&|[:space:]]*\s+([^-;&|#>[:space:]0-9]|[0-9]+[^>;&|[:space:]])'
  'git\s+(-C\s+\S+\s+)?(checkout|restore)\s+[^;&|]*\s--\s'
  'git\s+(-C\s+\S+\s+)?stash(\s*$|\s+(push|save)($|[^a-zA-Z])|\s*[;&|)#>]|\s+-)'
  'git\s+(-C\s+\S+\s+)?stash\s+(drop|clear)($|[^a-zA-Z])'
```

```bash
  "破壊的: git restore <パス> は指定ファイルの未コミット変更を破棄します（復元できません）。"
  "破壊的: グロブ/ディレクトリ指定の git checkout はパスとして扱われ、該当ファイルの未コミット変更を一括破棄します（復元できません）。"
  "破壊的: 複数引数の git checkout はパス指定として扱われ、未コミット変更を破棄します（復元できません）。"
  "破壊的: -- 付きの git checkout/restore は指定パスの未コミット変更を破棄します（復元できません）。"
  "破壊的: git stash は未コミット変更を作業ツリーから退避・除去します（並走セッション/親セッションの進行中作業が消えたように見えます）。"
  "破壊的: git stash drop/clear は退避済みの変更を削除します（復元できません）。"
```

追加位置の直前にコメント1行（iter61/full-review R1・残余=単一 bare パス checkout）。コメント孤立ランを作らない（エントリ行に隣接・空行なし）。

### regex 挙動マトリクス（テストがこの表を固定する）

ask（12形）:
| コマンド | 根拠 |
|---|---|
| `git checkout docs/*`（iter60 実事故） | glob |
| `git checkout docs/` | 末尾スラッシュ（ref 名不可） |
| `git checkout HEAD docs/STATUS.md` | 複数引数 |
| `git checkout HEAD 2026-notes.md` | 複数引数（数字始まりファイル） |
| `git checkout HEAD -- docs/STATUS.md` / `git checkout main -- docs/*` | ` -- ` 形 |
| `git restore docs/STATUS.md` | restore bare |
| `git -C /path/to/repo checkout docs/*` | -C prefix |
| `git stash` / `git stash push -m wip` / `git stash -u` / `git stash --all && pytest` | stash 破壊系 |
| `git stash && python3 -m pytest -q` / `(git stash)` / `git stash > /dev/null 2>&1` | 終端クラス |
| `git stash drop` / `git stash clear` | 復元不可系 |

allow（10形）:
| コマンド | 根拠 |
|---|---|
| `git checkout main` / `git checkout feature/foo` / `git checkout v1.2.3` | 単一 bare 引数=branch 形 |
| `git checkout main 2>/dev/null \|\| git checkout -b main` | **redirect は第2引数と見なさない（grill 致命2）** |
| `git checkout main > build.log 2>&1` | 同上 |
| `git checkout -b feature/x` / `git checkout --track origin/x` / `git checkout -` | dash 始まり |
| `git checkout main && make` | 2番目トークンが `&` |
| `git stash list` / `git stash show -p` / `git stash pop && pytest` | 非破壊サブコマンド |
| `git restore --staged file.txt` | index のみ |

## 確定文言B — snapshot.sh 追加関数（Rev.2: クォート修正済み・gate 名検証追加）

```bash
# aegis_snapshot_gate_regression <root> — rc 0 when the EXISTING snapshot holds
# an earned gate value (approved / n/a) that current STATUS.md shows as pending.
# Consumed by session-start.sh so an accidental docs/ revert (full-review
# 2026-07-06 R1 / iter60 incident) cannot launder the recovery anchor away at
# the next session boundary. Fail-open toward CURRENT behaviour: missing or
# unreadable snapshot/STATUS -> rc 1 (caller regenerates as before). Authorized
# writers refresh the snapshot on every legitimate reset, so a normal rollover
# never trips this. Gate names are restricted to [a-z_] before being used in
# the sed range (a tampered snapshot line like '  .*: approved' must not become
# a regex — phantom-regression injection would freeze regeneration forever).
aegis_snapshot_gate_regression() {
  local root="$1"
  [ -n "$root" ] || return 1
  local status_file="${root}/docs/STATUS.md"
  local snapshot_file="${root}/.claude/.gate-snapshot"
  [ -f "$status_file" ] || return 1
  [ -f "$snapshot_file" ] || return 1
  local line gate cur_val
  while IFS= read -r line; do
    case "$line" in
      '  '*': approved'|'  '*': n/a') ;;
      *) continue ;;
    esac
    gate="${line%%:*}"; gate="${gate#  }"
    case "$gate" in ''|*[!a-z_]*) continue ;; esac
    cur_val=$(sed -n "/^gate_approvals:/,/^[a-z]/s/^  ${gate}: //p" "$status_file" 2>/dev/null | head -1)
    [ "$cur_val" = "pending" ] && return 0
  done < "$snapshot_file"
  return 1
}
```

## 確定文言C — session-start.sh の snapshot 節差し替え（Rev.2: 日本語・自己完結の脱出手順）

```bash
SNAPSHOT_REGRESSION_WARNING=""
if command -v aegis_write_snapshot >/dev/null 2>&1; then
  if command -v aegis_snapshot_gate_regression >/dev/null 2>&1 \
     && aegis_snapshot_gate_regression "$ROOT"; then
    # full-review 2026-07-06 R1: the snapshot outlives a docs/ revert accident
    # (iter60). Regenerating here would launder the revert into the baseline
    # and destroy the only recovery anchor — preserve it and tell the operator
    # the two legitimate ways out (reconcile, or intentional reset by deletion).
    SNAPSHOT_REGRESSION_WARNING="[WARNING] .claude/.gate-snapshot に docs/STATUS.md が失った承認済みゲートが残っています（revert/改竄の可能性）。snapshot を復旧アンカーとして温存しました。復旧するには STATUS.md の gate_approvals を snapshot の値に戻してください（snapshot と一致させる Edit は audit を通過します）。意図的にゲートをやり直す場合のみ .claude/.gate-snapshot を削除してください（次回起動時に再生成されます）。"
  else
    aegis_write_snapshot "$ROOT" || true
  fi
fi
```
`SNAPSHOT_REGRESSION_WARNING` は session-start の既存警告出力経路（additionalContext 合流点）に他警告と同形式で連結。テストは `復旧アンカーとして温存` を pin（意味反転を含む句にできない場合は presence＋preservation の実挙動で担保）。

## Task 1: patterns.sh 拡張（RED-first）

1. RED: `tests/test_check_destructive_coverage.py` に `test_tree_revert_commands_ask`（ask 12形）と `test_tree_revert_benign_allow`（allow 10形）を追加 → ask 側テストの FAIL を確認（allow 側は最初から GREEN のガードテスト＝grill 軽微1 の正確化）。
2. GREEN: patterns.sh に確定文言A → 全 PASS。
3. 回帰: `test_destructive_warning_language`・`test_glob_expansion_hooks`・`test_hook_output_schema`・`test_patterns_parity` 緑確認。

## Task 2: snapshot 退行ガード（RED-first）

1. RED: `tests/test_snapshot_writers.py` に追加（既存 scaffold 流用・session-start 直接実行）:
   - `test_session_start_preserves_snapshot_on_gate_regression` — approved 状態で snapshot 生成→STATUS raw 後退→session-start 再実行→snapshot に approved 残存＋出力に警告 pin
   - `test_session_start_rewrites_snapshot_when_no_regression` — 後退なしで正常更新・警告なし
   - `test_regression_guard_fail_open_without_snapshot` — snapshot 不在→通常生成（現行動作）
   preservation テストのみ FAIL を確認。
2. GREEN: 確定文言B＋C を実装。
3. 回帰: `test_snapshot_writers`・`test_snapshot_atomic`・`test_session_start_*`・`test_runtime_state_hook`・`test_post_status_audit_*` 緑確認。

## Task 3: ゲート運用（順序固定）

grill-code → review（1次＋盲検2次・委譲は read-only 明示＝git checkout/reset/stash/clean 禁止）→ B1 drill（未コミット diff の実 mutation: 新 regex エントリ行削除→ask テスト赤／ループ内 `&& return 0` 反転→preservation テスト赤）→ qa レポート → security（1次＋盲検2次・同拘束）→ 実装を単一コミット → record-test-result（suite 完走後・`python3 -m pytest -q`）→ ref set→approve 連続で review/qa/security → ship（**v1.22.0 MINOR**＝operator 可視の新 ask 挙動追加・iter54/58/59 前例整合〔grill 要検討8で PATCH 案を却下〕・3箇所 bump）→ docs（LEARNINGS）→ push 手前停止。

## 受容する残余（文書化してクローズ）

- `git checkout <単一bareパス>`（glob/末尾スラッシュ/複数引数/`--` なし）: ブランチ切替と構文上区別不能 → 非対象。iter62 の委譲文言層で被覆。
- **mid-session laundering**（grill 要検討5）: Bash による STATUS revert 後に親が `update-gate.sh approve` を実行すると reverted STATUS から snapshot 再生成。本ガードは session 境界のみの防御（update-gate 側ガードは正規 reset の approved→pending を誤検知するため入れない）。
- `git -C` 以外のグローバルフラグ形（`--no-pager`/`-c k=v`）・変数間接・quote 難読化・バックスラッシュ行継続: SF-004 受容クラス（既存パターン群と同一の限界）。
- `git restore --staged -- file` の ask（` -- ` 形に一致）: 低頻度・ask-only の FP として受容。
- `git checkout $(...)` 等コマンド置換の複数引数誤認・fd≥10 リダイレクト（`22>f`）の複数引数誤認: 低頻度・ask-only で受容（grill-code m-3）。
- `git restore -q <path>` 等「--source/--worktree/-W 以外のフラグ先行 restore」: 低頻度残余（grill-code M-2 の fix-forward は --source/--worktree/-W を封鎖済み）。
- **逆方向 revert はスコープ外**（grill-code m-4）: rollover 直後（snapshot=pending）に「ゲートが進む」方向の revert は検知しない。本ガードは earned→pending の後退のみ＝復旧アンカー保全が目的。
- REGEX↔WARN の順序対応 pin・敵対 snapshot の行数上限: バックログ（grill-code m-1/m-2・ask-only/実運用影響ゼロ）。
- **/recover・session-recovery skill への snapshot 照合手順の追記は iter62 で回収**（grill 要検討4: 警告文自体を自己完結にすることで当面の行き止まりは解消済み）。

## Rev.3（grill-code fix-forward）

- M-1: `git checkout -f/--force` パターン追加（競合変更の黙殺破棄＝事故クラス隣接形）。
- M-2: `git restore --source/--worktree/-W` パターン追加（フラグ先行 restore の tree-revert 形）。
- CMD REGEX/WARN は 22→24 本・配列長 pin 更新。ask テスト+5形・allow ガード+1形（`checkout -q main`）。

## Rev.4（盲検2次レビュー fix-forward）

- M-1: **先頭グロブ形**（`git checkout *` / `*.md` / `?foo.md`）が素通り→ glob エントリの prefix を optional 化（`([^-][^;&|[:space:]]*)?`）で封鎖。ask テスト+3形。
- m-3: 「正規 reset → session-start 無警告」の pin テスト追加（誤検知ゼロの生命線を回帰固定）。
- 残余追記: `git restore <-q 等の非破壊フラグ連鎖> -W <path>`（短形式は第1フラグのみ捕捉・長形式 --worktree は位置不問で捕捉）／**approved→n/a 方向の後退は非検知**（earned→pending のみが検知対象＝bugfix 期 STATUS への revert は逆方向クラスと同様スコープ外）／`git checkout --ours/--theirs` はコンフリクト解決文脈の受容クラス。

## Rev.5（盲検2次セキュリティ fix-forward）

- Major-1: **fd 前置 redirect stash**（`git stash 2>/dev/null` / `1>/dev/null 2>&1`）が素通り＝エージェント最頻出形。stash 終端クラスを `\s*[0-9]*[;&|)#<>]` に拡張（fd 番号を許容）。ask テスト+2形・良性ガード+2形（`stash pop/list 2>/dev/null`）。
- Major-2: **巨大/破損 snapshot で session-start が数分ハング**（「brick しない」不変条件違反）。原因＝snapshot 行ごとの sed fork。→ STATUS の gate ブロックを1回だけ sed で読み、各 earned 行を case で照合（fork O(1)・bash 3.2 互換で連想配列不使用）。実測 119s→1.16s（退行なし50000行）。残余の「実運用影響ゼロ」記載は「実運用（8行）では無害・肥大時のハングは設計で解消済み」に訂正。
- Minor-3: **フラグ先行 force checkout**（`git checkout -q -f main` / `--quiet --force main`）が素通り。force エントリに先行フラグ群 `(--?[a-zA-Z][a-zA-Z=-]*\s+)*` を許容。ask テスト+2形・良性ガード（`checkout -q main` は既存）。

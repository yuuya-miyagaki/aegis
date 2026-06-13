# 実装計画: 監査 fix-forward 優先度1-2（A1-A8）

> 起点: `docs/audit-report-2026-06-06.md` の優先度1（保証修復 A1-A4）・優先度2（mirror drift A5-A8）。
> 方針: fix-forward（既存挙動を壊さず欠陥のみ修正）。TDD（failing test 先行）、全 195+ tests green 維持。
> 本計画は自己 grill-plan 済み（末尾「grill 反映」）。push はユーザー承認後。

## スコープと順序

| 順 | 項目 | 対象 | 種別 |
|---|---|---|---|
| 1 | A3 | `hooks/lib/extract-input.sh` | 抽出の正確性（truncation 封じ）|
| 2 | A1 | `hooks/check-skill-gate.sh` / `check-cron-gate.sh` / `check-task-created.sh` | gate の fail-closed 化 |
| 3 | A2 | `hooks/check-deploy-gate.sh` | deploy 正規表現の語境界化 |
| 4 | A4 | `tests/test_extractors.py` / `tests/test_hook_output_schema.py` | fail-mode 契約テスト |
| 5 | A5 | `scripts/check_reference_drift.py` + test | mirror 内容同一性 assert（先に red）|
| 6 | A6 | `examples/minimal-project/hooks/session-start.sh` ほか / `templates/CLAUDE.template.md` | drift 実体修正（A5 を green に）|
| 7 | A7 | `templates/profiles/full.json`（or `bin/setup.sh`）| deploy skill companion 同梱 |
| 8 | A8 | `examples/minimal-project/.claude/commands/retro.md` | /retro scaffold-safe ガード |

A3→A1 の順は、A1 が A3 と同型の「python3 失敗時 grep fallback」を使うため。A5→A6 は A5 を failing check として先に入れ、A6 で実体 drift を消して green にする（TDD アーク）。

## 設計判断（grill 対象）

### A3 — extract_command/file_path の truncation 封じ（perf 原則を維持）
- 欠陥: `grep -o '"command"…"[^"]*"'` が本文中の `\"` で停止。python3 fallback は「空」時のみ発火し「切り詰め」時は不発（report H3）。
- **却下案**: 無条件 python3-primary。→ 再アーキ §4 の明示原則「hook は毎ツール呼びで走るので python/jq 起動 30-50ms を回避」に反し、destructive/secrets/deploy/tdd/gate の**全 Bash/Edit 呼びに 30-50ms 回帰**。
- **採用案（条件付き python3）**: 生入力に escaped-quote（`\"`）が**在るときだけ** python3 を使い、無ければ従来 grep 高速路。加えて従来の「空→python3」fallback も残す。
  ```sh
  extract_command() {
    local input="$1" result
    if printf '%s' "$input" | grep -q '\\"'; then        # escaped-quote 在り → grep は不正確
      result=$(printf '%s' "$input" | python3 -c '…' 2>/dev/null || true)
      [ -n "$result" ] && { printf '%s' "$result"; return; }
    fi
    result=$(printf '%s' "$input" | grep -o '"command"…"[^"]*"' | head -1 | sed …)  # 高速路
    [ -z "$result" ] && result=$(printf '%s' "$input" | python3 -c '…' 2>/dev/null || true)
    printf '%s' "$result"
  }
  ```
  - 正確性: escaped-quote を含むコマンドは python3 が full 抽出 → destructive/secrets が後段の dangerous トークンを見られる。
  - 性能: 引用符無しの大多数は grep のまま（python3 ゼロ）。python3 は escaped-quote 時のみ（稀）。原則を尊重。
  - 同型を `extract_file_path` にも適用。
- テスト先行: `test_extractors.py` に「`echo \"hi\" && git push --force` を含む tool_input → extract_command が `git push --force` を含む full 文字列を返す」failing test。

### A1 — gate hook 3本の fail-closed 化（grep fallback ＋ 最終 fail-closed）
- 欠陥: skill/cron/task-created が判定値を python3 のみで抽出し、空時 `emit_allow`。python3 不在で素通り（report H2）。
- **採用案（層化）**:
  - **task-created**: hard-stop 判定（phase=implement かつ plan≠approved/n/a）は **STATUS.md の grep/sed のみで完結し subject 不要**。よって「subject 空→early `emit_allow`」（:61-69）を撤廃し、空時は placeholder（`(unparseable)`）＋debug dump のままゲート判定へ**フォールスルー**。→ payload 解析可否に関わらず hard-stop が効く＝完全 fail-closed。
  - **skill-gate / cron-gate**: 判定は抽出値（skill 名 / prompt）に依存。よって python3 抽出が空/失敗なら **pure-bash grep fallback**（`"skill"` 値 / cron は `prompt|task|instructions|command` 値を grep）。それでも空なら **fail-closed = `emit_ask`**（「評価不能。手動確認」）。両 hook は Skill/CronCreate matcher 限定登録のため、抽出不能＝解析失敗＝ask が妥当。
- テスト先行:
  - skill-gate, python3 不在（PATH に exit127 shim）, 正常 JSON `{"tool_input":{"skill":"update-config"}}` → grep が拾い **emit_ask**（fail-open しない）。
  - skill-gate, python3 不在, grep も拾えぬ崩れ入力 → **emit_ask**（最終 fail-closed）。
  - task-created, python3 不在, phase=implement+plan=pending, 任意 payload → **continue:false**（subject 不要で判定）。

### A2 — deploy 正規表現の語境界化
- 欠陥: `(^|[;&|] *)` アンカーで `npx vercel deploy`・`FOO=bar vercel deploy`・`sudo/time vercel deploy` が未マッチ→素通り（report H1）。`npx vercel deploy` は通常語。
- **採用案**: ツール名を**語境界**（行頭 or 空白/`;`/`&`/`|` 直後）でマッチし先行トークン非依存に:
  `DEPLOY_RE='(^|[[:space:];&|])(vercel +deploy|vercel[[:space:]]*$|firebase +deploy|netlify +deploy|(npm|pnpm|yarn|bun) +(run +)?deploy|flyctl +deploy|railway +deploy|gcloud +app +deploy)'`
- トレードオフ: `echo "… vercel deploy …"` 等が false-positive で ask になりうるが、**gate の false-positive コスト（ユーザー確認1回）≪ false-negative コスト（deploy 漏れ）**。report H1 の方向性「先行トークン非依存の語境界」と一致。
- 注: `check-cron-gate.sh` の DANGER_RE はアンカー無しで既に `npx vercel deploy` を捕捉済 → 変更不要。
- テスト先行: gate=pending で `npx vercel deploy --prod` / `FOO=bar vercel deploy` → deny。負例 `rg deploy` / `cat DEPLOY-CHECKLIST.template.md` → allow。

### A5 — mirror 内容同一性 assert
- **真の mirror 集合（byte-identical 必須）**: `.claude/agents/*`、`.claude/rules/*`、`hooks/*.sh`＋`hooks/lib/*.sh`、複製される `scripts/check_status.py`・`scripts/update-gate.sh`、`.claude/commands/*`。
- **除外（templated/意図的 divergence）**: `CLAUDE.md`・`docs/STATUS.md`・`docs/LEARNINGS.md`（プロジェクト固有）、allowlist=`.claude/commands/validate.md`（scaffold-safe 既定）＋`.claude/commands/retro.md`（A8 で同様に scaffold-safe 化）。
- 実装: `check_reference_drift.py` に `check_mirror_identity(root)`。両側に存在するファイルのみ hash 比較し、不一致は FAIL。存在有無は既存 `REQUIRED_EXAMPLE_FILES.exists()` が担当（二重化しない）。
- テスト先行: temp fixture（root/example で1ファイル差）→ violation 報告。実 repo に対しては現状 `session-start.sh` 差で **red**（→ A6 で green）。

### A6 — drift 実体修正
- `examples/minimal-project/hooks/session-start.sh` ← root と同期（`CLAUDE_CODE_SUBAGENT_MODEL` advisory ブロック追加）。**A5 green の必須条件**。
- `examples/minimal-project/CLAUDE.md` ← hook-enforcement 行＋Model Policy 節を追加（example は 12 agent 同梱＝Model Policy 適用対象）。※ templated のため A5 非対象だが H4/staleness 修正。
- `templates/CLAUDE.template.md` ← 同 3 要素を追加（scaffold 反映）。**【ユーザー確認したい fork】** Model Policy はエージェント同梱（full）でのみ実効。minimal/standard は agents 無し。**推奨: 完全契約のリファレンスとしてテンプレに含める**（プロジェクト側で削れる／害は記述冗長のみ）。異論あれば「full 専用 include」に切替可。

### A7 — deploy skill companion 同梱
- **採用案（最小）**: `templates/profiles/full.json` の file 一覧に `.claude/skills/deploy/platforms.md` を追加（setup.sh は一覧を1ファイルずつコピー）。
- **代替（堅牢）**: setup.sh を「skill は dir 単位コピー」に。将来の多ファイル skill に強い。→ 実装時 setup.sh を読んで最小差で堅牢にできるか判断。現状 deploy のみ companion 持ちのため最小案で十分。

### A8 — /retro scaffold-safe
- `examples/minimal-project/.claude/commands/retro.md` を `/validate` と同型のガード（「`retro_report.py` があれば実行、無ければ案内」）に。A5 allowlist に retro.md 追加（validate.md と同じ意図的 divergence）。

## 失敗モード / リスク
- R1: A2 の broad マッチで deploy gate の ask 頻度増 → gate の本質（確認を促す）に沿う。許容。
- R2: A3 の条件分岐が `\"` を他フィールドで検出し稀に python3 起動 → 正確性に影響せず perf 微増のみ。
- R3: A1 の skill/cron fail-closed-ask が python3 全断時に毎回 ask → python3 全断は CC 環境で異常事態。安全側。
- R4: A5 が既存の意図的 divergence を誤検知 → allowlist（validate.md/retro.md）で吸収。CLAUDE.md 等 templated は集合から除外。
- R5: 195 tests への影響 → 各 fix は新規 test 先行＋既存 green 維持を合格条件に。

## 検証（完了条件＝evidence）
- 新規 test が red→green。`python3 -m unittest discover -s tests` 全 PASS（195＋追加）。
- `run_eval.py --tier 0..3` / `check_framework_contract.py`（full＋standard）/ `check_reference_drift.py` / `check_status.py --strict` 全 PASS。
- 実装後 grill-code。push はユーザー承認後。

## grill-plan 反映（自己グリルの catch）
- A3 の無条件 python3 化を **却下**（再アーキ perf 原則違反）→ escaped-quote 条件付きに。
- A1 を「即 fail-closed-ask」でなく **grep fallback→最終 fail-closed** に層化（python3 不在でも正常 JSON は黙って正しく動く＝ask ノイズ最小）。task-created は subject 非依存と判明し **フォールスルー**で完全 fail-closed。
- A5 と A6 を **red→green の TDD アーク**として結合。
- A8 を **validate.md 先例と同型**（ガード＋allowlist）に統一。
- A6 テンプレの Model Policy scope は**ユーザー確認 fork**として明示（推奨＝含める）。

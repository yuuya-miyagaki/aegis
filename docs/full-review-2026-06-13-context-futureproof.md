# 第7回 全力レビュー報告書 — コンテキスト予算 / 機能整合 / 将来耐性

- 日付: 2026-06-13
- 対象: v1.6.2（HEAD `3f44478`）
- 依頼観点: ①常時読むコンテキストが大きすぎないか ②全機能が目的どおり動くか ③LLM 進化で陳腐化しない設計か ④その他重要観点
- 手法: 5 軸を独立サブエージェントで並列監査（read-only + テスト実行）。各所見は file:line 実証。
- 区分: charter と report を 1 ファイルに統合（doc スプロール抑制方針 M2 に従う）

---

## 0. 総評

中核は健全。依頼者が最も心配していた①②はおおむね杞憂で、本当に塞ぐべきは moat（決定論層）の未修正の穴 2 件。

- **① コンテキスト肥大 → 毎ターンの定常コストは実質ゼロ。** 実装フェーズ中、各 PreToolUse/PostToolUse フックは `{}`（`emit_allow`）しか返さない。文脈注入はフェーズ遷移・テスト失敗・compact 時のみ。常時オンは `CLAUDE.md`(~1,100tok) + skill description 18 個(~750tok) ≒ **約 1,850tok/セッション**。ただし session-start 注入が **上限なしで伸びる**設計。
  - 訂正: 会話中に観測した `routing.md`/`state-machine.md` の展開は **IDE の開ファイル注入**であり、Claude Code の常時ロードではない（`CLAUDE.md` に `@`-import なし）。
- **② 全機能が意図どおり動くか → 全項目 PASS。** 683/683 テスト OK、contract（全プロファイル）/drift/scaffold-smoke（フック実発火含む）/redteam 18/18 すべて緑。フック 17 個＝登録 17 個の 1:1、lib 欠落時は `deny`（fail-closed 実証）。機能破綻・サイレント fail-open は検出されず。
- **③ 将来陳腐化 → 中核はむしろ将来に強い。**「人間承認の hard gate＋機械観測エビデンス＋永続 state」はモデルが賢くなっても無効化されない。陳腐化リスクは session-start の HINT 説教文と skill 到達性再注入に局所化（＝切り離せる）。

---

## 1. 軸別所見

### R1 制御文字によるゲート無効化 — High（security / fail-open）
`hooks/lib/emit.sh:29-37` の `_aegis_json_escape` は `\ " \n \t \r` のみエスケープ。`0x01-0x08` 等の制御バイトは素通り。STATUS.md 由来値（攻撃者影響可能）が `post-status-audit.sh:93` などの `emit_block` reason に乗ると **JSON が壊れ、厳格パーサが hook 出力を破棄 → gate tamper がブロックされない**。1 箇所の修正で全 call site を一括カバーできる最高レバレッジ点。
- 制約: emit.sh の不変条件は「deny 経路に外部プログラム依存ゼロ」。修正は **pure-bash（パラメータ展開のグロブ範囲置換）**で行う。`tr` 等の外部コマンドは不可。

### R2 STATUS/LEARNINGS のコンテキスト注入 — High（prompt injection）
`hooks/session-start.sh` が blockers(:54/:81)、next_action(:47/:78)、learnings(:212-215) を **無サニタイズで verbatim** に additionalContext へ連結。これらは client 要件・上流成果物・失敗ログから書かれる＝攻撃者影響可能。`gates: plan=pending` 等の正規 signal と隣接注入され、プロンプトインジェクション面になる。実証: blocker に「IGNORE ALL PREVIOUS INSTRUCTIONS…」を置くと無改変で additionalContext に到達。

### R3 切断 stdin で deny フックが allow — Med（defense-in-depth）
stdin JSON が途中切断だと `extract_command`（`extract-input.sh:32-62`）が空を返し、`check-destructive.sh:35-37` / `check-secrets.sh` が `emit_allow`。CC は正常 JSON を出すため主要攻撃経路ではないが、二重防御の穴。raw `INPUT` に destructive/secret keyword があれば `emit_ask` にフォールバックすべき（`check-control-plane.sh:187-194` が既に採る型）。

### C1 session-start 注入が上限なし — High（context budget）
next_action/blockers/learnings に文字数キャップなし。LEARNINGS.md が育つと**毎セッション静かに肥大**。worst ~590tok。**R2 と同一コードで、1 回の修正で肥大とインジェクションの両方を塞げる（収束）。**

### C2 CLAUDE.md / skill description の重複 — Med（context budget）→ 一部訂正
- 訂正: Agent A の「skills 名前リスト(L60-66) 削除」は **不可**。`check_reference_drift.py:81-118` が CLAUDE.md の skill 名リストと `.claude/skills/` を双方向照合する drift 契約のため、削除すると契約違反。**skills リストは load-bearing＝残す。**
- `check_framework_contract.py` に `MAX_CLAUDE_WORDS=650` と `REQUIRED_CLAUDE_HEADINGS` あり。圧縮は見出し保持・語数制約内で行う。
- 安全な節約は `aegis-*` 3 skill description の短縮（~150char）程度。実効は小さい。→ **P1 は縮小スコープへ。**

### M1 example ミラー 520K の手動同期 — High（maintainability）
`examples/minimal-project/` が `.claude`/`hooks`/`scripts` を **byte-identical でコミット複製**し lockstep 維持。install 元ではなく「見本＋smoke fixture」。最大の保守税。`make example`で自動生成、または tmp install から smoke 化で除去可。

### M2 docs スプロール — Med（maintainability）
root docs 156 件中 **113 件が過程成果物**（qa-reports 59 / plans 54＝1.6M）。空 scaffold 3 ディレクトリ、40KB README。archive 化で root を約 70% 削減。

### M3 STATUS パーサ二重化 — High（maintainability / fragility）
`check_status.py`（schema 所有）と、フック内の場当たり sed/grep/awk が並存。`lib/frontmatter.sh` があるのに session-start は独自 `extract_value` をインライン。format 変更時に 2 箇所連動＝壊れやすい。`status_doctor.py` も `check_status.py` を cross-import。

### F1 将来陳腐化の局所 — 戦略（Med）
HINT 説教文（`session-start.sh:128-180`）・TDD 合理化テーブル・skill 到達性再注入は「賢いモデルには摩擦」。`disable-model-invocation:true` が到達性 machinery 全体を強制＝プラットフォーム改善で丸ごと不要化しうる。

### 機能整合の追認 — PASS（情報）
17 フック 1:1 登録・lib 9 個実在・lib 欠落→deny 実証・mirror byte 一致・683 テスト / contract / drift / smoke / 18 PoC 全 PASS。既存 redteam PoC が command-bypass と lib-integrity を網羅。**未カバーは R1/R2/R3 の 3 件。**

---

## 2. 優先度付き改善プラン（要約）

| 段 | 項目 | 重大度 | 実装計画 |
|---|---|---|---|
| **P0** | R1 制御バイトの pure-bash 処理（emit.sh 単一点） | High | `docs/plans/2026-06-13-v163-moat-context-hardening-plan.md` |
| **P0** | R2＋C1 session-start 自由文の cap＋sanitize＋untrusted envelope（収束） | High | 同上 |
| **P0** | R3 raw-fallback keyword → `emit_ask` | Med | 同上 |
| **P1** | aegis-* description 短縮（skills リストは残す）／CLAUDE.md は見出し・語数制約内で微圧縮 | Med | 同上（縮小スコープ） |
| **P2** | HINT/合理化テーブルを `AEGIS_NUDGE=off`＋profile 連動で opt-out 化 | 戦略 | 別途（backlog） |
| **P2** | volatile-truth マニフェスト復活（tool名/event名/schema検証日/model id を 1 宣言、drift 監視） | 戦略 | 別途（backlog） |
| **P3** | example ミラー自動生成 or smoke-only 化（520K lockstep 税の除去） | High | 別途（backlog） |
| **P3** | 過程 docs の archive 化・空 scaffold 削除 | Med | 別途（backlog） |
| **P3** | STATUS パーサを `lib/frontmatter.sh` に一本化・status_doctor を `--health` 統合 | High | 別途（backlog） |

今回の着手範囲: **P0 ＋ P1（縮小）= v1.6.3 patch**。P2/P3 は backlog として本報告書に記録。

---

## 3. 将来方向（P2/P3 backlog の論点）

- **enforce outcomes, delegate paths** を完遂する。gates とエビデンスログが moat、HINT 説教は legacy。賢いモデルほど「説教」は摩擦になり「決定論的禁止」は価値が上がる。
- emit.sh のチョークポイント規律を横展開し、プラットフォーム結合値（hook schema / tool 名 / event 名 / model id）を 1 マニフェストに隔離 → 追従トレッドミルの税を 1 箇所に集約。
- ミラー複製と過程 docs を構造的に削減し、ソロ運用の持続性を確保。

---

## 付録: 監査軸とサブエージェント

| 軸 | 観点 | 主要成果 |
|---|---|---|
| A | コンテキスト予算 | 毎ターン ≒0tok、常時オン ~1,850tok、session-start worst ~590tok（上限なし） |
| B | 機能整合 | 全 PASS（683 テスト / contract / drift / smoke / 18 PoC）、fail-open 無し |
| C | 将来耐性 | durable（gate/evidence/state）vs at-risk（HINT/到達性）を分離、coupling ランク |
| D | 複雑性・スプロール | ミラー 520K、過程 docs 113 件、STATUS パーサ二重化 |
| E | 敵対堅牢性・注入 | R1 制御バイト / R2 注入 / R3 切断 stdin の 3 未カバー gap |

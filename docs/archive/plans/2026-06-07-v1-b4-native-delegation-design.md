# B4 設計: native 冗長棚卸し（委譲マップ）

> 出典: `docs/audit-report-2026-06-06.md` §4 優先度4 B4（native 冗長の棚卸し — Checkpoints/`/rewind`・Routines・Auto Mode への委譲可否を評価し surface を削減）。
> B-series（B1/B2/B3a/B3b/B3c）の最後。北極星の穴ではなく future-proof な整地（「追従トレッドミルから降りる」方針と整合）。

## 前提の精査（grill-premise 相当）

監査 B4 の前提＝「Checkpoints/Routines/Auto Mode が aegis を冗長化する」は、native 機能を
claude-code-guide で確認した結果 **ほぼ成立しない**:

- **Checkpoints/`/rewind`**: ファイル undo のみ・セッション内・揮発。会話/実行状態は復元しない。aegis の `session-recovery`（STATUS.md からフレームワーク状態を再構築）とは**別問題**。
- **Routines / scheduling**: native Claude Code に該当機能が**存在しない**。委譲先なし。
- **Auto Mode**: 非決定的な許可分類器（research preview）。aegis の PaC hooks は**決定論的保証**（moat）。思想が違い、委譲すると保証が緩む。
- **真の重複候補**: `/recover`＋`session-recovery` ↔ native `/resume`＋auto memory＋CLAUDE.md。ただし会話復元（native）と状態台帳復元（aegis）は別レイヤーで、**併用関係**であって置換ではない。

結論: 削除すべき真の冗長 surface はほぼ無い。B4 の価値は「**何を native に委譲し、何を保持するか**」を1枚に記録し、将来の監査・adopter が再評価（treadmill）しないようにすることにある。

## スコープと決定事項（ブレストで確定）

1. **成果 ＝ 委譲マップ＋外科的 slim**: native 各機能ごとに「委譲/併用/保持」と根拠を記録するマップを作る。積極削除はしない（load-bearing surface を誤って削るリスク回避）。
2. **マップの置き場 ＝ README 節**「Relationship to native Claude Code features」。再評価するのはまさに adopter なので、発見点（README）で先回りする。migration/哲学が既に README にあり同居が自然。
3. **外科的 slim ＝ session-recovery に native 併用注記**のみ。会話復元は native `/resume`、状態台帳の再構築は本 skill、と棲み分けを明記。それ以外の surface は不変。

## 非目標（Non-goals / YAGNI）

- load-bearing surface の削除（session-recovery＝状態台帳復元・PaC hooks＝決定論 moat）はしない。
- 新機能・新 skill・新コマンドの追加はしない。
- Auto Mode への安全委譲はしない（決定論 hooks を維持）。
- ADR（docs/decisions/）への二重記録はしない（README 一本・drift とメンテ負荷回避）。

## コンポーネント（2）

| # | 成果物 | 種別 |
|---|---|---|
| 1 | `README.md` | 改修（委譲マップ節を追加） |
| 2 | `.claude/skills/session-recovery/SKILL.md` | 改修（native との関係を1節追加）＋ `examples/minimal-project` へ byte 同一ミラー |

> README は example 非ミラー。session-recovery は `.claude/skills/` 配下＝MIRROR_DIRS なので example へ同期必須。新 skill を足さないので example のスキル数（18）は不変。

## README 委譲マップ（節の中身）

節タイトル: `## Relationship to native Claude Code features`

導入文（要旨）: aegis は native と一見重なる surface を意図的に保持している。何を native に委譲し
何を保持するかを記録し、リリースごとに境界を再評価しないための一覧。**本マップは監査 B4 が挙げた
候補（Checkpoints/rewind・Routines・Auto Mode）＋精査で判明した実重複（/resume・auto memory・
/recover）を対象とする。網羅監査ではない。**

| Native feature | What it does | Aegis surface | Decision |
|---|---|---|---|
| Checkpoints / `/rewind` | Undo file edits, session-local, ephemeral | `session-recovery` | **Keep** — different problem: session-recovery rebuilds framework state (phase/gates/refs/partials) from STATUS.md, not file undo. Use both. |
| `/resume`, `--continue`, `--fork` | Replay a prior session's conversation | `session-recovery` | **Complement** — `/resume` may be enough when the prior session is available; session-recovery reconstructs/verifies state from STATUS.md when the conversation is gone (or to re-check partials). |
| (the `/recover` command) | aegis convenience trigger for the recovery protocol | `/recover` → `session-recovery` | **Keep** — a discoverable slash-command trigger; native `/resume` restores conversation but does **not** run the STATUS-based state-recovery protocol. The skill is `user-invocable`, so `/recover` is an affordance, not a dependency. |
| Auto memory (`MEMORY.md`) | Persist personal preferences across sessions | `docs/LEARNINGS.md` | **Delegate (bounded)** — auto-memory holds personal preferences only; project lessons stay in LEARNINGS (boundary documented in CLAUDE.md, not machine-enforced). |
| Auto Mode | Permission classifier (probabilistic; research preview) | PaC hooks (destructive-command deny) | **Keep** — aegis's moat is *deterministic* hooks-as-guarantees; a probabilistic classifier cannot provide the same guarantee (durable reason, independent of Auto Mode's preview status). |
| Routines / scheduling | (not a native Claude Code feature) | — | **N/A** — nothing to delegate. |

## session-recovery への注記（slim 実体）

`## いつ使うか` の前後に1節を追加:

> **native との関係**: 前回セッションが残っていれば native `/resume` で会話が戻り、それで足りる
> こともある。本 skill は会話復元や `/rewind`（ファイル undo）とは別で、**会話が無いとき**（新規
> セッション・コンテキスト圧縮・クラッシュ）や **STATUS.md に対して状態/partial を検証したいとき**に、
> `docs/STATUS.md` からフレームワーク状態（phase/gates/refs/partial）を再構築する。会話＝`/resume`、
> 状態台帳＝本 skill、と棲み分ける（毎回両方必要というわけではない）。

## テスト戦略

実行コードを持たない（README 節＋skill 注記）。検証は2層:
1. **構造的検証（自動）**: `check_framework_contract`（full/standard）・`check_reference_drift`（ミラー byte 同一）・`test_mirror_identity`・`eval_scaffold_smoke`・既存テスト非回帰。
2. **内容レビュー（人手）**: 委譲マップの判断と根拠が正確で、session-recovery 注記が native との棲み分けを誤解なく伝えるか（grill-code 相当）。

## Self-Review（執筆者チェック）

- **プレースホルダ/TBD**: なし。
- **内部整合**: 決定1-3 が各コンポーネントと一致（マップ=README、slim=session-recovery 注記、削除なし）。マップの各行が前提の精査結果と一致。
- **スコープ**: B4 単体に限定。surface 削除なし＝退行リスク最小。単一の小さな実装計画に収まる。
- **曖昧性**: 「委譲/併用/保持/該当なし」の4語で各 native 機能の扱いを一意化。session-recovery と native の棲み分けを注記で明示。
- **要確認（実装時）**: README のどの位置に節を置くか（Migration の前後どちらか、既存構成に合わせる）。session-recovery が example ミラー対象であることの再確認。

## grill-plan 反映（2026-06-07）

- **要検討1（/recover 明示）**: マップに `/recover` コマンド行を追加し「Keep」を根拠付きで明示（薄いラッパーだが発見可能なトリガー・native /resume は状態復帰プロトコルを起動しない・skill は user-invocable なので /recover は affordance）。削除はしない（公開コマンド削除＝SemVer 破壊変更で割に合わない）。
- **要検討2（auto memory 文言）**: 「enforced by CLAUDE.md」→「boundary documented in CLAUDE.md, not machine-enforced」に訂正。
- **要検討3（注記の棲み分け）**: session-recovery 注記を「/resume で足りることもある／本 skill は会話が無いとき・状態検証時」と修正し「毎回両方必要というわけではない」を明記。
- **要検討4（Auto Mode 根拠）**: 根拠を durable な「決定論 vs 確率的」に一本化、preview は補足に降格（GA 化しても腐らない）。
- **要検討5（評価範囲）**: マップ導入文に「監査候補＋実重複が対象・網羅監査ではない」と範囲を明記。

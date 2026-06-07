# B4 native 冗長棚卸し 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** native Claude Code 機能と aegis surface の「委譲/併用/保持」を README に記録し（再評価=treadmill を止める）、session-recovery に native 併用注記を足す。load-bearing surface の削除はしない。

**Architecture:** 設計は「README に新節」だったが、**計画段階の発見で README に既存節 `## Native Feature Mapping`（feature/usage/reason の3列表・auto-memory/TodoWrite は記載済み）があるため、新節でなく既存表を拡張**する（DRY・重複節を作らない・評価範囲が表として一意）。＋ `session-recovery` skill に native との棲み分け注記（mirror 必須）。実行コードなし。

**Tech Stack:** Markdown（README＋skill）／構造検証（contract・drift・mirror-identity・tier0/2・strict）。

> **テスト方針:** 実行コードを持たない（doc＋注記）。検証は登録整合の green ＋内容目視。
> **ミラー注意:** `session-recovery` は `.claude/skills/` 配下＝example へ byte 同一ミラー必須。README は example 非ミラー。新 skill を足さないので example スキル数（18）は不変。

---

## ファイル構成

| ファイル | 役割 | 新規/改修 |
|---|---|---|
| `README.md` | `## Native Feature Mapping` 表に B4 行を追加 | 改修 |
| `.claude/skills/session-recovery/SKILL.md` | native との関係を1節追加 | 改修（+example ミラー） |

---

## Task 1: README の Native Feature Mapping 表を拡張

**Files:**
- Modify: `README.md`（`## Native Feature Mapping` 表の末尾行 `| Context compaction | ... |` の直後）

- [ ] **Step 1: 表に B4 行を追加**

`README.md` の `## Native Feature Mapping` 表で、最終行
```markdown
| Context compaction | Controlled by PreCompact hook | Blocked when STATUS.md is stale |
```
の直後に、次の4行を追加する:

```markdown
| Checkpoints / `/rewind` | (complementary) `session-recovery` | **Keep** — `/rewind` undoes file edits (ephemeral); `session-recovery` rebuilds framework state (phase/gates/refs/partials) from STATUS.md. Different problem. |
| `/resume` / `--continue` / `--fork` | (complementary) `/recover` + `session-recovery` | **Complement** — `/resume` restores the conversation (may suffice); `session-recovery` reconstructs/verifies state from STATUS.md when the conversation is gone. `/recover` is the discoverable trigger for that protocol, which `/resume` does not run. |
| Auto Mode | — | **Keep PaC hooks.** aegis's moat is *deterministic* hooks-as-guarantees; a probabilistic permission classifier cannot give the same guarantee (durable reason, independent of Auto Mode's preview status). |
| Routines / scheduling | — | **N/A** — not a native Claude Code feature; nothing to delegate. |
```

> 既存行（Auto-memory=Personal preferences only / TodoWrite=session-local）が委譲済みの記録を既にカバーしている。本 Task はそれらを再記述せず、監査 B4 候補＋実重複の不足分のみ足す。

- [ ] **Step 2: contract と表妥当性を確認**

Run: `python3 scripts/check_framework_contract.py --profile=full 2>&1 | tail -1`
Expected: `PASS: aegis contract is aligned`

Run: `grep -c 'Keep\|Complement\|N/A' README.md`
Expected: 追加行が反映され 1 以上（目視で4行追加を確認）。

- [ ] **Step 3: コミット**

```bash
git add README.md
git commit -m "docs(b4): record native delegation map in Native Feature Mapping"
```

---

## Task 2: session-recovery に native 併用注記を追加

**Files:**
- Modify: `.claude/skills/session-recovery/SKILL.md`（`## いつ使うか` の直前）
- Modify (mirror): `examples/minimal-project/.claude/skills/session-recovery/SKILL.md`

- [ ] **Step 1: 注記を挿入**

`.claude/skills/session-recovery/SKILL.md` の `## いつ使うか` の行の直前に、次のブロックを挿入する:

```markdown
## native との関係

前回セッションが残っていれば native `/resume` で会話が戻り、それで足りることもある。本 skill は
会話復元や `/rewind`（ファイル undo）とは別で、**会話が無いとき**（新規セッション・コンテキスト圧縮・
クラッシュ）や **STATUS.md に対して状態/partial を検証したいとき**に、`docs/STATUS.md` から
フレームワーク状態（phase/gates/refs/partial）を再構築する。会話＝`/resume`、状態台帳＝本 skill、と
棲み分ける（毎回両方必要というわけではない）。

```

- [ ] **Step 2: example へミラー＋byte 同一確認**

```bash
cp .claude/skills/session-recovery/SKILL.md examples/minimal-project/.claude/skills/session-recovery/SKILL.md
diff -q .claude/skills/session-recovery/SKILL.md examples/minimal-project/.claude/skills/session-recovery/SKILL.md && echo "mirror OK"
python3 scripts/check_reference_drift.py 2>&1 | tail -1
```
Expected: `mirror OK` ＋ `PASS`

- [ ] **Step 3: コミット**

```bash
git add .claude/skills/session-recovery/SKILL.md examples/minimal-project/.claude/skills/session-recovery/SKILL.md
git commit -m "docs(b4): session-recovery notes native /resume complementarity"
```

---

## Task 3: 統合検証

- [ ] **Step 1: 全検証を green に**

Run（順に）:
- `python3 scripts/check_framework_contract.py --profile=full` → `PASS`
- `python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project` → `PASS`
- `python3 scripts/check_reference_drift.py` → `PASS`（警告ゼロ）
- `python3 -m unittest tests.test_mirror_identity` → `OK`
- `python3 scripts/run_eval.py --tier 0` → `Ran 296 tests` / `OK`（非回帰・新規テストなし）
- `python3 scripts/run_eval.py --tier 2` → `Result: PASS`
- `python3 scripts/check_status.py --root . --strict` → `PASS`

- [ ] **Step 2: 内容目視レビュー**

README の表に4行（Checkpoints/rewind・/resume 系・Auto Mode・Routines）が追加され、判断（Keep/Complement/N/A）と根拠が正確であること。session-recovery 注記が「/resume で足りることもある／本 skill は状態再構築」と棲み分けを誤解なく伝えること。

- [ ] **Step 3: 証拠コミット（変更があれば）**

変更が無ければ空コミットは作らない。

---

## Self-Review（プラン執筆者チェック・実施済み・grill 反映後）

- **spec カバレッジ**: 決定1（委譲マップ＋外科的 slim）=Task1 表＋Task2 注記 / 決定2（README）=Task1（既存 `## Native Feature Mapping` 表を拡張＝設計の「README 節」を DRY に実現）/ 決定3（session-recovery 注記のみ・他 surface 不変）=Task2。削除なし。検証=Task3。**未カバーなし**。
- **設計からの改善**: 「新節」→「既存 Native Feature Mapping 表の拡張」（重複節回避・grill 要検討5「評価範囲」も表が一意なので自然解消）。grill 要検討1-4（/recover Keep 明示・auto-memory 文言・注記棲み分け・Auto Mode durable 根拠）は Task1/Task2 の文言に反映済み。
- **プレースホルダ**: なし。
- **型/名称整合**: skill 名 `session-recovery`、節名 `## Native Feature Mapping`・`## native との関係`、判断語（Keep/Complement/N/A）一致。
- **コミット健全性**: 各 Task 後に contract/drift green。README は contract 非対象だが full で非回帰確認。

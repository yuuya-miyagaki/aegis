# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-25

## テーマ

- iteration 44（framework・暫定 M）= full-review 2026-06-24 の **C5**:
  `hooks/check-gate.sh` が **ROOT 外**の Edit/Write 対象にも plan-gate を適用し、
  無関係なファイル（auto-memory 等）を false-positive で deny する不具合の修正。

## コンテキスト

- 現在の状況: iter43（task tamper-evidence）完了・push 済（origin/main=93fc166）。
  iter44 は full-review 残課題から C5 を選定（推奨で進めて）。
- きっかけ: 2026-06-24 の本レビュー中、グローバル auto-memory ファイル
  （`~/.claude/projects/.../memory/*.md` ＝ ROOT 外）への Edit が
  `[gate] Plan gate is pending` で deny された **再現済み実バグ**。

## 根本原因

`check-gate.sh` の判定順:
1. docs allowlist（`*/docs/*|docs/*|*.gitkeep`）— auto-memory パスに `/docs/` なし → 非マッチ
2. `is_control_file` — `$ROOT/.claude/*` 等 root-anchored のみ。グローバル `~/.claude/...` は
   別プレフィックスなので非マッチ → control file 扱いされない
3. → mode/plan-gate 判定（line 153）に落ち、Dev × plan=pending で **deny**

plan-gate は「**この project の code** を plan 承認前に編集させない」ための workflow ゲート。
project 外の絶対パスに適用されるのは設計意図外。

## 検討したアプローチ

### アプローチ A: ROOT 外の絶対パスを plan-gate 直前で allow short-circuit（採用）

- 概要: control-file 判定の後・mode/plan-gate 判定の前に、
  `$ROOT/*`・`$ROOT_REAL/*` 以外の絶対パス（`/*`）を `emit_allow` で short-circuit。
  相対パスは従来どおり gate（cwd 不明＝保守的維持）。
- 利点: 最小・局所的。templates/control-file/docs の既存防御を一切弱めない（それらは前段で完結）。
  lexical 判定で既存方針（FS 非アクセス）と一致。
- 欠点: 相対 ROOT 外（`../../external`）は保守的に gate されたまま（auto-memory は絶対なので解消）。
  グローバル `~/.claude/settings.json` も plan pending 時 allow になる（後述・実質保護なし）。

### アプローチ B: plan-gate 条件自体を「ROOT 内対象のみ」に絞る

- 概要: line 153 の deny を「target が ROOT 内のときだけ」に限定する逆向き表現。
- 利点: 機能は A と同等。
- 欠点: 条件が plan-gate 行に埋め込まれ可読性が落ちる。allowlist 群（docs 等）と非対称。

### アプローチ C: docs allowlist を一般化し「project-external → allow」を上流に置く

- 概要: 早い段階で external 全般を allow 分類。
- 利点: 概念的に整理される。
- 欠点: 影響範囲が広く、control-file 判定との順序関係を壊すリスク。YAGNI 違反。

## 決定

- 採用アプローチ: **A**
- 採用理由: 緩和対象を「project 外の非 control 絶対パス」だけに限定でき、
  保護対象（project code・control file・templates・docs）を不変に保てる。差分が小さく検証容易。
- 不採用理由: B=可読性低下／非対称。C=スコープ過大・順序破壊リスク。

## スコープ境界

- やること:
  - `check-gate.sh` に ROOT 外絶対パスの allow short-circuit を 1 箇所追加
  - RED-first の behavioral test を新規追加（temp-root に hook を copy する既存 harness を流用）
- やらないこと:
  - 相対 ROOT 外パスの allow 化（cwd 不明＝保守的 deny を維持）
  - グローバル `~/.claude` 設定の整合性保護（別機能・別 iteration）
  - `check-control-plane.sh`（moat 本体）への変更
  - symlink 偽装の解決（lexical 限界は全フック共通・受容）

## 未解決事項

- なし（size=M は plan で確定。security gate は必須）

## 次のステップ

- [x] 設計ノートを作成する → `docs/specs/2026-06-25-iter44-root-external-plan-gate-design.md`

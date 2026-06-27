# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-28（iteration 51）

## テーマ

- 確認（permission prompt）の交通整理 — **第一スライス: 安全な読み取り/記録系コマンドの自動許可で確認数を削減**

## コンテキスト

- 現在の状況: iter48〜50 が「配布 self-containment／参照整合性 guard」を3連続（treadmill・status_doctor の stuck-in-docs）。内部 hardening（moat→tamper→guard-coverage→threat-model→ref-integrity）は飽和。
- きっかけ: ユーザーの一次情報 ＝「このフレームワークを使っていて**確認がとても多い**。知識の乏しいユーザーには、専門性の深い確認は**そもそも理解できない**」。North Star（知識の乏しい人が AI と堅牢に運用できる足場）を直撃する present-pain。
- grill-premise が当初の dogfood テーマ（仮想ユーザー＝YAGNI）を倒し、この present-pain に再方向付け。

## 検証済みの重要事実（設計の土台・一次確認）

1. **`emit_allow() { printf '{}\n'; }`** — フレームワークの hooks は空オブジェクト `{}` を返すだけで `permissionDecision:"allow"` を出さない。→ hooks は「deny しない」だけで自動承認はしない。**プロンプトを抑制する唯一のレバーは設定の `permissions.allow`**（公式ドキュメントで PreToolUse hook の allow は prompt を抑制すると確認済みだが、本フレームワークは allow を emit していない）。
2. `check-control-plane.sh:767` の `is_allowlisted` は `update-gate.sh`／`record-test-result.py`／`run-test-strength-drill.py` 等を**整合性層で安全**と既に判定（no-chain/no-redirect 条件付き）。ただしこれは deny 回避であってプロンプト抑制ではない（今も prompt する）。
3. `bin/setup.sh:generate_settings()` — **full** は `out = dict(template)`（テンプレ全体を同梱）、**minimal/standard** は `out = filtered`（**hooks ブロックのみ**）。→ テンプレに `permissions` を足しても **filtered では落ちる**＝初心者プロファイルに届かない。
4. 同 merge（line 340-343）は既存ユーザの `permissions` を **wholesale 置換** → 再 install で同梱デフォルトを clobber する。→ **union** が必要。
5. moat の在りか ＝ 会話上のハードゲート＋judge の evidence＋deny/ask hooks。OS の permission プロンプトではない。

## 検討したアプローチ

### アプローチ A: 読み取り専用のみ自動許可（最保守）

- 概要: status/check/test/git-read のみ allow。記録系・状態変更系は全てプロンプト維持。
- 利点: 最小の攻撃面。外部の最保守論に一致。
- 欠点: 記録系（record-test-result 等）は内部前例で安全と判定済みなのに過度に確認を残す。

### アプローチ B: 読み取り＋内部で安全と検証済みの全スクリプト（`update-gate.sh` 含む）

- 概要: `is_allowlisted` 集合をそのまま allow（ゲート承認も自動許可）。
- 利点: 確認数を最大削減。内部前例に忠実。
- 欠点: ゲート承認の自動許可は**外部コンセンサスが無く「設計を裏返す」**（意図的チェックポイントの無音化）。

### アプローチ C（採用）: 読み取り/診断＋純記録系を自動許可、状態変更系はプロンプト維持

- 概要: status_doctor / check_framework_contract / check_status / retro_report / judge カードプレビュー / pytest / git status·log·diff / record-test-result / run-test-strength-drill を**狭い** `Bash(<個別スクリプト>:*)` で allow。`update-gate.sh`／`update-task.sh` はプロンプト維持。
- 利点: 高頻度ノイズの大半を除去／リスト1本でシンプル／内部前例（is_allowlisted）と外部慎重論（ゲートは意図的）の交点／deny-hooks と会話ゲートで moat 保全。
- 欠点: ゲート/サイズの約8プロンプト/イテレーションは残る（許容＝意図的チェックポイント）。

### アプローチ D（保留）: プロファイル別リスト（初心者=寛容／保守者=厳格）

- 不採用理由: YAGNI。C 着地後に残痛があれば見直す。

## 決定

- 採用アプローチ: **C**。
- 採用理由: 「数」の痛みの大半を安全に解消／シンプル（保守可能性）／内部前例と外部ベストプラクティスの両方と整合／moat は deny-hooks＋会話ゲート＋evidence で不変。
- 不採用理由: B=ゲート自動許可はコンセンサス無し・設計反転。A=記録系まで残すのは過度に保守的。D=YAGNI。

## スコープ境界

- やること:
  - 安全コマンドの**狭い** `permissions.allow` を**全プロファイル**に同梱（テンプレ＋`generate_settings()` 修正で filtered にも permissions を carry、既存ユーザ allow と **union**）。
  - deny/ask hooks は無改変＝moat 健在をテストで実証。
- やらないこと:
  - `update-gate.sh`／`update-task.sh` の自動許可。
  - プロファイル別リスト（D）。
  - 残った確認の**平易化**（slice 2）。
  - Edit/Write/MCP のプロンプト削減（別 surface・別スライス）。
  - 「グリル＝担保」の機能化（非決定論ゆえ確認を*置換*しない。確認に*根拠を供給*する形＝slice 2 の有力候補として温存）。

## 未解決事項

- `generate_settings()` の permissions union の正確な実装（重複排除・順序・user 既存との突合）は plan／grill-plan で確定する。

## 次のステップ

- [ ] 設計ノートを作成する → `docs/specs/2026-06-28-permission-prompt-allowlist-design.md`
- テンプレート名: `SPEC.template.md`

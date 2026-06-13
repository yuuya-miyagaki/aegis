# Design: Aegis Model/Effort 継承ポリシー

> 作成日: 2026-06-05 / 対象モデル: Opus 4.8（セッション現行） / 起点: future-proof 再アーキ設計 §5・§10、memory `aegis-rearchitecture-direction.md`
>
> 位置づけ: future-proof 再アーキの後続「哲学変更」フェーズの一つ（model ポリシー）を分割審査として設計。Foundation（emit.sh / patterns.sh / version owner）はマージ済み。本書はその上に乗る agent の `model`/`effort` 方針を確定する。

## 1. 背景と問題

再アーキ設計 §5 は「大半の agent を `model: inherit` にして世代追従＝ゼロ保守」を to-be として掲げたが、同 §5 の事実訂正（Round 1 ④）と R4 が二つのギャップを残していた:

1. **品質保証のギャップ** — review/security/planner は「品質直結ゆえ静かに降格してはならない」役割だが、現状はすべて `inherit`。セッションが安価モデルに落ちると敵対的レビューや脆弱性検査も一緒に降格し、誰も気づかない。
2. **CC 解決順の未確認** — §5/R4 は「env / 起動オプションが frontmatter より強い経路があり inherit だけでは品質保証にならない」とし、model ポリシーを後続フェーズへ先送りしていた。

本書はこの2点を、CC 公式仕様を確認した上で確定させる。

### triage 上の位置づけ

設計の三層振り分け（保証 / 手順 / 揮発値）において、model 選択は**意図的に二層をまたぐ**:

- **既定の `inherit` = 手順（How / 揮発）** — 賢いモデルへ委譲。世代ごとに最適が変わる実装詳細。
- **品質固定（opus）= 保証（What / 不変）** — 「品質ゲートは静かに降格しない」というアウトカム保証。
- **揮発値の隔離** — 系統エイリアスのみを使い、版番号入りモデル id を frontmatter に登場させないことで、隔離用マニフェストを新設せずに達成。

## 2. 確認した CC 公式仕様（事実）

出典: code.claude.com/docs/en/sub-agents.md（claude-code-guide エージェントが実取得・引用）。本ポリシーはこれらの事実に依拠する。

| 項目 | 確認結果 |
| --- | --- |
| `model:` フィールド | 正規サポート。値は系統エイリアス（`opus`/`sonnet`/`haiku`、各系統の現行フラッグシップへ自動解決）／`inherit`（メイン会話と同一・省略時の既定）／版番号入り具体id のいずれも可 |
| `effort:` フィールド | **正規サポート（死に設定ではない）**。稼働中にセッションの effort レベルを上書きする実機能。値: `low`/`medium`/`high`/`xhigh`/`max`。ただし「利用可能レベルはモデル依存」 |
| モデル解決順 | (1) `CLAUDE_CODE_SUBAGENT_MODEL` 環境変数 → (2) per-invocation モデル指定 → (3) **サブエージェント定義ヘッダ `model:`** → (4) メインセッションのモデル |

**含意（重要）**: セッションを `--model haiku` で起動しても、`model: opus` 固定の agent は降格しない（セッションは第4位、固定の第3位より下）。固定を覆せるのは専用の `CLAUDE_CODE_SUBAGENT_MODEL`（＝全サブエージェント一括の意図的上書き）だけ。よって品質固定は「静かなセッション降格を防ぐ」目的に対し、当初想定より強い保証になる。

> この事実により、再アーキ設計 §5/R4 の「env/起動オプションが frontmatter に勝つので inherit だけでは品質保証にならない」という記述は**部分的に不正確**だったと判明（プレーンな `--model` は固定に勝たない）。本書がその点を上書き訂正する。

> **Round 1 反映（2026-06-06）**: 外部レビュー（IDE Chat / Opus 4.6）が公式 docs で解決順と `effort` の正規性を独立確認 → §10-① は P1→P2 に降格。ただし `max`/`xhigh` が現行実機で通るか・存在しない effort 指定時の挙動（エラー/クランプ）は docs だけでは不足。**実装/ship 前 smoke（§11）必須**。

## 3. 確定ポリシー：役割 → (model, effort)

| 階層 | 役割 | `model` | `effort` | 狙い |
| --- | --- | --- | --- | --- |
| **品質固定（保証）** | planner | `opus` | `max` | 設計の深掘り（下流汚染が最も高コスト） |
| | security | `opus` | `max` | 敵対的脅威モデリング（取りこぼし不可） |
| | reviewer | `opus` | `xhigh` | 徹底コードレビュー（QA/ship 前のゲート） |
| | qa | `opus` | `high` | 検証＋証跡収集（機械寄り、max 不要） |
| **コスト固定（下限 sonnet）** | reviewer-testing | `sonnet` | `high` | 並列専門掃引を弱くしない |
| | reviewer-performance | `sonnet` | `high` | 同上 |
| | reviewer-maintainability | `sonnet` | `high` | 同上 |
| | translation-specialist | `sonnet` | `high` | 現状維持 |
| **既定（手順＝委譲）** | implementer | `inherit` | `high` | セッションに追従。継承先で確実な effort |
| | qa-browser | `inherit` | `high` | 同上 |
| | ui | `inherit` | `high` | 同上 |
| | integration-specialist | `inherit` | `high` | 同上 |

`haiku` はどの役割にも使わない（cost-pin の下限は `sonnet`）。

### 設計ルール

1. **値は系統エイリアスか `inherit` のみ。** 版番号入り具体id（`claude-…-4-…`）を frontmatter に書かない。世代交代はエイリアス自動解決で吸収（4.8→4.9 でコード無変更）。
2. **`xhigh`/`max` は opus 固定ロール限定。** `inherit`／`sonnet` ロールは `high` 止まり。理由: 「利用可能レベルはモデル依存」であり、`inherit` は継承先が可変、`sonnet` も上位 effort を持つ保証がない。可用域の確実な範囲に収めて事故を防ぐ。**fallback:** `max` が現行実機で通らない場合は planner/security を `xhigh` に下げる（§11 smoke で確定）。
3. **固定は「既定値の保証」。** プレーンなセッション `--model` 降格には勝つが、`CLAUDE_CODE_SUBAGENT_MODEL` による意図的な全体上書きには従う（人間の明示操作が勝つ）。

## 4. 強制の仕組み（enforcement）

### 4.1 配置

新規テストファイルを作らず、既存 `scripts/check_framework_contract.py` を拡張する。同スクリプトは既に全 agent 定義ヘッダを走査し `model:`/`effort:`/`permissionMode:`/`color:` の**存在**を検証している（現 647 行目近辺）。ここに**値**の検証を追加するのが最小・自然。

frontmatter が CC の唯一の読み取り元（実装）、contract check が検証 ― マニフェストを第3の同期先にしない（Round 1 ②）原則と一致。patterns.sh と同じ思想（真実を消費元に置き、テストで不変条件を検証）。

**検証対象:** root の `.claude/agents/*` と `examples/minimal-project/.claude/agents/*` の両方に同一ポリシーを適用する（Round 1 反映で確定）。

### 4.2 検証する不変条件

- **対応表照合**: §3 の役割→(`model`, `effort`) 表をチェックに埋め込み、各 agent 定義ヘッダの実値と照合。不一致 → FAIL。
- **網羅性**: 12 agent ＝ 品質固定(4) ∪ コスト固定(4) ∪ 既定inherit(4)。集合外の役割が現れたら FAIL（新 agent 追加時に階層決定を強制し、無意識の既定混入を防ぐ）。
- **禁止則 A**: `model: haiku` をどの agent も使わない。
- **禁止則 B**: 版番号入り具体id（正規表現 `claude-[a-z]+-\d`）を使わない（エイリアスか `inherit` のみ）。
- **可用域則**: `xhigh`／`max` は opus 固定ロールのみ。`inherit`／`sonnet` ロールで使用していたら FAIL。

### 4.3 ドリフト区分（設計文書 R7 準拠）

役割→階層は**内部不変条件** ＝ **FAIL（hard stop）**、advisory ではない。役割が階層から外れるのは実回帰。エイリアスの裏の版番号は frontmatter に登場しないため、advisory（外部揮発値）対象は無い。

## 5. 変更面

| ファイル | 変更 |
| --- | --- |
| `.claude/agents/security.md` | `inherit → opus`、`effort: high → max` |
| `.claude/agents/planner.md` | `inherit → opus`、`effort: high → max` |
| `.claude/agents/reviewer.md` | `inherit → opus`、`effort: high → xhigh` |
| `.claude/agents/qa.md` | `inherit → opus`（effort `high` 据え置き） |
| `.claude/agents/reviewer-testing.md` | `haiku → sonnet`、`effort: medium → high` |
| `.claude/agents/reviewer-performance.md` | `haiku → sonnet`、`effort: medium → high` |
| `.claude/agents/reviewer-maintainability.md` | `haiku → sonnet`、`effort: medium → high` |
| `.claude/agents/implementer.md` | 変更なし（`inherit`/`high`） |
| `.claude/agents/qa-browser.md` | 変更なし（`inherit`/`high`） |
| `.claude/agents/ui.md` | 変更なし（`inherit`/`high`） |
| `.claude/agents/integration-specialist.md` | 変更なし（`inherit`/`high`） |
| `.claude/agents/translation-specialist.md` | 変更なし（`sonnet`/`high`） |
| `scripts/check_framework_contract.py` | 値検証（§4.2）を追加 |
| `examples/minimal-project/.claude/agents/*` | §6 の判断に従い本体へ追従 |
| `CLAUDE.md` | 「Model Policy」節を追加（§7） |
| `hooks/session-start.sh` | `CLAUDE_CODE_SUBAGENT_MODEL` 検出時の軽量 advisory を追加（§10.1） |

## 6. example ミラーの扱い

`examples/minimal-project/.claude/agents/` に同名 agent が存在し `effort` も持つ。

**方針: 本体と同じ役割→(model, effort) 値に揃え、contract check は root と example の両方を同一ポリシーで検証する。** 利用者がコピーする雛形なので一貫性を優先（Round 1 反映で確定）。実装計画で example の現値を読み取り、本体と同じ表に合わせる。

## 7. ドキュメント

`CLAUDE.md` に短い「Model Policy」節を1つ追加:

- 役割→階層の一覧（§3 表の要約）
- 固定の意味論（エイリアスのみ・`xhigh`/`max` は opus 限定・固定は既定値の保証で `CLAUDE_CODE_SUBAGENT_MODEL` に従う）

`routing.md` の specialist reviewer 記述（現状 `haiku` 前提の文言があれば）を `sonnet` に整合させる。

## 8. リスク

| # | リスク | 対応 |
| --- | --- | --- |
| R1 | `xhigh`/`max` の opus 可用性が将来変わる | contract check は値集合を許可するだけ。レベルが変わっても frontmatter 修正で吸収。可用域則で `inherit`/`sonnet` への波及は防止済み |
| R2 | 世代交代で固定が陳腐化 | エイリアス自動解決で 4.8→4.9 無変更（本設計の主目的） |
| R3 | `CLAUDE_CODE_SUBAGENT_MODEL` 設定で全固定が一括上書き | 意図的操作なので想定内。`CLAUDE.md` 明記＋`hooks/session-start.sh` 軽量 advisory（§10.1） |
| R4 | 新 agent 追加時に階層未決定のまま既定混入 | 網羅性チェック（§4.2）が集合外を FAIL にし、階層決定を強制 |
| R5 | example ミラーと本体の値ズレ | §6 で本体へ追従。contract check が root と example を同一検証（Round 1 反映） |
| R6 | `max`/`xhigh` が現行実機で未実在/エラー | §11 smoke で確認。不可なら §3 fallback（`xhigh`/`high` へ） |
| R7 | agent frontmatter に `name` 欠落（docs は required） | filename fallback で現状動作・183 緑。§11 で公式挙動を確認、要求なら name 付与を別途（§10-新A） |
| R8 | qa-browser が qa でなく session のモデルに従属 | §10.2 で明記。browser 駆動は機械的で `inherit` 妥当 |

## 9. 完了条件

- [ ] 4 agent を `opus` 固定（security/planner=`max`、reviewer=`xhigh`、qa=`high`）
- [ ] 3 specialist reviewer を `haiku → sonnet`（effort `high`）
- [ ] inherit/sonnet の据え置き role は無変更を確認
- [ ] `check_framework_contract.py` に §4.2 の値検証を追加（対応表照合・網羅性・禁止則 A/B・可用域則）、不変条件違反は FAIL
- [ ] example ミラーを本体へ追従（§6）
- [ ] `CLAUDE.md` に Model Policy 節、`routing.md` の haiku 文言を整合
- [ ] `hooks/session-start.sh` に `CLAUDE_CODE_SUBAGENT_MODEL` 軽量 advisory を追加（§10.1）
- [ ] 既存 183 テスト緑維持＋拡張した contract check 緑（root + example 両方）
- [ ] **ship（push）前に §11 smoke checklist を通過**（保証の実機確認）

## 10. Round 1 セカンドオピニオン反映（2026-06-06）

外部レビュー（IDE Chat / Opus 4.6、同一ワークスペース参照）: **総合判定 条件付き GO**。解決順と `effort` の正規性を公式 docs で独立確認。P1 指摘なし（①は P1→P2）。着手 GO、ただし push/ship は §11 smoke 通過後。

| # | 指摘 | 重大度 | 対応 |
| --- | --- | --- | --- |
| ① | 保証根拠が単一情報源 | P1→P2 | docs で独立確認済み。残る実機事実は §11 smoke で確定 |
| ④ | effort `max` の費用対効果/可用性 | P2 | §3 ルール2 に fallback（`max` 不可なら `xhigh`）明記。§11 で実機確認 |
| ⑦ | `CLAUDE_CODE_SUBAGENT_MODEL` の穴 | P2 | **採用確定**: `CLAUDE.md`（R3）明記＋`hooks/session-start.sh` 軽量 advisory（§10.1） |
| 新A | agent frontmatter に `name` 欠落（docs は required、現状 filename fallback で動作） | P2 | **別パスに分離で確定**（本ポリシー外）。§11 で公式挙動を確認し、CC が name 必須なら別パスを優先実施 |
| 新B | qa→qa-browser のネスト spawn と `inherit` 従属 | P2 | §10.2 に明記 |
| 受 | root と example 両方を同一ポリシーで検証 | — | §4.1・§6・§9 に反映済み |

③（qa 固定が広い）・⑤（haiku 全廃）・⑥（contract check 二重管理）は「許容範囲」判定。**qa=`opus` はユーザー Q3 決定を維持**（コスト最小設計なら qa は `inherit`/`sonnet` も成立、と注記）。

### 10.1 CLAUDE_CODE_SUBAGENT_MODEL advisory（採用・確定）

この env が設定されると security 含む全固定が一括降格する。block は過剰なので採らない。**確定: `CLAUDE.md`（R3）への明記に加え、`hooks/session-start.sh` で env 検出時に軽量 advisory（警告のみ・block しない）を出す。** 意図的上書きは許すが、保証が一括解除されている事実を可視化する。

### 10.2 qa-browser のモデル従属（補足）

qa-browser は `inherit` ＝ **メインセッションに追従**（qa の `opus` ではない）。browser 駆動は機械的作業なので `inherit` で妥当。なお qa.md は qa→qa-browser 委譲を記すが、CC のサブエージェント・ネスト spawn 制限により実際にはメイン orchestrator が起動する可能性がある。これは orchestration の論点で本ポリシー外だが、**qa-browser のモデルが qa でなく session に従う**点をここで明記する。

## 11. 実装/ship 前 smoke checklist（実機確認）

docs だけでは確定できない CC 実機挙動。**ship（push）前に最小再現で確認**し、失敗時は対応を実施:

- [ ] `--model haiku` セッションで `model: opus` の subagent が実際に opus で走る（保証の根幹）
- [ ] `CLAUDE_CODE_SUBAGENT_MODEL=haiku` が本当に全固定を一括上書きする（R3 の前提）
- [ ] `effort: max` / `xhigh` が opus alias で実行可能 → 不可なら planner/security を `xhigh`/`high` に下げる（§3 fallback）
- [ ] 存在しない effort 指定時に CC が fail するか無視/クランプするか（contract check の値集合と整合）
- [ ] `name` 無し project agent が公式に許容される挙動か（許容なら現状維持、要求なら name 付与を別途）

# Aegis Model/Effort 継承ポリシー — Second Opinion Brief (Round 1)

> **位置付け**: フレッシュな設計レビュー（Round 1）。追認ではなく **設計の妥当性を厳しく grill** してほしい。ブレインストーミングで合意済みの方針だが、実装着手前にセカンドオピニオンを通したい。
>
> **レビュアーへの前提**: 同一ワークスペースを参照可能。下記の一次資料を必ず読んでから判定してほしい。
> - 設計書（本ブリーフの対象）: `docs/plans/2026-06-05-v1-model-effort-policy-design.md`
> - 親設計（本書はその §5/§10・R4 を一部訂正する）: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`
> - 現状の agent 定義: `.claude/agents/*.md`（12本）
> - 既存 contract check: `scripts/check_framework_contract.py`（647 行目近辺が agent frontmatter 検証）
>
> **作成日**: 2026-06-05 / **想定モデル**: Opus 4.8（セッション現行）

---

## 0. レビュアーへの依頼

このブリーフの本体は **§4「最も突いてほしい論点」**。私自身が弱点だと考える 7 点を正直に挙げた。各点について:

1. 私の立場が妥当か / 反証はあるか
2. 重大度（P1=設計やり直し級 / P2=要修正 / P3=好みの範囲）の判定
3. 総合判定（GO / 条件付き GO / NO-GO）

を求める。特に **§4-① の「設計の保証根拠が単一情報源の事実主張に依存している」点**を最優先で検証してほしい。新しい観点の追加も歓迎。

---

## 1. 背景と現状

**Aegis** = Ultra Framework v7 を Claude Code ネイティブに落とした受託開発向けハーネス。本ポリシーは future-proof 再アーキの「哲学変更」フェーズの一つ（model ポリシー）を分割審査として確定するもの。Foundation（emit.sh / patterns.sh / version owner）はマージ済み。

**親設計が残したギャップ（本書が解く対象）:**

- 親設計 §5 は「大半の agent を `model: inherit` にして世代追従＝ゼロ保守」を to-be に掲げたが、R4 で「review/security/planner は品質直結ゆえ静かに降格してはならないのに現状すべて inherit」「CC の解決順では env/起動オプションが frontmatter に勝つ経路があり inherit だけでは品質保証にならない（要 docs 確認）」と保留していた。
- 現状の agent は大半が既に `inherit`、specialist reviewer 3本が `haiku`、translation が `sonnet`。

**現状の重要事実（実測）:**

- 12 agent すべてが `model` / `effort` / `permissionMode` / `color` を frontmatter に保持。`check_framework_contract.py` がその**存在**を既にテスト強制（**値**は未検証）。
- `effort` は全 agent に存在（私が当初「reviewer.md は effort 欠落」と誤読したが、13 行目に `effort: high` があった）。
- Foundation 後、183 テスト緑。

---

## 2. ここに至るまでの経緯（ブレインストーミングの意思決定ログ）

| # | 問い | 選択肢 | ユーザー決定 |
| --- | --- | --- | --- |
| Q1 | このポリシーで最優先に解く問題 | A=品質保護の成文化 / B=3層を1つの整合ポリシーに統合 / C=future-proof 優先 | **B（統合ポリシー）** |
| Q2 | 役割→tier をどこに置きどう enforce するか | A=manifestなし・frontmatter(alias)+contract test / B=manifest宣言+check / C=§5フルビジョン(setup codegen) | **A（manifestなし・contract test）** |
| Q3 | quality-pin（opus 固定）にする役割の範囲 | A=reviewer+security+planner / B=reviewer+security のみ / C=+qa | **C（reviewer+security+planner+qa）** |
| Q4 | 「最低 sonnet」の適用範囲（pin=上限という制約下で） | A=明示ピンだけ sonnet 以上・routine は inherit / B=全ロール sonnet 強制 | **A（明示ピンのみ・routine は inherit 維持）** |
| Q5 | effort 方針 | A=段階化(planner/security=max, reviewer=xhigh) / B=xhigh 上限 / C=現状維持 | **A（段階化）** |

**中核思想**: model 選択は triage の二層をまたぐ。既定の `inherit` = **手順（委譲）**、品質固定（opus）= **保証（ゲートは静かに降格しない）**。揮発値（版番号）は frontmatter に登場させない（系統エイリアスのみ）ことで隔離用マニフェストを不要化。

---

## 3. 合意した設計（要約。詳細は一次資料）

**確定ポリシー（役割 → model / effort）:**

| 階層 | 役割 | `model` | `effort` |
| --- | --- | --- | --- |
| 品質固定（保証） | planner | `opus` | `max` |
| | security | `opus` | `max` |
| | reviewer | `opus` | `xhigh` |
| | qa | `opus` | `high` |
| コスト固定（下限 sonnet） | reviewer-testing / performance / maintainability | `sonnet` | `high` |
| | translation-specialist | `sonnet` | `high` |
| 既定（委譲） | implementer / qa-browser / ui / integration-specialist | `inherit` | `high` |

**設計ルール:** ① 値は系統エイリアスか `inherit` のみ（版番号入り id 禁止）。② `xhigh`/`max` は opus 固定ロール限定（`inherit`/`sonnet` は `high` 止まり、可用域がモデル依存のため）。③ 固定は「既定値の保証」で、プレーンな session `--model` 降格には勝つが `CLAUDE_CODE_SUBAGENT_MODEL` には従う。

**enforcement:** 新規テストを作らず `check_framework_contract.py` を拡張し、役割→(model, effort) 対応表の照合・網羅性・禁止則（haiku/版番号id）・可用域則を **FAIL（hard stop）** で検証。`haiku` は全廃。

**依拠する CC 仕様（claude-code-guide が docs から取得）:** `model:` は alias/`inherit`/具体id を受理。`effort:` は正規フィールドで `low/medium/high/xhigh/max`（モデル依存）・session effort を上書き。解決順は (1)`CLAUDE_CODE_SUBAGENT_MODEL` → (2)per-invocation → (3)frontmatter → (4)session。

---

## 4. 最も突いてほしい論点（私が弱点だと考える 7 点）

> 各点に私の暫定立場と暫定重大度を付す。レビュアーはこれを攻撃してほしい。

### ① 【最重要】設計の保証根拠が単一情報源の事実主張に依存 — 暫定 P1

本設計の中核保証「`opus` 固定はセッション降格に勝つ」は、**モデル解決順で frontmatter(第3) > session(第4)** という事実に全面的に依存する。そしてこの事実は **claude-code-guide エージェントが docs を1回引用した結果**のみが根拠。`effort` が正規フィールドである・`xhigh`/`max` が現行 opus で実際に利用可能、も同様に単一取得。

- 私の立場: 公式 docs（code.claude.com/docs/en/sub-agents.md）の引用なので信頼度は高い。だが「保証」を名乗る以上、**実機検証なしに事実へ全賭けするのは弱い**。
- **問い: (a) 解決順 frontmatter>session は現行 CC で本当に成立するか（独立に docs / 実機で再確認できるか）。(b) `CLAUDE_CODE_SUBAGENT_MODEL` 未設定時に `--model haiku` セッションで `model: opus` の subagent が実際に opus で走ることを、実装前に最小再現で確かめるべきか。(c) もしこの前提が崩れたら設計はどう退避するか（フォールバック設計の要否）。**

### ② 親設計 §5/R4 の結論を上書き訂正してよいか — 暫定 P1/P2

本書は親設計 R4 の「env/起動オプションが frontmatter に勝つので inherit だけでは品質保証にならない」を「**部分的に不正確（プレーンな --model は固定に勝たない）**」と訂正している。R4 は前回のセカンドオピニオン（Opus 4.6）が出した P2 指摘。

- 私の立場: §① の事実が正なら R4 の前提は確かに不正確で、訂正は妥当。
- **問い: 前回レビューの結論を覆す訂正として、根拠は十分か。R4 が言っていた「env が勝つ経路」は `CLAUDE_CODE_SUBAGENT_MODEL` のことで、本書はそれを別途認めている — つまり R4 と本書は矛盾せず粒度が違うだけ、という整理で正しいか。**

### ③ quality-pin を4ロールに広げたのは過剰固定では — 暫定 P2

Q3 で reviewer+security+planner **+qa** まで opus 固定とした。inherit-first の「例外は最小」という原則に照らすと広い。特に **qa は証跡収集寄り**で、planner は下流の review で誤りを拾える。

- 私の立場: ユーザーは品質重視で広い集合を選択。固定は既定であり env 上書きの余地は残る（コスト懸念は限定的）。
- **問い: qa / planner の opus 固定は便益が固定コストに見合うか。最小集合 {reviewer, security} に絞り、planner/qa は inherit にすべきという反論は成立するか。**

### ④ effort `max` の費用対効果と可用性 — 暫定 P2

planner/security に `max`、reviewer に `xhigh` を割当てた。だが **`max` が `xhigh` を上回る品質を出す実証は無い**（トークン/遅延だけ増える可能性）。また docs は「利用可能レベルはモデル依存」と書くのみで、**現行 opus(4.8) で `max`/`xhigh` が実在するかは未確認**。

- 私の立場: 発火頻度が低い高レバレッジ役割なのでコスト増は局所的。可用域則で `inherit`/`sonnet` への波及は防いだ。
- **問い: (a) `max` は過剰で `xhigh` 上限（Q5 案B）が妥当では。(b) 現行 opus の effort 実在レベルを実装前に確認すべきか。(c) 存在しないレベルを指定した時 CC はエラーかクランプか（要確認）。**

### ⑤ haiku 全廃→sonnet 下限のコスト判断 — 暫定 P2/P3

specialist reviewer 3本を `haiku → sonnet`・effort も `medium → high` に上げた（ユーザー要望「haiku 使いたくない」）。並列専門掃引は本来「狭い機械的チェック」で haiku で足りる設計だった（README/旧 v060 report が haiku 前提）。

- 私の立場: レビューは敵対的品質チェックで、下限 sonnet は妥当。並列3本×sonnet×high のコスト増は限定的。
- **問い: 下限 sonnet は正当化されるか。それとも狭い機械チェックは haiku で十分で、コスト退行か。effort も medium→high に上げる必要があったか。**

### ⑥ enforcement を contract check に焼くのは「第3の同期先」の別名では — 暫定 P2

Q2 で「manifest を作らず frontmatter を真実、test で検証」とした。だが役割→tier 対応表は **frontmatter（実体）と test（期待値）の二箇所**に現れる。これは Round 1 ② が嫌った「同期先が増える」状態の小型版では。

- 私の立場: test は「真実の複製」でなく「不変条件の検証器」（patterns.sh をテストが検証するのと同じ構図）。frontmatter が唯一の source、test は assertion。
- **問い: この整理（source は frontmatter のみ・test は検証器）は妥当か。それとも対応表が test 内にハードコードされる時点で二重管理で、ズレた時に「どちらが正か」が曖昧にならないか。**

### ⑦ `CLAUDE_CODE_SUBAGENT_MODEL` による一括上書きの穴 — 暫定 P2/P3

固定は `CLAUDE_CODE_SUBAGENT_MODEL` 設定時に**全 agent 一括で**上書きされる。利用者が「全部安く回す」目的でこの env を haiku 等に設定すると、**security も haiku に降格**するが、本設計の防御は「CLAUDE.md に明記」だけ。

- 私の立場: これは意図的操作であり、人間の明示指定が勝つのは正しい挙動。hook で縛るのは過剰。
- **問い: ドキュメント明記で十分か。それとも security/その他ゲート稼働時にこの env を検出して警告する hook を足すべきか（保証の徹底 vs 過剰防御のトレードオフ）。**

---

## 5. 参考資料

- 設計書（対象）: `docs/plans/2026-06-05-v1-model-effort-policy-design.md`
- 親設計: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`（§5・§10・R4）
- 旧計画（effort 段階化の前例）: `docs/plans/v0130-modernization-plan.md`（planner=max/security=max/reviewer=xhigh/specialist haiku→sonnet を既に提案）
- 現状 agent: `.claude/agents/*.md`（12本）/ example ミラー `examples/minimal-project/.claude/agents/*`
- 既存 contract check: `scripts/check_framework_contract.py`（647 行目近辺）
- README design philosophy（haiku 前提の specialist 記述の有無を確認）
- CC 公式 docs（要再確認）: [Subagents](https://code.claude.com/docs/en/sub-agents)（frontmatter フィールド・model 値・effort 値・解決順）

---

## 6. レビュアー返答テンプレート

```markdown
## 総合判定: [GO / 条件付き GO / NO-GO]

## §4 各論点への判定
- ① 保証根拠が単一情報源: [立場妥当 / 反証あり] 重大度[P1/P2/P3] — コメント:
- ② 親設計 R4 の上書き訂正の妥当性: [...] [P1/P2/P3] —
- ③ quality-pin 4ロールは過剰固定か: [...] [P1/P2/P3] —
- ④ effort max の費用対効果と可用性: [...] [P1/P2/P3] —
- ⑤ haiku 全廃→sonnet 下限のコスト: [...] [P1/P2/P3] —
- ⑥ contract check は第3同期先か: [...] [P1/P2/P3] —
- ⑦ CLAUDE_CODE_SUBAGENT_MODEL の穴: [...] [P1/P2/P3] —

## 実装前に実機/再確認すべき事実（§4-① ④ 関連）
<自由記述: 解決順・effort 可用レベル・存在しないレベル指定時の挙動 等>

## 新規論点（私が見落としているもの）
<自由記述>

## 最小改修案（NO-GO/条件付きの場合、何を変えれば GO か）
<自由記述>

## 実装着手の可否
[着手 GO / 先に再検討すべき点あり]
```

# Aegis v1.0.0 Re-architecture — Second Opinion Brief (Round 1)

> **位置付け**: フレッシュな設計レビュー（Round 1）。追認ではなく **設計の妥当性を厳しく grill** してほしい。ブレインストーミングで合意済みの方針だが、実装着手前にセカンドオピニオンを通したい。
>
> **レビュアーへの前提**: 同一ワークスペースを参照可能。下記2つの一次資料を必ず読んでから判定してほしい。
> - 設計書: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`
> - Phase F 実装計画（完全コード付き）: `docs/plans/2026-06-05-v1-phase-f-foundation.md`
>
> **作成日**: 2026-06-05 / **想定モデル**: Opus 4.8（セッション現行）

---

## 0. レビュアーへの依頼

このブリーフの本体は **§4「最も突いてほしい論点」**。そこに私自身が弱点だと考える 9 点を正直に挙げた。各点について:

1. 私の立場が妥当か / 反証はあるか
2. 重大度（P1=設計やり直し級 / P2=要修正 / P3=好みの範囲）の判定
3. 総合判定（GO / 条件付き GO / NO-GO）と、特に **「そもそも再アーキテクチャ（v1.0.0）に踏み込むべきか、既存 v0.13.0 を完遂すべきか」**（§4-①）への意見

を求める。新しい観点の追加も歓迎。

---

## 1. 背景と現状

**Aegis** = Ultra Framework v7 を Claude Code ネイティブに落とした受託開発向けハーネス。Client/Dev の2モード状態機械、hard gate（ユーザー承認）、evidence-based completion、hook による Policy-as-Code 強制が柱。

**現状の重要事実:**
- v0.12.2 ship 済み（全 hook が CC 公式出力スキーマ準拠）。
- v0.13.0 が **Phase 0b 途中**。ただし STATUS.md は実態より遅れており、**Phase 0b の新 hook（check-skill-gate / check-cron-gate / check-task-created / check-task-completed）は既にファイルが存在**している（= 計画ナラティブより実装が先行）。
- 既存の `docs/plans/v0130-modernization-plan.md`（40KB・5ラウンドレビュー済み）は **2026-05-03 / Opus 4.7・Sonnet 4.6・Haiku 4.5 前提**で書かれている。今日は 2026-06-05、ユーザーは **Opus 4.8**。

**ユーザーの要求（原文ニュアンス）:** 「Opus 4.8 になってハーネスが古い。全力で調べて改善し、**将来モデルが進化しても使えるもの**にしたい。大改善になる。」

---

## 2. ここに至るまでの経緯（ブレインストーミングの意思決定ログ）

| # | 問い | 選択肢 | ユーザー決定 |
|---|---|---|---|
| Q1 | 既存 v0.13.0（途中まで実装済み）をどう扱うか | A=catch-up 優先 / B=re-architecture 優先 / C=統合 | **B（再アーキ優先、正しい部分は再利用）** |
| Q2 | Opus 4.8+1M 時代に「厳格さ」をどうするか | A=厳格維持しモデル非依存化 / B=大胆軽量化 / C=ハイブリッド | **A+C 統合案（私の推奨）** |
| Q3 | 「保証は決定論的強制／手順はモデルに委ねる／揮発値は manifest に隔離」原則 | 合意するか | **合意** |
| Q4a | TDD 強制（check-tdd.sh）は KEEP か DELEGATE か | — | **KEEP（保証）。ただし backstop 化 + manifest profile 値（strict/advisory/off）** |
| Q4b | context 予算の固定数値（L0-L3・同時3doc） | — | **数値撤廃・原則維持・soft budget は manifest 助言値** |

**中核思想（Q2-Q3 で確立）**: Aegis の設計思想を2層に分解する。
- **保証（What/不変）** = hard gate・evidence・破壊コマンド承認・secrets・handover → **hook で決定論的に強制（維持/強化）**
- **手順（How/揮発）** = どのモデル・effort・context 量・どの subagent・routing 細則 → **賢い 4.8 に委ねる**
- **揮発値（Platform 固有）** = モデル名・CC hook スキーマ・ツール名・version → **1枚の manifest に隔離**

---

## 3. 合意した設計（要約。詳細は一次資料）

**triage（現状要素の3層振り分け）**: KEEP=破壊/secrets/deploy/gate/STATUS改竄/evidence/handover/TDD（backstop化）。DELEGATE=context予算数値/routing細則/effort個別割当/冗長always-on。ISOLATE=モデル名/effort値/CC hookスキーマJSON形/ツール名/version。

**ADD（future-proof の3点セット）**:
1. `aegis.manifest.json`（揮発真実源）
2. `hooks/lib/emit.sh`（hook 出力スキーマを1関数群に集約。各 hook の手書き `printf '{...}'` を全廃）
3. drift detector 拡張（manifest↔lib↔実環境のズレを advisory 警告）

**model の future-proof（CC 実行時制約への対応）**: CC は agent の model/effort を frontmatter から直読し manifest を自動参照しない。よって **大半の agent を `model: inherit`**（セッション現行モデルへ自動追従＝ゼロ保守）、意図的に別モデルにする少数だけ manifest 宣言 + setup 同期。

**移行戦略 F→R→A→D**: F=土台（挙動不変、134テスト緑維持）→ R=triage 適用 → A=v0.13.0 catch-up を新方式で吸収 → D=仕上げ + version **v1.0.0** bump。

---

## 4. 最も突いてほしい論点（私が弱点だと考える 9 点）

> 各点に私の暫定立場と暫定重大度を付す。レビュアーはこれを攻撃してほしい。

### ① 【最重要】そもそも再アーキ（B）は YAGNI ではないか — 暫定 P1
既存の v0.13.0 は5ラウンドレビュー済みで動いており、drift check も既にある。「トレッドミルから降りる」は哲学的に魅力的だが、**実利は v0.13.0 完遂で足りるのでは?** v1.0.0 への格上げは過剰投資（ゴールドプレーティング）の疑い。
- 私の立場: emit.sh による「次回スキーマ変更=1ファイル修正」は実利が明確（v0.12.2 で12ファイル一斉書き換えの実害があった）。だが manifest と inherit 化の実利は弱い可能性あり（②③参照）。
- **問い: 再アーキの正味便益は投資に見合うか。Bの一部だけ（emit.sh のみ）採用して残りは v0.13.0 完遂、が最適解では?**

### ② manifest は本当に保守を減らすか、第3の同期先を増やすだけか — 暫定 P1
CC は manifest を runtime 参照しない。emit.sh も patterns.sh も値を**ハードコードし、manifest とは drift 検出で「同期確認」するだけ**。つまり manifest は runtime config ではなく「宣言 + drift ターゲット」。
- 私の立場: 価値は (a) ドキュメント/オンボーディング (b) drift 検出の基準 (c) profile 化できる少数（enforcement.tdd 等）。emit.sh/patterns.sh の集約自体は manifest 無しでも成立する。
- **問い: manifest はその重量に見合うか。むしろ「同期すべき場所が hook + patterns.sh + manifest の3つ」に増えて保守が増えないか? manifest を廃し emit.sh/patterns.sh だけにすべきでは?**

### ③ 【堅牢性の懸念】emit.sh の deny パスが python3 依存になる — 暫定 P1
現行 hook は deny を `printf`（常に成功）で出力。新 emit.sh は escaping のため **deny/block/context/continue_false を python3 で生成**。
- 懸念: python3 が無い/遅い環境で、**セキュリティ上最重要の deny が無音失敗**（出力ゼロ→ブロック不発）するリスク。allow（hot path）は printf のままだが、deny がフォールバック無しで python3 単一依存になるのは現行比で堅牢性後退では。
- 私の立場: python3 は既に extract-input.sh で使用済み（ただしそちらは bash 主・python フォールバック）。今回は deny で python 主。
- **問い: これは許容範囲か。pure-bash の JSON escaping フォールバックを emit.sh に持たせるべきか（複雑化とのトレードオフ）。それとも python3 を hard 依存と明記し setup で存在検査すべきか?**

### ④ inherit-first は review/security の品質を session モデルに従属させる — 暫定 P2
大半 agent を `model: inherit` にすると、安いモデル（haiku）でセッションした時に reviewer/security も haiku に落ちる。設計では review/security を opus 明示オーバーライドで守る、としているが。
- **問い: 「品質に直結する役割は明示固定、それ以外 inherit」の線引きは妥当か。inherit は CC の現行仕様で想定通り動くか（要 docs 確認）。安いセッションでの品質劣化を許容する設計でよいか?**

### ⑤ context 予算の数値撤廃は「低トークン浪費」という中核価値の後退では — 暫定 P2
README の design philosophy は「Low token waste」を売りにしている。固定数値（同時3doc）を撤廃しモデルに委ねると、**強制が無くなる＝保証が消える**。受託（コスト直結）で、4.8 が実際に薄く保つ保証は?
- 私の立場: 1M context で「文脈希釈」の失敗は弱まった。だが「コスト」の観点は別問題で残る。soft budget(manifest 助言値)は強制力ゼロ。
- **問い: 数値撤廃はコスト面で退行か。原則だけで実運用上 thin が保てるか、それとも soft budget を「助言」でなく「警告 hook（PostToolUse で doc 数を数える等）」にすべきか?**

### ⑥ TDD の profile 化（strict/advisory/off）は規律の蟻の一穴では — 暫定 P2/P3
backstop 化 + profile 値は柔軟だが、`off`/`advisory` が常用されると TDD 文化が形骸化する恐れ。
- **問い: profile に `off` を持たせるべきか。受託=既定 strict で十分で、`off` は不要（プロトタイプも advisory 止まり）にすべきか?**

### ⑦ drift detector が advisory のままだと誰も直さない — 暫定 P2
警告は無視されがち。「いつ advisory→enforce（FAIL）に昇格するか」の基準が設計に無い。
- **問い: 昇格条件を設計に明記すべきか（例: 1リリース advisory 運用→次で FAIL 化）。それとも永続 advisory で十分か?**

### ⑧ Phase F のみ計画し R/A/D を後回しにする判断 — 暫定 P2/P3
F は挙動不変で安全だが、R/A/D の要件を知らずに F の manifest スキーマを確定すると手戻りリスク。
- **問い: manifest スキーマは R/A/D を見越して十分か（例: routing/effort policy・schedule 連携・スキル改名マップ等の欄が将来必要にならないか）。F 着手前に R/A/D の骨子だけでも固めるべきか?**

### ⑨ STATUS.md と実態の drift（Phase 0b hook 既存） — 暫定 P3
STATUS は「Phase 0b 未着手」だが実際は新 hook が存在。再アーキの「A: catch-up 吸収」は一部すでに済み。
- **問い: 着手前に STATUS.md を実態へ同期し、v0.13.0 のどこまでが実装済みかを棚卸しすべきか（A フェーズのスコープ確定のため）?**

---

## 5. 参考資料

- 設計書: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`
- Phase F 実装計画（完全コード）: `docs/plans/2026-06-05-v1-phase-f-foundation.md`
- 旧計画（吸収対象）: `docs/plans/v0130-modernization-plan.md`（Rev.5）
- 現状: `CLAUDE.md` / `docs/STATUS.md`（framework_version 0.13.0-pre, phase=implement）/ `README.md`（design philosophy）
- 既存 hook 群: `hooks/*.sh`（16本）/ `hooks/lib/extract-input.sh` / `tests/test_hook_output_schema.py`（134テスト）
- 既存 drift: `scripts/check_reference_drift.py`（10 チェック）
- CC 公式 docs（要再確認・前回検証 2026-05-03）: [Skills](https://code.claude.com/docs/en/skills) / [Hooks](https://code.claude.com/docs/en/hooks) / [Subagents](https://code.claude.com/docs/en/sub-agents)

---

## 6. レビュアー返答テンプレート

```markdown
## 総合判定: [GO / 条件付き GO / NO-GO]

## §4 各論点への判定
- ① 再アーキは YAGNI か: [立場妥当 / 反証あり] 重大度[P1/P2/P3] — コメント:
- ② manifest は保守を減らすか: [...] [P1/P2/P3] —
- ③ emit.sh の python3 deny 依存: [...] [P1/P2/P3] —
- ④ inherit-first の品質従属: [...] [P1/P2/P3] —
- ⑤ context 数値撤廃のコスト退行: [...] [P1/P2/P3] —
- ⑥ TDD profile 化の形骸化: [...] [P1/P2/P3] —
- ⑦ drift advisory の放置: [...] [P1/P2/P3] —
- ⑧ Phase F 先行の手戻り: [...] [P1/P2/P3] —
- ⑨ STATUS 実態 drift: [...] [P1/P2/P3] —

## 新規論点（私が見落としているもの）
<自由記述>

## 最小改修案（NO-GO/条件付きの場合、何を変えれば GO か）
<自由記述>

## Phase F 着手の可否
[着手 GO / 先に再検討すべき点あり]
```

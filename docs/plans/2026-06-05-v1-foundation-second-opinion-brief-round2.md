# Aegis Foundation — Second Opinion Brief (Round 2 / 確認)

> **位置付け**: Round 2 = **確認**。Round 1（NO-GO for 全面 v1.0.0 / 条件付き GO for 縮約 Foundation）の P1/P2 指摘が改訂版に正しく反映されたかを確認してほしい。本質的な設計判断は Round 1 で決着済み。新規の大きな設計判断は無い。
>
> **レビュアーへの前提**: 同一ワークスペース参照可。改訂後の一次資料（§4）を読んでから判定してほしい。Round 1 の私の応答（このブリーフ §1 の「対応」列）も確認対象。
>
> **作成日**: 2026-06-05 / **想定モデル**: Opus 4.8

---

## 0. レビュアーへの依頼

1. **§1**: Round 1 の P1×3 + P2×6 + 新規3件への対応が、改訂版の該当ファイル/箇所に**正しく反映**されているか
2. **§2**: 唯一レビュー提案と**異なる対応**をした ③（pure-bash 化）が妥当か（提案2案より良い解と判断した根拠の是非）
3. **§3**: 私が判定を仰ぎたい **2つの judgment call**（seed manifest を Foundation に含める是非 / pure-bash escaping の網羅範囲）
4. **F0 着手の最終可否**（GO / 条件付き GO / NO-GO）

---

## 1. Round 1 指摘 → 対応マップ

| # | Round 1 指摘 | 重大度 | 対応 | 反映先 |
|---|---|---|---|---|
| ① | 全面 B は YAGNI、emit.sh だけ実利強 | P1 | 全面再アーキ撤回。Foundation のみに縮約（F0/F1/F2） | foundation plan 冒頭 / design 冒頭バナー・§9 |
| ② | manifest は declarative mirror=第3同期先 | P1 | **patterns/schema を manifest にミラーしない**。manifest は version + 外部揮発事実だけの最小シード。patterns.sh / emit.sh が単一真実 | foundation F2-1/F2-2 / design §4 注記 |
| ③ | emit.sh の deny が python3 依存=fail-open | P1 | **pure-bash 実装（subprocess ゼロ）**。手書き escape を `_aegis_json_escape`（bash param 展開）に統一 | foundation F1-1（§2 で詳述） |
| ④ | inherit 従属、設計文「override 維持」は実体と不一致 | P2 | model ポリシーを Foundation スコープ外へ。design §5/§8 を**事実訂正**（現状 planner/reviewer/security は inherit） | design §5 訂正注・§8 R4 |
| ⑤ | context 数値撤廃はコスト価値後退 | P2 | hard block でなく observability（Read 回数・doc サイズ計測）へ。Foundation スコープ外 | foundation 「スコープ外」節 / design §10 |
| ⑥ | TDD `off` の形骸化 | P2/P3 | `off` は minimal/local の escape hatch のみ、標準は strict | foundation スコープ外節 / design §10 |
| ⑦ | drift advisory 放置 | P2 | 昇格基準明記: **内部値（version/flagship）=FAIL / 外部揮発（model lineup・schema 日付）=advisory 継続** | foundation F2-3 docstring |
| ⑧ | Phase F の manifest schema が広すぎ | P2 | 最小シード（version + models のみ）。role_defaults/enforcement/profiles/security_patterns は消費者が出来てから（YAGNI） | foundation F2-2 + test_minimal_keys_only |
| ⑨ | STATUS 実態 drift（Phase 0b hook 既存） | P2 | **F0 で棚卸し最優先**（実装済み/未済を記録、A の二重計上防止） | foundation F0-1 |
| 新1 | pytest 前提誤り（本環境 unittest のみ） | — | 全テストコマンドを `python3 -m unittest` に統一 | foundation 全 Step |
| 新2 | test 数 134→174 | — | 全箇所 174 に訂正、完了条件は 189（174+15新規） | foundation 全体 / design §7 訂正 |
| 新3 | version 割れ（contract 0.12.0 / STATUS 0.13.0-pre） | — | **owner = `FRAMEWORK_VERSION`**（最後の ship 版）、STATUS=作業中版。F0-2 で 0.12.0→0.12.2 修正、manifest も owner に一致 | foundation F0-2 / F2-2 |

---

## 2. レビュー提案と異なる対応（③のみ）— 是非を確認してほしい

Round 1 ③ への提案は2案だった:
- (a) python3 不在時 fail-closed（PreToolUse stderr + exit 2）
- (b) setup で hard dependency 検査 + missing-python テスト

**私の対応**: どちらも採らず、**emit.sh から python3 依存自体を消す（pure-bash 化）**。

根拠:
- (a) は「依存は残すが落ち方を制御」、(b) は「依存を必須と明示」。いずれも **python3 依存を残す**。
- pure-bash 化は依存を**消す**ので、fail-open リスクが構造的に消滅し、deny/block 1回ごとの subprocess レイテンシ（Round 1 で別途懸念した点）も消える。
- escape は bash パラメータ展開で `\` `"` 改行 タブ CR を処理（`_aegis_json_escape`）。bash 3.2（macOS 既定）互換。
- fail-closed の**証明テスト**を2つ追加: (i) emit.sh に `python3`/`jq` 文字列が無いことの静的検査 (ii) 最小 PATH（`/usr/bin:/bin`）でも `emit_deny` が valid な blocking JSON を出すこと。

**確認依頼**: この「依存を消す」判断は (a)/(b) より優れているか。見落としはないか（特に §3-2 の escaping 網羅）。

---

## 3. 私が判定を仰ぎたい 2つの judgment call

### J-1: seed manifest を Foundation に含めるべきか、完全に後回しか
②⑧ を受け manifest は version + model lineup だけの最小シードに縮約した。だが厳密には Foundation 内の**唯一の消費者は drift チェック（manifest.version == FRAMEWORK_VERSION）**で、これは owner を二度書いて一致確認するだけとも言える（便益が薄い）。
- 私の lean: **最小シードを今作る**（ファイルと drift 習慣を早期に確立、後続フェーズの land 先が出来る）。
- 対立案: **manifest は Foundation では作らず、最初の実消費者（R の enforcement.tdd 等）が出来た時に新設**（純 YAGNI）。
- **問い: どちらが筋か。シードの「version 二重書き」は無駄か、それとも早期確立の価値が勝るか?**

### J-2: pure-bash escaping の網羅範囲は十分か
`_aegis_json_escape` は `\` `"` 改行 タブ CR を処理し、**生の制御文字（NUL や 0x01-0x08 等）は対象外**。reason 文字列は開発者が書くメッセージ（ユーザー入力ではない）なので制御文字混入は想定しない、という前提。
- **問い: この前提でよいか。reason に外部由来文字列（ファイルパス・コマンド断片など）が混じる経路があり、そこに制御文字や未対応文字が来て JSON が壊れる懸念はないか?** （例: `check-secrets.sh` は git コマンド断片を reason に含めうる。ただし現状も同じ断片を使っており、旧実装は `"` のみ escape だったので pure-bash の方が網羅は広い。）

---

## 4. 改訂後の一次資料

- **確定版 Foundation 実装計画（F0/F1/F2、完全コード）**: `docs/plans/2026-06-05-v1-phase-f-foundation.md`
- 全体ビジョン設計書（Round 1 反映済み・§10 に対応表）: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`
- Round 1 ブリーフ（私が送った原本）: `docs/plans/2026-06-05-v1-rearchitecture-second-opinion-brief.md`
- 実測: `python3 -m unittest discover -s tests -v` → **174 tests PASS**（pytest 未導入）
- 現状: `scripts/check_framework_contract.py`（FRAMEWORK_VERSION=0.12.0→F0で0.12.2へ）/ `docs/STATUS.md`（0.13.0-pre）/ `hooks/lib/extract-input.sh`（python3 fallback 有、F スコープ外）

---

## 5. レビュアー返答テンプレート

```markdown
## Round 2 判定: [GO / 条件付き GO / NO-GO]

## §1 Round 1 指摘の反映確認
- ① 縮約: [反映済み / 不足]
- ② manifest 非ミラー: [反映済み / 不足]
- ③ pure-bash: [反映済み / 不足]  ← §2 の是非も記入
- ④ inherit 訂正: [反映済み / 不足]
- ⑤ context observability: [反映済み / 不足]
- ⑥ TDD off 隔離: [反映済み / 不足]
- ⑦ drift 昇格基準: [反映済み / 不足]
- ⑧ manifest 最小化: [反映済み / 不足]
- ⑨ STATUS 棚卸し F0: [反映済み / 不足]
- 新1-3（unittest / 174 / version owner）: [反映済み / 不足]

## §2 ③ pure-bash 化の是非
[(a)/(b)より優 / どちらでもよい / 問題あり] — 根拠:

## §3 judgment call
- J-1 seed manifest: [今作る / 後回し] — 理由:
- J-2 escaping 網羅: [十分 / 要拡張] — 要拡張なら対象文字:

## 新たに気づいた点（あれば）
<自由記述>

## F0 着手の可否
[着手 GO / 先に直す点あり]
```

# Aegis 簡素化 — 設計書（決定の正典）

> 2026-06-20 作成・ユーザー承認済み。`brainstorm` フェーズの成果。
> 実装計画は `writing-plans` で別途作成し、本書を §チェックリストの正典とする。
> 引き継ぎ: `docs/plans/2026-06-20-aegis-simplification-handoff.md` / second-opinion 依頼書: 同 `-second-opinion-brief.md`。

## 1. 背景・目的

「thin operating model」を掲げる Aegis が、実体は self-consistency 機械（部品同士の整合検証）と
配布前の先行投資（examples ミラー）に肥大した。total の目安は framework 約15k行＋tests 約15k行＋
docs 約39k行＋examples ミラー約11k行。North Star に立ち返り、**過剰・不要・妨げ**を棚卸しして
削減・統合する。

## 2. North Star（不変の到達保証）

> **知識の無い人でも、Aegis に従って進むだけで、クライアント課題を *上流の設計（ゴール設計・
> ロジック構造・要件の抜け漏れ拾い）→ 下流の実装 → 運用後の改善* まで解決しきれる。
> ハーネスに導かれていること自体が正しいゴール到達になる。**

- **操作的バー**: あるステップが*人間に dev/運用の知識を要求する*なら、それは「ハーネスの穴」。
  「プロと同等」＝*人間が*プロになることではなく、*成果が*プロ級に届くこと。
- **配布モデル（消費者モデル P 寄り）**: end user は*封印された* Aegis を消費する（内部を編集
  しない）。保守は作者＋AI（将来は AI 自身）。→ **内部の複雑さは「ユーザーから封印され、AI が
  保守できる」限り許容**。利用者に露出する*表層*の複雑さは不可。
- **LLM進化レンズ**: LLM が賢くなるほどハーネスは*薄く*できる（目標は不変）。「進化したら足場を
  減らす」が North Star 準拠＝簡素化の追い風。
- 看板は「**LLM を制御するハーネス**」。その下に B（検証・信頼）/ C（進行管理）/ A（ガードレール・
  土台）がぶら下がり、頂点に D（知識代替）が立つ入れ子。A は手段の1つであって看板ではない。

## 3. 親基準（master cut-line）

> その機構が壊れて検知に失敗したとき、**知識の乏しいユーザーが静かに騙される × 他に安全網が
> 無い** か?
> - **Yes →** ユーザー保護なので*機能する最も薄い形で*残す。
> - **No（作者のミスを捕まえるだけ／他チェックと重複）→** 削る・統合する。

## 4. 判定（5件）

| # | 対象 | 判定 | 守る相手 / 理由 |
|---|------|------|----------------|
| 2 | test-strength-drill | **keep-thin** | end user。テストの*弱さ*を検出する唯一の手段で代替なし。framework タスクで skip するのは構造的縁ケースで、ターゲット用途（未コミットのプロダクトコード）では機能する＝「過剰」は誤診。 |
| 4 | observation/fingerprint hooks | **rebuild** | end user。AI の自己申告でなく*観測実行*でゲート判定＝代替なし＝機能は必須。ただし保証はゲート時にあるのに全 Bash コマンドで fingerprint 計算を払うのは無駄。テストランナー検出時／ゲート時の遅延計算へ寄せる。重いハーネスは hook 無効化を招く二次被害もある。 |
| 3 | skill_behavior_manifest（層1）＋ skill-pressure-drill（層2） | **cut／AI委譲** | 作者のみ。配布先では走らない（封印側）。層1: 自認の限界「同コミットで素通り＝壁でなく速度バンプ」・14トークン手動表は進化で*厚く*なる方向で North Star と逆・腐っても緑＝false assurance。層2(extensions/skill-pressure-drill): grill 由来で追加 cut＝作成以来一度も実走せず・唯一の自動部分は雛形の体裁検査(QA シアター)・WORKFLOW 自認で無意味化しやすい・他 skill 変更で壊れる地雷。要求（skill が機能し続ける）は git diff＋編集時 AI レビュー／必要時に subagent 即席で委譲。 |
| 1 | examples/minimal-project ミラー | **廃止（抽出→撤去）** | 作者のみ・配布前の先行投資。byte 完全コピー（99ファイル/約11k行）＋同期/drift/contract 機械（drift 6/15・contract 81参照・専用テスト5本）。ミラーがズレてもユーザーは騙されない。唯一 `bin/setup.sh` が scaffold-safe な `validate.md`/`retro.md`(/settings.json) を examples/ から読む runtime 依存があるため、**先に `templates/` へ抽出してから撤去**。 |
| 5 | docs 膨張 | **整理・統合** | 履歴は git に残す。203ファイル/約39.6k行のうち `docs/archive/` が74%（132ファイル/約29.3k行）。ユーザーを導く doc は残し磨く、作者の履歴・簿記は作業ツリーから外す。 |

### 守る核（North Star 直結・触らない）
薄い `CLAUDE.md` kernel・`STATUS.md`・pull-based skills・hooks/gates/moat の*基本形*・onboarding・
templates。M2/M4 の*保証*は維持（M4 は実装だけ作り替え）。難読化 moat（round8-11）は「今後足さない」
方針で対応済み（既存分の取り除きは優先度低・本簡素化のスコープ外）。

## 5. 実装順序とリスク（小さく1つずつ・暴走しない）

1. **M3 cut** — 独立・最小・低リスク。層1: `skill_behavior_manifest.py` 撤去＋`check_reference_drift.py`
   の該当チェック＋`tests/test_skill_behavior_contract.py` を除去。層2(grill 由来追加): `extensions/skill-pressure-drill/`＋`tests/test_skill_drill_format.py` を撤去（コード参照ゼロを実証済み）。
2. **examples 廃止** — ① `validate.md`/`retro.md`(/settings.json テンプレ) を正規 `templates/` へ
   抽出し `bin/setup.sh` の参照を切替 → ② ミラー本体＋`sync_example_mirror.py`＋`check_mirror_identity`＋
   contract の `REQUIRED_EXAMPLE_FILES`＋ミラー専用テストを撤去。installed-project 検証は**薄い
   scaffold テンプレ＋小さな smoke テスト**に置換。**本簡素化で唯一 blast radius が大きい工程＝要注意**。
3. **docs 整理** — `docs/archive/` を作業ツリーから撤去（git 履歴で保全）／ルート簿記の整理／完了
   plans を archive へ／**skill 参照に対し実体が無い dangling パス**（docs/requirements・docs/decisions・
   一部 handover）を stub 作成 or 参照削除で解消。
4. **M4 rebuild** — fingerprint/marker 計算を毎 Bash から外し、テストランナー検出時／ゲート時へ。
   ゲート時の判定（fail-closed・silent-green 禁止）は不変に保つ。
5. **M2 据置** — 必要なら「framework タスクは skip 想定」を1行明文化するのみ。

各工程はテストを保ったまま per-task で進め、3失敗で停止（second-opinion 手順）。

## 6. 検証（second opinion・三者収束）

判定 M2=keep-thin / M3=cut / M4=rebuild は、(1) 本セッションの分析、(2) 私の結論を見せない**盲検
エージェント**、(3) ユーザーが外部モデルでコードベースを検証、の**三者が独立に 3/3 一致**。親基準が
別判断者でも同じ答えを出す＝*再現性*を実証。よって候補 1/5 は重い外部レビューを省いた（学び:
rigor は reversibility×stakes に比例。`docs/LEARNINGS.md` プロセス節に記録）。

## 7. 規模感・期待効果

- 作業ツリーの主な削減: examples 約11k行＋同期機械、docs 約31k行（archive 撤去＋ルート整理）。
- self-consistency 機械（mirror/drift/manifest）と配布前投資を外し、「thin operating model」の実体を
  取り戻す。M2/M4 のユーザー保護は保つ（M4 はホットパスのみ軽量化）。

## 8. 非目標（やらないこと）

- 配布機械（profiles/SemVer/migration/distribution 検証）の新規作り込み（配布は「もっと詰めた先」）。
- 難読化 moat 既存分の取り除き（優先度低・別途）。
- M2 の再設計（据置）。
- ユーザー向け表層（onboarding・templates・handover/client）の機能削減。

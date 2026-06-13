# B3a 設計: 読者パラメータ化マニュアル生成（能力⑨）

> 出典: `docs/audit-report-2026-06-06.md` §4 優先度4 B3（ライフサイクル後半の厚み）。
> B3 を ⑨マニュアル / ⑩UAT / ⑫保守 の3独立サブに分解し、本 spec は **B3a（⑨マニュアル）** のみを対象とする。

## 目的（Goal）

納品物の**操作マニュアル**を、非エンジニアが読める形で機械的に生成できるようにする。監査で能力⑨は唯一の **✗（専用 MANUAL/ユーザーガイドテンプレートが無い）**。最も近い `HANDOVER-TO-CLIENT` は「Dev→クライアントの技術完了報告」であり、製品を**使う/運用する**人向けの操作手順ではない。この欠落を埋め、北極星「クライアント対応〜保守まで一気通貫」の後半（納品後成果物）の型を確立する。

## スコープと決定事項

ブレストで確定した4つの設計判断:

1. **読者パラメータ化（C）**: A=エンドユーザー操作マニュアル と B=クライアント運用者向けガイド を二択にせず、**1つの読者パラメータ化テンプレ＋生成 skill** とする。各案件が該当読者を宣言し、その分だけ手順章を生成。
   - 根拠: B（運用者）はほぼ全納品物で発生（LP/コーポレートでも更新者がいる）、A（利用者）はタスクのある製品限定。両者は読者とタスク集合が違うが**骨格（読者→前提→「〜するには」手順→つまずいたら→用語）は同一**。生成能力を1回作れば読者切替で A も B も出せる。LP=B のみ、アプリ=A+B、と案件差を吸収。
2. **生成機構＝(i)＋advisory**: 新 `user-manual` skill を作り `ship-and-docs` から参照（既存 `docs-sync` 参照と同型）。Dev 終盤で生成。hook ハードゲート/新フェーズにはしない（TO-CLIENT/LEARNINGS と同じ「証拠として作る」運用）。

> **grill-plan 反映（2026-06-07）**: skill 名は衝突回避の慣習に合わせ `manual`→`user-manual`。lint_names がスキルを双方向検査するため、skill 作成と登録（`REQUIRED_SKILL_FILES`＋`REQUIRED_EXAMPLE_SKILL_DIRS`＋`CLAUDE.md ## Skills`）は同一コミットで行う。architecture §6 への行追加は数値カウントが既に stale で非強制のため見送り。詳細は実装計画参照。
   - 根拠: state-machine を触らず段階開示と整合。運用ゲートが要るなら B3c（保守）で検討。
3. **配置・参照・宣言**: 単一ファイル `docs/handover/MANUAL.md`（読者は章で分割）。**`current_refs` に新キーを追加しない**（check_status/テンプレ/テスト/example の4箇所同期を回避）。TO-CLIENT の納品物欄からリンクし、`docs-sync` が存在＋章充足を検証。読者は **MANUAL.md の front-matter `audiences:`** で宣言。
4. **図＝(c)**: テンプレに図プレースホルダを置き、skill は「`ui_surface: true` で UI があれば `qa-browser`/`browser-assist` で主要画面を撮って貼る」と促すが**自動取得は必須化しない**。API/CLI 納品物もあるため browser 自動化への密結合を避ける。

## 非目標（Non-goals / YAGNI）

- B3b（⑩UAT 実行フェーズ）・B3c（⑫保守ライフサイクル）は本 spec の対象外。
- `current_refs.manual` 等のスキーマ拡張はしない。
- マニュアル生成のハードゲート化／新 state-machine フェーズ化はしない。
- スクリーンショットの自動取得を必須にしない。
- 運用者向け詳細（監視・トリアージ手順）は B3c に委ねる。MANUAL の operator 章は「日常運用（コンテンツ更新・基本設定）」に留める。

## コンポーネント（5）

| # | 成果物 | 種別 |
|---|---|---|
| 1 | `templates/MANUAL.template.md` | 新規テンプレ |
| 2 | `.claude/skills/user-manual/SKILL.md` | 新規 skill（pull-based・`disable-model-invocation: true`・`user-invocable: false`） |
| 3 | `.claude/skills/ship-and-docs/SKILL.md` | 改修（ship フェーズに manual ステップ参照を追加） |
| 4 | `.claude/skills/docs-sync/SKILL.md` | 改修（整合チェック項目を1つ追加） |
| 5 | 登録 | `check_framework_contract.py`（`REQUIRED_TEMPLATE_FILES`＋`REQUIRED_SKILL_FILES`＋`REQUIRED_EXAMPLE_SKILL_DIRS`）／`CLAUDE.md ## Skills`（lint 必須）／`templates/profiles/full.json`＋ `.claude/skills` の example ミラー。architecture §6/README スキル数は既に stale で非強制のため本 spec では追わない |

## MANUAL.template.md の構造

- front-matter:
  - `audiences: [end-user, operator]`（案件が該当読者のみ残す）
  - `product: "<記入>"` / `release: "<記入>"` / `date: "<記入>"`
- 冒頭: `<!-- 正本: user-manual skill -->`、`<!-- exit-check: 宣言読者ごとに手順章あり・図 or 図不要理由・つまずいたら/用語記入済み -->`
- **読者ごとに繰り返す章**（宣言された読者の数だけ）:
  - `## <読者名> 向け`
    - **対象読者**: 平易な一文（誰のための章か）
    - **前提**: アクセス方法・必要アカウント・環境（平易語）
    - **操作手順**: タスク1つ＝1ブロック。「### 〜するには」＋番号付きステップ＋図プレースホルダ `![説明](スクショ-パス)`
    - **つまずいたら**: よくある問題と対処（FAQ）
    - **用語**: 章中のエンジニア用語の平易な言い換え
- 末尾: 改訂履歴（任意）。

## user-manual skill の手順（SKILL.md 本文）

1. **読者決定**: `docs/requirements/SCOPE.md`・`PRD.md` と STATUS の `ui_surface` から該当読者（end-user / operator）を判定し、ユーザーに確認。MANUAL.md front-matter の `audiences` に宣言。
2. **タスク抽出**: SCOPE/PRD/ACCEPTANCE＋出荷した機能から主要タスクを列挙。読者ごとに「〜するには」を**平易語**（非エンジニアが読める語彙）で記述。1タスク=1ブロック。
3. **図（c 方針）**: `ui_surface: true` かつ UI が存在する場合、`qa-browser`/`browser-assist` で主要画面を撮って該当手順に貼る。UI が無い/撮れない場合はプレースホルダを残し、図不要の理由を1行記す。自動取得は必須化しない。
4. **つまずいたら・用語** を埋める。空欄を残さない。
5. **TO-CLIENT からリンク**: `docs/handover/TO-CLIENT.md` の納品物に `docs/handover/MANUAL.md` へのリンクを追加。
6. **整合確認**: `docs-sync` skill を読み、マニュアルの存在・章充足を確認。
- **Red flags（禁止）**: 空の手順章を残す／エンジニア用語を平易化せず素出し／宣言読者の章を欠落／理由なく「マニュアル不要」と宣言／チャット履歴を成果物ソースに使う。
- **Context budget**: SCOPE/PRD/ACCEPTANCE＋出荷機能一覧＋MANUAL テンプレのみ。過去チャットは参照しない。
- **いつ使うか**: docs フェーズで `ship-and-docs` の ship 段階から参照される。マニュアルが該当しない案件（例: 使う人も運用者もいない内部使い捨て）は、生成せず理由を記録。

## ship-and-docs への結合

ship フェーズ（現 Step1 証拠収集 → Step2 TO-CLIENT 作成 → Step3 ユーザー確認）に次を挿入:

- **Step 2.5: 操作マニュアル作成（該当時）** — `user-manual` skill を読み、該当読者向けに `docs/handover/MANUAL.md` を作成。TO-CLIENT の納品物欄からリンク。該当しない場合は理由を TO-CLIENT もしくは STATUS に記録。

## docs-sync への結合

整合チェックリストに1項目追加:

- `[ ] マニュアルが該当する案件なら docs/handover/MANUAL.md が存在し、front-matter の宣言読者ごとに手順章がある（該当なしなら理由が記録されている）`

## 登録・ミラー（実装時の同期先）

- `check_framework_contract.py`: `REQUIRED_TEMPLATE_FILES` に `templates/MANUAL.template.md`、`REQUIRED_SKILL_FILES` に `.claude/skills/user-manual/SKILL.md`、`REQUIRED_EXAMPLE_SKILL_DIRS` に `"user-manual"`（example スキルは SKILL_DIRS で管理。`REQUIRED_EXAMPLE_FILES` は触らない）。
- `CLAUDE.md ## Skills` に `user-manual` を追加（**lint_names が双方向検査するため必須**・skill 作成と同一コミット）。
- `templates/profiles/full.json`: `recommended` に `.claude/skills/user-manual/SKILL.md`（lint 非対象・分離可）。
- `.claude/skills` 配下は MIRROR_DIRS のため、新 `user-manual` skill と改修した `ship-and-docs`/`docs-sync` を `examples/minimal-project` へ byte 同一ミラー。
- architecture §6/README のスキル数（doc 上「12」だが実体 15+）は drift/contract 非強制かつ既に stale のため本 spec では追わない。
- 実行後 `check_reference_drift.py`／`check_framework_contract.py --profile=full/standard`／`test_mirror_identity`／`eval_scaffold_smoke.py` を green に。

## テスト戦略（正直な明記）

B3a は **実行コードを持たない**: `MANUAL.template.md` は静的 markdown、`user-manual` skill は LLM 向け手順、ship-and-docs/docs-sync 改修も手順文。よって B1/B2 のような Python ユニットテスト（振る舞い検証）は**書けないし書かない**。

検証は次の2層:
1. **構造的検証（自動）**: 新テンプレ＋skill の登録整合を既存インフラで担保 — `check_framework_contract`（必須ファイル存在・スキル数・name-lint）、`check_reference_drift`（参照名・ミラー byte 同一）、`test_mirror_identity`、`eval_scaffold_smoke`。これらが green であること。
2. **内容レビュー（人手）**: テンプレと skill 本文が「非エンジニアが読める手順を生む」よう書けているかをレビュー（必要なら grill-code 相当の文章レビュー）。スキャフォールド後に MANUAL.template が読者章を正しく持つことを目視。

この「振る舞いロジック不在ゆえユニットテスト無し・検証は登録整合＋内容レビュー」は B3a の性質上の事実であり、設計上の手抜きではない。

## Self-Review（執筆者チェック）

- **プレースホルダ/TBD**: なし（全節に具体記述）。
- **内部整合**: 決定1-4 が各コンポーネントと一致（読者パラメータ→テンプレ front-matter＋skill Step1、advisory→ship-and-docs/docs-sync 参照のみ・gate なし、schema 不変→current_refs 追加なし、図(c)→skill Step3）。
- **スコープ**: B3a 単体（⑨）に限定。⑩⑫ は明示除外。単一の実装計画に収まる規模。
- **曖昧性**: 「該当読者の判定」は skill Step1 でユーザー確認を必須化し一意化。「マニュアル不要」case は理由記録を必須化。

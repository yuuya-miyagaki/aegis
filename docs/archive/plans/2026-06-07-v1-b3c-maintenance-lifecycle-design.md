# B3c 設計: 保守ライフサイクル（能力⑫）

> 出典: `docs/audit-report-2026-06-06.md` §4 優先度4 B3（ライフサイクル後半の厚み）。
> B3 を ⑨マニュアル / ⑩UAT / ⑫保守 の3独立サブに分解し、本 spec は **B3c（⑫保守）** のみを対象とする。
> 前提: B3a（⑨マニュアル, v1.2.0 で版締め済み）の advisory パターンを踏襲する。

## 目的（Goal）

納品後の「**運用 → 監視 → トリアージ → 修正**」の導線を構造化し、運用者（非エンジニア）が
**動かし続けられ・壊れたら直す導線に乗れる**状態を作る。監査で能力⑫は **△**: `bug-diagnosis`
skill・bugfix/hotfix task type・`session-recovery` で Dev 側のバグ修正はあるが、**運用監視→
トリアージ→修正の保守ライフサイクル、運用 runbook テンプレ、保守担当の導線が無い**。この欠落が
北極星「クライアント対応〜保守まで一気通貫」の後半で構造的に最も薄い。本 spec はそこを埋め、
ライフサイクル一周（上流→Dev→納品→保守）を構造的に閉じる。

## スコープと決定事項

ブレストで確定した4つの設計判断:

1. **ライフサイクル構造 ＝ 軽量・advisory**: 新 Mode／新 state-machine フェーズ／新ゲートは
   作らない。修正実行は既存 `bug-diagnosis`・bugfix/hotfix task_type を再利用する。B3c が足すのは
   「保守の前段（runbook 成果物＋トリアージ/ルーティング/記録の導線）」であり、既存の fix 機構の
   上流に薄く乗せる。
   - 根拠: B3a と同じ advisory 路線で「追従トレッドミルから降りる」future-proof 方針・YAGNI と整合。
     既存 bug-diagnosis/bugfix を再利用し重複を避ける。重い新 Mode は state-machine/ミラー/テストの
     同期コストと追従負荷を上げるため見送り。

2. **成果物 ＝ 独立 `RUNBOOK.md`**: MANUAL.md（使い方・日常運用）とは別に、運用者向けの
   「監視・インシデント対応・エスカレーション」を担う単一ファイル `docs/handover/RUNBOOK.md` を
   生成する。ship 時に作成し TO-CLIENT からリンク、`docs-sync` の自己点検チェックリストで存在＋
   必須節を確認（`docs-sync` は自動 validator ではなく LLM 自己点検用のチェックリスト skill）。
   **`current_refs` に新キーは追加しない**（check_status/テンプレ/テスト/example の4箇所同期を回避＝
   B3a と同じ規律）。
   - 根拠: 「壊れたときに開く文書」は読者の瞬間が「使い方」と違うため MANUAL と分離が自然。B3a の
     非目標で監視/トリアージ手順は B3c に委譲済み（MANUAL operator 章は日常運用＝コンテンツ更新/
     基本設定に留める）。RUNBOOK は MANUAL と重複させず、システム健全性・監視・インシデント対応に絞る。

3. **ループの記録 ＝ RUNBOOK 内「インシデント履歴」節**: maintenance skill が発生時に分類→
   ルーティング（操作者対応 or 既存 bugfix/hotfix へエスカレーション）→解決後に RUNBOOK の
   「インシデント履歴」節へ追記する。専用の記録成果物（docs/maintenance/ 配下）は新設しない。
   - 根拠: 単一成果物（B3a の MANUAL 一本化と同規律）で、運用者が同じ文書で履歴も追える。
     新成果物/同期先を増やさない。件数が出てから構造化記録に移行しても遅くない（YAGNI）。

4. **監視の具体度 ＝ ガイド付きプレースホルダ・自動セットアップは非必須**: テンプレに監視対象/
   しきい値/確認手段/エスカレーション先/SLA のプレースホルダを置き、skill は記入を促すが、実際の
   監視インフラ構築（アラート設定等）は必須化しない。
   - 根拠: aegis はハーネスでありアプリでない。監視は案件/スタック依存（Vercel/Firebase 等が各々の
     監視を持つ）。B3a の「図は自動取得を必須化しない」と同型で、特定インフラへの密結合を避ける。

5. **skill 構成 ＝ 1 skill 2パート**: 新 `maintenance` skill を1つだけ作り、Part A（生成・ship時）と
   Part B（運用時・インシデント対応ループ）を同一 SKILL.md 内に分節で持つ。
   - 根拠: 両パートは同じ RUNBOOK.md を対象にする（Part B は履歴節に追記）。登録/ミラー/lint の
     同期面を倍増させず B3a の「surface 最小化」規律と整合する。分離（生成 skill と トリアージ skill）は
     「1ユニット1責務」では綺麗だが同期コストが倍になるため見送り。

## 非目標（Non-goals / YAGNI）

- B3a（⑨マニュアル）・B3b（⑩UAT 実行フェーズ）は本 spec の対象外。
- 新 Mode（Maintain）／新 state-machine フェーズ／新ゲート／新 task_type は作らない。
- 修正実行ロジックの新設はしない（bug-diagnosis・bugfix/hotfix を再利用）。
- `current_refs.runbook` 等のスキーマ拡張はしない。
- 専用インシデント記録成果物（docs/maintenance/）は作らない。
- 実際の監視インフラ構築・アラート自動設定を必須にしない。
- MANUAL operator 章（使い方・日常運用＝コンテンツ更新/基本設定）と内容を重複させない。

## 実行主体と到達経路

保守は「運用者（非エンジニア）」と「Claude（開発者セッション）」の二層で回す。役割を取り違えると
到達経路が空白になる（`maintenance` は `user-invocable: false` で運用者は起動できない）ため明示する。

- **運用者の入口 ＝ `docs/handover/RUNBOOK.md`（人間可読文書）**: 運用者は RUNBOOK を読み、`## 監視`
  で異常に気づき、`## インシデント対応（トリアージ）` で自己対応できる範囲を実施する。手に負えない
  場合は `## エスカレーション` の合図（高重大度／手順で復旧しない 等）に従い開発者へ連絡する。運用者は
  skill を起動しない（できない）。RUNBOOK が運用者向けの唯一の入口。
- **Part B（トリアージ→ルーティング→記録）の主体 ＝ Claude**: エスカレーションを受けた開発者が
  `task_type = bugfix`（緊急時 `hotfix`）で Dev セッションを開くと、`bug-diagnosis` が本番/運用起因
  ケースで `maintenance` Part B を参照する。Claude が重大度分類・ルーティング・RUNBOOK インシデント
  履歴への記録を行う。トリアージは1回で、診断本体（bug-diagnosis）に入ったら maintenance には戻らない。
- `maintenance` skill（`user-invocable: false`・pull-based）は Claude 側の手順書であり、運用者向け
  文書ではない。運用者に必要な情報はすべて成果物 RUNBOOK に出力する。

## コンポーネント（7）

| # | 成果物 | 種別 |
|---|---|---|
| 1 | `templates/RUNBOOK.template.md` | 新規テンプレ |
| 2 | `.claude/skills/maintenance/SKILL.md` | 新規 skill（pull-based・`disable-model-invocation: true`・`user-invocable: false`） |
| 3 | `.claude/skills/ship-and-docs/SKILL.md` | 改修（ship フェーズに RUNBOOK 生成ステップを追加） |
| 4 | `.claude/skills/docs-sync/SKILL.md` | 改修（整合チェック項目を1つ追加） |
| 5 | `.claude/skills/bug-diagnosis/SKILL.md` | 改修（本番/運用起因の入口に maintenance 参照を1節追加） |
| 6 | `templates/HANDOVER-TO-CLIENT.template.md` | 改修（納品サマリーに RUNBOOK リンク行を追加） |
| 7 | 登録 | `check_framework_contract.py`（`REQUIRED_TEMPLATE_FILES`＋`REQUIRED_SKILL_FILES`＋`REQUIRED_EXAMPLE_SKILL_DIRS`）／`CLAUDE.md ## Skills`（lint 必須）／`templates/profiles/full.json`＋ `.claude/skills` の example ミラー。architecture §6/README スキル数は既に stale で非強制のため本 spec では追わない |

## RUNBOOK.template.md の構造

- front-matter:
  - `product: "<記入>"` / `release: "<記入>"` / `date: "<記入>"`
  - `environment: "<記入: 本番URL・ホスティング先>"`
  - `owners: "<記入: 運用担当・エスカレーション先>"`
- 冒頭: `<!-- 正本: maintenance skill -->`、`<!-- exit-check: 監視/トリアージ/エスカレーション/履歴の必須節あり・プレースホルダ未記入なし・用語平易化済み -->`
- `## 監視`: 何を見るか（監視対象）・正常値/しきい値・確認手段・頻度。プレースホルダ。
- `## インシデント対応（トリアージ）`: 重大度の見分け方（例 サイト全停止=高 / 一部機能不調=中 / 軽微=低）・各重大度の初動・**操作者で対応できる範囲 vs 開発者へエスカレーションする線引き**。
- `## エスカレーション`: 連絡先/連絡方法・SLA/目標復旧時間・bugfix/hotfix 起動の合図。
- `## インシデント履歴`: 日付 / 事象 / 重大度 / 対応 / 恒久対策（追記式ログ。初期は空の表＋記入例1行。古い履歴はアーカイブ可の注記を置く）。
- `## 用語`: 章中のエンジニア用語の平易な言い換え。

> **MANUAL との境界（重複防止）**: 日常の使い方・更新手順は `MANUAL.md` に集約し、RUNBOOK には
> 書かない。RUNBOOK は「異常の検知（監視）と復旧（トリアージ→対応→記録）」に絞る。冒頭注記で
> 読者にこの住み分けを示す。

## maintenance skill の手順（SKILL.md 本文）

front-matter は `disable-model-invocation: true`・`user-invocable: false`（B3a の user-manual と同型の pull-based）。

### いつ使うか
- *Part A*: docs フェーズで `ship-and-docs` の ship 段階から参照される（RUNBOOK 生成）。
- *Part B*: 運用中にインシデント/監視シグナルが出たとき。`bug-diagnosis` の本番/運用起因ケースから参照される。
- 保守が該当しない案件（運用者不在の内部使い捨て等）は生成せず理由を記録。

### Part A: RUNBOOK 生成（ship 時）
1. **対象判定**: `docs/requirements/SCOPE.md`・`PRD.md`・配備情報（TO-CLIENT「配備と運用」）・STATUS から、運用者の有無とデプロイ先/監視手段/エスカレーション先を判定し、ユーザーに確認。
2. **記述**: `templates/RUNBOOK.template.md` をもとに `docs/handover/RUNBOOK.md` を作成。監視・トリアージ・エスカレーションを**平易語**で記述。プレースホルダを空のまま残さない。監視インフラ自動設定は必須化しない（記入を促すに留める）。
3. **リンク**: `docs/handover/TO-CLIENT.md` の納品サマリーに `docs/handover/RUNBOOK.md` へのリンクを追加。
4. **整合確認**: `docs-sync` skill を読み、RUNBOOK の存在・必須節充足を確認。

### Part B: インシデント対応ループ（運用時）
1. **シグナル確認**: 症状・影響範囲を把握。`docs/handover/RUNBOOK.md` の `## 監視`・`## インシデント対応` 節を読む。
2. **分類**: 重大度（高/中/低）とスコープを RUNBOOK のトリアージ基準で判定。
3. **ルーティング**:
   - 操作者で対応可（RUNBOOK の手順内）→ 実施。
   - 開発が必要 → `task_type = bugfix`（緊急なら `hotfix`）として `bug-diagnosis` skill へ。
4. **記録**: 解決後、RUNBOOK の `## インシデント履歴` に 日付/事象/重大度/対応/恒久対策 を追記してループを閉じる。

- **Red flags（禁止）**: 履歴を残さずインシデントを閉じる／重大度判定を飛ばす／エスカレーション線引きが不明のまま放置／プレースホルダを空で残す／エンジニア用語を平易化せず素出し／チャット履歴を成果物ソースに使う。
- **Context budget**: SCOPE/PRD＋配備情報＋RUNBOOK テンプレ（Part A）／RUNBOOK＋当該シグナル情報（Part B）のみ。過去チャットは参照しない。

## ship-and-docs への結合

ship フェーズ（Step1 証拠収集 → Step2 TO-CLIENT 作成 → Step2.5 操作マニュアル[B3a] → Step3 ユーザー確認）に次を挿入:

- **Step 2.6: 運用 RUNBOOK 作成（該当時）** — `maintenance` skill の Part A を読み、運用者がいる場合は `templates/RUNBOOK.template.md` をもとに `docs/handover/RUNBOOK.md` を作成。TO-CLIENT の納品サマリーからリンク。運用者不在なら生成せず理由を同欄に記録。

## docs-sync への結合

整合チェックリスト（LLM 自己点検）に1項目追加。RUNBOOK には MANUAL の `audiences` のような
宣言リストが無いため、これは parity ではなく**存在＋必須節の充足チェック**:

- `[ ] 保守が該当する案件なら docs/handover/RUNBOOK.md が存在し、front-matter（product/environment/owners）と必須節（監視/インシデント対応/エスカレーション/インシデント履歴/用語）が埋まっている（該当なしなら理由が記録されている）`

## bug-diagnosis への結合

`bug-diagnosis` の「いつ使うか」付近に1節を追加（既存の診断プロセスは不変）:

- **本番/運用起因の問題のとき（のみ）**: まず `maintenance` skill（Part B: トリアージ）を読み、重大度分類とルーティングを経てから本診断に入る。トリアージは1回で、本診断に入ったら maintenance には戻らない。解決後は RUNBOOK の `## インシデント履歴` に追記する。

> bug-diagnosis 本体のゲート処理・ReAct 診断ステップは変更しない。追加は「**本番/運用起因のときだけ** maintenance を先に通す」という参照1節のみ（通常の bugfix/hotfix は従来どおり）。

## HANDOVER-TO-CLIENT への結合

納品サマリーに RUNBOOK リンク行を MANUAL 行と並べて追加:

- `- 運用 RUNBOOK: <記入: docs/handover/RUNBOOK.md（運用者がいる場合）／不要なら理由>`

## 登録・ミラー（実装時の同期先）

- `check_framework_contract.py`: `REQUIRED_TEMPLATE_FILES` に `templates/RUNBOOK.template.md`、`REQUIRED_SKILL_FILES` に `.claude/skills/maintenance/SKILL.md`、`REQUIRED_EXAMPLE_SKILL_DIRS` に `"maintenance"`（example スキルは SKILL_DIRS で管理。`REQUIRED_EXAMPLE_FILES` は触らない）。
- `CLAUDE.md ## Skills` に `maintenance` を追加（**lint_names が双方向検査するため必須**・skill 作成と同一コミット）。
- `templates/profiles/full.json`: `recommended` に `.claude/skills/maintenance/SKILL.md`（lint 非対象・分離可）。
- `.claude/skills` 配下は MIRROR_DIRS のため、新 `maintenance` skill と改修した `ship-and-docs`/`docs-sync`/`bug-diagnosis` を `examples/minimal-project` へ byte 同一ミラー。
- architecture §6/README のスキル数は既に stale で非強制のため本 spec では追わない（B3a と同方針）。
- 実行後 `check_reference_drift.py`／`check_framework_contract.py --profile=full/standard`／`test_mirror_identity`／`eval_scaffold_smoke.py` を green に。

## テスト戦略（正直な明記）

B3c は **実行コードを持たない**: `RUNBOOK.template.md` は静的 markdown、`maintenance` skill は LLM 向け手順、ship-and-docs/docs-sync/bug-diagnosis 改修も手順文。よって B1/B2 のような Python ユニットテスト（振る舞い検証）は**書けないし書かない**。

検証は次の2層:
1. **構造的検証（自動）**: 新テンプレ＋skill の登録整合を既存インフラで担保 — `check_framework_contract`（必須ファイル存在・スキル数・name-lint）、`check_reference_drift`（参照名・ミラー byte 同一）、`test_mirror_identity`、`eval_scaffold_smoke`。これらが green であること。
2. **内容レビュー（人手）**: テンプレと skill 本文が「非エンジニアが運用・監視・トリアージできる手順を生む」よう書けているかをレビュー（grill-code 相当の文章レビュー）。スキャフォールド後に RUNBOOK.template が必須節を正しく持つことを目視。

この「振る舞いロジック不在ゆえユニットテスト無し・検証は登録整合＋内容レビュー」は B3c の性質上の事実であり、設計上の手抜きではない（B3a と同性質）。

## Self-Review（執筆者チェック）

- **プレースホルダ/TBD**: なし（全節に具体記述）。
- **内部整合**: 決定1-5 が各コンポーネントと一致（軽量→新 Mode/ゲートなし・bug-diagnosis 再利用、独立 RUNBOOK→新テンプレ＋ship-and-docs Step2.6、履歴記録→RUNBOOK インシデント履歴節＋skill Part B Step4、監視具体度→テンプレ プレースホルダ＋skill 非必須化、1 skill→maintenance 2パート）。
- **スコープ**: B3c 単体（⑫）に限定。⑨⑩ は明示除外。単一の実装計画に収まる規模。
- **曖昧性**: 「保守が該当するか」は skill Part A Step1 でユーザー確認を必須化し一意化。「運用者不在＝RUNBOOK 不要」case は理由記録を必須化。MANUAL との境界（使い方/日常運用 は MANUAL、監視/インシデント対応 は RUNBOOK）を非目標＋RUNBOOK 構造注記で明示。
- **grill-plan 反映（2026-06-07）**: ①実行主体と到達経路の節を追加（運用者の入口＝RUNBOOK 文書／Part B の主体＝Claude、`user-invocable:false` ゆえ運用者は skill を起動しない）。②docs-sync は parity でなく存在＋必須節の自己点検と明記（RUNBOOK に audiences 相当の宣言が無い）。③bug-diagnosis 結合は「本番/運用起因のときのみ・トリアージ1回」と限定。④RUNBOOK 履歴のアーカイブ可と MANUAL 重複防止注記を追加。詳細は実装計画の grill 反映欄参照。

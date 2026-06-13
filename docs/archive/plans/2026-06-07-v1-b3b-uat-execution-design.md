# B3b 設計: UAT 実行フェーズ（能力⑩）

> 出典: `docs/audit-report-2026-06-06.md` §4 優先度4 B3（ライフサイクル後半の厚み）。
> B3 を ⑨マニュアル / ⑩UAT / ⑫保守 の3独立サブに分解し、本 spec は **B3b（⑩UAT）** のみを対象とする。
> 前提: B3a（⑨, v1.2.0）・B3c（⑫, main push 済み）の advisory パターンを踏襲しつつ、UAT は
> 「合否で返却を律する」性質のため既存 `dev_ready_for_client` ゲートに最小の歯で連動させる。

## 目的（Goal）

ACCEPTANCE で「定義」した受入条件を、ビルド済み製品に対して **client（ユーザー）が実検証して
合否を記録する**場を作り、「基準定義」と「実行」を分離する。監査で能力⑩は **△**: ACCEPTANCE
テンプレで受入条件を上流定義するが、**納品時に client が実検証する UAT 実行フェーズ/skill が無い**。
受入「基準定義」と「実行」が未分離。本 spec はこの実行側を埋め、北極星後半（⑨マニュアル・⑩UAT・
⑫保守）を構造的に揃える。

## qa-verification との違い（重複回避）

`qa-verification` は **Dev 内部 QA**（テスト/lint/build を dev チームが実行しエビデンス収集）。
UAT は **client 視点の受入**（ビルド済み製品が ACCEPTANCE を満たすかを client が判定しサインオフ）。
両者は主体・観点・タイミングが違うため重複させない。UAT は qa-verification の結果を証拠として
参照してよいが、判定の正本は client サインオフ。

## スコープと決定事項

ブレストで確定した4つの設計判断:

1. **深さ ＝ advisory＋既存ゲート連動**: 新 state-machine フェーズ／新ゲートは作らない。UAT の
   合否は既存 `dev_ready_for_client`（Dev→client 返却ゲート）の受入証拠として機能させる。
   - 根拠: B3a/B3c の advisory 路線・future-proof「surface を増やさない」方針と整合。UAT は本来
     「合否で返却を律する」性質で、既存の返却ゲートが自然な連動先。新フェーズは state-machine/
     client-workflow/ミラー/テストの同期コストと追従負荷を上げるため見送り。

2. **連動の強制 ＝ スクリプト強制の存在チェック**: `dev_ready_for_client` の承認を、
   `docs/handover/UAT-RESULTS.md` が不在のときブロックする（`check_status.py` の
   `dev_ready_for_client` 承認処理に存在チェック＋ユニットテスト）。
   - 根拠: ユーザーが「純 advisory」でなく「ゲート連動」を選択。最小の歯＝存在チェックで「受入条件を
     定義した案件は UAT を記録しないと client へ返せない」を機械強制する。B1/B2 と同系の機械ゲート。
     B3a/B3c と違い **B3b は実コード＋テストを持つ**（gate チェック）。

3. **合否の主体 ＝ client（ユーザー）サインオフ**: Must-AC が通ったかの最終判定は client が行う。
   機械は UAT-RESULTS の**存在のみ**を見て、合否そのもの（✅/❌ の内容）は判定しない。
   - 根拠: 受入の判断は client の権限。機械が合否をパースすると誤判定とメンテ負荷を生む。存在チェックに
     留め、判定は人間（B2 の「非エンジニアが judge」哲学とも整合）。

4. **条件付き ＝ ACCEPTANCE.md がある案件のみ UAT-RESULTS を要求**: `docs/requirements/ACCEPTANCE.md`
   が存在するときだけ UAT-RESULTS を必須化する。ACCEPTANCE 不在なら従来どおり（UAT 不要）。
   - 根拠: 受入条件を定義した案件＝検証も必須、という論理的紐付け。ACCEPTANCE が無い案件（aegis 自身の
     framework タスク・内部タスク等）の `dev_ready_for_client` を壊さない。framework 自身の契約/テストへの
     巻き込みを防ぐ。

## 非目標（Non-goals / YAGNI）

- B3a（⑨マニュアル）・B3c（⑫保守）は本 spec の対象外。
- 新 state-machine フェーズ（uat phase）／新ゲートは作らない。
- 合否（✅/❌ の内容・Must 全通過か）の機械判定はしない（存在チェックのみ）。
- `current_refs.uat` 等のスキーマ拡張はしない。
- qa-verification（Dev 内部 QA）と内容を重複させない。
- UAT の自動実行（テスト自動起動等）は必須化しない。client 判定が正本。

## コンポーネント（8）

| # | 成果物 | 種別 |
|---|---|---|
| 1 | `templates/UAT-RESULTS.template.md` | 新規テンプレ |
| 2 | `.claude/skills/uat/SKILL.md` | 新規 skill（pull-based・`disable-model-invocation: true`・`user-invocable: false`） |
| 3 | `scripts/check_status.py` | 改修（`dev_ready_for_client` 承認時の UAT-RESULTS 存在チェック・ACCEPTANCE 条件付き） |
| 4 | `tests/test_check_status.py` | 追加（ブロック/許可/従来どおりの3ケース） |
| 5 | `.claude/skills/ship-and-docs/SKILL.md` | 改修（gate 申請前に UAT 実行ステップを追加） |
| 6 | `.claude/skills/docs-sync/SKILL.md` | 改修（UAT-RESULTS 整合チェック1項目） |
| 7 | `templates/HANDOVER-TO-CLIENT.template.md` | 改修（納品サマリーに UAT-RESULTS リンク行） |
| 8 | 登録・ミラー | `check_framework_contract.py`（TEMPLATE/SKILL/EXAMPLE_SKILL_DIRS の3箇所）／`CLAUDE.md ## Skills`／`full.json`／`examples/minimal-project` ミラー（skill）＋ example README/CLAUDE のスキル数 |

## UAT-RESULTS.template.md の構造

- front-matter:
  - `product: "<記入>"` / `release: "<記入>"` / `date: "<記入>"`
  - `tested_by: "<記入: 検証した client 担当者>"`
- 冒頭: `<!-- 正本: uat skill -->`、`<!-- exit-check: 全 Must-AC に合否・証拠あり・サインオフ済み -->`
- `## 判定サマリー`: 総合 合格/不合格・Must 全通過か（平易語）。
- `## 受入検証`: AC ごとの表 — `AC | 期待する結果 | 実際の結果 | 合否(✅/❌) | 証拠 | 優先度(Must/Should)`。
- `## 未合格と対応`: ❌ の項目と対応方針（再修正＝bugfix/hotfix へ／client が ack して受容）。
- `## サインオフ`: 承認者（client）・日付。

## uat skill の手順（SKILL.md 本文）

front-matter は `disable-model-invocation: true`・`user-invocable: false`（B3a/B3c と同型 pull-based）。

### いつ使うか
- docs フェーズで `ship-and-docs` の ship 段階から参照される（`dev_ready_for_client` 申請の前）。
- `docs/requirements/ACCEPTANCE.md` がある案件のとき。ACCEPTANCE が無い案件は UAT 不要（理由記録）。

### 手順
1. **受入条件を読む**: `docs/requirements/ACCEPTANCE.md` の各 AC とトレーサビリティ（検証方法: 自動テスト/手動確認/レビュー）を読む。
2. **実検証**: ビルド済み製品に対し各 AC を検証する。UI は `browser-assist`/`qa-browser` で実画面を確認、自動テストは qa 成果物の結果を参照。各 AC に 期待/実際/合否(✅/❌)/証拠 を記録。
3. **client サインオフ**: 結果を client（ユーザー）に提示し合否を確認。Must の ❌ は bugfix/hotfix へ戻すか、client が理由付きで ack して受容。
4. **保存とリンク**: `templates/UAT-RESULTS.template.md` をもとに `docs/handover/UAT-RESULTS.md` を作成し、TO-CLIENT の納品サマリーからリンク。
5. **整合確認**: `docs-sync` skill を読み、UAT-RESULTS の存在と必須節充足を確認。

- **UAT が不要なとき**: ACCEPTANCE が無い（受入条件未定義の内部タスク等）案件は生成せず、TO-CLIENT もしくは STATUS に理由を1行記録する。
- **Red Flags（禁止）**: ❌ を残したまま理由なくサインオフ／証拠リンク無しで✅／ACCEPTANCE の AC を UAT-RESULTS から欠落／qa-verification（内部QA）の結果をそのまま UAT 合否として流用（client 視点の確認を省略）／チャット履歴をソースにする。
- **コンテキスト予算**: ACCEPTANCE＋qa 成果物＋UAT テンプレのみ。過去チャットは参照しない。

## ship-and-docs への結合

ship フェーズ（Step1 証拠収集 → Step2 TO-CLIENT → Step2.5 マニュアル → Step2.6 RUNBOOK → Step3 ユーザー確認 → … → Step6 ゲート申請）に次を挿入:

- **Step 2.7: UAT 実行（該当時）** — `uat` skill を読み、ACCEPTANCE がある場合は各 AC を実検証して `docs/handover/UAT-RESULTS.md` を作成し client サインオフを得る。TO-CLIENT からリンク。ACCEPTANCE が無い場合は生成せず理由を記録。
- Step6 の `dev_ready_for_client` 申請時、UAT-RESULTS 不在（かつ ACCEPTANCE 有り）なら `update-gate.sh`/`check_status.py` がブロックする（機械強制）。

## docs-sync への結合

整合チェックリスト（LLM 自己点検）に1項目追加:

- `[ ] UAT が該当する案件（ACCEPTANCE あり）なら docs/handover/UAT-RESULTS.md が存在し、全 Must-AC に合否・証拠・サインオフがある。該当なしなら理由が記録されている`

## HANDOVER-TO-CLIENT への結合

納品サマリーに UAT-RESULTS リンク行を追加（MANUAL/RUNBOOK 行と並べる）:

- `- UAT 結果: <記入: docs/handover/UAT-RESULTS.md（ACCEPTANCE がある場合）／不要なら理由>`

## ゲート連動の仕組み（check_status.py）

存在チェックは `check_gate_prerequisites()`（`scripts/check_status.py:834` 付近、純 deterministic gating）の
`dev_ready_for_client` 分岐に追加する。**evidence 層の `pre_approve_gate` ではない**。同型の先例は
同関数内の `client_ready_for_dev` の mapping.md 存在チェック（`:866`、`root / "docs/translation/mapping.md"`）。

- `dev_ready_for_client` 分岐（既存の必須ゲート [review/qa/security] チェックの後）に追加:
  - `root / "docs/requirements/ACCEPTANCE.md"` が存在し、かつ `root / "docs/handover/UAT-RESULTS.md"` が
    **不在**なら、エラーを print して `return 1`（ブロック）。
  - ACCEPTANCE.md 不在なら従来どおり `return 0`（UAT 不要）。
  - UAT-RESULTS の中身（✅/❌）は検査しない（client サインオフが正本）。
- **エラーメッセージは既存の日本語スタイルに統一**（`client_ready_for_dev` の mapping エラーに倣う）。例:
  ```
  ERROR: docs/requirements/ACCEPTANCE.md があるのに docs/handover/UAT-RESULTS.md が見つかりません。
         dev_ready_for_client の前に UAT を実行してください。
         → uat skill を使用
  ```
- **「❌ のまま存在させれば機械は通る」抜け道**: 機械は存在のみ検査するため、未合格のまま UAT-RESULTS を
  置けばゲートは通る。これは「合否は client サインオフが正本」の意図通り。人手側の補完として docs-sync 自己
  点検（全 Must-AC に合否・サインオフ）と uat skill の Red Flags（❌ のまま理由なくサインオフ禁止）で塞ぐ。

## 登録・ミラー（実装時の同期先）

- `check_framework_contract.py`: `REQUIRED_TEMPLATE_FILES` に `templates/UAT-RESULTS.template.md`、`REQUIRED_SKILL_FILES` に `.claude/skills/uat/SKILL.md`、`REQUIRED_EXAMPLE_SKILL_DIRS` に `"uat"`（`REQUIRED_EXAMPLE_FILES` は触らない）。
- `CLAUDE.md ## Skills` に `uat` を追加（**lint_names 双方向検査のため必須**・skill 作成と同一コミット）。
- `templates/profiles/full.json`: `recommended` に `.claude/skills/uat/SKILL.md`。
- `.claude/skills` 配下は MIRROR_DIRS のため、新 `uat` skill と改修した `ship-and-docs`/`docs-sync` を `examples/minimal-project` へ byte 同一ミラー。
- example の `README.md`（スキル数 17→18）・`CLAUDE.md`（## Skills 行）も同期（B3c で取りこぼした教訓）。
- **`scripts/check_status.py` は example へ byte 同一ミラー（確定・確認済み）**: `examples/minimal-project/scripts/check_status.py` が本体と byte 同一であることを確認済み。`check_status.py` の改修は **必ず example 側へ同期**する（しないと `test_mirror_identity`・`check_reference_drift` が落ちる）。一方 **`tests/` は example 非ミラー**なので `tests/test_check_status.py` の追加はミラーしない（スクリプトはミラー／テストは非ミラーの非対称に注意）。
- 実行後 `check_reference_drift.py`／`check_framework_contract.py --profile=full/standard`／`test_mirror_identity`／`eval_scaffold_smoke.py`／`test_check_status.py` を green に。

## テスト戦略（今回は実テストあり）

B3a/B3c と違い B3b は**実コードを持つ**（`check_status.py` の gate チェック）。検証は3層:

1. **ユニットテスト（新規）**: `tests/test_check_status.py` に3ケース追加 —
   (a) ACCEPTANCE 有り＋UAT-RESULTS 無し → `dev_ready_for_client` 承認ブロック、
   (b) ACCEPTANCE 有り＋UAT-RESULTS 有り → 承認可、
   (c) ACCEPTANCE 無し → 承認可（従来どおり）。
   - **既存テストの非回帰**: dev_ready_for_client の既存テストは `TempProject`（STATUS.md のみ・ACCEPTANCE 無し）を使うため、ACCEPTANCE 条件付き分岐で素通りし壊れない見込み（特に許可期待の `test_dev_ready_for_client_all_approved_allows`）。**実装時に実走で確認**。
   - **fixture 拡張**: 新3ケースは temp root に `docs/requirements/ACCEPTANCE.md`・`docs/handover/UAT-RESULTS.md` を置く必要がある。`TempProject` helper が任意ファイルを置けるか確認し、不可なら最小限拡張する。
2. **構造的検証（自動）**: `check_framework_contract`（必須ファイル/スキル数/name-lint）・`check_reference_drift`（参照名・ミラー byte 同一）・`test_mirror_identity`・`eval_scaffold_smoke`。
3. **内容レビュー（人手）**: テンプレ/skill 本文が「client（非エンジニア）が受入検証できる」よう書けているか（grill-code 相当）。

## Self-Review（執筆者チェック）

- **プレースホルダ/TBD**: なし（全節に具体記述）。`<記入>` は成果物テンプレの記入欄。
- **内部整合**: 決定1-4 が各コンポーネントと一致（advisory+連動→新フェーズなし・既存ゲート、存在チェック→check_status.py+test、client サインオフ→テンプレ サインオフ節・機械は存在のみ、条件付き→ACCEPTANCE 有無分岐）。
- **スコープ**: B3b 単体（⑩）に限定。⑨⑫ は明示除外。単一の実装計画に収まる規模。
- **曖昧性**: 「UAT が該当するか」は ACCEPTANCE.md の有無で機械判定。「合否」は client サインオフで一意化。qa-verification との境界を明示。
- **要確認（実装時）**: TempProject helper が temp root に任意ファイル（ACCEPTANCE.md/UAT-RESULTS.md）を置けるか。既存 dev_ready_for_client 承認テストが ACCEPTANCE 無しで壊れないことの実走。example へ UAT-RESULTS を足すか（要検討1）。

## grill-plan 反映（2026-06-07）

- **致命1（ミラー確定）**: `scripts/check_status.py` は example と byte 同一ミラー（確認済み）。改修は example へ必ず同期。`tests/` は非ミラーなのでテストは同期しない（スクリプト=ミラー／テスト=非ミラーの非対称）。§登録・ミラーに確定反映。
- **致命2（配置・言語）**: 存在チェックは `check_gate_prerequisites()` の dev_ready_for_client 分岐（`:834`）に入れる（`client_ready_for_dev` の mapping 存在チェック `:866` と同型）。`pre_approve_gate` ではない。エラーは既存に倣い**日本語＋「→ uat skill を使用」**。§ゲート連動に反映。
- **致命3（テスト）**: 既存 dev_ready_for_client テストは TempProject（ACCEPTANCE 無し）で素通り見込み・要実走。新3ケースは fixture に ACCEPTANCE/UAT-RESULTS を置く拡張が要る。§テスト戦略に反映。
- **要検討2（抜け道）**: 機械は存在のみ検査＝❌のまま通る。docs-sync 自己点検＋skill Red Flags で人手補完、と§ゲート連動に明記。
- **要検討1（example）**: example は ACCEPTANCE 有り・UAT-RESULTS 無し。dev_ready_for_client=pending なので contract は通るが、ショーケース完結のため example に UAT-RESULTS.md を足すか実装時判断（任意）。
- **要検討3（空 ACCEPTANCE）**: profiles で scaffold されない（確認済み）ため誤発火低。空 AC でも要求は立つが「定義したら検証必須」の意図通りで許容。

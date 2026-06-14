# spec delta review（Client モード）設計書

- 作成日: 2026-06-14
- 出典: 進化ロードマップ `docs/plans/2026-06-14-aegis-evolution-roadmap.md` の **P2**
- 対象版: v1.8.0 → **v1.9.0**（新機能 minor）
- 種別: feature（framework）

## 1. 背景と目的

進化ロードマップ P2 は、spec-kit / OpenSpec の「コードを読まずに変更を高レベルで
把握・レビューする」語彙を Aegis の Client モードに取り入れる施策。北極星の
「LLM＝判断・可視化」に合致し、既存 Client gate（6成果物＋内容検査）への
**小規模拡張**として位置づける（レバレッジは P1 未満）。

解決する失敗モード: 反復2回目以降、client が要件を変えても、ゲートは同じ6成果物が
形式検査を通れば再承認されるため、**「何がどう変わったか」を誰も明示レビューしない
まま Dev に渡る（静かな要件ドリフト）**。非エンジニアの client は前回との差分を
把握できない。

本施策は、要件変更を伴う反復で、平易な日本語の **spec delta（差分）レビュー成果物**を
ゲートの必須要件に加え、client が「今回あらたに何を作る／変えるよう依頼しているか」を
コード非依存で明示確認できるようにする。

## 2. スコープ

### やること
- 反復2回目以降の `client_ready_for_dev` ゲートに、7枚目の成果物
  `docs/handover/CHANGES.md` を**条件付き必須**として追加。
- 既存6成果物と同型の検査（存在＋200バイト＋sentinel）を流用。
- 差分を平易に記す新テンプレ `templates/CHANGES.template.md`。
- client-workflow skill の handover 行に作成手順を追記。

### やらないこと（YAGNI）
- **git による差分の機械検出・照合**は行わない（A2 不採用）。トリガは STATUS.md の
  `iteration` 値のみ。差分の中身は LLM が git diff を読んで執筆し、client が判断する。
- 専用ゲートは新設しない。`client_ready_for_dev` に畳み込む。
- 逆方向（Dev→Client の納品レビュー）は対象外。既存 `HANDOVER-TO-CLIENT` と重複するため。

## 3. 採用方針の根拠（検討した代替案）

差分の捉え方として A（順方向＝要件変更レビュー）/ B（逆方向＝納品レビュー）/ C（両方）を
比較し、**A** を採用。ロードマップが明示する「要件→handover」「既存 Client gate に
上乗せ」に一致し、B は `HANDOVER-TO-CLIENT` と重複、C は「小規模拡張」枠を超えるため。

決定論の度合いとして A1（構造のみ）/ A2（git 強制）/ A3（中間）を比較し、**A1** を採用。
トリガ（`iteration > 1`）は STATUS.md から決定論的に取れるので git 配管なしでも「必須化」は
機械強制でき、Aegis の強み（決定論的強制）を保てる。A2 の git 照合は強力だが、baseline
commit の特定・保存という新しい状態管理を Client ゲートに持ち込み、P2 の費用対効果を崩す。

## 4. アーキテクチャ

### 4.1 二層構造（Aegis の定石）
- **決定論層（hook）**: 反復2回目以降に CHANGES.md の存在＋200バイト＋sentinel を強制。
  欠落・薄すぎ・sentinel 無しは deny。
- **判断層（client レビュー）**: 差分の内容が妥当かは client が読んで承認する。hook は
  内容の意味を問わない（既存6成果物と同じ割り切り）。

### 4.2 成果物 `docs/handover/CHANGES.md`
- **置き場所**: `docs/handover/`（`TO-DEV.md` と同じ。`client_ready_for_dev` ゲートで
  一緒にレビューされる handover-time の関心事）。
- **sentinel**: `<!-- aegis-required-section: spec-delta -->`（テンプレ末尾に埋め込み、
  通常の「テンプレをコピーして本文を埋める」操作で残る）。
- **必須セクション**:
  - `## この反復で変える理由`（1〜2文）
  - `## 追加（新しく作るもの）`
  - `## 変更（やり方が変わるもの）`
  - `## 削除・取りやめ`
  - `## 受入条件・スコープへの影響`
- **「変更なし」明示弁**: 冒頭に「☑ 今回は要件変更なし（理由を1文）」のチェック欄。
  チェック時は各セクションを「該当なし」で通せる（min-bytes と sentinel は形式として残す）。
  これにより「要件を変えず Dev だけ回した反復」や「再確認だけ」で空の差分を捏造させる
  嫌がらせを防ぐ。最終防壁は client の明示レビュー。

## 5. トリガと判定ロジック

`client_ready_for_dev` 承認時（`check_status.py` の `check_gate_prerequisites` 内、
`client_ready_for_dev` 分岐）に、STATUS.md フロントマターの `iteration`（top-level の
任意整数フィールド）を読む。

| iteration | CHANGES.md | 根拠 |
|-----------|-----------|------|
| `1` または欠落 | **不要** | 初回は差分の相手がいない。既存挙動を壊さない（fail-open） |
| `> 1` | **必須**（存在＋200バイト＋sentinel） | 前回承認時からの変化を明示レビューさせる |

判定は既存6成果物の検査ヘルパー（存在＋バイト＋sentinel のループ）を再利用する。
iteration を読んで CHANGES.md を「条件付き7枚目」として検査対象に足すだけ。

## 6. データフロー

1. 反復2回目以降、Client モードで要件を編集 → handover フェーズ。
2. LLM が `git diff` / `git log -- docs/requirements/` で前回承認時からの変化を把握し、
   CHANGES.md を執筆（または「変更なし」をチェック）。
3. client がゲートで CHANGES.md をレビューし、承認意思を表明。
4. `/gate client_ready_for_dev approve` → `scripts/update-gate.sh` →
   `check_status.py --pre-approve-gate client_ready_for_dev` が iteration>1 を見て
   CHANGES.md を検査 → 不足なら deny（テンプレ名つき案内）、充足なら approve。

## 7. エッジケース

- **iteration 欠落**: 初回扱い＝不要（fail-open）。iteration は OPTIONAL フィールドで、
  要件変更を伴う再入時は必ず値があるため、欠落を必須化すると初回や iteration 未使用
  プロジェクトで誤 deny する。よって fail-open を採用。
- **要件を変えず Dev だけ回した反復の再承認**: 「変更なし」弁で通す。
- **iteration>1 だが過去に Client ゲート未通過**（Dev 直開始等）: 差分の相手がないので
  全部「追加」扱いか「変更なし」弁で吸収。
- **python3 欠落**: 既存 client ゲート検査と同じ経路に乗るため追加対応不要
  （その経路の既存挙動に追随）。

## 8. 変更コンポーネント一覧

| 種別 | パス | 内容 |
|------|------|------|
| 新規 | `templates/CHANGES.template.md` | 5セクション＋「変更なし」弁＋末尾 sentinel |
| 変更 | `scripts/check_status.py` | `client_ready_for_dev` 検査に iteration>1 条件付き CHANGES.md 検査を追加 |
| 変更 | `scripts/_artifact_template_map.py` | `ARTIFACT_TO_TEMPLATE` に `docs/handover/CHANGES.md` → `templates/CHANGES.template.md` |
| 変更 | `.claude/skills/client-workflow/SKILL.md` | handover 行に「反復2回目以降は CHANGES.md を作成（git diff から執筆）」 |
| 変更 | `scripts/check_framework_contract.py` | `FRAMEWORK_VERSION` を 1.9.0 に。新テンプレを契約に登録 |
| 変更 | `templates/STATUS.template.md` | version を 1.9.0 に同期（contract の version-sync 検査に追随） |
| 新規 | `tests/test_spec_delta_review.py` | 下記テスト観点 |

## 9. テスト観点

`tests/test_client_ready_artifact_content.py` を踏襲し、新規 `tests/test_spec_delta_review.py`:

- `iteration == 1`: 6成果物のみで approve、CHANGES.md 不在でも通る。
- `iteration` 欠落: 同上（fail-open）。
- `iteration > 1` かつ CHANGES.md 不在: deny（テンプレ名つき案内を含む）。
- `iteration > 1` かつ CHANGES.md が 200バイト未満: deny。
- `iteration > 1` かつ sentinel 無し: deny。
- `iteration > 1` かつ「変更なし」弁つき妥当 CHANGES.md: approve。
- `iteration > 1` かつ通常の差分つき妥当 CHANGES.md: approve。
- テンプレ↔参照の sentinel 同期（テンプレ末尾の sentinel が検査側の文字列と一致）。

加えて全体回帰: `pytest`、`make contract`（全 profile）、`make drift`、`make example`
（mirror 差分ゼロ）、`make eval` 系。

## 10. 版・リリース

- 新機能のため minor: **v1.8.0 → v1.9.0**。
- `FRAMEWORK_VERSION` と `templates/STATUS.template.md` の version を同期。
- MIGRATION-HISTORY への追記は ship フェーズで判断（公開契約の変化＝Client ゲートに
  条件付き必須成果物が増えた旨）。

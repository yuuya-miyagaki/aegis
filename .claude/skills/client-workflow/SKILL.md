---
name: client-workflow
description: "Client phase progression rules for Client mode operation."
disable-model-invocation: true
user-invocable: false
---

# Client フェーズ進行ルール

> Client モードのフェーズ進行を統制する正本。各フェーズの産出物・完了条件・
> 遷移ルールを定義する。

## いつ使うか

- `mode = Client` でセッションを開始するとき
- Client フェーズを次に進めようとするとき
- Client → Dev のモード遷移を判断するとき

## フェーズ進行表

| # | フェーズ | 産出物 | 完了条件 | 遷移ルール |
|---|---------|--------|----------|-----------|
| 1 | **onboard** | なし（口頭 or チャット合意） | プロジェクトの目的・背景・主要ステークホルダーをユーザーと確認済み | 合意が得られたら `discovery` へ |
| 2 | **discovery** | なし（調査メモは任意） | 課題・ユーザー・既存システムの調査が完了し、要件定義に着手できる状態 | 調査結果をユーザーに共有し承認されたら `requirements` へ |
| 3 | **requirements** | `docs/requirements/PRD.md` | PRD の全セクションが埋まり、機能要件が列挙され、ユーザーが内容を承認 | PRD 承認後 `scope` へ |
| 4 | **scope** | `docs/requirements/SCOPE.md`, `docs/requirements/NFR.md` | スコープ境界が明確で、NFR が定義され、ユーザーが承認 | SCOPE + NFR 承認後 `acceptance` へ |
| 5 | **acceptance** | `docs/requirements/ACCEPTANCE.md` | 受入条件が機能要件・非機能要件と紐付き、判定基準が明確で、ユーザーが承認 | ACCEPTANCE 承認後 `handover` へ |
| 6 | **handover** | `docs/handover/TO-DEV.md`, `docs/translation/mapping.md`（反復2回目以降は `docs/handover/CHANGES.md` も） | 引き渡し文書が正本ドキュメントを参照し、優先順位・リスク・未解決事項が記載され、ユーザーが承認。translation mapping が作成済みであること（ref 設定は承認直前 — 下記参照） | HANDOVER 承認後、`client_ready_for_dev` ゲートを申請 |

## テンプレート対応表（正本: `_artifact_template_map.py`・テンプレ名は非自明）

- docs/requirements/PRD.md ← templates/PRD.template.md
- docs/requirements/SCOPE.md ← templates/SCOPE.template.md
- docs/requirements/NFR.md ← templates/NFR.template.md
- docs/requirements/ACCEPTANCE.md ← templates/ACCEPTANCE.template.md
- docs/handover/TO-DEV.md ← templates/HANDOVER-TO-DEV.template.md
- docs/handover/CHANGES.md ← templates/CHANGES.template.md
- docs/translation/mapping.md ← templates/TRANSLATION-MAPPING.template.md

## Translation Artifact

handover フェーズに入る前に、`docs/translation/mapping.md` を作成すること。
mapping.md はクライアント用語 → 機能仕様 → 実装ヒントの 3 層変換表。

- テンプレート: `templates/TRANSLATION-MAPPING.template.md`
- 支援 Agent: `translation-specialist`（mapping 作成・更新を委任可能）
- 支援 Skill: `translation-mapping`（手順ガイド）
- Gate 契約: `client_ready_for_dev` 承認時に mapping.md の存在がチェックされる
- **ref 設定のタイミング**: `current_refs.translation` は**承認の直前**に設定し、
  設定→承認（update-gate.sh）を連続実行する。pending のまま ref を置いて完了検査を
  挟むと stale-ref 違反で拒否される。

## Spec Delta（反復2回目以降）

要件改訂で Client モードに再入し `client_ready_for_dev` を申請するときは、
`docs/handover/CHANGES.md` を作成すること。前回ゲート承認時点からの要件差分を、
コードを読まなくても分かる平易な日本語で記し、依頼者が「何がどう変わるか」を確認・承認できるようにする。

- まず `client_ready_for_dev` を `reset` する（approved 据え置きだと再承認が短絡し検査が走らない）
- テンプレート: `templates/CHANGES.template.md`
- 書き方: `git log -- docs/requirements/` と `git diff` で前回からの変化を把握して埋める
- 要件を変えない反復では、テンプレ冒頭「変更なし」にチェックし各セクションを「該当なし」にする
- Gate 契約: `iteration > 1` のとき存在＋200バイト＋sentinel を検査（初回・iteration 無しは不要）

### 関連ディレクトリ

- `docs/client/context.md` — クライアント基本情報（onboard で作成）
- `docs/client/glossary.md` — 用語集（discovery で作成）
- `docs/client/open-questions.md` — 未解決事項（随時更新）
- `docs/translation/mapping.md` — 3 層マッピング（handover 前に作成）
- `docs/decisions/` — 意思決定ログ（随時作成）

## 運用ルール

### フェーズ飛ばしの禁止

- 上記の順序を飛ばしてはならない。
- ただし `onboard` と `discovery` は小規模タスクでは統合可能。その場合
  STATUS.md の `phase` は `discovery` に設定し、`session_history` に
  `onboard+discovery を統合` と記録する。

### 承認の取り方

- 各フェーズの完了条件を満たしたら、ユーザーに明示的に承認を求める。
- artifact があるフェーズでは、「次に進んでよいですか？」ではなく、産出物の内容を提示したうえで確認する。
- artifact がないフェーズ（`onboard`, `discovery`）では、会話で合意した内容を短く要約して確認する。
- ユーザーが承認したら `docs/STATUS.md` の `phase` を更新する。

### artifact がないフェーズの扱い

- `onboard` と `discovery` にはテンプレートがない。
- これらのフェーズでは、チャット上の合意が完了条件となる。
- 必要に応じて調査メモを `docs/requirements/` に残してよいが、必須ではない。
- この間は `current_refs.requirements` を空のまま維持してよい。

### current_refs の更新

- `requirements` で `docs/requirements/PRD.md` を作成したら、`current_refs.requirements` に追加する。
- `scope` で `docs/requirements/SCOPE.md` と `docs/requirements/NFR.md` を作成したら追加する。
- `acceptance` で `docs/requirements/ACCEPTANCE.md` を作成したら追加する。
- `handover` では requirements refs を維持し、`next_action` を handover 完了に合わせて更新する。
- `handover` で `docs/translation/mapping.md` を作成する。`current_refs.translation` への設定はゲート承認の直前（Translation Artifact 節のタイミング規定に従う）。

### モード遷移ゲート

- `handover` フェーズの承認後、`client_ready_for_dev` ゲートをユーザーに申請する。
- ゲートが承認されるまで Dev モードに入ってはならない。
- ゲート承認後、STATUS.md の `mode` を `Dev`、`phase` を `brainstorm` に切り替える。
- Dev へ入る時点では `current_refs.requirements` を維持し、`plan` / `spec` / `review` / `qa` / `security` は未作成なら `null` のままにする。
- `next_action` は「Dev handoff check を行い、brainstorm を開始する」に更新する。

## コンテキスト予算

- Client モードに入ったら本ドキュメントを 1 回読む。
- その後はフェーズに応じた artifact（テンプレートがあればそれ）だけを開く。
- 本ドキュメントを常時保持する必要はない（進行表を把握すれば十分）。

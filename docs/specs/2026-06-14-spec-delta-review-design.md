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
  欠落・薄すぎ・sentinel 無しは deny。**強制点は `client_ready_for_dev` ゲート承認時のみ**
  （完了検査には載せない。理由は §4.3）。
- **判断層（client レビュー）**: 差分の内容が妥当かは client が読んで承認する。hook は
  内容の意味を問わない（既存6成果物と同じ割り切り）。

### 4.3 強制点を「ゲート承認時のみ」に限定する理由（grill-plan C1）
既存6成果物の検査 `_client_artifact_issues` は2か所から呼ばれる——ゲート承認時
（`check_gate_prerequisites` の `client_ready_for_dev` 分岐）と**完了検査**
（`--check-completion-evidence`、`client_ready_for_dev == approved` で発火）。CHANGES を
この共有関数に入れると、client_ready_for_dev は初回承認後ずっと approved 据え置きのため
（§4.4）、**iteration≥2 の全 Dev タスク完了で CHANGES.md を要求**してしまう。要件を変えて
いない純 Dev 反復でも毎回書かされ、「変更なし」弁があっても常時負担になる。

よって CHANGES の検査は `_client_artifact_issues` には入れず、**ゲート承認分岐に限定**する。
具体的には単一 artifact 検査を `_artifact_content_issue(root, rel, sentinel, map)` に切り出し、
ゲート分岐でのみ `_spec_delta_issues(root)`（iteration>1 のとき CHANGES を1件検査）を
追加する。完了経路は6成果物のまま不変。CHANGES は時点レビュー成果物であり、6成果物のような
「承認後に消す」バイパス防止の双方向対称は不要（消しても過去のレビュー事実は覆らない）。

### 4.4 ゲートが sticky-approved である前提と再入リセット（grill-plan C2）
`update-gate.sh approve` は `CURRENT == approved` なら「No change needed」で即 exit し
内容検査を呼ばない。iteration リセット（`dev_ready_for_client` ハンドバック）は **dev ゲート
のみ** を pending 化し、`client_ready_for_dev` は approved 据え置き。したがって、要件改訂で
Client モードに**再入して再申請しても、ゲートが既に approved なら検査は走らない**。

対策（doc-first）: 要件改訂で Client モードに再入する際は、handover 申請前に
`/gate client_ready_for_dev reset`（`update-gate.sh client_ready_for_dev reset`）で
gate を pending に戻すことを **state-machine.md と client-workflow skill に明記**する。
これによりゲート再承認で §4.1 の検査が確実に発火する。既存の iteration リセットも手順
ベース（自動化なし）であり、これと同じ運用粒度。ハンドバック毎の自動 reset は採らない
（mode=Dev は client_ready_for_dev 承認必須という不変条件と衝突し、Dev 反復ループを壊す
リスクがあるため）。決定論ガード化は将来の hardening 候補として backlog に残す。

注: reset は `client_ready_for_dev` の評価 ref（`current_refs.translation`）を null に戻す
（既存 reset 挙動）。mapping.md ファイル自体は残るので、再承認時に ref を再設定すればよい。

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

`client_ready_for_dev` **ゲート承認時のみ**（`check_status.py` の
`check_gate_prerequisites` 内 `client_ready_for_dev` 分岐）に、STATUS.md フロントマターの
`iteration`（top-level の任意整数）を読む。値は `.strip()` してから判定する
（grill-plan 要検討1: 末尾空白で `.isdigit()` が False になり fail-open で黙って無効化
されるのを防ぐ）。

| iteration | CHANGES.md | 根拠 |
|-----------|-----------|------|
| `1` または欠落・非整数 | **不要** | 初回は差分の相手がいない。既存挙動を壊さない（fail-open） |
| `> 1` | **必須**（存在＋200バイト＋sentinel） | 前回承認時からの変化を明示レビューさせる |

判定は単一 artifact 検査ヘルパー `_artifact_content_issue`（既存6成果物ループから切り出し）を
再利用し、ゲート分岐でのみ `_spec_delta_issues(root)` として CHANGES を1件追加検査する。

### 5.1 トリガ代理の限界（grill-plan C3）
`iteration > 1` は「2回目以降の Dev サイクル」を表すだけで、厳密には「要件が改訂された」
ことを表さない。本来の意図イベント＝「前回 client_ready_for_dev 承認時点から要件 doc が
変わった」は git/baseline 判定（一度却下した A2）でしか厳密には捉えられない。本設計は
**(a) ゲート承認時のみ検査＋再入時 reset（§4.3/§4.4）** を採ることで、ゲート再承認＝
意図的な Client 再入のタイミングに限定し、iteration>1 を実用上の代理として用いる。
A2（git 厳密判定）は「小規模拡張」の枠を超えるため採らない。この代理の限界は許容済み。

## 6. データフロー

1. 反復2回目以降、要件改訂のため Client モードに再入し要件を編集 → handover フェーズ。
2. handover 申請の前に `client_ready_for_dev` を `reset`（§4.4）。gate が pending に戻る。
3. LLM が `git diff` / `git log -- docs/requirements/` で前回承認時からの変化を把握し、
   CHANGES.md を執筆（または「変更なし」をチェック）。
4. client がゲートで CHANGES.md をレビューし、承認意思を表明。
5. `/gate client_ready_for_dev approve` → `scripts/update-gate.sh`（pending なので短絡せず）
   → `check_status.py --pre-approve-gate client_ready_for_dev` が iteration>1 を見て
   CHANGES.md を検査 → 不足なら deny（テンプレ名つき案内）、充足なら approve。

## 7. エッジケース

- **iteration 欠落・非整数・末尾空白**: 不要（fail-open）。`.strip()` 後に `.isdigit()`
  で判定し、要件変更を伴う再入では必ず正の整数が入る前提。欠落で必須化すると初回や
  iteration 未使用プロジェクトで誤 deny するため fail-open を採用。
- **ゲートが approved 据え置きで再入**: §4.4 の reset 手順を踏まないと検査が走らない。
  state-machine.md と client-workflow skill に reset を明記し、reset→approve の統合テストで
  発火を保証する。
- **要件を変えず Dev だけ回した反復**: そもそも Client 再入も gate 再承認もしないので
  CHANGES は要求されない（C1 修正によりゲート時のみ検査＝完了時に強制しない）。意図的に
  Client 再入したが実質変更がない場合は「変更なし」弁で通す。
- **iteration>1 だが過去に Client ゲート未通過**（Dev 直開始等）: 差分の相手がないので
  全部「追加」扱いか「変更なし」弁で吸収。
- **python3 欠落**: 既存 client ゲート検査と同じ経路に乗るため追加対応不要
  （その経路の既存挙動に追随）。

## 8. 変更コンポーネント一覧

| 種別 | パス | 内容 |
|------|------|------|
| 新規 | `templates/CHANGES.template.md` | 5セクション＋「変更なし」弁＋末尾 sentinel |
| 変更 | `scripts/check_status.py` | `_artifact_content_issue` 切り出し＋`_spec_delta_required`/`_spec_delta_issues` 追加＋ゲート分岐に CHANGES 検査（完了経路は不変） |
| 変更 | `scripts/_artifact_template_map.py` | `ARTIFACT_TO_TEMPLATE` に `docs/handover/CHANGES.md` → `templates/CHANGES.template.md` |
| 変更 | `templates/profiles/full.json` | `recommended` に `templates/CHANGES.template.md`（parity 契約） |
| 変更 | `.claude/rules/state-machine.md` | iteration/再入の記述に「Client 再入時は `client_ready_for_dev` を reset」 |
| 変更 | `.claude/skills/client-workflow/SKILL.md` | handover 行 ＋ Spec Delta 節（reset 手順・作成手順） |
| 変更 | `scripts/context-budgets.json` | client-workflow の予算を明示的拡大（P1 sanctioned） |
| 変更 | `scripts/check_framework_contract.py` | `REQUIRED_TEMPLATE_FILES` 追加 ＋ `FRAMEWORK_VERSION` を 1.9.0 |
| 変更 | `templates/STATUS.template.md` | version を 1.9.0 に同期（contract version-sync） |
| 変更 | `examples/minimal-project/docs/STATUS.md` | version を 1.9.0 に同期（contract `:921-935`・mirror 対象外＝手動） |
| 新規 | `tests/test_spec_delta_review.py` | 下記テスト観点 |
| 自動 | `examples/minimal-project/...` | `make example` 再生成（check_status.py・_artifact_template_map.py・client-workflow skill が mirror 対象） |

## 9. テスト観点

新規 `tests/test_spec_delta_review.py`（`--pre-approve-gate` 直叩き）:

- `iteration == 1`: 6成果物のみで approve、CHANGES.md 不在でも通る。
- `iteration` 欠落: 同上（fail-open）。
- `iteration > 1` かつ CHANGES.md 不在: deny（`docs/handover/CHANGES.md` を含む）。
- `iteration > 1` かつ 200バイト未満: deny。
- `iteration > 1` かつ sentinel 無し: deny。
- `iteration > 1` かつ「変更なし」弁つき妥当 CHANGES.md: approve。
- `iteration > 1` かつ通常の差分つき妥当 CHANGES.md: approve。
- テンプレ末尾の sentinel が検査文字列と一致。

**統合テスト（grill-plan C2）**: `update-gate.sh` 経由で sticky-approved の穴と reset 復旧を実証:
- iteration=2・client_ready_for_dev=approved・CHANGES 無しで `approve` → 「already approved」短絡（rc0・検査走らず）。
- `reset` → pending → `approve`（CHANGES 無し）→ **deny**（ゲート時検査が発火）。
- CHANGES.md を埋めて `approve` → approve。

完了経路（`--check-completion-evidence`）は CHANGES 非対象（C1）ゆえテスト不要だが、
回帰として「iteration>1・approved・no-CHANGES の完了検査が6成果物のみ評価＝CHANGES を
要求しない」ことを1件確認する。

加えて全体回帰: `python3 -m pytest tests/`（contract/drift/mirror/eval をテスト内で実行）。

## 10. 版・リリース

- 新機能のため minor: **v1.8.0 → v1.9.0**。
- version 同期（suite を落とす hard 要件）: `FRAMEWORK_VERSION`・`templates/STATUS.template.md`・
  `examples/minimal-project/docs/STATUS.md` の3点。ルート `docs/STATUS.md` の version は
  contract 非照合（ship フェーズ/運用者が更新）。
- MIGRATION-HISTORY への追記は ship フェーズで判断（公開契約の変化＝Client ゲートに
  条件付き必須成果物が増えた旨＋再入時 reset 手順）。

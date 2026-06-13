# aegis 機能整合性監査 charter（2026-06-07）

> このファイルは新規セッション（/clear 後）が文脈ゼロから実行できるよう自己完結で書いてある。
> まず本 charter を通読し、`docs/STATUS.md` と `CLAUDE.md` を読んでから着手すること。

## これは何か（前回監査との違い）

前回の「全力監査」（`docs/audit-charter-2026-06-06.md` / `docs/audit-report-2026-06-06.md`）は
**哲学・12能力マトリクス・最新フレーム対比**が中心だった。本監査はそれとは別種で、目的は:

**aegis の各機能が「実際に走る・機能する」か、配線が繋がっているか、過不足が無いかを、細部まで実証的に確かめ、見つかった首（gap/dead/断線）を直して締める。**

合言葉は「読んで判断」ではなく「**動かして確かめる**」。`check_framework_contract` / `check_reference_drift` /
`lint_names` / eval は「登録・ミラー・命名」までは保証するが「実行して機能するか」は保証しない。本監査は
そこを越える。

## 見つけたい4分類（findings の分類軸）

1. **書いてあるが走らない（dead/broken）**: skill/command/hook/script が、参照先不在・exit code 異常・
   壊れた前提・満たせないゲート等で、書いてある通りに機能しない。
2. **走るのに書いてない（hidden/undocumented）**: コード/機構は対応しているのに、それを起動・露出する
   skill/command/doc が無い。
3. **不要（redundant/dead surface）**: どこからも参照・到達されない、または重複・死蔵している surface。
4. **必要なのに無い（missing）**: ある機能が成立するために要る相方（テンプレ/参照/ゲート/記録先）が欠けている。

加えて **構造的連結性**: state machine 遷移・ゲート前提・モード遷移（Client↔Dev）・skill→skill /
hook→script / command→skill の参照グラフが端から端まで繋がっているか。

## スコープ

**対象（全 surface を漏れなく）**:
- `.claude/commands/`（8: status, gate, judge, next, recover, retro, tutorial, validate）
- `.claude/skills/`（18）
- `.claude/agents/`（12）
- `hooks/`（PaC hooks ＋ `hooks/lib/`）と登録（`templates/hooks.template.json` / `.claude/settings*.json`）
- `scripts/`（check_status, check_framework_contract, check_reference_drift, lint_names,
  run_eval, eval_scaffold_smoke, eval_scenario, status_doctor, update-gate.sh, build-judge-card,
  run-test-strength-drill, record-test-result 等）
- `templates/`（各種テンプレ ＋ profiles/*.json）
- `docs/STATUS.md` を中核とする state machine / gate / ref の連結
- 本体 ↔ `examples/minimal-project` のミラー整合（byte 同一）

**非対象（YAGNI）**: 新機能の追加、北極星の再定義、前回監査で決着済みの論点の蒸し返し。

## 方法（4層・実証的・この順で）

### Layer 0: ベースライン（既存機械の green 確認）
- `python3 scripts/check_framework_contract.py --profile=full`
- `python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project`
- `python3 scripts/check_reference_drift.py`
- `python3 scripts/run_eval.py --tier 0`（unittest 全件）/ `--tier 1` / `--tier 2`
- `python3 scripts/check_status.py --root . --strict`
- これらが全 green であることを起点に記録。

### Layer 1: 静的配線トレース（全 surface × 到達性・参照健全性）
- 全 surface を列挙し、各々について:
  - **登録**されているか（contract の REQUIRED_* / profiles / CLAUDE.md ## Skills / hooks.template）。
  - **参照**されているか（どの skill/command/hook/agent/doc から呼ばれる入口があるか）。到達不能な孤児を検出。
  - **参照先が実在**するか（skill 本文が指す script/template/skill/doc・command の allowed-tools・
    hook の command パス・agent の model/effort・テンプレが指す正本）。
- contract/drift が見ない「本文中の相互参照」「command→skill」「skill→script/template」を**人手 grep で追う**。

### Layer 2: 実行検証（動かす）
- `scripts/` の各スクリプトを代表引数で実走し exit code / 出力を確認（異常終了・無言失敗・
  fail-open を検出）。
- 各 hook を代表入力で発火（`hooks/lib/emit.sh` 経由の deny/block/allow が意図通りか。
  破壊コマンド deny が本当に止まるか、pre-compact が STATUS stale で正しく振る舞うか 等）。
- `update-gate.sh` で各ゲートの approve / n/a を temp プロジェクトで実行し、前提・tri-state・
  judge card・B1 ドリルが意図通り発火/ブロックするか。

### Layer 3: ライブ・ドッグフード（端から端まで1周）
- 使い捨てプロジェクトを `bin/setup.sh --profile=full --target=<tmp>` で scaffold。
- **Client→Dev→UAT→handover→保守** を1周通す:
  - Client: onboard→…→acceptance（ACCEPTANCE 作成）→handover→`client_ready_for_dev`。
  - Dev: brainstorm→…→review/qa/security→ship（TO-CLIENT / MANUAL[B3a] / RUNBOOK[B3c] /
    UAT-RESULTS[B3b]）→`dev_ready_for_client`（UAT 存在チェックが効くか）。
  - 保守: 本番起因の bugfix で `maintenance`（Part B）→ bug-diagnosis → RUNBOOK 履歴記録。
- 各段で「skill が指示通り動くか・ゲートが正しく通る/止まるか・成果物が生成されるか」を実地確認し、
  壊れた所を findings に。

### Layer 4: 過不足・構造分析
- Layer 1-3 の結果を4分類（dead/hidden/redundant/missing）に整理。
- state machine（`.claude/rules/state-machine.md`）の全遷移・全ゲート・モード往復が実機構と一致するか。

## 進め方（調査と修正を分ける）

1. **調査フェーズ**: Layer 0-4 を実施し、findings を分類・重大度付きで
   `docs/functional-integrity-audit-report-2026-06-07.md` に記録（前回 report と同様の体裁）。
   **このフェーズではコードを直さない**（明白で無害な1行修正は例外可だが report に明記）。
2. **triage**: findings を「直す/様子見/非対象」に仕分け。首（本当に機能を損なう gap/断線）を優先。
3. **修正フェーズ**: 直すものを通常フローで実装 — コード変更は **TDD**、設計判断が要るなら
   brainstorm、計画は writing-plans、**grill-plan → 実装 → grill-code** の2段グリルを通す。
   `examples/minimal-project` ミラーと version sync を必ず保つ。
4. **再検証**: Layer 0 を全 green に戻し、**ライブ1周（Layer 3）が通る**ことを確認。
5. **版締め**: 修正規模に応じて patch/minor で締め（FRAMEWORK_VERSION＋STATUS/テンプレ同期＋
   README 移行節＋tag）。push/tag はユーザー確認の上。

## ガードレール

- **moat を壊さない**: 決定論的 hooks（PaC）の保証を緩めない。
- **過剰削除しない**: 「到達不能に見える」surface も、消す前に本当に未使用かを実証（grill-premise 的に前提を疑う）。
- **証拠主義**: 「直った」「動く」は実行ログで示す（verification-before-completion）。
- ミラー（本体↔example・byte 同一）と version owner 一本化を崩さない。

## 成果物

- 調査: `docs/functional-integrity-audit-report-2026-06-07.md`（findings・4分類・重大度・証拠）。
- 修正: 通常の feat/fix コミット群（2段グリル経由）。
- 締め: 版締めコミット＋tag、STATUS 同期、MEMORY 更新。

## 完了条件

- 全 surface が Layer 1-3 で「到達可能・参照健全・実行で機能」を確認済み（or 直済み）。
- 4分類の findings がすべて triage され、首が解消されている。
- Layer 0 全 green ＋ ライブ1周（Layer 3）成功。
- report・修正・版締めが揃い、STATUS/MEMORY が最新。

## キックオフ（新セッションの最初の一手）

1. 本 charter・`docs/STATUS.md`・`CLAUDE.md` を読む。
2. TaskCreate で調査フェーズ（Layer 0→1→2→3→4）をタスク化。
3. Layer 0 のベースライン green を取り、Layer 1 の surface 列挙から着手。
4. findings は逐次 `docs/functional-integrity-audit-report-2026-06-07.md` に追記。

## 現在地（着手時点の前提）

- 版: **v1.3.1**（B-series B1-B4 全完了・北極星後半 ⑨⑩⑫ 完成）。main push 済み。
- 直近の構成: 296 unittest・tier0/1/2 PASS・contract(full/standard)・drift・mirror-identity・strict が green。
- 関連: 前回監査 `docs/audit-report-2026-06-06.md`、再アーキ方針（emit.sh 単一出力源・triage・SemVer 安定契約）。

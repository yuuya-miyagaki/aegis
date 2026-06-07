# aegis 機能整合性監査 report（2026-06-07）

> charter: `docs/functional-integrity-audit-charter-2026-06-07.md`
> 目的: 各機能が「実際に走る・配線が繋がる・過不足が無い」かを実証的に確認し、首を直して締める。
> 合言葉: 「読んで判断」ではなく「動かして確かめる」。

## 監査メタ

- 版: v1.3.1（`git describe`: v1.3.1-1-gd91f0c1）
- ブランチ: main / HEAD: d91f0c1（charter コミット）
- 着手日: 2026-06-07
- working tree: クリーン（追跡外 `docs/architecture-overview.pdf` のみ・本監査と無関係）

## findings 分類軸

1. **dead/broken**: 書いてあるが走らない（参照先不在・exit 異常・壊れた前提・満たせないゲート）
2. **hidden/undocumented**: 走るのに書いてない（機構はあるが起動・露出する surface が無い）
3. **redundant**: 不要（到達不能・重複・死蔵）
4. **missing**: 必要なのに無い（成立に要る相方が欠落）

重大度: P1=機能を損なう首 / P2=整合性の傷 / P3=軽微・体裁

---

## Layer 0: ベースライン（既存機械の green 確認）

着手時点で全 green。本監査の修正後もここへ戻すことが再検証条件。

| チェック | コマンド | 結果 |
|---|---|---|
| contract full | `check_framework_contract.py --profile=full` | PASS (exit 0) |
| contract standard | `check_framework_contract.py --profile=standard --root examples/minimal-project` | PASS (exit 0) |
| reference drift | `check_reference_drift.py` | PASS (exit 0) |
| eval tier 0 | `run_eval.py --tier 0` | PASS — 296 tests OK (16.2s) |
| eval tier 1 | `run_eval.py --tier 1` | PASS (exit 0) |
| eval tier 2 | `run_eval.py --tier 2` | PASS (exit 0) |
| status strict | `check_status.py --root . --strict` | PASS (exit 0) |

> tier 0 出力中の `ERROR: Cannot approve 'plan'…` 行は、ゲート前提ブロックを検証する
> scenario テストの**期待出力**（fail-path の正常動作）であり異常ではない。

**Layer 0 結論: ベースライン全 green。** 以降の findings はこの green を起点とする。

---

## Layer 1: 静的配線トレース（surface × 到達性・参照健全性）

### surface インベントリ（charter 想定数と照合）

| 種別 | 実数 | charter 想定 | 一致 |
|---|---|---|---|
| commands | 8 | 8 | ✓ |
| skills | 18 | 18 | ✓ |
| agents | 12 | 12 | ✓ |
| hooks (`hooks/*.sh`) | 16 | — | — |
| hooks/lib | 3 (emit, extract-input, patterns) | — | — |
| scripts | 14 (13 py + update-gate.sh) | — | — |
| templates | 25 .md + hooks.template.json + profiles 3 | — | — |
| rules | 2 (state-machine, routing) | — | — |

### hook 登録の照合

- hooks.template.json は16 hook 全てを登録（孤児 hook なし）。
- `.claude/settings*.json` は本体に存在せず＝aegis 自身の repo では hook 非活性（install で target に展開される正しい設計）。
- example/minimal-project は settings.json で16中14を登録（後述）。

### Finding 1: REQUIRED_HOOK_FILES が稼働 hook 4件を欠く（登録整合性の穴）

- **分類**: missing（contract manifest の欠落）/ **重大度**: P2（PaC enforcement の登録保証に穴）
- **surface**: `scripts/check_framework_contract.py` `REQUIRED_HOOK_FILES`
- **事実**: `REQUIRED_HOOK_FILES` は12 hook（+lib/extract-input）のみ列挙し、`check-cron-gate.sh` /
  `check-skill-gate.sh` / `check-task-created.sh` / `check-task-completed.sh` を欠く。
  この4つは hooks.template.json と example settings.json に登録され、両ツリーに実在し、稼働している。
- **影響**: contract の template 登録チェック（L620-669）は required 集合を `REQUIRED_HOOK_FILES`
  から導出するため、この4 hook が**template から登録解除されても fail しない**。drift の `check_hooks`
  は registered→file-missing しか見ず（unregister は検出不能）。結果、Skill/Cron/Task の PaC
  enforcement hook が黙って無効化されうる。コメントの「single source of truth」表記と実態が乖離。
- **補足**: 内容 drift は `check_mirror_identity`（hooks/ 全体 rglob）が捕捉。main 側のファイル削除は
  drift `check_hooks`（template ref→存在）が、example 側削除は contract のexample-settings→存在チェック
  （L781-809）が捕捉するため、**存在は間接的に守られている**。穴は「template 登録の維持保証」に限定。
- **修正方針（triage 後）**: 4 hook を `REQUIRED_HOOK_FILES`（と必要なら `REQUIRED_EXAMPLE_FILES`）に追加。

### 参照グラフ（command→script / skill→script・template）

- command→script は全て実在: gate→update-gate.sh / judge→build-judge-card.py / retro→retro_report.py /
  validate→check_framework_contract.py・run_eval.py / status→check_status.py / next・tutorial=Read のみ。
- skill→template/script も全て実在（BRAINSTORM-RECORD/SPEC/TRANSLATION-MAPPING/RUNBOOK/MANUAL/
  UAT-RESULTS テンプレ、update-gate/run-test-strength-drill/status_doctor スクリプト）。
- script の入口: learnings_search←retro_report、record-test-result←build-judge-card（読み手/書き手）、
  eval_*←run_eval、lint_names←contract、check_reference_drift/check_status←run_eval/hooks。**孤児 script なし。**
- browser-assist は外部 `gstack/browse` を第一選択、Playwright MCP フォールバック付き（任意外部依存・断線ではない）。

### setup.sh の install モデル（profile 消費）

setup.sh は profile の `required`/`recommended` に**列挙されたファイルだけ**コピー（ディレクトリ一括ではない）。
hook は `hooks_include` から。settings.local.json は hooks_include から生成。
→ profile 列挙漏れ＝install 先で欠落。これが以下 F2-F4 の温床。

各 profile が install する command:
- minimal: なし / standard: gate・status・validate / full: gate・next・recover・retro・status・tutorial・validate（**judge 欠落**）
profile が install する script（meta系）: retro_report・status_doctor・learnings_search・check_framework_contract・
run_eval・check_reference_drift・lint_names・eval_* は**どの profile にも無い**（意図的＝後述）。

### Finding 2: `/judge` が全 profile に無く install されない

- **分類**: missing（install 配線の欠落）/ **重大度**: P2
- **surface**: `templates/profiles/{minimal,standard,full}.json`・`bin/setup.sh`
- **事実**: judge.md は `REQUIRED_COMMAND_FILES`（contract 必須）・example にあり root/example 同一だが、
  どの profile の required/recommended にも無い。一方その裏方 `build-judge-card.py` は full の recommended に有る。
- **影響**: full install でも `/judge`（B2 judge カードのプレビュー）コマンドが配置されず、非エンジニア向け
  tri-state 可視化を手動起動できない（カード生成器だけ届く）。北極星「非エンジニアの judge 可視化」の入口欠損。
- **修正方針**: judge.md を full（必要なら standard）profile に追加。

### Finding 3: setup.sh が非 scaffold-safe な retro.md を install（断線）

- **分類**: dead/broken（install される版が壊れる）/ **重大度**: P2
- **surface**: `bin/setup.sh` `resolve_source()`・`.claude/commands/retro.md` vs example 変種
- **事実**: retro.md は MIRROR_ALLOWLIST に登録された**意図的 scaffold-safe 変種**を持つ
  （example 版＝「retro_report.py が無ければ手動要約に degrade」）。しかし setup.sh の `resolve_source`
  は **validate.md だけ**を example 変種にマップし、retro.md は default（framework root 版）を install。
  framework 版 retro.md は `python3 scripts/retro_report.py --root .` を**無条件実行**。retro_report.py は
  どの profile にも無い。
- **影響**: full install で `/retro` が「retro_report.py が無い」でエラー＝degrade せず壊れる。
  意図された graceful 版（example）が install 経路に繋がっていない＝典型的断線。
- **修正方針**: `resolve_source` に retro.md → example 変種のマップを追加（validate.md と同じ扱い）。
  Layer 2/3 で setup.sh 実走し再現確認する。

### Finding 4: `/recover`（session-recovery）が status_doctor.py に無ガード依存

- **分類**: dead/broken（install で劣化）/ **重大度**: P2
- **surface**: `.claude/skills/session-recovery/SKILL.md` Step 1.5
- **事実**: Step 1.5 が `python3 scripts/status_doctor.py --root .` を「実行し結果確認」と無条件記述。
  status_doctor.py はどの profile にも無く、retro.md のような「if available」ガードも無い。
- **影響**: full install で `/recover`→session-recovery の Step 1.5 が status_doctor.py 不在で失敗しうる。
- **修正方針（要 triage）**: (a) Step 1.5 を「if available」化（retro 例に倣う）か、(b) status_doctor.py を
  profile に追加（運用健全性チェックは runtime 有用なので妥当）。どちらが設計意図かは triage で決める。

### Finding 5: テンプレ非配布と「artifact template を開く」指示の不整合（軽微）

- **分類**: missing/redundant 境界 / **重大度**: P3（advisory・hard break ではない）
- **surface**: `templates/*.template.md`・`bin/setup.sh`・client-workflow Step 90
- **事実**: 全 profile が `templates/*.template.md` を**1件も project に配布しない**（setup.sh は CLAUDE/STATUS/
  LEARNINGS/CLIENT-*/TRANSLATION-MAPPING のみテンプレを成果物として instantiate）。一方 client-workflow は
  「フェーズに応じた artifact template だけを開く」と指示。install 先には PRD/SCOPE/NFR/ACCEPTANCE/PLAN/SPEC/
  REVIEW 等のテンプレが存在しないため、この指示を字義通り実行できない。
- **影響**: 成果物作成自体は skill の構造記述から可能なので破綻はしないが、「テンプレを開く」導線が install 先で空振り。
  テンプレ群は framework repo 専用の参照面として機能している（contract が存在強制）。
- **修正方針（要 triage）**: (a) skill の表現を「テンプレがあれば開く／無ければ skill 内の構造に従う」に整える、
  (b) もしくは必要なテンプレを profile で配布。北極星「非エンジニアが構造に沿って作れる」観点では (b) も一考。

### 到達性まとめ（agents / rules）

- agents 12: routing.md が全 12 を列挙、drift `check_agents`（routing↔agents 双方向）が green ＝孤児/欠落なし。
  subagent-dev skill と Claude routing が起動入口。model/effort は contract が pin 検証（green）。
- rules 2（state-machine/routing）: CLAUDE.md と各 skill から参照、contract 必須。

### Layer 1 結論

- 孤児 surface（どこからも参照されない skill/command/agent/script）は**無し**。
- 断線/欠落の首は **install 経路**に集中（F2 judge 未配布 / F3 retro 非safe版配布＝resolve_source 断線 /
  F4 recover 劣化）。framework repo 内では全配線健全だが、setup.sh で project へ展開した瞬間に欠ける。
- contract manifest の穴（F1: 稼働 hook 4件未登録）は登録整合性の保証に限定された穴。
- F2-F4 は Layer 2/3 で setup.sh 実走＋コマンド実行により実証確認する。

---

## Layer 2: 実行検証（動かす）

### setup.sh 実走（profile=full → temp）で F2/F3/F4 を実証

- F2: `judge.md` が install 先に**不在**（確認）。
- F3: install された retro.md は **framework 版（非 graceful）**。`python3 scripts/retro_report.py --root .`
  を temp で実行 → `No such file or directory`＝`/retro` が degrade せず壊れる（実機再現）。
- F4: `status_doctor.py` が install 先に**不在**（確認）。
- 対照: `check_status.py`（/status の裏方）は install 先で PASS。`/validate`（example 変種）は
  「if available」退避で graceful。settings.local.json は16 hook を7イベントへ正しく生成。

### hook 発火検証（代表入力・moat 健全性）

framework repo 上で stdin に代表 JSON を流して emit 出力を確認。**全て意図通り**:

| hook | 入力 | 期待 | 実測 |
|---|---|---|---|
| check-destructive | `rm -rf /` | ask | ask ✓ |
| check-destructive | `rm -rf node_modules` | allow | allow ✓（safe 例外）|
| check-destructive | `git push --force` | ask | ask ✓ |
| check-destructive | `DROP TABLE` | ask | ask ✓ |
| check-secrets | `git add .env` | deny | deny ✓ |
| check-secrets | `git add ~/.ssh/id_rsa` | deny | deny ✓ |
| check-secrets | `git add -A`（repo に .env/鍵あり）| deny | deny ✓（repo 走査）|
| check-secrets | `git commit`（staged secret）| deny | deny ✓ |
| check-secrets | `cat .env` | allow | allow（設計: 漏洩ベクタは commit）|
| check-skill-gate | skill=update-config | ask | ask ✓ |
| check-skill-gate | skill=tdd | allow | allow ✓ |
| check-cron-gate | prompt に vercel deploy | ask | ask ✓ |
| check-task-created | phase=implement・plan=pending | continue:false | hard stop ✓ |
| check-task-created | phase=implement・plan=approved | allow | allow ✓ |
| check-task-completed | next_action 空 | exit 2 差し戻し | exit 2 ✓ |
| check-gate | src/app.ts・plan pending | deny | deny ✓（後述 F6 修正後の挙動）|
| check-tdd | src/app.ts・テスト変更なし | ask | ask ✓ |

- emit.sh は pure-bash で、python3 不在時も skill-gate/cron-gate/task-created が **fail-closed**（ask/評価継続）。
- `check_status.py --check-completion-evidence` フラグは**実在**（L1315/1343）＝task-completed の evidence
  整合チェックは本物（silent no-op ではない）。
- 注: 上表の check-gate/check-tdd は **framework repo 上で** emit.sh が在るため正常動作。install 先では F6 により死ぬ。

### Finding 6【最重要 P1】setup.sh が emit.sh / patterns.sh を install せず、全 hook が install 先で死ぬ

- **分類**: dead/broken（moat が install 先で全死）/ **重大度**: **P1（最優先・首の本体）**
- **surface**: `bin/setup.sh` `copy_hooks()`（L191-209）
- **事実**: `copy_hooks` は `hooks/lib/extract-input.sh` **だけ**を明示コピーし（L204）、`hooks_include` は
  トップレベル hook（`session-start.sh` 等）のみ列挙。**`hooks/lib/emit.sh` と `hooks/lib/patterns.sh` は
  どこからもコピーされない**。一方、全16 hook が `source .../lib/emit.sh`（16/16）、check-destructive は
  さらに `lib/patterns.sh` を source。
- **実証**: `setup.sh --profile=full`（および `--profile=standard`）で install した temp プロジェクトで
  任意 hook を発火 → `hooks/check-gate.sh: line 13: .../hooks/lib/emit.sh: No such file or directory`、
  `set -euo pipefail` により **exit 1**。install 先 `hooks/lib/` の中身は `extract-input.sh` のみ。
- **影響**: setup.sh で hooks を含む profile（standard / full）を install した瞬間、**決定論的 PaC enforcement
  層が丸ごと無効**。gate ブロック・TDD backstop・破壊コマンド ask・secrets deny・deploy gate・skill/cron gate・
  task hooks・session-start・pre-compact・post-* の全てが source 時に死ぬ。PreToolUse hook の exit 1 は
  非ブロッキング扱い＝**moat が silent に fail-open** し、破壊コマンドや秘密 commit が素通りする。
  これは aegis の最大の価値（LLM 非依存の決定論 hooks）が install 先で消える致命傷。
- **根因**: 2026-06-05 Foundation 改修で emit.sh（単一出力源）と patterns.sh を新設（commit 7cc7b2f）した際、
  `bin/setup.sh copy_hooks`（改修前 840cdd4 由来・extract-input.sh だけコピー）を**更新し忘れた**。
- **なぜ green 検査が見逃したか**: contract/eval/drift/mirror は全て **framework repo と手書き
  example/minimal-project**（emit.sh/patterns.sh が commit 済み）を検証するだけで、**setup.sh の出力を
  一度も実行しない**。install 経路が完全に無検査。本監査「動かして確かめる」が唯一捕捉。
- **修正方針（要 TDD）**: `copy_hooks` を `hooks/lib/*.sh` を全コピーする形に拡張（emit.sh / patterns.sh /
  extract-input.sh）。あわせて setup.sh 出力を実行検証する eval（scaffold→hook 発火 smoke）を追加し、
  install 経路の無検査を恒久的に塞ぐ。

### なぜ既存の scaffold smoke が F6 を見逃したか

`scripts/eval_scaffold_smoke.py`（tier2）は setup.sh を minimal/standard で実走するが、検証は
`check_framework_contract.py --profile=<p> --root=<target>`（**ファイル存在**）のみ。**hook を一度も実行しない**。
emit.sh はどの profile の `required` にも無いので、不在でも contract は PASS。→ install 経路は「ファイルが
揃っているか」しか見ておらず「hook が走るか」は無検査。F6 の修正は smoke に hook 発火を足すべき根拠。

### scripts 実走（framework repo 上・全 PASS）

status_doctor（PASS）/ lint_names（all consistent）/ retro_report（report 出力）/ build-judge-card
（🟡 tri-state カード生成）/ run-test-strength-drill（usage 表示・--spec/--report 必須）。生成物
`docs/qa-reports/judge-review.md` は調査の非改変方針に従い削除済み。

### update-gate.sh gate machine（temp example 複製で実走・全 PASS）

- prereq 強制: brainstorm pending で plan approve → `ERROR: prerequisite gate 'brainstorm' is 'pending'`。
- evidence advisory: current_refs.plan 空で approve → ADVISORY（完了時 TaskCompleted hook で強制）。
- tri-state 委譲: approve は check_status.py `--pre-approve-gate`（0🟢/2🟡ack/1🔴）に委譲。🟡 は
  `approve --ack "理由"` でのみ通過し judge カードに ACK 追記。
- na/reset 安全弁: approved を na 化しようとすると reset 誘導付き ERROR。
- **dev_ready_for_client の UAT 存在チェック**: ACCEPTANCE 有・UAT-RESULTS 無で approve →
  `ERROR: UAT-RESULTS.md が見つかりません … uat skill を使用`。**charter 名指しの懸念＝正しく発火**。

### Layer 2 結論

- **moat の hook ロジックは framework 上で全て健全**（deny/ask/hard-stop/差し戻し すべて意図通り）。
- gate machine（prereq/tri-state/evidence/UAT/mode）も健全。
- 唯一にして致命の破綻は **F6: install 先で hook が source 時に全死**。moat の「設計」は正しいが
  「配送」が壊れている。

## Layer 3: ライブ・ドッグフード（端から端まで1周）

### 実施範囲と F6 による制約

charter は `setup.sh --profile=full` で scaffold した使い捨てプロジェクトで Client→Dev→UAT→handover→保守 を
1周通すことを求める。しかし **F6 により setup.sh full install は hook が全死**するため、install 上での
「ゲートが hook で強制されるライブ1周」は**現時点で成立しない**（gate ブロック・TDD・secrets・task hooks が
発火しない）。これ自体が Layer 3 の最重要 finding（＝F6 の実地確認）。

### 代替で確認できたこと（emit.sh を持つ example 上）

- 状態機械の遷移・prereq・mode ゲート・evidence advisory・UAT 存在チェックは **example/minimal-project
  （hook lib 完備）上で end-to-end に機能**（Layer 2 の gate machine 検証で実証）。
- 成果物テンプレ（ACCEPTANCE/HANDOVER/MANUAL/RUNBOOK/UAT-RESULTS）は実在し skill から参照される（Layer 1）。

### 観察（軽微）

- example/minimal-project は ACCEPTANCE 有・UAT-RESULTS 無のため dev_ready_for_client を承認できない
  「Dev 途中」状態。完結デモとしては UAT-RESULTS.md を同梱すると北極星の保守完結まで見せられる（P3・任意）。

### Layer 3 結論

- **F6 修正後に、charter 規定の「setup.sh full → ライブ1周」を再実行して通すことが完了条件**
  （charter §進め方-4「再検証: ライブ1周が通る」に合流）。
- 現状の gate/状態機械ロジックは example 上で健全と確認済み。

## Layer 4: 過不足・構造分析

### 4分類整理

| 分類 | findings | 要点 |
|---|---|---|
| dead/broken（書いてあるが走らない）| **F6（P1）**, F3, F4 | install 先で hook 全死（F6）／retro 非safe版配布（F3）／recover の status_doctor 無ガード（F4）|
| hidden/undocumented（走るのに書いてない）| （該当なし）| framework 上の機構は概ね露出済み |
| redundant（不要・死蔵）| （明確な死蔵なし）| 孤児 surface ゼロ。テンプレ群は framework 参照面として機能 |
| missing（必要なのに無い）| F1, F2, F5 | contract が hook4件未追跡（F1）／judge 未配布（F2）／テンプレ非配布と指示の不整合（F5）|

### 構造的連結性（state machine ↔ 実機構）

- modes（Client/Dev）・phases・gate 順序・mode ゲート（client_ready_for_dev / dev_ready_for_client）は
  `.claude/rules/state-machine.md` と check_status.py の実装が一致（prereq・UAT・evidence を実走確認）。
- 断線は「状態機械の論理」ではなく「**install 配送**」に集中（setup.sh の F2/F3/F6）。

### 根本原因の共通項

F2/F3/F6 はいずれも **setup.sh が framework の進化に追従していない**ことに起因:
- emit.sh/patterns.sh 新設（Foundation）に copy_hooks 未追従（F6）。
- judge コマンド新設（B2）に profile 未追従（F2）。
- retro scaffold-safe 変種に resolve_source 未追従（F3）。
→ 共通対策: **setup.sh 出力を実行検証する eval（scaffold→hook 発火 + コマンド実行 smoke）**を追加し、
install 経路を恒久的に契約化する。これが個別修正より効く構造対策。

---

## Layer 3: ライブ・ドッグフード（端から端まで1周）

（未着手）

---

## Layer 4: 過不足・構造分析

（未着手）

---

## findings 一覧（随時追記）

| ID | Layer | 分類 | 重大度 | surface | 概要 | 状態 |
|----|-------|------|--------|---------|------|------|
| F1 | L1 | missing | P2 | check_framework_contract.py | REQUIRED_HOOK_FILES が稼働 hook 4件を欠く＝template 登録の維持保証に穴 | ✅修正済 |
| F2 | L1 | missing | P2 | profiles/*.json | `/judge` が全 profile に無く install されない（裏方 build-judge-card.py は full に有） | ✅修正済 |
| F3 | L1 | dead/broken | P2 | bin/setup.sh resolve_source | retro.md の scaffold-safe 変種が install に繋がらず、非safe版が配布され `/retro` がエラー | ✅修正済 |
| F4 | L1 | dead/broken | P2 | session-recovery SKILL | Step1.5 が status_doctor.py を無ガード実行（profile 未配布）→ `/recover` 劣化 | ✅修正済（案b: 配布）|
| F5 | L1 | missing | P3 | templates/・client-workflow | テンプレ非配布なのに「artifact template を開く」指示＝install 先で空振り（hard break なし） | 未triage |
| **F6** | **L2** | **dead/broken** | **P1** | **bin/setup.sh copy_hooks** | **emit.sh/patterns.sh を install せず、standard/full install 先で全 hook が exit 1 で死＝moat 全死・silent fail-open** | **✅修正済** |
| F7 | L2 | redundant | P3 | check_reference_drift.py | scaffold-safe を表す集合が2つあり食い違う（`MIRROR_ALLOWLIST={validate,retro}` vs `intentional_divergence={validate}`）。現状は両 command が root 実在で無害だが latent。grill-plan(F3) 由来 | 未triage |

## triage 推奨（調査→修正の橋渡し）

> 修正フェーズは TDD＋2段グリル＋ミラー/version sync 維持で進める（charter §進め方-3）。以下は推奨順。

1. **F6（P1・最優先・首）** — `setup.sh copy_hooks` を `hooks/lib/*.sh` 全コピーに直し、**install 先で hook が
   走る**状態に戻す。同時に `eval_scaffold_smoke.py` に「scaffold 後に代表 hook を実発火して deny/ask が
   出るか」の smoke を足し、install 経路を契約化（F6 の再発防止＝構造対策）。これが最大の moat 修復。
2. **F3（P2）** — `resolve_source` に retro.md→example 変種マップを追加（F6 の copy_hooks 修正と同じ
   setup.sh 内なので併せて）。
3. **F2（P2）** — judge.md を full（必要なら standard）profile に追加。build-judge-card.py が既に配布される
   full では特に整合が必要。
4. **F4（P2）** — session-recovery Step1.5 を「status_doctor.py があれば実行／無ければ STATUS 目視」に
   ガード化（retro 例に倣う）。または status_doctor.py を profile 配布。triage で設計意図を確認。
5. **F1（P2）** — 4 hook を `REQUIRED_HOOK_FILES`（＋必要なら example 必須）に追加し、contract の
   「single source of truth」表記を実態に一致させる。
6. **F5（P3・任意）** — テンプレ非配布と「artifact template を開く」指示の表現整合。

**再検証（charter §進め方-4）**: 修正後に Layer 0 全 green ＋ **setup.sh full → ライブ1周（Layer 3）が
hook 強制込みで通る**ことを確認して締める。

## 修正ログ

### F6（P1）— 修正済

- 計画: `docs/plans/f6-install-hook-lib-fix-plan.md`（grill-plan 反映済）。
- 変更: `bin/setup.sh` copy_hooks を `hooks/lib/*.sh` 全コピーに／`scripts/eval_scaffold_smoke.py` に
  `verify_hooks_runnable`（hook 実発火検証）を追加し install 経路を契約化。
- TDD: RED（3 profile FAIL: emit.sh 不在）→ GREEN（copy_hooks 修正で 3 profile PASS）。
- 検証: tier0(296)・tier1・tier2・contract(full/standard)・drift・--strict 全 green。
  実 install（full）で check-destructive→ask / check-secrets→deny / check-gate→allow / session-start 無エラー
  を再確認＝moat 復活。grill-code＝マージ可（Critical 0）。
- ミラー: setup.sh / eval_scaffold_smoke は MIRROR 対象外のため example 同期不要。version は版締めまで保留。

### F3+F2（P2）— 修正済

- 計画: `docs/plans/f3-f2-install-command-fidelity-plan.md`（grill-plan 反映済）。
- 変更: `bin/setup.sh` resolve_source に retro.md→example 変種マップ追加（F3）／`templates/profiles/full.json`
  required に judge.md 追加（F2）／`scripts/eval_scaffold_smoke.py` に `verify_command_surface` 追加。
- 回帰防止: `MIRROR_ALLOWLIST` を import し「allowlist コマンド ⊆ resolve_source 配線」を自己強制（F3 と
  同型の「足したが配線忘れ」class を封鎖）。retro は graceful guard 句、full は judge 存在も検証。
- TDD: RED（full で retro 非example変種＋guard欠落＋judge不在の3件 collect）→ GREEN（3 profile PASS）。
- 検証: tier0(296)/1/2・contract(full/std)・drift・--strict 全 green。実 full install で `/retro` graceful
  （guard 句あり）・`/judge` 存在を再確認。grill-code＝マージ可（guard 文字列を具体句に絞る🟡を反映済）。
- 新 finding: F7（drift の scaffold-safe 集合の二重・食い違い・P3・latent）を記録。

### F4（P2）— 修正済（採用: 案b status_doctor を配布）

- 計画: `docs/plans/f4-recover-status-doctor-guard-plan.md`。grill-plan で当初案(a graceful ガード)の
  「(b)却下＝minimal/standard 用ガードが要る」前提が**事実誤認**と判明（session-recovery は full のみ同梱・
  status_doctor 参照は session-recovery 1箇所）。ユーザー承認のうえ **(b) status_doctor を full に配布**へ転換。
- 北極星整合: status_doctor の健全性チェックは決定論＝harness 仕事。(a) の「LLM 手動目視」格下げより (b) が原則整合。
- 変更: `full.json` recommended に status_doctor.py 追加／example へ byte 一致コピー＋`MIRROR_FILES`・
  `REQUIRED_EXAMPLE_FILES` 追加／`PLACEHOLDER_ALLOWLIST` に CLI usage トークン `<project_root>` 追加（巻き込み
  ゼロを実証）／`eval_scaffold_smoke` に `verify_status_doctor`（full で実在＋実行を検証）。session-recovery SKILL は無編集。
- TDD: RED（full に status_doctor 不在）→ GREEN（配布で実在＋実行）。tier0(296)/1/2・contract(full/std)・
  drift(mirror 含)・strict 全 green。実 full install で status_doctor 実在＋`--root .` が正常出力を再確認。
  grill-code＝マージ可（Critical 0）。

### F1（P2）— 修正済

- 計画: `docs/plans/f1-required-hook-files-coverage-plan.md`（grill-plan 反映済）。
- 変更: `check_framework_contract.py` の `REQUIRED_HOOK_FILES`＋`REQUIRED_EXAMPLE_FILES` に4 hook
  （skill/cron/task-created/task-completed gate）を追加／`tests/test_hook_required_coverage.py` 新規。
- 副次効果: 4 hook を REQUIRED に入れたことで contract 既存の「REQUIRED⊆registered」が**直接** F1 の穴
  （4 hook が template から外れたら FAIL）を塞ぐ。新 test は逆向き「registered⊆REQUIRED」を root/example
  両方向で守る（example も同型の穴を持っていた＝grill-plan で判明）。向きは ⊆（required-but-unregistered の
  将来正当ケースを誤検知しないため）。
- TDD: RED（root/example で4件不足）→ GREEN。tier0(298)/1/2・contract(full/std)・drift・strict 全 green。
  grill-code＝マージ可（Critical 0）。

## 完了サマリ（調査フェーズ）

- Layer 0-4 完了。findings 6件（**P1×1**, P2×4, P3×1）。
- 核心: aegis の moat（決定論 hooks・gate machine・evidence 強制）は**設計は健全**だが、**setup.sh の
  install 配送が framework 進化に追従できておらず、install 先で hook が全死（F6）**。静的 green 検査群
  （contract/eval/drift/mirror）は framework repo と手書き example しか見ず、install 経路が無検査だった。
- 「動かして確かめる」が静的検査の死角（install 実行）を突いて P1 を捕捉＝本監査の主眼を達成。

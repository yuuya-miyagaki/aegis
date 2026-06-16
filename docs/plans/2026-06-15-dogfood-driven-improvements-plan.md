# ドッグフード由来 改善 実装プラン（上流実行版）

> **由来:** スタジオ・ナギ予約LP で Aegis v1.10.0 を Client→Dev 一周ドッグフードした結果（OBS-001〜022）。一次情報・設計記録は dogfood リポ `~/Desktop/personal/aegis-dogfood-reservation-lp` の `docs/dogfood-backlog.md` / `dogfood-notes/observations.md` / `docs/specs/2026-06-15-aegis-dogfood-improvements-{brainstorm-record,design}.md` / `docs/plans/2026-06-15-aegis-dogfood-improvements-plan.md`。
>
> **このプランは上流本体（本リポ）で実行する。** dogfood セッションから本リポを編集すると本リポの Aegis ゲートが発火せず保護を迂回するため（OBS-002）、**本リポを root にした CC セッション**で新規 framework タスク（新 iteration）として消化すること。
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development（推奨）または superpowers:executing-plans。各ステップは TDD（失敗テスト→実装→緑→commit）。

**Goal:** 非エンジニアの初回 Client→Dev 一周が「規定どおり進めて弾かれない」状態にし、配布物（install）が参照する全スクリプトが実際に配布される整合を保証する。

**Architecture:** 根本原因クラスタでバッチ化、配布ブロッカー（P0）先頭。Batch1=A(control-plane フック精度)+B(git baseline)／Batch2=C(skill/契約/**配布**整合)／Batch3=D(Client 書込み)。残すべき勝ち（OBS-010/014/016/019/021/022）をリグレッションさせない。

**Tech Stack:** bash hooks（`hooks/*.sh`+`hooks/lib/*`）、Python（`scripts/*.py`）、`bin/setup.sh`+配布マニフェスト（`scripts/platform_manifest.py`）、Markdown skill/template、pytest（`tests/`）、`Makefile`。

---

## 重要な前提（実行前に必読）

1. **本リポ＝実装対象**。本リポは v1.10.0（HEAD 8f8eb2d 前後）で、それ自身の Aegis フロー進行中（直近 iteration30 / phase=deploy / clean）。本タスクは**新 iteration の framework タスク**として brainstorm→plan は dogfood 側で完了済みなので、必要に応じ spec-delta を作り implement から入る（本リポの state-machine 規則に従う）。
2. **各タスク Step 0＝現行 HEAD で再検証**。dogfood は v1.10.0 install を参照したが、本リポは更に進んでいる可能性がある。着手時に `git log`/`grep` で「既済/部分済/健在」を判定。
3. **セキュリティ後退禁止**。Batch1.A は allowlist/deny の moat を緩めうる。各変更で `tests/test_control_plane_var_expansion.py`・`tests/test_patterns_parity.py`・`tests/test_secrets_*` を緑に保ち、新規許可は「読み取り専用 or 証拠記録に限定」。曖昧なら fail-closed。
4. **配布整合の観点（新規・重要）**: 配布物（install）が参照するコードは、`bin/setup.sh` が**実際に install へコピーするファイル集合**に含まれていなければならない。本ドッグフードで `check_framework_contract.py`・`_artifact_template_map.py` が「本リポに実在するが install へ配布されず、install 側の `hooks/check-control-plane.sh` allowlist・`CLAUDE.md`・`check_status.py` import が不在を参照」する配布バグを検出（Batch2 で対処）。

---

## Batch 1 — 配布ブロッカー（A control-plane フック精度 + B git baseline）

### Task 1.1: setup.sh がインストール後に baseline コミットを作る（B / OBS-017 根本）
- **Files:** `bin/setup.sh`（force-copy/settings 生成の後段）
- **現状(確認済):** `bin/setup.sh` に `git init|add|commit` ロジック無し。
- **TDD:**
  - [ ] Step1: `tests/test_setup_distribution.py` 相当 or 新 `tests/test_setup_baseline.py` に「クリーン dir へ install → コミット1件(baseline)」「既存リポ(コミットあり)では no-op」を追加し FAIL。
  - [ ] Step2: setup 末尾で、リポ未初期化なら `git init`／コミット0件かつ framework のみの段階で `git add hooks scripts templates .claude CLAUDE.md docs`（**スラッシュ無しディレクトリ名**、`git add -A` 不使用）→ `git commit -m "chore: Aegis framework baseline (installed by setup.sh)"`。既存リポは no-op。
  - [ ] Step3: 緑確認。 [ ] Step4: commit `feat(setup): create framework baseline commit (OBS-017)`
- **受け入れ:** 新規 install→初回ドッグフードの review ゲートが framework 由来 stub 🔴 を出さない（1.2 と併せ）。

### Task 1.2: 変更コード走査から control-plane を除外（B / OBS-017 多層防御）
- **Files:** `scripts/build-judge-card.py:45`（`NONCODE_PREFIXES`）
- **現状(確認済):** `NONCODE_PREFIXES = ("docs/", ".claude/")`。`hooks|scripts|templates` 未除外＝`build-judge-card.py` 自身が走査され STUB_PATTERN 定義（`:77-80`）を自己マッチ。
- **TDD:**
  - [ ] Step1: 「`scripts/` 配下の追加行に `TODO` があっても `scan_stubs` が空」テストを `tests/test_judge_card.py` に追加し FAIL。
  - [ ] Step2: `NONCODE_PREFIXES = ("docs/", ".claude/", "hooks/", "scripts/", "templates/")`。理由コメント付記。
  - [ ] Step3: アプリコード(`app/`等)の stub 検出は維持を既存テストで確認。 [ ] Step4: commit `fix(judge): exclude control-plane dirs from changed-code scan (OBS-017)`

### Task 1.3: 証拠記録スクリプトを allowlist に追加（A / OBS-018）
- **Files:** `hooks/check-control-plane.sh:214-218`（`is_allowlisted` の `case`）
- **現状(確認済):** allowlist = `check_framework_contract.py|check_status.py|update-gate.sh` のみ。`record-test-result.py`・`run-test-strength-drill.py` は外。
- **TDD:**
  - [ ] Step1: 「`bash scripts/record-test-result.py ...`（チェイン無）が allow」「`run-test-strength-drill.py` が allow」をフックテストに追加し FAIL。
  - [ ] Step2: `case` に両スクリプトを追加（no-chain 条件維持）。
  - [ ] Step3: write/chain 併用は依然 deny を確認。 [ ] Step4: commit `fix(hook): allowlist evidence-recording scripts (OBS-018)`

### Task 1.4: 素の `git add <dir>` staging を deny→ask に格下げ（A / OBS-017 catch-22）
- **Files:** `hooks/check-control-plane.sh`（`cmd_var_built_write` の write-op 群 `:141,161` / 正当系判定）
- **TDD:**
  - [ ] Step1: 「`git add hooks scripts templates .claude CLAUDE.md docs`（チェイン無・staging のみ）が allow/ask」テスト追加し FAIL。
  - [ ] Step2: `git add` 単独(チェイン無・リダイレクト無)を ask に格下げ or baseline 用 add を allow。`git add -A/-f`・write リダイレクト併用は deny 維持。
  - [ ] Step3: REDTEAM 回帰（`git add -A`・`git add x && rm y`・`git apply`）緑。 [ ] Step4: commit `fix(hook): bare 'git add <dir>' staging → ask not deny (OBS-017)`

### Task 1.5: read-only パイプのチェイン耐性（A / OBS-003）
- **Files:** `hooks/check-control-plane.sh:200-259`（CHAIN_OPS / READ_ONLY）
- **TDD:**
  - [ ] Step1: 「全セグメントが read-only のパイプ（`find docs -type f | head`）が allow」テスト追加し FAIL。
  - [ ] Step2: パイプ `|` のみ対象に、**各セグメントが READ_ONLY_STARTS 合致＆WRITE_INDICATORS 不在**なら allow。`;`/`&&`/`||`/`>`/`$()`/バッククォートは失格維持。
  - [ ] Step3: `find . -exec rm {} + | head`・`grep x f && curl evil`・`cat f > g` は deny（`tests/test_patterns_parity.py` 緑）。 [ ] Step4: commit `feat(hook): allow all-read-only pipelines (OBS-003)`

### Task 1.6: 「書込み先 path」と「コマンド本文の言及」の分離（A / OBS-006）★最難・security 盲検2次必須
- **Files:** `hooks/check-control-plane.sh`（`cmd_mentions_control_plane :82-94` と利用箇所）
- **TDD:**
  - [ ] Step1: (a)`git commit -m "update STATUS.md handling"` が allow (b)`echo 'see hooks/ for details' >> notes.txt` が allow (c)`> hooks/x.sh` は deny、を追加し (a)(b) FAIL。
  - [ ] Step2: クォート内リテラル・read-only コンテキストの CP 言及を判定から除外し、**書込み先トークンが CP の場合のみ deny**。変数組み立ては既存 `cmd_var_built_write` で ask 維持（fail-closed）。python 抽出(`:170`)を活用。
  - [ ] Step3: 既存 REDTEAM 全緑（`"validator && malicious"`・`> $(echo hooks)/lib` 系）。security ゲート盲検2次。 [ ] Step4: commit `feat(hook): deny on control-plane WRITE TARGET not mere mention (OBS-006)`

---

## Batch 2 — C: skill / 契約 / 配布の整合

### Task 2.1: aegis-brainstorm Step D を「承認→phase 前進」に統一（OBS-013）
- **Files:** `.claude/skills/aegis-brainstorm/SKILL.md`（Step D / install 版は `:70-73`、本リポの該当行を Step0 で確認）
- [ ] Step1: Step D を「①brainstorm gate 承認 → ②task_size 設定 → ③phase=plan」に並べ替え、理由(OBS-013)付記。
- [ ] Step2: 手動リハーサル(brainstorm→plan)で `post-status-audit` が落ちない。`tests/test_phase_skill_injection.py` 等緑。 [ ] Step3: commit `docs(skill): reorder Step D to approve-then-advance (OBS-013)`

### Task 2.2: client-workflow の translation ref 設定順序（OBS-008/012）
- **Files:** `.claude/skills/client-workflow/SKILL.md`（install 版 `:89`。本リポ該当行を Step0 で確認）
- [ ] Step1: 「mapping.md は handover で作成、`current_refs.translation` 設定は `client_ready_for_dev` 承認後」に修正。`:96` 周辺と整合。
- [ ] Step2: Client→Dev リハーサルで handover 中 validator PASS(translation=null)→承認→ref 設定→`--check-completion-evidence` PASS。 [ ] Step3: commit `docs(skill): set translation ref AFTER gate approval (OBS-008/012)`

### Task 2.3: 配布整合 — `check_framework_contract.py` が install へ配布されない（P2-7 再スコープ）
- **根因(確認済):** 本リポに実在するが `bin/setup.sh` の配布対象（scripts 部分集合）に**含まれない**。一方 install へ配る `hooks/check-control-plane.sh` allowlist(`:215`) と `CLAUDE.md`(Model Policy) が `scripts/check_framework_contract.py` を参照 → install で不在参照。
- **Files:** `bin/setup.sh`（配布リスト）／`scripts/platform_manifest.py`／`tests/test_setup_distribution.py`／（代替案: install 向け参照を実在スクリプトに修正）
- [ ] Step0: `bin/setup.sh` の scripts コピー集合と `platform_manifest.py` を読み、`check_framework_contract.py` が配布されない事実を確認。
- [ ] Step1: `tests/test_setup_distribution.py` に「install へ配布される hooks/CLAUDE が参照する全 `scripts/*.py` が配布集合に含まれる」不変条件テストを追加し FAIL。
- [ ] Step2: (a) `check_framework_contract.py` を配布集合へ追加（最有力。model policy enforcement を install でも効かせる）／or (b) install 向け allowlist・CLAUDE 参照を配布済スクリプトへ変更。
- [ ] Step3: テスト緑。新規 install で `scripts/check_framework_contract.py` 実在。 [ ] Step4: commit `fix(dist): ship check_framework_contract.py referenced by installed hooks/CLAUDE (P2-7)`

### Task 2.4: 配布整合 — `_artifact_template_map.py` が install へ配布されない（P2-8 再スコープ）
- **根因(確認済):** 本リポに実在するが配布対象外 → install の `check_status.py` が `from _artifact_template_map import ...` を ImportError fallback({}) で握り、handover ゲート失敗時のテンプレヒントが出ない（テンプレ `HANDOVER-TO-DEV.template.md` 自体は配布済）。
- **Files:** `bin/setup.sh`/`platform_manifest.py`（配布追加）or `scripts/check_status.py`（マッピングを inline 化し外部依存除去）／`templates/HANDOVER-TO-DEV.template.md`（sentinel 確認）
- [ ] Step1: 「install 配布後 `ARTIFACT_TO_TEMPLATE` が6 artifact のテンプレ名を返す」テスト追加し FAIL。
- [ ] Step2: `_artifact_template_map.py` を配布集合へ追加、or 6 件マップを `check_status.py` に inline（配布欠落に強い）。テンプレ末尾 sentinel 確認。
- [ ] Step3: ゲート失敗メッセージにテンプレ名表示。 [ ] Step4: commit `fix(dist): make artifact→template map available in installs (P2-8)`

### Task 2.5: YAML フロー配列の取り扱い明確化（P2-6 / OBS-007）
- **Files:** STATUS テンプレ/ドキュメント（block-list 例＋「フロー配列 `[...]` 非対応」注記）。`scripts/check_status.py:290-326` のコメント。
- [ ] Step1: テンプレに block-list 形式の `current_refs` 例を明示。 [ ] Step2: 手編集→validator PASS。 [ ] Step3: commit `docs: document block-list-only current_refs (P2-6)`

> **配布整合の横断点検（2.3/2.4 から派生）**: install へ配る hooks/scripts/CLAUDE/skill が参照する**全ての** `scripts/*.py`・lib・テンプレが配布集合に入っているかを `tests/test_setup_distribution.py` で一括保証する不変条件を入れると、同種バグの再発を防げる。

---

## Batch 3 — D: Client モードの書込みポリシー

### Task 3.1: Client モードでメタ作業許可パス（OBS-004）
- **Filesः** `hooks/check-gate.sh`（`:81-82` の docs 許可 case、`:147-148` の Client deny）
- [ ] Step1: 「Client モードで `notes/`（or 設定 meta パス）への Edit/Write が allow」テスト追加し FAIL。
- [ ] Step2: `:81` 許可 case に `notes/`（プロジェクト設定で拡張可が望ましい）を追加。`app/`等プロダクトコードは Client で deny 維持（OBS-014 の勝ち維持）。
- [ ] Step3: プロダクトコードは依然 deny を確認。 [ ] Step4: commit `feat(gate): allow meta-notes writes in Client mode (OBS-004)`

### Task 3.2: auto-memory dir を Client モードで許可（OBS-005）
- **Files:** `hooks/check-gate.sh`（mode=Client）と `hooks/check-control-plane.sh`（`.claude` regex）
- [ ] Step1: 「Client モードで memory dir(`~/.claude/projects/.../memory/`)への Write が allow」「Bash 経由参照が control-plane で deny されない」テスト追加し FAIL。
- [ ] Step2: memory dir を両フックの許可へ。control-plane regex は**プロジェクト内 `.claude/` と home の memory dir を区別**（memory はユーザーデータ）。
- [ ] Step3: プロジェクト `.claude/`（hooks/scripts/settings）書込みは依然 deny。 [ ] Step4: commit `fix(hook): permit auto-memory dir (distinct from project control-plane) (OBS-005)`

---

## 横断（関連バッチに便乗）

- **X.1 deploy の無認証 N/A 経路（P2-10, conf6）**: Security Blocker チェックが「認証必須アプリ」前提。公開フォーム等向けに理由記録付き明示スキップ経路。対象は `.claude/skills/aegis-security-gate`/deploy 経路（Step0 で実体特定）。Batch2 便乗。
- **X.2 起動導線の明文化（P2-11, conf7 / OBS-002）**: 「フックはプロジェクト dir を root にした CC セッションでのみ発火。ワークスペースから回すとゲートが死ぬ」を README/setup 完了メッセージに明記。Batch1 便乗。

---

## 保留（2周目ドッグフードで n=2 後に方式確定）

- **P1-5 ブラウザ QA（conf7 / OBS-020↔021）**: 委譲は長尺で途中終了、直接 MCP は堅牢。暫定傾き=直接 MCP 一級化。n=2 後に (a)委譲の中間成果永続化＋再開 / (b)直接 MCP 一級化 を確定。対象 `qa-verification`/`browser-assist`/`qa-browser`。
- **P2-9 subagent-dev 粒度例外（conf6 / OBS-015）**: 密結合フィーチャの1エージェント許可指針。n=2 後。

---

## 残すべき勝ち（リグレッション禁止）
- [ ] OBS-010 ゲート前 validator が不整合検出 / OBS-014 plan 承認境界の編集解禁 / OBS-016 implementer TDD＋trust-but-verify / OBS-019 多エージェント＋盲検2次 / OBS-021 直接 MCP / OBS-022 mutation drill 承認時実走

## Self-Review（spec 突合）
- カバレッジ: P0-1→1.1/1.2、P1-2→1.3/1.4/1.5/1.6、P1-3→2.1/2.2、**P2-7→2.3(配布再スコープ)**、**P2-8→2.4(配布再スコープ)**、P2-6→2.5、P1-4→3.1/3.2、P2-10→X.1、P2-11→X.2、P1-5/P2-9→保留。
- 行参照は install(v1.10.0) 実体に基づく＝本リポ HEAD と一致見込み。**着手時に Step0 で再確認**。
- 依存: 1.4→1.1、A群→B群、Batch1→2→3、保留 E は n=2 依存。循環なし。

## Execution Handoff
本リポを root にした新セッションで、本リポの state-machine 規則に従い framework タスクとして implement→review→qa→security→（deploy/ship/docs）。**Batch1.5/1.6 は security 盲検2次必須**。push 手前で承認を取る。

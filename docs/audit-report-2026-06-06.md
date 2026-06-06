# Aegis 全力監査レポート（2026-06-06）

> 起点: `docs/audit-charter-2026-06-06.md`。対象: **aegis v1.0.0**（F→R→A→D 再アーキ完了）。
> 監査方針: 2層構造（機械的健全性 → 哲学/設計妥当性）。最新フレームワークは web 実調査。
> **境界（charter §6）**: 本監査は読み取り・検証・記述に徹し、コード変更は行わない。再設計が要る論点は §4 優先度4 に分離し、別途 brainstorm→設計→grill→実装の通常フローへ渡す。

## エグゼクティブサマリ

機械層のベースラインは**全 green**（195 tests / eval tier 0-3 / contract full+standard / reference drift / status --strict すべて PASS、2026-06-06 実測）。しかし「green が証明しないもの」を精査した結果、北極星と moat に関わる実質的な所見が3領域で出た。

1. **自己検証が mirror drift を検知できない（🔴 C1）** — `check_framework_contract --profile=standard` が、Model Policy 節も hook-enforcement 行も欠落した stale な example に対して PASS する。「壊れたら検知できる構造か」への答えが、最重要の mirror 面で **No**。future-proof 看板「drift をハーネスが告げる」が未達。
2. **決定論的保証の実装が宣言より緩い（🟠 H1-H3 / 🟡 M1-M2）** — aegis の哲学的 moat は「書いたルールは無視される前提 → hook で決定論的に強制」。だが deploy ゲートは `npx vercel deploy` で素通り、gate 系 hook 3本は python3 不在で fail-OPEN、completion-evidence は違反時も exit 0。哲学は正しいが実装が哲学に追いついていない。
3. **ライフサイクル後半と「品質を非エンジニアが判断する」層が薄い（能力 ⑥⑨⑩⑫ / 哲学 P1-P2）** — マニュアル・納品時 UAT 実行・保守運用の構造が急減。さらに「テストが意味あるか」「成果物が崩れていないか」は未測定で、その最終ジャッジを非エンジニアができない。

哲学の賭け自体（hooks-as-guarantees × 非エンジニア×フルライフサイクル）は **2026 の本流かつ競合不在のニッチ**で筋が良い（§3）。課題は思想でなく、(a) moat である決定論的保証を実装水準で哲学に追いつかせること、(b) 北極星後半（保守まで／非エンジニアの judge）の構造的充足、の2点に集約される。

### 検証来歴（intellectual honesty）

[自己再現] = 監査担当が現物を読み/diff/実行して確認。[並列確認] = サブエージェントが /tmp コピー等で再現報告（未完全二次裏取り）。各所見に明記する。

---

## ① 機械層 所見（重大度別）

### 🔴 CRITICAL

**C1. 自己検証スイートが root↔mirror（templates / example）の内容 drift を検知できない。** [自己再現]
- 証拠: `python3 scripts/check_framework_contract.py --profile=standard --root examples/minimal-project` は **PASS** する。にもかかわらず `diff CLAUDE.md examples/minimal-project/CLAUDE.md` は、example 側に **Model Policy 節（root CLAUDE.md:39-48）と hook-enforcement 行（:17）が欠落**していることを示す。`diff hooks/session-start.sh examples/minimal-project/hooks/session-start.sh` も example 側に `CLAUDE_CODE_SUBAGENT_MODEL` advisory ブロック（root :199-205）が無いことを示す。
- 原因: `check_framework_contract.py` は `REQUIRED_EXAMPLE_FILES`（50+ の mirror）を `.exists()` でしか検査せず、内容同一性（`filecmp`/`read_text()==`）を比較しない（:486 付近）[並列確認]。`check_reference_drift.py` も registered hook の存在とスキル名解決を見るだけで、`hooks/*` vs `examples/.../hooks/*` を byte-compare しない（:154）[並列確認]。
- なぜ致命的か: 「テストが壊れたら検知できる構造か」という監査の中核問いに、最重要面で No と答えている。再アーキの看板「drift をハーネスが告げる」が、最も drift しやすい mirror 面で機能していない。実際に C1 配下の rot 実体が複数すでに存在する（H4・H5・H6）。**非エンジニアがコピーする example が、それが demonstrate すると謳う framework と一致する保証が無い。**
- 方向性（実装は別タスク）: mirror 対象に per-pair hash/内容同一 assert を追加。意図的 divergence（例 `validate.md`）は allowlist 化。

### 🟠 HIGH

**H1. deploy ゲートが command 接頭辞で素通りする。** [自己再現]
- `hooks/check-deploy-gate.sh:36` の `DEPLOY_RE='(^|[;&|] *)(vercel +deploy|...)'` は deploy 動詞を行頭か `;`/`&`/`|` 直後にしかアンカーしない。`npx vercel deploy --prod` / `FOO=bar vercel deploy` / `sudo vercel deploy` / `time vercel deploy` はいずれも未マッチ → `emit_allow`。
- なぜ重大か: **`npx vercel deploy` は通常の正規の言い回し**であり、敵対的意図が無くてもモデルが自然にこう書けば deploy 保証が抜ける。MCP deploy は別 matcher で覆うが、CLI deploy のこの穴は実害が高い。
- 方向性: deploy 動詞を先行トークンに依存しない語境界マッチに。

**H2. gate 系 hook 3本が python3 不在で fail-OPEN。** [自己再現]
- `check-skill-gate.sh:34`・`check-cron-gate.sh:40`・`check-task-created.sh:67,73` は判定入力を **python3 のみ**で抽出し、抽出失敗（空）時に `emit_allow`（task-created は hard-stop されず素通り）。python3 が PATH に無い/例外時、制御層スキルや gate 違反タスクが**黙って通る**。
- 対照: `check-deploy-gate.sh`（python3 失敗 RC≠0 → deny）と `check-control-plane.sh`（deny-by-default）は **fail-CLOSED**。同じ framework 内で保証 hook の失敗時挙動が非対称。
- なぜ重大か: 「保証は決定論的に強制」という哲学そのものに反する。決定論的であるべき deny 経路が、外部 interpreter の有無に依存して fail-open する。
- 方向性: gate 系は抽出失敗時 ask/hard-stop（fail-closed）に統一。pure-bash fallback 抽出を追加。

**H3. `extract_command` が escaped-quote で切り詰め → destructive/secrets/deploy/tdd/gate の抽出バイパス。** [自己再現]
- `hooks/lib/extract-input.sh:25` は primary が `grep -o '"command"…"[^"]*"'` で、コマンド本文中の `\"` で停止する。python3 fallback は **結果が空のときだけ**発火し（:26 `[ -z "$result" ]`）、**切り詰め（非空）時は発火しない**。
- 影響: `extract_command`/`extract_file_path` を使う全 hook（destructive, secrets, deploy, tdd, gate）。コマンド本文に引用符が dangerous トークンより前にあると、検査対象が欠落して通る。
- 方向性: 抽出を python3 primary・grep fallback に反転。

**H4. `CLAUDE.template.md` と example の CLAUDE.md が v1.0.0 契約をミラーしない。** [自己再現]
- `grep -c "Model Policy"`: root=1 / `CLAUDE.template.md`=0 / `examples/minimal-project/CLAUDE.md`=0。Model Policy 節・hook-enforcement 行・Completion Rule の `current_refs`/TaskCompleted 行が欠落。
- 影響: setup.sh で scaffold される**全プロジェクト**の CLAUDE.md が、`check_framework_contract` が実際に強制する契約の記述を欠いて始まる（C1 の rot 実体）。
- 方向性: テンプレートと example を root CLAUDE.md から再生成（`## Project Overrides` 末尾は保持）。

**H5. deploy skill が full scaffold で壊れる（companion file 未同梱）。** [SKILL 参照=自己再現 / 未コピー=並列確認]
- `.claude/skills/deploy/SKILL.md:63,85` が `.claude/skills/deploy/platforms.md` を参照する（root には両ファイル存在を確認）。だが `full.json` は `SKILL.md` のみ列挙し、setup.sh は1ファイルずつコピーするため、scaffold 後の `deploy/` に `platforms.md` が無い（並列エージェントが /tmp 再現）。
- 方向性: skill をディレクトリ単位コピー、または full.json に platforms.md を追加。

**H6. example の `/retro` が壊れたコマンド（orphan script target）。** [自己再現]
- `examples/minimal-project/.claude/commands/retro.md:10` が `python3 scripts/retro_report.py --root .` を実行するが、`examples/minimal-project/scripts/` には `check_status.py` と `update-gate.sh` のみ（`retro_report.py` 不在）。`/validate` と異なりガードが無い。
- 方向性: `/validate` の scaffold-safe パターンを踏襲、または retro_report.py を example に同梱。

### 🟡 MEDIUM

**M1. `--check-completion-evidence` が違反時も exit 0。** [自己再現] `check_status.py:1197-1206` は `EVIDENCE:` 行を print するが無条件 `return 0`。enforcement は `check-task-completed.sh` の **stdout 文字列依存**で exit-code 非連動。将来 exit code を信頼する caller / `set -e` リファクタで false-green。方向性: 違反時 `return 2`（stdout は維持）。

**M2. approval 時の gate-ref 空チェックが warning 止まり。** [自己再現] `check_status.py:33` `REF_CHECK_ERROR_VERSION="0.13.0"` だが versioning は 1.0.0 に振り直され、`pre_approve_gate` は警告を print するのみで block しない。約束した「承認時 hardening」が無効化され、ref 空は完了時にしか捕捉されない。方向性: FRAMEWORK_VERSION 基準で実 block 化、または stale 定数を削除し承認時=advisory と明記。

**M3. task_size 自己申告の整合性が WARN 止まり。** [自己再現] S サイズが qa/security を免除するのは state-machine.md の routing（`impl→review→ship`）どおりの**正規挙動**（`check_status.py:563,784`）。穴は「task_size が自己申告で、rationale 欠落が失格でなく警告のみ」な点。L 規模の feature を S と誤申告すると qa/security enforcement が静かに外れる。方向性: strict task type では rationale 欠落を FAIL 化。

**M4. gate 更新の指示が skill 間で不整合。** [並列確認] `deploy/SKILL.md` と `ship-and-docs/SKILL.md`(Step 6) は STATUS.md の gate を直接更新するよう指示する一方、`aegis-brainstorm`/`aegis-review-gate`/`aegis-security-gate` は `update-gate.sh` 経由を明示（「直接編集禁止」）。`check-gate.sh` は `docs/*` を allowlist するため直接編集は hook で止まらず、`.gate-snapshot` が desync しうる。方向性: 全 skill を `update-gate.sh` 経由に統一。

**M5. secrets チェックが大文字小文字を区別。** [並列確認・中確信] `check-secrets.sh` の `.env` マッチが case-sensitive で、`git add .ENV` が case-insensitive FS（macOS/Win 既定）で通過しうる。方向性: `.env` 部分を case-insensitive 化。

**M6. standard profile が未登録 hook 4本＋check-tdd.sh を同梱（dead weight）。** [並列確認] `standard.json` recommended が `check-control-plane.sh`/`check-destructive.sh`/`check-tdd.sh`/`post-bash.sh` をコピーするが standard の `hooks_include` には無く、どのイベントにも未登録。README「TDD は full のみ」が `standard.json:25` と矛盾。方向性: recommended hook を `hooks_include` と整合 or 文書化。

**M7. `restart_summary.py` が runtime 未参照（dead code）。** [自己再現] `grep -rn restart_summary hooks/ .claude/commands/ .claude/skills/` ヒット0。`session-start.sh` も `/recover` も呼ばない。141 行の未検証 surface。方向性: `/recover`/session-recovery に配線 or 削除。

**M8. `PLACEHOLDER_PATTERN` が実コンテンツに誤マッチしうる。** [並列確認] `check_framework_contract.py:226` が `<div>`/`<T>` 等にマッチ。現状の example が当該トークンを避けているため偶然 PASS。将来の `<details>` 等で false FAIL。方向性: `<<…>>`/`{{…}}` 等のマーカー規約にアンカー。

**M9. `evidence_integrity_violations` の `except Exception: return []`。** [並列確認] `check_status.py:458` がパースエラーを「違反なし」に握り潰す false-green vector（入力は事前 validate 済みだが narrow 化推奨）。

### 🔵 LOW / nits
- python3 欠落時の deny で reason 空（`check-deploy-gate.sh:45` 等）。
- `post-status-audit.sh` の gate-tamper 検知が「snapshot に無く edit で**追加**された gate」を未検知（`-n "$OLD"` ガード）。
- count 句が phrase-fragile（`check_reference_drift.py:249,333` — 句が言い換わると count チェックが黙って停止）。
- `reviewer.md:31` の prose「review skill」が曖昧（実体は `aegis-review-gate`）。drift チェック対象外の本文参照。
- `qa-browser` が `CORE_AGENT_FILES` の rationalization 強制対象外。
- control-char 正規化が hook 間で不一致（`check-task-created.sh:91` vs `check-task-completed.sh:81`、害は無し）。
- `pre-compact.sh` ヘッダ記述と実装（line 54 は PHASE のみ参照）の不一致。

### 機械層で「健全」と確認できた点（green が正しく証明する範囲）
- `emit.sh` の出力スキーマ各形は CC spec 準拠かつ pure-bash（外部 interpreter ゼロ）[並列確認]。
- 12 agent の `model`/`effort`/`name` が Model Policy に厳密一致、`name`==filename stem、haiku/version-pinned id/非 opus への xhigh-max なし。root↔example の `.claude/agents/*`・`.claude/rules/*` は **byte-identical** で contract enforced [並列確認]。
- routing.md の 12 agent manifest が disk と双方向一致、全 agent reachable。
- skill 15 dir が CLAUDE.md・contract・lint_names と完全同期、frontmatter（`disable-model-invocation:true`）完備、**aegis-\* 改名 drift なし**（旧 brainstorming/review/security-review の aegis-skill 参照ゼロ）。
- `evidence_integrity_violations` の再利用は genuinely shared（v0.12.6 の「再実装でなく抽出再利用」主張は成立）。`check_reference_drift` は agents/skills の **両方向** drift（欠落 AND 余剰）を検知。`lint_names` は抽出空時に loud fail（fail-safe）。

---

## ② 12能力 充足マトリクス（◯/△/✗ ＋根拠）

| # | 能力 | 判定 | 根拠 |
|---|---|---|---|
| ① | client から情報を引き出す | **◯** | `client-workflow` skill（onboard→discovery）、CLIENT-CONTEXT/GLOSSARY/OPEN-QUESTIONS テンプレ、`check-client-info` hook が context.md 不在時に requirements 編集を deny |
| ② | 仕様を作り切る | **◯** | PRD→SCOPE→NFR→ACCEPTANCE→HANDOVER-TO-DEV + translation/mapping の spec チェーン。テンプレ完備、Dev へ spec 駆動で引き渡し |
| ③ | サポート体制が harness 内（**絶対条件**）| **◯** | `client-workflow` skill が正本（フェーズ進行表＝産出物/完了条件/遷移）、`translation-specialist` agent + `translation-mapping` skill。構造的に充足 |
| ④ | 段階的情報開示 | **◯** | pull-based skills、thin kernel、フェーズ単位開示。2026 の progressive-disclosure 潮流と一致 |
| ⑤ | 部分/構造/全体の精査（LLM 外部レビュー）| **◯** | `reviewer`(opus/xhigh) + `reviewer-testing`/`-performance`/`-maintainability`(sonnet) + `security`(opus/max)。多角レビューが実装の厚みとして最も強い。役割分担「LLM=判断レビュー」の中核 |
| ⑥ | 機械的に正しい＋仕様遵守 | **△** | gate・evidence 完了・TDD backstop は「プロセスが走った証拠」を強制。だが (a) 仕様遵守は gate 有無で**意味的 conformance 検証でない** (b) **テストの意味性（バグを捕まえるか）を verify しない**（DAE の mutation / Tessl の eval 対比で blind spot）(c) 機械層で保証自体に穴（H1-H3, M1-M2）|
| ⑦ | 開発中の要望を巻き取る（変更管理）| **△** | state-machine の iteration reset（dev_ready_for_client 後 brainstorm へ、iteration++、requirements 保持）+ DECISION テンプレ。だが「Dev 途中のクライアント変更要求」専用ワークフローは無く、ループ再始動で代替 |
| ⑧ | 成果物の説明 | **◯〜△** | HANDOVER-TO-CLIENT テンプレ + `ship-and-docs` + `docs-sync` skill。テンプレはあるが「非エンジニアが理解できる形」への翻訳の厚みは要検証（P1）|
| ⑨ | マニュアル作成 | **✗〜△** | **専用の MANUAL/ユーザーガイドテンプレートが無い**。最も近いのは HANDOVER-TO-CLIENT。エンドユーザー向け操作手順の構造が不在 |
| ⑩ | UAT | **△** | ACCEPTANCE テンプレで受入条件を上流定義。だが**納品時に client が実検証する UAT 実行フェーズ/skill が無い**。受入「基準定義」と「実行」が未分離 |
| ⑪ | 納品 | **◯〜△** | HANDOVER-TO-CLIENT + `dev_ready_for_client` gate + Client mode 復帰。構造はあるが薄い |
| ⑫ | 運用問題に対応（保守）| **△** | `bug-diagnosis` skill・bugfix/hotfix task type・`session-recovery`。Dev 側のバグ修正はある。だが**運用監視→トリアージ→修正の保守ライフサイクル、運用 runbook テンプレ、保守担当 agent が無い**。「保守まで一気通貫」が構造的に最も薄い |

**役割分担の実現度（総評）**: harness=構造/段階開示/ゲート は ①〜⑤ で厚く実装。LLM=判断レビューは Dev で多角化され強い（⑤）。一方「**非エンジニアに分かる形での可視化**」は STATUS.md（plain-text ledger＝ややエンジニア寄り）止まりで、⑤⑥⑧⑩ の「結果を非エンジニアが judge できる形」への翻訳層が薄い。**充足が Client上流・Dev に集中し、納品後（⑨⑩⑫）で実装の厚みが急減**する — 北極星「クライアント対応〜保守まで一気通貫」の後半が構造的に未充足。

---

## ③ 哲学層 所見（最新フレームワーク対比・前提の穴）

### 2026 フレームワーク対比（web 実調査）

| 軸 | aegis | Superpowers v5.1 | GStack v0.4.1 | CC native 2026 | Spec-Kit / Kiro / DAE |
|---|---|---|---|---|---|
| ライフサイクル | **フル（intake→spec→dev→UAT→保守）** | Dev のみ | Dev+ship | primitives のみ | spec→build（intake/保守なし）|
| ゲート強制 | **hook=決定論的（PaC）** | soft「Iron Laws」| skill 認知モード | **native hook=決定論的** | DAE=決定論的 Python gate / Spec-Kit=AI 解釈 checklist |
| context 戦略 | thin kernel + pull skills | bootstrap doc | slash + browser daemon | CLAUDE.md + progressive disclosure | md 多ファイル |
| 非エンジニア親和 | **高（北極星）** | 中 | 低 | 低〜中 | 低（DAE は明示除外）|
| テスト意味性検証 | **無**（走ったかのみ）| verification-before-completion | — | — | DAE=mutation / Tessl=eval |

**含意の核**:
- **aegis の賭けは逆張りでなく本流。** 2026 の harness-engineering canon（「LLM は確率的、決定論的 outer constraint で gate せよ」）と Anthropic Managed Agents（公開ベータ）が aegis の triage 思想に収束。
- **非エンジニア×フルライフサイクルは競合不在の実ニッチ。** DAE は「非プログラマ向けではない」と明示除外、Spec-Kit/Kiro/BMAD は暗黙にエンジニア前提で ship 止まり。誰も降りていないニッチ＝**コピーできる先行事例が無く、自分で証明するしかない**。
- **native 冗長の発生。** Checkpoints/`/rewind`・Routines・Auto Mode・`/code-review`・Plan Mode が 2026 に native 化。aegis が手作りした一部は native 委譲で surface を減らせる（「トレッドミルから降りる」方針と整合）。
- **evidence 完了はもはや独自でない**（Superpowers も verification-before-completion を持つ）。差別化は「概念」でなく「ゲート連動×ライフサイクル統合の evidence（UAT/handover 成果物）」に置くべき。

### grill-premise（北極星の前提を攻める）

**P1（最重要の穴）: 「非エンジニアが最終ジャッジャー」が単一障害点。** 役割分担は「LLM レビューがユーザーの弱いチェックを補い、結果を非エンジニアが判断できる形に出す」。だが ⑤⑥ のレビュー結果（構造健全性・テスト意味性）を**非エンジニアが評価する手段が無い**。LLM が「OK」と言えば信じるしかなく、レビュアーが誤ったとき誰も気づけない。Fowler 2026 批評「精緻な構造は**統制の幻想**を与える／レビュアーは markdown を読みたくない」が直撃。charter §7 未検証仮説②「"非スラップ"の最終ジャッジ者」の答え＝**実質 LLM、人間の検証は形式的**。

**P2（測定の穴）: 「崩れない（非スラップ）」が測定されていない。** aegis が強制するのは「プロセス証拠」、検証するのは「テストが走った」。「テストが意味あるか・成果物が崩れていないか」は未測定（DAE の mutation testing / Tessl の eval-driven 対比で blind spot）。非エンジニアはテスト品質を判断できないため、**この穴は非エンジニア向けでこそ深刻**。charter §7 未検証仮説③「"崩れない"の測定法」＝未解決。

**P3（哲学の自己反証）: moat「決定論的強制」が実装で部分的に反証されている。** §1 の H1-H3/M1-M2 は、決定論を謳う gate が fail-open / 接頭辞バイパス / exit0 / warning 止まりであることを示す。web 研究の警告「hard gates が moat、ただし **prose でなく hook であること**を死守せよ」が当たっている。哲学が正しくても、実装が哲学水準に達していない。

### 同意できる点（哲学の強み）
- triage（保証/手順/揮発値）の3分解は思想的に正しく、2026 canon と一致。
- 非エンジニア×フルライフサイクルは実在の市場ギャップ。
- Dev レビューの多角化（reviewer + 3 specialist + security）は同クラスで厚い。

### charter §7 未検証仮説の監査結論
- **① 規模/寿命（"大規模で崩れない"は YAGNI か）**: ユーザーが意図的にフルライフサイクルを狙う以上「広さ」は論点でない（charter が先回りで決着）。ただし**「狙い」と「実装の厚み」に乖離**がある（②⑤ は厚いが ⑨⑩⑫ は薄い）。論点は広さでなく後半の厚み（→ 優先度4）。
- **② 最終ジャッジャー**: P1。実質 LLM。人間検証層が形式的。
- **③ 測定**: P2。未測定。mutation/eval-as-gate の導入が候補。

---

## ④ 推奨アクション（優先度順）

> 優先度1-3 は「今あるものの健全性」問題＝通常の bugfix/framework タスクで fix-forward 可能（監査の直接アウトプット）。優先度4 は再設計テーマ＝**監査では実装せず**、別途 brainstorm→設計→grill→実装へ（charter §6 の分離を維持。本レポートがそのインプット）。

### 優先度1 — 保証の信頼性回復（moat＝哲学の根幹）
- **A1** gate 系 hook を fail-CLOSED に統一（skill/cron/task-created の抽出失敗時は ask/hard-stop、pure-bash fallback 抽出を追加）。[H2]
- **A2** deploy ゲート正規表現を語境界ベースに（`npx`/`sudo`/`time`/`env=` 前置を捕捉）。[H1]
- **A3** `extract_command`/`extract_file_path` を python3 primary・grep fallback に反転（切り詰めバイパス封じ）。[H3]
- **A4** 上記の fail-mode を契約テスト化（python3 を PATH から外した gate 挙動、escaped-quote 入力、prefix 付き deploy コマンド）。現状これらの経路を踏むテストが無いため H1-H3 が green を通った。[hooks 観点]

### 優先度2 — mirror drift の検知（future-proof 看板の実装）
- **A5** `check_reference_drift`（or contract）に root↔templates↔example の**内容同一性 assert**（hash/`read_text()==`）を追加。意図的 divergence は allowlist。[C1]
- **A6** `CLAUDE.template.md` と example を root CLAUDE.md から再生成（Model Policy・hook-enforcement・Completion Rule を同期）。[H4]
- **A7** deploy skill をディレクトリ単位コピー（platforms.md 同梱）or full.json に追加。[H5]
- **A8** example の `/retro` をガード（/validate パターン）or retro_report.py 同梱。[H6]

### 優先度3 — 完了/承認 enforcement の堅牢化・dead weight 整理
- **A9** `--check-completion-evidence` を違反時 `return 2`（stdout は維持＝belt-and-suspenders）。[M1]
- **A10** approval 時 ref チェックを実 block 化 or stale 定数削除＋advisory 明記。[M2]
- **A11** task_size の rationale 欠落を strict task type で FAIL 化。[M3]
- **A12** deploy/ship-and-docs skill を `update-gate.sh` 経由に統一。[M4]
- **A13** standard profile の未登録 hook を整理 or 文書化、README の TDD 記述を standard.json と整合。[M6]
- **A14** `restart_summary.py` を `/recover` に配線 or 削除。[M7]
- **A15** secrets を case-insensitive 化（.env 部分）。[M5] ＋ M8/M9 と 🔵 nits。

### 優先度4 — 再設計インプット（監査では実装しない）
- **B1** 「テストの意味性」検証の導入検討（mutation testing / eval-as-gate を qa gate に）— ⑥⑫ と P2 の核。
- **B2** 非エンジニア向け「judge できる可視化」層の設計 — P1。レビュー結果/STATUS を非エンジニアが判断可能な形へ翻訳（`translation-specialist` の delivery 側拡張が candidate）。
- **B3** ライフサイクル後半の実装の厚み — ⑨ MANUAL テンプレ、⑩ UAT 実行フェーズ、⑫ 保守 runbook/監視/agent。
- **B4** native 冗長の棚卸し — Checkpoints/`/rewind`・Routines・Auto Mode への委譲可否を評価し surface を削減。

---

## 結論

v1.0.0 は機械的に「全 green」だが、green が証明しない3領域に実質的な所見がある: **(1) mirror drift 不可視（C1）、(2) 決定論的保証の実装が宣言より緩い（H1-H3, M1-M2）、(3) ライフサイクル後半と「テスト意味性／非エンジニアの judge」の薄さ（⑥⑨⑩⑫, P1, P2）。** 哲学の賭け（hooks-as-guarantees × 非エンジニア×フルライフサイクル）は 2026 の本流かつ競合不在のニッチで筋が良い。やるべきは思想転換でなく、**moat を実装水準で哲学に追いつかせる（優先度1-2）**ことと、**北極星後半の構造的充足（優先度4）**。優先度1-3 は fix-forward、優先度4 は別途 brainstorm へ — 監査と再設計の分離を保つ。

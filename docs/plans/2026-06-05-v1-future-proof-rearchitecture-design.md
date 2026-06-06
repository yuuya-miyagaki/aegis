# Design: Aegis Future-Proof Re-architecture（Foundation-first）

> 作成日: 2026-06-05 / 対象モデル: Opus 4.8（セッション現行） / 起点: v0.13.0 modernization plan（2026-05-03, Opus 4.7 前提）

> **⚠ Round 1 セカンドオピニオン後の改訂（2026-06-05）**: 「全面 v1.0.0 再アーキ即着手」は **NO-GO 判定**。emit.sh 中心の **Foundation（土台）だけを先行**し、manifest 拡張・context 撤廃・model inherit ポリシー・TDD profile などの**哲学変更は分割審査に回す**。本書は全体ビジョンの記録として残すが、**直近の実装スコープは `2026-06-05-v1-phase-f-foundation.md`（F0/F1/F2、挙動不変）に限定**する。version bump（v1.0.0）も Foundation には含めない（§9 改訂参照）。主要な P1 修正点は本書末尾「Round 1 反映」を参照。

## 1. 背景と問題

Aegis は成熟したハーネス（v0.12.2 ship 済み、v0.13.0 が Phase 0b 途中）。だが「古さ」には2種類ある:

1. **追従の遅れ** — hook スキーマ・新イベント・effort 階層・ビルトインスキル名衝突。既存 v0.13.0 計画でほぼカバー済み。
2. **設計思想そのものの陳腐化（本丸・未着手）** — Aegis の中核原則「Thin context（L0〜L3・同時3doc・CLAUDE.md <700語）」と「重い hook 強制（書いたルールは無視される前提）」は、**コンテキストが希少でモデルが非力だった時代の制約**。Opus 4.8 + 1M context + 指示追従力の向上で前提が崩れている。

さらに既存 v0.13.0 計画自体が「Claude Code 進化追従（chasing）」の産物であり、Opus 4.7 / 2026-05-03 docs 前提。4.8→4.9 でまた壊れる。ユーザーの真の要求は「**追従トレッドミルから降りる**」=モデル進化に耐えるアーキテクチャ。

## 2. 中核原則（合意済み）

設計思想を性質の違う2層に分解し、それぞれを正しく扱う:

- **保証（What / 不変）** = hard gate・evidence 必須・破壊コマンド承認・secrets 保護・durable handover。**決定論的に強制（hook 維持・強化）。** モデルが進化しても変える理由がない価値そのもの。
- **手順（How / 揮発）** = どのモデルで・effort いくつで・context を何 doc まで・どの subagent に振るか・routing 細則。**賢い 4.8 に委ねる。** 世代ごとに最適解が変わる実装詳細。
- **揮発値（Platform 固有）** = モデル名・effort 値・CC hook スキーマ・ツール名・version。**1枚の manifest に隔離。** 追従＝差し替えだけ。

一言: **「手順を強制する」harness から「アウトカムを強制し、経路はモデルに任せる」harness へ。**

## 3. 現状要素の3層振り分け（triage）

### 🔒 KEEP — 保証（決定論的強制を維持・強化）

| 要素 | 現状 | 再設計後 |
|---|---|---|
| 破壊コマンド承認 | `check-destructive.sh` | 維持。検知パターンは **`patterns.sh`（単一真実）**（※当初「manifest 化」と書いたが Round 1 ② で撤回。manifest にはミラーしない） |
| secrets 保護 | `check-secrets.sh` | 維持。パターンは **`patterns.sh`（単一真実）**（manifest 化は不採用、Round 1 ②） |
| deploy 承認 | `check-deploy-gate.sh` / `check-deploy-mcp-gate.sh` | 維持。MCP matcher は**将来 manifest 案**だが Foundation では不採用（hook 内に保持） |
| gate 承認→phase 遷移 | `check-gate.sh` | アウトカム強制に転換（gate approved かだけ見る） |
| STATUS 改竄防止 | `post-status-audit.sh` | 維持 |
| evidence 必須完了 | Completion Rule（文章のみ） | **Stop/TaskCompleted hook で強制に格上げ** |
| durable handover/restart | STATUS.md ledger | 維持（思想の中核） |
| **TDD** | `check-tdd.sh`（手順の逐一監視） | **保証として維持、ただし backstop 化**（red→green を経たテストを伴う、を強制）。strictness は manifest profile 値（strict/advisory/off）、受託は既定 strict → **完了**（2026-06-06・v0.12.5・profile→strictness 明文化＋`AEGIS_TDD_MODE=off` escape hatch＋session-start advisory。red→green 自動検証は非スコープ・heuristic backstop 維持。`2026-06-06-v1-tdd-profile-design.md`） |

### 🤖 DELEGATE — 手順（モデルに委ねる）

| 要素 | 現状 | 再設計後 |
|---|---|---|
| context 予算 L0〜L3・同時3doc | CLAUDE.md に固定数値 | **数値撤廃**。「STATUS 起点・pull-based・chat より repo 優先」は原則として残す。何をどれだけ読むかは 1M モデルに委ねる → **完了**（2026-06-06・v0.12.4・「max 3 docs」hard 数値のみ撤廃／L0-L3 語彙維持・`2026-06-06-v1-context-budget-principle-design.md`） |
| routing 細則 | `routing.md` 詳細ルール | **原則だけに縮約**（分離が安全/明確/小さくする時のみ subagent）→ **完了**（2026-06-06・v0.12.3・`2026-06-06-v1-routing-principle-design.md`） |
| effort/model 個別割当 | 12 agent にハードコード | manifest 既定＋`inherit` 優先（§5 参照） |
| 冗長 always-on 指示 | CLAUDE.md / rules 過剰記述 | 削減 |

### 📦 ISOLATE — 揮発値（manifest に隔離）

モデル系統・effort 値・**CC hook 出力スキーマ JSON 形**（v0.12.2 で12ファイル一斉書き換えの激痛の元凶）・CC 機能/ツール名（Skill, TaskCreate, Explore, Plan, schedule/loop, MCP deploy matcher, ビルトインスキル名）・version 番号・CC スキーマ版・docs 検証日。

### ➕ ADD — future-proof の骨格（3点セット）

1. **manifest（単一揮発真実源）** `aegis.manifest.json`
2. **`hooks/lib/emit.sh`（出力スキーマ単一化）** — 各 hook の手書き `printf '{"hookSpecificOutput"...}'` を全廃し1関数へ
3. **drift detector（陳腐化の自動検知）** — `check_reference_drift.py` を拡張し manifest↔lib↔実環境のズレを警告。「人間が手で気づく」状態を「ハーネスが告げる」状態へ

## 4. manifest スキーマ

> **【Round 1 ② で縮約】** 下記は *全体ビジョン* の広い manifest。Round 1 で「manifest は patterns/schema をミラーすべきでない（第3同期先化）」となったため、**Foundation で作るのは version + 外部揮発事実（model lineup・schema 日付）だけの最小シード**（`2026-06-05-v1-phase-f-foundation.md` F2-2）。`security_patterns` は `patterns.sh`、`hook_output_shapes` は `emit.sh` が単一真実とし、manifest には置かない。role_defaults/enforcement/profiles は実消費者が出来てから追加。

`aegis.manifest.json`（全体ビジョン時点の canonical 案。※ Foundation では未採用）:

```jsonc
{
  "version": { "framework_version": "1.0.0", "schema_verified_date": "2026-06-05" },
  "platform": {
    "hook_output_shapes": { /* PreToolUse=wrap, PostToolUse=top-level, ... */ },
    "tool_names": { "skill": "Skill", "task_create": "TaskCreate", "explore": "Explore", "plan": "Plan" },
    "builtin_skills": ["brainstorming","review","security-review","writing-plans","schedule","loop","find-skills"],
    "mcp_matchers": { "vercel_deploy": "mcp__claude_ai_Vercel__deploy_to_vercel" }
  },
  "models": {
    "lineup": { "opus": "claude-opus-4-8", "sonnet": "claude-sonnet-4-6", "haiku": "claude-haiku-4-5" },
    "flagship": "opus",
    "effort_tiers": ["low","medium","high","xhigh","max"]
  },
  "role_defaults": {
    "planner": { "model": "opus", "effort": "max" },
    "reviewer": { "model": "opus", "effort": "xhigh" },
    "implementer": { "model": "inherit", "effort": "high" }
  },
  "enforcement": { "tdd": "strict", "context_soft_budget": null },
  "security_patterns": {
    "secrets": ["*.pem","id_rsa","*credentials*.json","service-account*.json"],
    "destructive": ["git filter-branch","git reflog expire --expire=now --all","npx rimraf","find .* -delete"]
  },
  "profiles": { "minimal": {}, "standard": {}, "full": {} }
}
```

### フォーマット方針

canonical は `aegis.manifest.json`（Python・人間が直読）。hook のホットパス（出力スキーマ・検知パターン）は `hooks/lib/*.sh` に bash 実装として持ち、**drift detector で manifest と同期検証**。理由：hook は毎ツール呼びで走るので実行時 JSON パース（python/jq 起動 30-50ms）を回避（既存計画 R8 リスクと同じ）。「宣言＝manifest / 実装＝lib / 同期＝drift検出」は lockfile 的で堅牢。

## 5. CC 実行時制約と model の future-proof

Claude Code は agent の model/effort を **frontmatter から直読**する。manifest を CC が自動参照する仕組みは無い。したがって:

- **大半の agent を `model: inherit`** に（セッション現行モデルへ自動追従＝ゼロ保守。今日 4.8、明日 4.9）。これが究極の future-proof。
- **意図的に別モデルにしたい役割だけ明示**（例：review は常に最強、機械作業は安価）。その少数を manifest が宣言し `bin/setup.sh` が frontmatter へ同期＋drift 検証。
- 結果：モデル名がコードに散らばらず、現れるのは manifest 1箇所＋意図的オーバーライド数件のみ。

これは旧 v0.13.0 Task 1-1「frontmatter に model/effort を一括ハードコード」と**逆方向**（旧は hardcode を増やす、新は外す）。

> **【事実訂正・Round 1 ④】** 本節は *to-be* の目標であり、**現状の repo では `planner.md` / `reviewer.md` / `security.md` は `model: inherit`**（明示オーバーライドは未実装）。よって「明示オーバーライド維持」という表現は誤り。さらに CC のモデル解決順では env / per-invocation override が frontmatter より強い経路があるため、`inherit` だけでは品質保証にならない。**この model ポリシー（inherit-first + 品質直結役割の明示固定）は Foundation スコープ外**とし、後続フェーズで CC docs 再確認の上で設計・実装する。

## 6. ディレクトリ before → after

```text
                              BEFORE                          AFTER
aegis/
  aegis.manifest.json         ─                          →   ★NEW 揮発真実源
  CLAUDE.md                   原則+手順+揮発が混在        →   原則・保証だけに減量。manifest 参照
  .claude/
    agents/*.md               model/effort ハードコード   →   inherit 優先、明示は manifest 同期
    rules/routing.md          詳細 routing 手順           →   原則だけに縮約
    skills/                   （維持）
  hooks/
    check-*.sh                各自で出力JSON手書き+inline  →   emit.sh / patterns.sh を source
    lib/extract-input.sh      入力抽出のみ                →   （維持）
    lib/emit.sh               ─                          →   ★NEW 出力スキーマ単一化
    lib/patterns.sh           ─                          →   ★NEW 検知パターン（drift検証対象）
  scripts/
    check_reference_drift.py  参照ドリフトのみ            →   ★拡張 manifest↔lib↔実環境
  templates/profiles/*.json   独立3プロファイル           →   manifest への薄い overlay
```

## 7. 移行戦略（F → R → A → D）

**順序の鍵**：先に土台、その上に乗せ直す。新規 hook やパターン拡張を旧来方式（手書きJSON・inline）で先に作ると移行債務が増える。

| Phase | 内容 | 旧 v0.13.0 の吸収 |
|---|---|---|
| **F：土台**（挙動不変） | manifest 作成 → emit.sh 化＋既存11 hook 機械書き換え → patterns.sh 抽出 → drift detector 拡張 | （新規。Phase 0a 成果の上） |
| **R：再配分**（triage 適用） | CLAUDE.md 減量（数値撤廃）・routing 原則化・agent model を inherit 化・evidence 完了の hook 強制化・TDD backstop+profile 化 | Phase1 routing / Phase3 哲学の一部 |
| **A：吸収**（catch-up を新方式で） | 新 hook 群（skill/cron/task-created/task-completed）を emit.sh+manifest matcher で実装・スキル改名3件・commands/skills frontmatter・schedule/loop 連携 | Phase 0b 全部 / Phase 2 全部 |
| **D：仕上げ** | README・LEARNINGS・INTEGRATION・migration guide・version bump v1.0.0 | Phase 3 残り |

### 旧計画から変わる/捨てる
- ❌ Phase 1 Task 1-1「model/effort 一括ハードコード」→ 方向転換（inherit 優先で外す）
- 🔄 secrets/destructive 拡張 → inline 追記でなく patterns.sh へ
- ✅ 温存（5ラウンドレビュー成果）：TaskCreated=`continue:false`(hard stop) / TaskCompleted=exit2+stderr(差し戻し)、`stop_hook_active` ガード、raw_input ダンプは gitignore 対象限定

### 順序とリスク低減
- **Phase F は挙動不変リファクタ**：v0.12.2 で公式スキーマ準拠済みなので emit.sh 化は出力を1バイトも変えない。**既存174テスト緑のまま**が合格条件。`test_hook_output_schema.py` を「emit.sh 出力＝期待JSON」契約に拡張。
- **drift detector は最初 advisory**（警告のみ）。誤検知で作業を止めない。
- **段階リリース**：F/R は内部改善（破壊小）→ A は新 matcher（破壊中）→ D で version 確定。各 Phase 末で gate。

## 8. リスク

- R1: emit.sh 化で出力が変わる → 契約テストで「emit 出力＝期待JSON」を全イベント assert、174テスト緑維持
- R2: drift detector 誤検知で作業停止 → advisory 始動、env でバイパス可
- R3: manifest↔lib の二重管理ズレ → drift detector が同期を検証（lockfile 的）
- R4: `inherit` 化で意図せぬモデル降格 → 品質直結役割（review/security/planner）は明示固定する設計を後続フェーズで実装（**現状は inherit、未対応**）。CC の override 解決順を docs で再確認
- R5: スキル改名で外部（uccc）参照破壊 → migration guide + reference drift check
- R6: CC が将来また hook スキーマ変更 → emit.sh 1ファイル修正で吸収（本設計の狙い）

## 9. バージョン（Round 1 改訂）

当初は **v1.0.0** を提案したが、Round 1 で「全面再アーキは NO-GO、Foundation 先行」となったため:
- **Foundation（F0/F1/F2）は version bump を含まない**。挙動不変リファクタなので現行 `0.12.x` 系（owner=`FRAMEWORK_VERSION`、F0 で `0.12.2` に確定）のまま、必要なら patch（例 `0.12.3`）。
- **v1.0.0 への格上げは、哲学変更フェーズ（manifest 拡張・model ポリシー・context observability・TDD profile）を分割審査で通し終えた後**に判断する。「トレッドミルから降りる」という看板は維持するが、看板を掲げるのは中身が揃ってから。

## 10. Round 1 セカンドオピニオン反映（2026-06-05）

外部レビュー（IDE Chat / Opus 4.6、同一ワークスペース参照、174 tests PASS を実測）からの P1 指摘と対応:

| # | 指摘 | 重大度 | 対応 |
|---|---|---|---|
| ① | 全面 B は YAGNI。emit.sh 集約だけ実利が強い | P1 | 全面再アーキ撤回。Foundation 先行（本書冒頭バナー + §9） |
| ② | manifest は runtime truth でなく declarative mirror（第3同期先化） | P1 | patterns/schema を**ミラーしない**。manifest は version + 外部揮発事実だけの最小シードに縮約 |
| ③ | emit.sh の deny が python3 依存＝fail-open リスク | P1 | **pure-bash 実装**（外部 interpreter ゼロ・外部依存ゼロ）。fail-closed テスト追加（Round 2: 静的テストはコメント除外で自己矛盾回避） |
| ④ | inherit 従属。実体は inherit で設計文の「override 維持」と不一致 | P2 | §5/§8 を事実訂正。model ポリシーは後続フェーズへ |
| ⑤ | context 数値撤廃はコスト価値後退 | P2 | hard block でなく observability（Read 回数・doc サイズ計測）へ。後続 |
| ⑥ | TDD `off` の形骸化 | P2/P3 | `off` は minimal/local の escape hatch のみ。標準は strict |
| ⑦ | drift advisory 放置 | P2 | 昇格基準明記（内部値=FAIL、外部揮発値=advisory 継続） |
| ⑧ | Phase F の manifest schema が広すぎ | P2 | 最小シードに縮小（YAGNI） |
| ⑨ | STATUS 実態 drift（Phase 0b hook 既存） | P2 | **F0 で棚卸し最優先**。A フェーズの二重計上防止 |
| 新 | pytest 前提誤り / test 数 134→174 / version 割れ | — | 全コマンド `python3 -m unittest`。version owner=`FRAMEWORK_VERSION` を F0 で確定 |

直近スコープの確定版実装計画: **`2026-06-05-v1-phase-f-foundation.md`**（F0/F1/F2）。

## 11. 完了条件（概要・全体ビジョン到達時点）

> 下記は F→R→A→D を全て終えた「全体ビジョン」の完了条件。**Foundation の直近完了条件は `2026-06-05-v1-phase-f-foundation.md` の Verification を正とする**。

- [ ] manifest / emit.sh / patterns.sh / drift detector（advisory）実装
- [ ] 既存11 hook が emit.sh 経由、出力契約テスト全 PASS、174テスト緑維持
- [x] CLAUDE.md から固定 context 数値撤廃（2026-06-06・v0.12.4） / [x] routing 原則化（2026-06-06・v0.12.3）
- [x] TDD backstop+profile 化（2026-06-06・v0.12.5・明文化＋escape hatch＋advisory）
- [ ] agent model が inherit 優先、明示オーバーライドは manifest 同期
- [ ] evidence 完了の Stop/TaskCompleted hook 強制化（旧確定案を採用）
- [ ] 新 hook 群・スキル改名・commands frontmatter（新方式で吸収）
- [ ] README/LEARNINGS/INTEGRATION/migration guide、version v1.0.0
- [ ] tier 1/2 eval・check_framework_contract・check_reference_drift 全 PASS

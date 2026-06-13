# 全力レビュー（第5回・2026-06-12、対象 v1.6.0／HEAD `437b857`）

## 0. サマリ

過去 4 回のレビュー（機械契約／機能整合性／進化哲学／行動）と**重複しない 6 軸**で独立サブエージェントを並列投入し、新規所見のみを抽出した。結論を 3 行で述べる。

1. **決定論 moat に PoC 付きの穴が複数残る**。emit.sh 上書きルート（変数展開バイパス）、テスト緑色偽装、6 成果物 touch 化、`git --git-dir=` 経由 `.env` add の 4 件はマージ前修正対象。
2. **公開契約と実装の drift が再発系統**。architecture-overview.md の `user-invocable` 表が 17 件嘘、hook/lib カウントも旧値。「手書きカウント」が更新追随できない構造を畳む時期。
3. **正面玄関が北極星と乖離**。onboarding 教材は突出して良いが、README／テンプレ／hook deny 文言がエンジニア母語のまま。superpowers の trigger description 質と gstack の ETHOS preamble を最小手で取り込むのが次の進化軸。

総合推奨は**修正後マージ → v1.7 で構造強化**。Critical 6 件を v1.6.1 でクリア → v1.7 で「単一所有の水平展開」「思想テキスト 2 枚追加」「trigger eval 1 本」を実装。**v2.0 再設計は時期尚早**。

---

## 1. 重大度マトリクス（軸横断・優先順）

### 🔴 Critical（v1.6.1 マージ前修正）

| # | 場所 | 軸 | 問題 | PoC / 根拠 |
|---|------|----|------|------------|
| **C-1** | `hooks/check-control-plane.sh:46-51` | A | 制御プレーン書込み deny の regex が**変数展開後**のリテラル `hooks/` を見ない | `D=ho; D=${D}oks; echo evil > $D/lib/emit.sh` が allow。emit.sh 上書き→全 deny hook が `{}` を返し**moat 全崩壊** |
| **C-2** | `scripts/build-judge-card.py:185-215` × `hooks/lib/patterns.sh:83-92` | A | テスト走行有無を判別せず runner 名だけで分類 | `pytest --version` / `--collect-only` / `-k <miss>` で judge card に「テスト: green」が刻まれる。qa/deploy ゲートが嘘で 🟢 化 |
| **C-3** | `scripts/check_status.py:471-476` | A | `client_ready_for_dev` の 6 成果物検査が**存在のみ**（0 バイト OK） | `mkdir -p docs/{requirements,handover,translation}; touch …; update-gate approve` が成功。行動レビュー §5.1 P1-D が touch 1 行で復活 |
| **C-4** | `templates/hooks.template.json:5` ＋ `examples/minimal-project/.claude/settings.json:5` | E | SessionStart matcher `"startup\|clear\|compact"` が公式の **`resume` を欠落** | `--resume`／会話復元時に SessionStart hook が無発火 → STATUS.md 注入・gate-snapshot 生成・evidence ローテが silent fail。v1.6.0 P1-A の前提を破る |
| **C-5** | `docs/architecture-overview.md:287-306` ↔ `.claude/skills/*/SKILL.md` | D | スキル表が「14/18 件 `user-invocable: true`」と主張するが**実態は `session-recovery` の 1 件のみ true**、残り 17 は全て false | grep 一発で発覚する公開契約の嘘。v1.6.0 P1-A の起動経路設計と矛盾 |
| **C-6** | `docs/architecture-overview.md:312, 452, 535, 103-106, 402` ↔ profile JSON / contract / drift | D | hook 数「16」/ lib 数「3」/ drift checks「11」と書くが、実装は 17 / 7 / 12 | v1.5.0 で `post-bash-observe.sh` 追加・lib 4 本追加・drift 1 本追加。新規 onboarding と差分監査の起点が壊れている |
| **C-7** | `tests/test_update_gate_lock.py:270-314` × `scripts/update-gate.sh:165` | B | 17 テストで CI 全体の **70% (93/132 秒)** を sleep で消費 | ロック wait を伸ばすたび CI が線形に遅くなる。3 年後にローカル skip が常態化 → TDD 文化崩壊。`--wait-iterations=N` の差し込み口で解決可 |
| **C-8** | `scripts/check_status.py:485-721 validate_status_file`（237 行 / 87 分岐）<br>`scripts/check_framework_contract.py:518-967 main`（449 行 / 121 分岐） | B | 検証カテゴリが inline 順列で並ぶ巨大関数。fixture `make_status_md` を 149 ケースが共有 → スキーマ進化のたびに 50+ ケース赤化 | スキーマを安全に進化させる経路を 1 個も持っていない。validate_status_file を純関数列に割って collect → 集約 |
| **C-9** | `hooks/check-secrets.sh:29, 60, 64, 99` | B | credential リストが**regex / case glob / find -name / staged regex の 4 形式で重複コピー** | 既存コメントが「real second consumer まで centralization deferred」と書くが**既に 4 consumer**。新規 credential 種別追加で fail-open リスク確定 |

### 🟡 Should fix（v1.6.x〜v1.7 で順次）

| # | 場所 | 軸 | 問題 | 修正方針 |
|---|------|----|------|----------|
| S-1 | `hooks/check-gate.sh:64-69` | A | `*/docs/*` 早期 allowlist が制御プレーン分類より早く、`hooks/docs/evil.sh` が書ける | `is_control_file` を先に判定してから docs allowlist |
| S-2 | `hooks/check-destructive.sh` × `hooks/lib/patterns.sh:14` | A | SQL `DELETE FROM` / `UPDATE … SET` / `DROP COLUMN`/`SCHEMA` / SQL コメント空白代替を検出せず | 検出 regex を追加、または「SQL 破壊は 2 件のみ」と v160-security に明示 |
| S-3 | `hooks/check-secrets.sh:46, 97` | A | `git --git-dir=.git --work-tree=. add .env` / `git -C /tmp add .env` / `git stage` / `git stash push` / `eval "git add .env"` が素通り | `git\s+(--?[A-Za-z][-A-Za-z0-9_=./:]*\s+)*?(add\|stage\|update-index\|stash)\b` |
| S-4 | `templates/hooks.template.json:113` | E | `PreCompact` の matcher 不在で `auto\|manual` 区別不能 → manual 圧縮で誤ブロック寄り | matcher 分離＋manual は閾値緩和 |
| S-5 | `.claude/agents/planner.md:5` | E | `readOnly: true` は公式表に**存在しない** frontmatter。Claude Code は黙殺するため「効いている錯覚」が生じる | 除去するか `disallowedTools: [Edit, Write, NotebookEdit]` に置換（reviewer は既にこの形） |
| S-6 | `.claude/commands/*.md`（8 本） | E | 公式が「Custom commands have been merged into skills」と誘導 | 移行計画化。今すぐ deprecate ではないが将来互換破棄リスク |
| S-7 | （横断・設計） | E | `includeCoAuthoredBy` は公式 deprecated（→ `attribution`） | drift にキーチェック追加、テンプレに混入させない |
| S-8 | `.claude/rules/state-machine.md:57` ↔ `scripts/check_status.py:99-103` | D | state-machine.md は S サイズで `impl→review→ship` と書くが、実装は `brainstorm` も S で許可 | doc を `(brainstorm)→impl→review→ship` に揃えるか実装側を絞る |
| S-9 | `CLAUDE.md:86` ↔ `scripts/check_status.py:37-44` / `:470-476` | D | Completion Rule は 5 ゲートのみと宣言、実装は `client_ready_for_dev` + 6 成果物まで強制 | CLAUDE.md L86 に P1-D 検査を明記 |
| S-10 | `docs/architecture-overview.md:450-452` ↔ `templates/profiles/standard.json:36-47` | D | arch-overview は standard を 4 hooks と書くが、v1.4.0 P2-1 / v1.5.0 で 10 hooks に拡張済み | 表を更新 |
| S-11 | `scripts/check_framework_contract.py:122-150 REQUIRED_HOOK_FILES` | D | `hooks/lib/phase-skills.sh` が disk に存在し session-start.sh から source されるが REQUIRED に未登録（**F6 教訓と同型の検出穴**） | REQUIRED_FILES / REQUIRED_EXAMPLE_FILES に追加、または `hooks/lib/*.sh` glob 化 |
| S-12 | `hooks/lib/extract-input.sh:6-62` | B | deny 系まで grep fast-path → python3 fallback で動く。`"` 等で silent truncation の脆弱性履歴 | deny 系（check-control-plane / check-secrets）は無条件 python3 経路に統一 |
| S-13 | `scripts/check_status.py:37 GATE_REF_MAPPING` ↔ `scripts/update-gate.sh:290 get_ref_key()` | B | 既知の JUDGE_GATES とは**別の** bash/python 二重実装。parity test なし | `--print-gate-ref-map` を python から出力して bash が動的読込、または parity test |
| S-14 | `scripts/check_status.py` 全体 | B | `STATUS.md` パスを 9 か所で再構築、`extract_frontmatter()` 23 か所 | `class StatusContext` で 1 度ロード共有 |
| S-15 | `scripts/eval_scenario.py`（142 行） | B | README / `.claude/commands/` / tests のいずれからも参照ゼロ＝**死蔵**。extensions は "manual opt-in, not in core contract" | 生かす（README に手順追記）か殺す（archive/） |
| S-16 | `README.md:1-93` | C | トップ 200 行が完全エンジニア向け。"thin kernel"／"PaC via hooks"／"frontmatter"／"`disable-model-invocation`" が説明なしで連射 | L1 で `docs/onboarding/README.md` へ送る、L2-30 を `02-explainer.md` の「監督＋検査官」縮約版に |
| S-17 | `README.md:172-499` | C | 全長の半分以上が v0.5→v0.6 までの 27 リリース migration log | 最新 1〜2 リリース分のみ残し残りを `docs/CHANGELOG.md` に外出し |
| S-18 | `templates/*.template.md` 横断 | C | `<記入>` プレースホルダの自立度が低い。`PRD`/`NFR`/`SPEC`/`TRANSLATION-MAPPING` で「何を書くか」が示されない。`MANUAL`/`RUNBOOK`/`UAT-RESULTS` だけ秀逸 | 全テンプレに「悪い例／良い例」1 行ずつコメント。`MANUAL.template.md` の体裁を標準化 |
| S-19 | `hooks/check-gate.sh:132` ほか英文 hook deny 群 | C | 英文・命令形・固有名詞のみ。次に何すべきかが書かれない。`check-client-info.sh:51` だけ日本語＋導線あり | `emit_deny_with_recovery "<reason>" "<next_step>"` ヘルパに昇格・全 hook で統一 |

### 🟢 Nice to have（v1.7+）

- `hooks/check-tdd.sh:43-49`：`src/test/` ディレクトリ命名で TDD バックストップ無効化（`*/__tests__/*` のみに絞るか二重条件化）
- `scripts/build-judge-card.py:218-220`：security 用 secret regex が狭い（gitleaks 代表 10〜15 件を取込）
- `hooks/lib/emit.sh` の handler type 多様化：公式の `type: prompt` / `type: agent` は決定論 moat と緊張するが Phase 2 検討
- subagent `isolation: worktree` を `implementer` に付与 → main 汚染防止を frontmatter で完結
- `CLAUDE.md:78-85` Completion Rule の 6 条件中 3 つ（zero-tool-call / blockers 記録 / evidence-based summary）が機械検査なし
- `templates/HANDOVER-TO-CLIENT.template.md` 等の deadweight 化リスク → 各テンプレに「使用 skill」frontmatter
- `examples/minimal-project/` の 95 ファイル mirror を「コア hook のみ」に縮める案
- `TRANSLATION-MAPPING.template.md` に使用例 1 行追加（「直感的な操作」→「3 クリック以内で予約完了」→「Form を 1 ページ wizard」）
- `STATUS.template.md` の frontmatter 41 行 → スリム版を別途用意し advanced を `STATUS.template.advanced.md` に分離
- `build-judge-card.py:404` 「あなたが取るアクション」が `（LLM が平易日本語で記述）` プレースホルダのまま出力される
- README Quick Start が `standard` 推奨だが onboarding ハンズオンは `full` 必須 → 教材を進めるなら `full` を README で明示

---

## 2. 横断テーマ（番号別ではなく、構造パターン）

### T1. 「単一所有」の未適用領域がまだ残る

**成功事例**: `hooks/lib/patterns.sh`（bash/python parity test）／`hooks/lib/phase-skills.sh`（BFS 到達性検証）。

**未適用領域**: gate 名・phase 名・ref キーが依然 3〜4 箇所に分散。
- `scripts/check_status.py:37-44, 58`（python）
- `scripts/update-gate.sh:26, 290-297`（bash）
- `hooks/session-start.sh:57`（bash 配列）
- `hooks/post-status-audit.sh:62`（bash 配列）

**3 年スパンの最重要負債解消は「成功した単一所有モデルの水平展開」**。bash 側を python から動的に読む（`--print-gate-ref-map`）か、parity test を追加するか、いずれかが v1.7 必須。

### T2. 「docs ↔ 実装」の手書きカウントが再発系統 drift

C-5 / C-6 / S-10 はいずれも arch-overview.md の手書き数値が実装に追従できていない。本質は「真の単一所有は実装側（JSON / Python リスト）なのに、doc が独立に手書きカウントを持つ」構造。

**解**: `scripts/generate_arch_inventory.py` で `REQUIRED_FILES` / profile JSON / `ALL_CHECKS` から arch-overview の §15 / §10 / §7 を自動生成し、`ALL_CHECKS` に「arch-overview の生成セクションが当期生成出力と一致する」契約を追加。手書き drift を恒久封鎖。

### T3. 「fast-path / fallback」が deny 系まで侵入

C-1（変数展開バイパス）、C-2（test-green 偽装）、S-12（extract-input fast-path）、S-3（`git --git-dir=` バイパス）はいずれも**「軽い検査を先に走らせて該当しなければ素通り」型**の構造的脆弱性。

軽量 grep / regex は高頻度な post-bash 系では正解だが、**deny 系では「該当しない = 安全」を保証できない**。

**解**: deny 系は無条件 python3 経路（AST 的または完全展開後の文字列で検査）、observe 系のみ fast-path 許可。これを `hooks/lib/extract-input.sh` の API レベルで `extract_*_strict()` / `extract_*_fast()` に分離する。

### T4. 正面玄関が非エンジニア向けでない

aegis の中に**二層**が並走している：
- **対非エンジニア層**：`docs/onboarding/`（突出して良い）／`MANUAL`／`RUNBOOK`／`UAT-RESULTS` テンプレ／`02-explainer.md` の「監督＋検査官」たとえ
- **対エンジニア層**：`README.md` トップ／`templates/PRD,NFR,SPEC,STATUS` テンプレ／hook 英文 deny メッセージ／migration log

**問題は入口で後者に当たること**。非エンジニアは README L1-200 でほぼ確実に離脱する。

**解**: `02-explainer.md` の品質を「入口表面」に持ち込む。S-16〜S-19 を 1 セットで実施し、`emit_deny_with_recovery` ヘルパで hook 文言も統一。

### T5. 公式仕様追従に隙

C-4（SessionStart `resume` 欠落）と S-5（`readOnly: true` 架空フィールド）が示すのは「公式 docs を**一度しか**読んでいない」可能性。emit.sh の「verified 2026-06-05」注記の運用を、settings / agents / skills 全体に拡張するべき。

**解**: `tests/test_official_spec_currency.py` を新設し、各 frontmatter キー・matcher 値・hook event 名を公式表からハードコードして単純比較。公式が変わったら CI が落ちて気づける。

### T6. 他フレームから取り込む最小手は 2 つ

軸 F が選んだ**戦略 A**（v1.7 で最小取込・v2.0 再設計は時期尚早）：

1. **superpowers 流「skill description が trigger 文として書かれているか」eval**
   - 出典: `superpowers-main/skills/*/SKILL.md`（"Use when X, before Y" 形式）
   - 組込先: `scripts/check_framework_contract.py` に「skill frontmatter description が "Use when" を含み 40 文字以上」契約を追加
   - 効果: 非エンジニアが skill 名を覚えなくても phase 遷移時に自動起動しやすくなる

2. **gstack 流 ETHOS preamble の規範化**
   - 出典: `gstack-main/ETHOS.md` ＋ `scripts/resolvers/preamble.ts`
   - 組込先: `aegis/PHILOSOPHY.md`（200 字で「決定論 moat / 証拠で完了 / 3 失敗で停止」を再表明）を新設し、`scripts/build-skill.sh` で全 skill 冒頭に注入
   - 効果: skill 単独で読まれた際にも moat の理由が伝わり、judge を任せた LLM の判断軸が揃う

**取り込んではいけない**：gstack の LLM-as-judge を CI 常設（決定論 moat に非決定論の眼が乗る）／everything-cc の 30 agents/135 skills スケール（非エンジニアに選ばせる時点で破綻）／command→agent→skill 3 段オーケストレーション（デバッグ不能）／superpowers の zero-dependency 配布モデル（hook を捨てると moat も消える）。

---

## 3. 優先順位付き提案バックログ

### v1.6.1（マージ前ブロッカー・3〜5 日想定）

1. **C-1** 制御プレーン bypass を fail-closed 化（PoC 7 経路を test_check_control_plane で fixture 化）
2. **C-2** test-runner 分類に「passed/failed/PASS/FAIL/session starts」マーカー再確認（forge を unverified へ）
3. **C-3** `client_ready_for_dev` の 6 成果物に「sentinel 文字列」または「最小バイト＋必須見出し」を要求
4. **C-4** SessionStart matcher を `"startup|resume|clear|compact"` に拡張＋契約テスト
5. **C-5 / C-6** arch-overview.md の `user-invocable` 表・hook/lib/drift カウントを一斉訂正
6. **S-3** `.env` `git add` 異形 4 種＋`stash`/`stage`/`update-index` を deny に追加
7. **S-11** `hooks/lib/phase-skills.sh` を REQUIRED_HOOK_FILES に登録（F6 同型穴の封鎖）

### v1.7（構造強化・10〜15 日想定）

8. **T1** 単一所有の水平展開：`--print-gate-ref-map`（python）→ bash が動的読み込み。phase 配列も同様
9. **T2** `scripts/generate_arch_inventory.py` ＋ `ALL_CHECKS` 契約化（手書きカウント drift の恒久封鎖）
10. **T3** `extract_*_strict()` / `extract_*_fast()` API 分離 → deny 系は strict 強制
11. **T5** `tests/test_official_spec_currency.py` 新設（公式表の手動写経＋簡易比較）
12. **T6-1** skill description trigger eval を `check_framework_contract.py` に追加
13. **T6-2** `aegis/PHILOSOPHY.md` ＋ `scripts/build-skill.sh` の preamble 注入
14. **C-7** `update-gate.sh` のロック wait iteration を環境変数で差し込み可能化 → テスト時 N=3 / iter=10ms
15. **C-8** `validate_status_file` を `_validate_*` 純関数列に分割 → fixture も検査単位に
16. **C-9** `hooks/lib/secrets-patterns.sh` 新設で credential リストを単一所有化

### v1.7 並行（北極星 UX・8〜10 日想定）

17. **S-16** README L1 行目で onboarding へ送る／L2-30 を「監督＋検査官」縮約版に
18. **S-17** migration log を `docs/CHANGELOG.md` に外出し
19. **S-18** 全テンプレに「悪い例／良い例」1 行ずつ。`MANUAL.template.md` の体裁を標準化
20. **S-19** `emit_deny_with_recovery` ヘルパ＋全 hook で統一

### v1.8 以降（任意）

- 公式 frontmatter の `disallowedTools` / MCP scoping / `isolation: worktree` 活用
- `.claude/commands/*.md` → skills へ移行
- judge card secret regex を gitleaks 代表 10〜15 件に拡張
- `CLAUDE.md` Completion Rule の 3 declarative 条項を機械検査化

### v2.0 検討（6 ヶ月後判断）

- `CLAUDE.md` を `SOUL.md`（思想）／`RULES.md`（運用契約）／`EVALUATION.md`（評価規範）に正式分離（ECC 流）
- v1.7 の効果が出てから着手。今やると行動レビュー直後の落ち着きを壊す

---

## 4. よく書けている点（評価）

過去 4 回でも触れた決定論 moat 以外で、今回新たに評価できる構造：

- **`hooks/lib/patterns.sh` の単一所有 + `tests/test_patterns_parity.py`**：同じ regex を bash(grep -E) と python(re) で消費する典型的二重実装に対し、共通 fixture で挙動一致を強制。「禁止構文 `[[:space:]]` / `\b`」を明文化し CI で捕捉。**他の二重領域（T1）に水平展開すべき教科書的防衛機構**
- **`hooks/lib/phase-skills.sh` 単一所有 + BFS 到達性検証**：skill 起動経路を「`names="..."` を root に BFS」と機械検査可能な形に閉じている。`test_skill_reachability` は実 SUT を tempdir に scaffold して検査するので DSL 変更時も reachability が落ちれば必ず気づく
- **`tests/test_hook_required_coverage.py` の双方向 ⊆ 契約**：registered ⊆ REQUIRED と REQUIRED ⊆ registered を別個に検査。新規 hook を追加して「契約・テンプレ・設定」のどれか 1 つを忘れたら CI で必ず止まる
- **`check_reference_drift.py:check_mirror_identity`**：`examples/minimal-project` を byte-identical で維持。95 ファイル mirror の維持コストは drift 検査の機械化で実質ゼロ、「本体と乖離した嘘の example が出荷される負債」を完封
- **`docs/onboarding/02-explainer.md`**：「監督＋検査官」のたとえは極めて秀逸。北極星「非エンジニアが上流〜保守まで非スラップ」の到達点を明確に表現。**README L1 に持ち込むだけで初見の腹落ちが激変する**
- **`MANUAL.template.md` / `RUNBOOK.template.md` / `UAT-RESULTS.template.md`**：記入例・コメント注記が手厚く非エンジニアでも独立して書ける。**他テンプレの標準にすべき体裁**
- **judge card の tri-state（🟢🟡🔴 ＋ ack）**：非エンジニアにも「進める／止まる／確認」が 3 択で見える理想形
- **`hooks/lib/emit.sh` の「verified 2026-06-05」注記運用**：公式追従の証拠を残す習慣は良い。他の frontmatter／settings にも拡張すべき

---

## 5. 総評

**修正後マージ（v1.6.1 で Critical 9 件をクリア → v1.7 で構造強化）**。

理由：
- 9 件の 🔴 のうち **C-7（テスト sleep 70%）と C-8（巨大関数）以外は 1 日でクリア可能**。C-7 / C-8 は v1.7 の構造強化で扱う
- v2.0 再設計は**時期尚早**。v1.6.0 で実装した P1×4（行動レビュー由来）の効果検証期間中であり、構造を二度動かすと負債が累積する
- 軸 F が指摘する「他フレーム取り込み」は最小手で済む（哲学テキスト 2 枚＋trigger eval 1 本）。**北極星「非エンジニアが上流〜保守まで非スラップを作れる」は v1.7 で射程に入る**

決定論 moat は今回のレッドチーミングでも**fail-closed 設計の大半は破れなかった**（normalize、検査対称、UTF-8 偽装、F6 教訓のスキャフォルド smoke）。穴は「fast-path に倒れた deny 検査」と「doc の手書きカウント」の 2 系統に集中している。両方とも構造的に塞ぐ道筋がある。

次サイクルの最大の隠れリスクは、**onboarding の品質をそのまま正面玄関に持ち込まないこと**。せっかくの「監督＋検査官」が、README L1 で「Claude Code native distribution」に阻まれて読まれずに終わる。

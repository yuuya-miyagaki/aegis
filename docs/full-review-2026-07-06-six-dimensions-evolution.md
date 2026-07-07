# Aegis 全体レビュー 2026-07-06 — 6次元＋外部比較＋進化プラン

> 対象: aegis v1.21.0（コミット 9ae1f2f・push 済み・クリーンツリー）
> 方法: 6次元（moat / gate-flow / context-budget / skill-guidance / distribution / test-strength）の独立レビューエージェント並列 fan-out ＋ ローカル7ハーネス比較 ＋ Web 動向調査（2026-07 時点）。全レビューは read-only 厳守（conf9 準拠・tree 変更ゼロを git status で確認済み）。
> 検証: Critical/High 級所見は親セッションが実フック起動・grep・ドライラン再現で反証チェック済み（下記に verified 印）。
> 既知照合: docs/LEARNINGS.md・docs/security-followups.md・full-review-2026-06-13/24 と突合し、既知・修正済み事項は除外または「既知」明記。

---

## 1. エグゼクティブサマリ

**総合評価: 差別化資産は世界水準・ただし「自分が立てた原則を自分が破っている」箇所が3系統ある。**

1. **強みの確認（外部比較で裏付け）**: enforcement・evidence 体系（tamper-evident gate / OS-lock / evidence fingerprint / B1 mutation drill / 盲検2次）は、調査した全フレームワーク — superpowers(★247k)・ECC(★226k)・spec-kit(★118k)・BMAD(★50k)・ローカル7ハーネス — のいずれにも相当機構が存在しない。**ここは唯一無二の moat であり、進化の軸足にすべき差別化資産。**

2. **最重要問題（内部）は3系統**:
   - **(A) iter60 事故クラスの再発防御がゼロ** — conf9 教訓は LEARNINGS に記録されたが、guidance（grep 0 ファイル）にも機械防御（`git checkout <pathspec>`・`git stash` は実フック検証で allow 素通り）にも反映されていない。さらに session-start が snapshot を無条件再生成するため、**次の同型事故では復旧アンカー自体が失われる**。
   - **(B) 罠18項目の約6割はフレームワーク自身の設計負債の人間側転嫁** — 根は「fingerprint の HEAD sha 束縛」と「judge の newest-entry 即断」の2点に集中し、いずれも配線変更レベルで根絶可能。「非エンジニアが回せる」北極星に対し、現状は正しい操作列の暗記（職人芸）を要求している。
   - **(C) 自原則との矛盾** — thin L0 哲学に対し STATUS.md（常時ロードの69%・無予算）が肥大。「S サイズ」は check-gate が task_size を見ないため広告どおりに使えず全タスクが M 儀式へ逃避。正規 upgrade 手順は OS-lock と衝突し全実インストールで死ぬ。quality-pin（opus）は Fable 5 世代で反転済み（品質役ほど弱いモデルで走っている）。

3. **進化の方向（外部ギャップ）**: 欠けているのは (1) CI/第三者検証経路（ゲートの再実行が本人のローカルのみ）、(2) プロセススキルの深さ（デバッグ規律・計画品質規格・リサーチ規律）、(3) 学習・決定の永続化（決定ログ・retro 半自動蒸留）、(4) plugin 配布、(5) Client モードの cost/risk/change（v7 蒸留の取りこぼし）、(6) 出荷後監視（canary）。逆に swarm・ベクトルメモリ・マルチホスト対応は北極星と不整合であり**追わない**のが正しい。

---

## 2. 確定所見（重大度順・次元横断統合)

凡例: [次元] / verified=親セッションで実地検証済み / 新規=既知レビュー・LEARNINGS 未収載

### 🔴 R1. iter60 事故クラス（検証サブエージェントの tree 破壊）に対する防御が三層すべて欠落 — [moat×skill 収束・新規・verified]

- **文言層**: `grep -rn 'checkout|git reset|stash' .claude/` → **0 ファイル**。routing.md の Subagent continuation 節・aegis-review-gate/security-gate の盲検2次ディスパッチ節・qa-verification の5点拘束、いずれにも tree 変更禁止なし。iter60 で実際に事故を起こした security-gate 経路も未防御。エージェント定義の汎用文言（「do not use Bash commands that modify files」reviewer.md:56 等)は**存在したのに事故を防げなかった**ことが実証済み（「復元」は modify と合理化されない）。
- **機械層**: `hooks/lib/patterns.sh:25,27` は `git checkout/restore` の `.` 形と `--` 形のみ。**実フック起動テストで `git checkout docs/*` → `{}`(allow)、`git stash` → `{}`(allow) を確認**（`git checkout .` は正しく ask）。
- **復旧層**: `hooks/session-start.sh` が `aegis_write_snapshot` を**無条件**実行 → revert 事故後に resume/compact が一度走ると、iter60 復旧の生命線だった `.claude/.gate-snapshot` が revert 済み STATUS から再生成され消失。同経路は「raw Edit 改竄 → block 無視 → 次セッションで snapshot laundering」という cross-session re-bless にもなる（既知の受容「tamper-evident は revert しない」がセッション境界を越えて想定より広いことは未整理）。
- **修正方向（三層セット）**: (1) routing.md に「検証系委譲の標準拘束雛形」を単一正本で置き qa-verification 5点＋6点目「read-only・git checkout/reset/clean/stash 禁止・汚したら報告して触るな」を規定、review/security/subagent-dev から参照＋token-pin。 (2) patterns.sh に `git\s+(checkout|restore)\s+[^-]`（bare pathspec）と `git\s+stash` を追加（ask）。 (3) session-start の snapshot 再生成を「gate 退行検知つき条件付き」へ — 後退（approved→pending）検出時は上書きせず WARNING＋/recover 誘導。将来: 新 hook イベント `SubagentStart`（platform は現在32イベント）での注入を検討。

### 🔴 R2. S サイズは feature/refactor でコード編集が構造的に不能 — [gate-flow・半既知の一般化・verified]

- `hooks/check-gate.sh` の task_size 参照 **0 件**（grep 確認）。plan gate 未承認で無条件 deny（:247-252）。plan フェーズは S に存在せず（`SIZE_ALLOWED_PHASES["S"]` に plan なし）、feature は plan を n/a 化できない（`pre_na_gate` は bugfix/hotfix 限定）。rule 文書「skipped phases exempt their gates」・python 側実装に対し **bash hook だけが例外を未実装の三者不整合**。
- 帰結: S の存在意義が事実上なく、1ファイル級の変更も M 儀式（ゲート6＋judge3＋B1＋盲検2次×2＋record 儀式）へ逃避 — 過剰オーバーヘッドの主因。LEARNINGS:91,93 は「framework-M が唯一クリーン」という暗記で受容していたが、設計欠陥として再構成すべき。
- 併発: S の terminal（罠 q）— `check_phase_transition` は `allowed_after_old` が空リストだと検査スキップ（check_status.py:1336-1341）で ship→docs が rc0 通過、static 検査だけ FAIL する割れ。
- **修正方向**: check-gate.sh が STATUS から task_size を読み size-skip フェーズのゲート要求を差し替え＋transition 検査の空リスト穴封鎖＋**S に docs を含めて terminal を M/L と統一**（罠 q 自体が消える）。

### 🔴 R3. 正規 upgrade 手順が「一度でも使った install」で必ず死ぬ（OS-lock × setup.sh 衝突） — [distribution・新規・ドライラン実証]

- `cp-lock.sh` が hooks/scripts/templates 等を chmod a-w（session-start で非 framework task_type 時に毎回 engage・永続）。`bin/setup.sh` は `cp -f`＋`set -e` → **再インストールが `cp: Permission denied` rc=1 で途中 abort**（scratchpad で再現済み）。status_doctor 自身が「Re-run bin/setup.sh」と案内するのに、その手順が全実インストールで失敗。原因説明ゼロ・mixed-version 残置・rollback なし。既存 upgrade テストは未 lock target でしか走らないため検出されず（iter57 の OS-lock 昇格が 06-24 レビュー後のため既知レビューにも未収載）。
- **修正方向**: setup.sh 冒頭で `aegis_cp_unlock` self-heal（再 lock は次回 session-start 任せ）＋locked-target 回帰テスト＋lock 起因のエラーメッセージ。v1.21.1 パッチ級。

### 🔴 R4. B1 drill の看板「偽造不能」に原理的フォージ穴 — [test-strength・新規・verified]

- `run-test-strength-drill.py` の parse_spec は test_command を非空文字列としか検証しない。`test_command: "pytest --collect-only -q"`＋構文破壊 mutant で **1件もテストを実行せず DRILL PASS が成立**（baseline=収集成功 green、mutant=収集エラーで全数 caught）。evidence 側には同クラスを封じる `AEGIS_TEST_NO_RUN_FLAG_REGEX`（evidence.sh:127-131）が既にあるのに drill 側が未消費 — **非対称を grep で確認済み**。
- 併発: mutant の意味的品質が未強制（anti_gaming は配置検査のみ）— 構文破壊 mutant だけで coverage floor 充足可＝「assert の強さ」を証明しない。
- **修正方向**: parse_spec で NO_RUN regex を single-source 消費して reject（数行）＋mutant を `py_compile`/`bash -n` で parse 検証し構文破壊 mutant を spec エラー化。

### 🟠 R5. quality-pin が Fable 5 世代で反転（現在進行の実害） — [distribution・既知バックログの実害確定]

- `platform_manifest.py:27` の `ALLOWED_MODELS={"opus","sonnet","inherit"}` に `fable` なし。公式 doc（2026-07-04 build）検証: `fable` は有効 alias で Fable 5 に解決、`opus`=Opus 4.8（一段下）。現運用（セッション既定 claude-fable-5）では **implementer（inherit）が Fable 5、planner/security/reviewer/qa（opus pin）がより弱い Opus 4.8** — 「品質役ほど最上位」の設計意図が反転済み。frontmatter pin はセッションモデルより優先のため `--model` では直らない。系譜移行は実際には4面（manifest 2 set＋POLICY dict＋agent 12＋CLAUDE.md×2）に及ぶ。
- **修正方向**: `fable` 追加＋quality-pin 4 role 移行＋`OPUS_ONLY_EFFORTS` を top-tier-pin へ改名。`best` alias（最上位へ自動解決）の frontmatter 受理を実機検証し、通るなら**世代交代自体を無改修化**。

### 🟠 R6. 罠18項目の約6割は設計で根絶可能（2つの根に集中） — [gate-flow×test-strength 収束]

分類結果: **設計で潰せる=10（a,b,c,d,e,l,m,n,q,r）／軽減可=1（f）／doc・表示で十分=7／「本質的に必要な注意」=実質 0**。

| 根 | 症状 | 修正（いずれも既存機構内の配線変更） |
|---|---|---|
| **fingerprint の HEAD sha 束縛**（fingerprint.sh:87） | 罠 r → 順序制約 b/c/d を連鎖誘発。docs-only コミットで green が unverified 化し record 儀式を強制 | `head:<sha>` → **非 docs/.claude の tree-hash**（`git ls-tree -r HEAD` から docs/・.claude/ 行を除外して hash）。コード変更コミットは必ず fp が動く＝silent-green 防止は完全保存（test-strength 次元で性質保存を論証済み）。移行は marker_verified 導入時と同型で安全 |
| **judge read_test_result の newest-entry 即断**（build-judge-card.py:223-240） | 罠 e・m・並走シャドー。判定不能エントリが新しいだけで green が消え、クォート技法の暗記を強制 | 判定不能エントリ（fp 不一致/observed で marker 無し）を return でなく **continue**（skip して次に古いエントリへ）。採用条件は依然「runner ∧ fp==current ∧ (manual∨marker)」で健全性不変。検証済み red が newest なら従来どおり red が勝つ |
| SIGPIPE（update-gate.sh:241-252 が書込み前に大量出力） | 罠 a（tail 必須の暗記） | 状態変更を出力より先に or `trap '' PIPE` |
| ref/approve の順序結合（stale-ref violation） | 罠 b/c | `update-gate.sh <gate> approve --ref <path>` で**原子化**＋pending+ref を advisory 降格（writer が reset 時 null 化済みの現行では防御価値が冗長） |
| コメントハンク floor 割れ／committed diff 空 | 罠 l/f | coverage floor から「コメント/空行のみのラン」を言語別に自動除外＋`--since <baseline-ref>` モード（LEARNINGS:76 既起票の実装） |
| record の引数事故 | 罠 n | 引数を `AEGIS_TEST_RUNNER_REGEX` で事前検証し、非該当は red 記録でなく usage エラー |

この6修正で罠 a,b,c,d,e,l,m,n,q,r の10項目が消え、**STATUS next_action の罠常駐（→R8）も解消可能になる**。

### 🟠 R7. ゲート承認が「時点証明」のまま完了まで有効扱い — [gate-flow・新規]

- 承認時のみ judge が fp/tests を見る。承認後のコード変更（docs フェーズでの「ついで修正」等）を無効化する機構がなく、完了検査（TaskCompleted / dev_ready_for_client）は refs 存在のみ。LEARNINGS:105 はプロセス注意として記録するのみ。
- **修正方向**: 承認時 fp を `.gate-snapshot` に記録 → 完了検査で現 fp と比較、不一致は 🟡 fail-visible（ack 可）。**機構は全部既存・配線のみ**でゲートを「完了時点まで有効な証明」へ格上げする最大の残り伸びしろ。

### 🟠 R8. thin L0 哲学と STATUS.md 肥大の自己矛盾 — [context-budget・新規・実測]

- 常時ロード実測: CLAUDE.md 641語(~1.3k tok)＋**STATUS.md 1,123語(~5.3k tok・無予算)**＋rules(~0.75k)＋session-start 注入(~0.4k) ≒ **7.7k tok、うち69%が予算非管理の STATUS.md**。next_action の罠18項目(~1.5k tok)は恒久知識で LEARNINGS と重複（罠r↔conf9 等）— CLAUDE.md:10 が「auto-memory は LEARNINGS を複製するな」と定める非対称。session_history も件数 cap のみでサイズ無制限（3件 ~1.7k tok）。
- 併発: CLAUDE.md budget（650語）headroom **9語** — contract が raw word_count を使い budget-exclude 機構が届かないため、skill 1本追加→drift 契約が CLAUDE.md 追記を強制→即超過の地雷。iter60 が routing.md で解いた病理と同型。
- **修正方向**: (1) R6 完了後に残存罠を LEARNINGS `[phase:X]`/L2 へ移管し next_action を「次の一手＋参照1行」に縮約、check_status に next_action 語数上限（まず warning）。効果 −2.5〜3k tok（**常時ロード −35%**）。(2) contract の CLAUDE.md 計数を `_budget_word_count` 化＋Skills roster をマーカー包み＋専用ガード＋allowlist 更新。(3) session_history エントリのサイズ規約1文。

### 🟠 R9. guidance と enforcement の矛盾5件（従うと機械 block/ERROR を踏む） — [skill-guidance・新規]

| # | 矛盾 | 根拠 |
|---|---|---|
| M-1 | aegis-brainstorm Step D「phase→plan 更新が先、brainstorm 承認が後」— **phase-skip 検査で必ず block** | SKILL.md:69-74 vs check_status.py PHASE_REQUIRES_GATES＋post-status-audit:158-175。state-machine.md:34 の正順とも矛盾 |
| M-2 | ship-and-docs 前提「qa/security: approved または n/a」— qa/security は**構造的に n/a になれない**（n/a は brainstorm/plan×bugfix/hotfix 限定）。qa.md:21/security.md:21 の n/a 文言も死文 | SKILL.md:24-25 vs check_status.py:1146-1158 |
| M-3 | チートシート「deploy は小タスクなら n/a でよい」— 実際は ERROR 拒否。同ファイル内でも自己矛盾 | onboarding/03-cheatsheet.md:52 |
| M-4 | チートシート K-13「第2意見は S なら state-machine 規約で省略可」— **その規約は存在しない**（grep 0件）。盲検2次必須化と矛盾し、ack 濫用を誘導 | 03-cheatsheet.md:76 |
| M-5 | /next のフェーズ×スキル表が正本 phase-skills.sh から drift（review/qa/security 行で必読スキル欠落）— SoT 二重化 | next.md:34-44 vs phase-skills.sh:36-40 |

- **修正方向**: 一括修正＋恒久化として「guidance 内の機械可検証な主張（gate 名・n/a 可否・フェーズ順序）を check_status.py の enum と突合する静的検査」を追加 — **presence-pin の汎用化より費用対効果が高く、既知バックログ「意味ドリフト機械化」の現実的な次の一歩**。

### 🟡 R10. Medium/Minor 所見（要対応・箇条书き）

- **[dist F-2]** baseline commit が settings.local.json を履歴に焼き込みうる（作者機のグローバル gitignore が隠蔽・配布先で発現）→ ensure_target_gitignore に追加
- **[dist F-3]** ユーザー自身が足した hooks が再 install で無警告消滅（`if k=='hooks': continue`）→ aegis 非所有エントリは保全 or 破棄警告
- **[dist F-4]** install profile 無記録 — upgrade 時の profile 取り違え（full→standard）で enforcement がサイレント縮退 → stamp を {version, profile} JSON 化＋相違 abort
- **[dist F-6]** manifest 陳腐化検知が field install でほぼ機能しない（minimal/standard は manifest 非配布・/validate は drift 未呼出・staleness 180日はモデル市場に不適合）→ session-start にセッションモデル系譜 advisory 1行＋models 窓 60-90 日
- **[dist F-8]** uninstall 手段なし＋profile 切替が additive-only（lock 残骸で rm -rf も失敗する詰み方）→ install manifest 逆再生
- **[gate F6]** 依存ゼロ repo で deps=unverified が恒久 🟡 → 毎 iteration 無意味 ack の踏み車。manifest 不在は info へ降格
- **[gate F9/F10/F12/F13]** rollover 手作業（authorized writer 不在）→ rollover.sh ／ dead enum `blocked` ／ /next size 非対応 ／ size 除外ゲートの無意味承認が可能
- **[gate F11]** iteration 検証が非 ASCII 数字で crash（isascii ガードが片側未適用）
- **[test #3]** judge カード「テスト: green」がスコープ非表示 — 単一ファイル green と full suite green が見分け不能（fail-visible の欠け）→ 決定エントリの cmd/src/ts をカード表示
- **[test #5/#6]** Tier1（contract full self-check・drift 8/10・eval 系）が pytest 非到達 ／ status_doctor 等運用 CLI 3本が挙動テストゼロ
- **[test #8]** suite wall time の37%が update-gate.sh のハードコード lock 待ち → env 化で 233s→~150s
- **[moat Minor]** dogfood repo 自身の settings.local.json が template より薄い（skill-gate/tdd 等未配線）／ask 依存 tripwire は自走×サブエージェント文脈で人間不在（update-task.sh の framework 昇格=moat 解錠が ask のみ）／snapshot 整合検査が task_type/size の空欄を見ない
- **[skill m-1〜m-6]** qa/security agent に disallowedTools なし（reviewer と非対称）／bug-diagnosis の手順逆順／translation mapping タイミング揺れ／model pin 優先順位未記述／tutorial の gate→reviewer 語順逆／ship|docs の必読5本一括注入は task_type 分岐で2本に絞れる（~3.5k tok 削減）
- **[budget #3]** 語数計数が CJK をほぼ数えない（budget 数値≒トークン実費の1/3〜1/5・言語スイッチで迂回可）— 既知コアの未処理含意。全 re-seed 必要のため低優先

---

## 3. 外部比較（何が強く・何が足りないか）

### 3.1 確認された差別化資産（伸ばす軸）

調査対象: obra/superpowers(★247k)・affaan-m/ECC(★226k)・github/spec-kit(★118k)・claude-mem(★86k)・ruflo(★63k)・BMAD(★50k)・beads/gastown・SuperClaude・agent-os・ローカル7ハーネス（superpowers/gstack/everything-claude-code/best-practice/gsd-2/ultra-v7/ultradesign-v2）。

**tamper-evident gate 簿記・OS-lock・evidence fingerprint・B1 mutation drill・盲検2次レビュー・context budget ラチェットの組合せは全調査対象に相当物なし。** 他は文書＋名誉制（superpowers の verification も自己申告）か警告どまり。上流 Client モード（要件〜UAT〜翻訳）を持つのも aegis/v7 のみ。

### 3.2 欠けている能力カテゴリ（重要度順）

| # | カテゴリ | なぜ重要か | 参考実装 | aegis に入れる形 |
|---|---|---|---|---|
| 1 | **CI/チーム統合** | ゲート・judge・B1 が全てローカル1セッション完結＝本人以外が検証不能。CI は改竄不能な第三者実行環境で evidence 哲学と最も相性が良い | anthropics/claude-code-action(公式) | `extensions/ci/`: PR 時に contract＋judge-card＋B1 を再実行し結果を PR コメント化。盲検2次の CI 版 |
| 2 | **プロセススキルの深さ** | 強制の外側「LLM の思考手順」が薄い。いずれも skill 改稿のみで thin 思想を壊さない | superpowers systematic-debugging / writing-plans / receiving-code-review | bug-diagnosis に4フェーズ＋Iron Law＋レッドフラグ表統合、plan 成果物に「プレースホルダ禁止・2-5分粒度」規格、新 research skill（search-first・出典検証→external_evidence 接続） |
| 3 | **学習・決定の永続化** | LEARNINGS は手動起票のみ＝書き忘れは消える。「なぜこの設計にしたか」の決定ログがなく再訴訟が起きる | gstack decisions.jsonl / ECC continuous-learning-v2 / beads | `docs/DECISIONS.md`（script 経由のみ追記=PaC 整合・再導出不能な決定のみ）＋retro 時に evidence-log からパターン候補抽出→**人間承認で** LEARNINGS 昇格（自動書込みはしない=claude-mem の HIGH リスク監査事例と整合） |
| 4 | **plugin/marketplace 配布** | 配布物化戦略の本丸。settings マージ・stale prune・uninstall・upgrade×lock 衝突（R3）の問題クラスが**構造ごと消える**。894行 check-control-plane 退役バックログとも整合 | superpowers の marketplace 掲載 / claude-plugins-official | 「hooks+skills+agents+commands=plugin、setup.sh=STATUS/LEARNINGS scaffold 専任」の2層から段階移行。`/aegis-init <profile>` |
| 5 | **行動シナリオ eval（Tier4）** | 「同一モデルでもハーネス差でベンチ10-20点振れる」— 現 Tier0-3 は構造契約検証であり行動品質を測れない | ECC verification-loop / DeepEval v4 / arxiv 2604.25850 | **過去の運用事故（iter60 の git checkout 事故・gate 飛ばし誘惑・改竄誘惑）を敵対シナリオ化**し、盲検 LLM 採点＋決定論チェックで回帰測定。事故が資産になる |
| 6 | **出荷後監視（canary）** | 北極星「保守まで」に対する明確な未充足。deploy gate の後「見張る」仕組みが runbook 含めゼロ | gstack canary/benchmark | deploy skill に ship 後 canary 手順（console エラー・死活・性能前後比較）→ maintenance トリアージ接続。実行は既存 qa-browser 流用 |
| 7 | **Client モードの cost/risk/change** | v7 蒸留の取りこぼし。**見積フェーズなしで Dev に渡る**のは受託の北極星に対し構造的欠落 | ultra-framework-v7 client/cost・risk・change | client-workflow へ統合（成果物テンプレ必須）。change は iteration ルールに変更影響セクション |
| 8 | **サブエージェント運用の堅牢化** | 「完了しました」の鵜呑み・失敗種別を区別しないリトライ | superpowers status enum / gsd-2 recovery taxonomy | routing.md に DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED＋ステータス別対応表（R1 の委譲拘束雛形と同居） |
| 9 | **Observability/コスト実測** | cost-tracking テンプレ（手動）は 2026 年水準で見劣り。native OTel は設定同梱だけで動く | 公式 OTel / ccusage | `extensions/observability/` に OTLP 設定＋retro_report へコスト合流 |
| 10 | **scan-at-sink リダクション** | check-secrets は commit 向けのみ。外部シンク（gh pr/issue・公開 docs）直前の検査がない | gstack redact-engine | check-secrets の PreToolUse 対象拡張＋HIGH/MEDIUM/LOW 段階制 |

### 3.3 追わないもの（北極星と不整合）

- **swarm/動的編成・ベクトルメモリ・学習型ルーティング**（ruflo 系）— 薄さ・決定論哲学と真逆
- **マルチホスト対応/AGENTS.md**（superpowers/ECC/spec-kit は全て対応）— 「Claude Code 専用で薄く保つ」は公開契約級の設計判断。対応するなら CLAUDE.md を指す shim 1枚まで
- **常駐バックグラウンド学習**（claude-mem 型）— 2026-02 のコミュニティ監査で HIGH リスク判定の前例。人間承認昇格型に留める
- **サンドボックス自作** — 敵対耐性は公式 sandbox-runtime へ委譲（full プロファイルに推奨手順を書くだけ）

---

## 4. 改善プラン

方針: **「守りの完成（事故クラス封鎖）→ 摩擦の根切り（罠を設計で消す）→ L0 純化 → 進化（配布・CI・新能力）」の順**。前段が後段の前提になる（例: 罠根切りなしに STATUS 縮約は不可、plugin 化なしに CI 配布は半端）。各バッチは aegis の iteration 慣行（1 iter = 1テーマ・M サイズ中心）に合わせて分割。

### Phase 0: v1.21.1 パッチ（即時・防御の穴3点）
| # | 項目 | 対応所見 | サイズ |
|---|---|---|---|
| 0-1 | 委譲拘束雛形（routing.md 単一正本＋6点目 tree 変更禁止＋token-pin）＋patterns.sh に checkout bare-pathspec / stash 追加 | R1 文言層・機械層 | S〜M |
| 0-2 | session-start snapshot の gate 退行検知（後退時は温存＋WARNING） | R1 復旧層 | S |
| 0-3 | setup.sh の self-heal unlock＋locked-target 回帰テスト | R3 | S |

### Phase 1: v1.22「罠の根切り」（摩擦半減・operator 体験の正常化）
| # | 項目 | 対応所見 |
|---|---|---|
| 1-1 | fingerprint: HEAD sha → 非 docs tree-hash | R6 根1（罠 r,b,c,d） |
| 1-2 | judge read_test_result: skip-and-continue | R6 根2（罠 e,m） |
| 1-3 | update-gate: `approve --ref` 原子化＋状態変更を出力より先（SIGPIPE）＋pending+ref advisory 降格 | R6（罠 a,b,c） |
| 1-4 | S サイズ修復（check-gate の size 対応＋transition 空リスト穴＋S に docs 追加） | R2（罠 q,h 周辺） |
| 1-5 | drill: NO_RUN 拒否＋mutant parse 検証＋コメントラン floor 除外＋`--since` モード | R4・R6（罠 l,f） |
| 1-6 | record-test-result 引数事前検証／deps 無 manifest info 降格／judge カードに tests スコープ表示 | R6（罠 n)・F6・test#3 |

### Phase 2: v1.23「整合と純化」
| # | 項目 | 対応所見 |
|---|---|---|
| 2-1 | guidance 矛盾一掃（M-1〜M-5＋minor 6件）＋「guidance 主張 vs enum」静的検査（意味ドリフト機械化の第一歩） | R9 |
| 2-2 | STATUS 縮約: 罠移管（Phase1 で 10 項目消滅後の残余を LEARNINGS/L2 へ）＋next_action 語数 warning＋session_history サイズ規約 | R8 |
| 2-3 | CLAUDE.md への budget-exclude 適用（contract 計数差し替え＋ガード） | R8 併発 |
| 2-4 | fable lineage 移行（`best` alias 実機検証→quality-pin 更新）＋session-start モデル系譜 advisory | R5・F-6 |
| 2-5 | rollover.sh（iteration リセットの authorized writer 化）＋/next の size 対応機械算出 | F9・F12 |
| 2-6 | 配布衛生: gitignore 追加・ユーザー hooks 保全・install manifest {version,profile,paths}（uninstall の基盤） | F-2/3/4/8 |

### Phase 3: v2.0「進化」（配布物化＋新能力・テーマ別に iter 分割）
| # | テーマ | 内容 |
|---|---|---|
| 3-1 | **plugin 化 PoC** | hooks+skills+agents+commands を plugin 構造へ、setup.sh は scaffold 専任。成立すれば R3/F-3/F-7/F-8/F-9 の問題クラスが構造ごと消え、OS-lock の守備範囲縮小（894行退役バックログ）とも整合 |
| 3-2 | **CI extension** | PR 時 contract＋judge＋B1 再実行→PR コメント。チーム/第三者検証経路の新設 |
| 3-3 | **プロセススキル移植** | bug-diagnosis 4フェーズ化・plan 品質規格（プレースホルダ禁止）・research skill・サブエージェント status enum＋recovery 分類 |
| 3-4 | **学習・決定の永続化** | DECISIONS ログ（script 追記のみ）＋retro 半自動蒸留（人間承認昇格） |
| 3-5 | **Client 補完** | cost/risk/change を client-workflow へ統合＋成果物完成度チェック（v7 の check_client_deliverables 思想の aegis 流再実装） |
| 3-6 | **Tier4 行動 eval** | 運用事故の敵対シナリオ化＋盲検採点。以後のフレームワーク変更の回帰基盤 |
| 3-7 | **運用系** | canary/保守後監視 runbook・OTel/ccusage 連携・scan-at-sink 拡張 |

### 優先順位の考え方（推奨）
1. **Phase 0 は即時**（次 iteration）— R1 は「同じ事故がもう一度起きたら今度は復旧できない」状態であり、他のどの改善よりも先。
2. **Phase 1 が最大 ROI** — 罠10項目の根絶は「非エンジニアが回せる」北極星の回復そのもの。全修正が既存機構内の配線変更で、リスクが低い割に operator 体験が一変する。
3. **Phase 3 の先頭は plugin 化 PoC** — 配布系の Medium 群（F-3/4/7/8/9）は plugin 化で消えるものが多く、個別修正（2-6）とどちらに投資するか PoC の結果で決めるのが二度手間回避になる。PoC を早めに回し、2-6 は plugin 化が遠い場合の保険として最小限に。

---

## 5. レビュー実施メタ情報

- 6次元エージェント＋比較2エージェントの計8並列（すべて read-only・tree 変更ゼロ確認済み）
- full suite 実測: 1056 passed / 2 skipped（case-sensitive FS・shellcheck 不在＝環境条件つき by-design）/ 233s / 実行後 porcelain クリーン3回確認
- Critical/High 所見の親セッション反証チェック: patterns.sh regex 実フック起動（`git checkout docs/*`→allow・`git checkout .`→ask・`git stash`→allow・`rm -rf build`→safe-targets 例外で意図設計）、.claude/ 内 tree 変更禁止文言 grep 0、check-gate.sh task_size 参照 0、session-start snapshot 無条件再生成、drill NO_RUN 非対称、setup.sh lock 衝突ドライラン再現
- 出典付き外部調査の詳細（★数・URL・各プロジェクト分析）はレビューセッションの調査ログに基づく。主要: github.com/obra/superpowers・affaan-m/ECC・github/spec-kit・bmad-code-org/BMAD-METHOD・anthropics/claude-code-action・anthropic-experimental/sandbox-runtime・code.claude.com/docs/en/agent-teams ほか

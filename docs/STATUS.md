---
framework: aegis
framework_version: "1.19.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iteration 58（framework・qa-browser 委譲プロンプト標準化・guidance のみ）= M。footprint は .claude/skills/qa-verification/SKILL.md（委譲ルール節を標準プロンプト雛形へ）＋tests/test_skill_guidance_tokens.py（load-bearing トークン pin）＋.claude/agents/qa.md（Browser QA 節を skill 参照へ縮約＝grill-plan 致命1: 委譲 guidance の単一正本化）の3ファイル＝M（2-5）。moat 非該当（skill guidance のみ・hook/判定コード不変）＝M framework は review+qa+security 必須・deploy 自動 exempt。"
iteration: 58
ui_surface: false
last_updated: "2026-07-05T15:50:36Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: pending
  dev_ready_for_client: approved
current_refs:
  requirements: []
  plan: docs/plans/2026-07-05-iter58-qa-browser-delegation-plan.md
  spec: docs/specs/2026-07-05-iter58-qa-browser-delegation-design.md
  review: docs/qa-reports/iter58-review.md
  qa: docs/qa-reports/iter58-qa.md
  security: docs/qa-reports/iter58-security.md
  deploy: null
  translation: null
external_evidence:
  - type: "second-opinion-v1-foundation-r1-r2"
    scope: "future-proof 再アーキ計画 2 ラウンドレビュー（IDE Chat）"
    findings: "R1: 全面再アーキは YAGNI(P1) / manifest は declarative mirror=第3同期先(P1) / emit.sh の python3 deny 依存=fail-open(P1) / inherit 従属 / context 数値撤廃のコスト退行 / TDD off / drift advisory 放置 / Phase F schema 過大 / STATUS 実態 drift。R2: emit.sh コメントで静的テスト自己矛盾(P1) / design doc 旧方針残骸(P2)。"
    resolution: "全面 v1.0.0=NO-GO、emit.sh 中心の縮約 Foundation=条件付き GO。pure-bash emit.sh で fail-open 解消、seed manifest と check-secrets 集約は descope。Foundation を F0/F1/F2 で実装し main にマージ（183 tests green）。"
  - type: "second-opinion-v0130-r5"
    scope: "v0.13.0 計画 5 ラウンドレビュー"
    findings: "Round 1〜5 で計 25 件の指摘（hook 出力スキーマ陳腐化、TaskCreated/Completed 制御方式、Plan 条件付き許可、effort 配分、pre-compact.sh 同種破損、`if` 単一 rule 制約等）"
    resolution: "Rev.5 で全件反映、Phase 0a 即時実装着手 GO。hotfix/v0122-hook-schema ブランチで開始。"
next_action: "**【iter58 docs 完了・全 dev ゲート approved・push 手前で停止】** ◆**現在地**: iter58/v1.19.0（qa-browser 委譲プロンプト標準化・guidance のみ）を brainstorm→plan（grill-plan 致命1「qa.md SoT 一本化」＋要検討1-5 反映）→implement(TDD・commit 8de3f8a)→grill-code(Critical/Major 0)→review(1次 approve・盲検2次 approve_with_notes・note1=SendMessage SoT 起票/note2-3=据置記録)→qa(B1 SKIP＋RED-first 代替実証・full 1050 passed)→security(1次 approve・盲検2次 approve・後退なし・deps🟡=依存ゼロ ack)→**deploy は M で exempt**→ship(v1.18→1.19・3箇所 bump・TO-CLIENT)→docs(LEARNINGS 3件)まで**全 dev ゲート approved**。実装=8de3f8a・ship/docs 成果は未コミット（evidence 5本・plan・version bump・TO-CLIENT・LEARNINGS）。 ◆**⚠ 次にやること（ここから再開）**: (1) dev_ready_for_client を承認済みなら **ship/docs をコミット**（8de3f8a に続く docs コミット）。(2) **push＝ユーザー確認待ちで停止中**（`gh auth switch --user yuuya-miyagaki` 後に push で iter58 クローズ→origin/main 更新）。 ◆**次イテレーション候補**: SendMessage 継続機構の SoT 定義（subagent-dev/routing.md へ1行・review 2次 note1・起票=TO-CLIENT/iter58-review.md）。 ◆**罠（iter41-58 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。 (r) **fingerprint は HEAD sha を混ぜ込む**（hooks/lib/fingerprint.sh＝新規未テストコミットが古い記録に一致する silent-green を防ぐ）＝green 記録は「記録時の HEAD」に束縛され、その後の**docs-only コミットでも HEAD が動けば次ゲートで tests=unverified🟡**。対処＝(a) 各ゲート承認の直前・そのゲート用の全コミット後に record-test-result、または (b) 連続ゲート（qa/security/deploy）でコードを変えないなら HEAD 固定のまま docs を未コミットで積み green を1回記録して一括承認・最後にまとめてコミット（iter57 実測・LEARNINGS conf9）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-05"
    mode: Dev
    phase: "docs"
    note: "iter56 / v1.17.0 全8ゲート approved・docs 完了（push 手前で停止）。M2 FB 6件＋可視性2件を1イテレーション一括実装（TDD）。brainstorm→plan（grill-plan 致命5件反映）→implement→grill-code（🔴1: broad-dot 境界をデリミタ列挙→否定クラス反転）→review（10並列ファインダー＋盲検2次 approve_with_notes・Major=qa ゲートで未記入 verdict 沈黙通過→1次 verdict 検証を全ゲート常時化で解消）→qa（B1 SKIP・RED-first 代替実証・full suite 1319→1322 passed）→security（盲検2次 Major=先頭ドットグロブ .en* の add-moat 純回帰を実 repo 実測で検出→グロブ節 \\.[^space]*[*?[] 追加で封鎖・commit ゲートは元々漏洩阻止・Low=verdict キー欠落の沈黙も可視化）→deploy（install 契約検証・外部デプロイなし）→ship（v1.16→1.17・LEARNINGS 蒸留2件・version 同期テストを single-owner 参照化で bump 毎手更新を撤廃）。全実装コミット未 push（push は gh auth switch 後・ユーザー確認待ち）。教訓核: moat 緩和は列挙でなく否定クラス＋グロブ展開考慮／値検査の fail-visible 保証は『どの分岐に置くか』で到達範囲が決まる（LEARNINGS conf9/conf8 追記）。"
  - date: "2026-07-05"
    mode: Dev
    phase: "docs"
    note: "iter57 / v1.18.0 主 moat 交代（OS-lock 昇格・check-control-plane 979行 退役・残余ガード check-runtime-state／EACCES advisory explain-oslock-eacces 新設・aegis_cp_verify 全数照合）を全 dev ゲート approved まで完走（push 手前で停止）。review（fix-forward: 盲検2次 Minor2＝POC v162 の退役 hook 参照 fail-open／manifest 全数列挙テスト粒度低下＋divergence: advisory=PostToolUseFailure spec 同期）→qa（B1 SKIP・RED-first 代替実証・full 1045→fix 後 1048）→security（盲検2次 Major=**難読化 unlock 形の silent 保護回帰**＝旧 check-control-plane の shlex トークナイザが deny→新平文 grep が allow・unlock 後 write で moat 無効化を実測→`_obfuscated_unlock_on_cp` で ASK 化・回帰テスト3本・SF-009 記録。deps🟡 は依存ゼロで ack）→deploy（scaffold smoke 全3プロファイル PASS・installed tree で OS-lock apply+verify）→ship（v1.17→1.18・3箇所 bump・TO-CLIENT・LEARNINGS 2件蒸留）→docs。全実装未 push（push=gh auth switch --user yuuya-miyagaki）。教訓核: (1) 静的→syscall moat 交代で syscall は write 全形を包摂するが unlock 難読形は包摂しない＝『移植』主張は旧 deny の全被覆を検証してから（1次バイパス試行が write 形に偏り2次が unlock 軸を捕捉＝盲検の価値）。(2) test-evidence fingerprint は HEAD sha 束縛＝green 記録後のコミット（docs-only でも）で次ゲート unverified→記録は各ゲートの全コミット後に置くか HEAD 固定で一括承認（LEARNINGS conf9×2）。"
  - date: "2026-07-05"
    mode: Dev
    phase: "docs"
    note: "iter58 / v1.19.0（qa-browser 委譲プロンプト標準化・guidance のみ）を全 dev ゲート approved まで完走（push 手前で停止）。plan（writing-plans）→grill-plan（致命1=qa.md の重複委譲 guidance が SoT を割る→qa.md を skill 参照へ縮約で解消／要検討1=長文完全一致 pin を短核2本へ／要検討3↔5=intro 圧縮で headroom 優先）→implement(TDD・commit 8de3f8a：委譲節を拘束5点雛形へ＋短核 token pin＋語数相殺 449/455)→grill-code(Critical/Major 0・🟢2=SendMessage 重複/`$B か`スペース・実測反証済)→review(1次 approve・盲検2次 approve_with_notes・note1=SendMessage 機構 SoT 未定義→次iter起票/note2=3-failure リンク据置/note3=[n/N done] 非pin 監視項目)→qa(B1 SKIP＝コミット済で working-tree 空・RED-first 代替実証: `最終報告を出さない`削除→FAIL・`SendMessage`全2箇所削除→FAIL・復元で緑・full 1050 passed)→security(1次 approve・盲検2次 approve・後退なし=moat/保護コード不変・secrets0・削除ブロックは存置チェックリストで被覆・browser 検査は qa-browser.md が正本・deps🟡=依存ゼロ ack)→deploy=M で自動 exempt→ship(v1.18→1.19・contract/STATUS テンプレ/live STATUS の3箇所 bump・TO-CLIENT)→docs(LEARNINGS 3件蒸留)。実装 commit=8de3f8a・ship/docs 成果は未コミット（push 前にまとめてコミット予定）。**教訓核**: (1) spurious cross-runner evidence は並走セッションだと record 後に着地して green を潰す→writer 非含スコープの最小 record で安定 green（trap m 拡張・LEARNINGS conf9）。(2) token pin は presence 保証＝重複トークンは単一削除で不発・RED 実証は全出現削除で（conf8）。(3) budget 逼迫下の guidance 追加は同一ファイル内の逐語重複除去で相殺（引き上げ=ラチェット違反・別ファイル圧縮=footprint 増を回避・conf7）。⚠ 実装中に別 Claude セッション（別 cwd prefix）の pytest が evidence-log を汚染＝メモリの『2セッション並走→静止監視必須』が実務で効いた。"
---

## Summary

Claude Code ネイティブの Aegis 運用フレームワーク。2026-06-05、モデル進化（Opus 4.8）
に耐える future-proof 再アーキに着手。v0.13.0 Phase 0b（新 Skill/Cron gate・Task event hook・
スキル aegis-* 改名）を確定後、Foundation を実装: hook 出力スキーマを `hooks/lib/emit.sh` に
単一化（pure-bash・外部依存ゼロ）、破壊パターンを `hooks/lib/patterns.sh` に隔離、version owner
を一本化。挙動不変・183 tests green・main マージ済み（origin 未push）。

## Recent Decisions

- 設計原則を「保証=決定論的強制 / 手順=モデル委譲 / 揮発値=隔離」の 3 層に分解（再アーキの土台）
- emit.sh は pure-bash（python3/jq 非依存）→ deny/block が fail-open しない（Round 2 P1 解決）
- 全面 v1.0.0 再アーキは見送り、emit.sh 中心の Foundation を先行（YAGNI、Round 1）
- seed manifest と check-secrets の patterns 集約は descope（実消費者が出来てから、Round 2 J-1）
- MCP matcher: `mcp__.*__deploy.*` — `push` は除外（通常リモート更新と区別不能）
- Ref チェック: v0.12.0 は DEPRECATION WARNING のみ、v0.13.0 で ERROR 化予定
- Name lint: regex 一本ではなく、ファイル種別ごとの小さい extractor に分割
- Health check: 警告のみ（ブロックなし）、session-start.sh から呼び出し
- Item 3 (Lean/Full プロファイルモード) はセカンドオピニオンにより v0.13.0 に延期

## Session History

- 2026-04-15: v0.7.0-v0.7.2 実装。ネイティブ機能改善、scaffold自己完結性、信頼境界ハードニング。
- 2026-04-17: v0.8.0 Client モード強化 実装完了+全ゲート通過+コミット+プッシュ。48ファイル変更。
- 2026-04-18: v0.9.0-v0.10.0 integration-assist, browser-assist。全ゲート通過+コミット+プッシュ。
- 2026-04-22: v0.11.0 Hair Salon Bloom 振り返り7施策実装+コミット+プッシュ。
- 2026-04-22: v0.12.0 MCP gate + ref check + name lint + health check。48テスト全PASS。
- 2026-06-05: future-proof 再アーキ着手。Phase 0b 確定 + Foundation（emit.sh 単一出力源 / patterns.sh / version owner）実装。Round 1/2 セカンドオピニオン反映。183 tests PASS、main マージ（未push）。
- 2026-06-06: Phase R 再配分を連続 ship（routing 0.12.3／context 0.12.4／model-effort／name-hygiene／TDD 0.12.5／evidence 完了強制 0.12.6）。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋version **1.0.0**。各タスクで brainstorm→2段グリル→実装→grill-code を完走。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0「トレッドミルから降りる」看板を掲示。**
- 2026-06-07: 機能整合性監査（charter 2026-06-07）。Layer 0-4 で 7 finding（P1×1/P2×4/P3×2）全修復。核心 F6（P1）＝setup.sh が hooks/lib を配布せず install 先で moat 全死→copy_hooks 修復＋scaffold smoke の hook 実発火で install 経路を契約化。v1.3.2 patch（298 tests・tag v1.3.2）。
- 2026-06-28: iter52（framework・permission prompt 交通整理＝read-only 完全性ガード＋allow 10→14・M）完了・push 済 origin/main=5660f99。詳細は git log 5660f99。
- 2026-06-29: iter53（framework・破壊的コマンド警告の日本語化＋REGEX↔WARN parity ドリフトガード・M・v1.14.0 据置）完了・push 済 origin/main=69632d0。詳細は git log 69632d0。
- 2026-07-02: iter54（framework・ドッグフード前 Critical バッチ修正・L・v1.14.0→v1.15.0）完了・push 済 origin/main=9a36d72＝完全クローズ。case-insensitive FS の moat バイパス封鎖（条件付き case-fold・deny-only）＋setup.sh fail-open install 封鎖＋drill quotepath。詳細は git log 9a36d72。
- 2026-07-03: iter55 rollover＋設計着手（ドッグフード一周目 FB・許可リスト単一ソース化 scripts-manifest.tsv ほか）→ v1.16.0 完了・push 済 origin/main=9578612。詳細は git log 9578612。
- 2026-07-05: iter56（M2 FB 6件＋可視性・v1.16.0→v1.17.0）完了・push 済 origin/main=584d22c。起票 backlog=docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md。詳細は git log 584d22c。

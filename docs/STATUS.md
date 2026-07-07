---
framework: aegis
framework_version: "1.22.0"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iteration 61（framework・iter60 事故クラスの機械防御＝destructive patterns 拡張＋snapshot 退行ガード）= M。footprint は hooks/lib/patterns.sh（git checkout pathspec/stash 系パターン追加）＋hooks/lib/snapshot.sh（gate 退行検知ヘルパ）＋hooks/session-start.sh（snapshot 無条件再生成→退行検知つき条件化）＋tests/test_check_destructive_coverage.py（新パターン挙動）＋tests/test_snapshot_writers.py（退行ガード）の5ファイル＝M（2-5）。moat 該当（enforcement コード変更＝check-destructive のパターンデータ＋tamper-evidence の復旧アンカー保全）＝review+qa+security 必須・盲検2次は read-only 拘束を委譲文言に明示・deploy は M で自動 exempt。"
iteration: 61
ui_surface: false
last_updated: "2026-07-07T00:00:00Z"
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
  plan: docs/plans/2026-07-07-iter61-incident-class-machine-defense-plan.md
  spec: null
  review: docs/qa-reports/iter61-review.md
  qa: docs/qa-reports/iter61-qa.md
  security: docs/qa-reports/iter61-security.md
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
next_action: "**【iter61 docs フェーズ・全 dev ゲート approved・push 手前で停止中】** iter61/v1.22.0（iter60 事故クラスの機械防御＝全体レビュー Phase 0）完走。全 dev ゲート approved（deploy は M で自動 exempt）。実装＝patterns.sh に git checkout/restore/stash 系9パターン＋snapshot 退行ガード＋session-start 条件化。**次にやること＝(1) 実装+docs+STATUS を1コミット（未コミット）→(2) push 手前で停止しユーザー確認**（push=gh auth switch --user yuuya-miyagaki）。**その後の予定＝Phase 0 残り: iter62=委譲拘束 SoT 標準化（R1 文言層・routing.md に検証系委譲雛形＋tree 変更禁止・token-pin）／iter63=setup.sh self-heal unlock（R3）。以降 Phase 1（罠の根切り: fingerprint tree-hash 化・judge skip-and-continue・S サイズ修復・approve --ref 原子化・drill NO_RUN 拒否）**。正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §4。◆罠の正本は full-review §2 R6 分類表と LEARNINGS。要点のみ: gate 承認出力は tail／ref set→approve は連続／record-test-result は全編集後・suite 完走後・実行可能単一コマンド／M は deploy 自動 exempt。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-06"
    mode: Dev
    phase: "docs"
    note: "iter59 / v1.20.0（サブエージェント継続 SendMessage の SoT を routing.md に定義・guidance のみ）を全 dev ゲート approved まで完走（push 手前で停止）。iter58 review 2次 note1 の dangling をクローズ。routing.md に「## Subagent continuation」節（SendMessage で停止サブエージェントを同一継続・guidance 非強制・maxTurns/3-failure 有界）＋principle 1文化＋context-budgets.json budget 75→90＋test_skill_guidance_tokens.py に継続 token pin。plan(writing-plans)→grill-plan(致命ゼロ・要検討 headroom-0 文書化/単一コミット/相対緑基準 反映)→implement(TDD 単一コミット b2c2851: RED 実証→routing.md+budget+test)→grill-code(致命ゼロ)→review(1次 approve・盲検2次 approve_with_notes: pin 反転 false-PASS を fix-forward 89fb52f で解消＝`harness-enforced`→`not harness-enforced` 句)→qa(B1 SKIP＋RED-first/反転捕捉/drift 回帰の代替実証・full 1052 passed)→security(1次 approve・盲検2次 approve・findings ゼロ・moat/enforcement 不変・secrets 0・deps🟡 ack)→ship(v1.19→1.20・3箇所 bump・TO-CLIENT)→docs(LEARNINGS 2件蒸留)。実装未 push（push=gh auth switch --user yuuya-miyagaki）。**教訓核**: (1) budget raise vs 圧縮は『圧縮パスの有無』で決まる＝drift-pin 済 100% load-bearing なら追加分ちょうどの raise が正当（iter58 dedup との対比・line18/122 統合）。(2) presence-pin は否定を含む句で pin しないと意味反転(false-PASS)を見逃す＝盲検2次が別軸で捕捉（line121 の反転 facet）。"
  - date: "2026-07-06"
    mode: Dev
    phase: "docs"
    note: "iter60 / v1.21.0（budget ratchet policy 見直し＝drift 支配構造の計数除外）を全 dev ゲート approved まで完走（push 手前で停止）。context_budget.py に `<!-- aegis:budget-exclude-start/end -->` マーカー領域を計数前 strip する `_strip_excluded`/`_budget_word_count`（check/tighten/seed 3経路統一）＋routing.md roster をマーカー囲み＋budget 90→70（prose のみ計数）＋濫用ガード3重（行単位==roster／len==1／allowlist トリップワイヤ）＋CLAUDE.md terse policy。iter59 headroom-0 の根本（roster が floor 押上げ）を計数正常化で解消。plan→grill-plan(致命ゼロ・B1 は SKIP＋実 mutation demo に訂正/多領域封鎖/相対緑基準)→implement(acc2ad4)→grill-code(🟡 allowlist トリップワイヤ fix-forward c971894)→review(1次 approve・盲検2次 approve_with_notes: note1 nested コメント誤り・note2 ガード⊆弱述語→行単位==roster 強化 fix-forward f8974f1)→qa(B1 SKIP＋実 mutation M1/M2・full 1056)→security(1次 approve・盲検2次 approve_with_notes・Minor2件 residual)→ship(v1.20→1.21・3箇所 bump)→docs。実装未 push。**⚠ 運用事故＋復旧**: security 盲検2次エージェントが検証後 `git checkout docs/*` で親の未コミット gate 簿記（STATUS review/qa approved・drill）を revert→`.claude/.gate-snapshot`(docs 外)が earned 状態保持ゆえ STATUS を snapshot に一致させて復旧（f8974f1 無傷）。**教訓核**: (1) budget floor は別 invariant 支配の圧縮不能構造に食われる＝それを計数除外し budget を自由 prose に正す（headroom 水増しより筋）＋濫用ガード必須（conf8）。(2) 検証サブエージェントに git checkout/reset を許すと親の未コミット作業を破壊＝委譲は read-only 明示・tree 変更禁止／snapshot が docs 外＝STATUS 壊れても真実源（conf9）。"
  - date: "2026-07-07"
    mode: Dev
    phase: "docs"
    note: "iter61 / v1.22.0（iter60 事故クラスの機械防御＝全体レビュー Phase 0 の機械層＋復旧層）を全 dev ゲート approved まで完走（push 手前で停止）。動機正本＝docs/full-review-2026-07-06-six-dimensions-evolution.md §2 R1。実装: hooks/lib/patterns.sh に git checkout(glob/末尾/複数引数/`--`/`-f`)・restore・stash(fd redirect 含む)系9パターン追加（誤爆ゼロ＝ブランチ切替/stash pop/restore --staged は allow）＋hooks/lib/snapshot.sh に aegis_snapshot_gate_regression（earned→pending 後退検知）＋session-start.sh の snapshot 再生成を退行検知つき条件化（復旧アンカー温存＋日本語警告）。plan(Rev.5)→grill-plan(条件付きGO・致命3=確定文言B クォート不均衡で全編集 brick/redirect 誤爆/`checkout -- pathspec`・`stash -u` 見逃し→全反映)→implement(TDD RED-first 両タスク)→grill-code(fix-forward要・M-1 `checkout -f`/M-2 `restore --source` 素通り→パターン追加)→review(1次 approve・盲検2次 approve_with_notes: M-1 先頭グロブ `git checkout *` 素通り→glob prefix optional 化で fix-forward)→qa(実 B1 drill 9/9 caught・full 1061)→security(1次 approve・盲検2次 approve_with_notes: Major-1 fd redirect stash/Major-2 巨大 snapshot で session-start 119s ハング=brick 違反/Minor-3 フラグ先行 force→全て ship 前 fix-forward・residual なし・deps🟡 ack)→ship(v1.21→1.22 MINOR・3箇所 bump・TO-CLIENT)→docs(LEARNINGS 3件)。実装未 push（push=gh auth switch --user yuuya-miyagaki）。**教訓核**: (1) conf9 の委譲文言は防御3層のうち文言層のみ＝機械層(破壊検知)+復旧層(snapshot 保全)が別途要る＝『LEARNINGS に記録』と『機械で再発防止』は別物（conf9）。(2) hooks は bash 3.2 互換＝`declare -A` 不可・ループ内 sed fork は敵対入力で hook を DoS（brick 不変条件違反）＝単一 read+bash 内処理へ（conf9）。(3) grill-plan は実 grep/`bash -n` で確定文言を検証させると実装地雷(構文/誤爆/見逃し)を設計段階で潰せる（conf8）。"
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

---
framework: aegis
framework_version: "1.17.0"
project_name: "Aegis"
mode: Dev
phase: implement
task_type: framework
task_size: L
task_size_rationale: "iteration 57（framework・主 moat 交代）= L。footprint は hooks/check-control-plane.sh 削除＋hooks/lib/cp-lock.sh（verify 追加）＋hooks/session-start.sh＋新規 hooks/check-runtime-state.sh＋新規 hooks/explain-oslock-eacces.sh＋templates/hooks.template.json＋profiles＋scripts/check_framework_contract.py＋テスト置換多数（SF カタログ lock 下 EACCES 回帰・test_control_plane_* 群の 1対1 置換）＝6+ ファイル。moat の主機構交代そのもの＝全ゲート必須。"
iteration: 57
ui_surface: false
last_updated: "2026-07-05T09:20:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: docs/plans/2026-07-05-iter57-oslock-promotion-plan.md
  spec: docs/specs/2026-07-05-iter57-oslock-promotion-design.md
  review: null
  qa: null
  security: null
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
next_action: "**【iter57 brainstorm 完了・plan へ】** ◆**現在地**: rollover 済（iteration=57・全ゲート reset）→ brainstorm 完了＝**主 moat 交代の設計確定（案A 一気交代・ユーザー承認 2026-07-05）**。決定: cp-lock 昇格（fail-visible＋aegis_cp_verify 全数照合）・check-control-plane.sh 979行 退役・残余ミニフック hooks/check-runtime-state.sh 新設（runtime-state ガード＋chmod-unlock deny・scripts-manifest allowlist 継承・fail-closed）・EACCES 説明 advisory hooks/explain-oslock-eacces.sh 新設（rev.2 撤回理由②の恒久対策）・**公式サポート=macOS/Linux/WSL 限定**（Windows ネイティブは保護なしを README/manifest 明記・ユーザー決定）・check-secrets/check-gate 改修・意味ドリフト機械化・fable lineage はスコープ外。spec=docs/specs/2026-07-05-iter57-oslock-promotion-design.md・record=同 -brainstorm-record.md。rev.2（2026-06-21 撤回）との関係は record の「決定」節が正本。 ◆**次**: brainstorm 承認 → phase=plan → 実装計画（writing-plans・退役テストの 1対1 置換マッピング必須）→ grill-plan → plan 承認 → 実装。 ◆**罠（iter41-55 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-05"
    mode: Dev
    phase: "brainstorm"
    note: "iter57 着手。iter56/v1.17.0 を push（origin/main=584d22c）後に rollover 実施（iteration=57・dev ゲート全 reset via update-gate.sh・phase docs→brainstorm 後方遷移・非 requirements refs null・task framework/L 継続＝update-task.sh 不要）。テーマ＝構造リアーキ（文字列判定→FS 実解決 realpath+inode・OS-lock cp-lock 主 moat 昇格・check-control-plane 979行 退役・静的アナライザ advisory 降格）。特記: iter56 クローズ時に2セッション並走が発生（qa docs コミット 991199b が別セッション割り込み・内容同一で実害なし・第三者検収 PASS）。教訓＝引き継ぎ前の静止監視必須。次＝brainstorm 設計探索。"
  - date: "2026-07-05"
    mode: Dev
    phase: "docs"
    note: "iter56 / v1.17.0 全8ゲート approved・docs 完了（push 手前で停止）。M2 FB 6件＋可視性2件を1イテレーション一括実装（TDD）。brainstorm→plan（grill-plan 致命5件反映）→implement→grill-code（🔴1: broad-dot 境界をデリミタ列挙→否定クラス反転）→review（10並列ファインダー＋盲検2次 approve_with_notes・Major=qa ゲートで未記入 verdict 沈黙通過→1次 verdict 検証を全ゲート常時化で解消）→qa（B1 SKIP・RED-first 代替実証・full suite 1319→1322 passed）→security（盲検2次 Major=先頭ドットグロブ .en* の add-moat 純回帰を実 repo 実測で検出→グロブ節 \\.[^space]*[*?[] 追加で封鎖・commit ゲートは元々漏洩阻止・Low=verdict キー欠落の沈黙も可視化）→deploy（install 契約検証・外部デプロイなし）→ship（v1.16→1.17・LEARNINGS 蒸留2件・version 同期テストを single-owner 参照化で bump 毎手更新を撤廃）。全実装コミット未 push（push は gh auth switch 後・ユーザー確認待ち）。教訓核: moat 緩和は列挙でなく否定クラス＋グロブ展開考慮／値検査の fail-visible 保証は『どの分岐に置くか』で到達範囲が決まる（LEARNINGS conf9/conf8 追記）。"
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

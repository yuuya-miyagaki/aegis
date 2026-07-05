---
framework: aegis
framework_version: "1.16.0"
project_name: "Aegis"
mode: Dev
phase: plan
task_type: framework
task_size: L
task_size_rationale: "iteration 56（framework・ドッグフード二周目 M2 フィードバック反映）= L。footprint は hooks/check-secrets.sh（先頭ドット誤検知修正）＋scripts/build-judge-card.py（skip 経路 claims・verdict 名目差段階化）＋scripts/check_status.py または update-gate.sh（spec-delta 合格1行出力）＋templates/profiles/full.json（未配布4本追加）＋contract/install テスト＋subagent-dev / qa-verification SKILL.md＋新規テスト複数＝6+ ファイル。check-secrets の deny 判定変更＝moat 変更を含むため全ゲート必須。"
iteration: 56
ui_surface: false
last_updated: "2026-07-05T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: pending
  review: pending
  qa: pending
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: null
  spec: docs/specs/2026-07-05-iter56-m2-feedback-design.md
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
next_action: "**【iter56 着手（rollover 済・brainstorm 進行中）】** ◆**現在地**: 起票コミット 894eaff push 済（origin/main=894eaff）→ rollover 実施（iteration=56・dev ゲート全 reset・phase=brainstorm・task framework/L 継続）。テーマ＝ドッグフード二周目（M2）フィードバック反映。バックログ正本= `docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md`（根因裏取り済み）。 ◆**候補6件**: ①secrets hook 先頭ドット誤検知（check-secrets.sh:148・P1） ②drill skip 経路の claims 検査（skill×judge 契約矛盾・P1） ③verdict 名目差の 🟡 閾値（build-judge-card.py:380-385・P2） ④subagent-dev 共有テスト DB ルール（skill 追記・P2） ⑤spec-delta 🟢 通過時の1行出力（check_status.py:150・P2） ⑥retro_report.py 等4本の scaffold 同梱漏れ（full.json 8本 vs manifest 実行可12本・P1）。推奨着手順= P1（①⑥②）→ P2（③⑤④）・全件独立で1イテレーション一括。 ◆**次**: 設計書（docs/specs/）作成 → brainstorm 承認 → 実装計画（docs/plans/）→ grill-plan → plan 承認 → 実装。 ◆**iter56 後の候補**: 構造リアーキ（FS 実解決/OS-lock 昇格・check-control-plane 退役＝最有力）／ドッグフード LOG の残り（scope+acceptance 統合承認の軽量ルート・discovery exit チェックリスト・qa-browser 委譲プロンプト標準化）。 ◆**罠（iter41-55 で確立・必読）**: (a) gate 承認出力は **tail**（head は SIGPIPE で STATUS 書込み前中断）。(b) current_refs.<gate> は承認直前に設定（pending+ref は contract stale-ref FAIL）。(c) ref set→approve の間に record を挟むと stale-ref 赤＝set→approve を連続。(d) record-test-result は全コード編集後・**対象 gate ref を null にしてから**（full suite 内 contract テストの stale-ref 回避）。(e) judge `read_test_result` は **newest test-runner entry** で判定・observed は `marker_verified` 必須＝非クォート pytest を含む Bash が newest になると tests=unverified→record-test-result（src:manual）で再 record（外側 Bash は pytest 部をクォート＝strip で Q マスク）。(f) framework **焦点変更で未コミット追加実行行＋テストが hook を copy** なら本物の B1 drill 成立（混在 diff は skip）。(g) qa は **SECOND_OPINION_GATES（review/security）非対象**＝claims 付き QA レポートを ref にすれば 🟢。(h) **M は deploy 自動 exempt**（SIZE_ALLOWED_PHASES）。(i) task_type/size は update-task.sh のみ（raw Edit は tamper block）。(j) push は `gh auth switch --user yuuya-miyagaki`。(k) phase rollover(ship→brainstorm)は backward 遷移＝常時 allow。(l) B1 drill: 純コメントのみの追加ハンクは behavior-catching mutant 不能で coverage floor を割る→冗長コメントを除去し全ハンクを behavioral/text-coverable に整形（echo メッセージ変更は message を assert するテストで mutant 可）＝skip 回避。(m) full suite 実走中に suite 自身が spurious observed test-runner エントリ（vitest 等・marker false）を real evidence-log へ書く→record-test-result を suite 完走の**後**に置けば manual エントリが newest で勝つ。(n) `record-test-result.py` は command 引数を**実行して**合否記録＝実行可能な単一コマンド（`python3 -m pytest -q`・シェル機能不可）を渡す。説明文字列だと実行失敗で `red` が newest になり judge 🔴→正しいコマンドで再実行すれば green が newest で自己修復。(o) judge の 1次/2次相違は claims の**トップレベル `verdict:`（1次）**と `second_opinion.verdict`（2次）比較（build-judge-card:382）＝review/security レポートは両方明記して一致させる。docs-only review の tests=unverified🟡 は ack 可（test 実行は qa の領分）。(p) docs-only iteration の qa: `test-strength.drill` に `{\"skip\":true,\"reason\":...}`＝B1 SKIP。qa ref は claims 付き iter46-qa.md（test-strength.md は drill 再生成で claims 置けず）。(q) **size S は terminal=ship**（`SIZE_ALLOWED_PHASES[\"S\"]={brainstorm,implement,review,ship}`＝plan/qa/security/deploy/docs を含まない）。ship→docs の transition 検査は rc0 で通るが contract static 検査が『phase docs not allowed for size S』で FAIL→docs に遷移しない。S の LEARNINGS 更新・dev_ready_for_client 承認は **ship から**実施。必須ゲートは brainstorm+review のみ。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-05"
    mode: Dev
    phase: "brainstorm"
    note: "iter56 着手。起票コミット 894eaff をユーザー承認のうえ push（origin/main=894eaff）→ rollover 実施（iteration=56・dev ゲート全 reset via update-gate.sh・phase docs→brainstorm 後方遷移・非 requirements refs null・task framework/L 継続＝update-task.sh 不要）。テーマ＝M2 フィードバック反映6件（backlog 正本 docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md・根因裏取り済み）。次＝設計書作成→brainstorm 承認。"
  - date: "2026-07-05"
    mode: Dev
    phase: "docs"
    note: "ドッグフード二周目（M2・yoga-tsukinowa-lp iteration=2 キャンセル待ち）完走を受け **iter56 を起票**（起票のみ・rollover 未実施＝着手時に実施）。一次情報=DOGFOOD-M2-LOG.md／docs/LEARNINGS.md フレームワーク改善／docs/retro-m2-2026-07-05.md（いずれも yoga-tsukinowa-lp 側が正本）。**iter55 実効検証の確定: 回帰0件・チェックリスト6/6 ✅**（戦闘1〜7 すべて実使用で解消。戦闘7のみ hook ALLOW だがファイル未同梱という別レイヤ drift が露出=候補⑥）。M2 集計: 迷子0・実質ゲート戦闘0・人手介入1回・blocking 0・[P4]見逃し0・295 tests green(+103)・spec-delta 初実戦合格。候補6件を根因裏取り付きで backlog 化（docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md）: ①check-secrets.sh:148 の広範 staging 検出でドット開始トークンが末尾非アンカー前方一致し .env.example/.gitignore を誤 deny（P1・2回再現・git add -- で回避可） ②drill skip 時に current_refs.qa=test-strength.md 規約（qa-verification skill）と build-judge-card.py:374 の ref 先限定 claims 読取が衝突し claims 構造的不能=毎回 🟡 ack。罠(p) の回避運用と配布 skill が矛盾（P1・推奨=skill を罠(p) に揃える） ③judge の 1次/2次 verdict 相違が approve vs approve_with_notes の名目差で発火し3ゲート連続 ack=build-judge-card.py:380-385 の文字列不一致判定（P2・段階化） ④subagent-dev 並列規則が共有テスト DB を無想定→並行 integration の偽 fail。wave 1体運用で解消済＝skill 明文化（P2） ⑤spec-delta 合格が無言=check_status.py:150（P2・承認出力に1行追加） ⑥full.json 配布 scripts 8本 vs manifest 実行可 12本の drift。retro_report.py/check_reference_drift.py/learnings_search.py/lint_names.py 未配布・install テストは hook allow のみ検証でファイル実在を未検証（P1・full へ4本追加＋配布整合の contract 検査）。候補外の記録のみ観測（引用符内 grep 交替演算子 deny・原因不明 deny 1件・.gitignore carve-out・qa-browser 途中停止の根治未達・judge deny 文面の是正手順案内なし）も backlog に収載。規模想定 L・check-secrets 判定変更=moat 変更のため全ゲート必須。iter55 は push 済（origin/main=9578612）・本起票コミットの push のみユーザー確認待ち。"
  - date: "2026-07-03"
    mode: Dev
    phase: "brainstorm"
    note: "ドッグフード一周目完走（yoga-tsukinowa-lp・Client→Dev 全16フェーズ・全8ゲート・約1.5日・迷子0/blocking 0/[P4]見逃し0・H1/H2/H3 全実証）→ iter55 rollover 実施（iteration=55・dev ゲート全 reset・task framework/L 継続）。テーマ=フィードバック反映（LEARNINGS フレームワーク改善5件＋retro Try）。調査で許可リストドリフトの実態を確定: permissions 8本 vs hook allowlist 5本・重なり2本のみ・update-task.sh は両漏れ・/recover の status_doctor.py も対象プロジェクトで実行不可（未発火の同類バグ）。設計書 docs/specs/2026-07-03-iter55-dogfood-feedback-design.md 作成（P0 manifest 単一ソース化・P1 契約矛盾・P2 メタ文書・P3 メッセージ・P4 委譲粒度。代替案 B=permissions 参照は moat 弱体化で棄却・C=検査のみは第3ミラー教訓で棄却。update-gate.sh の ask 維持=人間承認トリップワイヤを設計判断として明記）→ brainstorm 承認申請へ"
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

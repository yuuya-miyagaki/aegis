---
framework: aegis
framework_version: "1.14.0"
project_name: "Aegis"
mode: Dev
phase: implement
task_type: framework
task_size: M
task_size_rationale: "iteration 37 = moat lifecycle re-lock（セッション中 task_type 切替での再施錠）: iteration 35 follow-up（繰延項目）。現状 lock/unlock は session-start の1箇所のみで、framework→非 framework に同一セッションで移ると CP が unlock のまま＝layer-2 が必要時に無効。アプローチ C（ユーザー承認）＝cp-lock.sh に共有 aegis_cp_apply を新設（desired 判定→sentinel 安価プローブ→不一致時のみ chmod -R）、session-start のインライン判定を置換し post-status-audit からも呼ぶ。post-status-audit が新 lock トリガになるため iter36 の Bug A（os.chmod symlink 追従）が再発しうる＝post-status-audit を起動する全テスト scaffold の symlink→copy 化＋回帰ガードを必須に含む。cp-lock.sh／session-start／post-status-audit＋テスト＋分離再監査で M 見込み（L になれば plan で更新）。security 関与（moat）につき review+qa+security 必須。"
iteration: 37
ui_surface: false
last_updated: "2026-06-22T04:10:00Z"
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
  requirements:
    - docs/full-review-2026-06-13-context-futureproof.md
  plan: docs/plans/2026-06-22-iter37-moat-relock-plan.md
  spec: docs/plans/2026-06-22-iter37-moat-relock-design.md
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
  - type: "second-opinion-v0122-r6-r9"
    scope: "v0.12.2 実装後 4 ラウンドレビュー"
    findings: "Round 6 (P1×2, P2×1: pre-compact exit 2 / minimal-project / test rc), Round 7 (P1×1, P3×1: git add 漏れ / テスト件数表記), Round 8 (P2×1, P3×1: stale last_updated / grep 自己マッチ), Round 9 (P3×2: コメント不整合)"
    resolution: "9件全反映。tier 1/2 PASS、134 tests PASS、本体と minimal-project 完全同期確認済み。"
next_action: "**【iteration 37 = moat lifecycle re-lock・brainstorm 完了／plan 着手・2026-06-22】** task_type=framework・size=M（plan で確定）。**スコープ（ユーザー承認）＝(a) セッション中 task_type 切替での再施錠のみ**（(b) クラッシュ窓 default-lock 硬化はスコープ外＝既存 session-start でほぼ自己修復）。**アプローチ C 承認済み**: cp-lock.sh に `aegis_cp_apply <root> <task_type>` を新設（desired= framework?unlock:lock → sentinel `[ -w hooks/session-start.sh ]` で現状を安価プローブ → 不一致時のみ chmod -R）。session-start:272-280 のインライン判定を同関数呼び出しに置換（挙動保存）。post-status-audit.sh から同関数を呼ぶ＝**セッション中再施錠の発火点**。**重大エッジ（必須）**: post-status-audit が新 lock トリガになるため iter36 Bug A（os.chmod が symlink 追従→実ファイル mode 化）が再発しうる＝**post-status-audit を起動する全テスト scaffold の symlink→copy 化＋回帰ガード**を含む（特に test_phase_skill_injection.py:61 が check_status.py を symlink）。default-lock: task_type 空/不読は非 framework 扱い=lock。**テスト(TDD)**: test_cp_lock_lib.py に aegis_cp_apply（framework→unlock/非→lock/既状態→no-op 冪等/空→lock）、mid-session task_type 切替で post-status-audit が再 lock する統合、full suite 後 実 check_status.py mode 644 維持の不変ガード、session-start 挙動保存。**YAGNI 除外**: PreToolUse 毎ツール再 lock／SessionEnd default-lock／settings.json lock。**ゲート**: brainstorm✓（design: docs/plans/2026-06-22-iter37-moat-relock-design.md）→plan 次。review+qa+security 必須（M は deploy skip）。設計/正典は design doc。Bash gotcha: パスはクォート・commit は -F・特殊文字は python FILE。push は yuuya-miyagaki。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-22"
    mode: Dev
    phase: "ship"
    note: "iteration 36（テスト分離バグ修正・S・framework）完了・/clear 後 /recover で復帰し再開。iter35 発見の follow-up を systematic-debugging で根本特定（当初 cp-lock 仮説は直接プローブで反証＝chmod -R は symlink 非追従・cp-lock 無罪）。**バグA（mode-flip）**: session-start scaffold が実 scripts/check_status.py を scratch に symlink→cp_lock が scratch を a-w→TemporaryDirectory cleanup の resetperms が os.chmod(0o700)（symlink 追従）で実ファイルを 700 化し fingerprint を揺らしていた。修正＝該当 2 scaffold（test_phase_skills_lib.py・test_session_start_injection.py）を shutil.copy2 化。回帰ガード test_scaffold_check_status_is_regular_file_not_symlink を **両 scaffold に対称配置**（grill-code 🟡#1 で非対称を是正）。**バグB（deploy-gate）**: test_hook_output_schema.py::test_check_deploy_gate_deny_when_gate_pending が scratch STATUS を書くが check-deploy-gate.sh は ROOT を AEGIS_ROOT_OVERRIDE|script-parent で解決（cwd も CLAUDE_PROJECT_DIR も見ない）→実 STATUS 依存で実 size=S だと ask≠deny。修正＝env={AEGIS_ROOT_OVERRIDE: scratch} 固定＋vacuous if out: 撤去で非 vacuous 化。**検証**: full suite 1027 passed/1 skip・実 check_status.py mode 644 維持（pre/post 計測）・contract PASS・record-test-result green。Bug B は RED(ask!=deny)→GREEN、回帰ガードは symlink で RED を実証。**ゲート**: review🟢 approved（judge 🟢・盲検 reviewer-testing 第2意見 approve_with_notes 一致・ref iter36-review.md）／qa/security/deploy=pending（S は size-skip exempt＝短絡）。**follow-up（別 iteration・現状無害）**: 同クラス latent symlink test_hook_output_schema.py:1429/1508（cp_lock 不発火で安全）。LEARNINGS 3件更新（os.chmod symlink 追従・hook root 解決は env 変数依存・leak 三条件）。push は yuuya-miyagaki。"
  - date: "2026-06-22"
    mode: Dev
    phase: "deploy"
    note: "iteration 35（案A immutable moat・layer-2 OS lock）全6ゲート完了: 設計を user review→初版『静的 moat 全退役・置換』を撤回し layer-2 追加（rev.2）。**設計レビュー時の暫定案は後段の grill で 3 点 reversed（最終はこちらが正典）**: (a) settings*.json を当初 LOCK 予定→**grill-plan で両方 除外**（Claude Code ハーネスが settings へ permission grant を書く・本リポは hook 登録が settings.local.json で settings.json 不在を実測）、(b) chmod-unlock guard 新規追加予定→**既存 layer-1 が既に deny 済と実測→回帰テストで固定のみ**、(c) mv gap で root 非再帰 a-w 予定→**root は lock しない**（downstream のユーザー root を縛る・mv は layer-1 deny で足る）、(d) SF を『実務クローズ』予定→**敵対 os.chmod 解錠で閉じない＝CLOSED にしない・disposition 追記のみ**、(e) chflags uchg→不採用、(f) lifecycle re-lock→繰延。実装: subagent-dev で Task0-4 per-task TDD（cp-lock.sh 単一所有/session-start fail-warn/layer-1 回帰固定/SF カタログ lock 実証/contract+版1.13.0+docs）→grill-code（🔴0🟡0・🟢 空root ガード/scripts assertion を fix-forward）→Review Army 3（testing rc=1 gap・maintainability drift・performance NFS を fix-forward／NFS は非ブロッカー follow-up）→review ゲート approve（judge 🟢・manual record で test green）。検証: full suite 1025 passed/1 skip・contract PASS・版 1.13.0 同期。コミット 1e46e4d〜244c32e（実装）。**ゲート（全6 approved）**: review🟢／qa🟡ack（skip-drill＝per-task commit 済の想定縁ケース・手動 mutation 同等で lock 破壊を実証＝chmod no-op 化で lock/SF テスト FAIL→復元で PASS）／**security🟢（短絡せず正規実施）**＝盲検 adversarial で lock 中の CP へ 9 ベクタ実走→全遮断（truncate/O_TRUNC/dd/tee/open(w)/rm/mv/install/**hardlink**＝inode 共有で mode 効く）・唯一の残余 pre-open-FD は os.chmod 解錠と同じ accepted クラス（事故ベクタでない）・secrets0・deps N/A ack・deploy-blocker なし／deploy🟢（framework＝push 締め）。grill-code🔴0🟡0・Review Army3（testing rc=1 gap/maintainability drift/performance NFS）全 fix-forward。証拠: iter35-review/security/deploy.md・test-strength.md。**発見した follow-up（別 iteration）**: テスト分離バグ＝full suite が実リポ scripts/check_status.py をモード700 化し fingerprint を揺らす（要原因特定）。STATUS rollover は gate-tamper 監査に阻まれ update-gate.sh reset 経由に是正。push は yuuya-miyagaki アカウント。"
  - date: "2026-06-21"
    mode: Dev
    phase: "review"
    note: "iteration 34（レビュー集中修正）完了・push: 全力レビュー（内製5レンズ）＋外部レビュー(E1-E5)の確定 P1/P2 を TDD で修正。A1 emit.sh 利用 6 hook の fail-closed 統一（byte-identity 12 hook・新規 test_hook_emit_failclosed が emit.sh を使う check-*.sh の fallback 必須を動的検査）/ A2 standard で moat4 hook required-registration / C1 setup baseline を実コピー path 限定（INSTALLED_PATHS funnel＋git-ignore skip）/ B1 vacuous safety test 実効化 / B3 missing-ref rc 検証 / D1 README 数字+guarantee 限定 / D2 check-secrets scope / 版 1.12.1。検証: full suite 1006 passed/1 skip・contract(full)・Tier1・各タスク RED→GREEN・盲検3エージェント（2件 infra stall だが核心の fail-closed/normal-path を実走確認・1件 complete=approve_with_notes・Critical0・scope creep0）。grill-plan 致命2（Task0 を update-gate.sh 経路へ・B4 phase↔gate 自動検査は YAGNI＋ロジック不全で Batch E 繰延）と grill-code 🟡1（C1 baseline 完全性テスト）を反映。review gate approve（judge 緑・record-test-result で緑確立）。qa/security/deploy の formal ゲートはユーザー判断で短絡し push で締め（iteration 32 同パターン）。コミット f8aff7a〜dd4c593。push は yuuya-miyagaki アカウント。残=Batch E＋戦略 PoC は別 iteration。"
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

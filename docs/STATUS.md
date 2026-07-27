---
framework: aegis
framework_version: "1.31.3"
project_name: "Aegis"
mode: Dev
phase: security
task_type: framework
task_size: M
task_size_rationale: "iter77（framework・SF-020＋SF-021 封鎖＝両 High・OPEN・silent allow の先行クローズ・**M 確定**＝brainstorm Step D 2026-07-26）。案A（High 先行）をユーザー承認: SF-020=check-destructive.sh raw 経路 grep -i 化（iter75 FF7 と同方式・CMD_LC は chmod -R 大文字リテラル破壊で不採用）＋SF-021=_STAGE_BROAD_RE (add|stage) 拡張。src 2 ファイル（check-destructive.sh/check-secrets.sh）＋tests＝M（qa/security ゲート維持・deploy skip）。attestation は iter78 へ。設計正本＝docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md。"
iteration: 77
ui_surface: false
last_updated: "2026-07-26T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: pending
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: "docs/plans/2026-07-26-iter77-moat-case-fold-stage-alias-implementation-plan.md"
  spec: "docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md"
  review: "docs/qa-reports/iter77-review.md"
  qa: "docs/qa-reports/iter77-qa.md"
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
next_action: "**【iter77 implement 完了・review 着手】** Task1 RED（赤11/緑4・a200862）→Task2 SF-020（grep -i 4サイト・298043f）→Task3 SF-021（(add|stage)＋文言汎化・1a81bd6）→Task4 統合検証（full 1411 passed/2 skipped・moat 非弱体化=1395 全 green 維持＋新規・削除0・contract/drift/doctor PASS・record green）→grill-code（🔴0・🟡2 pin fix-forward 18/18・cac9993・🟢1=rm regex 左境界なし FP 既存クラスは ship 時台帳判断）。Task4 qa agent の plan-mode 詰まりは親が record 実行を in-session 引き取り（iter76 stall 引き取りと同型）。次: review フェーズ（1次 finder=opus fan-out＋盲検2次=fable→iter77-review.md→review gate）。未 push。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-23"
    mode: Dev
    phase: "docs"
    note: "iter76 / v1.31.3（framework・evidence 整合＋locale 掃討完了＝roadmap §5 P0・**PATCH**＝既存 evidence-integrity/runtime-state moat の穴封鎖・公開契約不変）を全 dev ゲート approved まで完走（M＝deploy skip・review→ship→docs）。設計正本＝docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md。**実装（session=fable・implementer=opus per-task commit）**: W1=check-runtime-state.sh に LC_ALL=C（SF-018・2モード fail-open〔tr crash＋silent allow〕封鎖・iter73 掃討3本目）／W2b=marker.sh Stage6 green 矛盾 veto（exit0×失敗証拠→false・rc3 8ソース化・patterns.sh AEGIS_TEST_FAIL_TOKEN_REGEX 新設）／W2a+W3=judge washed-cmd transparent＋src allowlist（未知src終端🟡）。brainstorm(案A・SF-020/021 分離)→plan(grill-plan 致命3/要検討4 反映)→implement(Task1 RED 10/8 実測→Task2-5 per-task commit)→grill-code(🔴0・🟡1〔[[:space:]]契約違反→literal TAB〕＋🟢2〔W2b-6 pin〕fix-forward)→review(1次4角度 finder=opus〔仕様/敵対/テスト強度/保守性〕→**stall 多発を親が in-session 引き取り**・washed-green 10綴り〔A1-6+V1-4〕全 unverified／SF-018 byte 4綴り全 deny／record no-shell 免疫／差分歯 mutation を実走裁定・**盲検2次=fable が errors 語形の1次見落としを摘発**→実証裁定〔脅威モデル内独立到達不能〕＋tight anchor 緩和・SF-022 起票・保守性 F-1〔TAB 実バイト pin〕/F-3〔相互参照〕fix-forward)→qa(B1=since 案 DRILL BLOCKED 実証→sanctioned skip＋6軸 mutation 代替実証・E2E 3項目メイン tree PASS)→security(1次 親 in-session S1-S6〔注入/secrets/依存/ReDoS/moat174 非弱体化〕＋**盲検2次=fable が unittest unexpected successes バナー欠落〔A7〕摘発**→有界3語彙完成で封鎖〔treadmill でなくバナー網羅〕・新規脆弱性0)→ship(v1.31.2→1.31.3 PATCH・3箇所 bump・TO-CLIENT iter76 版・MANUAL/RUNBOOK/UAT=n/a〔framework 自己改善〕)→docs(LEARNINGS 既存2更新〔line148 denylist 有界完成・line156 locale 2モード〕＋新規2〔terminal↔transparent 双 pin・drill BLOCKED 実証〕＋line40 process〔stall 引き取り〕・docs-sync drift なし・昇格 該当なし)。実装コミット済（9898153〜）・未 push（gh auth switch --user yuuya-miyagaki）。**新規起票**: SF-022（marker Stage6 fail-token denylist の原理的不完全性・Low・脅威モデル内独立到達不能を実証・iter77 execution attestation で根治・iter76 は pytest errors＋unittest 有界バナー完成の net 改善）。**教訓核**: (1) denylist は「有界な構造化語彙〔unittest バナー3語〕は完成させてよい／無限空間は positive proof に委ねよ」（line148 精密化）。(2) 同一 fail-open が環境依存の2支配機構〔tr crash/silent allow〕を持つ＝入力バッテリで確認・byte-wise で両封鎖（line156）。(3) trust-scan の terminal↔transparent 逆向き2分岐は各々に非対称 mutant pin（新規 conf8）。(4) subagent の『最終報告直前 stall』は SendMessage 再開＋親 in-session 裁定で回収・finder の critical 候補は親が実走反証してから採否（line40）。**dev_ready_for_client 承認済＝iter76 完全クローズ**（全ゲート approved・未 push）。次＝push or iter77 rollover。"
  - date: "2026-07-22"
    mode: Dev
    phase: "brainstorm"
    note: "セッション復帰（session-recovery skill・status_doctor PASS・tree clean・HEAD=097c103）＋maintenance: body Session History 11→8（2026-06 期 3 件を evidence-archive へ移設・health ≤10 回復）・frontmatter session_history ≤3 維持（iter74 entry を移設）→Before brainstorm 手順→aegis-brainstorm 完走: 案A（roadmap 準拠 3 点セット・M）をユーザー承認・brainstorm-record＋design を docs/specs/2026-07-22-iter76-evidence-integrity-locale-* に保存・update-task --size M・brainstorm gate approve・phase→plan。SF-020/021 は次 iter 分離（L 化・テーマ混在回避）。次＝実装計画→grill-plan→plan gate。"
  - date: "2026-07-21"
    mode: Dev
    phase: "docs"
    note: "iter75 / v1.31.2（framework・SF-017 fix-forward「FF9」＝moat 難読化バイパスの空白注入クラス封鎖）を security 再走→道C 確定でクローズ（M＝deploy skip・review→ship→docs）。**発端**: 前回 security で 3-failure 到達（review×2＋security×1）＝docs/second-opinion.md でユーザーが道A（1回だけ根本封鎖）を選択。**FF9 実装（session=fable・実装は inline TDD）**: (1) SEC-1＝`aegis_dequote_normalize` に `${IFS...}` parameter-expansion family（`${IFS:0:1}`/`${IFS: -1}`/`${IFS/x/y}`/`${IFS#}`/`${IFS:-x}`）＋裸 `$IFS` を**単一 sed（非貪欲・O(n)）**で畳み込み（改行/タブ畳みを sed 前へ移動）。(2) Finding 1＝check-destructive の SAFE_TARGETS 早期 allow を `NORM==CMD`（難読化非実在）時のみ適用＝`rm -rf${IFS}/x` の silent 再帰削除を封鎖。RED→GREEN（tests/test_moat_quote_split.py 67 ケース）。**bash 実行シェルで runtime 実証**: IFS-family は word-split で実 `rm -rf`/`git add .env`＝実バイパス→ask 化。ANSI-C `$'\\x20'` は literal-in-word で command not found＝非 exploitable と実証し畳まず pin。**grill-code（fable）**: `${c//…}` 全置換が 5000 件で ~21s（O(n²)→hook timeout=fail-open 危険）を摘発→単一 sed で ~40ms（~500倍）に修正・scale pin 追加。**security 再走（1次 opus＋盲検2次 fable・物理隔離 e2e・read-only）**: 主張クラス（非空 `${IFS}`/quote/BS）内バイパス**0件**を両者確認・divergence なし。1次が **Root cause B**（ゼロ幅 IFS `${IFS:0:1→0}` は runtime で空展開＝glue だが静的 fold は過分割＝unsound／mixed split/glue は 2ⁿ 展開列挙が必要）を摘発、2次が param-default ネスト `${Q:-${IFS}}`（.env 実 staging e2e）・変数間接 `${!x}` を摘発。**道C 確定**: これらは全て**構造化 argv でしか根治できない SF-019 residual**（意図的難読化限定・事故経路なし・deploy blocker なし）＝主張を「非空 IFS 展開＋Finding 1」に正確化し残余を SF-019 へ統合、security=approve_with_notes でクローズ（FF10 は追わず＝事前合意の『新穴→道C・無限リトライ回避』に準拠）。full 1367 passed/2 skipped（trusted-runner 記録 green）・contract PASS。SF-017=CLOSED-in-review／SF-019 拡張／iter75-security.md 新規／LEARNINGS 3件追加／TO-CLIENT・version 3箇所 bump。**残: dev_ready_for_client はユーザー承認待ち（ship skill Red Flag＝自動承認しない）。** 次＝ユーザー承認。"
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

> 2026-04 期（v0.7.0〜v0.12.0）の 5 エントリは `docs/evidence-archive.md` に移設（2026-07-12）。2026-06 期（v1.0.0 再アーキ〜整合性監査）の 3 エントリも同所へ移設（2026-07-22・health 上限 ≤10 維持）。

- 2026-06-28: iter52（framework・permission prompt 交通整理＝read-only 完全性ガード＋allow 10→14・M）完了・push 済 origin/main=5660f99。詳細は git log 5660f99。
- 2026-06-29: iter53（framework・破壊的コマンド警告の日本語化＋REGEX↔WARN parity ドリフトガード・M・v1.14.0 据置）完了・push 済 origin/main=69632d0。詳細は git log 69632d0。
- 2026-07-02: iter54（framework・ドッグフード前 Critical バッチ修正・L・v1.14.0→v1.15.0）完了・push 済 origin/main=9a36d72＝完全クローズ。case-insensitive FS の moat バイパス封鎖（条件付き case-fold・deny-only）＋setup.sh fail-open install 封鎖＋drill quotepath。詳細は git log 9a36d72。
- 2026-07-03: iter55 rollover＋設計着手（ドッグフード一周目 FB・許可リスト単一ソース化 scripts-manifest.tsv ほか）→ v1.16.0 完了・push 済 origin/main=9578612。詳細は git log 9578612。
- 2026-07-05: iter56（M2 FB 6件＋可視性・v1.16.0→v1.17.0）完了・push 済 origin/main=584d22c。起票 backlog=docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md。詳細は git log 584d22c。
- 2026-07-06: iter60（framework・budget ratchet policy 見直し＝drift 支配構造の計数除外・M・v1.20.0→v1.21.0）完了・push 済（origin/main=60b1e22 に内包）。budget-exclude 機構＋濫用ガード3重で iter59 headroom-0 解消。⚠security 盲検2次の `git checkout` 事故→snapshot 復旧（→iter61 で機械防御化）。詳細は git log 9ae1f2f/dfc4ce1。
- 2026-07-16: iter71 / v1.30.0（marker positive proof＝SF-014 恒久策・record/drill zero-run CLOSED・marker.sh 逐語抽出）完了・push 済。詳細は git log 7aeed78。
- 2026-07-18: iter72 / v1.31.0（marker count proof＝SF-014 完結編・grep moat の locale 依存を LC_ALL=C で byte-wise 化）完了・push 済。詳細は git log。

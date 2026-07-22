---
framework: aegis
framework_version: "1.31.2"
project_name: "Aegis"
mode: Dev
phase: review
task_type: framework
task_size: M
task_size_rationale: "iter76（framework・P0＝evidence 整合＋locale 掃討完了・**M 確定**＝brainstorm Step D 2026-07-22）。案A＝roadmap 準拠 3 点セット: W1=SF-018（check-runtime-state.sh に LC_ALL=C・iter73 同型 3 本目）＋W2=washed-green 封鎖 2 軸（judge undecidable 拡張＋marker 矛盾軸）＋W3=SF-012(b) src allowlist。src 3 ファイル（check-runtime-state.sh/marker.sh/build-judge-card.py）＋tests＝M（deploy skip）。SF-020/021 は次 iter へ分離（L 化・テーマ混在回避）。設計正本＝docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md。"
iteration: 76
ui_surface: false
last_updated: "2026-07-22T00:30:00Z"
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
  plan: "docs/plans/2026-07-22-iter76-evidence-integrity-locale-implementation-plan.md"
  spec: "docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md"
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
next_action: "**【iter76 review フェーズ】** implement 完了（Task1-5＝9898153/0d73d09/d3875e6/2c47cf6/c73afcf/e115e82・grill-code 反映 dc8ffd8・full 1391 passed/2 skipped・contract PASS・record green）。実測確定: SF-018 は 2 モード fail-open（tr crash＋silent allow）・意図された flip 2 件・RED 分布 10/8。**次アクション: aegis-review-gate＝1次 4角度 finder（opus・物理隔離 clone・read-only 6拘束）→親 verify（fable）→盲検2次（fable・fresh）→docs/qa-reports/iter76-review.md（対照表・severity・claims）→update-gate review approve --ref→qa へ。** 残余方針: 単一コマンド fake binary は iter77 attestation の天井。未消化: SF-019／SF-020・SF-021（次 iter・S 消化）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-22"
    mode: Dev
    phase: "brainstorm"
    note: "セッション復帰（session-recovery skill・status_doctor PASS・tree clean・HEAD=097c103）＋maintenance: body Session History 11→8（2026-06 期 3 件を evidence-archive へ移設・health ≤10 回復）・frontmatter session_history ≤3 維持（iter74 entry を移設）→Before brainstorm 手順→aegis-brainstorm 完走: 案A（roadmap 準拠 3 点セット・M）をユーザー承認・brainstorm-record＋design を docs/specs/2026-07-22-iter76-evidence-integrity-locale-* に保存・update-task --size M・brainstorm gate approve・phase→plan。SF-020/021 は次 iter 分離（L 化・テーマ混在回避）。次＝実装計画→grill-plan→plan gate。"
  - date: "2026-07-21"
    mode: Dev
    phase: "docs"
    note: "iter75 / v1.31.2（framework・SF-017 fix-forward「FF9」＝moat 難読化バイパスの空白注入クラス封鎖）を security 再走→道C 確定でクローズ（M＝deploy skip・review→ship→docs）。**発端**: 前回 security で 3-failure 到達（review×2＋security×1）＝docs/second-opinion.md でユーザーが道A（1回だけ根本封鎖）を選択。**FF9 実装（session=fable・実装は inline TDD）**: (1) SEC-1＝`aegis_dequote_normalize` に `${IFS...}` parameter-expansion family（`${IFS:0:1}`/`${IFS: -1}`/`${IFS/x/y}`/`${IFS#}`/`${IFS:-x}`）＋裸 `$IFS` を**単一 sed（非貪欲・O(n)）**で畳み込み（改行/タブ畳みを sed 前へ移動）。(2) Finding 1＝check-destructive の SAFE_TARGETS 早期 allow を `NORM==CMD`（難読化非実在）時のみ適用＝`rm -rf${IFS}/x` の silent 再帰削除を封鎖。RED→GREEN（tests/test_moat_quote_split.py 67 ケース）。**bash 実行シェルで runtime 実証**: IFS-family は word-split で実 `rm -rf`/`git add .env`＝実バイパス→ask 化。ANSI-C `$'\\x20'` は literal-in-word で command not found＝非 exploitable と実証し畳まず pin。**grill-code（fable）**: `${c//…}` 全置換が 5000 件で ~21s（O(n²)→hook timeout=fail-open 危険）を摘発→単一 sed で ~40ms（~500倍）に修正・scale pin 追加。**security 再走（1次 opus＋盲検2次 fable・物理隔離 e2e・read-only）**: 主張クラス（非空 `${IFS}`/quote/BS）内バイパス**0件**を両者確認・divergence なし。1次が **Root cause B**（ゼロ幅 IFS `${IFS:0:1→0}` は runtime で空展開＝glue だが静的 fold は過分割＝unsound／mixed split/glue は 2ⁿ 展開列挙が必要）を摘発、2次が param-default ネスト `${Q:-${IFS}}`（.env 実 staging e2e）・変数間接 `${!x}` を摘発。**道C 確定**: これらは全て**構造化 argv でしか根治できない SF-019 residual**（意図的難読化限定・事故経路なし・deploy blocker なし）＝主張を「非空 IFS 展開＋Finding 1」に正確化し残余を SF-019 へ統合、security=approve_with_notes でクローズ（FF10 は追わず＝事前合意の『新穴→道C・無限リトライ回避』に準拠）。full 1367 passed/2 skipped（trusted-runner 記録 green）・contract PASS。SF-017=CLOSED-in-review／SF-019 拡張／iter75-security.md 新規／LEARNINGS 3件追加／TO-CLIENT・version 3箇所 bump。**残: dev_ready_for_client はユーザー承認待ち（ship skill Red Flag＝自動承認しない）。** 次＝ユーザー承認。"
  - date: "2026-07-19"
    mode: Dev
    phase: "brainstorm"
    note: "iter75 rollover（framework・P0 SF-017 MOAT-BYPASS 修正）。iter74 の二重網羅レビュー（Codex 外部隔離＋Fable 盲検2次隔離 clone・対象 77566ed）を完遂し、親が乖離/片方のみを実走裁定→突合正本 docs/full-review-2026-07-19-dual-codex-fable.md（§5 ロードマップ iter75-82）を作成、生レビュー2本を証跡保全、SF-017（Critical MOAT-BYPASS）/SF-018（Medium LOCALE-1）を起票、iter74 deliverable を commit（a51a3f9）。**二重レビューの核成果**: 決定論 moat は健在だが「生シェル文字列（moat）と生テスト出力（evidence）」の最終2入力に実走再現できる欠陥。層1の乖離が2実バグを摘発（MOAT-BYPASS=Codex のみ／LOCALE-1=Fable のみ・互いの盲点）。iter75 は SF-001 の shlex トークン化を check-destructive/secrets へ一般化する。次＝brainstorm。"
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

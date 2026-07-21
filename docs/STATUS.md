---
framework: aegis
framework_version: "1.31.2"
project_name: "Aegis"
mode: Dev
phase: docs
task_type: framework
task_size: M
task_size_rationale: "iter75（framework・P0＝SF-017 MOAT-BYPASS の修正＝check-destructive.sh/check-secrets.sh の生 regex 判定に SF-001 の shlex トークン化防御を一般化）。footprint: hooks/check-destructive.sh＋hooks/check-secrets.sh＋hooks/lib/patterns.sh（共有トークナイザ）＋tests＝M（2-5）。control-plane moat を触るため review+qa+security 必須・M のため deploy skip。正本＝docs/full-review-2026-07-19-dual-codex-fable.md §4.1／§5。size は brainstorm Step D で確定。"
iteration: 75
ui_surface: false
last_updated: "2026-07-21T08:00:00Z"
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
  plan: "docs/plans/2026-07-20-iter75-moat-quote-split-implementation-plan.md"
  spec: "docs/specs/2026-07-20-iter75-moat-quote-split-design.md"
  review: "docs/qa-reports/iter75-review.md"
  qa: "docs/qa-reports/iter75-qa.md"
  security: "docs/qa-reports/iter75-security.md"
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
next_action: "**【iter75 完全クローズ】** dev_ready_for_client=approved（ユーザー承認 2026-07-21）。全 dev ゲート完了（review/qa/security approved・deploy は M で exempt）。FF9（`${IFS...}` family 単一 sed 畳み込み＋SAFE_TARGETS NORM ガード）→ security 再走→道C 確定（残余ゼロ幅/mixed IFS・param-default・変数間接・cmdsub を SF-019 へ統合＝iter77 構造化 argv 根治）。v1.31.2・full 1372 passed/2 skipped・commit 2d04228＋gate 承認を push 済み。**次タスク着手時は state-machine の iteration rollover（brainstorm へ reset・dev ゲート pending 化・iteration++）を適用。** 未消化: SF-018（iter76 P0・runtime-state locale crash）／SF-019（iter77 構造化 argv）／SF-020・SF-021（iter76）。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-21"
    mode: Dev
    phase: "docs"
    note: "iter75 / v1.31.2（framework・SF-017 fix-forward「FF9」＝moat 難読化バイパスの空白注入クラス封鎖）を security 再走→道C 確定でクローズ（M＝deploy skip・review→ship→docs）。**発端**: 前回 security で 3-failure 到達（review×2＋security×1）＝docs/second-opinion.md でユーザーが道A（1回だけ根本封鎖）を選択。**FF9 実装（session=fable・実装は inline TDD）**: (1) SEC-1＝`aegis_dequote_normalize` に `${IFS...}` parameter-expansion family（`${IFS:0:1}`/`${IFS: -1}`/`${IFS/x/y}`/`${IFS#}`/`${IFS:-x}`）＋裸 `$IFS` を**単一 sed（非貪欲・O(n)）**で畳み込み（改行/タブ畳みを sed 前へ移動）。(2) Finding 1＝check-destructive の SAFE_TARGETS 早期 allow を `NORM==CMD`（難読化非実在）時のみ適用＝`rm -rf${IFS}/x` の silent 再帰削除を封鎖。RED→GREEN（tests/test_moat_quote_split.py 67 ケース）。**bash 実行シェルで runtime 実証**: IFS-family は word-split で実 `rm -rf`/`git add .env`＝実バイパス→ask 化。ANSI-C `$'\\x20'` は literal-in-word で command not found＝非 exploitable と実証し畳まず pin。**grill-code（fable）**: `${c//…}` 全置換が 5000 件で ~21s（O(n²)→hook timeout=fail-open 危険）を摘発→単一 sed で ~40ms（~500倍）に修正・scale pin 追加。**security 再走（1次 opus＋盲検2次 fable・物理隔離 e2e・read-only）**: 主張クラス（非空 `${IFS}`/quote/BS）内バイパス**0件**を両者確認・divergence なし。1次が **Root cause B**（ゼロ幅 IFS `${IFS:0:1→0}` は runtime で空展開＝glue だが静的 fold は過分割＝unsound／mixed split/glue は 2ⁿ 展開列挙が必要）を摘発、2次が param-default ネスト `${Q:-${IFS}}`（.env 実 staging e2e）・変数間接 `${!x}` を摘発。**道C 確定**: これらは全て**構造化 argv でしか根治できない SF-019 residual**（意図的難読化限定・事故経路なし・deploy blocker なし）＝主張を「非空 IFS 展開＋Finding 1」に正確化し残余を SF-019 へ統合、security=approve_with_notes でクローズ（FF10 は追わず＝事前合意の『新穴→道C・無限リトライ回避』に準拠）。full 1367 passed/2 skipped（trusted-runner 記録 green）・contract PASS。SF-017=CLOSED-in-review／SF-019 拡張／iter75-security.md 新規／LEARNINGS 3件追加／TO-CLIENT・version 3箇所 bump。**残: dev_ready_for_client はユーザー承認待ち（ship skill Red Flag＝自動承認しない）。** 次＝ユーザー承認。"
  - date: "2026-07-19"
    mode: Dev
    phase: "brainstorm"
    note: "iter75 rollover（framework・P0 SF-017 MOAT-BYPASS 修正）。iter74 の二重網羅レビュー（Codex 外部隔離＋Fable 盲検2次隔離 clone・対象 77566ed）を完遂し、親が乖離/片方のみを実走裁定→突合正本 docs/full-review-2026-07-19-dual-codex-fable.md（§5 ロードマップ iter75-82）を作成、生レビュー2本を証跡保全、SF-017（Critical MOAT-BYPASS）/SF-018（Medium LOCALE-1）を起票、iter74 deliverable を commit（a51a3f9）。**二重レビューの核成果**: 決定論 moat は健在だが「生シェル文字列（moat）と生テスト出力（evidence）」の最終2入力に実走再現できる欠陥。層1の乖離が2実バグを摘発（MOAT-BYPASS=Codex のみ／LOCALE-1=Fable のみ・互いの盲点）。iter75 は SF-001 の shlex トークン化を check-destructive/secrets へ一般化する。次＝brainstorm。"
  - date: "2026-07-19"
    mode: Dev
    phase: "brainstorm"
    note: "iter74 rollover＋brainstorm 記録（framework・Fable+Codex 二重網羅レビュー＋改善ロードマップ策定）。iter73 完全クローズ後に dev ゲート全 reset（sanctioned update-gate reset）・iteration=74・phase=brainstorm・非 requirements refs=null・spec=iter74 design。方法論＝2層ハイブリッド盲検（層1共通6次元 逐語同一＝moat/SF/locale-byte/test-strength/regression/North Star複雑性・層2特化＝Codex fresh-eyes配布／Fable ハーネス結合度/context経済/model-policy）。設計原理＝一致=高確度・乖離=バグの在処（iter72 F-CRIT-1 実績）。3文書を docs/specs/2026-07-19-iter74-* に保存。方法論自体を grill-plan で検証し致命5（突合ID規約/生出力必須/環境SHA固定/完了規律/fresh-first）＋要検討5（severityルーブリック/複雑性証拠形式/盲検起動条件/層2負荷/脅威モデル）を全反映。対象SHA=77566ed 固定。**未解決**: size/gate モデル（分析 iteration が review/qa/security/deploy に馴染まない＝research-iteration-type 不在・North Star 次元の指摘候補）／Codex は外部CLIでユーザー実行／Fable は hook-free clone 必須。次＝brainstorm gate。"
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

> 2026-04 期（v0.7.0〜v0.12.0）の 5 エントリは `docs/evidence-archive.md` に移設（2026-07-12・health 上限 ≤10 維持）。

- 2026-06-05: future-proof 再アーキ着手。Phase 0b 確定 + Foundation（emit.sh 単一出力源 / patterns.sh / version owner）実装。Round 1/2 セカンドオピニオン反映。183 tests PASS、main マージ（未push）。
- 2026-06-06: Phase R 再配分を連続 ship（routing 0.12.3／context 0.12.4／model-effort／name-hygiene／TDD 0.12.5／evidence 完了強制 0.12.6）。続けて Phase D（仕上げ）: migration guide(v0.12.2→v1.0.0)＋README リフレッシュ＋安定契約/SemVer 明文化＋version **1.0.0**。各タスクで brainstorm→2段グリル→実装→grill-code を完走。195 tests green・tier1/2 PASS。**再アーキ F→R→A→D 全完了＝v1.0.0「トレッドミルから降りる」看板を掲示。**
- 2026-06-07: 機能整合性監査（charter 2026-06-07）。Layer 0-4 で 7 finding（P1×1/P2×4/P3×2）全修復。核心 F6（P1）＝setup.sh が hooks/lib を配布せず install 先で moat 全死→copy_hooks 修復＋scaffold smoke の hook 実発火で install 経路を契約化。v1.3.2 patch（298 tests・tag v1.3.2）。
- 2026-06-28: iter52（framework・permission prompt 交通整理＝read-only 完全性ガード＋allow 10→14・M）完了・push 済 origin/main=5660f99。詳細は git log 5660f99。
- 2026-06-29: iter53（framework・破壊的コマンド警告の日本語化＋REGEX↔WARN parity ドリフトガード・M・v1.14.0 据置）完了・push 済 origin/main=69632d0。詳細は git log 69632d0。
- 2026-07-02: iter54（framework・ドッグフード前 Critical バッチ修正・L・v1.14.0→v1.15.0）完了・push 済 origin/main=9a36d72＝完全クローズ。case-insensitive FS の moat バイパス封鎖（条件付き case-fold・deny-only）＋setup.sh fail-open install 封鎖＋drill quotepath。詳細は git log 9a36d72。
- 2026-07-03: iter55 rollover＋設計着手（ドッグフード一周目 FB・許可リスト単一ソース化 scripts-manifest.tsv ほか）→ v1.16.0 完了・push 済 origin/main=9578612。詳細は git log 9578612。
- 2026-07-05: iter56（M2 FB 6件＋可視性・v1.16.0→v1.17.0）完了・push 済 origin/main=584d22c。起票 backlog=docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md。詳細は git log 584d22c。
- 2026-07-06: iter60（framework・budget ratchet policy 見直し＝drift 支配構造の計数除外・M・v1.20.0→v1.21.0）完了・push 済（origin/main=60b1e22 に内包）。budget-exclude 機構＋濫用ガード3重で iter59 headroom-0 解消。⚠security 盲検2次の `git checkout` 事故→snapshot 復旧（→iter61 で機械防御化）。詳細は git log 9ae1f2f/dfc4ce1。
- 2026-07-16: iter71 / v1.30.0（marker positive proof＝SF-014 恒久策・record/drill zero-run CLOSED・marker.sh 逐語抽出）完了・push 済。詳細は git log 7aeed78。
- 2026-07-18: iter72 / v1.31.0（marker count proof＝SF-014 完結編・grep moat の locale 依存を LC_ALL=C で byte-wise 化）完了・push 済。詳細は git log。

---
framework: aegis
framework_version: "1.32.0"
project_name: "Aegis"
mode: Dev
phase: ship
task_type: framework
task_size: M
task_size_rationale: "iter78（framework・pytest execution attestation＝roadmap full-review §5 行77 P0/P1・**M 確定**＝brainstorm Step D 2026-07-28）。案A（pytest プラグイン attestation）採用: argv spawn＋structured event で positive proof・src=attested のみ pytest family の decisive green・fake 出力は event 不能。src 4 ファイル（attest-test-run.py 新規／aegis_attest_plugin.py 新規／build-judge-card.py／record-test-result.py）＋tests＝M（deploy skip）。SF-014/SF-022 根治・SF-015 attested 経路解消。B1 drill 統合は roadmap 行78＝次 iter へ分離。設計正本＝docs/specs/2026-07-28-iter78-pytest-execution-attestation-design.md。"
iteration: 78
ui_surface: false
last_updated: "2026-07-28T00:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: pending
  dev_ready_for_client: pending
current_refs:
  requirements: []
  plan: "docs/plans/2026-07-28-iter78-pytest-execution-attestation-implementation-plan.md"
  spec: "docs/specs/2026-07-28-iter78-pytest-execution-attestation-design.md"
  review: "docs/qa-reports/iter78-review.md"
  qa: "docs/qa-reports/iter78-qa.md"
  security: "docs/qa-reports/iter78-security.md"
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
next_action: "**【review approved・qa 着手】** iter78 attestation。review 完了（🟢 judge card・judge 判定源 src=attested・executed=1447）: 4角度 finder（仕様準拠 approve_with_notes/敵対 バイパス0/テスト強度 M3 gap 摘発/保守性）＋盲検2次は agent ハード stall→親 in-session で独立検証回収（drift/counts 堅牢/rotation/plugin 例外 全安全・新規 finding 0）。fix-forward: judge read-time counts 検証・M3 pin・_mask_cmd 単一ソース化・SF-024 起票（in-process event 偽造＋attested 手書き＝OS-limit・drill subsume・load-bearing 不変 pin 保証）。review 正本 docs/qa-reports/iter78-review.md。次: qa-verification skill（drill 実行可否実測→BLOCKED なら sanctioned skip＋代替実証・機能対照表）→qa gate approve --ref。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-07-27"
    mode: Dev
    phase: "docs"
    note: "iter77 / v1.31.4（framework・SF-020 case-fold＋SF-021 stage エイリアス封鎖＝両 High・OPEN・silent allow の先行クローズ・**PATCH**＝既存 destructive/secrets moat の穴封鎖・公開契約不変）を全 dev 検証ゲート approved まで完走（M＝deploy skip・review→ship→docs・dev_ready_for_client はユーザー承認待ち）。設計正本＝docs/specs/2026-07-26-iter77-moat-case-fold-stage-alias-design.md。**スコープ判断**: roadmap §5 は iter77=pytest execution attestation を予定していたが、台帳の High・OPEN・silent allow（SF-020/021）が iter75→76 と2回繰延のまま残存＝重大度実態（High×2 vs attestation 根治対象 SF-022=Low緩和済）とコスト（S vs M 1-2iter）でユーザーが案A（High 先行）を承認・attestation は iter78 へ。**実装（session=fable・implementer=opus per-task commit）**: Task1 RED（15 pin 赤11/緑4・a200862）→Task2 SF-020（check-destructive.sh raw 4 サイト grep -qE→-iqE・fallback CMD_REGEX/fallback rm/本体 rm 特例/本体 CMD_REGEX・NORM 経路と対称化・SAFE_TARGETS sed は意図的非fold＝大文字 RM は safe-artifact でも ask・298043f）→Task3 SF-021（_STAGE_BROAD_RE の add→(add|stage)・update-index は broad 綴りなしゆえ非流用・文言 verb 非依存汎化・1a81bd6）→Task4 統合検証（qa agent が自ら plan-mode に入り record 書込不能→親が in-session 引き取り・full 1411 passed/2 skipped・record green・contract/drift/doctor PASS）。grill-code（fable・🔴0・🟡2 pin fix-forward＝D-6b 混在ケース/S-5b 大文字×難読化合成・cac9993）。**review（1次4角度 finder=opus〔仕様/敵対/テスト強度/保守性〕＋盲検2次=fable）**: 仕様準拠 findings0／敵対 65+入力クラス内バイパス0／テスト強度 mutation 6/6 検知者確立（fallback CMD_REGEX の検知者不在を摘発→D-7b で封鎖・ea21045）／保守性 Minor4（行番号 drift 等・修正済 d4cea18）。**盲検2次が RED カウントの記録ずれ（赤11→実測14・grill 追加3 pin 未反映）を摘発**→親が旧実装再走で 14/5 裏取り・訂正。finder は仕様準拠=一発完走／敵対=報告直前 stall→SendMessage 回収／テスト強度=SendMessage 再開後も watchdog hard-fail→**残 mutation バッテリを親 in-session 一括実走で回収**（LEARNINGS line40 3例目）。**qa**: since:ad04973 案を実走→DRILL BLOCKED 実測（coverage floor が emit_deny 文言3行＋新規テスト全体に mutant 要求＝framework 混在 diff 構造的不成立）→sanctioned skip＋差分歯 mutation 6/6・14 RED・敵対0-bypass 代替実証。**security（1次 親 in-session S1-S6＋盲検2次=fable・old-vs-new 差分照合という別手法）**: 新規脆弱性0。injection なし/ReDoS なし（最悪239-768ms）/LC_ALL=C 下 grep -i は ASCII のみ畳む（Turkish-I 異常なし）/moat 非弱体化を構造論証＋251 pin green＋2次の 134入力弱体化0 の2手法で確認/secrets 0/依存0。**ship**: v1.31.3→1.31.4・version 3箇所 bump・TO-CLIENT iter77 版・MANUAL/RUNBOOK/UAT=n/a（framework 自己改善）。**新規起票**: SF-023（>> append redirect のシステムパス取りこぼし・Low・OPEN・case 非依存の既存 regex 穴・fail-safe 側・敵対 finder 検出＋親裏取り）。SF-020/021=CLOSED-in-review。**教訓核**: (1) moat 修正が検出集合のスーパーセット操作（grep -i・(add|stage)）なら非弱体化は構造で保証＝集合論で論じ old-vs-new differential で安価に裏取り（新規 conf8）。(2) iter54 が realpath リアーキ＝別テーマに送った大文字コマンド名残余は grep -i だけで閉じられた＝過大見積りだった（line24 更新）。(3) finder の stall は同一 iter でも一発完走/報告直前 stall（SendMessage 回収）/watchdog hard-fail（親引き取り）が混在＝再開1回で駄目なら即親 in-session・機械的 mutation バッテリは最初から親が速い（line40 更新）。**dev_ready_for_client 未承認＝ユーザー申請待ち**。次＝承認 or push or iter78 rollover。"
  - date: "2026-07-23"
    mode: Dev
    phase: "docs"
    note: "iter76 / v1.31.3（framework・evidence 整合＋locale 掃討完了＝roadmap §5 P0・**PATCH**＝既存 evidence-integrity/runtime-state moat の穴封鎖・公開契約不変）を全 dev ゲート approved まで完走（M＝deploy skip・review→ship→docs）。設計正本＝docs/specs/2026-07-22-iter76-evidence-integrity-locale-design.md。**実装（session=fable・implementer=opus per-task commit）**: W1=check-runtime-state.sh に LC_ALL=C（SF-018・2モード fail-open〔tr crash＋silent allow〕封鎖・iter73 掃討3本目）／W2b=marker.sh Stage6 green 矛盾 veto（exit0×失敗証拠→false・rc3 8ソース化・patterns.sh AEGIS_TEST_FAIL_TOKEN_REGEX 新設）／W2a+W3=judge washed-cmd transparent＋src allowlist（未知src終端🟡）。brainstorm(案A・SF-020/021 分離)→plan(grill-plan 致命3/要検討4 反映)→implement(Task1 RED 10/8 実測→Task2-5 per-task commit)→grill-code(🔴0・🟡1〔[[:space:]]契約違反→literal TAB〕＋🟢2〔W2b-6 pin〕fix-forward)→review(1次4角度 finder=opus〔仕様/敵対/テスト強度/保守性〕→**stall 多発を親が in-session 引き取り**・washed-green 10綴り〔A1-6+V1-4〕全 unverified／SF-018 byte 4綴り全 deny／record no-shell 免疫／差分歯 mutation を実走裁定・**盲検2次=fable が errors 語形の1次見落としを摘発**→実証裁定〔脅威モデル内独立到達不能〕＋tight anchor 緩和・SF-022 起票・保守性 F-1〔TAB 実バイト pin〕/F-3〔相互参照〕fix-forward)→qa(B1=since 案 DRILL BLOCKED 実証→sanctioned skip＋6軸 mutation 代替実証・E2E 3項目メイン tree PASS)→security(1次 親 in-session S1-S6〔注入/secrets/依存/ReDoS/moat174 非弱体化〕＋**盲検2次=fable が unittest unexpected successes バナー欠落〔A7〕摘発**→有界3語彙完成で封鎖〔treadmill でなくバナー網羅〕・新規脆弱性0)→ship(v1.31.2→1.31.3 PATCH・3箇所 bump・TO-CLIENT iter76 版・MANUAL/RUNBOOK/UAT=n/a〔framework 自己改善〕)→docs(LEARNINGS 既存2更新〔line148 denylist 有界完成・line156 locale 2モード〕＋新規2〔terminal↔transparent 双 pin・drill BLOCKED 実証〕＋line40 process〔stall 引き取り〕・docs-sync drift なし・昇格 該当なし)。実装コミット済（9898153〜）・未 push（gh auth switch --user yuuya-miyagaki）。**新規起票**: SF-022（marker Stage6 fail-token denylist の原理的不完全性・Low・脅威モデル内独立到達不能を実証・iter77 execution attestation で根治・iter76 は pytest errors＋unittest 有界バナー完成の net 改善）。**教訓核**: (1) denylist は「有界な構造化語彙〔unittest バナー3語〕は完成させてよい／無限空間は positive proof に委ねよ」（line148 精密化）。(2) 同一 fail-open が環境依存の2支配機構〔tr crash/silent allow〕を持つ＝入力バッテリで確認・byte-wise で両封鎖（line156）。(3) trust-scan の terminal↔transparent 逆向き2分岐は各々に非対称 mutant pin（新規 conf8）。(4) subagent の『最終報告直前 stall』は SendMessage 再開＋親 in-session 裁定で回収・finder の critical 候補は親が実走反証してから採否（line40）。**dev_ready_for_client 承認済＝iter76 完全クローズ**（全ゲート approved・未 push）。次＝push or iter77 rollover。"
  - date: "2026-07-22"
    mode: Dev
    phase: "brainstorm"
    note: "セッション復帰（session-recovery skill・status_doctor PASS・tree clean・HEAD=097c103）＋maintenance: body Session History 11→8（2026-06 期 3 件を evidence-archive へ移設・health ≤10 回復）・frontmatter session_history ≤3 維持（iter74 entry を移設）→Before brainstorm 手順→aegis-brainstorm 完走: 案A（roadmap 準拠 3 点セット・M）をユーザー承認・brainstorm-record＋design を docs/specs/2026-07-22-iter76-evidence-integrity-locale-* に保存・update-task --size M・brainstorm gate approve・phase→plan。SF-020/021 は次 iter 分離（L 化・テーマ混在回避）。次＝実装計画→grill-plan→plan gate。"
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
- 2026-07-21: iter75 / v1.31.2（framework・SF-017 fix-forward「FF9」＝moat 難読化バイパスの空白注入クラス封鎖・道C＝非空 IFS 展開に主張正確化・残余 SF-019 統合）完了。詳細は git log・docs/qa-reports/iter75-security.md。

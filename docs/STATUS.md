---
framework: aegis
framework_version: "1.7.1"
project_name: "Aegis"
mode: Dev
phase: deploy
task_type: framework
task_size: L
task_size_rationale: "確定（brainstorm→writing-plans→grill-plan→TDD 実装→grill-code）: 第7回全力レビュー §1 M3『STATUS パーサ二重化』。Python 側は既に一本化済みと判明し bash のみがスコープ。frontmatter.sh に frontmatter_value/gate_value を追加し extract_value 2定義＋インライン約11箇所＋gate抽出（post-status-audit の extract_gate 含む）を集約。lib+8 hook+テスト+profiles+版数。8 commit。"
iteration: 26
ui_surface: false
last_updated: "2026-06-13T18:00:00Z"
gate_approvals:
  client_ready_for_dev: n/a
  brainstorm: approved
  plan: approved
  review: approved
  qa: approved
  security: approved
  deploy: approved
  dev_ready_for_client: pending
current_refs:
  requirements:
    - docs/full-review-2026-06-13-context-futureproof.md
  plan: docs/plans/2026-06-13-v171-status-parser-unification-implementation.md
  spec: docs/plans/2026-06-13-status-parser-unification-design.md
  review: docs/qa-reports/v162-review.md
  qa: docs/qa-reports/v162-qa.md
  security: docs/qa-reports/v162-security.md
  deploy: docs/qa-reports/v162-deploy-checklist.md
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
next_action: "iteration 26（v1.7.1 M3: STATUS パーサ bash 一本化）実装完了: frontmatter.sh に frontmatter_value（whole-file grep）/gate_value（frontmatter_section||raw_section 両対応・2スペース anchor）を追加し、散在する extract_value 2定義＋インライン scalar 約11箇所＋gate 抽出（check-gate/check-task-created＋post-status-audit の extract_gate/extract_gate_from_status）を単一所有者へ集約。Python 側は既に一本化済みのため bash のみ。挙動不変は equivalence テスト（scalar/gate/bare-snapshot 新旧一致）＋既存 tamper/snapshot テスト緑で実証。control-plane/task-completed/client-info/pre-compact に frontmatter.sh source 追加（前3者は fail-closed require）。grill-plan 致命2（gate_value の bare 非対応・post-status-audit extract_gate 取りこぼし）を着手前に反映、grill-code 🟡1（frontmatter.sh が minimal/full の required 未ピン）を fix-forward（REQUIRED_LIBS＋3 profile に追加）。版数4箇所を 1.7.1 統一。726 tests OK（711→726・新規15）/ contract 全 profile / drift / scaffold smoke / v162 18 PoC / v163 5 PoC 全 PASS。残: tag v1.7.1 付与＋origin push（ユーザ判断）。backlog: P2 volatile マニフェスト / P3 ミラー自動生成・docs archive。"
blockers: []
failure_tracking: null
session_history:
  - date: "2026-06-13"
    mode: Dev
    phase: "deploy"
    note: "iteration 26（v1.7.1 M3: STATUS パーサ bash 一本化）実装完了: 第7回全力レビュー §1 M3『STATUS パーサ二重化』。調査で Python 側（check_status.py が extract_* を所有・status_doctor が再利用）は既に一本化済みと判明し、実重複は bash のみ＝スコープを正しく絞った。frontmatter.sh に frontmatter_value（whole-file grep で STATUS.md・bare .gate-snapshot 両対応）と gate_value（frontmatter_section||raw_section fallback＋2スペース anchor）を追加。散在する extract_value 2定義（session-start/pre-compact）＋インライン scalar 約11箇所＋gate 抽出（check-gate/check-task-created）＋post-status-audit のローカル extract_gate/extract_gate_from_status 2関数を単一所有者へ集約。挙動不変は equivalence テスト（旧3段パイプ vs 新関数を scalar/gate/bare-snapshot の3軸で全キー一致）＋既存 tamper/snapshot テスト緑で実証。control-plane/task-completed/client-info/pre-compact に frontmatter.sh source 追加（前3者は fail-closed require＝コメント明記）。grill-plan が致命2件（gate_value の frontmatter_section-only では bare snapshot で silent-empty＝frontmatter_value と非対称／post-status-audit の extract_gate を取りこぼし）を指摘→着手前に gate_value を両対応化＋extract_gate も統一に含める形で反映。実装中に control-plane fixture（frontmatter.sh 非copy）の fail-closed リグレッションを検知し fixture 修正。grill-code 🟡1（frontmatter.sh が standard のみ required＝minimal/full 未ピン、複数 hook が hard-depend）を fix-forward（REQUIRED_LIBS＋minimal/full.json に追加）。版数4箇所（定数/template/example STATUS/本体 STATUS）を 1.7.1 統一。726 tests OK（711→726・新規15）/ contract 全 profile / drift / scaffold smoke / v162 18 PoC / v163 5 PoC 全 PASS。残 backlog: P2 volatile マニフェスト / P3 ミラー自動生成・docs archive。"
  - date: "2026-06-13"
    mode: Dev
    phase: "deploy"
    note: "iteration 25（v1.7.0 P2-a: AEGIS_NUDGE opt-out）実装完了: 第7回全力レビュー §2 P2-a。session-start の phase HINT 説教のみを AEGIS_NUDGE=off で抑制し、gates/skill 起動パス/blockers/failure_tracking/各 warning/unknown-phase 診断は無条件で残す（enforce outcomes, delegate paths）。スコープは常時オンの session-start のみ＝skill/agent の静的合理化テーブルは env で切れず profile 別二重化＝M1 複製税なので非ゴール。profile 連動 full=on / minimal・standard=off は setup.sh の generate_settings が settings.local.json の env に AEGIS_NUDGE=off を key-level setdefault で注入（settings env→hook 伝播は CC 公式仕様で実証・ユーザ明示値は再 install で保全）。fail-safe=小文字 off のみ off、他は on。brainstorm→writing-plans→grill-plan→TDD→grill-code を完走: grill-plan 致命1（unknown-phase 警告が HINT 変数同居で off 巻き添え→minimal/standard 既定 off で恒久診断喪失）を着手前にゲート外 [WARNING] へ分離、grill-code 🟡1（env clobber でユーザ値上書き）を key-level setdefault に修正。版数4箇所（定数/template/example STATUS/本体 STATUS）を 1.7.0 統一（v1.6.3 が docs/STATUS.md のみ bump し scaffold stamp 1.6.2 残置だった split を解消）。711 tests OK（705→711・新規6）/ contract 全 profile / drift / scaffold smoke / v162 18 PoC / v163 5 PoC 全 PASS。残 backlog: P2 volatile マニフェスト / P3 ミラー自動生成・docs archive・STATUS パーサ一本化。"
  - date: "2026-06-13"
    mode: Dev
    phase: "deploy"
    note: "iteration 24（v1.6.3 第7回全力レビュー fix-forward）実装完了: 5 軸並列レビュー（コンテキスト予算 / 機能整合 / 将来耐性 / 複雑性 / 敵対堅牢性）で moat の未カバー 3 件（R1 制御バイトで deny/block JSON 破損→fail-open・R2 STATUS/LEARNINGS の無サニタイズ注入・R3 抽出失敗時の emit_allow）を抽出。R1=emit.sh の _aegis_json_escape に C0 制御バイト空白置換（pure-bash・外部依存契約維持）。R2+C1=新 lib sanitize.sh（aegis_sanitize_field + UTF-8 安全 byte 切断 _aegis_utf8_trunc）+ session-start で blockers/learnings を untrusted エンベロープ封入・next_action はフェンス外維持・全自由文に上限。R3=check-destructive/secrets の抽出失敗分岐を raw INPUT パターン一致で emit_ask に fail-closed 化。grill-code 中に capital-R 再帰削除の既存 gap を発見し R4 として畳み込み（-[a-zA-Z]*[rR]）。P1（aegis-* description 短縮）は disable-model-invocation で system prompt 非掲載=0 トークンの YAGNI として除外。grill-plan 致命4件（UTF-8 切断割れ・next_action フェンス誤封入・P1 無価値・severity 過大）を着手前に実証反映、UTF-8 切断は bash 3.2 で 80+20 fuzz 検証。705 tests OK（683→705・新規22）/ contract 全 profile / drift / smoke / v162 18 PoC / v163 5 PoC 全 PASS。R1/R2/R3 は defense-in-depth（前提条件が gate 済 or 稀）と整理。"
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

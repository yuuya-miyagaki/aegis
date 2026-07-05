# iter57 レビューレポート（review ゲート）

- 対象: origin/main(584d22c)..HEAD（iter57・主 moat 交代・12実装コミット＋review fix-forward）
- 仕様正本: docs/specs/2026-07-05-iter57-oslock-promotion-design.md
- 実装計画: docs/plans/2026-07-05-iter57-oslock-promotion-plan.md
- 1次レビュー方式: セッション内フルコンテキスト実読（5リスク軸: moat バイパス／fail-open／
  cp_verify 正しさ／over-deny／テスト置換健全性）＋決定論検査（suite/contract/drift/budget）＋
  grill-code（実装中に完了・🔴1/🟡1 を 142733a で修正済）。盲検2次は fresh context の
  general-purpose エージェントで独立実施（下記）。

## 対照表（plan タスク × 実装）

| # | plan タスク | 実装ファイル | 実装状態 | 備考 |
|---|------------|------------|---------|------|
| 1 | aegis_cp_verify（全数照合）＋symlink 除外 | hooks/lib/cp-lock.sh・tests/test_cp_lock_verify.py | ✅ 完了 | framework/非framework で `-perm -u+w` 反転・`! -type l`・POSIX（BSD/GNU 両対応） |
| 2 | session-start の verify 配線（fail-visible） | hooks/session-start.sh・tests/test_session_start_cp_lock.py | ✅ 完了 | Windows 分岐（chmod no-op スパム防止）＋不一致で強警告＋是正手順 |
| 3 | check-runtime-state.sh 骨格＋runtime-state deny | hooks/check-runtime-state.sh・tests/test_runtime_state_hook.py | ✅ 完了 | fail-closed（抽出失敗/manifest 欠落/safety lib 欠落＝deny） |
| 4 | allowlist＋read-only＋git-stage 迂回（PORT-4〜7） | hooks/check-runtime-state.sh・tests/test_runtime_state_hook.py | ✅ 完了 | verbatim 移植＋OBS-006 (a)(b)(c) 救済（142733a 反映） |
| 5 | explain-oslock-eacces（EACCES advisory） | hooks/explain-oslock-eacces.sh・tests/test_explain_oslock_eacces.py | ✅ 完了 | **PostToolUseFailure** に精緻化（Step 5-0 envelope 実証・純 advisory・fail-open） |
| 6 | 配線・登録の交換 | templates/hooks.template.json・profiles・check_framework_contract.py・bin/setup.sh・eval_scaffold_smoke.py・.claude/settings.local.json | ✅ 完了 | live 配線も交換・退役 hook の install prune 追加 |
| 7 | 事故カタログの lock 下 EACCES 回帰 | tests/test_cp_lock_sf_catalog.py | ✅ 完了 | grill 由来バイパス形＋新規作成＋unlock 対照（弁別性実証） |
| 8 | 退役実行（削除＋テスト置換マッピング） | hooks/check-control-plane.sh 削除・test_control_plane_* 群 削除/書換 | ✅ 完了 | 1対1 置換マッピングどおり・コード/テンプレ/live 参照 0件 |
| 9 | ドキュメント・台帳更新 | docs/security-followups.md・README.md・docs/architecture-overview.md | ✅ 完了 | SF-001〜005 状態追記・Windows サポート表明・移行ノート |

## Findings（1次・検証済みのみ）

### Critical — 該当なし

grill-code 検出分（🔴 OBS-006 クォートリテラル救済の移植漏れ＝`git commit -m "…STATUS.md…"` の
誤 deny）は review 前に 142733a で修正済み（mask_quoted＋(a)(b)(c) 移植・(c) は echo/printf/git commit の
no-write allowlist 限定で writer 漏洩を防止）。

### Major — 該当なし

### Minor（本レビューで fix-forward 済み）

- **`tests/poc/v162-redteam-rerun.sh:80-97`（REDTEAM-02/02b）**（1次・2次が独立収束・confidence 9）—
  退役済み `check-control-plane.sh` を実行対象に残置。手動実行時に「No such file」で無出力→
  deny/ask マーカー不在で「SLIPPED THROUGH」と **fail-open 誤報告**（security ハーネスとして皮肉な陳腐化）。
  pytest 非収集のため自動 suite は緑。**→ 修正**: 難読化形（cmdsub/backtick/printf-v/read/eval）は
  moat 交代後 OS-lock が syscall で形非依存に阻止するため、`_assert_oslock_intact`（lock 下で実走→
  ファイル INTACT）へ書換え。ハーネス 18/18 passed で再検証（`test_cp_lock_sf_catalog.py` の bash 版）。
- **`tests/test_runtime_state_hook.py`（テストギャップ・2次検出・confidence 8）** —
  退役した `test_scripts_manifest_hook.py::TestManifestRunnable` は manifest の allow|ask **全12本**の
  実行時 ALLOW ＋ framework-only の DENY を全数列挙で回帰固定していたが、新テストは代表3本のみ。
  現行挙動は健全（over-deny なし・全数実測確認済）だが将来の per-script 誤 deny 回帰を捕捉できない。
  **→ 修正**: `_manifest_entries()` で manifest を読み、allow|ask 全数の runtime-state 文脈 ALLOW ＋
  framework-only 全数の DENY を pin する2テストを追加（GREEN 確認）。
  ※新 hook では `scripts/` は RUNTIME_STATE 外＝素の実行は early-allow のため、docs/STATUS.md を
  伴わせて manifest allowlist 経路を実際に通す点を反映。

### Divergence（2次検出・いずれも良性・記録のみ）

- **advisory の配線先**: 設計書/plan は「PostToolUse Bash」記述だが実装は `PostToolUseFailure`。
  これは plan Step 5-0 の envelope 実証を経た**正しい精緻化**（PostToolUse では失敗 stderr が
  信頼できる形で載らない・platform_manifest.py の PLATFORM_VERIFIED に 2026-07-05 記録）で劣化ではない。
  **→ 設計書の文言を PostToolUseFailure＋理由に同期（fix-forward）**。
- **plan Task 8 置換マッピングの表記**: `test_scripts_manifest_hook.py` を「書換（温存）」と記載したが
  実際は削除＋粒度低下。黙った削除ではない（plan で列挙済）が宣言と実際が食い違う。上記テストギャップ修正で解消。

### 却下・受容した候補（実証で反証／設計判断）

- 「主 moat 一本化で難読化形がすり抜ける」→ **反証**: 1次・2次とも scratch で quote-split/glob/
  case-fold/subshell cwd 移動/`python3 -c`/`find -exec`/`touch`（新規作成）/rename を lock 下実走し、
  全て EACCES で物理阻止・対象ファイル INTACT を実測（POC ハーネス 18/18・sf_catalog カタログ）。
- 「symlink 経由で lock を貫通／verify が symlink を誤検知」→ **反証**: lock/unlock/verify 全 find に
  `! -type l`・外部向き symlink 実測で貫通なし・誤検知なし（test_cp_lock_verify.py）。
- 「rename `mv hooks hooks_bak` が root 非 lock ゆえ成功しうる」→ **受容**（rev.2 既定の accepted residual）:
  hooks/ 内ファイルは INTACT・脅威モデル（事故防止）内では非問題。カタログにコメント明記。

## Evidence Checklist

- [x] diff を実読した（chat summary ではなく実ファイル: check-runtime-state.sh・cp-lock.sh・
  explain-oslock-eacces.sh・session-start.sh・関連テスト・POC）
- [x] plan/spec の受入条件と突合した（対照表・全9タスク実装済）
- [x] 未カバーのエッジケースを列挙した（却下候補として実証反証付きで記録）
- [x] 全 finding に severity と confidence を付与した

## 決定論検査

- full suite: **1045 passed / 2 skipped**（record-test-result 経由で green 記録・review ref=null 状態で実走）
- check_framework_contract: **PASS** ／ check_reference_drift: **PASS** ／ context_budget check: **exit 0** ／
  status_doctor: **PASS**

## 判定

- **PASS（1次: approve）**
- 理由: plan 全9タスク実装済・Critical/Major 0（grill-code 検出分は 142733a で修正済）・Minor 2件は
  本レビュー内で fix-forward 済（POC 陳腐化・全数列挙テスト復元）・divergence 2件は良性（うち spec 同期は
  fix-forward）・full suite 全 green・決定論検査（contract/drift/budget/status）全 PASS。
  主 moat 交代の核心（OS-lock による形非依存の物理阻止・fail-closed 残余ガード・全数照合 verify）を
  1次・2次の独立実測で確認。

## 盲検 第2意見（self-attested）

2次レビュアー（general-purpose・fresh context・1次結論非開示）による独立レビュー。
diff＋spec/plan のみを渡し、moat バイパス／fail-open／cp_verify／over-deny／テスト置換健全性の
5軸で精査し、scratch で難読化形の lock 下実走・cp_verify の half-locked 検出（BSD/GNU 両 find）も実測。
verdict= **approve_with_notes**（confidence 8）・Minor 2件（POC 陳腐化・全数列挙テストギャップ）→ **全件反映済み**。
divergence 2件（advisory の PostToolUseFailure 精緻化・plan Task8 表記）は良性と評価が一致。

```claims
verdict: approve
tests_green: true
second_opinion:
  verdict: approve_with_notes
  notes: Minor 2（POC v162 の退役 hook 参照＝fail-open 誤報告／manifest 全数列挙テストの粒度低下）＋divergence 2（advisory=PostToolUseFailure の正しい精緻化・plan Task8 表記）— 全て fix-forward 反映済み（POC を OS-lock 検証へ書換・全数列挙テスト復元・spec 同期）
  divergence_points: ["advisory は PostToolUse ではなく PostToolUseFailure に配線（Step 5-0 実証の正しい精緻化・spec 文言を同期）", "plan Task8 の test_scripts_manifest_hook.py は書換でなく削除（全数列挙テスト復元で受け皿を回復）"]
```

# iter55 レビュー — ドッグフード一周目フィードバック反映

- 対象: ドッグフード一周目（yoga-tsukinowa-lp）で実測したゲート戦闘 7 件の原因を封鎖。
  許可リストの3重管理ドリフト解消（最優先）＋契約矛盾・メタ文書ロック・stderr 誤爆・メッセージ改善・委譲粒度。
- 参照: 設計 `docs/specs/2026-07-03-iter55-dogfood-feedback-design.md`／計画 `docs/plans/2026-07-03-iter55-dogfood-feedback-plan.md`
- diff: `hooks/lib/scripts-manifest.tsv`（新規・単一正本18本4クラス）/ `hooks/check-control-plane.sh`（is_allowlisted の manifest 化・実行形プレフィックスマッチ・stderr 正規化・メッセージ）/ `hooks/check-gate.sh`（repo 直下 *.md prose allow）/ `scripts/check_framework_contract.py`（check_scripts_manifest 3方向）/ `bin/setup.sh`（.tsv 配布）/ `tests/test_permission_allowlist_install.py`（SCRIPT_CLASS を manifest 由来化）/ `.claude/skills/{client-workflow,qa-verification}/SKILL.md`（文言）/ 新規テスト5＋既存3更新＋版数 v1.16.0＋予算2件。

## 対照表（摩擦 → 実装 → 状態）

| P | ゲート戦闘 | 実装 | 状態 |
|---|-----------|------|------|
| P0 | 許可リスト二重管理ドリフト（戦闘5・7。update-task.sh 両漏れ・/recover /retro /gate が deny） | scripts-manifest.tsv 単一正本＋is_allowlisted manifest 化＋contract 3方向＋setup.sh 配布＋SCRIPT_CLASS 由来化 | 完了 |
| P1 | client-workflow と hook の translation ref タイミング矛盾（戦闘3） | SKILL.md に「承認の直前」を明文化＋旧文言除去＋テンプレ対応表（parity テスト付き） | 完了 |
| P2 | メタ文書 *.md が Client/plan 承認前に書けない（戦闘2・4） | check-gate.sh に repo 直下 *.md prose allow（control 検査の後） | 完了 |
| P3a-c | 初見殺しメッセージ（戦闘5・6・docs 摩擦） | チェーン専用文言・正規手段案内・mention ヒントの日本語化 | 完了 |
| P3d | 読み取り専用 `ls` の誤 deny（戦闘1） | 安全 stderr リダイレクト（2>/dev/null・2>&1）の正規化 | 完了 |
| P4 | qa-browser 委譲粒度（19項目1委譲で停止3回） | qa-verification SKILL.md に「5項目程度×複数委譲」ガイド | 完了 |

## moat 確認（allow 判定変更の方向性）

- **fail-closed 維持**: manifest 欠落/読取不能/壊れ行は is_allowlisted が常に rc1＝全 deny
  （test_scripts_manifest_hook の TestManifestFailClosed で pin）。
- **allow を狭める修正（grill-code 🔴）**: manifest_script_in を substring マッチから**実行形
  プレフィックスマッチ**（`python3|python|bash|sh <path>` / `<path>` / `./<path>` で開始）に変更。
  旧 substring（および置換前の旧ハードコード5本の case）は `cp evil scripts/update-gate.sh` のような
  **許可スクリプトへの書込み**を実行と誤認して allow していた pre-existing 穴。今回封鎖＝allow を狭める方向。
- **stderr 正規化は 2 形限定**: `2>/dev/null`（`2> /dev/null` 含む）と `2>&1` のみを単語境界で除去。
  `2>>`・`2>file`・`2>/dev/nullish`・fd1 の `>/dev/null`・除去後に残る `>` は fail-closed
  （TestUnsafeRedirectsStayDenied で pin）。CONTROL_PLANE 検出は生文字列のまま＝緩めるのは allow carve-out のみ。
- **repo 直下 *.md allow の位置**: CLAUDE.md（および case-fold 変種）は直前の control 検査で deny 済み・
  docs/* は先頭 allowlist で allow 済みなので、この allow が開く穴は無い。サブディレクトリ .md は対象外。
- **contract の fail-visible 化（grill-code 🟢）**: manifest 読込を read_bytes 経由に変更。read_text の
  ユニバーサル改行が `\r` を隠し、bash reader（`\r` を class 値の一部として見て silent deny）との
  非対称を生む＝CRLF 混入で「contract PASS・hook 全 deny」になり得た。生バイト経由で whitespace 厳格検査が FAIL。

## findings（severity・出所・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🔴 Critical | manifest_script_in の substring マッチが `cp evil scripts/update-gate.sh` 等の許可スクリプト**書込み**を allow（旧ハードコード5本にも存在した pre-existing 穴） | grill-code | **修正済**: 実行形プレフィックスマッチ化＋test_write_to_allowlisted_script_denied 等4本 |
| 🟡 Should | チェーン演算子なしの書込みコマンドに「単体で実行せよ」と誤診し得る | grill-code | **修正済**: プレフィックス化で manifest_script_in が false＝汎用メッセージに落ちる（test_write_to_script_gets_generic_not_standalone_hint） |
| 🟡 Should | contract の方向3が SKILL.md のみ走査＝配布補助 md（deploy/platforms.md 等）の将来穴を見逃す | grill-code | **修正済**: `.claude/skills/*/*.md` に拡大 |
| 🟢 Minor | CRLF 混入で contract PASS・hook silent deny の非対称 | grill-code | **修正済**: read_bytes 経由＋test_crlf_line_ending_fails |
| 🟢 Minor | skill 予算 2 件を明示的に微増（client-workflow 435→450・qa-verification 443→455） | 実装時 | **受容**: ドッグフード由来の load-bearing 追記（テンプレ対応表・ref タイミング契約・委譲粒度）。CJK は空白 word count で過小計上されるため可読性を犠牲にした圧縮はしない判断。tighten-only ratchet に反しないよう budgets.json を明示更新 |
| 🟢 Minor | repo 直下 *.md prose allow が symlink を解決せず、制御ファイルへの root symlink が Client/plan 承認前でも allow（iter55 前は plan-gate deny）＝防御多層の後退 | 盲検2次(security・26経路実発火) | **修正済**: is_root_prose_md が symlink（`-L`）を fast-path から除外＝gate へ落とす。symlink regression テスト追加（commit 7fa435e）。LLM 単独では悪用不能（symlink 設置が control-plane deny・Edit/Write 不可・layer-2 chmod backstop）だが事前設置＋layer-2 不在の残余を封鎖 |
| 🟢 Minor | contract 方向2 の逆方向: scripts/ にも manifest にも無い幽霊 permission allow 行が silent rot | 盲検2次(review) | **修正済**: 逆チェック追加（scripts/ を指す allow 行⊆manifest class=allow）・test_ghost_permission_entry_fails |
| 🟢 Minor | contract 方向3 が .claude/agents/*.md を走査せず、agent がスクリプト指示を書くと死角 | 盲検2次(review) | **修正済**: 走査集合に agents 追加・test_agent_ref_to_framework_only_fails。現状 agent 12 本に script 参照ゼロ（予防） |
| 🟢 Minor | 設計書・計画のマッチ規則記述が substring のまま（コードは実行形プレフィックスに修正済・doc 反映漏れ）＝正本どおり再実装すると穴再発 | 盲検2次(review) | **修正済**: design/plan の記述を実行形プレフィックスに訂正・「substring 禁止」を明記 |

## tests

- 新規5（test_scripts_manifest_hook / test_scripts_manifest_contract / test_safe_stderr_redirect /
  test_control_plane_messages / test_gate_root_prose_md）＋既存3更新（test_control_plane_allowlist /
  test_permission_allowlist_install / test_check_status ハーネス）。full suite は qa ゲートで実施。

## verdict

grill-code で 🔴 1件（許可スクリプト書込みの allow・pre-existing 穴）を自己検出し実行形プレフィックス化で解消。
🟡 2件（誤診メッセージ・補助 md 見逃し）・🟢 1件（CRLF 非対称）も同イテレーション内で解消。
盲検2次レビュー2体（review コード正確性・security 攻撃者視点26経路）はともに approve_with_notes。
security 指摘の symlink 後退・review 指摘の contract 逆方向/agents 走査/doc ドリフトを全て修正済み。
moat は fail-closed 維持・allow を狭める方向・stderr 正規化は 2 形限定・contract は fail-visible 化を確認。
**approve_with_notes**（notes は上表のとおり全て解消済み・残余は受容明記）。

```claims
verdict: approve_with_notes
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "2次(review・盲検・コード正確性)は git HEAD blob から実体化して再実測し approve_with_notes。minor 4件（doc ドリフト・contract 逆方向の幽霊 permission・agents 未走査・symlink prose）を独立に検出→本イテレーション内で全修正（幽霊 permission 逆チェック・agents 走査・doc 訂正・symlink 除外＋各 regression テスト）"
    - "2次(security・盲検・攻撃者視点)は 26 経路を実発火し approve_with_notes。stderr 正規化は生 $CMD で CONTROL_PLANE 検出後に allow 側だけ strip＝全 smuggle 形 deny を実測。substring→prefix 変更は pre-existing vuln を CLOSE と確認。唯一 minor=repo 直下 *.md prose の symlink 未解決（防御多層の後退）→ is_root_prose_md の symlink 除外で修正済"
    - "両 2次とも fail-closed・permissions への状態変異スクリプト非混入・layer-2 OS ロック backstop を独立に確認。full suite 1285 passed・contract PASS"
```

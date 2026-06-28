# iter52 セキュリティレビュー — allow-list read-only 完全性ガード＋拡張

- 参照: plan `docs/plans/2026-06-28-permission-allowlist-completeness-implementation-plan.md` / spec `docs/specs/2026-06-28-permission-allowlist-completeness-design.md`
- diff: `tests/test_permission_allowlist_install.py` / `templates/hooks.template.json`（production code 無改変・hooks 無改変）

## OWASP（該当項目のみ）

- **Injection（コマンド実行）**: 本変更の主攻撃面＝allow-list（auto-allow されたコマンドはプロンプト無しで実行）。新規 auto-allow 4 件（`check_reference_drift`/`learnings_search`/`lint_names`＋`git show`）を**全コードパスでソース監査**し、(a) ファイル書込み (b) 引数/標準入力制御コマンドの実行 (c) 破壊操作 のいずれも無いことを確認。`:*` matcher は全フラグを許可するため既定モードだけでなく全フラグを検討済。`git show` に破壊サブコマンドなし（`--output` は diff 書出しで非破壊・`-c core.pager` は `git -c …` 形が必要で `git show` prefix に不一致）。
- **Sensitive Data Exposure**: diff に secrets パターンなし（grep 済）。
- **Security Misconfiguration**: allow-list が設定そのもの。mutator/exec gadget/destructive を fail-closed で排除（下記 moat）。
- **Vulnerable Dependencies**: 依存マニフェスト無改変。新規 import は標準ライブラリ `re` のみ。dep 監査＝新規ゼロ。
- 非該当: Broken Authentication（認証フロー無関与）。

## moat 確認

- `hooks/*.sh` 無改変＝deny/ask hooks（check-destructive/check-control-plane/check-secrets/check-*-gate）全て不変。allow-list はプロンプト抑制のみで hook を bypass しない。
- `must_prompt` 分類（`record-test-result`＝`drill._execute(args.command)` exec gadget／`context_budget`＝`--tighten`/`--seed` で `scripts/context-budgets.json` を write／`update-gate.sh`/`update-task.sh`＝STATUS+snapshot write）は allow 不在を `test_non_safe_scripts_are_not_allowed` で negative assert。
- 複合コマンド（`git show … ; rm -rf`）は control-plane が never-allowlistable 扱い＋deny-hook が常時発火＝auto-allow も un-block もされない。
- 18 scripts == 18 分類（`test_every_script_is_classified`）で新規 entrypoint に分類を強制。orphan/非safe/exec-executor ガードで fail-closed。

## findings（severity・remediation）

| severity | finding | disposition |
|---|---|---|
| 🟢 Low（hardening・盲検2次 security agent） | exec-gadget ガード `test_allowed_scripts_do_not_invoke_command_executor`（`tests/...:111-119`）は `python3 scripts/*.py` allow エントリの**リテラル `._execute(`** のみ検査。将来 `subprocess`/`os.system` で arg を shell out する別 reader を safe 誤分類した場合、この特定テストは捕捉しない。 | **受容（修正不能を実証）**: agent 提案の「`subprocess` 一般を flag」は**偽陽性で不可**＝`check_status.py:922,949`/`check_framework_contract.py:893`/`retro_report.py:33`/`build-judge-card.py:75,120` は正当な `safe_auto_allow` だが **fixed-internal subprocess** を使う。静的に「固定 vs arg 制御」を判別不能。実際の制御は (1) `test_every_script_is_classified` が新規 script に人手分類を強制 (2) その時点の security レビュー (3) deny-hooks。本テストは既知 gadget の固定であり、網羅ガードではない（honest framing）。 |

## evidence checklist

- [x] secrets/credentials grep（diff の `+` 行）→ 検出なし。
- [x] 外部入力サニタイゼーション＝新規 allow スクリプトは arg を read-target/in-process 比較にのみ使用・shell out なし（ソース確認）。
- [x] dependency audit＝マニフェスト無改変・新規 dep ゼロ。
- [x] 全 finding に severity＋remediation 付与。

## deploy blocker

なし（M＝deploy size-exempt・配布物のみ）。

## verdict

新規 auto-allow は全件 read-only 実証・mutator/exec/destructive は fail-closed 排除・moat 不変・secrets/deps clean。Low は修正不能を実証した受容残渣。**approve**。

```claims
tests_pass: true
no_secrets: true
deps_clean: true
verdict: approve
second_opinion:
  verdict: approve
  divergence_points:
    - "盲検2次(security agent)は新規 allow 4 件を独自にソース全パス監査し read-only と確認＝1次と一致"
    - "2次が exec-gadget ガードの `.sh`/非`._execute` shell-out 非カバーを Low hardening として独立指摘→偽陽性で一般化不能を実証し受容（fixed-internal subprocess 正当 reader と区別不能）"
```

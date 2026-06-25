# 全力レビュー統合記録（2026-06-24）— hooks / gates / 配布経路

2 つの独立レビューを統合した punch-list。次イテレーションの着手元。

- **レビューA**: 多エージェント敵対レビュー（gate 機構 / guard hooks / installer+status 検証）＋ crown jewel（check-control-plane.sh）精読。
- **レビューB**: ユーザー自身のレビュー（`docs/hook-failure-policy.md` 起点の P1/P2 群）。

全 finding は**一次資料で裏取り済み**（file:line 添付）。深刻度は**作者自身の文書化済み脅威モデル**
（`docs/security-followups.md`：moat は「事故防止であって敵対 sandbox ではない／敵対者は os.chmod・
interpreter コードで無限に回避でき、これは受容済み」）に照らして再較正している。

## 脅威モデルの較正（最重要・読む前に）

- moat（control-plane 静的解析・SF-001〜005）の目的は**非 framework 作業中の事故的な制御プレーン書込み防止**。
  敵対的回避は SF-004（interpreter コード）等で**原理的限界として受容済み**。
- gate（review/qa/security 承認）は**人間承認が agent に偽造されない**という*より強い*性質。
  `post-status-audit.sh` の gate-tamper 検知がこれを担う。
- 従って finding は「moat の事故防止目的を破るか」「gate の偽造不能性を破るか」「単に壊れているか」で評価する。
  「敵対者なら抜ける」は SF-004 で既に受容済みなので、それ単体では深刻度を上げない。

## 深刻度マトリクス（再較正済み）

### 🔴 配布正常化（高確度・脅威モデル非依存・ただ壊れている・低リスク修正）

- **D1 / 推奨 standard profile で gate 承認が不能** — `templates/profiles/standard.json`（builder 不在）+ `scripts/check_status.py:1126-1130`（review/qa/security/deploy で `run_judge_card` 必須）+ `:945-947`（builder 不在 → return 1 fail-closed）。`build-judge-card.py` は `full.json:38` のみ。→ standard install では review/qa/security/deploy を**一切承認できない**。
  Fix: standard.json に `scripts/build-judge-card.py` を追加（または judge を full 専用機能として標準フローから外す設計判断）。

- **D2 / 推奨 standard（および実 active 設定）が完了強制を配線しない** — `standard.json` の `hooks_include` に `check-task-created.sh`/`check-task-completed.sh` が無い。`.claude/settings.local.json` にも無い（`templates/hooks.template.json:132-151` の TaskCreated/TaskCompleted のみが持つ）。`TaskCreated`/`TaskCompleted` は Claude Code 実在イベント（公式 doc 確認済）。→ CLAUDE.md「completion requires evidence」を機械強制する唯一の hook（`check-task-completed.sh`）と plan-gate hard stop（`check-task-created.sh`）が**推奨 profile で発火しない**。`check_framework_contract.py` は active settings の hook 登録を full モードで検査しないので気づけない。
  Fix: standard の hooks_include に両 Task hook を追加。contract に「active settings ⊇ template hooks（profile 応分）」検査を追加。

- **D3 / 再 install/upgrade が stale hook を残し stamp だけ前進** — `bin/setup.sh:143-147`（`install_file` は既存ファイルを `--force` 無しで SKIP）+ `:477`（version stamp を無条件更新）。→ 既存 hook スクリプトが**upgrade で一切更新されない**のに、stamp と `check_framework_contract.py:386` の standard check は「最新・PASS」と報告。セキュリティ修正が既存ユーザに届かない配布ハザード。
  Fix: バージョン管理された framework 資産（hooks/scripts）は upgrade 時に上書き、ユーザ資産は保全、という分離。最低限 stamp 前進時の content-drift 警告。

- **D4 / setup.sh が壊れた既存設定でユーザ設定を無警告全消し** — `bin/setup.sh:272-281`（`except Exception: existing = {}` で permissions/env を破棄し hooks だけ書き戻す）。`.bak` は残すが "Setup complete." と表示。Claude Code 設定は JSONC ではないので `//` 混入を非エンジニアが踏みやすく、権限喪失に気づけない。
  Fix: パース失敗を stderr で明示警告（.bak 退避＋手動復元）か abort。

### 🟡 整合性 fail-closed（clean・contained）

- **I1 / P2-B：gate改竄検知が advisory/fail-open** — `hooks/post-status-audit.sh:26-29`（他の deny hook と違い `AEGIS_SAFETY_FALLBACK` 無しで lib を直接 source）+ `docs/hook-failure-policy.md:27`（advisory・python3 不在時 allow と宣言）。gate/mode tamper 検知は bash のみで python3 不要なのに、lib source 失敗や python3 不在で監査ごとスキップ＝fail-open。
  Fix: safety fallback を追加し、gate/mode/task_type tamper 検知を fail-closed 化（python3 依存の phase-transition 検査部のみ advisory 維持）。

- **I2 / M2：完了evidence 検査が fail-open** — `scripts/check_status.py:1484-1497`。STATUS.md 不在/frontmatter 不正で `violations=[]` → exit 0（PASS）。同条件で `validate_status_file`（:1499-）は fail-closed なので非対称。
  Fix: `not status_path.exists()` か `frontmatter is None` を violation（exit 1）化。

- **I3 / P1-A + task_size：post-status-audit が task_type/task_size を監査しない** — `hooks/post-status-audit.sh:89-139` は gate/phase/mode のみ監査。`task_type` は `docs/STATUS.md` 内（`check-gate.sh:80-85` の docs/* 無条件 allow で自由 Edit 可）。`:61-64` の `aegis_cp_apply` が task_type 変更で layer-2 OS ロックを張り替えるため、`task_type: feature→framework` の単一 Edit で layer-1（check-gate）+ layer-2（OS chmod）が同時解錠。`task_size: L→S` は必須 gate（deploy 等）を skip させる。
  **較正**: これは「新規の敵対的 moat 破綻」ではない（事故では task_type を書き換えない＝moat の事故防止目的は無傷／敵対経路は SF-004 の os.chmod 解錠と同クラスで受容済み）。**正当な残課題は非対称性**：gate-advancement は tamper-evident なのに、gate 要件と moat を制御する task_type/task_size は無監査＝強い性質に側道。
  Fix: task_type/task_size を tamper 検知対象に追加（authorized-path 経由のみ変更可）。I1（fail-closed 化）が前提。

### 🟡 guard 網羅（事故防止スコープに合致）

- **G1 / M3：破壊コマンドガードの網羅不足** — `hooks/check-destructive.sh` / `hooks/lib/patterns.sh:22-34`。実測で ALLOW: `dd of=/dev/sda`、`chmod -R 777 /`、`rm -f /etc/passwd`（非再帰）、`mkfs`、`shred`、`> /etc/hosts`（truncate）。rm -r 系/git に偏り。
  Fix: `dd of=`/`chmod -R`/`mkfs`/`shred`/system-path truncate を CMD_REGEX に追加。

- **G2 / M6：`git -C <repo> commit` で staged-diff スキャンが空振り** — `hooks/check-secrets.sh:162,167`。`git diff --cached` をフック CWD で実行。`-C` 指定で CWD≠repo だと検出ゼロ。
  Fix: CMD から `-C`/`--git-dir` を抽出。

- **G3 / M9：deploy/cron gate の取りこぼし** — `hooks/check-deploy-gate.sh:62` / `hooks/check-cron-gate.sh:73`。`git push heroku main`、`V=vercel; $V deploy`、cron 内 `dd`/`chmod -R` が ALLOW。
  Fix: `patterns.sh` を single source 化して全 gate で import。

- **G4 / M5：秘密スキャンが Bash の git commit のみ** — Write/Edit の `.env` 直接生成、`curl -d @.env` 外部送信が無防備。一部 by-design（`check-secrets.sh:9-13`）。
  Fix: 漏洩主経路（exfil）のリスク受容を再評価。Edit/Write matcher にファイル名ベース ask を検討。→ **iteration 46 で再評価: by-design（accepted）。secret ゲートはファイル名・commit-stage 限定が意図（D2）。Write/Edit .env はローカル生成が正常で commit が既存 chokepoint。exfil は経路無限で regex 防御不能＝モデル外（false-assurance 回避）。`.gitignore nudge` は ROI 低で YAGNI。`docs/security-followups.md` SF-008 へクローズ。**

### 🟢 訂正・構造的留意・小

- **C1 / P2-A の訂正：MultiEdit バイパスは現行 platform で不成立** — 公式 `code.claude.com/docs/en/tools.md` 確認により **MultiEdit は廃止**（Edit に統合）。filesystem 書込み built-in tool は `Edit/Write/NotebookEdit` の 3 つで matcher が全カバー。残る構造的留意点：`hooks/lib/extract-input.sh:20` の first-path-only と、matcher がツール名ホワイトリスト列挙（`platform_manifest.py:46-50` の `KNOWN_TOOL_NAMES`＝自認の best-effort registry）である点。
  Fix: `PLATFORM_VERIFIED` 再検証時に「write 可能な全 tool を列挙 → matcher と突合」を必須項目化。→ **iteration 47 で再評価: forward-looking / 現状到達不能（複数パス built-in tool が無い・matcher 全カバー＋`stale_keys()` 再検証機構あり）。`docs/security-followups.md` SF-009 へクローズ。**
- **C2**: `bin/setup.sh:46` は `--profile=*` のみ受理。`CLAUDE.md:17` は散文で `--profile`。空白形式が「Unknown argument」で即死。
- **C3**: `bin/setup.sh:100-111` の FRAMEWORK_VERSION heredoc は `<<'PY'` 内で `$FRAMEWORK_ROOT` 非展開→必ず FileNotFoundError→"unknown"。grep フォールバック頼みの dead 第一経路。
- **C4**: gate 値パーサの bash/python 分岐（`hooks/lib/frontmatter.sh:69-73` vs `scripts/check_status.py:283`）。行コメント付き値で別結果。strict allowlist（`pending|approved|blocked|n/a`）へ統一。→ **iteration 46 で再評価: NOT-A-VULN と実証（両消費側は clean トークンでのみ allow・bypass-direction 0 行）。strict 化は tamper backstop を弱める逆効果のため不採用＝据え置き。`docs/security-followups.md` SF-007 へクローズ。**
- **C5（本レビュー中に実証）**: `hooks/check-gate.sh:153` がプロジェクト root の外の Edit/Write 対象にも plan-gate を適用する。2026-06-24 本レビュー中、グローバル auto-memory ファイル（`~/.claude/projects/.../memory/*.md`＝ROOT 外）への Edit が `[gate] Plan gate is pending` で deny された。`:80-140` の docs/ allowlist と control-file 判定はいずれも ROOT 基準なので、ROOT 外の任意パスは素通りして plan-gate 判定に落ち、Dev×plan=pending で false-positive deny になる（プロジェクトの plan gate は外部ファイルと無関係）。Fix: ROOT 外（および明確に project 外）の対象は plan-gate 前に allow へ short-circuit するか、plan-gate 判定を ROOT 内対象に限定する。クロスカッティングなツール（auto-memory 等）との摩擦点。

## root cause（2 本）

- **RC-1: STATUS.md がセキュリティ制御面と自由編集ドキュメントを兼ねる。** task_type/task_size/mode/gates は全て moat/gate を制御するのに STATUS.md は自由 Edit 可。間に立つ `post-status-audit` は (i) task_type/task_size を監査せず（I3）、(ii) 自身が fail-open（I1）。→ I1+I3+I2 で対処。**moat 本体（check-control-plane）の再設計は不要。**
- **RC-2: 配布形態（standard profile ＋ reinstall 型 upgrade）が core 保証を提供しない。** D1+D2+D3。ドッグフード full は堅いが配布形態が壊れている非対称。

## 推奨修正順

- **Batch 1（全部小さく低リスク・高確度）**: D1, D2, D3, D4, I1, I2。→ 推奨 profile が動く＋upgrade がコードを更新する＋整合性 hook が fail-closed。
- **Batch 2**: I3（task_type/size の tamper-evidence・I1 が前提）, G1（破壊ガード網羅）, G2, G3。
- **Backlog**: ~~C1〜C4, G4~~ → 整理済み（2026-06-25）。**C2/C3** = iteration 45 実装（`bin/setup.sh`）。**C4** = iteration 46 で再評価し **NOT-A-VULN（実証・bypass-direction 0 行・strict 化は tamper backstop 弱体化で逆効果）**＝`docs/security-followups.md` SF-007 へクローズ。**G4** = iteration 46 で **by-design（accepted・exfil はモデル外/futile・commit が既存 chokepoint）**＝同 SF-008 へクローズ。**C1** = iteration 47 で再評価し **forward-looking / 現状到達不能**（複数パス built-in tool が無く first-path-only は到達不能・matcher は現行 write-tool 全カバー＋`stale_keys()` 再検証機構あり）＝`docs/security-followups.md` SF-009 へクローズ。→ **backlog triaged-complete（2026-06-26）: 残る実コード修正タスクはゼロ**（実装=C2/C3/C5/G1-3/I1-3/D1-4・by-design/not-a-vuln/forward-looking=C4/G4/C1）。
- **やらないこと**: `check-control-plane.sh`（moat 1000 行）の再設計。今回の指摘はどれもそこを触らず閉じられる。

## 検証メモ

- `python3 scripts/run_eval.py --tier 0/1` は既存スイート green（レビューB 実測）。
- レビューA の 🔴 は本記録筆者が settings/template/各 hook/Python ソースで独立に裏取り。
- `TaskCreated`/`TaskCompleted`・`MultiEdit` の platform 事実は claude-code-guide 経由で公式 doc 確認。

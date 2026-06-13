# 全力レビュー（第6回・2026-06-13、対象 v1.6.1／HEAD `2ac5eb6`）

## 0. サマリ

Charter `docs/full-review-charter-2026-06-13.md` に基づき 6 軸の独立サブエージェントを並列投入。**Phase A**（v1.6.1 修正の独立再 PoC）と **Phase C1〜C5**（過去 5 回が手薄だった障害／性能／配布／競合／非エンジニア体験）から **新規所見計 51 件**（🔴 16・🟡 23・🟢 12）を抽出。結論を 4 行で述べる。

1. **v1.6.1 の C-1 / C-2 / S-3 修正は半分しか塞いでいない**。テスト緑色偽装は `pytest -k __NEVER__` で復活、変数展開系の deny は `$(echo hooks)/...` の純コマンド置換と `"${F}"` クォート付きでバイパス可。`echo` 1 行で moat の中核「テストが本当に走ったか」を破れる以上、v1.6.2 はマージ前修正。
2. **「F6 同型」の install 経路死角が 2 例再発**。lib 欠落で deny hook が空 stdout を返し Claude Code 仕様で fail-open、upgrade で旧 lib 残留しても同じ穴。`test_failure_policy.py` の網に lib 欠落系がそもそも無い＝検査表面の構造的欠陥。
3. **配布パスは upgrade と既存衝突に対し設計が無い**。`settings.local.json` 無条件上書きでユーザ設定消失、`framework_version` スタンプ無しで自己診断が版差分を見ない、python3 不在で「Setup complete.」EXIT=0 + 0 ファイル install。
4. **北極星阻害の核は「install 配布と機械検査の非対称」**。`full.json` は PRD/SCOPE/NFR を配らないのに `client_ready_for_dev` は sentinel 付きでそれらを要求。非エンジニアは「テンプレが無いのにテンプレ通り埋めろ」で確実に詰む。

総合推奨は **v1.6.2 で Critical 修正 → v1.7 で構造強化＋非エンジニア配布の対称化**。本レビューで PoC 付き REDTEAM 4 件は **マージブロッカー**。

---

## 1. 重大度マトリクス（軸横断・優先順）

### 🔴 Critical（v1.6.2 マージ前修正・PoC 添付）

| # | 場所 | 軸 | 問題 | PoC / 根拠 |
| --- | --- | --- | --- | --- |
| **K-1** | `hooks/lib/evidence.sh:_check_test_marker` × `hooks/lib/patterns.sh:AEGIS_TEST_NO_RUN_FLAG_REGEX` × `scripts/build-judge-card.py:read_test_result` | A | 強マーカー一致のみで「テスト緑」と判定。`-k <NOMATCH>` や `collected 0 items` を検出しない | `echo "===== 3 passed in 0.42s ====="; pytest -k __NEVER__` で judge カードが 🟢 承認可・「テスト: green」を刻む（REDTEAM-01）。v1.6.1 C-2 修正の主目的破綻 |
| **K-2** | `hooks/check-control-plane.sh:88-105` (`cmd_var_built_write`) | A | 純コマンド置換 / `printf -v` / `read` / `eval` 経路で書込先静的解決を素通り | `> "$(echo hooks)/lib/emit.sh"` / `printf -v D %s hooks; > $D/lib/emit.sh` がいずれも allow → 実際に `emit.sh` を truncate（REDTEAM-02） |
| **K-3** | `hooks/check-secrets.sh:149-153` | A | `git add "${F}"` クォート付き変数の `.env` ステージを検出しない（クォート無しは検出） | `F=.env; git add "${F}"` で allow（REDTEAM-03） |
| **K-4** | `hooks/check-secrets.sh:46,59` | A | `git` 自体をコマンド置換で組み立てると全 git deny regex を素通り | `$(echo git) add .env` で実際に `.env` がステージされる（REDTEAM-04） |
| **K-5** | `hooks/check-control-plane.sh` / `check-secrets.sh` / `check-destructive.sh` / `check-gate.sh` 冒頭 | C1 | `set -euo pipefail` 下で `hooks/lib/*.sh` source が失敗すると exit 1 + 空 stdout → Claude Code 仕様で **fail-open** | F-01。lib 欠落・破損で moat 全 deny hook が沈黙の fail-open。`test_failure_policy.py` は lib 欠落シナリオを 1 件も持たない |
| **K-6** | `templates/hooks.template.json` / `examples/minimal-project/.claude/settings.json` / `templates/profiles/*.json` | C1 | hook 起動の `timeout` を 1 件も宣言していない | F-02。`grep -rn timeout` で 0 件ヒット。長時間 hook が native 既定で打ち切られると K-5 と同じ exit 124/137 で fail-open |
| **K-7** | `hooks/post-status-audit.sh:121-125` / `hooks/session-start.sh:23-27` | C1 | snapshot 書き込みが 3 段 `>` `>>` `>>` で非アトミック。中断で `phase:` `mode:` 欠落 | F-03。欠落状態で phase/mode タンパー検出が `[ -n "$OLD_PHASE" ]` ガードで素通り |
| **K-8** | `bin/setup.sh:113-196` (`generate_settings`) | C3 | 既存 `.claude/settings.local.json` を無条件上書き。`.bak` 退避なし | DIST-01。ユーザの `permissions.allow` と自前 hook 行が完全消失（実走再現済み） |
| **K-9** | `bin/setup.sh:82-96` (`copy_file`) / `:217-220` (lib コピーループ) | C3 | upgrade で旧 `hooks/lib/emit.sh` が `SKIP (exists)` で残留 → 新 hook が `emit_ask: command not found` → exit 127 → fail-open | DIST-02。**F6（install 死角）と同型の 2 例目**。`/tmp/aegis-audit/upgrade` で実走再現 |
| **K-10** | `bin/setup.sh:99-110` (`parse_json_array`), `:4` (`set -euo pipefail`) | C3 | python3 不在で process substitution が `pipefail` を伝播せず、empty stdout でループ 0 回 → "Setup complete." EXIT=0 / 0 ファイル install | DIST-03。偽 python3 stub で実走再現 |
| **K-11** | `bin/setup.sh` 全体 + `scripts/status_doctor.py` + `scripts/check_framework_contract.py:18` | C3 | install 時に `framework_version` を target に書かず、doctor / contract が版差分を見ない | DIST-04。`framework_version: "1.4.0"` のまま v1.6.1 setup を当てても自己診断 PASS |
| **K-12** | `templates/profiles/full.json:36-77` ↔ `scripts/check_status.py:54-89` | C5 | `full` profile が PRD/SCOPE/NFR/ACCEPTANCE/HANDOVER-TO-DEV/HANDOVER-TO-CLIENT 等を**配らない**のに `client_ready_for_dev` は sentinel 付きでそれらを要求 | JNY-07。**北極星阻害の核心**。配布される template は `BRAINSTORM-RECORD / SPEC / TRANSLATION-MAPPING / RUNBOOK / MANUAL / UAT-RESULTS` の 6 件のみ＝機械検査と install 配布の名前空間が一致しない |
| **K-13** | `docs/onboarding/03-cheatsheet.md:64` | C5 | 🟡 ack 判断基準が 1 行（signal 説明）のみで「いつ ack せず止めるか」の例が無い | JNY-12。非エンジニアが「LLM 大丈夫って言ってるから」で機械事実を読まず ack 連打 →**aegis の最大 moat である決定論ガードを人間が無効化** |
| **K-14** | `hooks/post-bash.sh:23` + `hooks/post-bash-observe.sh:20` + `hooks/lib/fingerprint.sh:42-101` | C2 | PostToolUse Bash チェーンが **400ms/call**（fingerprint 単独 108-122ms × 毎 Bash） | PERF-1。100 Bash/session で 52s、500 Bash で 4.3 分の純粋ハーネスオーバーヘッド |
| **K-15** | `tests/test_update_gate_lock.py:144-228` | C2 | C-7 とは独立の sleep ロック層 8 本が **88s/138s ＝ 64%** を占有 | PERF-2。3 年後の test 数線形成長と相まって CI feedback loop が崩壊 |
| **K-16** | `bin/setup.sh:282` 出力末尾 + `README.md:1-25` | C5 | setup 完走後の「次に何を打つか」と README 最初の 25 行に非エンジニア向け導線無し | JNY-01 / JNY-04。「Setup complete.」で止まる素人の離脱点。README は `thin working context` `Policy as Code` `pull-based document loading` が説明なし連発 |

### 🟡 Should fix（v1.6.x〜v1.7 で順次・PoC または明確な根拠付き）

| # | 場所 | 軸 | 問題 | 修正方針 |
| --- | --- | --- | --- | --- |
| S-1 | `templates/profiles/{standard,minimal,full}.json` の `required` | A | install profile の `required` に `hooks/lib/secrets-patterns.sh` `phase-skills.sh` が無く、削除されても contract PASS | REDTEAM-05 = **F6 同型 3 例目**。required リストに追加 |
| S-2 | `scripts/check_status.py:66-89` | A | 6 成果物の sentinel + 250 バイトを `x` 連打で満たせる | REDTEAM-06。各テンプレ固有の `## 見出し` を 2-3 個マッチ要求、または sentinel 後の非空白本文 N バイト要求 |
| S-3 | `hooks/lib/emit.sh:56-59` `emit_context` | C1 | additionalContext の長さ上限が無い。blockers 巨大文字列で 100KB 注入可 | F-04。`emit_context` で 4KB 超を `...[truncated]` 切り捨て |
| S-4 | `scripts/update-gate.sh:89,160` | C1 | EXIT trap のみで SIGINT/SIGTERM 未捕捉。2 分間の孤立 lock dir が新規 update を全 block | F-05。`trap '...' EXIT TERM INT HUP` |
| S-5 | `hooks/check-task-completed.sh:76-79` / `check-task-created.sh` | C1 | STATUS.md 不在で即 `emit_allow` → 完了ゲートを丸ごと bypass 可 | F-06。policy 表に「state 不在」セルを追加し fail-closed |
| S-6 | `hooks/post-status-audit.sh:46-49` | C1 | snapshot 不在/0 バイトで audit 素通り → 直後の Edit→commit でタンパー永続見逃し | F-07。snapshot 不在時の再構築 or fail-closed |
| S-7 | `hooks/post-bash-observe.sh:13` | C1 | advisory hook なのに `evidence.sh` 欠落で exit 1（policy 「fail-open」宣言違反） | F-09。`source ... \|\| { emit_allow; exit 0; }` |
| S-8 | `tests/test_update_gate_lock.py` | C2 | `os.kill(pid, 0)` 確認窓を 10s 実時間で待機している（88s 累積の主因） | PERF-2。monkeypatched poller / injected clock で 0.5s 化、`sleep 10` → `sleep 0.5` |
| S-9 | `pytest.ini` / `pyproject.toml` 不在 | C2 | parallelize 戦略未定、testpaths/markers 未整理 | pytest-xdist 導入＋marker 整理。138s → 期待 40s |
| S-10 | `docs/qa-reports/`（rotation 不在） | C2 | iter ごとに 4 ファイル × 17KB 機械的増。3 年で +600 files / +2.2MB | PERF-4。SemVer 連動アーカイブ or per-iter ディレクトリ化 |
| S-11 | `bin/setup.sh:82-96` `--force` 分岐 | C3 | `.bak` 退避ゼロでユーザ作業を一撃で失う | DIST-09。`cp "$dst" "$dst.bak.$(date +%s)"` を先行 |
| S-12 | `examples/minimal-project/README.md`（バナー不在） | C3 | starter として `cp -r` できてしまうが、STATUS は完了済み状態。混乱の入口 | DIST-06。`<!-- FIXTURE: do not copy as starter -->` バナー＋README 警告 |
| S-13 | `examples/minimal-project/.claude/settings.json` ↔ setup.sh の `settings.local.json` | C3 | example は `settings.json` を出荷、setup.sh は `local.json` を生成→二重定義で同 hook 2 回発火可 | DIST-07。一方に統一 |
| S-14 | `bin/setup.sh` 全体 | C3 | 旧 profile の hook を削除しないまま新 profile install＝orphan 残留 | DIST-08。`templates/profiles/_retired.json` で差分検出 |
| S-15 | `scripts/aegis-doctor.py` または `bin/aegis-doctor` 不在 | C3 | README/MEMORY が示唆するが実体無し。doctor/contract/drift/scaffold-smoke が散在 | DIST-05。4 スクリプトを集約する thin wrapper を新設 |
| S-16 | `templates/CLIENT-CONTEXT.template.md:9-35` | C5 | 全行が `<記入>` のみ。「ドメインって業界？技術？」「予算レンジって万円？」で詰まる | JNY-08。`<記入>` の後ろに 1 行例（「例：会議室予約システム」） |
| S-17 | `scripts/check_status.py:942-947` の deny メッセージ | C5 | 不足ファイル列挙のみ、テンプレ場所が出ない | JNY-06。deny 出力に `→ templates/PRD.template.md をコピー` |
| S-18 | `.claude/commands/status.md` | C5 | 出力フォーマットを LLM 整形依存にしている＝セッションごとに揺れる | JNY-10。雛形を明示 |
| S-19 | `scripts/build-judge-card.py` の「あなたが取るアクション」セクション | C5 | テンプレに `（LLM が平易日本語で記述）` のプレースホルダが残り、LLM が埋め忘れた fallback 無し | JNY-11。signal→action マッピングを最低限埋め込む |
| S-20 | `.claude/skills/subagent-dev/SKILL.md` | C4 | superpowers `subagent-driven-development` の **task 単位 2 段レビュー**（spec → quality）が aegis では review フェーズ単一に固まっている | COMP-01。task 単位化＋prompt テンプレ 3 本同梱 |
| S-21 | CLAUDE.md / `tdd` skill | C4 | 「動くはず」「自信ある」「今回だけ」「lint は通った」の Rationalization Prevention 表が無く、Claude 側主観発話の抑制が弱い | COMP-02。日本語禁則表を追加 |
| S-22 | `maintenance` / `deploy` skill | C4 | 長時間タスクで Claude が「I'll be notified」「後で確認」と勝手に沈黙するリスク | COMP-07。Monitor/sleep ループで張り付け規律＋禁則語 |
| S-23 | `templates/HANDOVER-TO-CLIENT.template.md` | C4 | 数値表（変更前/後/Δ）と禁則語（「包括的」「堅牢な」「〜できるようになりました」）が無い | COMP-04。voice rule 明文化 |

### 🟢 Nice to have（v1.7+）

- F-10: judge card cat 出力に長さ cap（端末スクロールバッファ汚染防止）
- F-11: minimal profile に `session-recovery` skill を昇格 or inline fallback
- F-12: `status_doctor._parse_date` の garbage 日付を WARNING 表面化
- PERF-3: PreToolUse hook 5 本を 1 本の dispatcher に統合（195ms → ~50ms）
- PERF-5: `check_reference_drift.py` の `rglob("*")` を拡張子限定化
- PERF-7: `docs/perf-baseline.md` で profile 別 per-call latency 表
- DIST-10: profile downgrade 時の orphan ファイル clean-up（`scripts/aegis-prune.py` 分離）
- DIST-11: `docs/decisions/` の用途を `DECISION.template.md.example` で示す
- DIST-12: `--target` が framework_root と同一なら abort
- JNY-09: `templates/TRANSLATION-MAPPING.template.md` と `docs/translation/mapping.md` の二重供給整理
- JNY-13: SECOND-OPINION.template.md を full profile に追加＋cheatsheet 記述
- JNY-14: cheatsheet に「運用者は RUNBOOK.md だけ読めばよい / skill は触らない」1 行
- COMP-09: planner agent / `PLAN.template.md` に「Forbidden Placeholders」表（TBD/TODO/あとで/タスク N と同様）
- COMP-15: `scripts/skill-health.py`（trigger description 長 / `disable-model-invocation` 整合 / SKILL.md H2 存在）
- COMP-16: README に「Composite Skill Pattern」セクション新設（公式 skill を Step 0 で呼び aegis 契約を被せる独自設計のアピール）

---

## 2. 横断テーマ

### T1. 「fail-closed 一律倒し」が未完了

K-2 / K-4 / K-5 / K-6 / S-1 / S-5 / S-6 / S-7 すべてが **「静的に解決不能 = ALLOW」型** の構造的脆弱性に属する。第5回 T3「fast-path / fallback が deny 系まで侵入」の続編で、今回新規発見されたのは：

- **コマンド置換と eval/printf -v/read** はそもそも assignment 検出の枠に入らない（K-2）
- **`git` 自体をコマンド置換で組み立てる** とコマンド名 regex が全滅（K-4）
- **lib source 失敗 / hook timeout / interpreter 不在** で Claude Code 仕様の fail-open に落ちる（K-5 / K-6 / F-08）
- **STATUS.md / snapshot 不在** を「state 喪失」として扱う設計が無く allow（S-5 / S-6）

**解**: deny 系の入口に「静的解決不能なら ASK」「state 不在なら DENY」「lib/timeout/interpreter 失敗なら明示 DENY を `emit_deny` で吐いて exit 0」の 3 種類のフェイルセーフを `hooks/lib/safety.sh` に集約。policy doc（`docs/hook-failure-policy.md`）に **「lib 欠落」「timeout」「state 不在」**の 3 行を追加し、`test_failure_policy.py` でこれらの**シナリオごとの contract test** を強制する。

### T2. 「テストが本当に走った」の意味論ギャップ

K-1（test-marker forge）と K-13（🟡 ack 判断基準欠落）は **同じ問題の機械側と人間側**。

- 機械側: 出力に sentinel 文字列があるかを見ているだけで、runner が 0 件を走らせたかを構造的に検証していない
- 人間側: 🟡 ack で「LLM 大丈夫って言ってる」を根拠に通せる経路がある

両者が組み合わさると **aegis の最大 moat である「テストの結果は事実」というメッセージ**が壊れる。`echo + pytest -k __NEVER__` で機械を、`/gate approve qa` で人間を、それぞれ 1 行で通せる。

**解**:

- 機械側: `collected 0 items` / `0 tests ran` / `No tests found` / `Ran 0 tests` を構造的に検出、`-k <NOMATCH>` を no-run 扱い、`tool_response.exit_code` と「出力 1 行目以降が echo 由来か runner 由来か」のヒューリスティック
- 人間側: cheatsheet に「🟡 のうち ack していい例／ダメな例」を 3-5 例（「テスト未記録は ack 不可」「self-attested 第2意見なし＋規模小なら ack 可」）

### T3. install 経路の死角が「同型で再発する」構造的問題

REDTEAM-05（profile required の lib 不在）／DIST-02（upgrade で旧 lib 残留）／DIST-04（version stamp 不在）はすべて **「framework repo の static check は緑だが install 先で死ぬ」** という F6 と同型の問題。F6 修正は scaffold_smoke を「hook 実発火」に拡張したが、それは新規 install の冒頭 1 回しか検査せず、**upgrade 経路と installed-then-mutated 経路を見ていない**。

**解**:

- install 時に `.claude/.aegis-install-version` を書く（version stamp）
- `bin/aegis-doctor` を新設し、(a) version mismatch (b) `hooks/lib/*` SHA 整合 (c) settings 参照先存在 (d) prereq バージョン を 1 コマンドで集約
- profile `required` に `hooks/lib/*.sh` を glob 包含（手書き列挙の drift を畳む）
- `tests/test_failure_policy.py` に「lib 欠落／hook timeout／snapshot 不在」の 3 シナリオを追加

### T4. 配布の非対称（テンプレ・lib・version）

K-12（full profile が PRD/SCOPE/NFR を配らないのに client_ready_for_dev は要求）／REDTEAM-05（lib が配布 required に無い）／K-11（version stamp が install されない）はすべて **「機械検査が要求する物が配布されていない」** の同じ形。

**解**: 「Required by check_status / check_framework_contract に出てくる artifact / lib は、対応 profile の `required` リストに**必ず**含まれている」を **profile vs checker の双方向 parity test** で契約化。

### T5. PostToolUse Bash の常時 400ms はハーネスの体感品質を支配する

K-14 は「機能空間からは見えないが長セッションで分単位の損失」。短期: fingerprint プロセス内 cache（HEAD 単位で 1 回計算→再利用）。中期: PostToolUse hook を 1 本の dispatcher に集約し bash cold start を 3 回 → 1 回に。

### T6. README/setup/cheatsheet の「導線が継がない」

K-16 / K-13 / JNY-05 / JNY-06 はすべて **「次に何をすればいいか」が継がれていない**。第5回 T4「正面玄関が北極星と乖離」の続編で、今回は **モジュール内部の継ぎ目**（setup 出力末尾、deny メッセージ、judge card、cheatsheet）が空白という形で顕在化。**「最後の 1 行で次の一手を示す」を全 user-facing 出力の契約**として CLAUDE.md / hook-failure-policy に明文化する。

---

## 3. 優先順位付き提案バックログ（v1.6.2 / v1.7）

### v1.6.2（マージ前必須・**1 週間以内**）

| 順 | ID | 工数感 | 期待効果 |
| --- | --- | --- | --- |
| 1 | K-1 / T2 機械側 | 中 | judge 緑色偽装の最大経路を封鎖。`collected 0 items` 検出と `-k` 無効化判定 |
| 2 | K-2 / K-3 / K-4 / T1 cmdsub-fail-closed | 中 | 制御プレーン書込／secret stage の純コマンド置換／クォート付き変数を ASK 化 |
| 3 | K-5 / K-6 / K-7（safety.sh 集約） | 中 | lib 欠落・timeout・snapshot 中断を全 deny 系で明示 DENY emit |
| 4 | K-8 / K-9 / K-11 配布パスの破壊抑止 | 小〜中 | settings.local.json バックアップ／lib 強制上書き／version stamp |
| 5 | K-10 setup prereq 検査 | 小 | python3 / bash バージョン早期検査、`parse_json_array` 件数検査 |
| 6 | K-12 full profile に PRD/SCOPE/NFR 等追加 | 小 | 非エンジニア体験の核心ブロッカー解消 |
| 7 | K-13 cheatsheet に 🟡 ack 例 | 小 | moat 人間側の無効化経路を塞ぐ |

### v1.7（構造強化・**1 ヶ月以内**）

| 順 | ID | 工数感 | 期待効果 |
| --- | --- | --- | --- |
| 1 | T3 `bin/aegis-doctor` + version stamp + profile parity test | 中 | install 経路死角の再発系統を畳む |
| 2 | T4 profile vs checker parity test 自動化 | 中 | 「機械が要求する物は profile が配る」を契約化 |
| 3 | K-14 / K-15 PERF-1 / PERF-2 | 中 | hook 400ms → 100ms、test 138s → 40s |
| 4 | T6 「最後の 1 行に次の一手」契約 | 小 | README / setup / deny / cheatsheet の継ぎ目を埋める |
| 5 | S-20〜S-23 競合フレーム取り込み（Rationalization 表 / 長時間ジョブ規律 / HANDOVER voice rule） | 小〜中 | 公式 skill 進化に乗りつつ aegis 契約を被せる |

### v1.7+ 検討

- COMP-15 `skill-health.py`（drift scanner 拡張）
- COMP-09 plan No-Placeholder 禁則
- COMP-01 subagent 2 段レビューの task 単位化
- COMP-16 README に Composite Skill Pattern を前面化

---

## 4. aegis 独自で他フレームが真似しにくい優位点（維持事項）

1. **Hook-based Policy-as-Code moat（決定論ゲート）** — superpowers/gstack/ECC は全て「Claude が rule を読む」型。aegis の hook 17 本＋bash/python parity test＋mirror 検査は他に類例なし
2. **Client/Dev 二段モード + 6 成果物対称検査** — 非エンジニアの上流から保守までを単一 framework で貫く設計は aegis のみ
3. **Composite Skill Pattern**（公式 skill を Step 0 で呼び aegis 契約を被せる）— 公式の進化に追従しつつ自前契約を守る。「追従トレッドミルから降りる」v1.0.0 哲学の実装
4. **Bash/Python parity test + smoke fixtures + drift scanner + contract の 4 層静的検査** — install 出力にも適用（F6 教訓）
5. **3 失敗で停止 + second-opinion.md + IDE chat 誘導** — 「分からなくなったら止まり、外部レビューに渡す」が contract 化。失敗循環を機械的に断つ規律は aegis 固有

**ただし上記は README で前面化できておらず長期採用判断に効きにくい**（COMP-16）。

---

## 5. 軸別所見の出典マップ

| 所見 ID | 出自軸 | 元レポート（サブエージェント raw） |
|---------|--------|----------------------------------|
| K-1, K-2, K-3, K-4, S-1, S-2 | Phase A | REDTEAM-01〜06 |
| K-5, K-6, K-7, S-3〜S-7, F-08, F-10〜F-12 | Phase C1 | F-01〜F-12 |
| K-14, K-15, S-8, S-9, S-10, PERF-3, PERF-5, PERF-7 | Phase C2 | PERF-1〜PERF-7 |
| K-8, K-9, K-10, K-11, S-11〜S-15, DIST-10〜DIST-12 | Phase C3 | DIST-01〜DIST-12 |
| S-20, S-21, S-22, S-23, COMP-09, COMP-15, COMP-16 | Phase C4 | COMP-01〜COMP-16 |
| K-12, K-13, K-16, S-16〜S-19, JNY-09, JNY-13, JNY-14 | Phase C5 | JNY-01〜JNY-14 |

各サブエージェントの raw 所見はそれぞれの軸内で `[REDTEAM-NN]` `[F-NN]` `[PERF-N]` `[DIST-NN]` `[COMP-NN]` `[JNY-NN]` のラベルを保持しており、本統合レポートからは ID で逆引き可能。

---

## 6. 次の判断点

本レビューは所見の提示まで。次の判断ポイントは：

- **v1.6.2 を tag/push する前に Critical 7 件（K-1〜K-7 機械系 + K-8〜K-11 配布系 + K-12 K-13）を消化するか**
- **PoC を加えた `test_failure_policy.py` 拡張を v1.6.2 と同時に入れるか v1.7 に回すか**
- **`bin/aegis-doctor` 新設（T3）を v1.6.2 の延長で着手するか v1.7 charter に立てるか**

PoC は本レビューで全て構築済み（実走再現可能）。grill-code 工程に直接投入できる。

---

参照 charter: `docs/full-review-charter-2026-06-13.md`
過去レビュー: `docs/audit-report-2026-06-06.md` / `docs/functional-integrity-audit-report-2026-06-07.md` / `docs/evolution-review-2026-06-10.md` / `docs/behavioral-review-report-2026-06-12.md` / `docs/full-review-2026-06-12.md`

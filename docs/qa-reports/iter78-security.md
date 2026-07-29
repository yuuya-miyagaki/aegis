# セキュリティレポート — iter78 pytest execution attestation
<!-- 正本: security agent -->

## 対象

- 変更: 新規 scripts/attest-test-run.py（argv spawn＋イベント突合）・scripts/aegis_attest_plugin.py（イベント書出）・scripts/build-judge-card.py（src=attested 受入＋pytest-green 制限＋read-time counts 検証＋_mask_cmd）・scripts/record-test-result.py（pytest→attest 誘導）・manifest/full.json/evidence.sh コメント。
- 手法: 1次＝親 in-session S1-S6（実走反証）＋盲検2次（fable・独立）。脅威モデル＝「自分の qa gate を欺く LLM/人」。

## OWASP 該当項目（S1-S6）

### S1 Injection（command/argv）— clean
- attest-test-run.py は `subprocess.run(..., shell=False)`＝シェル非経由。ユーザーコマンドは `shlex.split`→argv 直接 spawn。シェル演算子トークン（`&& || ; | &`）は rc2 拒否・env 代入 prefix（`argv[0]` に `=`）は rc2 拒否（実走: `PYTHONPATH=/tmp/evil python3 -m pytest`→rc2）。
- `-p aegis_attest_plugin` はハードコード注入・PYTHONPATH は attestor が scripts/ を先頭前置（ユーザー非制御）。`-p ... aegis_attest_plugin` 指定/打ち消しは rc2。
- **プラグイン shadowing（S6 併合）**: 被テスト repo が自前 `aegis_attest_plugin.py` で本物を shadow し実失敗 suite に偽 green イベント（passed＋sessionfinish 0）を吐いても → **rc2・記録なし**（実走確認）。理由: プロセスの実 exit code は **waitpid（kernel）由来**で in-process コードが偽造不能＝失敗 suite は必ず非0 exit→sessionfinish 突合不一致 or red 記録。**「本物の red は green にできない」= attestation が出力パースより強い核心**を再確認。

### S2 Sensitive Data Exposure — clean
- 新規ファイルに credential パターン 0（grep 実測）。イベントファイルは nodeid/outcome のみ・evidence-log は cmd[:500]（record と同一の pre-existing 挙動・新規暴露なし）・payload_sha はハッシュ。イベント一時ファイルは try/finally で全パス削除。

### S3 Vulnerable Dependencies — clean
- 新規/変更スクリプトの import は python3 stdlib のみ（future/pathlib/hashlib/importlib/json/os/shlex/subprocess/sys/tempfile/time）。外部依存 0。

### S4 Security Misconfiguration（ReDoS 含む）— clean
- 新規に untrusted 入力へ適用する正規表現なし。判定に使う `AEGIS_TEST_IS_PYTEST_REGEX` は patterns.sh 既存・timing 線形（n=20000 paren-flood で 2.1ms）＝catastrophic backtracking なし。かつ入力は `cmd[:500]` に有界＝二重に安全。`_mask_cmd` の strips も既存パターン。

### S5 Moat 非弱体化 — clean（厳格化方向）
- deny 系フック（check-destructive/secrets/control-plane/runtime-state・patterns.sh・marker.sh・cp-lock）は iter78 diff で**全不変**（`git diff --name-only a5ef438 HEAD` 実測）。evidence.sh は**コメントのみ**（実コード追加0）。
- judge の変更は**セキュリティを締める方向のみ**: (a) pytest family の observed/manual 'ok' を transparent 化（旧: green 可 → 新: green 不可）、(b) attested green に read-time `counts.executed>=1` 要求（fail-closed）、(c) washed-green 透明化を attested へ拡張。いずれも accept 集合を狭める純改善＝回帰0（full 1447 green で確認）。

### S6 Attack surface / 残余 — 新規脆弱性0・SF-024 の OS-limit のみ
- 敵対7クラス実走（review フェーズ）＋本 security の plugin-shadowing 追加検証で、**新規 Critical/Major バイパス0**。
- 残余2（SF-024・in-process event 偽造＋attested 手書き）は**同一ユーザー権限内の OS-limit**（event チャネル・kernel 以外は子が到達可能・SF-004 同型）。roadmap §6 が対象外と明示。**load-bearing 不変「本物の red は偽イベント/偽プラグインでも green 化不能」を pin＋実走で保証**・drill が subsume（all-skip→marker false→BLOCKED）。attestation は accidental 偽 green（`;true`/`-q`/all-skip/collect-only/fake 出力）を全封鎖した net 改善で、残るは故意偽造のみ（pre-iter78 echo-class と同クラス・非拡大）。

## Evidence Checklist

- [x] secrets/credentials grep（新規0）
- [x] 外部入力サニタイゼーション確認（shell なし・shlex・env-prefix/shell-op/-p 抑止 rc2）
- [x] dependency audit（stdlib のみ・外部依存0）
- [x] 全 finding に severity/remediation 付与（下記）

## Findings

| # | severity | 内容 | remediation |
|---|---|---|---|
| — | — | 新規脆弱性 0 | — |
| 残余 | Low（accepted） | SF-024: in-process event 偽造＋attested 手書き（OS-limit・drill subsume・load-bearing 不変 pin 保証） | 別ユーザー/コンテナ境界が必要＝roadmap §6 対象外。文書化＋緩和（read-time counts 検証）済み。deploy blocker でない |

## 盲検2次（独立）

盲検2次 security エージェント（fable・fresh context）を dispatch したが**ハード stall**（16分ツール活動なし・SendMessage 再開も無応答）。LEARNINGS line40 に従い、**独立2次の実質を親が in-session で実走**（1次が深掘りしなかった角度を新たに検証）:

| 独立2次の観点 | 試行 | 観測 | 判定 |
|---|---|---|---|
| 整数 overflow | attested fail に `counts.executed=999999999999` | red のまま（counts は green 判定のみに効く・fail は不変・green forge は executed=1 で足り追加の力なし） | 安全 |
| 並行 attest 一時ファイル衝突 | 2プロセス同時 attest | evidence-log 3行全て valid JSON・torn 0（POSIX append 原子性）・残留一時ファイル0（mkstemp 一意＋finally 削除） | 安全 |
| symlink/event path 乗っ取り | event path 制御可否 | attestor が root/.claude/tmp に mkstemp 生成＝ユーザー非制御（cmd 指定不可・env は親が上書き） | 安全 |

- 独立2次（親 in-session 回収）の**新規脆弱性 0**。1次の結論（新規脆弱性0・load-bearing 不変保持・SF-024 は OS-limit 残余）と**一致**（分岐なし）。

### 盲検2次 agent の完走（約18時間後・post-close）

stall と判断した盲検2次 security agent が最終的に完走し、**verdict approve_with_notes・新規 Critical/High 0** を返した。独立実走で以下を確認し本レポートに収束:
- **本物の red→green は構造的に不能**を多綴りで反証（偽 sessionfinish=0 のみ注入→red／空 suite＋偽 pass 注入 exit5→red／strict-xfail exit 非0→red）。green を作れるのは conftest が `os._exit(0)` で**実 exit code ごと握った**場合のみで、それでも fp 束縛（悪意 conftest を可視コミット木に残さないと clean tree で fp が変わり unverified に落ちる＝実走 STEP1/2 確認）＝SF-024 の既知天井と同クラス（fp が唯一の moat）。
- moat は**強化**（pytest manual/observed 手書き green の transparent 化・counts gate の非対称除去）・依存0・secrets 0・ReDoS なし（2000-test 1.9s/42MB）・並行 attest/symlink 安全・`_mask_cmd` parity 一致（drift なし）。
- **独立 note 2件**（いずれも Informational・非ブロッキング）:
  - **F1（bool 型混同）**: read-time counts gate の `isinstance(int)` が `executed: true`（bool⊂int）を通す。→ **既に post-close で修正済**（`isinstance(bool)` 明示拒否・pin `test_handwritten_attested_bool_executed_fails_closed`・盲検2次の独立発見が修正を裏付け）。
  - **F2（doc-accuracy）**: attest-test-run.py docstring の「PYTEST_ADDOPTS `-p no:` は rc2 に collapse」は不正確＝attestor が明示 `-p aegis_attest_plugin` を末尾付与し pytest 後勝ちで**プラグインは走る**（rc0・実 proof・green mint 不能は不変）。→ **docstring を実測に合わせて精緻化**（`PYTEST_ADDOPTS='-p no:...'` で rc0・executed=1 を実走裏取り）。

## Blockers

- なし。

## Claims（judge が機械読取する）

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["盲検2次を親 in-session で先行回収（整数overflow/並行/symlink 全安全）＋盲検2次 agent が約18時間後に完走 approve_with_notes・新規 Critical/High 0・real red→green 不能を独立多綴り反証・SF-024 天井に収束", "独立 note F1（counts の bool 型混同）＝既に post-close 修正済み・独立発見が裏付け／F2（docstring の PYTEST_ADDOPTS rc2 主張が不正確）＝実測に合わせ精緻化・いずれも Informational 非ブロッキング"]
```

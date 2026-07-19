# Aegis 網羅レビュー（Fable・独立盲検2次）— 2026-07-19

## 0. アンカリング / 実行環境（突合の生命線）

- **対象コミット**: `git rev-parse HEAD` = `77566eda7d15cb70d6ca68377fdbd764834d6fe5` ✅（指示書の対象と一致）
- **framework_version**: `1.31.1`（docs/STATUS.md）／phase=docs / task_type=framework / iteration=73
- **read-only 不変条件**: レビュー全体を通して `git status --short` は空・HEAD 不変を維持（成果物 `docs/fable-review-2026-07-19.md` の新規作成のみが書込み）。
- **レビュアー**: Claude Fable 5（`claude-fable-5`）・reasoning effort high。層2 の breadth（harness/model・context/north-star）に read-only 偵察サブエージェント（general-purpose）2体を使用。severity を持つ再現は全て親（本レビュアー）が自身で実走。

### 実行環境（BSD か GNU か＝実装依存挙動の判別に必須）

```
uname -a : Darwin ...arm64 (Darwin Kernel 25.0.0, RELEASE_ARM64_T8103)
python3  : Python 3.9.6
locale   : LANG="C.UTF-8"  LC_ALL=(空)   ← 対話既定は C.UTF-8（UTF-8 ロケール）
bash     : フックは #!/usr/bin/env bash → PATH 先頭に bash 無し → /bin/bash 3.2.57 で実行
grep(対話): ugrep 7.5.0（Claude Code shell-snapshot の `grep` シェル関数ラッパ）
grep(フック): /usr/bin/grep = "BSD grep, GNU compatible 2.6.0-FreeBSD"   ← フックが実際に使う grep
```

> **方法論上の最重要注意（突合前提）**: 対話シェルの `grep` は **ugrep** に化けている（Claude Code の snapshot 関数）。一方フックは非対話 `/bin/bash` 下で **実 `/usr/bin/grep`（BSD grep）** を使う。したがってフック挙動の再現は「実フックを stdin で走らせる」か「`/usr/bin/grep` を明示」で行い、素の `grep` は使っていない。**作者の基準環境も同じ ugrep ラッパを持つ**ため、作者が対話 grep で「実測」した locale/byte 結論の一部は ugrep 由来で汚染されうる（本レビューはフック実走で回避）。また BSD grep 2.6.0-FreeBSD は `-E` で `\s`/`\b` を**honor する**ことを実測（後述 MOAT-1）。

---

## FRESH top-3（既知事項ドキュメントを読む前に、コード読解のみで固定）

> 手続き: STATUS.md は session-start 契約で先に読んだ（アンカリング一部露出・透明化）。security-followups.md / full-review / LEARNINGS は**この top3 を固定した後**に読んだ。

- **FRESH-1（gate/snapshot tamper-evidence）**: moat の要。update-gate.sh が STATUS + `.gate-snapshot` を書き、raw 編集は post-status-audit.sh で検知される設計。→ 追跡結果は **intact**（settings も両経路で保護・snapshot regression guard 健在）。ただし **post-status-audit は PostToolUse `Edit|Write|NotebookEdit` のみ配線**で Bash 非対象＝非 framework の Bash gate 改竄を止めるのは check-runtime-state 単独 → これが **LOCALE-1 の crash と交差**（下記）。
- **FRESH-2（test-strength green 偽造）**: `aegis_marker_verdict` は「テスト本体が1件以上実行された」ことしか証明せず、**pass/fail は exit code 依存**。exit を洗浄（`; true` / `|| echo` / `| tee`）すると**失敗テストが green 認定**される。→ **TEST-1（SF-012(a) 再現・現行 HEAD で生存）**。
- **FRESH-3（非 hardened フックの locale/byte）**: LC_ALL=C を hook スコープで張るのは check-destructive/secrets のみ。他の抽出/tr 使用フックは C.UTF-8 のまま。→ **LOCALE-1**: `check-runtime-state.sh` が不正 UTF-8 バイトで **`tr: Illegal byte sequence` crash＝fail-open**（iter73 が「同型不成立」と明記した hook が実は crash する＝known-broken）。

---

## エグゼクティブサマリ

Aegis の中核 moat（破壊的コマンド ask・secrets deny・control-plane deny・OS-lock・tamper-evident gate・fingerprint）を実走で再攻撃した結果、**決定論的サーフェス（Edit/Write path・emit deny schema・secrets・OS-lock・settings 保護）は健在**で、iter72 の locale 依存 false-GREEN（F-CRIT-1）も**再攻撃で本当に閉じている**ことを確認した。一方、**iter73 が「完了」と主張した byte-wise 掃討は不完全**で、**test-strength の pass/fail 判定が exit code 単独依存**という構造的天井が現行 HEAD で生きている。層2（Fable 固有）では **モデル品質ピンが Fable 世代で反転**していることを実証した。

**最重要（3〜5件）**:

1. **MODEL-1（Medium・reproduced・known-broken）**: security/planner/reviewer/qa が `opus`（Opus 4.8）に**契約で固定**され、Fable 5 セッション（＝現行）では**最重要役ほど弱いモデルで走る**。implementer/ui は `inherit`＝Fable 5（より強い）で走る。`fable` は `ALLOWED_MODELS` に無く、品質役を Fable に上げる経路が存在しない（前回 R5 の反転が現行で生存）。
2. **LOCALE-1（Medium・reproduced・known-broken）**: `check-runtime-state.sh` が不正 UTF-8 で `tr` crash → rc=1・stdout 空 = **fail-open**。iter73 設計正本の「runtime-state は crash せず＝同型不成立」は**実測で反証**（python3 抽出は surrogateescape でバイトを温存し空にならない）。iter73 の一行修正（`export LC_ALL=C`）で消える（実証）。
3. **TEST-1（Medium・reproduced・known-confirmed→再裁定）**: marker は「実行」しか証明せず、judge は `status=ok` だけで green 認定（build-judge-card.py:312）。exit 洗浄（`; true`/`|| echo`/`| tee`）で**失敗テストが green**。SF-012(a) は「明示的自己欺瞞が必要＝Low」と記録されているが、`|| echo`/パイプは**事故的到達**しうる（reachability 較正で severity 引上げを主張）。
4. **HARNESS-1（Medium／副 reviewer は High・reproduced）**: 全 deny/block は「exit0＋厳密 JSON 形」だけで効き、Claude Code は未認識形を **allow（fail-open）** として扱う。整合の自動検証は無く、drift 検知は subset-only（rename/削除を取りこぼす）、時間 backstop は休眠（stale on ~2026-12-11）。Claude Code の schema 変更で**全 moat が最長半年 無言に fail-open**しうる（配布ユーザに最も刺さる）。
5. **NORTH-1（Medium/High・reproduced）**: gate 承認の儀式が「`approve --ref <path> --ack` を1コマンドで」必須。`--ref` を落として `approve` すると gate は approved になるが ref 空で、**承認時点では失敗せず**完了検査まで顕在化しない。既 approved の ref 後差しは不可（reset→再承認しかない）＝人間への設計負債転嫁（前回 R6 の続き）。
6. **CTX-1/CTX-2（Medium・reproduced・R8 系）**: 常時ロードの `CLAUDE.md`/`STATUS.md` を budget が計測対象外（唯一の enforcement が最重要2ファイルを見ていない）／budget 単位 `len(text.split())` が CJK を ~6x 過小計数＝「context budget green」が信用できない。

**総合評価**: 決定論的 moat の作りは堅牢で、独立盲検の value（F-CRIT-1・SF-016 等）も機能している。残る穴は (a) **出力ベース proof の原理天井（TEST-1）**、(b) **byte-wise 掃討の未完（LOCALE-1）**、(c) **モデル/ハーネス結合の staleness（MODEL-1・HARNESS-1）**、(d) **配布に向けた複雑性・常時ロード肥大（CTX/NORTH）**。(a)(c)(d) は North Star（非エンジニアが強く運用）に直結する。

---

## 層1: 共通コア

### [LOCALE-1] check-runtime-state.sh が不正 UTF-8 バイトで tr crash → fail-open（iter73 掃討の未完・設計主張の反証）
- 次元: locale-byte（＋moat 交差）
- severity: **Medium**（fail-open in a deny-side moat hook・完全性主張の反証・robustness 契約違反。ただし到達性は valid-UTF-8 制約下でゼロ＝High/Critical は付けない）
- confidence: **reproduced**
- 新規性: **known-broken**（iter73 設計/セッション履歴が明示的に「runtime-state は crash せず」と主張）
- 主張: `check-runtime-state.sh` は LC_ALL=C を張らず、コマンドに不正 UTF-8 バイトがあると `tr '\n\r' ';;'`（L121）が `Illegal byte sequence` で異常終了し、`set -euo pipefail` によりフックが rc=1・decision 未出力で死ぬ＝**fail-open**。iter73 は check-destructive/secrets の同一 crash を fix しつつ、runtime-state は「python3 抽出でバイト→空 CMD ＝同型不成立」と記録したが、**python3 は surrogateescape でバイトを温存し空にならない**（実測）。
- 証拠:
  - 配線: `templates/hooks.template.json:53-59`（check-runtime-state は PreToolUse `Bash`）。crash 箇所: `hooks/check-runtime-state.sh:114`（python3 抽出）→ `:120-122`（`if [ -n "$CMD" ]; then CMD=$(printf '%s' "$CMD" | tr '\n\r' ';;'); fi`）。
  - 実走（clean は allow・byte で crash）:
    ```
    $ printf '{"tool_input":{"command":"echo x > docs/STATUS.md"}}' | bash hooks/check-runtime-state.sh
    {}                     [rc=0]      ← task_type=framework で正常 allow
    $ printf '{"tool_input":{"command":"echo \xff x > docs/STATUS.md"}}' | bash hooks/check-runtime-state.sh
    tr: Illegal byte sequence
    [rc=1]                 ← stdout 空・rc≠0 = fail-open crash
    ```
  - 反証（python3 抽出はバイトを温存＝空にならない）:
    ```
    $ printf '{"tool_input":{"command":"echo \xff x > docs/STATUS.md"}}' \
        | python3 -c 'import sys,json; c=json.loads(sys.stdin.read())["tool_input"]["command"]; sys.stderr.write("EXTRACTED: %r\n"%c.encode("utf-8","surrogateescape"))'
    EXTRACTED: b'echo \xff x > docs/STATUS.md'
    ```
  - 修正が効く（iter73 と同一の一行）:
    ```
    $ printf '{"tool_input":{"command":"echo \xff x > docs/STATUS.md"}}' | LC_ALL=C bash hooks/check-runtime-state.sh
    {}    [rc=0]           ← LC_ALL=C を張れば crash 消滅
    ```
  - 対照: 同じバイトで check-tdd.sh / check-gate.sh / check-deploy-gate.sh は crash せず正常 decision を返す（この crash は runtime-state 単独）。
- 到達性較正: バイト 0xFF は JSON(UTF-8) transport 上、モデルが emit するコマンドには出現しない（valid UTF-8 のみ）＝**脅威モデル内で到達不能**。iter73 が destructive/secrets の同一 crash を「robustness hardening（到達性ゼロ）」として直したのと**同カテゴリ**。ただし本 hook は**非 framework モードで Bash による runtime-state（gate 値含む）改竄を止める唯一の PreToolUse ガード**（FRESH-1・post-status-audit は Bash 非配線）であり、fail-open の落ち先が「gate/CP-runtime の Bash 改竄」＝moat の要である点で影響は destructive/secrets より重い。
- North Star への影響: iter73 が「制御フックは任意 stdin で crash しない堅牢性契約」を掲げて2本直したのに、**同契約を満たさない3本目が残存**し、かつ**設計正本に反証済みの完全性主張が durable に残っている**＝配布時に「掃討完了」を信じた保守者を誤誘導する。dimension 3（掃討が完全か）の答えは **No**。
- 修正方向: check-destructive/secrets と同一＝`INPUT=$(cat)` 直後に `export LC_ALL=C LC_CTYPE=C LANG=C`（抽出の python3 は PEP 540 で UTF-8 fidelity 維持）。effort **S**。併せて設計正本の「同型不成立」記述を訂正し、`tests/test_hook_locale_byte.py` に runtime-state の crash-regression pin を追加。

### [TEST-1] test-strength の pass/fail は exit code 単独依存 — 洗浄された失敗テストが green 認定（SF-012(a) 再裁定）
- 次元: test-strength
- severity: **Medium**（誤判定・完了 evidence の中核が破れる。直接 bypass ではないが「evidence-based completion」の看板そのものが失敗）
- confidence: **reproduced**
- 新規性: **known-confirmed**（SF-012(a)・Low/pre-existing と記録）＋**reachability 再裁定**
- 主張: `aegis_marker_verdict` は「本体1件以上実行」しか証明しない。judge（`build-judge-card.py:312`）は marker 済み observed entry を `status=="ok"` だけで green 認定し、**出力の `N failed` を一切再照合しない**。status は exit code 由来なので、exit を洗浄すれば失敗テストが green になる。
- 証拠:
  - marker が「失敗テストでも true」を返す（親実走・実出力）:
    ```
    # 失敗サマリ + prologue、cmd に exit 洗浄
    $ printf 'platform darwin -- Python 3.9\nrootdir: /x\ncollected 3 items\n===== 1 failed, 2 passed in 0.42s =====' \
        | bash -c 'source hooks/lib/patterns.sh; source hooks/lib/marker.sh; cat | aegis_marker_verdict "0" "python3 -m pytest -q; true"'
    → verdict=true
    # パイプ経由（accidental exit-wash）でも true
    $ ... aegis_marker_verdict "0" "pytest | tee log.txt"   → verdict=true
    ```
  - judge の判定コード（出力再照合なし）: `scripts/build-judge-card.py:312`
    ```python
    return {"tests": "green" if d.get("status") == "ok" else "red", ...}
    ```
    status は success recorder（`hooks/post-bash-observe.sh` が `append_evidence "$ROOT" ok ...`）＝exit0 で ok 固定。
  - 分類が runner に載る: `pytest | tee ...` / `pytest || echo done` は `is_test_runner_cmd`＝`AEGIS_TEST_RUNNER_REGEX` の `(^|...)pytest($|[^..])` に一致（先頭 pytest）→ fp 計算・marker 計算経路へ。
- 到達性較正（再裁定の核）: SF-012(a) は severity Low の根拠を「`; true` 等の**明示的 exit 洗浄＝自己欺瞞行為が必要**」に置く。しかし **`pytest || echo done`（失敗を握り潰す典型）・`pytest | tee log`・`pytest | head`（pipefail 未設定時）は事故的に exit0 を作る**普通のパターンで、知識の乏しい利用者や AI 自身が書きうる。少なくとも `|| echo`/`; true` は pipefail 非依存で無条件に exit0。よって「Low＝自己欺瞞限定」という較正は**事故的到達を過小評価**しており、rubric の「誤判定（実害あり・直接 bypass でない）＝Medium」が妥当。
- North Star への影響: フレームワークの中核約束は「evidence-based completion（confidence ではなく証拠）」。失敗テストが green 認定されると、非エンジニアは「テスト緑」を信じて gate を通す＝**中核機能が North Star 条件下で失敗**。marker 層の原理天井（出力ベース proof）＝execution attestation まで塞げない（SF-014 で自認済み）。
- 修正方向: reader 側の矛盾検出＝marker green かつ出力に `[0-9]+ failed`（family サマリ内）同居 かつ status=ok なら green→red/🟡 に落とす（SF-012 の fix 方向・未実装）。または status を pipeline-aware に（観測側で pipefail 相当の signal を要求）。effort **M**（reader 1点 + pin）。

### [SF-011] bash `read_frontmatter` と python `extract_frontmatter` の終端デリミタ差 — 現行 HEAD で生存（contained）
- 次元: SF / locale-adjacent
- severity: Low
- confidence: **reproduced**
- 新規性: **known-confirmed**（SF-011 OPEN・3層 contained）
- 主張: bash `frontmatter.sh` の `read_frontmatter` は `^---[[:space:]]*$`（末尾スペース許容）で frontmatter を閉じ、python `check_status.py:256` の `extract_frontmatter` は `\A---\n...\n---\n`（strict）。`--- `（末尾スペース）を注入すると両者の frontmatter 範囲が割れる。
- 証拠（同一 fixture・両パーサ実走）:
    ```
    fixture frontmatter 中に `task_size: M` の後へ `--- `（末尾スペース）→ `task_size: S` を隠す
    BASH read_frontmatter →  "a: 1\ntask_size: M"                       ← --- で終端
    PYTHON extract_frontmatter → "a: 1\ntask_size: M\n--- \ntask_size: S\nmode: Dev"  ← 継続
    ```
- 到達性/contained: SF-011 記載通り3層で封鎖（check-gate は plan-gate で deny・gate 承認は update-gate 必須・contract の PyYAML cross-check）＝phase-skip の数字上許容に留まりコード編集は unlock されない。単一ユーザ dogfood の自傷面。**再裁定 verdict: Low・OPEN 妥当**（現行 HEAD で乖離は生きているが実害到達なし）。
- 修正方向: SF-011 記載の `read_frontmatter` 終端 strict 化 or parity drift-guard fixture 追加。effort S。

### [SF-CRIT-1] iter72 の locale 依存 false-GREEN（F-CRIT-1）は再攻撃でも閉じている（positive 再裁定）
- 次元: test-strength / locale-byte
- severity: Info（穴ではない・閉鎖確認）
- confidence: **reproduced**
- 新規性: **known-confirmed（閉鎖が本当に閉じている）**
- 主張: iter72 が `aegis_marker_verdict` 冒頭に `local LC_ALL=C` を入れた修正は、stray-byte による Stage4 zero-run veto/Stage5 count 減算の取りこぼしを実際に塞いでいる。
- 証拠（pre-fix で true 再現していた入力が post で false 維持）:
    ```
    all-skip unittest に 0xFF 付与 → verdict=false（`OK (skipped=3)\xff` / `Ran 3 tests\xff` とも）
    forged strong marker + `collected 0 items\xff` → verdict=false（Stage4 健在）
    clean all-skip → verdict=false（対照）
    ```
- 所見: 独立盲検の value（1次 opus 見落とし→盲検2次摘発）が iter72 で機能し、その fix が現行で堅い。**dimension 2（閉じた主張の再攻撃）で「本当に閉じている」側の確認**。対照的に LOCALE-1 は「閉じたと主張したが実は未着手」の側。

### [SF-015 / SF-016 / SF-013 再裁定（簡潔）]
- **SF-015（pytest all-xfail 偽陰性）**: `===== 3 xfailed in 0.5s =====` のみ→verdict=false を再現。**fail-closed（安全側）・Low・OPEN 妥当**（実行過小評価のみ、false-GREEN を作らない）。known-confirmed。
- **SF-016（LC_ALL=C が Unicode 空白 moat を狭める）**: 文書化済みの accepted residual。bash は NBSP/U+3000 で word-split しない＝非コマンドゆえ無害という判断は妥当。**非 exploitable・OPEN 妥当**。known-confirmed（再現省略）。
- **SF-013（update-gate sed 範囲 / --ref symlink）**: canonical STATUS では範囲が top-level key で閉じる＝到達には異常 frontmatter が必要。**Low・OPEN 妥当**。known-confirmed（深掘り再現は tree を汚すため回避）。

### [MOAT-1] 決定論的 moat サーフェスの再攻撃 — 健在（known-confirmed・偽陽性1件を自己棄却）
- 次元: moat
- severity: Info（健在確認）
- confidence: **reproduced**
- 新規性: known-confirmed
- 再攻撃と結果（全て実フック実走）:
  - **破壊的 ask**: `rm -rf /` `rm -rf /etc` `drop table users` `git push -f` → 全て `ask`（emit_ask）。BSD grep 2.6.0-FreeBSD は `-E` の `\s`/`\b` を **honor**（`rm\s+-rf`/`\btruncate\b`/`git\s+push\s+.*(-f\b)` 全一致・実測）。patterns.sh の cross-engine subset 制約は grep∩python-re parity の話で、grep 単独の destructive パターンが `\s`/`\b` を使うのは非バグ。
  - **escaped-quote decoy（SF-001 系の続き）**: `echo "safe" ; rm -rf /etc` / `git commit -m "done" ; rm -rf /etc` / `echo "a\"b" ; rm -rf /etc` → **全て `ask`**（extract_command が `\\[\\nrtbfu"/]` 検出で python3 経路へ→末尾の destructive を正しく抽出）。**⚠自己棄却**: 初回 `{}`(allow) を観測したが、原因は私のシェル escaping による malformed JSON であり、`python3 json.dumps` で payload を決定化したら全て `ask`＝**偽陽性**。moat バイパスではない。
  - **secrets deny**: `git add .env` / `git add config/credentials.json` → **`deny`**（emit_deny schema 妥当＝`hookEventName:PreToolUse`・`permissionDecision:deny`、python で parse 検証済）。
  - **settings 保護**: `.claude/settings.local.json`（hook 配線本体・OS-lock 対象外）は check-gate の `is_protected_dir .claude`＝`.claude/*` glob で Edit/Write deny、Bash は `RUNTIME_STATE='...\.claude/...'` で deny（非 framework）。**hook 無効化経路なし**。
  - **gate tamper（FRESH-1）**: update-gate.sh が STATUS+snapshot 原子書込み、raw Edit/Write は post-status-audit で tamper block、session-start の `aegis_snapshot_gate_regression` が approved→pending の revert laundering を阻止。Edit/Write path は健在。**残留観察**: post-status-audit は Bash 非配線ゆえ、非 framework の Bash gate 改竄は check-runtime-state 単独依存（→ LOCALE-1 と交差）。framework モードの Bash gate 改竄は「信頼モード＝受容」（SF-006 と同クラス）。
- North Star への影響: 中核 moat は事故防止として機能している（positive）。**教訓**: 生 payload を決定論的に作らないと moat 再現は偽陽性を生む（本レビューで実際に1件発生・自己棄却）＝「生出力必須」規律の実証。

### [NORTH-1] gate 承認の儀式が単一原子コマンド前提 — 直感的経路が「後で気づく」不整合を残す
- 次元: north-star
- severity: **Medium/High**（設計負債の人間側転嫁・非エンジニア運用に直撃）
- confidence: **reproduced**（偵察サブエージェントが隔離コピーで再現・親がコード裏取り）
- 新規性: 新規（前回 R6「罠の6割は設計で根絶可能」の続き）
- 主張: review/qa/security/deploy/plan の承認は「`approve --ref <path>` ＋（🟡 なら）`--ack "理由"`」を**1コマンド**で渡す必要がある。`--ref` を落として `approve` すると gate は approved になるが `current_refs.<gate>` が空のまま＝**承認時点では成功扱いで、完了検査（別タイミング）まで顕在化しない**。しかも既 approved の ref 後差しは update-gate では不可（`already approved. --ref 未適用`）＝**reset→再承認しか回復手段がない**（raw Edit は tamper block）。
- 証拠:
    ```
    approve（フラグ無し・🟡 gate）→ 「🟡 要確認... --ack "理由" を添えてください」で拒否
    approve --ack "reviewed"（--ref 無し）→ gate=approved
    python3 scripts/check_status.py --check-completion-evidence
      → EVIDENCE: gate 'review' is approved but current_refs.review is empty
    ```
    正解シーケンス: `scripts/update-gate.sh:6` の `approve --ref <path> --ack "reason"` を1発。既approved後: `update-gate.sh:269-274`（`--ref 未適用`）。
- North Star への影響: 「正しい操作列の暗記（職人芸）」を人間に要求。非エンジニアが自然な手順で承認すると、approved だが完了検査で無言に落ちる状態を作り、手で直せない（tamper block）。advisory 文言はあるが失敗が**遅延**し回復経路が儀式知識前提。
- 修正方向: ref を生む gate の `approve` は**承認時点で `--ref` を必須化して fail-fast**（完了検査ではなく approve で落とす）／または対話プロンプト。effort **S**。

### [NORTH-2] 複雑性収支（懐疑側に立った操作的証拠）
- 次元: north-star
- severity: Medium（保守性天井は hypothesis・数値は reproduced）
- confidence: reproduced（counts）/ hypothesis（impact）
- 主張・証拠（偵察サブエージェント実測・親が抜き取り確認）:
  - 単一保守者が整合を保つ制御面: **hooks 18 + hook libs 14 + scripts 19（Python 6,938 行・shell 5,021 行）+ skills 18 + agents 12**、manifest⇄allowlist⇄snapshot⇄drift⇄budget の invariant 網、**tests 1,306（95 files）**、**docs 287 files / 37,301 行**。最大 script は `check_status.py` 1,569 行・`check_framework_contract.py` 1,113 行。
  - 未使用に近い抽象: `scripts/learnings_search.py` は production 参照が `retro_report.py` の import 1件のみ・CLI 呼出し0（`grep -rn learnings_search hooks scripts .claude bin` で確認）＝CLI+lib のうち lib 半分だけ使用。
- North Star への影響: 「単一作者が保守でき、非エンジニアが使える」水準に対し、invariant 網の結合度が高く（1 script 変更で 3-4 cross-check が連動）保守天井が近い。impact は hypothesis ゆえ Medium 上限。
- 修正方向: 最高結合の checker（`check_status` と `check_framework_contract` の gate/ref invariant 重複）統合、learnings_search を内部ヘルパ降格。effort L（単発 fix ではない）。

---

## 層2: Fable 特化

### [MODEL-1] 品質ピンが Fable 世代で反転 — 最重要役が弱いモデルに契約固定（前回 R5 が現行で生存）
- 次元: model-policy
- severity: **Medium**（防御の縮退＝security/review moat が利用可能な最強モデルより弱いモデルで走る。config は reproduced・品質差 impact は hypothesis）
- confidence: **reproduced**（config 事実）
- 新規性: **known-broken**（R5 の反転が Fable 世代で顕在・未対応）
- 主張: `security`/`planner`=`opus`/max、`reviewer`=`opus`/xhigh、`qa`=`opus`/high に**契約固定**。モデルカード上 Fable 5（＝現行セッション model）は Opus 4.8 の上位（Mythos-class は Opus 超）。frontmatter は session model を outrank するので、**Fable 5 セッションでも security/planner/reviewer/qa は Opus 4.8（弱い方）で走り、implementer/ui（`inherit`）は Fable 5（強い方）で走る**＝品質役ほど弱い。`fable` は `ALLOWED_MODELS={opus,sonnet,inherit}` に無く、品質役を Fable に上げる経路が無い（`CLAUDE_CODE_SUBAGENT_MODEL` は全 pin **降格**のみ）。
- 証拠:
    ```
    .claude/agents: security=opus/max  planner=opus/max  reviewer=opus/xhigh  qa=opus/high
                    implementer=inherit/high  ui=inherit/high
    scripts/platform_manifest.py:27  ALLOWED_MODELS = frozenset({"opus","sonnet","inherit"})   # fable 不在
    grep -rin 'fable|mythos' platform_manifest.py check_framework_contract.py .claude/agents CLAUDE.md → 0 hits
    scripts/check_framework_contract.py:305-319  MODEL_EFFORT_POLICY を exact-match で FAIL 検証
      → security を fable にすると FAIL: model=fable not in ALLOWED_MODELS ['inherit','opus','sonnet']
      → かつ OPUS_ONLY_EFFORTS={xhigh,max} は文字列 "opus" に gate（:326-327,351-352）＝
        fable を ALLOWED に足しても effort:max は依然 FAIL＝policy は capability tier ではなく名前 "opus" に溶接
    python3 scripts/check_framework_contract.py → exit=0 "PASS"（session tier に対し盲目）
    ```
  - **作者は既知で未対応**: `docs/plans/2026-07-02-iter54-critical-batch-design.md:147` が「モデル manifest の Fable 5 再ティア」を **deferred item として列挙**（＝反転は認識済みだが iter73 まで未クローズ）。session が fable で走ることは framework 自身の docs（iter65/68 plan・iter73 design「review 1次=opus→親verify=fable・盲検2次=fable」）が establish。
- 到達性較正: これは edge ではなく**任意の Fable セッションでの既定挙動**（＝本レビューセッション自体がその状態）。ただし「Opus 4.8 が見逃し Fable 5 なら捕える脆弱性が実際に漏れる」は未実証ゆえ品質 impact は hypothesis。
- North Star への影響: Aegis の差別化資産は security/review moat。それを**利用可能な最強モデルより弱いモデルに固定**するのは、moat を一番効かせたい局面で自ら縮退させる。配布時、モデル世代が動くたびピンが陳腐化し、staleness 窓（180日）は tier 再編（Fable は ~35日前）に対して粗すぎる（HARNESS-1 参照）。
- 修正方向: (1) `fable` を lineage alias として `ALLOWED_MODELS` に追加、(2) 品質役の pin を「session model が opus 超なら inherit、未満なら opus 床」に変える（＝下方は守り、上方は追随する非対称 pin）、(3) `MODEL_EFFORT_POLICY` を「≥opus」意味論に。effort **M**（manifest+contract+agents 数行だが設計判断を伴う）。

### [HARNESS-1] deny/block enforcement が Claude Code の schema drift で静かに fail-open — 唯一の検知器は休眠中の 180日日付
- 次元: harness
- severity: **Medium**（rubric の到達性規律に従い Medium＝防御の縮退・fail-visible の欠け。ただし**トリガ時の impact は全 moat の fail-open** で、副 reviewer は **High** を主張。将来 Claude Code 変更が前提ゆえ現時点で reproduced-reachable な bypass ではない＝High は付けない）
- confidence: **reproduced**
- 新規性: 新規（構造的留意点）
- 主張: 全ゲート（deny/ask/block/hard-stop）の強制は「exit0 時に stdout に印字する厳密な JSON 形」だけに依存し、Claude Code は **exit0＋未認識/空/malformed stdout を allow（fail-open）として扱う**（副 reviewer が claude-code-guide＋公式 `code.claude.com/docs/en/hooks-guide.md` で確認: "Exit 0 with no output … the tool call continues"／"JSON output is only processed on exit 0"）。この整合を検証する自動チェックは存在せず（Aegis のテストは「Aegis が Aegis の期待形を印字する」ことしか証明しない）、唯一の drift 検知は subset-only ＝ **rename/削除を検知できない**うえ、時間 backstop も休眠中。
- 証拠:
  - 実 deny（emit の deny schema が効くのは Claude Code が `hookSpecificOutput.permissionDecision:"deny"` を認識する時のみ）: `hooks/lib/emit.sh:47-72`／`git add .env` → deny 出力（MOAT-1 で実走済）。
  - **drift check は subset-only で rename/削除を取りこぼす**（`scripts/check_reference_drift.py:470-475` は `event not in KNOWN_HOOK_EVENTS` の混入のみ検出）:
    ```
    $ python3 scripts/check_reference_drift.py → PASS: no reference drift detected
    # Claude Code が PreToolUse を rename/deny キーを変えても、template ⊆ stale set のまま PASS
    ```
  - 時間 backstop は休眠: `platform_manifest.py:54-66`、`stale_keys(2026-07-19) → []`（hook_output_schema は 2026-06-14 検証・age35日・**stale on ~2026-12-11**）。
  - **同一契約の "verified" 日付が2ファイルで不一致**: `emit.sh:17` は "Schema reference (verified 2026-06-05)"・manifest は `2026-06-14`＝drift の temoto。
- North Star への影響: moat の最終有効性が「作者が半年ごとに手で platform を再確認する」に依存。非エンジニア配布ユーザは Claude Code 更新で全 deny が allow に縮退しても**エラーもテスト失敗も advisory も 180日出ない**まま「守られている」と信じて出荷し続ける＝target user に最も刺さる失敗モード。
- 修正方向: (M) install/session-start で「既知 deny 入力→実インストール済み Claude Code hook 経路が実際に block したか」を smoke 検証する `verify-harness`。(S) 2つの verified 日付を manifest へ一本化（emit.sh:17 の prose 日付削除）＋`STALENESS_DAYS` を 180→~60 に短縮＋advisory を session-start 出力に載せる（現状 `check_reference_drift.py` 手動実行でしか出ず初心者は走らせない）。

### [HARNESS-2] TaskCompleted の完了強制は exit-2 依存で fail-closed fallback が無い
- 次元: harness
- severity: Medium
- confidence: **reproduced**
- 新規性: 新規
- 主張: deny 系（safety.sh で fail-closed）と違い、`TaskCompleted` の「完了に evidence 必須」は JSON でなく **`exit 2`＋stderr** で強制する。Claude Code が TaskCompleted の exit-2-as-pushback を honor しなくなる/event を rename すると、**完了が evidence 無しで無言に成功**し、この経路には fail-closed fallback が無い。
- 証拠: `hooks/check-task-completed.sh:111-114,140` が `exit 2`／pin `tests/test_hook_output_schema.py:936`（"TaskCompleted push-back must exit 2"）。対照的に `TaskCreated` は fail-closed JSON hard-stop（`{"continue":false,...}`・実走確認）。`safety.sh` の fail-closed emitter は PreToolUse deny / PostToolUse block のみで exit-2 経路には無い。
- North Star への影響: "Completion requires evidence, not chat confidence" は operating-contract の核。非エンジニアが「AI の早すぎる完了宣言を止める」ために依存する経路が無言に退行すると、虚偽 done が素通りする。exit-code 意味論は JSON より安定ゆえ HARNESS-1 より低め。
- 修正方向: (S) exit-2 依存を manifest の独立 verification key として dated 追跡（現在 hook_events に相乗り）＋TaskCompleted boot path に「exit-2 契約喪失＝fail-open」の upgrade チェック注記。

### [HARNESS-3] Claude Code 入力契約への広い人手保守結合 — 縮退が graceful だが silent（deploy-MCP matcher rename で moat 無言停止）
- 次元: harness
- severity: Medium
- confidence: **reproduced**
- 新規性: 新規
- 主張: 出力 schema 以外にも、payload キー名（`task_subject`・`tool_response.stderr`・`tool_response.exitCode`）、`settings.local.json` の `hooks→Event→[{matcher,hooks:[{command}]}]` 構造、event 別 matcher 意味論、tool 名トークンを hard-code。多くは key 不在時 pass-through（fail-open）へ縮退。
- 証拠:
  - payload キー推測（`extract-input.sh` が3 schema を試すのは実 key が不明ゆえ）・test docstring "camelCase, Claude Code 2.x suspected"（`tests/test_hook_output_schema.py:1077`）。
  - **third-party MCP matcher rename で deploy gate 無言停止**: `platform_manifest.py:46-50` の `KNOWN_TOOL_NAMES` に `mcp__claude_ai_Vercel__deploy_to_vercel`。Vercel MCP tool 名が変わると `check-deploy-mcp-gate.sh` の matcher が発火せず deploy が素通り。かつこの検査は **WARN であって FAIL ではない**（`check_reference_drift.py:483-487`）＋手動実行時のみ表面化。
  - `bin/setup.sh:362-472` が settings の入れ子形を前提に parse/rewrite・`check_framework_contract.py:595-609` が同構造から登録コマンドを再導出＝settings schema 変更で install 配線が壊れる。
- North Star への影響: 「単一作者が保守できる」に直撃＝platform bump ごとに emit.sh/manifest/extract-input/setup.sh 横断で十数点を手再検証。多くが silent 縮退（matcher miss→hook skip→allow）でエラーが出ない。
- 修正方向: (M) 全 payload 前提を manifest へ集約＋control-plane hook（deploy/secrets）の matcher 検査を WARN→FAIL 昇格（rename が build を壊す＝moat を静かに壊すのでなく）。

### [HARNESS-4] subagent frontmatter 契約（model/effort/maxTurns/readOnly/permissionMode）は自己参照でしか検証されない
- 次元: harness
- severity: Low
- confidence: reproduced
- 新規性: 新規
- 主張: `check_framework_contract.py:962-994` は frontmatter の `maxTurns`/`readOnly`/`permissionMode`/`effort` を検証するが Aegis-対-Aegis のみ。Claude Code がこれらキーを rename/削除すると、契約は PASS のまま挙動（read-only 強制・turn cap）だけ無言に停止。
- 証拠: 契約 PASS（`python3 scripts/check_framework_contract.py → PASS`）／`.claude/agents/security.md:2-11` の `readOnly:true`/`permissionMode:plan`/`maxTurns:20` は Claude Code の behavioral directive だが honor を検証する術は無い。
- North Star への影響: reviewer の read-only/turn-cap 退行は品質退行であってセキュリティ bypass ではない（security agent の実力は deny hook＝frontmatter ではない）ゆえ Low。保守面で「key があること＝platform が honor する証拠」と誤認する surface が1つ増える。
- 修正方向: (S) これらキーを manifest の dated verification set に追加。

### [CTX 群] context 経済（R8 既知中心・新規の operational 証拠）
> charter 指示に従い dimension 8 は known-confirmed 中心。前回 R8 で「常時ロード肥大・thin 哲学の自己矛盾・CJK 未計数」は既知。以下は現行 HEAD の**実測**。

- **[CTX-1] budget が L0 の2ファイルを計測対象外**（severity Medium・reproduced・R8 系）: `context_budget.py:61-65 iter_targets()` は skills+rules のみ。**唯一の enforcement が「常時ロード」と自称する CLAUDE.md/STATUS.md を見ていない**。実測: CLAUDE.md ~1,298 tok / STATUS.md ~6,493 tok / rules ~949 tok ＝ L0 合計 ~8,740 tok が無 budget。STATUS.md は毎 iteration 成長（73回）で歯止め無し。
- **[CTX-2] budget 単位が `len(text.split())`＝CJK ~6x 過小**（severity Medium・reproduced・R8/budget#3 既知）: `context_budget.py:21-22`。日本語は空白無しゆえ1段落≈1「語」。例: `qa-verification` budget 507語 実 ~3,017 tok。**budget green が token 実費と乖離**。
- **[CTX-3] ratchet headroom 実質0**（Low・reproduced）: routing.md/state-machine.md/client-workflow が headroom 0。単位が split ゆえ「CJK 追記は0加算で通り、ASCII 追記は breach」＝誤ったシグナルで発火。
- **[CTX-5] STATUS.md の 76% が session_history**（Medium・reproduced）: 15,661 字中 session_history 11,887 字。1エントリ 3,383/3,018/5,471 字の commit-essay 級 jargon（fail-open/byte-wise/PEP 540）。**非エンジニアが毎回最初に読めと言われるファイル**が読めない・毎回高コストでロード。≤3 件 cap はあるが**1件あたりの語数 cap が無い**。
- **[CTX-6] LEARNINGS 138KB/~41,700 tok**（Low）: session-start 注入は conf8-10 の grep ≤3行で有界（＝常時全ロードではない・good）。ただし docs phase の「LEARNINGS 更新必須」は全読み/追記を要し単調増加。auto-memory の重複は未検出（CLAUDE.md 規則は遵守）。
- North Star への影響: 「thin L0」は enforcement の穴（CTX-1）と CJK 盲点（CTX-2）で**未強制**。配布に向け、常時ロードの STATUS を人間可読・機械計測可能に絞るのが最も費用対効果が高い。
- 修正方向: (1) CLAUDE.md/STATUS.md を CJK-aware 単位で budget 対象化（CTX-1+2 統合・M）、(2) session_history の1件語数 cap＋全文は evidence-archive へ（CTX-5・S/M）。

### [MODEL-2] `CLAUDE_CODE_SUBAGENT_MODEL` は全 pin を security 含め一括降格するのみ（上げ経路なし）
- 次元: model-policy
- severity: Low
- confidence: reproduced（挙動はコード/CLAUDE.md 記述で確定）
- 新規性: known-confirmed
- 主張: CLAUDE.md model policy 上、pin を上書きする唯一の env は `CLAUDE_CODE_SUBAGENT_MODEL`＝**全役割を一括降格**（security も）。個別役割を強い方へ上げる env/frontmatter 経路が無い（MODEL-1 の裏返し）。session-start が env 設定時に advisory を出すのは適切だが、advisory であり block ではない。
- North Star への影響: 品質役を強くしたい正当ケース（Fable セッション）に対し policy が「降格しか用意していない」＝MODEL-1 と同根の非対称。
- 修正方向: MODEL-1 の非対称 pin（下方は床、上方は追随）で一括解消。

---

## 次元別サマリ表

| 次元 | 新規/known-broken 件数 | 最高 severity | 主所見 |
|---|---|---|---|
| moat | 0 新規（health 確認・偽陽性1自己棄却） | Info | 決定論サーフェス健在・settings 両経路保護 |
| SF（再裁定） | 0 新規（SF-011/013/015/016 = OPEN 妥当・F-CRIT-1 = 閉鎖確認） | Low | SF-011 現行生存だが contained |
| locale-byte | **1 known-broken（LOCALE-1）** | **Medium** | runtime-state tr crash fail-open・iter73 掃討未完 |
| test-strength | **1 known-confirmed 再裁定（TEST-1）** | **Medium** | pass/fail が exit code 単独＝洗浄で false-green |
| regression | 1（R5=MODEL-1 で再掲・R6/iter60 は健在確認） | Medium | quality-pin 反転が現行生存 |
| north-star | 2（NORTH-1 新規・NORTH-2 複雑性） | Medium/High | gate 承認儀式の罠・保守面過大 |
| harness | 4 新規（HARNESS-1〜4） | Medium（impact-if-triggered は全 moat fail-open＝副 reviewer は High 主張） | schema drift → 静かな fail-open（subset-only drift 検知・180日休眠窓）／TaskCompleted exit-2 無 fallback／deploy-MCP matcher rename で無言停止／frontmatter 自己参照検証 |
| context | 群（CTX-1/2 = R8 系・operational 更新） | Medium | budget が L0 未計測・CJK 6x 過小 |
| model-policy | 2（MODEL-1 known-broken・MODEL-2） | Medium | Fable 世代でピン反転（契約固定） |

---

## 触れない/追わないと判断した提案（ノイズ抑制の透明化）

- **「CI を足せ / 型注釈 / カバレッジ向上」等の一般論**: 具体的失敗シナリオ＋North Star 影響に結びつかないため除外。
- **SF-004/005（interpreter コード・extglob）を格上げ**: 静的解析の原理的限界＋OS-lock 補完で受容済み・脅威モデル外（意図的難読化）。到達性実証なしに格上げしない。
- **OS-lock（cp-lock.sh）の敵対 bypass（os.chmod 解錠）**: 脅威モデルが明示的に「敵対者は解錠して書ける＝範囲外」と宣言済み・by-design。事故防止スコープでは syscall 強制で健在。
- **LOCALE-1 を High/Critical に格上げ**: 不正 UTF-8 はモデルの valid-UTF-8 emit では到達不能＝rubric「到達性未実証は High 不可」に従い Medium 上限（iter73 自身の格下げ較正と整合）。
- **TEST-1 のパイプ変種を「無条件到達」と主張**: pipefail 設定依存ゆえ、無条件は `; true`/`|| echo` に限定して主張（過大主張回避）。
- **budget-exclude 濫用（CTX-4）を格上げ**: 現状 routing.md の roster 1箇所のみ・専用 pin あり＝contained。将来 marker 拡散時のみ再評価。

---

## STATUS（完了規律）

**STATUS: 層1 完走（moat/SF/locale/test-strength/regression/north-star）＋層2 完走（harness #7・model #9・context #8）。** severity を持つ全所見に親自身の実走生出力を添付（層2 breadth は read-only 偵察サブエージェント2体が収集→親が裏取り・severity 判定は親）。read-only 不変条件（git clean・HEAD 不変）維持。

- **hypothesis 止まり**: TEST-1/MODEL-1 の「品質 impact」（弱モデルが実脆弱性を見逃す/exit洗浄が事故頻度）は原理上実証困難ゆえ hypothesis 明記。NORTH-2 の保守天井も hypothesis（counts は reproduced）。HARNESS-1〜4 は「将来 Claude Code 変更時の縮退」＝reproduced（現在の構造ギャップ）だが trigger 自体は将来条件。
- **深掘りを意図的に見送った面（透明化）**: cp-lock.sh の OS-lock 敵対 bypass（脅威モデル外）／SF-013(a) の異常 STATUS 構築再現（tree 汚染回避）／check-gate.sh の全 glob 難読化クラス総当り（iter32 rounds で網羅済みと判断）。これらは known-confirmed として扱い、新規攻撃はしていない。
- **severity 内部 divergence の透明化**: HARNESS-1／MODEL-1 を副 reviewer（偵察）は **High**、親は charter rubric の到達性規律（到達性未実証は High 不可・将来条件 or 品質 impact hypothesis）に従い **Medium** と裁定。impact-if-triggered は両件とも重大（全 moat fail-open／security 縮退）ゆえ、下振れさせない旨を明記。

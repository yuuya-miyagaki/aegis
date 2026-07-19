# Aegis v1.31.1 Codex 独立レビュー — 2026-07-19

## 0. 判定

- **レビュー対象**: `77566eda7d15cb70d6ca68377fdbd764834d6fe5` / framework `1.31.1`
- **レビュー網羅状態**: **COMPLETE**（指定された全7次元を調査）
- **実行検証範囲**: **PARTIAL**（個別の攻撃再現と `pytest --collect-only` は実施。read-only 制約を優先し、全1306テストの実走や installer の新規 target 書込みは行っていない）
- **総合判定**: **REJECT UNTIL P0 IS CLOSED**
- **理由**: Aegis の安定 control plane と byte-wise 決定化は実際に改善している。一方、現行の静的シェル文字列検査は実行可能な quote-concatenation を見落とし、secret deny と destructive ask を `allow` にできる。また test green は依然として出力文字列から作られ、実行していないテストの green を再現できる。後者は文書化済み residual だが、本レビュー指示の severity rubric（「reachable forged green = Critical」）では受容できない。

今回の重要な結論は「防御をさらに増やす」ではない。**raw shell text と raw test output を真実の代理にしている2箇所を、構造化された argv と実行イベントへ置換する**ことが次の進化点である。

## 1. 方法・前提

既知 finding を読む前に、現行コードを fresh-first で攻撃した。その後 `docs/security-followups.md`、前回レビュー、STATUS/LEARNINGS、関連 hook・judge・test-strength drill・installer・onboarding を照合した。

判定ラベル:

- **new / reproduced**: 今回初めて抽出し、現行 HEAD への command/output で到達を確認。
- **known-confirmed / reproduced**: 既知項目を現行 HEAD で再現。
- **known-confirmed / source**: 現行 source で残存を確認したが、今回の隔離 E2E は未実施。
- **closed / revalidated**: 閉鎖主張を再攻撃し、現行 HEAD で閉鎖を確認。
- **hypothesis**: コード上の経路はあるが、今回の raw E2E 証拠が不足。

環境:

```text
Darwin 25.0.0 arm64
GNU bash 3.2.57(1)-release
Python 3.9.6
LANG/LC_ALL/LC_CTYPE=C.UTF-8
```

開始時点から存在した user-owned change は `docs/STATUS.md` と iter74 の5 spec。これらは変更していない。

## 2. Executive summary

| ID | Severity | 状態 | 結論 |
|---|---:|---|---|
| MOAT-001 / FRESH-1 | **Critical** | new / reproduced | `g""it a""dd .e""nv` と `r""m -rf` は Bash では正規 argv になるが、secret/destructive hook は allow |
| TEST-001 / FRESH-2 / SF-014 | **Critical** | known-confirmed / reproduced | 実 runner 不在でも pytest 風 output を印字すれば marker=true、judge green に到達 |
| TEST-002 / FRESH-3 | **High** | known-confirmed / partial reproduction | B1 は構文的に有効な import/runtime-crash mutant を許し、任意の nonzero を `caught` と数える |
| SF-012 | **Critical + Low** | known-confirmed / reproduced | `pytest; true` の washed-green は再現。unknown `src` の decidable-by-default も残存 |
| SF-011 | Low | known-confirmed / source | Bash/Python frontmatter terminator drift は残存。既存3層で contained |
| SF-013 | Low | known-confirmed / source | sed 範囲終端と symlink ref の hardening backlog は残存 |
| SF-015 | Low | known-confirmed / reproduced | all-xfail は false-negative。安全側だが実行済みテストを証明できない |
| SF-016 | Info | accepted / revalidated | Unicode space の narrowing は allow になるが Bash では非コマンド、exploit 不成立 |
| LOCALE-001 | Info | closed / revalidated | iter72 invalid-byte false-green と iter73 `tr` crash の修正方針は有効 |
| NORTH-001 | Medium | known-confirmed | L0 が再膨張。STATUS 1445 words、CLAUDE.md は上限650 wordsで余白ゼロ |
| DIST-001 | Medium | new / source-confirmed | setup が baseline commit を自動作成するのに hands-on は再度 commit を必須化 |
| DIST-002 | Medium | known-confirmed | onboarding は `deploy na` を指示するが checker は deploy の n/a を必ず拒否 |
| DIST-003 | Low | known-confirmed | installer に dry-run がなく、stamp は version のみ。profile switch の意味が見えない |

Critical 2クラスは独立している。MOAT-001 は「危険操作の前段」を抜け、TEST-001 は「完了証拠の後段」を偽る。両方を閉じない限り、Aegis の「事故を防ぎ、偽 green を作らない」という中核 claim は強すぎる。

## 3. Finding details

### MOAT-001 / FRESH-1 — Bash quote-concatenation で moat token を分断できる

**Severity: Critical / confidence: high / new / reproduced**

静的 regex は `rm`、`git add`、`.env` 等を raw command 上で探す。一方 Bash は隣接した quoted/unquoted fragment を1 token に連結する。空 quote は実行時に消えるため、raw text に検出語を置かず、正規の危険 argv を作れる。

```bash
python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]}}))' \
  'r""m -rf /tmp/aegis-review-victim' | bash hooks/check-destructive.sh
bash -c 'set -- r""m -rf /tmp/aegis-review-victim; printf "argv[0]=%s argv[1]=%s argv[2]=%s\n" "$1" "$2" "$3"' _
```

```text
{}
argv[0]=rm argv[1]=-rf argv[2]=/tmp/aegis-review-victim
```

```bash
python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]}}))' \
  'g""it a""dd .e""nv && g""it c""ommit -m leak' | bash hooks/check-secrets.sh
bash -c 'set -- g""it a""dd .e""nv; printf "argv[0]=%s argv[1]=%s argv[2]=%s\n" "$1" "$2" "$3"' _
```

```text
{}
argv[0]=git argv[1]=add argv[2]=.env
```

`{}` は hook の allow。後段 argv は Bash が実際に解釈する token である。これは hostile filesystem や evidence-log 直接編集を必要とせず、モデルが valid UTF-8 の command を1回生成するだけで到達する。特に secret hook は ask ではなく deny のため Critical とする。

**修正方針**: raw regex を捨てず第一層として残し、その前に conservative shell lexical normalization を追加する。Python `shlex` の punctuation mode 等で command segment と argv を作り、parse error は secret=deny / destructive=ask。少なくとも adjacent empty quotes、quoted fragment、escaped charactersを正規化した token viewにも同じ policyを適用する。完全な Bash parser を自作してはならない。

### TEST-001 / FRESH-2 / SF-014 — output marker だけで test green を製造できる

**Severity: Critical / confidence: high / known-confirmed / reproduced**

現行 marker は no-run flag、prologue、zero-run、count を丁寧に検査するが、入力が「runner 自身から来た」ことを証明しない。存在しない executable の失敗を `|| printf` で洗い、pytest 風出力と shell exit 0 を作るだけで classifier と marker の両方が true になる。

```bash
pytest-not-installed || printf 'platform darwin -- Python 3.9.6\nrootdir: /tmp\ncollected 1 item\n=== 1 passed in 0.01s ===\n'
```

```text
bash: pytest-not-installed: command not found
platform darwin -- Python 3.9.6
rootdir: /tmp
collected 1 item
=== 1 passed in 0.01s ===
classifier=true
marker=true
```

同じ evidence を現行 `read_test_result_detail` に与えた再現結果:

```text
{'tests': 'green', 'cmd': 'pytest-not-installed || printf forged',
 'src': 'observed', 'ts': '2026-07-19T00:00:00Z'}
```

SF-014 は echo-marker を「output-based proof の床」と正しく記録している。しかし judge card と gate がこの値を test fact として green 表示する限り、これは単なる residual ではなく claim の境界違反である。今回の rubric に従い Critical へ再裁定する。

**修正方針**: output marker を「実行証明」から「互換用の診断信号」へ格下げする。green を作れる producer は、shellを介さず test argv を spawn し、runner adapter が structured event（executed/failed/skipped/collection_error/exit）を生成した経路に限定する。最初は Aegis 自身が使う pytest のみでよい。unknown runner は yellow/unverified のままにする。

### SF-012 — washed-green と unknown-src

**Severity: Critical (washed-green) / Low (unknown-src) / known-confirmed**

washed-green は現行 HEAD で再現した。

```bash
printf '%s\n' \
  'platform darwin -- Python 3.9.6' 'rootdir: /tmp' 'collected 3 items' \
  '=== 1 failed, 2 passed in 0.01s ===' \
| bash -c 'source "$1"; printf "verdict="; aegis_marker_verdict 0 "pytest -q; true"; printf "\n"' \
  _ hooks/lib/marker.sh
```

```text
verdict=true
```

`build-judge-card.py:303-312` は `src == "observed" and marker_verified is not True` だけを undecidable とするため、未知/欠落 src は status と fingerprint が合えば decidable のままである。未知 src は実 writer が発行しないため Low 据置。ただし allowlist 化は小さく、安全側なので P0 に含める。

**短期修正**: exit 0 と failed count > 0 の矛盾を marker false にする。`src not in {observed, manual, attested}` は undecidable。中期には TEST-001 の structured execution でまとめて置換する。

### TEST-002 / FRESH-3 — B1 が crash mutant を「テストに殺された」と数える

**Severity: High / confidence: high / known-confirmed / partial reproduction**

構文検査は parse 可否だけを見る。

```bash
python3 -c 'import importlib.util,pathlib; p=pathlib.Path("scripts/run-test-strength-drill.py"); s=importlib.util.spec_from_file_location("drill",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); samples=["raise RuntimeError(\"mutant crash\")","if 1/0:\n    pass"]; [print(repr(x), "parses=", m._parses("sample.py", x)) for x in samples]'
```

```text
'raise RuntimeError("mutant crash")' parses= True
'if 1/0:\n    pass' parses= True
```

`run-test-strength-drill.py:645-649` は mutation run の outcome が `failed` なら理由を区別せず `caught` を返す。したがって import/collection/runtime crash でも「assertion が mutant の意味変化を検出した」ことにできる。SF-014 の non-run probe は positive marker で狭まったが、semantic mutant quality はまだ証明されない。

今回、実リポジトリを書き換える full drill は read-only 方針により行っていないため、ラベルは partial reproduction とする。ただし parser 結果と decisive branch は現行 source で直結しており、到達確度は高い。

**修正方針**: pytest adapter では collection error / internal error / setup error を `inconclusive` にし、少なくとも1件の test report が生成され、mutantごとに test-phase failure が出た場合だけ caught と数える。mutant operator は「実行時即死」ではなく、return/condition/operator の意味変化を優先する。

### SF-011 — frontmatter terminator parity drift

**Severity: Low / known-confirmed / source**

現行 `hooks/lib/frontmatter.sh:24-27` は終端 `^---[[:space:]]*$`、`scripts/check_status.py:255-259` は strict `\n---\n`。途中の `--- ` 後に `task_size: S`、さらに strict delimiter を置くと Python は S を frontmatter として読み、Bash は前方で閉じる。既知の gate deny、snapshot tamper audit、strict contract の3層 containment は維持されている。

**裁定**: accepted residual のままでも直ちに危険ではないが、二重 parser の drift は再発源。修正費用が小さいため P1 で strict delimiter に統一し parity fixture を加える。

### SF-013 — sed range と symlink evidence ref

**Severity: Low / known-confirmed / source**

現行 writer は canonical STATUS shape を前提に current_refs の更新範囲を閉じ、`--ref` の存在確認は symlink を辿る。通常 writer が作る STATUS では top-level key が後続するため sed 越境は contained、ref は非実行ポインタなので即時 moat bypass ではない。

**裁定**: 緊急性はない。ただし frontmatter 境界で必ず止める構造化更新と、`realpath` の repo containment は小さな hardening。TEST-001/MOAT-001 より先に扱わない。

### SF-015 — all-xfail false-negative

**Severity: Low / known-confirmed / reproduced**

```bash
printf '%s\n' \
  'platform darwin -- Python 3.9.6' 'rootdir: /tmp' 'collected 1 item' \
  '=== 1 xfailed in 0.01s ===' \
| bash -c 'source "$1"; printf "verdict="; aegis_marker_verdict 0 "pytest -q"; printf "\n"' \
  _ hooks/lib/marker.sh
```

```text
verdict=false
```

実行済み body を過小評価する false-negative であり、安全側。output regex をさらに広げるより、structured pytest report へ移す際に xfailed/xpassed の意味論を定義する。

### SF-016 — C locale の Unicode whitespace narrowing

**Severity: Info / accepted residual / revalidated**

```text
hook output: {}
bash: rm -rf: command not found
shell_rc=127
```

NBSP 区切りの raw text は hook で allow になるが、Bash は NBSP を IFS separator として扱わず、`rm -rf` 全体を存在しない command name とする。ASCII space/tab を使う runnable command は C locale でも検出対象。accepted residual は妥当で、Unicode matcher の再拡張は不要。

### LOCALE-001 — iter72/73 byte hardening

**Severity: Info / closed / revalidated**

UTF-8 locale を親に置き、出力末尾へ `0xFF` を混ぜて再攻撃した。

```text
pytest forged pass + collected 0 items\xff -> verdict=false
unittest Ran 1 + OK(skipped=1)\xff     -> verdict=false
```

`marker.sh:69-82` の function-local `LC_ALL=C` が Stage 4/5 全体に効いており、F-CRIT-1 の false-green は閉じている。iter73 の deny hooks も command 抽出後に C locale を固定するため、不正 byte で `tr` が落ちるクラスを狭く閉じる。今回、同じ invalid-byte クラスの新しい false-green は発見しなかった。

### NORTH-001 — L0 が再び「薄い司令塔」ではなくなっている

**Severity: Medium / known-confirmed / reproduced metrics**

| 対象 | words | bytes |
|---|---:|---:|
| `CLAUDE.md` | 650 | 5,227 |
| `.claude/rules` 合計 | 497 | 3,801 |
| `docs/STATUS.md` (HEAD) | 1,445 | 22,752 |
| `docs/LEARNINGS.md` | 7,593 | 138,732 |
| `docs/security-followups.md` | 4,799 | 77,734 |

CLAUDE.md は budget 上限650 wordsに達し、余白がない。STATUS は前回レビュー時1123 wordsから約29%増え、現在は CLAUDE+rules 全体より長い。iter73 の rationale が frontmatter 1 scalar に巨大なレビュー履歴を持つため、毎回読む L0 の役割と矛盾する。

テスト1306件、production shell/python 約12k LOC、test 約22k LOC は安心材料である一方、one-person framework では変更時に理解すべき mechanism 数を増やす。次の iteration は capability 追加より **claim・状態・証拠経路の削減**に使うべきである。

### DIST-001 — official hands-on が setup 直後に失敗する

**Severity: Medium / new / source-confirmed**

`bin/setup.sh:547-621` は fresh target を `git init` し、framework baseline commit を1件作る。`tests/test_setup_baseline.py` もこの契約を固定している。一方 `docs/onboarding/01-hands-on-reservation.md:36-44` は setup の直後に `git init && git add -A && git commit -m scaffold` を「必須」とする。fresh setup が成功した場合、2回目 commit は通常 `nothing to commit` で rc 1 になり、最初の体験を壊す。

**修正**: hands-on の再初期化を削除し、「setup が baseline commit を作ったことを `git log -1` で確認」に変える。baseline を望まない利用者向けに installer へ `--no-baseline-commit` を足すなら、その時だけ手動 init を案内する。

### DIST-002 — onboarding の deploy n/a は実装契約と矛盾する

**Severity: Medium / known-confirmed / source**

`01-hands-on-reservation.md:167-172` と `03-cheatsheet.md:52` は小タスクの `deploy na` を案内する。しかし `scripts/check_status.py:1165-1177` は n/a を brainstorm/plan だけに限定し、deploy を必ず拒否する。前回 R9 から残っている。

同 cheatsheet の「規模Sなら second opinion 無しを ack 可」も、参照する state-machine 規約が機械契約として確認できない。official golden path を機械が拒否する状態は、個別 hook の高度さより North Star を傷つける。

**修正**: policy を一つ選ぶ。推奨は checker を正本とし、deploy は `approved` または `pending`、n/a 不可として docs を直す。S second-opinion 省略も実際の checker contract に合わせる。

### DIST-003 — installer の preview と profile provenance が不足

**Severity: Low / known-confirmed / reproduced/source**

```text
$ bash bin/setup.sh --dry-run
ERROR: Unknown argument: --dry-run
```

setup は copy、settings生成、git init、baseline commit を行うが preview がない。`.claude/.aegis-install-version` は version 1行のみで、どの profile から生成したかを残さない。full→standard 等の再実行で hook set が変わっても、利用者と doctor が意図的な profile switch かを判定できない。

**修正**: `--dry-run` で write/commit 予定を列挙し、stamp を version/profile/install-time の小さなJSONへ移行する。uninstall は profile provenance と installed path manifest が整ってから検討し、先に作らない。

## 4. 過去 R1〜R10 の再点検

| 前回 | 現在の裁定 | 根拠・残余 |
|---|---|---|
| R1 three-layer accident prevention | **改善維持** | checkout/restore/stash/force pattern、snapshot regression guard、OS lock が現存。ただし MOAT-001 の shell lexical view が新たな同クラス穴 |
| R2 S size bypass | **改善維持** | task_size snapshot/tamper と size-aware gate tests が現存 |
| R3 setup vs cp-lock | **改善維持** | `selfheal_unlock_target` と stamp+actual-lock 二条件が現存 |
| R4 test-strength/evidence | **部分改善** | no-run、positive marker、count、fingerprint は維持。TEST-001/002 が本質残余 |
| R5 model/agent policy | **新しい回帰なし** | local manifest/agent contract に新たな不整合は今回検出せず。外部モデル優劣の再評価は本レビュー範囲外 |
| R6 trust/fingerprint/atomicity | **改善維持** | tree-aware fingerprint、trust scan、atomic ref/since validation が現存 |
| R7 approval/evidence binding | **部分改善** | ref existence と completion-time check はあるが、証拠内容の execution provenance は TEST-001 により不足 |
| R8 L0 context budget | **未解決・悪化** | NORTH-001。STATUS +29%、CLAUDE.md は上限到達 |
| R9 guidance contradictions | **未解決** | DIST-001/002。official hands-on と checker が不一致 |
| R10 distribution | **部分改善** | baseline commit、upgrade self-heal は改善。dry-run/profile provenance は未解決 |

## 5. 次の進化案

### 選択肢 A — regex と denylist を追加し続ける

最小差分だが非推奨。quote-concatenation の別表記、runner summary の別表記、未知 runner を追い続ける。今回の2 Criticalはいずれも「raw textを意味の代理にする」構造から生じ、個別 regex では終わらない。

### 選択肢 B — 構造化 argv + attested runner へ狭く移行する（推奨）

moat は conservative lexer が作る argv view、test は Aegis-controlled runner が作る structured event を正本にする。まず Aegis 自身の pytest だけを強くし、他 runner は output-based yellow を維持する。全 ecosystem 対応を一度に作らないため、North Star と両立する。

### 選択肢 C — sandbox、署名 daemon、CI service まで作る

現時点では過剰。single-user local framework で同一ユーザーが signer/key を読めるなら、暗号署名だけでは trust boundary が増えない。外部CIを必須化すると offline/速度/導入容易性を損なう。B の bypass が実証された時だけ再評価する。

## 6. 推奨実装プラン

### Phase 0 — claim と golden path を正す（P0、S、1 iteration）

1. `hooks/check-destructive.sh`、`hooks/check-secrets.sh`、`hooks/lib/patterns.sh`
   - raw command に加え、conservative token view を生成する共通 helper を導入。
   - quote-concatenation、escaped token、`&&`/`;`/pipe の各 segment を fixture 化。
   - parse不能時は destructive=ask、secret=deny。
   - acceptance: 本書の `r""m` / `g""it a""dd .e""nv` が block/ask。通常の quoted path は誤拒否しない。

2. `hooks/lib/marker.sh`、`scripts/build-judge-card.py`
   - exit 0 と failed count > 0 の矛盾を false。
   - `src` を明示 allowlist 化。
   - UI/docs の現行 green を「output-consistent」に改称し、execution-attested と混同しない。
   - acceptance: `pytest -q; true` は green 不可。unknown src は unverified。

3. `docs/onboarding/01-hands-on-reservation.md`、`03-cheatsheet.md`
   - setup 後の重複 git commit、deploy n/a、S second-opinion 記述を実 contract に一致させる。
   - docs の全 command を順番に実行する1本の golden-path integration test を追加。

4. `docs/STATUS.md`
   - task_size_rationale を5行以内へ縮小し、長い実証履歴は既存 qa/security report への pointer にする。
   - acceptance: STATUS <= 700 words、CLAUDE.md <= 600 words を新 budget とする。

### Phase 1 — pytest execution attestation（P0、M、1–2 iterations）

1. `scripts/run-tests-attested.py`（新規）と最小 pytest plugin を追加。
   - shell string ではなく argv list を spawn。
   - pytest report hook から `collected/executed/passed/failed/skipped/xfailed/xpassed/collection_errors/exit_code` を生成。
   - worktree fingerprint、runner/version、開始/終了時刻、schema version を一つの event に記録。
   - `executed >= 1 && failed == 0 && collection_errors == 0 && exit_code == 0` の時だけ `src=attested` green。

2. `hooks/lib/evidence.sh`、`scripts/build-judge-card.py`
   - observed output は診断用。gate-deciding green は `src=attested` のみにする。
   - 互換 runner は yellow のまま ack 可能とし、突然全利用者を block しない。
   - event は current fingerprint と完全一致し、古い schema/未知 field combination は unverified。

3. 必須攻撃テスト
   - fake pytest output、`pytest-not-installed || printf`、`pytest; true`、all-skip、all-xfail、collection error、test-body runtime error、invalid byte、truncated output、stale fingerprint。
   - acceptance: fake output は event を作れず、通常 pytest pass/fail/xfail は structured count どおり。

### Phase 2 — B1 を同じ truth source に統合（P1、M）

1. `scripts/run-test-strength-drill.py`
   - baseline/mutant run を attested pytest adapter 経由へ。
   - collection/import/internal/setup error は `inconclusive`。
   - test-phase failure があり、実行件数が1以上の mutant だけ caught。

2. mutant quality
   - `raise RuntimeError`、import-time zero division 等の即死 mutant を reject。
   - condition/operator/return-value の semantic operator を優先。
   - report に mutant種別、実行tests、failure phase を残す。

3. acceptance
   - 本書の crash mutant だけでは drill PASS にならない。
   - assertionが意味変化を検出した mutant は PASS。
   - restore byte verification と atomic safety は既存契約を維持。

### Phase 3 — installer と配布を整える（P1、S/M）

1. `bin/setup.sh`
   - `--dry-run`、`--no-baseline-commit`。
   - dry-run は copied/overwritten/removed/settings/hooks/git action を列挙し、write 0件。

2. install metadata
   - stamp を version/profile/schema のJSONへ移行し、旧1行 stamp は read-compatible。
   - profile switch 時に「追加・上書き・無効化される hook」を明示。

3. fresh Codex onboarding
   - README 冒頭に 5分の path: dry-run → isolated install → baseline確認 → attested pytest → judge。
   - plugin化や marketplace 配布は、この path が新規利用者テストで成功してから。

## 7. 優先順位と完了条件

| 優先 | 項目 | 見積り | 完了条件 |
|---|---|---:|---|
| P0-1 | MOAT lexical normalization | S/M | quote-concat攻撃が deny/ask、既存正常commandの回帰なし |
| P0-2 | washed-green/src allowlist | S | 現行再現2件が green 不可 |
| P0-3 | onboarding + L0縮小 | S | official golden path E2E成功、STATUS <=700 words |
| P0-4 | pytest attested event | M | fake output不可、real pytestのみ decisive green |
| P1-1 | B1 event統合 | M | crash/collection errorが caught 不可 |
| P1-2 | installer dry-run/profile metadata | S/M | preview write 0、profile差分可視化 |
| P2 | 他 runner adapter | demand-based | 実利用のある runnerから1つずつ追加 |

次 release の ship 条件は「1306 tests green」だけでは足りない。本書の raw repro を回帰テストへ変換し、**旧実装では赤、新実装で緑**を示すこと。特に MOAT-001 と TEST-001 は severity を下げず、P0 完了まで framework claim の更新を止める。

## 8. 意図的に追わないもの

- Bash 全文法 parser の自作。
- 全 test ecosystem の同時 adapter 実装。
- 同一ユーザー権限内だけで完結する署名/秘密鍵による擬似 attestation。
- vector memory、swarm、多人数承認、常設外部CIなど North Star 外の capability。
- Unicode whitespace matcher の再拡張（SF-016 は非 exploitable）。
- SF-013 のような Low hardening を Critical 2件より先に処理。
- test数を増やすこと自体を目標にすること。各追加testは claim/risk/finding ID に紐付ける。

## 9. 最終評価

Aegis は「弱い」のではない。OS-lock、snapshot、fingerprint、atomic writer、byte-wise marker、1306件の検査は、過去の失敗をかなり丁寧に機械化している。問題は、その強さを支える最終2入力がまだ **raw shell text** と **raw test output** であることだ。この境界だけが、周囲の精密さに比べて意味論的に弱い。

したがって次の進化は機能追加ではなく、次の一本化である。

> **危険操作は argv で判断し、テスト事実は実行イベントで判断する。文字列は説明には使うが、真実の決定には使わない。**

これを pytest と2本の moat hookに狭く実装し、同時に onboarding と L0 を縮めれば、Aegis は防御力だけでなく、一人で理解・修正・配布できる framework として一段進化する。

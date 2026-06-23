# Security Follow-ups（未消化のセキュリティ課題・durable）

> 後で必ず潰すと決めた未対応のセキュリティ課題を、消えない形で残すトラッカー。
> per-iteration の qa-reports と違い、解決まで root に残す。解決したら「状態」を
> CLOSED にし、対応コミット/ゲートを記す。

## OPEN

### SF-001: control-plane フックのクォート/エスケープ トークン分割バイパス（Critical・pre-existing）

- **発見**: iteration 31 / Batch1 review ゲートの盲検 break-attempt レビュー（reviewer ＋ reviewer-maintainability が独立に検出）。2026-06-16。
- **種別**: **pre-existing**（変更前 8f8eb2d でも同一挙動＝allow を実測確認。Batch1 が導入した後退では**ない**。Batch1 の orig-vs-new 比較は control-plane 書込みで後退ゼロ）。
- **重大度**: Critical（フル moat 崩壊。非 framework タスクのエージェントが control-plane ファイルへ任意内容を書ける）。
- **再現（task_type=feature の install で `{}`=allow になる。非分割形は全て deny）**:
  ```
  cp safe.txt hooks""/lib/emit.sh            # 空クォートで hooks を分割
  cp safe.txt "ho""oks/lib/emit.sh"          # 隣接クォート連結
  cp safe.txt 'hoo'ks/lib/emit.sh            # シングルクォート
  cp safe.txt hooks"/"lib/emit.sh            # スラッシュを分割
  cp safe.txt hooks\/lib/emit.sh             # バックスラッシュ エスケープ
  echo evil > "hoo""ks/lib/emit.sh"          # リダイレクト形（チェック b も回避）
  cp evil "STAT"US.md                        # STATUS.md / CLAUDE.md / .claude/ も同様
  echo x | xargs -I{} cp {} "hoo"ks/lib/emit.sh
  find . -name x -exec cp {} "hoo"ks/lib/emit.sh \;
  # 同クラス（trailing-slash 無しの bare ディレクトリ operand。CP 正規表現は `hooks/` を要求するため bare `hooks` を取りこぼす）:
  find hooks -type f -exec rm {} +            # hooks/ 配下を削除（find hooks/ は deny）
  rm -rf hooks                                # rm -rf hooks/ は deny
  cp evil hooks                              # ディレクトリ hooks へコピー
  ```
- **根本原因**: `hooks/check-control-plane.sh` の判定（正規表現＋`mask_quoted` のクォート span マスク）は、シェルの**クォート除去＋隣接トークン連結＋パス解決**（word splitting）を再現していない。判定は**リテラル `hooks/`|`scripts/`|… 部分文字列**に一致するだけなので、シェルが control-plane パスに解決するが当該リテラルを含まない全ての形を取りこぼす: クォート分割（`hooks""/`）・バックスラッシュ（`hooks\/`）・**trailing-slash 無しの bare operand（`find hooks`/`rm -rf hooks`/`cp x hooks`）**。`hooks""/lib` はシェルでは語 `hooks/lib` だが生にもマスク後にもリテラル `hooks/` が無く一致しない。
- **iteration 31 security ゲートでの確認**: 1 次（security エージェント）＋盲検 2 次が独立に、上記全形を orig(8f8eb2d) vs new HEAD で実走し **両者とも allow＝完全に pre-existing**（Batch1 後退ゼロ）と確認。security skill の deploy blocker 列挙（auth bypass/default creds/hardcoded secret/HTTPS）には非該当のため **deploy blocker ではなく Critical 残存リスク**として繰延承認。
- **なぜ安易に直せないか**: 「クォート除去＋連結」を素朴に適用すると、`git commit -m "update STATUS.md handling"` のような**クォート内メッセージ救済（OBS-006）を再び壊す**（語の値に `STATUS.md` 部分文字列が現れる）。正しくは「シェル忠実なトークン化 → 各語をクォート除去して**語の値**を得る → その語が**書込み先**の control-plane パスか判定」。重い新プリミティブで、セキュリティ境界ゆえ独立した設計＋TDD＋盲検レビューが必要。
- **修正方針（暫定・非確定）**: コマンドを語単位にトークン化（python の `shlex` 等＝抽出と同様に python 優先＋bash fail-closed フォールバック）し、各語の literal value を再構成してから control-plane 判定。リダイレクト先・write コマンドの宛先語に限定して deny。`git commit -m`/`echo`/`printf` のメッセージ語は「語全体がパスでない」ため救済を維持。
- **状態**: **FIX IMPLEMENTED（review/qa/security ゲート＋push は未／ユーザー判断待ち）**。iteration 32 で path-resolution augment（shlex トークン化→各語を解決→control-plane write-target 判定）を実装し、盲検 break-attempt と pre-QA review を反復して**静的難読化クラスを網羅的に閉鎖**。修正計画＝`docs/plans/2026-06-18-sf-001-cp-token-bypass-implementation-plan.md`、設計＝`docs/specs/2026-06-18-sf-001-cp-token-bypass-design.md`。
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。
- **iteration 32 の閉鎖ラウンド（2026-06-20・各 TDD RED→GREEN・未 push）**:
  - F-1〜F-6: 絶対パス／ANSI-C／cmdsub・$VAR write-target／param-default／brace（commits 〜`1644cd3`）
  - round5（`3c98666`）: tilde-plus `~+`＝PWD・`~-`＝OLDPWD→ask・入れ子 `${X:-${Y:-hooks}}` の fixpoint 解決
  - round6: 展開分割（`h${X:-ooks}`/`{h,x}ooks`）・bare `.claude` 末尾
  - round7: bare special-param（`$0`-`$9`/`$$`/`$?`/`$#`/`$!`/`$-`/`$*`/`$@`）→ask
  - round8（`29caac6`）: glob/wildcard/char-class（= 旧 SF-002）を fnmatch 静的照合で deny
  - round8b＋round9（`4c65229`）: glob×空展開 `ho${E}ok?`（fail-open）／write-redirect 演算子族 `&>` `&>>` `>|` `>&` `<>`・fd 付 `1>|`
  - round10（`a9168fd`）: 多群/入れ子 brace cross-product `{h,x}{ooks,uild}`/`{hoo{ks,X},build}`・`opt=PATH`/`dd of=PATH` 書込み先
  - round11（`623201f`）: brace SEQUENCE `{a..z}`/`{0..9}`（`hook{s..s}`=hooks）・`mapfile`/`readarray` array path→ask・brace 展開 DoS cap
- **検証**: token-split 195 passed / full suite 1025 passed・1 skip / contract・drift・mirror PASS。盲検 break-attempt（security エージェント）×3＋pre-QA reviewer×2 が各ラウンドの新クラスを検出→fix-forward（agent は infra で stall 散発・部分結果を活用）。
- **網羅性の自己検証（2026-06-20）**: exec-redirect/eval/process-sub/here-string/install/ln/link/sed -i/git config -f/truncate/mv -t・cp -t/mkdir/fd-redirect/extglob `@(hooks)` を実走→**全て DENY/ASK**。残る静的形は extglob の名前分割形（SF-005）と interpreter コード（SF-004）のみ。
- **残課題**: SF-003（cmdsub 内 CP 名）・**SF-004（interpreter コード＝原理的限界・実証済み）**・**SF-005（extglob 条件付き）**。**最終結論**: 実用的なシェル難読化は閉鎖したが、静的コマンド解析は SF-004 で原理的に不完全＝moat は「敷居を上げる層」であり sandbox ではない。ロバスト化は OS/FS レベルの防御（下記）を別途検討。

### SF-002: control-plane フックの glob メタ文字 bare-dir バイパス（High・pre-existing）

- **発見**: iteration 32 / SF-001 修正計画の grill-plan（自己グリル）。2026-06-18。
- **種別**: **pre-existing**（SF-001 と同じく既存 moat も素通り。SF-001 修正でも**意図的にスコープ外**）。
- **重大度**: High（bare-dir 破壊と同等の効果。`rm -rf hooks*` で hooks/ を削除可能）。
- **再現（task_type=feature で allow になる）**:
  ```
  rm -rf hooks*        # 末尾 glob。語が厳密 `hooks` でも `hooks/` でもない
  rm -rf hook?         # ? glob
  rm -rf [h]ooks       # 文字クラス glob
  cp evil scripts*     # 同クラス
  ```
- **根本原因**: control-plane 判定（SF-001 の token-aware augment 後も）は語の literal value で CP を判定する。glob メタ文字（`* ? [`）を含む語はシェルが実行時にファイル名展開して CP パスに解決するが、判定時点の語は `hooks*` 等で、`CONTROL_PLANE` 正規表現にも bare-name 厳密一致にも当たらない。shlex も glob を展開しない。
- **修正方針（暫定・非確定）**: bare-name 検出の右境界に glob メタ文字（`*?[`）を許容するか、glob を含む CP 接頭辞語を fail-closed 扱いにする。SF-001 と同じくセキュリティ境界ゆえ独立 TDD＋盲検が要る。
- **状態**: **FIX IMPLEMENTED（round8 `29caac6`・gate/push 未）**。GATE に `?`/`*`/`[` を追加し resolver で各 path component を CP 絶対パス集合へ component-wise prefix-fnmatch 照合（位置を尊重: `build/*` は非CP、bare `*`/`*/lib` は hooks 配下）→ write=deny / read=carve-out で allow。brace-sequence 形（`hook{s..s}`）は round11 で別途閉鎖。
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。
- **重要な是正**: 本件を当初「glob＝runtime 値依存の原理的限界」と記録しかけたが**誤り**。glob は cmdsub/$VAR と違い実行時状態に依存せず、既知 CP 名に `fnmatch` で**静的に**照合でき閉じられる。「原理的限界は実証してから言う」の原則どおり、glob は実証の結果 closable と判明した（真の原理的限界は SF-004）。

### SF-003: CP ディレクトリ名が不透明な cmdsub の中に消える残余（Low・accepted residual）

- **発見**: iteration 32 / SF-001 review round3 の break-attempt ＋ ユーザー指摘による再検証。2026-06-18。
- **種別**: **accepted residual**（静的解析の本質的限界・moat の脅威モデル外の意図的難読化）。
- **重大度**: Low（accidental 書込みでは発生しない。実用上の現実的攻撃は SF-001 の F-4 修正で閉鎖済み）。
- **再現（task_type=feature で allow になる唯一の cmdsub 形）**:
  ```
  rm -rf $(echo hooks)/lib       # CP 名 hooks が不透明な cmdsub の中
  rm -rf $(printf hooks)/x       # 同型
  rm -rf $(cat file_with_hooks)  # CP 名が外部データ由来でコマンド文字列に無い
  ```
- **根本原因**: SF-001 の F-4 修正は cmdsub/$VAR を sentinel 化して「未知前置＋残る CP 名」を ask で捕捉するが、CP **名自体が cmdsub の内部に入る**形は sentinel が名前ごと飲み込むため検出できない。cmdsub を実行しない限り出力（=CP 名）を静的に復元できない。
- **なぜ accept するか**: (1) accidental/casual な書込み（moat の主目的）では発生しない＝`$(echo hooks)` を書く者は `hooks` を直接書ける（それは捕捉される）。(2) 任意の静的 moat が同じ限界を持つ。(3) 敵対エージェントは base64/eval 等で無限に回避でき、静的 moat はサンドボックスではない。完全動的解決を求めるのは YAGNI。
- **状態**: **OPEN（accepted residual・記録のみ）**。現実的 cmdsub ベクタ（`$(pwd)/hooks` 等）は SF-001 F-4 で閉鎖済み。
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。

### SF-004: interpreter `-c`/`-e` の runtime 構築パス（**原理的限界・実証済み**・accepted residual）

- **発見**: iteration 32 / SF-001 閉鎖後の網羅性自己検証。2026-06-20。
- **種別**: **fundamental limit**（静的コマンド解析では原理的に閉じられない。実証済み）。
- **重大度**: 中（敵対的な意図が必要。accidental では発生しない）。
- **再現（task_type=feature で `{}`=allow＝実 CP write）**:
  ```
  python3 -c "open('hook'+chr(115)+'/x','w')"             # 'hook'+chr(115) = 'hooks'
  perl -e "open(F,'>','hook'.'s'.'/x')"
  bash -c "rm -rf hook${x}s"
  node -e "require('fs').writeFileSync('hook'+'s'+'/x','y')"
  ```
  リテラル形（`python3 -c "open('hooks/x','w')"`）は上流の literal 一致で **DENY**。runtime 構築形のみ漏れる。
- **根本原因**: `python3 -c`/`perl -e`/`bash -c`/`node -e` は任意言語のコードを実行し、CP パスを**実行時に**文字列構築する。これを静的に検出するには当該 interpreter 言語をパースまたは実行するしかなく、不可能。全ての `python3 -c`/`bash -c` を ASK にすれば通常の開発が破綻するため、bare interpreter 呼び出しは意図的に flag しない設計。
- **なぜ accept するか**: (1) 静的コマンド解析の**原理的限界**（任意コード実行は静的に不透明）。(2) 敵対エージェントは base64/eval/外部スクリプト等でも無限に回避でき、moat は sandbox ではない。(3) これを閉じるには moat の外＝OS/FS レベルの防御が必要。
- **状態**: **OPEN（accepted residual／原理的限界）**。→ 下記「防御の多層化」提言を参照。
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。

### SF-005: extglob `@()`/`!()`/`+()` の名前分割形（条件付き・Low・記録のみ）

- **発見**: iteration 32 / 網羅性自己検証。2026-06-20。
- **種別**: 条件付き residual（`shopt -s extglob` が有効な場合のみ展開。bash 既定は OFF）。
- **重大度**: Low（条件付き＋稀。`rm -rf` 形は check-destructive フックでも部分カバー）。
- **再現（extglob 有効時に CP へ展開・hook は allow）**:
  ```
  rm -rf @(hook)s     # @(hook) が 'hook' にマッチ → 'hooks'（shlex が () を分割し hook|s に割れる）
  rm -rf !(zzz)       # zzz 以外すべて＝hooks を含む
  rm -rf +(hook)s
  ```
  リテラル名を含む `@(hooks)` は shlex が `hooks` を素の語として露出させ **DENY**。
- **根本原因**: shlex が `()` を句読点として分割するため extglob 内の語が CP 名に再結合されない。`!()` は「マッチしない」意味論で静的解析が困難。
- **修正方針（非確定）**: extglob 構文 `[?*+@!](` を検出して書込み文脈なら保守的 ASK。ただし条件付き＋稀＋ブラントなので、SF-004 と併せて OS/FS 防御で一括カバーする方が筋が良い。
- **状態**: **OPEN（条件付き residual・記録のみ）**。
- **状態（2026-06-21 更新）**: iteration 35 で layer-2 OS lock を defense-in-depth として
  追加。lock がアクティブな間（POSIX/macOS の project モード）は本形の**事故**書込みが
  syscall で EACCES（test_cp_lock_sf_catalog.py で実証）＝多層保険で軽減。ただし**敵対者は
  `os.chmod` で解錠してから書けるため本項目は CLOSED にしない**（特に SF-004 は静的・OS
  どちらでも敵対閉鎖は原理的に不可）。Windows ネイティブは layer-2 no-op＝layer-1 のみ。

### SF-006: tamper-evidence の非対称（gate改竄検知の fail-open＋task_type/task_size 無監査・Medium）

- **発見**: 2026-06-24 全力レビュー統合（多エージェント敵対レビュー＋ユーザーレビュー P1-A/P2-B）。全件一次資料で裏取り。詳細＝`docs/full-review-2026-06-24-hooks-gates-distribution.md`（I1/I2/I3）。
- **種別**: 整合性の**非対称/網羅性**の穴。SF-001 系（moat＝事故防止・敵対受容）とは別レイヤ＝**gate の偽造不能性**（人間承認が agent に偽造されない、というより強い性質）の側道。
- **重大度**: Medium。理由の較正＝下記。Critical 扱いはしない（脅威モデル準拠）。
- **構成する 3 点**:
  - **I1（gate改竄検知が fail-open）**: `hooks/post-status-audit.sh:26-29` は他 deny hook と違い `AEGIS_SAFETY_FALLBACK` 無しで lib を直接 source。`docs/hook-failure-policy.md:27` で advisory・python3 不在時 allow と宣言。gate/mode tamper 検知は bash のみ（python3 不要）なのに、lib source 失敗/python3 不在で監査ごとスキップ。
  - **I2（完了evidence が fail-open）**: `scripts/check_status.py:1484-1497`。STATUS.md 不在/frontmatter 不正で `violations=[]`→exit 0。`validate_status_file` は同条件 fail-closed＝非対称。
  - **I3（task_type/task_size 無監査）**: `hooks/post-status-audit.sh:89-139` は gate/phase/mode のみ監査。task_type は docs/* 無条件 allow（`check-gate.sh:80-85`）で自由 Edit 可。`:61-64` の `aegis_cp_apply` が task_type 変更で layer-2 を張り替えるため `task_type: feature→framework` の単一 Edit で layer-1+2 が同時解錠。`task_size: L→S` は必須 gate を skip させる。
- **再現（task_type=feature の install で）**:
  ```
  # I3: STATUS.md の task_type を framework へ Edit → post-status-audit は {} (allow・無監査)
  #     → 直後の hooks/check-gate.sh 編集も {} (allow)。control-plane 編集が成立。
  # I1: python3 を PATH から外す or lib を壊す → post-status-audit が gate 改竄を検知できない。
  # I2: docs/STATUS.md を削除/破損 → TaskCompleted の完了evidence 検査が PASS。
  ```
- **根本原因（RC-1）**: STATUS.md がセキュリティ制御面（task_type/task_size/mode/gates）と自由編集ドキュメントを兼ねる。間に立つ `post-status-audit` が (i) task_type/task_size を監査せず、(ii) 自身 fail-open。gate-advancement は tamper-evident にしたのに、gate 要件と moat を制御する switch は無監査＝強い性質に側道。
- **較正（重要・過大評価を避ける）**: I3 は**新規の敵対的 moat 破綻ではない**。事故では task_type を書き換えない（moat の事故防止目的は無傷）。敵対経路としては SF-004 の os.chmod 解錠と同クラスで**受容済み**。正当な残課題は「tamper-evidence の網羅性/非対称」であって「フル moat 崩壊」ではない。
- **修正方針（暫定・非確定）**: I1＝post-status-audit に safety fallback を足し gate/mode/task_type tamper 検知を fail-closed 化（python3 依存の phase-transition 検査部のみ advisory 維持）。I2＝STATUS 不在/None-frontmatter を violation 化。I3＝task_type/task_size を tamper 検知対象に追加（authorized-path 経由のみ変更可）。I1 が I3 の前提（fail-open のままでは I3 監査もスキップされる）。**check-control-plane の再設計は不要。**
- **状態**: **PARTIALLY ADDRESSED（iteration 41 Batch 1 で I1/I2 対処済・I3 は OPEN）**。
  - **I1（fail-open）= 対処済**: `hooks/post-status-audit.sh` に PostToolUse 用 fail-closed fallback（`AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN/END`）＋`safety.sh` の `aegis_require_lib_block` を追加。lib source 失敗で `{"decision":"block"}` を emit＝gate/mode tamper 検知（bash のみ）が lib 欠落で skip されない。phase-transition の python3 依存部は現挙動維持（最小変更）。テスト: `tests/test_post_status_audit_fail_closed.py`。
  - **I2（完了evidence fail-open）= 対処済**: `scripts/check_status.py` の `--check-completion-evidence` で STATUS 不在 / frontmatter None を violation（exit 1）化＝`validate_status_file` と対称。テスト: `tests/test_completion_evidence_fail_closed.py`。
  - **I3（task_type/task_size 無監査）= OPEN（Batch 2）**: post-status-audit に task_type/task_size の tamper 検知を追加する。I1（fail-closed 化）が前提＝達成済なので Batch 2 で着手可能。
  - 関連配布修正（同 iteration・SF ではないが文脈）: standard profile が judge builder / Task 完了強制 hook を欠いていた（gate 承認不能・completion 強制不発）＝D1/D2 で是正。再 install で framework 所有ファイルが `.bak` つきで上書きされるよう変更（D3）＝security 修正が既存ユーザーに届く。

---

## 防御の多層化（提言・2026-06-20・ユーザー判断待ち）

SF-001 系の網羅的閉鎖（rounds 5-11）で**実用的なシェル難読化**はほぼ塞いだが、SF-004
（interpreter コード）が示すとおり、**静的コマンド解析による moat は原理的に不完全**。
これ以上の静的ラウンドは逓減（extglob 等の条件付き・稀な形が残るのみ）。真にロバストに
するには、コマンド文字列を解釈しない**別レイヤ**を足す:

- **案A（推奨）**: 非 framework タスク中は control-plane パスを**物理的に書込み不可**にする
  （install/フック起動時に `chmod`/ACL/`chflags uchg`（macOS immutable）等で CP を保護し、
  framework タスク開始時のみ一時解除）。コマンド形に依存せず確実。
- **案B**: PostToolUse で CP ファイルの**整合性チェック**（fingerprint 比較）→ 非 framework
  タスク中に CP が変化したら検出・revert・警告。検出ベースの事後防御。
- **案C**: エージェントの bash を権限制限ユーザー/サンドボックスで実行。
- 現行の静的 augment は「層1＝敷居を上げる」として維持（accidental＋多くの意図的難読化を
  捕捉）。案A/B を「層2＝原理的限界の補完」として追加するのが費用対効果が高い。

### 案A PoC findings（2026-06-21・throwaway spike・非 root 実走）

事故防止スコープでは案A は「層2 補完」ではなく **静的 moat の置換** が可能と実証:

- `chmod -R a-w`（CP code/dir）で、`echo>`/`cp`/`rm`/`rm -rf` に加え **`python3 -c open(w)`（SF-004 原理的限界）・`perl -e open(>)`・quote-split `> "hoo""ks/x"`（SF-001）も全て遮断**（CP file は INTACT）。OS は**コマンド文字列を解釈せず syscall で強制**＝形非依存で SF-001〜005 をまとめて閉じる（静的解析では原理的に不可能だった面）。
- uid≠root・cross-platform（`chmod`）。`chflags uchg`（macOS）は owner の `chmod +w` 後も "Operation not permitted"＝追加硬化（root 不要・macOS のみ）。`chattr +i`（Linux）は root 必要＝不採用。
- UNLOCK（`chmod -R u+w`）で framework 書込みは即復帰＝lifecycle は task_type 連動で実装可能。
- **非 sandbox（許容）**: エージェントが `chmod +w` を前置すれば書ける＝事故防止スコープでは許容（事故は chmod を前置しない）。
- **実装時の必須設計（no-go 回避）**: lock 対象は**安定 CP（hooks/*.sh・scripts/*.py・CLAUDE.md・.claude/rules・.claude/skills・templates）に限定**し、framework が実行時に書く runtime-state（`docs/STATUS.md`・`.claude/.gate-snapshot`・`evidence-log`・settings）は**除外**（さもないと framework 自身が壊れる）。re-lock は default-lock＋積極再施錠で crash 窓を縮小。
- **結論: GO**。iteration 35 で 案A を実装し、成立すれば `check-control-plane.sh`〜1000行＋SF-001〜005 を層1 ごと退役。設計: `docs/specs/2026-06-21-immutable-moat-design.md`。
- 案A は iteration 35 で layer-2（事故ケース多層保険）として実装。敵対 sandbox ではない旨を明記。

## CLOSED

（なし）

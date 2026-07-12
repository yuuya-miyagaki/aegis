# Security Follow-ups（未消化のセキュリティ課題・durable）

> 後で必ず潰すと決めた未対応のセキュリティ課題を、消えない形で残すトラッカー。
> per-iteration の qa-reports と違い、解決まで root に残す。解決したら「状態」を
> CLOSED にし、対応コミット/ゲートを記す。

## 脅威モデル（canonical）

> Aegis のセキュリティ層が**何を守り／何を守らないか**の単一正典。各 SF エントリ・
> README §95・`docs/architecture-overview.md` はこの節を参照する（重複記述は本節に集約）。

**対象とする脅威 = LLM の自己バイパス（self-bypass）**。善意だが過誤を犯しうる/
ミスリードされうるコーディングエージェントが、**自身に課されたフレームワーク規律を
事故的に（または手近な手段で）回り込む**こと。**決定論的に守る**のは path/gate サーフェス
（下記の Edit/Write・gate・commit-stage）で、**Bash の任意コマンド経路は「敷居を上げる層」**
（静的解析の原理的限界＝SF-004／決定論ではない）と切り分ける（README §95 と同じ区別）:

- **gate の改竄検知（tamper-evident）**: 人間承認ゲート（review/qa/security/deploy 等）の値は
  authorized writer（`scripts/update-gate.sh`）以外が書き換えると `.gate-snapshot` 比較で検知・
  block する。`task_type`/`task_size` も同様（iter43・`update-task.sh`）。**tamper-evidence で
  あって偽造不能の証明ではない**（chmod 権を持つ敵対者・cross-session re-bless は下記「守らない」／SF-006 較正）。
- **control-plane path の保護（Edit/Write は決定論的・Bash command は OS-lock 主体）**: フック・
  スクリプト・`CLAUDE.md`・`.claude/rules`・skills・templates への **Edit/Write は path 一致で
  決定論的に deny**（非 framework タスク中・`check-gate.sh`）。同パスへの **Bash 経由の書込みは
  iter57 で主 moat を OS-lock（`hooks/lib/cp-lock.sh`・chmod・syscall 強制・形非依存）に交代**した。
  かつての layer-1 静的解析（`check-control-plane.sh`・979行）は退役し、lock が物理的に守れない
  runtime-state（`docs/STATUS.md`・`.claude/` 設定類）の Bash 書込みだけを残余静的ガード
  `check-runtime-state.sh` が担う。**事故スコープでは OS-lock が SF-001〜005 を形非依存に構造閉鎖**
  するが、**敵対者は `os.chmod` で解錠して書ける（脅威モデル外）**点は不変＝決定論的な敵対防御ではない。
  公式サポートは macOS/Linux/WSL（Windows ネイティブは chmod が no-op＝OS-lock 無効・保護なし）。
- **事故的な secret commit の阻止**: 認証**ファイル名**（`.env`/PEM/SSH 鍵/
  credentials*.json 等）の git ステージ/コミットを block（最も高頻度な AI 事故）。
- **完了 evidence の強制**: ゲート承認・完了主張に artifact/evidence を要求（fail-closed）。

**対象としない（境界・意図的）**:

- **sandbox ではない**: 任意シェルの静的コマンド解析には原理的限界がある（SF-004 実証済）。
  Bash moat は「**敷居を上げる層（threshold-raising layer）**」であって sandbox ではない。
- **exfil 耐性ではない**: 秘密の**外部送信**（`curl -d @.env`・base64-in-commit-msg・DNS・
  PR 本文 等）は経路が無限でコマンド regex では原理的に塞げない。これを防ぐとは主張しない
  （false-assurance 回避）。秘密保護の chokepoint は「**commit/stage の阻止**」であって
  「送信の阻止」ではない。
- **content スキャナではない**: 秘密**値**が任意名ファイルに書かれる形（D2・SF-008）は
  ファイル名ゲートの対象外。
- **filesystem/chmod 権を持つ敵対者を守らない**: ディスクに直接書ける相手はフック自体を
  無効化でき（`os.chmod` で OS lock 解錠 等、SF-001/004）、静的 moat の範囲外。

要するに **Aegis は「規律の事故的回避」を決定論的に防ぐ guardrail であって、敵対的
エージェント/侵入者に対する sandbox や DLP ではない**。「限界は実証してから主張する」
方針を貫く（SF-002 の glob 再分類・SF-004 の原理的限界実証・SF-007 の bypass 不能実証が先例）。

## OPEN

> **iteration 57 状態更新（2026-07-05・SF-001〜005 一括）**: 主 moat を静的解析
> （`check-control-plane.sh`・979行）から **OS-lock（`hooks/lib/cp-lock.sh`・chmod・
> syscall 強制）に交代**し、静的層は退役した。lock がアクティブな間（POSIX/macOS の
> 非 framework モード）、**SF-001〜005 の全形（クォート分割・glob・cmdsub・interpreter
> `-c`・extglob）は syscall が形非依存に EACCES で遮断**する（`tests/test_cp_lock_sf_catalog.py`
> が grill 由来バイパス形＋新規作成＋case-fold で回帰固定）。**ただし敵対者は `os.chmod` で
> 解錠してから書けるため、いずれも CLOSED にはしない**（特に SF-004 は静的・OS どちらでも
> 敵対閉鎖は原理的に不可＝脅威モデル外）。Windows ネイティブは chmod が no-op ＝ OS-lock
> 無効（公式サポート外）。各 SF の以下「状態（2026-06-21）」の layer-1/layer-2 記述は、
> 「layer-1＝退役／layer-2＝主 moat に昇格」と読み替える。
>
> **iter57 security 盲検2次 追補（SF-009・難読化 unlock 形の後退→ASK 化）**: 退役した
> `check-control-plane.sh` は shlex トークナイザで**難読化された unlock 形**（`chmod u+w hoo\ks/…`・
> `chmod +w hooks""/…`・`"ho""oks"`・`$(echo hooks)/…`）を deny していたが、残余ガード
> `check-runtime-state.sh` の平文 `LOCKED_CP` grep はこれを取りこぼし **silent に allow** していた
> （難読化 **write** は OS-lock が形非依存に EACCES で遮断するが、難読化 **unlock** は主 moat の
> 外＝静的判定のみ）。これは「旧 deny→新 allow」の silent regression。**対処**: `_obfuscated_unlock_on_cp`
> を追加し、unlock ツール＋（バックスラッシュ/連結クォート/コマンド置換）＋正規化後に CP トークンを
> 検出したら **ASK**（fail-visible・broad recursive chmod と同格）。deny でなく ASK なのは検出が
> ヒューリスティック（パーサ非導入）ゆえ偽陽性を deny 側に倒さないため。**残余**: 深い `$()` 構築や
> 変数間接（`D=hooks; chmod +w $D`）は依然すり抜けうるが、これらは意図的難読化＝事故防止の
> 脅威モデル外（SF-004 と同じ原理的限界）。回帰固定 = `tests/test_runtime_state_hook.py::
> TestUnlockFormDeny::test_obfuscated_unlock_on_cp_asks`。

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
- **状態**: **ADDRESSED（I1/I2=iteration 41 Batch 1・I3=iteration 43）**。
  - **I1（fail-open）= 対処済**: `hooks/post-status-audit.sh` に PostToolUse 用 fail-closed fallback（`AEGIS_SAFETY_FALLBACK_POSTTOOL_BEGIN/END`）＋`safety.sh` の `aegis_require_lib_block` を追加。lib source 失敗で `{"decision":"block"}` を emit＝gate/mode tamper 検知（bash のみ）が lib 欠落で skip されない。phase-transition の python3 依存部は現挙動維持（最小変更）。テスト: `tests/test_post_status_audit_fail_closed.py`。
  - **I2（完了evidence fail-open）= 対処済**: `scripts/check_status.py` の `--check-completion-evidence` で STATUS 不在 / frontmatter None を violation（exit 1）化＝`validate_status_file` と対称。テスト: `tests/test_completion_evidence_fail_closed.py`。
  - **I3（task_type/task_size 無監査）= 対処済（iteration 43・commit `93fc166`）**: `scripts/update-task.sh`（task_type/task_size の authorized writer）＋`hooks/post-status-audit.sh` の task tamper 検知ループ（gate と同型・snapshot 取り込み）で tamper-evidence 化。`aegis_cp_apply` の moat 再施錠を tamper チェック後へ移動し、改竄編集が moat を解錠する前に block。テスト: `tests/test_update_task.py` ほか。
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

## 調査済み・非該当（NOT-A-VULN / by-design / forward-looking）

> 「セキュリティ課題か？」と提起され調査した結果、**脅威モデル内では脆弱性ではない**
> （NOT-A-VULN）・**意図的な境界**（by-design）・**現状到達不能で将来トリガ時のみ再評価**
> （forward-looking / accepted residual）のいずれかと判明した項目。CLOSED（実在した課題を
> 修正したもの）とは区別する。再調査の重複を防ぐため verdict と根拠を durable に残す。

### SF-007: gate 値パーサの bash/python 乖離（**NOT-A-VULN・実証済み**）

- **発見**: full-review 2026-06-24 の C4（`docs/full-review-2026-06-24-hooks-gates-distribution.md:69`）。gate 値を bash（`hooks/lib/frontmatter.sh` の `gate_value`＝permissive）と python（`scripts/check_status.py` の `extract_approval_map`＝strict allowlist）が別ロジックで parse し、行コメント付き値等で結果が割れる、という指摘。iteration 46 で再評価。
- **種別**: **not-a-vulnerability（実証）**。脅威モデル（self-bypass）内で gate bypass に到達する乖離が存在しないことを実測で確認。
- **重大度**: なし（脆弱性ではない）。
- **verdict（実証）**: bypass には「bash=approved/n-a ∧ python≠approved」な**到達可能**な STATUS 行が要る。だが —
  - **消費側はどちらも fail-safe**: `hooks/check-gate.sh` の plan-gate は `[ "$PLAN_GATE" = "approved" ]`/`"n/a"` の **exact-match** でしか allow せず、python は `approvals.get(key, "pending")`＝strict 正規表現に外れた値は不在→`"pending"`（not approved）。**両者が clean トークンで一致しない限り allow にならない**。
  - **混入経路が無い**: in-session の gate 値変更は `update-gate.sh`（clean enum のみ）か raw Edit（`post-status-audit.sh` が**任意**の値変化を tamper block）に限られ、divergent な値を STATUS＋snapshot 両方へ入れる clean 経路が存在しない。ディスク直編集は filesystem 権を持つ敵対者＝**脅威モデル外**（canonical 節）。
- **最小再構築キット**（第三者が 5 分で検証可能）:
  - 両パーサ: `gate_value`（`frontmatter.sh`）と `extract_approval_map`（`check_status.py:267-`）。
  - bypass 定義: bash の `gate_value` は値を**そのまま返す**（末尾空白等も保持・surrounding double-quote のみ除去）。clean トークン以外を拒否するのは**消費側**＝`check-gate.sh:174` の exact-match `[ "$PLAN_GATE" != "approved" ]` と python の `approvals.get(key, "pending")`。bypass には「**両者が同一の clean トークンで一致**」が必要で、weird 値はどちらかが必ず not-approved 方向に倒れる。
  - 検証手順: 各形を `  plan: <値>` の gate_approvals 行にした STATUS fixture を作り、`gate_value`（bash）と `extract_approval_map`（python）＋PyYAML に通して値を突き合わせる。
  - 試した 12 形の代表: `approved` / ` approved` / `approved `(末尾空白) / `approved x` / `approvedx` / `"approved"` / `'approved'` / `""approved""` / `approved#c` / `n/a` / `approved\t` / `  approved`。**bash が `approved` を返しつつ python が `approved` を返さない行は 0**。残る乖離は全て「片方が stricter＝fail-safe」方向。`""approved""`/`approved\t` は `check_status.py:865` の PyYAML cross-check でも別途検出される。一方 `"approved"`/`'approved'`（quoted）は cross-check では**検出されない**（PyYAML と strict 正規表現が一致するため）が、bash 消費側の exact-match で fail-safe（`'approved'` ≠ `approved` → not approved）かつ authorized writer は clean enum しか書かず raw Edit は tamper block＝**in-session 到達不能**。よって cross-check の死角は穴ではない（safety net は cross-check ではなく consumer の exact-match と writer/tamper 不到達）。
  - **strict 化は逆効果（C4 提案＝python の正規化に倣う場合）**: `gate_value` を「trim 後 allowlist で正規化」する python ミラー実装にすると、`post-status-audit.sh:129-130` が同関数で OLD/NEW を比較するため `approved`↔`approved `(末尾空白) を同一視し tamper を**取りこぼす**＝backstop 弱体化の net-negative。permissive のまま据え置くのが正しい（仮に「exact-match 以外は空文字」で strict 化すれば検知は維持されるが、整合の利得が無いまま分岐が増えるだけ＝やはり不要）。
- **状態**: **調査クローズ（NOT-A-VULN・コード変更なし）**。`docs/LEARNINGS.md`[tech] に二重記録。乖離を見たら「security」ではなく「同一概念の二言語実装＝maintainability」と切り分ける。

### SF-008: secret ゲートの scope（ファイル名・commit-stage 限定／**by-design**・accepted）

- **発見**: full-review 2026-06-24 の G4/M5（`docs/full-review-2026-06-24-hooks-gates-distribution.md:60`）。秘密スキャンが Bash の git add/commit のみで、Write/Edit の `.env` 直接生成・`curl -d @.env` 外部送信が無防備、という指摘。iteration 46 で再評価。
- **種別**: **by-design boundary（accepted）**。脅威モデル（canonical 節）に照らし、追加防御は不要かつ一部は原理的に不可能（exfil）と判断。
- **重大度**: Low（脅威モデル内の実害到達は限定的）。
- **判断**:
  - **`check-secrets.sh` は意図的に「認証ファイル名」ゲート**（D2 scope・`hooks/check-secrets.sh:9-13`）。content スキャナではない（秘密**値**が任意名ファイルに入る形は対象外＝canonical の「非 content スキャナ」）。
  - **Write/Edit の .env 直接生成は by-design で許容**: ローカルに `.env` を作ること自体は正常・必要（アプリ開発）。漏洩の chokepoint は **commit/stage** で、そこは既に `git add .env`/`git add .`/`git add -A` で block 済み（`check-secrets.sh:122-181`）。Write/Edit に block を足しても commit gate の重複で、正常操作に摩擦を増やすだけ。
  - **`curl -d @.env` 外部送信は防御対象としない**: exfil は経路が無限（commit メッセージへ base64・DNS・PR 本文・別名ファイル経由…）でコマンド regex では原理的に塞げず、block しても false-assurance になる。canonical 節の「非 exfil 耐性」境界そのもの。SF-004（interpreter コード）と同クラスの原理的限界。
- **早期警告の現状（誤解防止）**: **Bash 経由の `.env` 生成**（`> .env`・`cp … .env`）には `.gitignore` 保護が無ければ advisory ask する nudge が**既にある**（`check-secrets.sh:241-258`・Check 3）。未カバーは **Write/Edit ツール経由の `.env` 生成のみ**（check-secrets は Bash の PreToolUse hook なので Write/Edit には発火しない）。だがそれも commit gate（Check 2・`:189-208`／broad-stage `:127-186`）が漏洩を塞ぐため、Write/Edit 用の新 nudge は ROI 低＝今回は実装しない（YAGNI）。将来 UX 改善として検討可。なお **Check 3 は `emit_ask` の advisory であって block ではなく**、コマンドテキスト照合ゆえ難読化リダイレクト（`> "$(echo .env)"` 等）には SF-001/004 と同じ静的限界がある。**拘束力ある保証は commit/stage の block**（Check 0-2・broad-stage）＝事故的 .env commit はそこで確実に止まる。
- **状態**: **調査クローズ（by-design・accepted residual・コード変更なし）**。

### SF-009: フック入力抽出の first-path-only ＋ matcher ホワイトリスト（**forward-looking / 現状到達不能**・accepted）

- **発見**: full-review 2026-06-24 の C1（`docs/full-review-2026-06-24-hooks-gates-distribution.md:65`）＝「MultiEdit バイパスは現行 platform で不成立」という訂正 finding の**残留構造的留意点**。iteration 47 で再評価。
- **種別**: **forward-looking robustness（現状到達不能・accepted residual）**。
- **重大度**: なし（現行 platform では脅威モデル内に実害経路なし）。
- **判断**:
  - **(1) `hooks/lib/extract-input.sh:20` first-path-only**: `extract_file_path` は `grep … | head -1` で最初の `file_path`/`notebook_path` のみ抽出する。だが現行の filesystem-write built-in tool は Edit/Write/NotebookEdit で**各 1 パス/呼び出し**、複数パスを渡した旧 MultiEdit は**廃止済**。複数パス入力が生成されないため取りこぼし経路が**現状存在しない**。duplicate-key JSON（`{"file_path":"safe","file_path":"hooks/x"}`）も LLM の単一スキーマ tool 呼び出しでは生成できず脅威モデル（self-bypass）外。
  - **(2) matcher のツール名ホワイトリスト**（`scripts/platform_manifest.py` の `KNOWN_TOOL_NAMES`）: 現行 write-tool（Edit/Write/NotebookEdit）は matcher で**全カバー**＝漏れなし。新 write-tool 追加時の取りこぼしは、`stale_keys()`（`PLATFORM_VERIFIED["tool_names"]`・180 日）が再検証を催促する**既存機構**で軽減される（ただし `check_reference_drift.py` 経由の**advisory 警告であって blocking ではない**＝再検証の実施と write-tool 列挙は人手に委ねられる）。full-review の Fix 案＝再検証時に write-tool 列挙、は部分的に機械化済み。
- **やらない（YAGNI）**: 存在しない複数パス入力への防御コード追加（テスト不能・mutant を置く実行経路なし）／matcher の動的列挙（`stale_keys` と重複）。
- **状態**: **調査クローズ（forward-looking・現状到達不能・コード変更なし）**。将来トリガ＝(a) 複数パスを渡す built-in write-tool の登場（→ `extract_file_path` を全パス検査へ）(b) `stale_keys()` の tool_names 失効（→ write-tool を列挙し matcher と突合）。

### full-review 2026-06-24 backlog: triaged-complete（2026-06-26）

`docs/full-review-2026-06-24-hooks-gates-distribution.md` の全指摘を triage 完了：

- **実コード修正**: D1-D4/I1/I2（iter41）・G1-G3（iter42）・I3（iter43・→SF-006）・C5（iter44）・C2/C3（iter45）。
- **by-design / not-a-vuln / forward-looking（コード変更なし）**: C4→SF-007（NOT-A-VULN）・G4→SF-008（by-design）・C1→SF-009（forward-looking・現状到達不能）。
- 残る実コード修正タスクは**ゼロ**。今後 backlog 由来の着手は、上記 SF の「将来トリガ」が発火した時のみ。

### SF-010: task_size の empty-baseline raw-Edit が migration-grace で tamper 検知を逃れる（**OPEN**・iter65 review 検出）

- **発見**: iter65（S サイズ修復）review 1次 finder（gate 迂回）。親セッションで独立再現・CONFIRMED（旧実装 26de7f6 では両経路 deny＝この diff の回帰面）。
- **種別**: **moat 回帰（文書化済み tamper-evidence 保証の違反）**。脅威モデル節「task_type/task_size も authorized writer 以外が書き換えると .gate-snapshot 比較で検知・block」に対する empty-baseline の穴。
- **重大度**: **Medium**（iter65 security 盲検2次で Major→Medium に較正）。上げ止まり＝文書化済み tamper-evidence 保証に実在の例外を作る moat 回帰・empty-baseline は authorized フロー到達の正規状態。抑制＝**end-state（mislabel-S で plan skip）は authorized な RISK-3 経路（`update-task.sh --size S`）で既に到達可能かつ fail-visible 受容済みで、SF-010 の capability 増分は「update-task.sh の監査ログ行を省く」だけ＝新 capability を解錠しない**。加えて brainstorm ハードゲート必須・git/transcript/snapshot で完全可視・review/qa/security は下流で依然強制（skip は plan のみ）・脅威モデルは単一ユーザ dogfood の事故的自己バイパス（外部攻撃者面ではない）。発火前提つき（下記）。
- **経路**:
  - `hooks/post-status-audit.sh:210` の tamper 判定 `[ "$OLD_TF" != "$NEW_TF" ] && [ -n "$OLD_TF" ]` は、snapshot 側 task_size（OLD_TF）が**空**だと block をスキップ（migration-grace）。
  - task_size は OPTIONAL frontmatter キー＝**fresh scaffold / rollover 直後〜brainstorm Step D 前**は未設定（empty-baseline）が正規状態。この窓で `docs/STATUS.md`（docs/* ゆえ check-gate は raw-Edit を常時 allow）の frontmatter に `task_size: S` を raw-Edit で足すと、update-task.sh を通さず・tamper 検知されず S 化。
  - 以降 check-gate は task_size=S を読み brainstorm gate へ切替＝**brainstorm 承認済みなら plan 儀式を bypass**してコード編集 allow。
  - **この diff 以前は無害**（task_size 非参照）だったが、size-aware 化で task_size が gate 判定に昇格し初めて gate-bypass に転化。
- **発火前提（severity 較正）**: task_size 設定済み（M/L 等）なら OLD_TF 非空で block されるため**到達不能**。empty-baseline 窓（早期タスク状態）＋意図的 frontmatter raw-Edit が必要。単一ユーザ dogfood では自傷経路（外部攻撃者面ではない）。
- **本 iter で封鎖済みの姉妹経路（参考）**: 同 finding の本文 spoof 経路（frontmatter に task_size 無し・**本文**行頭 `task_size: S`＝`frontmatter_value` whole-file grep が拾う）は `b9c95f7` で check-gate の task_size 読取を frontmatter スコープ化して封鎖済み。
- **修正方向（次反復・専用 brainstorm/plan 推奨）**:
  - migration-grace を「真の旧フォーマット snapshot（task_type すら無い）」限定に絞る（task_type は必須キー＝現行 snapshot には常在。task_type 在で task_size 空→値 は raw-Edit＝block）。正規 update-task.sh 経路は snapshot 同期済みで tamper 判定に到達しないため無影響。migration ケース（真の旧 snapshot）は grace 温存。
  - 併せて bash（check-gate/audit/snapshot の whole-file grep）と python（frontmatter-scope extract_frontmatter）の**パーサ二重実装 drift** を統一検討。次の同根 3 件を明示スコープに含める:
    - (i) gate_approvals 重複キーの先勝ち(bash `grep -m1`)/後勝ち(python `extract_approval_map` dict 上書き) 乖離（1次 finding 2(b) Minor）。
    - (ii) **`extract_scalar_value`（check_status.py:264-273）の引用形優先**（盲検2次 F-1・Minor conf8）: `task_size: M` の後に `task_size: "S"` を raw 追記すると、audit 比較（bash 先勝ち）は M→M で tamper 非検知のまま、python 消費側（`check_phase_transition` の S 隣接判定・`task_size != "S"` strict-gate 免除）だけが S を読む＝audit-evading な enforcement 緩和（python=S/bash=M の割れ・実測）。check-gate 自体は騙されない（コード編集ゲートは緩まない）。
    - (iii) **`gate_value` の `raw_section` 本文フォールバック**（盲検2次 F-2・Minor conf9・pre-existing）: frontmatter に gate_approvals 節が無い STATUS では本文の gate_approvals ブロックが gate 判定に採用され allow になり得る（旧版でも同様＝この diff の回帰ではない）。empty-baseline class では audit を逃れ得るため SF-010 修正時に gate_approvals 側も対象化。
  - control-plane（post-status-audit.sh）変更＋migration 正当性の edge を含むため、review fix-forward で急がず専用反復で設計する（rushed な control-plane 変更は新規バグ源）。
- **状態**: **OPEN**。iter65 security gate で residual として明示 ack 予定。次反復（iter66 候補）で対応。
- **iter66 対応（本反復で封鎖・docs で CLOSED 化予定）**: Fix ①（`feff60c`）で migration-grace を task fields＋gate loop とも「真の旧フォーマット snapshot」限定に絞り、(i) 重複キー先勝ち乖離・(ii) `extract_scalar_value` 引用形優先を Fix ⑤（`6229fd5` first-match/先勝ち）で、(iii) `gate_value` 本文 fallback を Fix ④（`c5f5fd2` ---無しファイル限定）で消化。qa で hook 直接発火 4 ケース（canonical size 注入 BLOCK・gate 行欠落注入 BLOCK・真の旧フォーマット grace 温存・正規 update-task.sh 無影響）＋fresh 変異 M1-M5 全 kill、security 1次＋盲検2次とも approve で機械裏取り。

### SF-011: bash `read_frontmatter` と python `extract_frontmatter` の終端デリミタ許容差（**OPEN**・iter66 security 盲検2次検出・pre-existing）

- **発見**: iter66 security 盲検2次（fable・独立・1次結論非開示）。differential battery（`deb4a8a` baseline vs HEAD の実 hook 発火）で **pre-existing** を実証（この diff の回帰ではない＝両 rev で同挙動）。
- **種別**: パーサ二重実装 drift（frontmatter 終端デリミタの許容差）。bash `hooks/lib/frontmatter.sh` の `read_frontmatter` は `^---[[:space:]]*$`（末尾スペース許容）で終端判定するが、python `scripts/check_status.py:254` の `extract_frontmatter` は `\A---\n(?P<body>.*?)\n---\n`（strict・末尾スペース不可）。両者とも iter66 で変更なし（baseline=HEAD）。
- **重大度**: **Low**（pre-existing かつ 3 層で contained・実害到達なし・単一ユーザ dogfood の事故的自己バイパス面）。
- **経路**: STATUS frontmatter の途中に `--- `（末尾スペース）を raw-Edit で挿入し、その後続に `task_size: S` を隠す。bash はそこで frontmatter 終了と判断し `task_size` を本文扱い（scoped 読み→空）、python `check_phase_transition` は frontmatter 継続と見なし `task_size: S` を読む＝S-flow 隣接判定で phase-skip（brainstorm→implement や review→ship）を**数字上**許容し得る。
- **contained（3 層・iter66 で実証済み）**:
  - (1) `check-gate.sh` はコード編集ゲート＝bash が空を読む→plan gate→**deny**（コード編集は unlock されない・qa 変異 M2 で実測）。
  - (2) gate 承認は `update-gate.sh` 必須＝raw-Edit で gate 値を approved にできず tamper audit が block（本 iter の (iii) gate loop 絞り込みでさらに堅牢化）。
  - (3) `check_status.py:842 validate_with_pyyaml`（`--strict`/contract）が `extract_frontmatter`＋`yaml.safe_load` の regex↔PyYAML cross-check で mode/phase/gate 不一致を検出→contract FAIL＝malformed frontmatter を "done" に洗浄できない。
- **修正方向（次反復・hardening）**: `read_frontmatter` の終端を strict `^---$` に締めて python に一致させる、または parity drift-guard（`tests/test_parser_parity_driftguard.py`）に `--- ` mid-delimiter fixture を追加。iter66 の `frontmatter_value` scoped 化は fail-closed 方向で本乖離を悪化させていない（whole-file→scoped は strictly ≤ permissive）。
- **状態**: **OPEN**。iter66 security gate で residual として ack。緊急性低（pre-existing・contained）・次反復候補。

## CLOSED

（なし）

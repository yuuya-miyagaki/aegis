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

### SF-010: task_size の empty-baseline raw-Edit が migration-grace で tamper 検知を逃れる（**CLOSED**・iter66 v1.26.1 で封鎖・iter65 review 検出）

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
- **状態**: **CLOSED**（iter66 v1.26.1・ship コミット `dace3b7`）。(i)(ii)(iii) 全消化・機械裏取り済み（下記 iter66 対応）。
- **iter66 対応（本反復で封鎖・v1.26.1）**: Fix ①（`feff60c`）で migration-grace を task fields＋gate loop とも「真の旧フォーマット snapshot」限定に絞り、(i) 重複キー先勝ち乖離・(ii) `extract_scalar_value` 引用形優先を Fix ⑤（`6229fd5` first-match/先勝ち）で、(iii) `gate_value` 本文 fallback を Fix ④（`c5f5fd2` ---無しファイル限定）で消化。qa で hook 直接発火 4 ケース（canonical size 注入 BLOCK・gate 行欠落注入 BLOCK・真の旧フォーマット grace 温存・正規 update-task.sh 無影響）＋fresh 変異 M1-M5 全 kill、security 1次 opus＋盲検2次 fable とも approve で機械裏取り。**新 capability を解錠せず既存 moat 保証の穴のみを fail-closed 方向で封鎖**（正規 update-task.sh/update-gate.sh 経路は snapshot 原子同期で無影響）。残余の終端デリミタ差は SF-011 へ分離。

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

### SF-012: evidence 信頼判定の hardening 2件 — washed-green（exit 洗浄×marker regex）＋unknown-src decidable-by-default（**OPEN**・iter67 review 角度B/security 1次 検出・両方 pre-existing）

- **発見**: iter67（judge test-fact trust-scan 化）review 1次 角度B（敵対 finder・opus）が (a) を、security 1次（opus）F-1 が (b) を検出。いずれも **differential battery（baseline d2c4dd6 vs HEAD の実走）で pre-existing を実証**（OLD=NEW＝iter67 の回帰ではない）。review 盲検2次も (a) を独立に観察（周辺観察として一致）。
- **種別**: evidence writer/reader の信頼判定 hardening（marker/status 整合＋src allowlist）。moat 回帰ではない（文書化済み保証の違反なし）。
- **重大度**: **Low**（pre-existing・実 writer 集合と脅威モデルで contained・発火に明示的な自己欺瞞行為または脅威モデル外 capability が必要）。
- **経路**:
  - (a) **washed-green**: `python3 -m pytest -q; true`（テスト失敗だが `; true` で exit 0）を Bash 実行 → observer の status は exit code 由来で `ok`、出力の `=== 1 failed, 2 passed in …` が `AEGIS_TEST_PASS_MARKER_REGEX`（`={3,} [0-9]+ (passed|failed)`）にマッチして `marker_verified=true` → **decidable green**（1 failed でも judge が green）。iter67 trust-scan の影響は到達性のみ（washed-green の上に noise-ok がある場合、旧は 🟡 に隠れ新は表面化＝W2）＝**green の新規製造なし**（透明化は fp 一致の decidable green の実在が前提）。
  - (b) **unknown-src decidable-by-default**: `src` キー欠如/異値（`"forged"` 等）のエントリは `undecidable = (src=="observed" and …)` の述語に落ちず decidable 扱い＝status どおり green/red 化。実 writer（`hooks/lib/evidence.sh`＝observed 固定・`scripts/record-test-result.py`＝manual 固定）は他の src を発行せず、evidence-log への任意書込みは脅威モデル外（それが可能なら src:"manual" green を直接偽造できるため capability 増分なし）。
- **発火前提（severity 較正）**: (a) は `; true` 等の明示的 exit 洗浄＝自己欺瞞行為が必要（事故で書く形ではない・通常の失敗は exit≠0 → status=fail → 終端 🟡/red）。(b) は log への任意 JSON 書込み＝脅威モデル外。
- **修正方向（iter68 hardening 候補）**:
  - (a) writer 側（evidence.sh `_check_test_marker`）: pass-marker ヒット時に同一 summary へ fail トークン（`[0-9]+ failed`）が同居し **かつ exit=0** なら marker 無効化（zero-run gate と同型の整合軸追加）。または reader 側で `status=ok` × summary-failed の矛盾検出。
  - (b) reader 側（read_test_result）: src allowlist（`src in ("manual","observed")` 以外は undecidable-fail 扱い＝終端 🟡）。docstring は iter67 で実挙動を明記済み（0739a79）。
- **状態**: **OPEN**。iter67 security gate は approve（新規リスクなし・両件 pre-existing 実証済み）。

### SF-013: update-gate sed 範囲終端の無限界（`/^[a-z]/` が `---` で閉じない）＋--ref symlink 越境（**OPEN**・iter68 review 敵対1次/盲検2次 検出・いずれも pre-existing/Minor）

- **発見**: (a) iter68 review 敵対1次（opus・F-2 Low conf8）。scratch で「current_refs が frontmatter 末尾 key ＋ body に `  <key>:` 形の行」の合成 STATUS に対し body 行の書換えを再現。**baseline 8ab52ed の reset null 化 sed に同一範囲パターンが既存＝pre-existing**（iter68 の --ref 書込みはそれを踏襲したのみ）。(b) 同 review 盲検2次（fable・4-B Minor conf6）: `--ref` の `-f` 判定は symlink を辿るため、repo 内に置いた「repo 外実ファイルへの symlink」が存在チェックを通過し得る（path 検証自体は絶対/../allowlist で拒否済み・書かれる値は repo 相対リンク名）。
- **種別**: (a) sed 範囲アドレスの防御的堅牢化（canonical STATUS では到達不能）・(b) evidence ref の指し先検証の厳密化。いずれも moat 回帰ではない。
- **重大度**: **Low**（(a) canonical STATUS は current_refs の後に必ず top-level key〔external_evidence/next_action〕が続き範囲が正しく閉じる＝到達には手書きの異常 frontmatter 構造が必要。(b) single-user・ref は非実行の証跡ポインタ・tamper-evident writer 前提で capability 増分なし）。
- **contained**: (a) iter68 qa の fixture 本番同型化（next_action 追加）で正常経路の範囲終端はテスト済み。pre-write sanity が key 行実在を検証するため「素通りで gate だけ approved」の複合は封鎖済み（1956ac1）。(b) approved+ref のファイル不在は完了検査 FAIL 維持。
- **修正方向（iter69+ hardening）**: (a) sed 範囲終端を `/^[a-z-]/`＋`/^---$/` の複合（または awk 化）で frontmatter 境界に閉じる＋異常構造 fixture のテスト。(b) `--ref` 検証に realpath の repo 包含チェックを追加（YAGNI 評価と併せて判断）。
- **状態**: **OPEN**。iter68 security gate で residual として評価（1次/盲検2次とも非ブロッキング判定・pre-existing 実証済み）。

### SF-014: B1 drill の NO_RUN は flag 列挙 denylist ＝ 非フラグ no-run コマンドはフォージ可能（**OPEN**・iter69 review 盲検2次＋fix 敵対再検証 検出・pre-existing/Major-class・非ブロッキング）

- **発見**: iter69 review。盲検2次（fable）が **flag の quoting 迂回（F-1 Critical＝検査系 raw grep vs 実行系 shlex.split の不整合）** を実証→本反復で fix-forward 済み（`800948b` shlex 正規化統一）。その fix 敵対再検証（fable・独立）が、**列挙外の非フラグ no-run コマンド**（例 `python3 -c "import src.m"`・`go test -list` 等）は依然 NO_RUN 検査を素通りし、import-crash mutant と組んで **verdict PASS / テスト本体実行0 の偽 DRILL PASS を実際に生成できる**ことを隔離 clone で実測。
- **種別**: 反ガミング機構（B1 drill）の denylist 網羅性。`check_no_run_command`（`scripts/run-test-strength-drill.py:62`）は「テストランナーの no-run フラグ」を列挙する構造で、**そもそもテストランナーですらないコマンド**（任意の import プローブ）を no-run と判定できない。
- **重大度**: **Major-class だが本 gate 非ブロック**。理由: **pre-existing**（差分実測で cbc49e7〔iter69 の NO_RUN 機能導入前〕でも同一の偽 PASS＝iter69 は net 改善で回帰ゼロ）。脅威モデルは「自分の qa gate を欺く LLM」（自己欺瞞行為が必要）。iter69 は R4 の flag 系フォージを閉塞し、この denylist 不完全性を `hooks/lib/patterns.sh` コメントに明示済み。
- **contained**: (a) qa の drill は人手が `.drill` の test_command をプレビュー実走・レビューする運用（qa-verification skill）＝非ランナーコマンドは目視で不審。(b) B1 は多層の1枚で、E1 実行観測（fingerprint＋record-test-result）や judge の claims 検査と併走する。(c) patterns.sh コメントに残余と恒久策を文書化済み。
- **修正方向（iter70+ 恒久策）**: **列挙 denylist を positive proof に置換／補強** — 「baseline 実行が実際に N≧1 件のテストを走らせた」ことを出力マーカー（`AEGIS_TEST_PASS_MARKER_REGEX` 等の実行証跡）で drill 側でも要求する。これにより flag 迂回・非フラグ probe・未知ランナーを一括で塞げる（denylist の whack-a-mole を終わらせる）。evidence.sh の marker realness と設計を揃える。
- **状態**: **OPEN**。iter69 review で residual として評価（1次 approve_with_notes／盲検2次は F-1 Critical を fix 後 approve_with_notes／fix 敵対再検証 approve_with_notes・本 residual を pre-existing/非ブロッキングと全員一致で判定・実証済み）。iter69 security（1次 opus＋盲検2次 fable 物理隔離 clone）も差分実測で pre-existing を独立確認。
- **同クラス拡張（iter70 review 敵対2次＋親 verify・record 層で実測）**: 本 SF は B1 drill（`check_no_run_command`）だけでなく **manual writer `record-test-result.py`** にも同一クラスで現れる。iter70 は record に runner 照合＋NO_RUN＋非シェル互換の事前検証を追加したが、これも「no-run フラグ／非ランナー」の denylist であり、**runner 正規表現に該当しつつ実テストを0件実行して exit 0 するコマンド**は素通りして src=manual の green を記録できる。実測2インスタンス: (a) `python3 -m unittest discover -p <nomatch>` は unittest が0件一致でも exit 0（pytest は exit 5）→ green 記録（親 verify が HEAD で rc=0/status=ok を実測）。(b) `npm test` で package.json の `"test":"true"` スクリプト（0件実行・exit 0）→ green 記録（敵対2次が実測。ただし judge 側は fp が 64-hex 一致を要求するため、fingerprint.sh のある実 repo でのみ card 到達）。**pre-existing／net 改善**: iter70 以前の record は引数を一切検証せず `true` すら green にできた（差分実測: 37ec449 の record に検証ロジック0行）＝iter70 は accept 集合を狭めた純改善で回帰ゼロ。**contained**: 自己欺瞞行為が必要・多層防御（judge fp/marker・人手プレビュー）併走。**恒久策は本 SF と同一**＝denylist を positive「N≧1 件のテストが実行された」proof に置換（record 側は実行出力の pass-marker 件数、drill 側は同マーカー）。`record-test-result.py` の module docstring に本残余を明記済み（iter70）。
- **iter71 で record/drill に positive proof を適用（本丸の恒久策・net 改善）＋marker 粒度限界を実証（review 敵対2次＋親 verify）**: iter71 は恒久策「positive N-tests proof」を実装＝`hooks/lib/marker.sh` に4段検証コアを抽出し、`record-test-result.py`（green 記録前に marker verdict 必須・不成立は rc2・ログ非書込）と `run-test-strength-drill.py`（`check_baseline` に no-test-proof BLOCKED）へ適用。これで **iter69/70 の zero-run フォージ（`unittest discover -p nomatch`／`npm test`→`"test":"true"`）は CLOSED**（record 実記録で rc2 拒否を実測）。ただし marker は **出力ベース proof** のため、粒度限界クラスが残る（同 SF バケット・denylist で塞がない）: **(a) all-skip suite** — 全テスト `@skip` の unittest は `Ran N tests ... OK (skipped=N)`（unittest は skip を `Ran N` に数える）、go は全 `t.Skip()` でも `ok pkg dur` を出し、いずれも marker=true → record green＋judge `tests:green`（親 verify が実測: record `recorded: green`／judge `read_test_result:green`）。**pytest（`N skipped in`）と cargo（`0 passed`）は marker=false で正しく拒否**（実測）。**(b) echo-marker** — `npm test` script が marker 風文字列を echo（iter70 記載の残余）。**pre-existing**（marker.sh は evidence.sh の逐語移動＝byte 一致・pre-iter71 evidence.sh も all-skip 入力で同一 true を差分実走で確認）＝iter71 は net 改善で回帰ゼロ。**contained**: drill が subsume（all-skip/echo baseline は mutant を1つも殺せず DRILL FAIL・実測）＝qa gate は drill＋judge の両層で守られ本穴単独では破れない。**恒久策**: pass-marker の**マッチ**でなく passed/failed の**実数カウント**を要求する positive proof（skip 数を実行数から除外）＝iter72+。**moat 保護 pin 追加（iter71 review fix-forward）**: `tests/test_marker_lib.py::TestSkipSuiteResidual`（pytest/cargo=false の退行防止 pin＋unittest/go=true の既知残余記録）・`TestWeakPairBoundary`（companion-only=false）・`tests/test_patterns_parity.py::TestMarkerZeroRunParity`（リテラル TAB 化した PASS_MARKER/ZERO_RUN の grep-E∩python-re parity）。**併せて発見・即修正した pre-existing 欠陥**: ZERO_RUN の mocha パターン `0 passing(\b|$)` の `\b` が BSD grep -E で bare `0 passing` に非マッチ（macOS で mocha zero-run 検出が機能しない cross-engine 乖離）＝共通部分集合形 `($|[^a-zA-Z])` に修正（両エンジン実測一致・parity テストが摘発）。`record-test-result.py` docstring にも本残余(a)(b)を明記。
- **iter72 で count proof を適用（残余 (a) の主形 CLOSED・偽陰性 2 件修正）**: `aegis_marker_verdict` に Stage 5（count proof）を追加＝count 族サマリ検出時に executed（passed+failed・skip 除外）≧1 を要求（`AEGIS_TEST_COUNT_FAMILIES`・unittest: `Ran N`−Σ`skipped=K`／pytest・jest・vitest・cargo: Σ(passed+failed)／go `-v`: `--- PASS|FAIL` 行数）。これで **(a) all-skip の unittest（`Ran N ... OK (skipped=N)`）と go `-v`（`--- SKIP:` のみ）は CLOSED**（残るは素の `go test`＝非 verbose 出力に count が存在せず all-skip と実 run が byte 同形〔iter71 実測〕・`-v` 強制は全 go ユーザーの UX 退行のため見送り・drill subsume で contained）。**(b) echo-marker は count でも原理的に閉じない**（数字ごと偽装可能・出力ベース proof の床）＝(a)-go 素出力とともに恒久策候補は execution attestation（iter73+ audit_deps positive proof と同トラック）。**併せて修正した pre-existing 偽陰性 2 件（いずれも 2026-07-16 実証）**: (i) cargo の zero-run 行 deny が doc-tests 空セクション（`running 0 tests`→`test result: ok. 0 passed`＝doc-test を持たない全 crate の実出力）を誤拒否→行 deny を削除し Stage 5 の合計算術に委譲（all-ignored は Σ=0 で引き続き false・moat pin 黒箱不変。削除で開くのは「echo pair＋実 zero-run cargo 併走」形のみだが、実 run を省いた pure echo が現行でも true のため攻撃価値は strictly dominated＝設計追補 3・受理側の pin は `test_cargo_hybrid_echo_forge_true_known_residual`）。(ii) jest の実サマリ順序（failed, skipped, todo, passed）で skipped 混在時に STRONG marker の隣接要求が破れ実 run を誤拒否→中間セグメント許容へ緩和（厳格形は echo 可能だったため forge 価値不変）。vitest はサマリ行のインデント疑義に対しアンカー緩和（受理側のみ・実環境実証は qa フェーズで試行）。
- **iter72 review fix-forward（多角レビューで摘発・CLOSED-in-review／残余明記）**: count proof 初版（be77a85）を 1次4角度＋公式 code-review workflow＋親verify＋盲検2次でレビューし、以下を fix-forward（fail-closed 原則維持）。**(F-2 Major・false-POSITIVE)** vitest アンカー緩和の副作用で実 vitest all-skip（`Test Files 1 passed`＝file 単位 pass で緩和 STRONG に一致）が iter71 false→iter72 **true の false-GREEN** に反転していた（当初封鎖表の「vitest は Stage 2 で false」は誤認）。count DETECT を `Tests N (passed|failed|skipped|todo)` に拡張し `Tests N skipped` を検出→passed+failed=0 で veto（pin `test_vitest_all_skip_false_closed`）。**(F0/F1 false-negative)** unittest MINUS を `[(,] ?skipped=` にアンカー（本体印字の偶発 `skipped=N` での過剰減算＝実 green 誤拒否を修正）／pytest DETECT に `N (passed|failed)` 必須化（CI バナー誤検出→他ランナー実 green の cross-family veto を修正）。**(F4/F5/F6 hygiene)** Stage 5 grep に `-a`（GNU binary 検出保険）／DETECT grep rc≥2＝host grep 非対応 regex と malformed entry を rc3 fail-closed（strict 5-field parse）。**受容 fail-closed 残余**: 素 go log に偶発的な他族ゼロカウント行が column-0 で出ると cross-family veto で実 go が false（friction・稀・安全側・output-based の原理コスト。command-keying は `npm test` ラッパで false-positive 方向のため moat 原則上不採）。**marker 層の天井（(c) 追加）**: unittest の `TextTestResult.addSkip` を no-op に monkeypatch すると `Ran N`+`OK`（`skipped=` 消失）で実 N-pass と区別不能＝unittest CLOSED は「ランナーが skip を honest 自己申告する」前提下での CLOSED（echo-class・drill subsume）。**pre-existing（下記 SF-015 起票）**: pytest all-xfail suite の偽陰性。
- **iter72 security 盲検2次が摘発した locale 依存 false-GREEN（F-CRIT-1・High・CLOSED-in-security）**: `aegis_marker_verdict` の全 grep が **UTF-8 locale（macOS/Linux の対話既定・hooks/record が継承）下で不正バイトに脆弱**だった。攻撃者統制のテスト出力のサマリ行末に 1 バイト（0xFF 等）を付けると、その行の grep 抽出が UTF-8 LC_CTYPE で破綻し (i) **Stage 5 の `skipped=N` 減算が取りこぼされ**（all-skip unittest → executed=N≧1 → **true の false-GREEN**・iter72 由来）、(ii) **Stage 4 の zero-run veto も取りこぼす**（forged strong marker + `collected 0 items\xff` → true・**iter71 由来の pre-existing**）。C locale では各バイトが1文字＝決定的にマッチし正しく false。1次（opus）は injection/parse/secrets を PASS としたが本 locale 経路を見落とし、**盲検2次（fable・物理隔離 clone）が reject で摘発**＝独立性の value を再実証。**修正（security 内 fix-forward）**: 関数冒頭で `local LC_ALL=C LC_CTYPE=C LANG=C; export ...`＝全 5 stage の grep を byte-wise 決定化（全パターンは ASCII＋literal TAB のため byte-wise が正）。local scope で呼び出し元へ非漏洩・LC_ALL 未設定環境でも機能（実測）。pin: `test_stray_byte_all_skip_stays_false_utf8_locale`（新 Stage5 instance）・`test_stray_byte_zero_run_gate_stays_false_utf8_locale`（pre-existing Stage4 instance）＝いずれも pre-fix marker.sh で true 再現を確認した非空 pin。iter72 の review/qa/1次security が見落とした理由＝既存 50 pin が全て ASCII で stray-byte 経路を一度も踏まなかった（テスト網羅の盲点）。
- **iter70 で発見・即修正した回帰（本 diff 由来・review 敵対2次・CLOSED-in-review）**: iter70 新設の `audit_deps` 第4状態 `no-manifest` が、初版の `UNAUDITABLE_MANIFESTS` に未収載だが実依存を宣言する 15+ 種（Node lockfile 単独・.NET `.csproj`/`packages.config`・conda `environment.yml`・Deno・CocoaPods `Podfile`/`.podspec`・Nix・Crystal・Erlang・Ruby `.gemspec` 等）を `unverified`(🟡) から `no-manifest`(info) に降格し、security 信号を fail-visible→fail-silent に弱める回帰を含んでいた（baseline 37ec449 差分実測）。**2段 fix-forward 済み**: (1) review 敵対2次で `UNAUDITABLE_MANIFESTS` を全主要エコシステムへ拡張＋拡張子 glob `UNAUDITABLE_MANIFEST_GLOBS`（`*.csproj`/`*.gemspec`/`*.podspec`）追加・lockfile 単独も `unverified`（b32deb0）。(2) security 盲検2次が更に実証した 14 エコシステム（Haskell/sbt/Clojure/Julia/R/Perl/Dart-lock/vcpkg/conan/meson/bazel）と `*.cabal` glob を追加。回帰テスト3本（lockfile/ecosystem 16＋more-ecosystems 16＋glob 6）。**severity 限定の実証**: no-manifest は audit_deps 最終行のみ返り、auditable manifest（requirements/lock・package.json+lock）は先に監査され `vuln`/`clean` を返す＝**実脆弱性は隠蔽不能**。差分は 🟡 ack→info の視認性のみ（deps は red 非寄与）。**残余**: `no-manifest` は依然 denylist（未知エコシステムの manifest は誤って `no-manifest` になりうる）＝本 SF の positive-proof（依存ゼロの積極証明）根治対象。恒久策までは「依存宣言らしきファイルがあれば `unverified` に倒す」広めの denylist で contained。
- **相乗り追跡（iter69 security 盲検2次 R-2・Low・本 diff 由来）**: `non_coverable_lines`（`scripts/run-test-strength-drill.py`）の floor 免除が、py の複数行文字列（triple-quote 非docstring）内部の `#` 始まり/空行を「コメント」と誤分類し免除しうる。**PASS 偽造は不可**（免除されても宣言 mutant は真に caught される必要があり、文字列/コメント行 mutant は survive→FAIL＝親 verify 実測）。floor の緩和のみ。恒久策は本 SF の positive-proof と同バケットで、py の comment 判定を `tokenize`（COMMENT/NL）ベースへ寄せる。iter70+ hardening。

### SF-015: pytest all-xfail suite が STRONG marker 不成立で偽陰性（**OPEN**・iter72 review 敵対角度検出・pre-existing/Low/fail-closed）

- **発見**: iter72 review（敵対角度・fable）。`===== 3 xfailed in 0.5s =====`（全 test が `@pytest.mark.xfail`・実 body は 3 件実行され期待どおり fail）のみの出力は、STRONG marker `={3,} [0-9]+ (passed|failed)` の `passed|failed` トークンに `xfailed`/`xpassed` が非一致 → marker 不成立 → verdict **false**。実 body が実行された正当な green（pytest exit 0）を誤拒否する。
- **種別**: 偽陰性（false-negative）。record は rc2 で green 記録を拒否・observed は marker_verified=false。**fail-closed 方向**（実行を過小評価するだけで false-GREEN は作らない）。
- **重大度**: **Low**。(a) 混在 run（`1 passed, 3 xfailed`）は `1 passed` で STRONG 発火するため実害は「xfail/xpass 専用スイート」に限定。(b) fail-closed（安全側）。(c) xfail 専用スイートは稀。
- **pre-existing**: STRONG marker は iter71 以前（commit 1587a69 由来）から `passed|failed` のみで、iter72 は STRONG を未改修。count proof（Stage 5）とは独立。
- **恒久策候補**: STRONG/count に `xpassed`（＝実行され予期せず pass＝body 実行済み）を実行証跡として含めるか、pytest の `collected N items` prologue を実行下限の proof に使う。ただし `xfailed` を「実行済み」と数えるべきかは意味論判断（期待された失敗も body は走っている）を要するため、単純拡張でなく設計判断として iter73+ で扱う。marker 層の他残余（SF-014）と同バケット。

### SF-016: deny 側フックの `LC_ALL=C` 固定が Unicode 空白区切りの moat マッチを狭める（**OPEN**・iter73 review 盲検2次検出・非 exploitable/accepted residual）

- **発見**: iter73 review 盲検2次（fable・blind・1次結論非開示）。1次（opus・approve）が「NBSP 区切りは bash が単一トークン化＝非コマンドゆえ無害」と判定したのに対し、盲検2次が「coverage narrowing＋コメント事実誤り」を Major で摘発した divergence。
- **種別**: locale 固定の副作用（moat パターンの `[[:space:]]`/`\s` が C locale で ASCII 空白のみに狭まる）。iter73 の byte-wise 化（`export LC_ALL=C LC_CTYPE=C LANG=C`・commit 7bfb8f7/95e08ae）で導入。
- **重大度**: **非 exploitable（accepted residual）**。実測（2026-07-19）: `[[:space:]]`/`\s` は UTF-8 で NBSP(U+00A0)/U+3000 に match するが C では non-match。しかし **bash は NBSP/U+3000 で word-split しない**ため `rm<NBSP>-rf`・`git<NBSP>add` は**単一の非存在トークン→`command not found`**＝削除もステージングも起きない＝機能的に無害。ASCII space/TAB は C でも match するため、**runnable な破壊的/シークレットコマンド（ASCII IFS 区切り必須）は取りこぼさない**。
- **経路（pre→post 実測）**: `rm<NBSP>-rf /x` は pre-change UTF-8 で `ask`→post-change C で `allow`、`git<NBSP>add .env` は `deny`→`allow`。いずれも対象コマンドは非実行。
- **なぜ re-widen しないか**: Unicode 空白まで match させると (1) 非コマンド（実行不能）への spurious な warn/deny が復活し、(2) C-locale の決定性（byte-injection crash/grep-drop の封鎖）と矛盾する。narrowing は「実行可能コマンドの網羅」を損なわず「非コマンドへの誤マッチ」だけを除くため、accept が筋。
- **対処済み**: (a) 両フックの誤コメント「ASCII + literal だから byte-wise が正」を「runnable command は ASCII IFS 区切り必須ゆえ byte-wise で取りこぼさない・非 ASCII 区切りは非コマンド」へ訂正（commit 8be219d）。(b) 受容 residual を pin（`tests/test_hook_locale_byte.py::test_{destructive,secrets}_unicode_ws_separator_is_accepted_residual_allow`＝将来 re-widen 時に flip して revisit を強制）。
- **状態**: **OPEN（accepted residual・記録のみ・コード再修正なし）**。将来トリガ＝Unicode 空白を IFS に含める非標準シェル対応が要件化された場合、または「moat は非コマンドにも警告すべき」という UX 判断が出た場合に再評価。

### SF-017: `check-destructive.sh` / `check-secrets.sh` の空クォート トークン分割バイパス（**Critical・実装済み(review 再走中)**・iter74 二重レビュー Codex 検出＝SF-001 防御の未伝播）

- **発見**: iter74 二重網羅レビュー（Codex 外部・層1 moat 次元）。Fable（盲検2次）は同次元を「健在」と結論したが、Fable が試したのは平文 decoy（`echo "safe" ; rm -rf /etc`＝ASK 正常）で、**token 内空クォート形は未攻撃**。親（本セッション）が実走再現し確定＝乖離が摘発した実バグ。
- **種別**: SF-001 クラス（クォート除去＋隣接トークン連結）の**未伝播**。SF-001（iter32-35）は shlex トークン化＋パス解決で control-plane **書込み先**検出に対し同クラスを網羅閉鎖したが、その防御が `check-destructive.sh` の破壊語検出（生 regex）と `check-secrets.sh` の `.env` 検出（生 regex）に**適用されていない**。
- **重大度**: **Critical**。`g""it a""dd .e""nv` は bash で正規の `git add .env` になるが **secret DENY が ALLOW に落ちる**（＝認証情報の staging/commit を止められない）。フレームワーク自身の脅威モデルは SF-001 で同クラスを Critical 認定済み（「非 framework エージェントが任意書込み」）。到達性: モデルが emit する単一 valid-UTF-8 コマンドで到達（hostile FS や evidence-log 直接編集は不要）。
- **再現（HEAD 77566ed・親実走生出力）**:
  ```
  check-destructive  r""m -rf /tmp/x     -> {}  [ALLOW]   （平文 rm -rf は ASK）
  check-secrets      g""it a""dd .e""nv  -> {}  [ALLOW]   （平文 git add .env は DENY）
  変種  r\m -rf /tmp/x  -> ALLOW   "rm" -rf /tmp/x  -> ALLOW
  対照  hooks/check-control-plane 系（SF-001 で token 化済）は同形を deny/ask（既存テストで pin）
  ```
- **根本原因**: destructive/secrets の判定が「生コマンド文字列上の literal 部分文字列 regex」で、シェルのクォート除去＋隣接連結を再現しない。SF-001 が control-plane 判定に導入した「shlex トークン化→各語の literal value を再構成→判定」プリミティブが両フックに無い。
- **修正方針（実装済み・iter75＋fix-forward）**: フル tokenizer 移植ではなく（意図的に退役済みの設計思想に沿い）、**静的正規化 helper `aegis_dequote_normalize`**（quote(`"`/`'`)・backslash・**backslash-newline(行継続)**・`${IFS}`/`$IFS`・残改行/タブ を純 bash param 展開で畳む）を共有し、両フックが**生形判定を保存**したまま正規化形で既存検出器を再適用（正規化のみ一致＝難読化実在→ASK・生 DENY 不変）。broad-stage(`git add -A/.`)・commit 検出は **FS/staged スキャンを NORM でも再利用**（raw=deny/norm=ask・`git commit -m "…"` 誤検知なし）。難読化大文字は destructive 正規化経路の**全 grep を `grep -i`（case-insensitive）on NORM 化**してクラス全体（rm/chmod/find/dd/shred/mkfs/git 系＝全 `AEGIS_DESTRUCTIVE_CMD_REGEX`）を封鎖（FF7・実測: `NORM_LOWER` では `chmod -R` の `R` リテラルが壊れ捕捉不可ゆえ `grep -i` を採用）。`git commit -m "…STATUS.md…"` 等のメッセージ救済は不変。残余は SF-019（brace/param/cmdsub）・SF-020（raw 大文字直打ち）へ分離。footprint: check-destructive.sh＋check-secrets.sh＋patterns.sh＋tests。
- **封鎖範囲（iter75 実測封鎖）**: quote(`"`/`'`)・backslash・backslash-newline・**非空 `${IFS...}` parameter-expansion family（`${IFS}`/`${IFS:0:1}`/`${IFS: -1}`/`${IFS/x/y}`/`${IFS#}`/`${IFS:-x}`＝実行時に空白へ展開する形）**・`$IFS`・broad-stage 難読化(`git${IFS}add -A`)・commit 難読化(`git${IFS}commit`)・**Finding 1（flag 密着 `${IFS}` の SAFE_TARGETS 早期 allow swallow・`rm -rf${IFS}/x`＝NORM!=CMD で early-exit skip）**・難読化大文字クラス全体（rm/chmod/find/dd/shred/mkfs/git 系＝全 `AEGIS_DESTRUCTIVE_CMD_REGEX`・`grep -i`）。IFS-family 畳みは FF9 で**単一 sed（`s/\$\{IFS[^}]*\}/ /g`・非貪欲・O(n)）**化（bash `${c//…}` 全置換は多数一致で O(n²)＝5000 件 ~21s→sed ~40ms・hook timeout=fail-open 回避）。回帰 pin＝`tests/test_moat_quote_split.py`（67 ケース）＋`tests/test_patterns_parity.py`。
- **道C による主張の正確化（iter75 security 再走）**: 静的文字列正規化で**健全に**畳めるのは**非空 IFS 展開**のみ。security 1次(opus)/盲検2次(fable) が、**空/ゼロ幅 IFS 展開**（`${IFS:0:0}`・オフセット超過）の unsound fold（過分割）と mixed split/glue（`rm${IFS}-${IFS:0:0}rf${IFS}/x`＝fold-to-space/fold-to-empty のどちらの純形でも非マッチ＝2ⁿ 展開列挙が必要）、param-default ネスト（`rm${Q:-${IFS}}-rf`）、変数間接（`x=IFS; rm${!x}-rf`）を摘発（bash runtime で実削除/実 leak を実証）。これらは全て**構造化 argv でしか根治できない＝SF-019 residual**（下記に統合）。全て意図的難読化を要し事故経路で発生しない（脅威モデル外・North Star から severity 低）。証跡＝`docs/qa-reports/iter75-security.md`。
- **状態**: **CLOSED-in-review（iter75・道C 確定）**。review approved（`docs/qa-reports/iter75-review.md`）／qa approved（`docs/qa-reports/iter75-qa.md`）／security approve_with_notes（`docs/qa-reports/iter75-security.md`・deploy blocker なし）。正本＝`docs/full-review-2026-07-19-dual-codex-fable.md` §4.1。**review 盲検2次が2回・security 1次/盲検2次が各1回、独立に段階的に残穴を摘発（broad-stage/commit・backslash-newline→FF1-6／難読化大文字→FF7／ゼロ幅・mixed IFS・param-default・変数間接→SF-019 へ分離＝道C）＝独立盲検レビューが機能した実例**。残余は SF-019（構造化 argv・iter77 根治）・SF-020（raw 大文字直打ち）へ分離。

### SF-022: marker Stage 6 の fail-token denylist は語彙不完全＝positive proof が根治（**Low・iter76 で緩和・iter77 attestation で根治**・盲検2次検出）

- **発見**: iter76 review 盲検2次（fable・fresh）。1次バッテリは `failed`/`FAILED`/`FAIL` を叩いたが `errors` 語形を見落とし。2次が pytest の `===== 1 passed, 2 errors in 0.42s =====`（collection/setup error）を exit0 で流すと marker Stage 6 が veto せず `true` を返すことを摘発。
- **種別**: marker Stage 6（SF-012(a)）は**失敗トークンの denylist**。iter76 実装時点では pytest の `errors` サマリ語形が非対象で、Stage-5 count family も EXEC が `passed|failed` のみ数えるため error を減算しない。
- **重大度**: **Low（緩和済み・脅威モデル内で独立到達不能を実証）**。実証（iter76 review 親実走）: (E1) marker 単体は `1 passed, 2 errors`+exit0 で pre-fix `true`／(E2) judge e2e（observed・演算子なし単一 cmd）で pre-fix `green`＝**合成到達は可能**。だが**脅威モデル内では独立到達不能**——本物の単一 pytest が errors を出すと **exit 2**（非0）で status=fail、observed で status=ok にするには (a) 演算子洗浄（`; true`）→ judge W2a が捕捉／(b) fake runner binary → SF-014/iter77 attestation 天井、のどちらかが必要。record 経路（manual）は実 exit code ゲートで弾く。
- **iter76 緩和（2 段）**: (1) review 盲検2次＝`AEGIS_TEST_FAIL_TOKEN_REGEX` に第5 alt `[1-9][0-9]* errors? in [0-9]`（pytest の timing tail `N errors in T.TTs` に tight anchor・benign `caught 3 errors in total`／`5 errors in the log` は `in <digit>` 非該当で非マッチ）。(2) security 盲検2次 A7＝既存 unittest バナー alt を `FAILED \((failures|errors)=`→`FAILED \((failures|errors|unexpected successes)=` に完成（unittest FAILED バナーの語彙は failures/errors/unexpected successes の**有界3種**＝これで網羅・treadmill でなくバナー完成）。judge を経由しない共通コア消費者（record/drill）でも errors/unexpected-successes washed を veto。pin＝`test_w2b7_*`（errors-only/mixed）＋`test_w2b7b`（過剰マッチ防止）＋`test_w2b8`（unexpected successes バナー）。
- **根本原因/根治**: 列挙 denylist は原理的に不完全（LEARNINGS conf9・SF-014 と同型）＝失敗語彙を足し続けても網羅しない。**根治は iter77 の pytest execution attestation**（argv spawn＋structured event で「実行され passed/failed/error のいずれか」を positive proof・src=attested のみ decisive green）。本 SF はその天井の一事例で、iter76 は denylist を1語広げた net 改善に留まる。
- **状態**: **iter76 緩和（errors 語形封鎖）・残余は iter77 attestation で根治**。denylist の原理的不完全性そのものは OPEN（iter77 で positive proof に置換）。

### SF-018: `check-runtime-state.sh` が不正 UTF-8 バイトで `tr` crash → fail-open（**Medium・OPEN**・iter74 二重レビュー Fable 検出＝iter73 完全性主張の反証）

- **発見**: iter74 二重網羅レビュー（Fable 盲検2次・層1 locale-byte 次元）。Codex（外部）は同次元を「iter72/73 の byte hardening は closed」と結論したが、Codex は runtime-state フックを未攻撃。親が実走再現し確定＝乖離が摘発。
- **種別**: iter73 の locale/byte 掃討（`export LC_ALL=C` を抽出直後に張る）が **check-destructive/secrets の2本のみに適用され、`check-runtime-state.sh`（3本目）に未適用**。iter73 設計正本は「runtime-state は python3 抽出でバイト→空 CMD＝同型不成立」と記録したが、**python3 は surrogateescape でバイトを温存し空にならない**（実測で反証）。
- **重大度**: **Medium**（fail-open だが到達性は valid-UTF-8 制約下ゼロ＝モデルは 0xFF を emit しない。iter73 自身の格下げ較正と整合）。ただし本フックは**非 framework モードで Bash 経由の runtime-state（gate 値含む）改竄を止める唯一の PreToolUse ガード**で、fail-open の落ち先が moat の要である点は destructive/secrets より重い。robustness 契約（制御フックは任意 stdin で crash しない）違反＋durable な誤完全性主張の残存が本質。
- **再現（HEAD 77566ed・親実走生出力）**:
  ```
  echo x > docs/STATUS.md            -> rc=0 {}                                   [allow]
  echo <0xFF> x > docs/STATUS.md     -> rc=1 '' stderr:"tr: Illegal byte sequence"  [FAIL-OPEN crash]
  同バイト -> check-destructive（iter73修正済）  -> rc=0 {}   （crash せず）
  同バイト + LC_ALL=C -> check-runtime-state       -> rc=0 {}   （一行修正で解消）
  ```
- **根本原因**: `hooks/check-runtime-state.sh:120-122` の `tr '\n\r' ';;'`（および下流 grep）が C locale 非固定のまま、抽出済み CMD 中のバイトで crash。`set -euo pipefail` で rc=1・decision 未出力＝fail-open。
- **修正方針**: check-destructive/secrets と同一＝`INPUT=$(cat)`（もしくは CMD 抽出）直後に `export LC_ALL=C LC_CTYPE=C LANG=C`（抽出の python3 は PEP 540 で UTF-8 fidelity 維持）。併せて iter73 設計正本の「同型不成立」記述を訂正し、`tests/test_hook_locale_byte.py` に runtime-state の crash-regression pin を追加。effort S。
- **状態**: **OPEN（未修正・iter76 P0 で消化予定）**。正本＝`docs/full-review-2026-07-19-dual-codex-fable.md` §4.3。

### SF-019: check-destructive/secrets の brace/param-default/cmdsub トークン分割は文字列正規化で塞げない（残余・構造化 argv 待ち）

- **発見**: iter75 / SF-017 修正（quote/BS/`${IFS}` 封鎖）の網羅性自己検証。2026-07-19。**iter75 security 再走（1次 opus／盲検2次 fable・2026-07-21）で本クラスの3綴りを runtime 実証付きで追加検出**（下記）。
- **種別**: SF-017 と同クラス（静的 matcher がシェルのトークン化を再現しない）の**未畳み込み綴り**。iter75 は quote/BS/**非空 `${IFS}` 展開**を静的文字列畳み込みで閉じたが、以下は**文字列正規化では塞げず残存**（いずれも語の literal value がコマンド文字列に現れない＝実行時展開/構築）: (a) brace 展開（`{r,x}m`/`r{,}m`）、(b) param-default（`${x:-rm}`・**ネスト `${Q:-${IFS}}`**）、(c) cmdsub（`$(...)`/backtick）、(d) **変数間接（`x=IFS; rm${!x}-rf`・`${!var}`）**、(e) **ゼロ幅/空 IFS 展開と mixed split/glue**（`${IFS:0:0}`＝空展開は runtime で隣接連結だが静的 fold は過分割＝unsound。`rm${IFS}-${IFS:0:0}rf${IFS}/x` は fold-to-space/fold-to-empty のどちらの純形でも非マッチ＝**2ⁿ 展開列挙が必要**）。SF-001 系（control-plane）が resolver で brace/param を展開済みなのと非対称。
- **重大度**: **Medium（残余・記録のみ）**。理由: (1) brace は実行時に重複トークンを生む綴りもあり（`r{,}m -rf` → `rm rm -rf`）到達は非自明。(2) cmdsub/param は SF-004 隣接＝**runtime 構築（静的解析の原理的限界・実証済み）**。(3) secret-staging の主要綴り（quote/BS/`${IFS}`）は iter75（SF-017）で閉鎖済み。
- **再現（HEAD iter75 実装後・不変。grill_verify 確認）**:
  ```
  check-destructive  r{,}m -rf /tmp/x   -> {}  [ALLOW]   （brace で 'rm' に展開）
  check-secrets      g{,}it add .env    -> {}  [ALLOW]   （brace で 'git add .env'）
  同型  ${x:-rm} -rf /tmp/x  -> ALLOW（param-default）   $(printf rm) -rf  -> ALLOW（cmdsub）
  pin   tests/test_moat_quote_split.py の test_residual_* 2 件が iter75 実装後も allow を固定
  ```
- **根本原因**: destructive/secrets の判定は「クォート除去＋隣接連結の静的畳み込み」までは SF-017 で実装したが、brace/param-default/cmdsub は**語の literal value がコマンド文字列に現れない**（実行時展開/構築）ため文字列正規化の射程外。cmdsub は実行しない限り出力（=破壊語/対象パス）を静的復元できない＝SF-003/SF-004 と同じ原理的限界。brace/param は静的展開可能だが、それには control-plane resolver 相当の展開器が要る。
- **修正方針**: **ロードマップ iter77 の構造化 argv（実行イベント/argv 判定）で根治**——raw shell text ではなく実際に渡る argv を真実とすれば brace/param/cmdsub の展開結果を直接判定できる。または SF-001 の control-plane リゾルバ（brace/param 展開対応済み）を destructive/secrets へ移植（重い・共有トークナイザの複雑化＝North Star の作者保守可能性に非整合ぎみ）。系としては**「raw shell text を真実の代理にするな」**の一般化。
- **状態**: **OPEN（accepted residual・iter77 系で根治予定）**。iter75 の残余 pin（`tests/test_moat_quote_split.py::test_residual_*` 2 件）が将来対応時に flip して revisit を強制する。cmdsub 部分は SF-004 と同じく敵対閉鎖は原理的に不可（脅威モデル外）。

### SF-020: `check-destructive.sh` が大文字コマンド名を case-fold せず case-insensitive FS で破壊コマンドが silent allow（**High・CLOSED-in-review iter77**・iter75 grill-code 検出＝iter54 secrets case-fold の destructive 版・非対称）

- **発見**: iter75 grill-code（本セッション・fable・2026-07-20）。SF-017 修正（quote-split 封鎖）の網羅性グリルで隣接検出。iter75 diff の欠陥ではなく既存挙動の穴。
- **種別**: iter54（case-insensitive FS の moat バイパス封鎖・commit 9a36d72）が secrets 側で塞いだ case-fold 非対称の **destructive 版**。`check-secrets.sh` は `CMD_LC`（小文字化）で `.ENV`→`.env` を捕捉し `GIT ADD .ENV` を deny するが、`check-destructive.sh` は raw CMD を生 grep し大文字コマンド名（`RM`）を取りこぼす。
- **重大度**: **High（raw 大文字直打ちに限定）**。実 exploit 可能（前提＝case-insensitive FS＝macOS APFS デフォルト/Windows デフォルト）。ASK 止まりでなく **silent allow**（破壊コマンドの唯一の PreToolUse ガードが無反応）。SF-017 とは独立の既存穴で、iter75 の quote-split 修正は本穴を導入も解消もしない。**iter75 fix-forward で難読化大文字（`NORM!=CMD`）は rm/chmod/find/dd/shred/mkfs/git 系まで含めクラス全体を封鎖済み**（正規化経路の全 grep を `grep -i` on NORM 化・FF4 5f03ac0＋FF7 9c3d7ea。`NORM_LOWER` では `chmod -R` の `R` リテラルが壊れるため `grep -i` 採用）。本 SF は **raw 大文字直打ち（`RM -rf`＝`NORM==CMD` で正規化経路に入らない）に限定**して残存。
- **再現（iter75 fix-forward 後・本セッション実走生出力）**:
  ```
  check-destructive  RM -rf /tmp/x     -> {}    [ALLOW]   （raw 大文字直打ち＝本 SF の残存分・NORM==CMD）
  check-destructive  R""M -RF /tmp/x   -> ASK             （難読化大文字＝iter75 で封鎖済み）
  check-destructive  RM${IFS}-rf /tmp/x -> ASK            （同上）
  対照  check-secrets  GIT ADD .ENV    -> deny            （iter54 で case-fold 済み＝非対称）
  傍証  type -p RM -> /bin/RM           （case-insensitive FS で /bin/rm に解決＝RM -rf は実行される）
  ```
- **根本原因**: `check-destructive.sh` の raw 破壊語判定（`AEGIS_DESTRUCTIVE_CMD_REGEX` 等・:118 再帰削除 regex）が CMD を小文字化せず生 grep で、regex は `rm` 小文字固定。secrets は iter54 で `CMD_LC` 化したが destructive の raw 経路は未適用。難読化経路（`NORM!=CMD`）は iter75 fix-forward で `NORM_LOWER` 化して塞いだが、raw 大文字（`NORM==CMD`）は正規化経路に入らないため raw case のみ残存。
- **修正方針（残存分）**: destructive の **raw 破壊語判定を `CMD_LC` ベースへ**寄せ secrets と対称化（大文字コマンド名も小文字 regex にマッチ）。難読化経路は iter75 対応済みゆえ raw 経路のみ。回帰 pin: safe-artifact 除外（`rm -rf node_modules`）が case-fold で誤変化しないこと・LOWER 化が iter73 の C locale narrowing（SF-016）と衝突しないこと。TDD で raw `RM -rf`→ASK（旧=赤/新=緑）。effort S。iter76 候補。
- **範囲（iter75 review 1次 F-1 追記・2026-07-20）**: raw 大文字残余はコマンド名だけでなく **redirect システムパスの大文字**も含む。実測: `echo x > /ETC/passwd`（大文字 `/ETC`・`NORM==CMD`）→ allow（`>\s*/(etc|usr|bin...)` パターンの `etc|usr|bin` リテラルが case-fold されない）。難読化形 `echo x >${IFS}/ETC/passwd`（`NORM!=CMD`）は iter75 fix-forward の grep -i で ask 済み。iter76 の raw 大文字 case-fold 対応で redirect システムパスも一括消化（`grep -i` or `CMD_LC` 化）。
- **関連実測（ANSI-C quoting は無害＝穴でない・記録のみ）**: 同グリルで `rm$'\t'-rf`・`git$'\t'add .env` を exploit 候補として疑ったが実測で反証。ANSI-C quoting `$'\t'` はタブを生成するが**それ自体がクォート**ゆえ単語分割を起こさない（実測: `set -- foo$'\t'bar` → argc=1・`foo<TAB>bar` が単一語。対照 `${IFS}` は argc=2）。よって `rm$'\t'-rf` は実行時に `rm<TAB>-rf` という非存在1語コマンド→`command not found`＝機能的に無害。現状 allow は正しく moat の穴ではない（SF-019 の残余にも含めない）。同カテゴリで unicode 全角 `ｒｍ`（`ｒｍ -rf`）も fix-forward の grill-plan で helper 非畳み込みを実測したが、bash で `ｒｍ` は別コードポイント＝非存在コマンド・case-insensitive FS でも `rm` に解決されず＝**SF-016（Unicode 空白）と同カテゴリの無害**（塞ぐ必要なし・pin 不要）。
- **状態**: **CLOSED-in-review（iter77・2026-07-26）**。修正: `check-destructive.sh` の raw 経路 grep 4 サイト（fallback CMD_REGEX ループ／fallback rm 再帰／本体 rm 再帰特例／本体 CMD_REGEX ループ）を `grep -qE`→`grep -iqE` に case-fold し NORM 経路（iter75 FF7 で既 -i）と対称化（commit 298043f）。redirect システムパス大文字（`> /ETC/passwd`）も同配列 grep の -i で一括封鎖。SAFE_TARGETS の sed（safe-artifact 早期 allow）は**意図的に非 fold**＝allow 例外を大文字へ広げない（大文字 `RM -rf node_modules` も ask に落ちる／D-6 pin）。review 実走: 大文字/混在/長flag/redirect大文字/fallback の全形（`RM`・`Rm -Rf`・`GIT RESET --HARD`・`CHMOD -R`・`DD OF=`・`MKFS`・`SHRED`・`> /ETC`・fallback 大文字6形）が ask、クラス内バイパス 0 件。pin=tests/test_moat_case_fold_stage_alias.py（D 系・mutation 6/6 検知者確立）。review approved（`docs/qa-reports/iter77-review.md`・approve_with_notes）。残: raw 大文字とは別クラスの `>>` append redirect 穴を SF-023 として分離起票（case 非依存・fail-safe 側）。

### SF-021: `check-secrets.sh` の broad-stage 検出器が `git stage` エイリアスを見ておらず `git stage -A/.` が silent allow（**High・CLOSED-in-review iter77**・iter75 fix-forward grill-code 検出＝broad 検出器の動詞網羅穴）

- **発見**: iter75 fix-forward grill-code（本セッション・fable・2026-07-20）。盲検2次 F1（broad-stage 難読化）の封鎖検証中に、broad-stage 検出器自体が `git add` のみで `git stage` を見ていない動詞網羅穴を隣接検出。
- **種別**: broad-stage 検出器（`_STAGE_BROAD_RE`・`git...add...(-a|--all|.)`）の**動詞網羅漏れ**。`git stage` は `git add` の完全なエイリアス（git 公式・`-A`/`--all`/`.` を取る）だが、regex は `add` のみ。SF-017（quote-split クラス）とも SF-020（case-fold）とも別軸。
- **重大度**: **High**。実 exploit 可能。生でも難読化でも `git stage -A`（実 .env 存在）→ 全ファイル broad staging で .env silent 漏洩。難読化以前に**生でも通る**（F1 の難読化とは別・より基本的）。
- **再現（iter75 fix-forward 後・本セッション実走生出力）**:
  ```
  check-secrets  git stage -A        (実 .env) -> {}   [ALLOW]   （silent broad staging）
  check-secrets  git${IFS}stage -A   (実 .env) -> {}   [ALLOW]
  対照  check-secrets  git add -A     (実 .env) -> deny            （add は捕捉）
  ```
- **根本原因**: `check-secrets.sh` の `_STAGE_BROAD_RE`（および旧 inline regex）が `git[[:space:]]+...add[[:space:]]+...` で `add` 固定。加えてコメント `:181`「Only `add` (not stage / update-index) has the -A/--all/. broad-stage spellings」は**事実誤認**（`git stage` は add と同一の broad 綴りを持つ。`update-index` は別＝低レベルで挙動が異なるが `stage` は完全同義）。
- **修正方針**: `_STAGE_BROAD_RE` の `add` を `(add|stage)` に拡張。二経路トリガ（raw=deny/norm=ask）は既存構造のまま流用（`git stage -A`→deny・`git${IFS}stage -A`→ask）。コメント :181 を訂正。回帰 pin: `git stage`（実 .env）→deny・`git stagearea`(誤マッチ回避)→allow。effort S。**iter76 で SF-020（raw 大文字）と併せて broad/destructive 網羅 iter として消化**（iter75 は review reject 分〔F1/F2/F3/F4〕でクローズ・焦点保全）。
- **状態**: **CLOSED-in-review（iter77・2026-07-26）**。修正: `_STAGE_BROAD_RE` の verb `add`→`(add|stage)`（commit 1a81bd6）。`${GIT_STAGE_VERB}`（`(add|stage|update-index)`）は流用せず broad 検出は `(add|stage)` のみ（`update-index` は `-A/--all/.` の broad 綴りを持たない plumbing＝混ぜると非実在綴りを許容）。事実誤認コメント（旧「Only add … has broad-stage spellings」）を訂正。deny/ask 文言を `git add -A / git stage -A / git add .` へ verb 非依存に汎化。review 実走: `git stage -A/--all/./-a`・`.[!e]*` glob・`GIT STAGE -A`・`git -c x=y stage -A`・`git${IFS}stage -A`（実 .env）が全て deny/ask、対照 `git stagearea`・`git update-index --add`（broad 綴りなし）・個別 `git stage README.md` は正しく allow。明示 .env 経路（`_STAGE_ENV_RE`・update-index 含む）は不変＝`git update-index --add .env` は依然 deny。pin=tests/test_moat_case_fold_stage_alias.py（S 系・mutation (e) を S-1/2/3/5/5b が検知）。review approved（`docs/qa-reports/iter77-review.md`）。

### SF-023: `check-destructive.sh` の `>` redirect システムパス検出が `>>` (append) を取りこぼす（**Low・OPEN**・iter77 review 敵対 finder 検出＝既存 regex カバレッジ穴・case 非依存）

- **発見**: iter77 review 敵対バイパス finder（opus・2026-07-26）＋親裏取り。SF-020 の redirect 大文字封鎖の検証中に隣接検出。
- **種別**: `AEGIS_DESTRUCTIVE_CMD_REGEX` の redirect パターン `(^|[^0-9>])>\s*/(etc|usr|bin|sbin|boot|sys|lib)(/|[[:space:]]|$)` の**左コンテキスト負クラス `[^0-9>]`** が、`>>`（append）の 2 番目の `>` を「直前が `>`」として弾くため、`echo x >> /etc/passwd` が非マッチ＝allow。SF-020（case-fold）とは独立で、**小文字形 `echo x >> /etc/passwd` も同じく allow**（親実走確認）＝case 非依存の既存穴。
- **重大度**: **Low**。(1) `> /etc/passwd`（truncate・単発）は既に ask 済みで、append は truncate より危険度が低い（追記は既存内容を消さない）。(2) システムパスへの `>>` は通常 sudo を要し PreToolUse の可視範囲では稀。(3) fail-safe 側（allow のままで deny を弱めるものではない・新規退行ではない）。iter77 が導入した穴ではなく `>` パターン新設時からの既存カバレッジ穴。
- **修正方針（未実施）**: 負クラスを `(^|[^0-9])>>?\s*/(etc|...)` 等へ拡張して `>>` も捕捉。回帰 pin: `echo x >> /etc/passwd`→ask・`echo 2>>log`（fd リダイレクトの誤爆回避）→allow・`a>>b`（非システムパス）→allow。effort S。テーマは redirect 系の網羅で SF-020 と同系だが、case-fold クラスとは別軸ゆえ iter77 スコープ外（焦点保全）。次 iter 候補。
- **状態**: **OPEN（未修正・iter77 で分離起票）**。fail-safe 側（allow・危険方向でない）ゆえ非ブロッキング。

### SF-024: pytest execution attestation の in-process イベント偽造＋attested 手書き天井（**Low・OPEN**・iter78 review 敵対2 finder 検出＝同一ユーザー権限内の OS-limit 残余・fp が moat・防御多層で contain）

- **発見**: iter78 review 敵対 finder 2 体（opus・plan-mode stall→親 in-session 実走裁定・2026-07-28）。attestation（SF-014/SF-022 根治）の残余天井 2 綴りを摘発。
- **種別**: (a) **in-process イベント偽造** — 被テスト suite の `conftest.py` が env の `AEGIS_ATTEST_EVENT_PATH` を読み、偽 `{"e":"test","when":"call","outcome":"passed"}` を追記 → all-skip suite（実 exit 0・実 sessionfinish 0）と合成して `executed>=1` を捏造し attested green を実 writer 経由で製造できる（親再現: rc0・src=attested・counts.executed=1〔実 1 skipped〕）。(b) **attested 手書き天井** — evidence-log に手書きした `src:"attested",status:"ok",fp:<正しい fp>` は fp 一致だけで green（bogus `go test` でも）。judge が read-time に counts を再検証していなかったため counts 皆無でも green だった。
- **重大度**: **Low（OS-limit 残余・非拡大）**。理由: (1) **load-bearing 不変は保持** — 実失敗 suite は real exit code が sessionfinish 突合で勝ち **red 記録**（偽 sessionfinish/pass を注入しても green 化不能・親実走 5a/5c 確認・pin `test_forged_pass_events_cannot_green_a_real_red`）。攻撃で作れるのは「all-skip/all-pass を実行済みに見せる」偽陽性のみで、**本物の red は緑にできない**。(2) 両綴りとも**故意の自己欺瞞**（悪意ある conftest のコミット＝レビュー可能・aegis 内部 env と event schema の知識が必要／evidence-log 直書き）で、脅威モデル（自分の qa gate を欺く）内。(3) **fp が唯一の moat で不変** — attested 手書きは既存の非 pytest manual/observed 手書き天井と同クラス（fp 計算＝git tree 制御が必要）。(4) **防御多層で contain**: drill が subsume（all-skip は marker verdict false → drill baseline BLOCKED・親実走確認）＋human preview＋fingerprint。iter78 は accidental な偽 green（`;true`・`-q`・all-skip 単体・collect-only・fake 出力）を**新たに全封鎖**した net 改善で、残るのは故意偽造のみ（pre-iter78 の echo-class 偽造と同クラス・非拡大）。
- **iter78 review 内の緩和（fix-forward・commit 次段）**: (b) に対し judge の read_test_result_detail に **read-time counts 検証**（attested green は `counts.executed>=1` 必須・欠如/0 は fail-closed unverified）を追加＝「counts 皆無 attested が fp 一致だけで green」の非対称を除去（pin: `test_handwritten_attested_no_counts_fails_closed`／`test_handwritten_attested_zero_executed_fails_closed`）。ただし counts を捏造した手書きは依然 green（trust boundary でなく consistency check・pin `test_handwritten_attested_forge_residual_documented` で天井を documenting）。(a) の in-process 偽造は **exit-reconciliation で red→green を封鎖**する pin（`test_forged_sessionfinish_mismatch_rejected`＝M3 テスト強度 gap の検知者・`test_forged_pass_events_cannot_green_a_real_red`）を追加。
- **post-close hardening（盲検2次 review が約90分後に完走・型混同ホール摘発・2026-07-28）**: 上記 read-time counts 検証に **bool 型混同ホール**があった＝Python の `bool` は `int` の subclass ゆえ `counts.executed: true`（JSON boolean）が `isinstance(int)` を通過し `True>=1` で green 化していた（親再現: green）。実 attestor は int しか吐かないので bool executed は定義上 hand-forged。**Minor（trust boundary 不拡大**＝(b) の手書き天井内で forger は `executed:5` を書けば既に green にできるため attack class は増えない・consistency check の宣言意図が silently 破れる code-clarity 欠陥）。修正: `isinstance(_ex, bool)` を明示拒否（`build-judge-card.py`・単調強化＝forged 形を1つ増やして拒否するだけでゲート結論は不変）。pin=`test_handwritten_attested_bool_executed_fails_closed`（ガード除去で RED を実証）。full 1447 green・contract PASS で回帰なし確認。
- **根本原因/根治**: 同一ユーザー権限内では event チャネル（ファイル・env・fd いずれも子が到達可能）に trust boundary を作れない＝SF-004 と同型の**原理的限界**。真の根治は別ユーザー/コンテナ境界だが **roadmap §6 が「同一ユーザー権限内の署名/秘密鍵による擬似 attestation」を対象外と明示**（trust boundary が増えない）。denylist 的な event 構造検証（setup↔call 対応強制等）は whack-a-mole＝roadmap §5 の反パターンゆえ不採。
- **状態**: **OPEN（accepted residual・iter78 で緩和＋文書化）**。load-bearing 不変（real red は green 化不能）は pin で保証。attestation の正直な限界主張＝「accidental 偽 green は全封鎖／故意の in-process 偽造は OS-limit で残り drill が subsume」。

## CLOSED

- **SF-010**（Medium・iter65 review 検出→iter66 v1.26.1 で封鎖）: task_size empty-baseline raw-Edit × migration-grace の tamper 逃れ。Fix ①（`feff60c` migration-grace を真の旧フォーマット限定に絞り込み・task fields＋gate loop）＋(i)(ii) Fix ⑤（`6229fd5` python first-match/先勝ち）＋(iii) Fix ④（`c5f5fd2` gate_value 本文 fallback を ---無し限定）。hook 直接発火 4 ケース＋fresh 変異 M1-M5＋1次/盲検2次 approve で裏取り。詳細は上記 SF-010 節。

# 案A immutable moat — 設計（iteration 35・rev.2 layer-2）

> brainstorm/discovery は 2026-06-21 の throwaway PoC スパイクで完了（結果は
> `docs/security-followups.md` 「案A PoC findings」）。本書はその実装設計。
> **rev.2（2026-06-21）**: 初版「静的 moat を全退役して OS lock に置換」を設計レビューで
> 撤回し、**OS lock を layer-2 として追加し、`check-control-plane.sh` を cross-platform
> layer-1 として存置**する方針に改めた（理由は下記「方針転換の根拠」）。

## 目的

事故防止スコープにおいて、control-plane への誤書込み防御を **OS/FS レベルの書込み保護
（layer-2）で多層化**する。OS はコマンド文字列を解釈せず syscall で強制するため、
SF-001〜005（quote-split / brace / interpreter `python3 -c` / extglob …）を**形非依存で
まとめて閉じる**——静的解析（layer-1）が原理的に閉じられなかった面（特に SF-004
interpreter コード）を補完する。

### 実測による justification の正し直し（2026-06-21・計画着手時）

設計レビュー後の実測（feature モード scratch）で、**layer-1 が想定より広く事故クラスを
網羅している**ことが判明した:

- `echo>` / `cp` / `rm` / `mv` / `chmod +w` / `chmod -R u+w` / `chflags nouchg` / `chattr -i`
  が CP を対象とする形は **全て `check-control-plane.sh`（Bash matcher）で deny 済み**。
- **Edit/Write/NotebookEdit ツールでの CP 編集も `check-gate.sh`（Edit|Write|NotebookEdit
  matcher）で deny 済み**（task_type 連動）。

→ さらに grill-plan で **SF-004 の「閉鎖」主張が敵対に対して成立しない**ことが判明した:
`chmod`/`chflags` は write 権限ではなく**所有権**で判定されるため、owner（エージェント）は
a-w 下でも `os.chmod(constructed_path, 0o644)` で解錠できる。敵対者は SF-004 と同じ interpreter
channel で解錠してから書けるため、**OS lock は敵対 SF-004 を閉じない**（macOS `chflags uchg` も
`os.chflags(path,0)` で同様に解錠可＝硬化にならない）。SF-004 は「事故」では起きない
（`chr(115)` を偶然書かない）。

→ したがって layer-2（OS lock）の*固有*価値は**ただ1点**に絞られる（正直な位置づけ）:

- **事故ケース限定の独立 syscall 保険**: layer-1（`check-control-plane.sh` 889 行＋`check-gate.sh`）は
  SF-001〜005 の 5 件のバイパス実績がある脆い層。その**未発見バイパスクラスに対する「事故」
  書込み**を、lock がアクティブな間は syscall が形非依存に止める。layer-1 の論理バグ/将来の
  リファクタ退行に対する独立バックストップ（iteration 34 の「hook を fail-open させない」投資の延長）。

普通のコマンド形による「事故」は layer-1 で足りる。layer-2 は穴埋めでも SF-004 閉鎖でもなく、
**事故ケースの多層保険**として lean に実装する。敵対 sandbox ではない。

## 方針転換の根拠（全退役 → layer-2 追加）

初版は `check-control-plane.sh`（889 行）＋ SF-001〜005 を OS lock で**全退役**する計画
だったが、設計レビューで以下が判明し撤回した:

1. **Windows でゼロ保護**: `chmod -R a-w`/`chflags` は POSIX/macOS 専用。Windows ネイティブ
   （git-bash）では `chmod` は実質 no-op。静的 hook（layer-1）は OS 非依存で発火するため、
   全退役すると Windows downstream が無防備化する（将来配布想定）。
2. **EACCES の失敗シグナルが `chmod +w` 自己修復を誘発**: 静的 hook は「control-plane:
   blocked」という**ポリシー停止メッセージ**でエージェントを止める。OS lock は raw EACCES
   （ただの権限エラーに見える）を返すため、CP を誤って触ったエージェントが「権限を直そう」と
   `chmod +w` を前置 → 捕捉済みの事故が未捕捉に転落しうる（敵対意図ではなくエラー復旧の
   自然な挙動）。layer-1 を残せば**casual な誤書込みは PreToolUse で明確に停止**でき、
   EACCES に到達するのは layer-1 が取りこぼす稀・敵対的な形（SF-004 等）だけに限定される。
   **実測（2026-06-21）**: `chmod +w`/`chmod -R u+w`/`chflags nouchg`/`chattr -i` が CP を
   対象とする形は project モードで**既に layer-1 が deny 済み**。よって chmod-unlock guard は
   **新規ロジック不要＝既存挙動を回帰テストで固定するだけ**でよい（②の懸念は既存挙動で解消）。
3. **退役の回帰リスクゼロ化**: layer-1 を残せば 889 行の難読化耐性を捨てずに済む。

→ **OS lock（layer-2）を追加し、layer-1 はそのまま存置**するのが、Windows 保護・
事故停止のエルゴノミクス・回帰ゼロをすべて満たす。退役による行数削減は今回スコープ外。

## スコープと非スコープ

- **追加対象（layer-2）**: 非 framework タスク中、安定 CP パスを OS/FS で書込み不可にする
  lock 機構（`hooks/lib/cp-lock.sh` ＋ session-start 連動）。
- **存置（layer-1・不変）**: `hooks/check-control-plane.sh`（Bash matcher・静的 moat）＋
  `hooks/check-gate.sh`（Edit|Write|NotebookEdit matcher・CP 編集ブロック）。**退役しない**。
  chmod-unlock guard は**既存挙動で担保済**（実測）＝**回帰テストで固定**するのみ（新規ロジック無し）。
- **非スコープ（不変）**: `check-destructive`（破壊コマンド警告）/ `check-secrets` /
  `check-gate`（plan 未承認時の編集ブロック・gate/path 保護）/ deploy gate 群 /
  fail-closed fallback。これらは OS lock と直交で維持。
- **プラットフォーム サポート方針**:
  - macOS / Linux / WSL: layer-1 ＋ layer-2 の二層。
  - Windows ネイティブ（git-bash・非 WSL）: layer-2 は no-op。**layer-1 のみが保護**。
    session-start は chmod 失敗を warn して継続（block しない）。この差は migration guide
    と README に明記する。
- **脅威モデル**: 事故防止（非 sandbox）。エージェントが `chmod +w`/`chflags nouchg` を
  前置すれば書ける＝許容（事故は前置しない／casual な誤書込みは layer-1 が停止）。
  adversary 対策は本設計の目的ではない。

## アーキテクチャ（lock state は task_type 連動・session 単位）

中核の洞察: **lock 状態は STATUS の `task_type` から session-start で決まる**。

| task_type | 安定 CP の状態 | 根拠 |
|---|---|---|
| `feature` / `refactor` / `bugfix` / `hotfix`（プロジェクト作業） | **LOCKED**（`chmod -R a-w`） | エージェントは framework コードを触らない＝誤書込み遮断 |
| `framework`（framework 自体の開発） | **UNLOCKED**（`chmod -R u+w`） | framework コードの編集が正当な作業 |

task_type は session 内で原則不変なので、**session-start で 1 回 lock/unlock を決めれば足りる**。

- **default は LOCKED**: 安全側に倒す。session-start が走らない/失敗しても、
  既に locked なら project 作業は保護されたまま。
- **lifecycle re-lock**: iteration rollover（`dev_ready_for_client` 後に task_type が反転
  しうる稀ケース）に備え、session-start に加え **phase/iteration 遷移点でも lock 状態を
  再計算**する（具体的フック点は実装計画 §未確定#1 で確定）。
- **crash 窓**: 「framework session 中（unlocked）に crash → CP unlocked のまま」だが、
  次 session-start で default-LOCK 判定により再 lock。窓は限定的。

## コンポーネント（File Structure）

- `hooks/lib/cp-lock.sh`（新規）— `aegis_cp_paths`（lock 対象列挙）/ `aegis_cp_lock` /
  `aegis_cp_unlock`。pure-bash・bash 3.2 安全・冪等。
- `hooks/session-start.sh`（改修）— 末尾で task_type を読み、`cp-lock.sh` を呼んで lock/unlock。
- `hooks/check-control-plane.sh`（**改修なし・回帰テスト追加のみ**）— chmod-unlock guard は
  既存挙動で担保済（`chmod +w`/`chflags nouchg`/`chattr -i` が CP 対象なら project モードで
  既に deny）。新規テストで「CP 対象の chmod/chflags/chattr unlock 形 → deny」を固定し、将来の
  リファクタで退行しないようにする。
- **安定 CP セットの単一所有**: `hooks/lib/cp-lock.sh` の `aegis_cp_paths` が **chmod 対象の
  FS パス列挙**を所有する。`check-control-plane.sh` の `CONTROL_PLANE` 正規表現とは**統合しない**
  ——前者は FS パスの列挙（layer-2 の chmod 対象）、後者はコマンド文字列トークンの照合（layer-1）で
  ドメインが異なり、無理な統合はかえって脆くなる。`platform_manifest.py`（volatile-truth 専用）には
  載せない（CP セットは stable-structural）。
- **退役しない**: `hooks/check-control-plane.sh`・`hooks/lib/`（`emit.sh`/`safety.sh`/
  `evidence.sh`/`patterns.sh` 等は**全 hook 共有インフラ**で CP 専用ではない）・SF-001〜005
  の OPEN 項目（layer-2 は事故ケースを多層保険で軽減するのみ・**CLOSED にはしない**＝下記 §SF 対応）。

## 安定 CP セット（lock 対象）と除外

**LOCK（chmod a-w）**: `hooks/*.sh`・`hooks/lib/*.sh`・`scripts/*.py`・`scripts/*.sh`・
`CLAUDE.md`・`.claude/rules/`・`.claude/skills/`・`.claude/commands/`・`templates/`・
`.claude/agents/`。

> **rename/move gap は repo root を lock しない**（rev.2 当初案を撤回）: `mv hooks hooks_bak`
> は親 root の write だけで通るが、**downstream の install では root はユーザーのプロジェクト
> root** であり、ここを `a-w` にすると**ユーザーが自分のプロジェクトに新規 top-level ファイルを
> 作れなくなる**（過剰）。一方 `mv hooks …`/`cp x hooks` 等の CP operand を持つ rename/move は
> **layer-1（check-control-plane）が既に deny** する（実測）。よって root は lock せず、
> mv/rename gap は「layer-1 でカバー＋form 難読化した mv は adversarial＝スコープ外」の
> **accepted residual** とする。

**除外（常に writable）**: `docs/STATUS.md`・`.claude/.gate-snapshot`・
`.claude/evidence-log.jsonl*`・`.claude/.audit-skip.log`・`.claude/.task-event-debug.log`・
`docs/`（STATUS 以外の成果物）・`.claude/.aegis-install-version`・
**`.claude/settings.json`・`.claude/settings.local.json`（両方）**。

> **settings は両方とも layer-2 除外**（grill#2・初版/rev.2 当初案を撤回）: (1) **Claude Code
> ハーネス自身**が permission grant（"常に許可"）や hook 更新を settings（特に
> `settings.local.json`）へ書く。lock すると EACCES でサイレント破損し、ユーザーの「常に許可」
> 等が無言で効かなくなる。検証で「runtime writer 無し」を確認したのは hooks/ のみで、
> ハーネスの書込みを見落としていた。(2) 実環境では hook 登録が `settings.local.json` にある
> ケースがある（本リポがそう・`settings.json` は不在）＝lock しても無意味/逆効果。
> (3) settings は **layer-1 で既に保護済**（`check-gate` が Edit、`check-control-plane` が
> Bash 書込み、`check-skill-gate` が settings.json 改変 skill を deny）。よって layer-2 では
> settings に触らず layer-1 に委ねる。

> 旧静的 moat は code と runtime-state を混在判定していた。OS lock は両者を**物理的に分離**
> でき、むしろ綺麗（STATUS.md は update-gate.sh が常時書くので必ず除外）。

## プラットフォーム

- **主機構: `chmod -R a-w`** — cross-platform・root 不要・owner 可逆（事故防止に最適）。
  ディレクトリも `a-w` にすることで entry の作成/削除/rename を封じる（`-R` が両方を担う＝
  load-bearing）。
- **macOS `chflags uchg` は不採用**（grill#1）: owner の `chmod +w` は封じるが、敵対者は
  `os.chflags(path,0)` を interpreter で実行して解錠でき硬化にならない。事故には chmod a-w で
  十分。macOS 分岐の複雑度のみ増えるため採用しない。
- **`chattr +i`（Linux）も不採用**（root 必要）。Linux/macOS とも `chmod` のみ。
- **Windows ネイティブ**: `chmod`/`chflags` は no-op。layer-2 は機能せず layer-1 のみで保護。
  session-start は lock 失敗を warn。

## Error handling / fail 方針

- lock 失敗（chmod が一部 path で失敗 / Windows no-op）→ session-start で **warn**
  （block しない・session-start は injection 用）。OS lock は「層」であり、`check-gate` 等の
  fail-closed は別途維持。layer-1 が常時存在するため lock 失敗でも moat は残る。
- unlock 失敗 → framework タスクで CP 編集が EACCES になる → ユーザーに可視（明確なエラー）。
- **EACCES エルゴノミクス**: casual な CP 誤書込み（Bash も Edit/Write も）は layer-1 が
  **ポリシーメッセージで停止**するため EACCES に到達しない。EACCES に達するのは layer-1 が
  取りこぼす稀・敵対的な形（SF-004 interpreter コード等）のみ。さらに「EACCES を見て
  `chmod +w` で自己修復」しようとしても、その `chmod +w hooks/x` 自体を layer-1 が deny する
  （実測済・回帰テストで固定）。

## SF-001〜005 の対応（layer-2 導入後・grill#1 反映）

- **CLOSED にはしない**。layer-2 は lock がアクティブな間の**事故**書込みを syscall で止める
  （defense-in-depth）が、敵対者は `os.chmod`/`os.chflags` で解錠してから書けるため SF-001〜005
  の脅威としての残存は変わらない（特に SF-004 は静的・OS どちらでも敵対閉鎖は原理的に不可）。
- `security-followups.md` の各項目には「iteration 35 で layer-2 を defense-in-depth として追加・
  事故ケースは多層保険で軽減・敵対は CLOSED にしない・Windows は layer-2 no-op」と**状態追記**する
  （CLOSED へは移さない）。
- この更新は実装が main にランドした後に反映（本設計では方針のみ宣言）。

## テスト戦略（TDD）

- `tests/test_cp_lock_lib.py` — `aegis_cp_lock` 後に scratch CP へ `echo>`/`cp`/`rm`/
  **`python3 -c open(w)`** が全て EACCES（file INTACT）。`aegis_cp_unlock` 後に書込み可。
- **SF-001〜005 再現カタログ全形**を lock 下で実走 → lock がアクティブな間は全て EACCES
  （CP INTACT）を実証（quote-split・backslash・interpreter）。**defense-in-depth 証拠**
  （事故ケースの形非依存阻止）であり、敵対 SF-004 閉鎖の証明ではない（os.chmod 解錠は別途残る）。
- **rename/move gap**: root は lock しない方針。`mv hooks hooks_bak`/`cp x hooks` は
  **layer-1（check-control-plane）が deny** することを回帰テストで固定（OS lock ではなく layer-1 担当）。
- **chmod-unlock 回帰**: CP 対象の `chmod +w`/`chmod -R u+w`/`chflags nouchg`/`chattr -i` が
  project モードで layer-1 deny・非 CP の `chmod 755 src/app.py` は allow、を固定。
- runtime-state 除外: lock 中も `docs/STATUS.md`・`.gate-snapshot`・`evidence-log` が writable。
- session-start 連動: task_type=feature → CP locked / task_type=framework → unlocked。
- **テスト skip**: Windows（`chmod` no-op）＋ **root（`geteuid()==0`・a-w を無視）** を skip。
  Windows では session-start が lock 失敗を warn して継続することを確認。
- layer-1 回帰: 既存 `test_control_plane_*.py` は**存置**（layer-1 は退役しないため）。

## SemVer / 移行

- layer-1 は退役せず、layer-2（cp-lock + session-start 連動）を**追加**＝public contract は
  拡張のみで後方互換 → **MINOR バンプ**（例 1.12.1 → 1.13.0）。実装時に確定。
  ただし既存 install は upgrade 後に project 作業中 CP が read-only 化する**挙動変化**が
  あるため、migration note は必須（破壊的ではないが可視）。
- 移行ガイド（README）: 「OS lock 追加・task_type 連動・Windows は layer-1 のみ・unlock は
  framework task_type で自動」＋ **on-disk read-only がセッション外（エディタ）にも残る**・
  **framework 更新（`git pull`）は framework mode で行う**注意を記載。settings は lock しない。

## 決定事項（計画着手時に確定）と未確定

**確定**:
- 価値の射程 = 事故ケース限定の独立 syscall 保険（defense-in-depth）。**敵対 SF-004 は閉じない**
  （owner os.chmod 解錠）・SF 項目は CLOSED にしない。
- 安定 CP セットの単一所有 = `hooks/lib/cp-lock.sh` の `aegis_cp_paths`（`platform_manifest` には
  載せない・`check-control-plane` 正規表現とは統合しない）。
- chmod-unlock guard = 新規ロジック無し（既存 layer-1 で deny 済）・回帰テストで固定。
- mv/rename gap = root を lock せず layer-1 でカバー＋accepted residual。
- settings = `settings.json`・`settings.local.json` とも **layer-2 除外**（ハーネスが書く・layer-1 で保護済）。
- macOS `chflags uchg` = **不採用**（敵対に無力・複雑度のみ増）。
- lifecycle re-lock = MVP は default-LOCK＋session-start で吸収・`post-status-audit` への
  phase 遷移 re-lock は繰延（毎遷移 chmod -R のコスト/複雑度に見合わず）。
- テストは Windows＋root を skip（root は a-w を無視）。

**未確定（残）**:
1. lifecycle re-lock の繰延残余（framework session 中 rollover で task_type 反転＋次 session-start
   前に CP 操作する窓）を将来埋める必要が出るか（現状は次 session-start で再 lock＝許容）。

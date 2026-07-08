# iter63 独立セキュリティ2次レビュー（盲検）

- 対象: `bin/setup.sh` self-heal unlock（R3）差分 92 行 ＋ 依存 `hooks/lib/cp-lock.sh`
- レビュア: 独立2次（1次判定は未参照）
- 日付: 2026-07-08
- 手法: 静的読解（named ファイル＋直接依存に限定・全体探索なし）
- 総合判定: **approve_with_notes**（HIGH/MEDIUM なし・LOW/informational のみ）

## 観点バッチ（有界・番号付き）

観点を 6 バッチに分割。各バッチに {action / expected / observed / verdict}。

---

### 観点1: unlock の発火条件と範囲（任意 --target を chmod しないか／symlink 追従／framework 自身のソース木を触らないか）

**action**: `selfheal_unlock_target()`（setup.sh L622-666）の発火ゲートと unlock 対象集合を、
`aegis_cp_paths`/`aegis_cp_unlock`（cp-lock.sh L22-68）まで追跡。TARGET 解決（L117, L122-126）と
FRAMEWORK_ROOT（L37）を確認。

**expected**: 発火は「aegis install かつ実 lock 検出」の AND。unlock 対象は CP path 集合に限定。
symlink 非追従。framework 自身のソース木は対象外。

**observed**:
- ゲートは 3 段 AND: (a) `AEGIS_SETUP_SELFHEAL != off`、(b) marker 存在
  （`.claude/.aegis-install-version` **or** `hooks/lib/cp-lock.sh`）、(c)
  `aegis_cp_verify "$target" framework` の非空 findings（＝実際に非 writable な CP path がある）。
  3 つ全てを満たさないと `aegis_cp_unlock` に到達しない（L636-660）。
- unlock 対象は `aegis_cp_paths` の固定集合（`hooks scripts templates CLAUDE.md
  .claude/{rules,skills,commands,agents}`）を `${target}/` 前置したものだけ（cp-lock.sh L27-37）。
  任意 path は列挙されない。`.claude/settings*.json` は意図的に対象外（L24-26）。
- symlink: `aegis_cp_unlock`/`aegis_cp_verify` とも `find "$p" ! -type l -exec chmod u+w {} +`
  で symlink エントリを除外（cp-lock.sh L64-65, L105）。chmod は symlink を追従して
  CP 外の実ファイルを触ることはない（iter55/iter57 の symlink-pierce 対策が依存側に実在）。
- framework ソース木: unlock 引数は `$TARGET`（install 先）であり `$FRAMEWORK_ROOT` ではない。
  source は framework 側だが、chmod 対象は TARGET のみ。さらに setup.sh は
  `TARGET_REAL == FRAMEWORK_ROOT_REAL` を pwd -P（symlink 解決）で拒否する（L120-127）。
  ゆえに framework 自身のソース木を unlock する経路は存在しない。

**verdict**: PASS。発火は適切に絞られ、範囲は CP path 集合＋TARGET subtree に限定、
symlink 非追従、framework ソース木は不可侵。

---

### 観点2: source する cp-lock.sh は信頼側か（target への悪性ファイル植え込みで実行できるか）

**action**: `source "$cplib"`（L644, L650）の `cplib` 由来を確認。cp-lock.sh の
top-level 副作用有無を全読。marker leg (b) が target path を読む点を精査。

**expected**: source 対象は framework 側の固定 lib。target 側の同名ファイルは実行されない。
cp-lock.sh は関数定義のみで top-level 実行なし。

**observed**:
- `cplib="$FRAMEWORK_ROOT/hooks/lib/cp-lock.sh"`（L644）。source は **必ず framework 側**。
  `$target/hooks/lib/cp-lock.sh` は marker 判定（L637: `[ -f ]` 存在テストのみ）に使うだけで、
  **source も実行もしない**。攻撃者が target に悪性 `hooks/lib/cp-lock.sh` を置いても、
  installer は自分（framework）側の lib を読むため、コードは注入されない。
- cp-lock.sh は L1-19 のコメントと L22-122 の関数定義のみ。top-level に実行文・
  `set` 切替・変数破壊なし。source は関数を定義するだけ（rc0）で `set -euo pipefail` 下でも
  abort しない。関数名は `aegis_cp_*` で namespaced、setup.sh の `copy_file` 等と衝突なし。
- FRAMEWORK_ROOT は setup.sh 自身の位置由来（L36-37）。ここを書ける攻撃者は既に
  「実行中の framework 本体」を書けており、任意コード実行と等価＝この diff の scope 外
  （設計書 §セキュリティ考慮 L108-111 と一致）。

**verdict**: PASS。source は信頼側（framework）に固定。target 経由のコード注入経路なし。

---

### 観点3: コマンド/パスインジェクション（敵対的なファイル名・パス）

**action**: 新規/変更コードの変数展開・`echo`・`find`・`dirname`・while ループを
インジェクション観点で精査。`eval`/`bash -c "$var"`/未クォート glob の有無を確認。

**expected**: 全変数クォート済み。`eval` なし。stderr 出力は表示のみで再実行されない。
ancestor walk は有界。

**observed**:
- `explain_unwritable_dst`（L155-176）: `dst` `d` `why` は全て `"..."` クォート。
  `[ -e "$dst" ]` `[ ! -w "$dst" ]` `dirname "$dst"` `[ ! -d "$d" ]` すべてクォート。
  `eval` なし。`$dst`/`$d`/`$why` は `echo … >&2` で表示するのみ（コマンドとして再評価されない）。
- `selfheal_unlock_target`（L631-665）: `target` `cplib` `locked` クォート。
  `aegis_cp_verify "$target"` `aegis_cp_unlock "$target"` クォート済み。
- ancestor walk（L162-164）: `while [ ! -d "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]` は
  dirname が最終的に `/` に到達して停止。TARGET は L117 で `cd && pwd` により絶対パス化され、
  dst は `$target_dir/...` 構成の絶対パスなので相対/`.` に落ちない。**無限ループなし**。
- cp-lock.sh 側 `find "$p" ! -type l -exec chmod {} +`: `-exec … +` はシェル再解釈を挟まず
  argv 直渡し。悪意あるファイル名（スペース/改行/メタ文字/`$(…)`）でも安全。

**verdict**: PASS。クォート徹底・`eval` 不在・出力は表示専用・walk 有界。注入経路なし。

---

### 観点4: fail-open か fail-closed か（env off／marker 無／lib 無／部分 unlock 失敗／混在版のサイレント成功再発）

**action**: 各分岐の帰結を追跡。特に「copy が黙って成功して混在木を残す」経路が
新設されていないかを copy_file/copy_file_force（L200-273）で確認。

**expected**: セキュリティ的に危険な方向（silent mixed version）へ倒れないこと。
lock 済みで copy 不能な場合は必ず loud abort（exit 1＋帰属）。

**observed**:
- `AEGIS_SETUP_SELFHEAL=off`（L632-634）: heal skip → lock 済み target では後段 cp が失敗し
  `explain_unwritable_dst`→`exit 1`。**fail-closed**（T3 が pin）。
- marker 無（L636-639）: heal skip。非 aegis の read-only target は cp 失敗で `exit 1`。
  **fail-closed・chmod せず**（T4 が perms 不変を pin）。
- lib 無（L644-648）: WARNING→return。lock 済みなら cp 失敗で帰属 abort。**fail-closed**。
- 部分 unlock 失敗（L661-663, `aegis_cp_unlock` rc1）: WARNING して続行。残った lock で
  copy が失敗すれば `exit 1`。**fail-closed**（cp-lock ヘッダ「failure is NON-fatal」慣習に一致・
  実害は帰属エラーで顕在化）。
- **混在版サイレント成功の再発**: `copy_file`/`copy_file_force` の `mkdir -p`・`cp`・`cp -f` は
  すべて `if ! …; then explain; exit 1; fi`（L227-234, L263-270）。cp 失敗が rc0 で握り潰される
  経路は新設されていない。ファイル単位の cp は原子的で、失敗＝即 exit 1。
  self-heal で unlock 済みなら完全 upgrade、heal off/失敗なら loud abort。
  **新たな silent-mixed 経路なし**。
- 補足: `.bak` の best-effort `|| true`（L259）は copy_file_force 側の既存 D3 仕様で、
  self-heal が copy 前に走るため upgrade 時は unlock 済み＝`.bak` も成功する。
  copy_file 側の `.bak` 失敗は `exit 1`（L219-222）で fail-closed。
- verify 意味論: task_type=`framework` の verify は `! -perm -u+w`（＝非 writable = lock 状態）を
  findings とする。非空 → unlock。half-locked（iter40）も全列挙で検出・全走査で復旧。整合。

**verdict**: PASS。全分岐が安全側（fail-closed）。silent mixed-version の再発経路なし。

---

### 観点5: ログに秘密・env 値が漏れないか

**action**: 新設 `echo`/WARNING/NOTE/ERROR 出力の内容を精査。

**expected**: 秘密・env 値を印字しない。

**observed**:
- 出力される値は path 名（`$dst` `$d` `$target`）と固定文言のみ。
- env は `AEGIS_SETUP_SELFHEAL` の **名前** を remedy 文言で言及するだけ（L170）。
  値は印字しない。他の env（秘密含む）を印字する箇所なし。
- unlock/verify は stdout/stderr に path 名しか出さない（cp-lock.sh は秘密を扱わない）。

**verdict**: PASS。秘密・env 値の漏洩なし。

---

### 観点6: 権限昇格の有無（chmod が owner 書込み復元を超えるか）

**action**: unlock の chmod 実体（cp-lock.sh L65）を確認。ownership/setuid/group-other への
波及を精査。

**expected**: `chmod u+w` のみ（owner 書込みビット復元）。所有者変更・setuid/setgid・
group/other 付与なし。

**observed**:
- `aegis_cp_unlock`: `find "$p" ! -type l -exec chmod u+w {} +`（cp-lock.sh L65）。
  **owner の write ビットのみ付与**。lock（`chmod a-w`）の逆操作で、元の owner-writable 状態に戻すだけ。
- 所有権変更（chown）なし。setuid/setgid（`u+s`/`g+s`）付与なし。group/other write 付与なし。
- 対象は TARGET subtree の CP path のみ（観点1）。TARGET は install に owner-writable が
  前提のディレクトリ。よって「installer 実行ユーザーが元々持てる権限」を超えない
  （設計書 L110「owner の chmod u+w が常に可能なことと等価」と一致）。

**verdict**: PASS。owner 書込み復元に限定。権限昇格なし。

---

## Findings（severity 付き）

HIGH / MEDIUM: **なし**。

### LOW-1 (informational): marker leg のフィンガープリント緩さ
発火ゲート leg (b) は `.aegis-install-version` **or** `hooks/lib/cp-lock.sh` 存在の OR。
非 aegis プロジェクトがたまたま `hooks/lib/cp-lock.sh` という path を持ち（例: aegis の cp-lock を
vendored したが full install していないフォーク）、かつ CP 名のディレクトリを owner が意図的に
read-only にしていた場合、verify-lock 検出も満たせば self-heal がそれらに `chmod u+w` する。
影響は限定的（(1) verify で実 lock 検出も必要、(2) chmod u+w＝owner 書込み復元のみ、
(3) TARGET subtree の CP 集合内、(4) 昇格・所有権変更なし・symlink 非追従）。
脅威モデル（偶発書込み防御）の残余として受容範囲。設計書の「aegis install マーカー」定義とも一致。
対処不要（記録のみ）。

### LOW-2 (informational・accepted residual): default-on による意図的 unlock 窓
`AEGIS_SETUP_SELFHEAL` 既定 on のため、target セッション内でエージェントが framework の
setup.sh を実行すれば moat を一時 unlock できる。ただし setup.sh 実行＝任意スクリプト実行と
等価で、owner はいつでも chmod できる。NOTE 出力で可視・監査可能。設計書 §セキュリティ考慮
L108-111 で明示的に受容済み。純粋にセキュリティ最保守なら default-off（fail-closed）も選べるが、
「documented upgrade path が全 install で死ぬ」という R3 の核を解く目的と、脅威モデル（意図的
多段バイパスは scope 外）を踏まえると default-on は妥当。env seam は capability を**減らす**方向
（off = fail-closed）のみでバイパス lever にならない点も確認済み。対処不要。

## 独立に気づいた相違点（divergence_points）
- 実装は設計書・計画と整合。プロンプト背景の懸念（任意 --target chmod／symlink 追従／
  framework ソース木／target 経由コード注入／injection／silent mixed／秘密漏洩／昇格）は
  すべて否定的に確認（該当なし）。新規の HIGH/MEDIUM 相違は検出せず。
- 唯一の質的相違: marker gate が AND ではなく leg (b) 内に OR を含む点（LOW-1）。ただし
  これは設計の「marker」定義通りで、実害は owner-chmod 等価に留まる。

## 結論
diff は well-scoped・fail-closed（セキュリティ関連分岐は全て安全側）・注入なし・昇格なし・
symlink pierce なし・source は信頼側固定・秘密漏洩なし。**approve_with_notes**（LOW 2件は
いずれも設計で受容済みの残余で対処不要）。

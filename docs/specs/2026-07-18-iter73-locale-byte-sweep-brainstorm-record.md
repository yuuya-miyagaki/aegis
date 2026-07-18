# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-07-18

## テーマ

- iter73 = locale/byte-injection 掃討。iter72 F-CRIT-1（marker.sh の locale 依存 grep が
  UTF-8 下で不正バイトに脆弱→false-GREEN）と**同型の locale 依存 tr/grep が deny 側 moat
  フックに残存**しないか掃討し、成立すれば byte-wise 決定化（`LC_ALL=C`）で封鎖する。

## コンテキスト

- 現在の状況: iter72 で marker.sh に `LC_ALL=C LC_CTYPE=C LANG=C`（関数 local scope）を入れ
  false-GREEN を封鎖済み（commit 90b4b61）。deny 側の `check-destructive.sh`（grep 6・tr 2）と
  `check-secrets.sh`（grep 17・tr 6）は LC_ALL 設定ゼロ（実測 2026-07-18）。
- きっかけ: iter72 security 盲検2次が「1次 approve を独立レビューが reject で摘発」した
  divergence が High バグの在処だった前例。deny 側同型が成立すれば「破壊的コマンド/シークレット
  のとりこぼし＝fail-open」で moat より深刻という仮説（next_action の HIGH 仮説）。

## 実証で判明した事実（過大評価の回避＝「限界は実証してから主張する」）

> next_action の「HIGH 相当」仮説を、実測で **hardening/Medium 止まり** に**格下げ**する。

1. **支配的機構は grep 取りこぼしではなく `tr` クラッシュ**（実測）。フックは非対話 bash で
   `/usr/bin/grep`＝**BSD grep** を使う（対話シェルの ugrep エイリアスではない）。BSD grep は
   末尾に不正バイト（0xFF）があっても `rm -rf` 等を**正しく MATCH**（取りこぼさない）。真の
   fail-open 経路は、`CMD_LOWER=$(printf '%s' "$CMD" | tr '[:upper:]' '[:lower:]')` の **`tr` が
   UTF-8 locale で不正バイトに `Illegal byte sequence` でクラッシュ**し、`set -euo pipefail` に
   より**フックが rc=1・stdout 空で異常終了**する点。moat チェックに到達する前に落ちる。
2. **スコープは check-destructive.sh と check-secrets.sh に限定**（実測）。両者は `extract_command`
   の grep fast-path で raw バイトを保持した CMD を得てから `tr` する→クラッシュ。一方
   `check-runtime-state.sh`・`check-deploy-gate.sh` は python3 json 抽出でバイト→空 CMD になり
   （UnicodeDecodeError→`|| true`）tr に届かず、または tr 前に BSD grep（バイト安全）を通る＝
   **crash しない**（byte-in-CMD で rc=0・`{}` を実測）。next_action の想定2本が正しい。
3. **valid な多バイト（日本語）は影響なし**（実測）。`rm -rf ~/プロジェクト`→ask、
   `git add テスト/.env`→deny が現状でも正しく動く。BSD tr/grep は valid UTF-8 を処理でき、
   クラッシュは**不正バイト列に固有**。よって i18n（日本語パス/コミットメッセージ）の
   事故的経路では発火しない＝**日本語ユーザーは安全**。
4. **不正バイトでの fail-open 自体は宣言済みポリシー**。`docs/hook-failure-policy.md`＝
   「入力パース失敗時は全 hook allow（誤 deny を避ける）」。よって crash→allow はポリシー準拠の
   帰結でもある。ただし crash（rc1・出力なし）は「常に JSON 判定を emit し exit 0」という
   フック契約からの**逸脱**であり、かつ**フック自身が持つ raw-payload fail-safe フォールバック**
   （check-destructive.sh:38-54 が抽出失敗時に raw scan→emit_ask）を**下流の tr crash が迂回**する。
5. **`LC_ALL=C` で `tr` crash は消える**（実測 rc=0）。全パターンは ASCII＋literal のため byte-wise
   が正。ただし**素朴に script 全体へ export すると上流の python3 json 抽出が C locale で valid
   UTF-8 を読めなくなる**懸念（iter72 が関数 local scope にした理由と同根）＝配置に注意。

## 検討したアプローチ

### アプローチ A: 抽出後に `LC_ALL=C` を export（各フック 1 行）【推奨】

- 概要: `CMD=$(extract_command "$INPUT")` の**直後**（python3 抽出が済んだ後）に
  `export LC_ALL=C LC_CTYPE=C LANG=C` を置き、以降の全 tr/grep/sed を byte-wise 化。
  両フックとも抽出後に python3 を呼ばない（実測）ため C locale 汚染が起きない。
- 利点: 1 フック 1 行＝最小 footprint・可読・全 tr/grep を漏れなく被覆（23 箇所を個別に触らない）。
  iter72 の LC_ALL=C 方針と一貫。crash（tr）と GNU grep poison の両方を一括で封鎖。
- 欠点: 「抽出後は python3 を呼ばない」前提に依存＝将来 python3 を下流に足すと C locale 下で走る
  （テストと設計コメントで pin する）。`[ -z "$CMD" ]` の raw-input fallback ブロックも tr を使う
  ため export はそのブロック**より前**（＝抽出直後）に置く必要がある。

### アプローチ B: tr/grep を個別に `LC_ALL=C <cmd>` prefix

- 概要: `printf ... | LC_ALL=C tr ...`・`LC_ALL=C grep ...` を 23+ 箇所へ個別付与。
- 利点: 汚染範囲が各パイプに限定＝python3 と完全非干渉。iter72 の「必要箇所だけ」に最も忠実。
- 欠点: 23+ 箇所の機械的改変＝差分肥大・付け漏れリスク（1 箇所落とすと穴が残る）・レビュー負荷大。
  control-plane の大量小改変は「rushed control-plane 変更は新規バグ源」の戒めに逆行。

### アプローチ C: 共有ヘルパー関数化（`aegis_force_byte_locale`）＋ crash-safe trap

- 概要: safety.sh 等に `aegis_force_byte_locale(){ export LC_ALL=C LC_CTYPE=C LANG=C; }` を足し
  各フックが抽出直後に呼ぶ。加えて `trap 'emit_allow' ERR` 等で「未捕捉エラーでも必ず JSON を
  emit し rc0」に契約を強化（crash→allow をポリシー準拠の明示 allow に格上げ）。
- 利点: DRY・crash-safe 契約でバイト以外の未知クラッシュにも fail-safe。
- 欠点: 4 フック以上に配る/共有 lib を触る＝blast radius 拡大。trap は control-plane 挙動の
  構造変更＝独立設計＋盲検が要る大玉。今回のテーマ（locale/byte 掃討）を超える scope creep。

## 決定

- 採用アプローチ: **A（抽出後に `LC_ALL=C` export・各フック 1 行）**。
- 採用理由: 実証で判明した footprint（2 フック・crash が支配機構）に対し最小で漏れない。iter72
  方針と一貫。両フックが抽出後 python3 非依存という前提を**設計コメント＋テストで pin**すれば
  A の唯一の欠点は塞げる。B は付け漏れリスクと差分肥大、C は scope creep で不採用。
- crash-safe trap（C の後半）は**今回やらない**（YAGNI・control-plane 構造変更は別テーマ）。
  ただし「crash がフック契約逸脱＋fail-safe fallback 迂回」である点は設計に記録し、恒久的な
  crash-safe 契約は将来 SF/レビュー候補として残す。

## スコープ境界

- やること:
  - `check-destructive.sh`・`check-secrets.sh` の抽出直後に `LC_ALL=C LC_CTYPE=C LANG=C` を export。
  - 回帰 pin（両フック）: (a) 不正バイト混入コマンドで **crash せず**（rc=0・JSON emit）かつ
    実破壊的/実シークレット対象に対し従来どおり **ask/deny** を維持、(b) valid 多バイト（日本語）で
    従来どおり ask/deny、(c) fix 前は crash（rc≠0）を再現する非空 pin（iter72 の pin 流儀）。
  - 「抽出後 python3 非依存」不変を守る設計コメント＋（可能なら）静的 pin。
- やらないこと:
  - `check-runtime-state.sh`・`check-deploy-gate.sh` の改変（実測で crash せず＝同型不成立。
    掃討の完全性として「調査して非該当」を設計に記録）。
  - crash-safe trap 等の control-plane 構造変更（YAGNI・別テーマ）。
  - Low な SF（011/012/013/015）の先食い（網羅レビューが再優先度付け）。
  - grep パターン自体の変更（BSD/GNU 差の追求は iter71 の cross-engine 教訓の範囲で、今回は
    locale 決定化に限定）。

## 未解決事項

- なし（severity は実証で hardening/Medium と確定。fix 方針・スコープ・pin 方針まで確定）。

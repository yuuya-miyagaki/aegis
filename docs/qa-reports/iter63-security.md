# iter63 セキュリティレビュー（PRIMARY security role）

- 日付: 2026-07-07
- レビュア: security 1次（in-session・Opus 4.8＝security ロール pin の opus/max 相当。read-only 準拠）
- 手法: aegis-security-gate Step 0（公式 `security-review` スキル起動）→ 空 diff を実 diff で補い、脆弱性同定 → FP フィルタ → confidence<8 除外を in-session 適用（対象 92 行・全経路トレース済のため subagent 分割は不要かつハング根本回避）
- 対象: iter63 diff = `bin/setup.sh`（self-heal / R3・+92/-4）+ 新規 `tests/test_setup_locked_target_upgrade.py`（テストのみ）
- 仕様: `docs/specs/2026-07-07-iter63-setup-self-heal-design.md` §セキュリティ考慮（受容残余 (a) unlock 窓／(b) session 内 setup 実行）
- 先行レビュー参照: `docs/qa-reports/iter63-review.md`（symlink 被害者 / 偽 marker / DIST-12 の実プローブ済・approve_with_notes）

## 1. 堀の完全性（layer-1/layer-2 弱体化の有無・残余 (a)(b) のスコープ）

- self-heal は layer-2（OS/FS write-lock）を copy 前に**一時 unlock** し、**再 lock しない**。再 lock は
  target の次回 session-start（`aegis_cp_apply`）が task_type に応じて復元する（NOTE 2行で可視化）。
- layer-1（静的 moat＝`patterns.sh` のコマンドトークン照合）は lock 状態と**独立に常在**。cp-lock.sh
  ヘッダも「OS lock is a defense layer, not a fail-closed gate — layer-1 static moat is always present」と明記。
  ゆえに layer-2 の一時 unlock は layer-1 を弱体化しない。
- unlock 窓（＝残余 (a)）: setup 完了〜次回 session-start まで target CP が writable。これは通常の
  framework-mode セッションと同じ露出であり、実行者＝upgrade を行う owner 自身の端末。**新規攻撃面ではない**。
- verdict: **PASS**（moat 弱体化なし。窓は既存 framework-mode と等価な受容残余）。

## 2. アンロック範囲（aegis_cp_paths 限定・symlink ガード・TARGET 正規化・DIST-12 順序）

- 発火ゲート＝**AND**: (a) aegis install マーカー（`$target/.claude/.aegis-install-version` **or**
  `$target/hooks/lib/cp-lock.sh`）**かつ** (b) 実 lock 検出（`aegis_cp_verify "$target" framework` が非空）。
  → マーカーなしの任意 read-only `--target` は return（黙）で**触らない**。テスト T4 が perms byte 不変を pin。
- unlock 対象は `aegis_cp_paths` の固定集合（hooks/scripts/templates/CLAUDE.md/.claude/{rules,skills,commands,agents}）
  に限定。`.claude/settings*.json` は意図的対象外（cp-lock 設計どおり）。任意 path を触らない。
- symlink: `aegis_cp_unlock` は `find "$p" ! -type l -exec chmod u+w {} +`＝リンク自体を skip（追従して CP 外の
  実ファイルを chmod しない・iter57 symlink-pierce 教訓を保全）。
- TARGET 正規化: L116 `TARGET="$(cd "$TARGET" && pwd)"` で正規化後に self-heal（L676）が走る。
- DIST-12 順序: DIST-12 guard（L119-128・`TARGET_REAL == FRAMEWORK_ROOT_REAL` → abort）が self-heal より**前**。
  → target=framework root は heal 到達前に abort＝自身のソース木を unlock しない（review S2/S4 実測）。
- verdict: **PASS**（二重ゲート＋固定集合＋symlink-safe＋正規化・DIST-12 の後段配置で範囲は最小）。

## 3. インジェクション（explain_unwritable_dst / NOTE echo・敵対的ファイル名）

- `explain_unwritable_dst`: `$dst`/`$d` はいずれもクォート展開（`echo "…$dst"`・`dirname "$dst"`・`[ -e "$dst" ]`）。
  `eval` なし・変数値のコマンド置換再評価なし＝敵対的ファイル名（`$(...)`・改行・メタ文字）を含んでも
  echo 引数として渡るだけでコマンド化しない。祖先遡り while は `/`・`.` で停止（bounded）。
  なお `$dst` は framework 内部の template マッピング由来で untrusted 入力ではない（Precedent #12 非該当）。
- NOTE/WARNING echo: 静的文字列のみ（変数補間なし）。
- verdict: **PASS**（command/path injection なし）。

## 4. fail-open / fail-closed 棚卸し（env off / marker 無 / cplib 無 / verify 空 / unlock rc1・混在版サイレント成功の再発有無）

| 条件 | 挙動 | 判定 |
|------|------|------|
| `AEGIS_SETUP_SELFHEAL=off` | heal skip → locked なら cp 失敗 → `explain_unwritable_dst` → **exit 1** | fail-**closed**（帰属 token 出力・T3 pin） |
| marker 無（非 aegis target） | return（黙）→ read-only なら cp 失敗 → exit 1 | fail-**closed**（T4） |
| framework 側 cplib 無 | WARNING → return → 後段 cp 失敗で exit 1 | fail-**closed**（サイレント破損なし） |
| `aegis_cp_verify` 空（未 lock） | `[ -n "$locked" ] || return 0`＝no-op（NOTE なし） | 正（idempotent・review S5） |
| unlock rc1（部分失敗） | WARNING「copies below may fail」→ 続行 → 残 locked path の cp が exit 1 | fail-**closed**（成功偽装なし） |

- **混在版サイレント成功の再発**: 元バグ（`set -e` が cp 失敗で install を途中死＝混在版木＋cp の素の stderr のみ）は
  mkdir/cp を `if ! …; then explain; exit 1; fi` 型に置換して**帰属つき明示 abort**に是正。self-heal は新たな
  silent-mixed-version 経路を導入しない（部分 unlock は WARNING＋後段 exit 1・完全 unlock は全 copy 成功）。
- `set -e` 相互作用: `locked=$(...) || true`（rc1=findings をマスク）・`if aegis_cp_unlock`（if 条件は set -e 免除）・
  全 return 経路 rc0（review S1〜S5 実測）。
- verdict: **PASS**（全 seam が fail-closed・混在版サイレント成功の再発なし）。

## 5. ソース信頼（source されるのは FRAMEWORK_ROOT 側 cp-lock.sh のみか）

- `source "$cplib"` の `cplib="$FRAMEWORK_ROOT/hooks/lib/cp-lock.sh"`＝**framework（install 元）側**のみ。
  target 側 `hooks/lib/cp-lock.sh` は `-f` 存在判定に使うだけで**source しない**＝攻撃者が target に悪性
  cp-lock.sh を植えても実行されない（信頼境界 正）。
- cp-lock.sh のトップレベル副作用: 関数定義のみ（grep 実測でトップレベル実行文ゼロ）＝関数内 source 安全。
- 名前空間衝突: cp-lock.sh の `aegis_cp_*` は setup.sh の関数（copy_file 等）と非衝突＝shadowing なし。
- verdict: **PASS**（trusted framework 側のみ source・target 側は不実行）。

## 6. ログ衛生（新規 echo がパスのみか・env/秘密の漏洩なし）

- Evidence（実 grep）: 新規 diff 内に secrets/credentials パターン**該当なし**／`$AEGIS_*` env の**値**を echo する箇所**なし**（変数名の静的言及のみ）。
- 新規 echo は `$dst`/`$d`（パス）＋静的 remediation 文言（`hooks/lib/cp-lock.sh`＝公開パス）のみ。
- verdict: **PASS**（Precedent #11＝非 PII/非秘密ログは非脆弱性。秘密漏洩なし）。

## Findings

**HIGH: 0 / MEDIUM: 0 / LOW: 0**（confidence ≥ 8 の報告対象なし）

OWASP Top 10 該当確認（非該当は理由付きスキップ）:
- Injection: §3 でトレース済＝command/path injection なし（**該当・PASS**）。
- Broken Authentication: 認証フロー変更なし（**非該当**）。
- Sensitive Data Exposure: §6・実 grep でログ/コードへの secrets 混入なし（**該当・PASS**）。
- Security Misconfiguration: lock ライフサイクル変更を §1/§2/§4 で確認＝既定 on・fail-closed・再 lock は次回 session-start（**該当・PASS**）。
- Vulnerable Dependencies: 純 bash・新規依存ゼロ（**非該当**。既存 deps🟡 は iter61/62 からの pre-existing ack）。

## 残余リスク受容判断

- **(a) unlock 窓（次回 session-start まで target CP が writable）**: 受容。通常の framework-mode セッションと
  等価な露出で、実行者＝owner 自身。NOTE 2行で可視・監査可能。severity: Info（accepted・設計明記）。
- **(b) session 内から framework clone の setup.sh 実行で moat を外す経路**: 受容。layer-2 の脅威モデルは
  偶発書込み防御で、意図的多段バイパス（任意スクリプト実行）は元来 scope 外。owner の `chmod u+w` 常時
  可能と等価。explain-oslock の「chmod するな」文言はエージェント self-repair 抑止であり、installer 内部の
  sanctioned unlock とは別物。severity: Info（accepted・設計明記）。
- **(c) marker leg の OR（LOW-1・1次＋盲検2次が独立に指摘）**: 受容。発火 (a) は
  `.aegis-install-version` **or** `hooks/lib/cp-lock.sh` の OR で、非 aegis dir でも後者を持ち かつ CP 名の
  dir を read-only にして実 lock 検出も満たすと `chmod u+w` されうる。ただし影響は owner 書込み復元のみ
  （TARGET subtree 内・昇格/chown/setuid/symlink 追従なし）で、そこへ setup を走らせる＝aegis を install
  する行為と等価。設計書の「marker」定義どおりの意図的挙動。fingerprint 厳格化（tree-hash 等）は
  Phase 1 罠根切りバックログ（full-review §2 R6）で別途検討。severity: LOW（accepted）。
- 新規 deploy blocker: **なし**（M＝deploy skip）。

## claims

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "marker leg が AND ではなく OR を含む（.aegis-install-version or hooks/lib/cp-lock.sh）＝LOW-1。1次も Info(c) として同定済＝収束。実害は owner-chmod 等価・昇格なし。"
  findings: "HIGH/MEDIUM なし。LOW-2 件（OR marker・unlock 窓）はいずれも設計受容済み残余。"
  evidence_ref: docs/qa-reports/iter63-security-2nd.md
```

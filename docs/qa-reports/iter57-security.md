# セキュリティレビュー（iter57）

- 対象: origin/main(584d22c)..HEAD（iter57・主 moat 交代＋review fix-forward）
- 中心的関心: **moat の主機構交代**＝安定 control-plane 防御を文字列静的解析
  （check-control-plane.sh・退役）から OS-lock（chmod a-w・syscall 強制）へ昇格。
  静的層は残余（runtime-state 書込み・unlock 形）に縮退。
- 脅威モデル: **事故防止**（敵対 sandbox 化ではない）。os.chmod 等の意図的解錠は従来どおり
  脅威モデル外。公式サポート = macOS/Linux/WSL（Windows ネイティブは保護なし・明記）。

## OWASP チェックリスト（該当項目のみ）

- [x] **Injection**: check-runtime-state の正規表現は固定パターン（変数展開は CASE_I 配列
  splice のみ）。emit_* は固定文言。advisory `explain-oslock-eacces.sh` は tool 出力を
  **判定にのみ**使い、additionalContext は**固定文言**（tool 出力を反映・注入しない）。→ 問題なし
- [x] **Sensitive Data Exposure**: diff 追加行を credential パターンで grep → 混入なし。
  judge の scan_secrets も承認時に tier-1 実走。advisory は秘密を出力しない。→ 問題なし
- [x] **Security Misconfiguration（moat 交代の攻撃面）**: OS-lock バイパス・残余ガード回避・
  unlock 形を scratch 実走で実測（下記 24/24）。→ 保護維持を確認
- [x] **Vulnerable Dependencies**: 依存追加ゼロ（pure-bash / stdlib python のみ）。→ 該当なし
- 非該当: Broken Authentication（認証フローなし）

## moat 交代の実バイパス試行（1次・scratch で cp-lock 実 lock ＋ hook 実入力）

### A. OS-lock による安定 CP 書込みの物理阻止（lock 下・全て EACCES＋対象 INTACT）

| 形 | 結果 |
|----|------|
| `> hooks/lib/emit.sh`・`echo > `・`printf >>` | blocked ✅ |
| `cp`・`mv`・`tee`・`python3 -c open(...,'w')`・`sed -i` | blocked ✅ |
| subshell cwd 移動 `(cd hooks && > lib/emit.sh)` | blocked ✅ |
| `find hooks -exec sh -c 'echo x > {}'` | blocked ✅ |
| 新規作成 `touch hooks/NEWFILE.sh`（dir a-w が創作を阻止） | blocked ✅ |
| symlink 作成 `ln -s /etc/passwd hooks/evil_link` | blocked ✅ |

12形すべて OS-lock が syscall で形非依存に阻止（旧静的層が正規表現で追っていた難読化形を含む）。
POC ハーネス（tests/poc/v162-redteam-rerun.sh）も 18/18 passed で cmdsub/backtick/printf-v/read/eval/
multi-redirect を再確認。sf_catalog（test_cp_lock_sf_catalog.py）が unlock 対照で弁別性を実証。

### B. 残余ガード check-runtime-state（runtime-state 改竄・非framework task）

| 形 | 期待 | 実測 |
|----|------|------|
| `sed -i s/pending/approved/ docs/STATUS.md`（gate 改竄） | deny | deny ✅ |
| `echo x > docs/STATUS.md` | deny | deny ✅ |
| `printf x > .claude/.gate-snapshot`（snapshot 改竄） | deny | deny ✅ |
| `echo '{}' > .claude/settings.json`（settings 改竄） | deny | deny ✅ |
| `cd docs && sed -i s/x/y/ STATUS.md`（cwd 移動） | deny | deny ✅ |
| `python3 -c open('docs/STATUS.md','w')` | deny | deny ✅ |
| `bash scripts/update-gate.sh review approve`（正当） | allow | allow ✅ |
| `cat`/`grep` docs/STATUS.md（読取り） | allow | allow ✅ |
| `chmod +w hooks/lib/emit.sh`（平文 unlock 形） | deny | deny ✅ |
| `chmod -R u+w .`（broad recursive・唯一 moat 無効化） | ask | ask ✅ |
| `chmod u+w hoo\ks/…`・`hooks""`・`"ho""oks"`・`$(echo hooks)/…`（**難読化 unlock**） | ask | ask ✅（**2次検出の Major を修正後**） |

### C. fail-closed

- manifest（scripts-manifest.tsv）欠落時も `echo x > docs/STATUS.md` は deny 維持 ✅
- safety lib 欠落＝deny（PORT-1 バイト同一フォールバック・POC F-01 で確認）／抽出失敗＝deny
  （raw input の `.claude/` alternation が必ず当たる設計）

**1次バイパス試行 合計 24/24 PASS**（sec-bypass-test スクリプト）。

## fail-open / silent 無防備化の検査

- session-start の lock 適用失敗・verify 不一致は **block でなく warn（fail-visible）**。ただし
  保護の独立性は check-runtime-state（fail-closed）＋check-gate（Edit/Write の CP deny・fail-closed）が
  担保＝OS-lock が無効でも二層が残る。
- install 経路: setup.sh の copy_hooks が退役 hook を prune し新配線を配布・scaffold smoke が
  install 先で OS-lock apply→verify rc0 を契約化（deploy で実走確認）。F6（配布欠落 silent fail-open）
  の再発防止が REQUIRED_HOOK_FILES に advisory も含めて配線済み。

## Findings

- Critical: なし
- **Major（盲検2次が検出→修正済み・1次は見落とし）**: `hooks/check-runtime-state.sh`
  `_unlock_form_on_cp` の平文 `LOCKED_CP` grep が **難読化 unlock 形**（`chmod u+w hoo\ks/…`・
  `chmod +w hooks""/…`・`"ho""oks"`・`$(echo hooks)/…`）を取りこぼし silent に allow していた。
  退役した `check-control-plane.sh` は shlex トークナイザで deny していた＝**旧 deny→新 allow の
  silent regression**。難読化 **write** は OS-lock が形非依存に阻止するが難読化 **unlock** は主 moat の
  外（unlock 後に write が通り moat 無効化を実測）。**→ 修正**: `_obfuscated_unlock_on_cp` を追加し、
  unlock ツール＋難読化マーカー（バックスラッシュ/連結クォート/コマンド置換）＋正規化後 CP トークンを
  **ASK**（fail-visible・ヒューリスティックゆえ deny でなく ASK・偽陽性なしを実測: `chmod +w my\ file.txt`
  等は allow 維持）。回帰テスト `test_obfuscated_unlock_on_cp_asks`＋`test_plain_unlock_still_denies…`＋
  `test_obfuscated_chmod_without_cp_token_allowed`。台帳 SF-009 に記録。
- Minor: なし（review で検出の POC 陳腐化・全数列挙テストギャップは review fix-forward で解消済み）

## 残余（脅威モデル外・SF-009 記録）

- 深い `$()` 構築・変数間接（`D=hooks; chmod +w $D`）はヒューリスティックをすり抜けうるが、
  意図的難読化＝事故防止の脅威モデル外（SF-004 と同じ静的判定の原理的限界）。

## Blockers

- なし

## 残余リスク（脅威モデル内・記録のみ）

- 敵対的 `os.chmod`/`chflags` 解錠は従来どおり脅威モデル外。
- `mv hooks hooks_bak`（root 非 lock ゆえ rename 成功しうる）は rev.2 既定 accepted residual・
  hooks/ 内は INTACT。Windows ネイティブは OS-lock 無効（公式サポート外・session-start で毎回明示）。

## Blockers

- なし（Major は push 前に修正済み）

## 判定

- 1次: **approve**（moat 交代後も安定 CP の write は形非依存に物理保護・残余ガードは fail-closed・
  正当操作は通過・平文 unlock/broad chmod は封鎖/確認・secrets 混入なし・OWASP 該当項目クリア）。
  ただし1次バイパス試行（24形）は**難読化 unlock を含まず**、盲検2次がその保護回帰（Major）を検出＝
  盲検2次の価値が発揮された。当該 Major は push 前に修正済み（ASK 化・回帰テスト・SF-009 記録）。

## 盲検 第2意見（self-attested）

2次レビュアー（security 役・general-purpose・fresh context・1次結論非開示）が実バイパス試行を含む
独立レビューを実施。verdict= **approve_with_notes**（confidence 8・Major 1・Minor 1）→ **全件修正済み**:
難読化 unlock 形（`chmod u+w hoo\ks/…`）が旧 hook では deny だったのに新 hook で silent allow 化した
保護回帰を実測検出（moat 無効化を再現）。Minor（broad recursive の難読化 `chmod -R u+w hoo\ks`）は同根。
→ `_obfuscated_unlock_on_cp` で ASK 化（fail-visible）・回帰テスト3本・SF-009 台帳記録で解消。
OWASP（A01/A08/A03/secrets）・保護ギャップ評価・secrets スキャンは1次と一致（write 経路の穴なし・
advisory インジェクションなし・secrets 0件）。

```claims
verdict: approve
tests_green: true
second_opinion:
  verdict: approve_with_notes
  notes: Major（難読化 unlock 形の silent 保護回帰＝旧 deny→新 allow・moat 無効化を実測）＋Minor（難読化 broad recursive・同根）を push 前に修正（_obfuscated_unlock_on_cp で ASK 化・回帰テスト3本・SF-009 記録）。write 経路の穴なし・advisory 非注入・secrets 0件は1次と一致
  divergence_points: ["1次バイパス試行は難読化 unlock を含まず・2次が保護回帰を検出（旧 tokenizer が deny→新平文 grep が allow）→ ASK 化で解消"]
```

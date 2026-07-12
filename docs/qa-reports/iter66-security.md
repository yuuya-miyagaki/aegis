# iter66 security レポート — SF-010 封鎖＋frontmatter 読取意味論統一

- **対象**: `git diff deb4a8a..HEAD`（実装 10 コミット `abf6d04`〜`6148a60`・HEAD=`da42506`）
- **task_type/size**: framework / M（control-plane：review+qa+security 必須・deploy skip）
- **仕様正本**: `docs/specs/2026-07-12-iter66-sf010-parser-unification-design.md`
- **動機正本**: `docs/security-followups.md` SF-010
- **検証体制**: 公式 `security-review` スキルを基盤に aegis OWASP 重畳。1次＝security agent（opus max・実 hook 発火）＋親 verify（in-session・pre-existing/contained 裏取り）＋盲検2次＝security agent（fable・fresh context・1次結論非開示・diff＋spec/plan のみ）
- **判定**: **PASS（approve）**。新規脆弱性 0（≥0.7）・1次＋盲検2次とも approve で収束・結論レベルの割れなし。

## OWASP Top 10（該当項目のみ・aegis 固有重畳）

| 項目 | 該当 | 結果 |
|------|------|------|
| Injection（Command） | ○ | bash hook にクラフト STATUS/snapshot 値を投入＝literal capture・`$(touch)`/backtick/`;&\|` 非実行（`/tmp/PWNED` 未作成）・`aegis_snapshot_gate_regression` の `case` は `[a-z_]` glob 制限で `ev*l`/`UP` を drop。**穴なし** |
| Sensitive Data Exposure | ○ | iter66 追加行に secret パターン（AKIA/private key/api_key/token/password）grep ヒット 0。block 理由文字列は gate/phase/task-field 名と enum 値（`<unset>`/`approved`/`S`）のみ＝PII/secret なし。新規ログ追加なし。`.audit-skip.log` はタイムスタンプのみ（不変）。**穴なし** |
| Broken Authentication（gate-bypass） | ○ | 主脅威。下記「SF-010 閉塞実測」参照。**閉塞** |
| Security Misconfiguration | ○ | 全変更 fail-closed 方向（whole-file→scoped・未終端→空・4-space 誤検出封鎖）。fail-open 退行 0（differential battery で HEAD が baseline より permissive なケース 0・唯一の差分は SF-010 の allow→block）。 |
| Vulnerable Dependencies | △ | N/A（pure bash＋python stdlib・依存マニフェスト変更なし・iter63-65 と同じ ack 前提）。 |
| Path Traversal | ○ | 変更コードのファイルパスは STATUS/snapshot **内容**から構成されない（`$ROOT`/`$SCRIPT_DIR`/`CLAUDE_PROJECT_DIR` 由来・trusted）。case-fold probe は env-override 不可の `SCRIPT_DIR` 由来 `PROBE_ROOT`。**穴なし** |

## SF-010 閉塞実測（hook 直接発火・1次＋qa で二重確認）

| ケース | baseline `deb4a8a` | HEAD `da42506` |
|--------|--------------------|-----------------|
| canonical SF-010（task_size empty-baseline に `task_size: S` raw-Edit 注入・task_type 在 snapshot） | ALLOWED（穴） | **BLOCK** `[task-tamper] task_size changed <unset>→S` ✓ |
| gate 行欠落 snapshot（`deploy:` 削除）に `deploy: approved` 注入（(iii)） | ALLOWED（grace） | **BLOCK** `[gate-tamper] deploy gate changed <unset>→approved` ✓ |
| 真の旧フォーマット（task_type 行そのものなし）＋ migration edit | grace | grace 温存（allow・false-block なし）✓ |
| task_type 除去（OLD 非空・自己防衛） | — | **BLOCK** `[task-tamper] task_type changed framework→<unset>` ✓ |
| 正規経路（`update-task.sh`/`update-gate.sh`） | allow | 無影響（snapshot 原子同期で audit 差分なし）✓ |
| task_size 本文 spoof（frontmatter 無・本文行頭 `task_size: S`） | whole-file grep が拾う | scoped 読みで**不可視**（deny）✓ |
| gate_value 本文 fallback（frontmatter に gate 節無・本文に gate ブロック）(iii) | 本文採用で allow 得る | frontmatter_section 限定で**本文不採用**✓ |

全変更が deny 方向のみ（allow が増える経路ゼロ）。SF-010 の (i) 重複キー先勝ち乖離・(ii) `extract_scalar_value` 引用形優先も python first-match/先勝ち化（Fix ⑤）で bash `grep -m1` に一致＝audit-evading な python=S/bash=M 割れを消去。

## パーサ差分（bash enforcement vs python check_status.py）

- first-wins parity 一致確認: 重複 gate 行（両 approved）・二重 `gate_approvals` ブロック（両 first）・重複 scalar `task_size: M` 後 `S`（**両 M**＝F-1 乖離消去）。
- enforcement 方向スイープ（single/double-quote・末尾空白・先頭空白・本文 spoof・dup 各種・CRLF）: `""S""` nested-quote を除き bash==python。当該残余は bash 側が `"S"`（S 非該当＝**fail-closed**）で design doc がスコープ外と明記（design:70）・authorized writer 経由到達不能＝報告閾値外。
- `gate_approvals_extra:` は `gate_approvals:` を spoof しない（`index($0,key":")==1` matcher 安全）。

## 盲検2次が独立検出した pre-existing 乖離 → **SF-011 起票**

盲検2次（fable・独立）が `read_frontmatter`（bash `^---[[:space:]]*$` 末尾スペース許容）と `extract_frontmatter`（python `\A---\n...\n---\n` strict）の**終端デリミタ許容差**を differential battery で発見。親 verify で以下を裏取り:

- **pre-existing 確定**: bash 終端 `^---[[:space:]]*$`・python 終端 regex とも baseline `deb4a8a`=HEAD で不変（iter66 変更は `extract_scalar_value` first-match 化・`extract_approval_map` first-wins のみ）＝この diff の回帰ではない。
- **contained（3 層・実証済み）**: (1) check-gate は bash empty→plan gate→deny（コード編集 unlock されず・qa M2 で実測）／(2) gate 承認は update-gate.sh 必須（raw-Edit で approve 不可・(iii) gate loop 絞り込みで堅牢化）／(3) `validate_with_pyyaml`（--strict/contract）が regex↔PyYAML cross-check で mode/phase/gate 不一致を検出→contract FAIL（"done" 洗浄不能）。

→ **新規脆弱性ではない**（gate をブロックしない）が、実証済みの実在乖離として `docs/security-followups.md` **SF-011（Low・OPEN）** に起票。修正方向＝`read_frontmatter` 終端を strict `^---$` 化 or parity drift-guard に `--- ` fixture 追加（次反復 hardening）。

## Evidence Checklist（aegis 固有）

- [x] Grep で secrets/credentials パターンを検索した（iter66 追加行・ヒット 0）
- [x] 外部入力（クラフト STATUS/snapshot 内容）のサニタイゼーションを確認した（literal capture・injection 非実行を scratch 実証）
- [x] dependency audit（N/A＝pure bash＋stdlib・理由明記）
- [x] 全 finding に severity と remediation を付与（新規 finding 0・SF-011 は pre-existing として Low＋修正方向付与）

## 残存リスク ack（deploy blocker ではない）

- **SF-010 residual**: 本 iter で (i)(ii)(iii) 込みで封鎖・機械裏取り済み。**CLOSED 化は docs フェーズ**（plan 完了条件）。
- **SF-011**（新規・pre-existing・Low・contained）: security gate で residual として ack。次反復候補。
- **snapshot 削除→grace 窓**: 脅威モデル外（SF-006 同境界・`.claude/` Bash 書込みは check-runtime-state.sh が block）。
- **flaky `test_update_gate_lock`**（env timing・full-review R10 test#8・本 diff 不接触＝回帰外）。

## 判定

**PASS（approve）**。新規脆弱性 0・全変更 fail-closed・SF-010 閉塞を hook 直接発火で実測・1次＋盲検2次収束。盲検2次発見の pre-existing 乖離は 3 層 contained で gate 非ブロック＝SF-011 起票で徹底追跡。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points:
    - "PRE-EXISTING（deb4a8a=HEAD で同挙動・この diff の回帰ではない）: bash read_frontmatter の終端 `^---[[:space:]]*$`（末尾スペース許容）と python extract_frontmatter の strict `\\A---\\n...\\n---\\n` の乖離。mid-frontmatter の `--- ` 後に task_size: S を隠すと python check_phase_transition だけが S を読み phase-skip を数字上許容。ただし check-gate fail-closed(bash empty→deny)・gate は update-gate.sh 必須・--strict/contract の PyYAML cross-check が reject の 3 層で contained＝実害到達なし。SF-011(Low) として起票・次反復 hardening。"
  evidence: "scratch clone で実 hook 発火・differential battery(baseline vs HEAD)で HEAD-more-permissive ゼロ・唯一の差分は SF-010 の allow→block・89-93 changed-area tests green・injection 非実行・main tree clean。"
```

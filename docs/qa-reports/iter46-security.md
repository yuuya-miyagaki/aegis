# iteration 46 security — threat-model 境界ドキュメント（C4/G4 クローズ）

- 日付: 2026-06-26
- task_type/size: framework / M（docs-only）
- 対象: `docs/security-followups.md`（canonical 脅威モデル節＋SF-007/008）・`docs/full-review-...md`（backlog/pointer）・`docs/LEARNINGS.md`
- 参照: plan / review=`docs/qa-reports/iter46-review.md` / qa=`docs/qa-reports/iter46-qa.md`

## OWASP Top 10 該当性（docs-only ＝大半 N/A）

- **A01 Broken Access Control**（該当・概念）: 本成果物は gate/access-control モデルの記述。verdict は access-control サーフェスを正確に特徴づける（gate 強制は両パーサとも exact-match fail-safe）＝穴なし。
- **A04 Insecure Design**（該当）: SF-007/008 は設計境界の判断。verdict は脅威モデルと整合・健全。
- **A05 Security Misconfiguration**（弱く該当）: 「strict 正規化は tamper 検知を弱める」は設定/設計トレードオフを正しく解決。
- A02/A03/A06/A07/A08/A09/A10: N/A（docs verdict 変更・実行コード/依存/認証/暗号の変更なし）。

## findings（severity / remediation）— 1次（self）＋盲検2次（`security` agent・fresh context・diff/code/spec のみ）統合

- **Minor 1 / conf 8** — SF-007 が PyYAML cross-check を「weird quoted 形の safety net」と読ませうるが、`'approved'`/`"approved"` は cross-check 非検出（PyYAML と strict 正規が一致）。実際の safety net は **bash 消費側の exact-match＋writer/tamper 不到達**。→ **反映済**（SF-007 に明記・cross-check 死角は穴でないと追記）。
- **Minor 2 / conf 7** — SF-008 の Check 3 は `emit_ask` の **advisory であって block でない**・難読化リダイレクトに静的限界（SF-001/004）。拘束力ある保証は commit/stage の block。→ **反映済**（SF-008 に明記）。
- **canonical 節の determinism 過大主張（盲検2次の初回指摘）** — 「決定論的に守る」が Bash command moat（SF-004 限界）まで含意していた。→ **反映済**: 決定論サーフェス（Edit/Write path・gate tamper-evidence・commit-stage file-name）と threshold-raising な Bash moat を切り分け（README §95 と同区別）。修正後の盲検2次 = 「determinism は正しくスコープ・過大主張なし」。

Critical=0 / Major=0。秘密スキャン＝検出なし（docs に実シークレットなし）。依存監査＝変更なし（unverified＝advisory）。tests=green（1120 passed/1 skipped・record 済）。

## verdict 検証（独立・盲検2次が一次資料で確認）

- **SF-007=NOT-A-VULN に AGREE**: 独立に 12 形 differential を再実行し bash-approved∧python-not-approved の行 0 を再現。消費側（`check-gate.sh:174` exact-match／`check_status.py:985-986,1058` の `.get(...,"pending")`）は両方 fail-safe。writer（`update-gate.sh:253/276/284`）は clean enum のみ。strict 正規化は `post-status-audit.sh:129-130` の tamper 比較を弱める（実測 NO-MISS→YES-BLOCK の喪失）＝net-negative も確認。
- **SF-008=by-design に AGREE**: `check-secrets.sh` は `Bash` matcher 限定（`templates/hooks.template.json`）＝Write/Edit ツール経由 .env は構造的に未発火だが、事故的漏洩の chokepoint（commit/stage）は Check 0-2＋broad-stage で閉鎖済。open path（Write/Edit 生成・curl exfil）は commit gate と冗長 or 原理的に regex 不能＝scope 外が妥当。
- **canonical 節 = README §95・SF-001/004/006 と整合**。

## Evidence Checklist

- [x] Grep/scan で secrets パターン確認（judge: secrets 検出なし）
- [x] 外部入力サニタイゼーション: 該当なし（docs・実行コードなし）
- [x] dependency audit: 依存変更なし（unverified は advisory・ack）
- [x] 全 finding に severity/remediation 付与（Minor 2 件＋determinism＝全反映）

## 判定

**PASS（approve_with_notes）**。Critical/Major=0。Minor 3 件（cross-check 死角の明記・Check 3 advisory 明記・determinism スコープ）全反映。deploy blocker なし。docs-only・コード/依存/認証の変更なし。依存監査 unverified は新規依存ゼロのため ack で承認。

```claims
verdict: approve_with_notes
deps_clean: true
no_secrets: true
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "盲検2次は当初 canonical 節の determinism 過大主張を指摘→修正反映後は『正しくスコープ・過大なし』に収斂（1次/2次とも approve_with_notes で一致）"
    - "Minor 1（cross-check 死角）/Minor 2（Check 3 advisory）も反映済＝実質的相違なし。両者とも SF-007=NOT-A-VULN・SF-008=by-design に AGREE"
```

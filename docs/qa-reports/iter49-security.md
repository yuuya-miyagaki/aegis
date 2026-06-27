# iter49 セキュリティレビュー — 配布 self-containment 射程拡大

- 対象 diff: `tests/test_profile_referential_integrity.py`（test-only）／`templates/profiles/{full,standard}.json`
  （`required` に `scripts/update-task.sh` 追加）／`README.md`（件数 20→21）。
- 参照: plan=`docs/plans/2026-06-27-command-skill-ref-integrity-implementation-plan.md`／qa=`docs/qa-reports/iter49-qa.md`。

## OWASP Top 10（該当項目のみ）

- **A03 Injection**: 該当なし。新規 test は `re.findall`／`read_text` を **repo 所有の .md/.json** にのみ適用。
  `eval`/`exec`/`os.system`/`subprocess`/`shell=True`/`__import__` なし（grep 実測。唯一の "subprocess" は docstring 語）。
- **A05 Security Misconfiguration**: **改善**。shipped skill が未同梱 script を参照して install 後に
  silent-degrade する設定ミスを CI で fail させる（本変更の主目的）。
- **A02 Crypto / A07 AuthN / A08 Deserialization / A10 SSRF**: いずれも非該当（暗号・認証・直列化・外部通信なし）。
- **Vulnerable Dependencies**: 新規依存ゼロ（標準ライブラリ `re` のみ）。

## 同梱スクリプトの監査: `scripts/update-task.sh`

- 既存・無改変（diff は同梱リスト 1 行のみ。`git diff --name-only` に update-task.sh 自体は無し）。
- `set -euo pipefail`。引数は `--type`/`--size` の allow-list、固定 enum（S/M/L・feature…framework）で
  検証後にのみ使用。`eval`/`sh -c` へ未検証値を渡す経路なし＝injection 不能。
- 書き込みは `$ROOT` 内の `docs/STATUS.md` ＋ `.claude/.gate-snapshot` のみ。atomic `mv`＋mkdir lock。
- これは **tamper-evident な authorized 変更経路**（raw STATUS 編集は hook で block）。同梱は
  「skill が参照する authorized ツールが install で no-op になる privilege gap」を**塞ぐ**もので、開けない。

## Evidence Checklist

- [x] secrets/credentials grep（diff 全体）→ 検出ゼロ。
- [x] 外部入力サニタイゼーション → 該当なし（入力は repo ローカルファイルのみ・path は `__file__`/glob 由来で traversal なし）。
- [x] dependency audit → 新規依存ゼロ。
- [x] 全 finding に severity／remediation → 下記（material finding ゼロ）。

## findings（severity / remediation）— 1次（self）＋盲検2次（`security` agent・fresh context・verdict=approve）統合

- Critical/High/Medium/Low = **0**。material finding なし。
- residual risk: update-task.sh の blast radius は repo 内で既に統治している STATUS.md/snapshot 変更に限定＝negligible。

## 盲検 第2意見（`security` agent・fresh context・diff＋spec/plan のみ・verdict=approve）

独立ディスパッチ。結論 approve・findings ゼロ。一次資料で update-task.sh を読み「allow-list 引数＋enum 検証＝
injection 不能・書込は $ROOT 内 STATUS/snapshot のみ・authorized tamper-evident path」を確認。test は
ast/regex/read_text のみで unsafe sink 無しを独立確認。A05 を「改善」と評価＝1次と一致。divergence なし。

## 判定

**PASS（approve）**。Critical/High/Medium/Low=0。盲検2次（独立 `security` agent）も approve・divergence なし。
test-only＋pure-data 同梱＋非実行 regex/ast で攻撃面拡大なし。むしろ A05 silent-degrade を CI で封鎖する防御的変更。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points:
    - "1次/2次とも approve・material finding ゼロ・divergence なし。両者 update-task.sh を一次資料で監査し injection 不能・authorized tamper-evident path と確認、新規 test を ast/regex/read のみで unsafe sink 無しと確認、A05 を防御改善と評価。tests_pass は qa で full suite green を record 済（2次は read-only ゆえ未実行だが deterministic と claim）。"
```

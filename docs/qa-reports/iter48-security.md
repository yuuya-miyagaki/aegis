# iter48 Security Review — profile 参照整合性チェック＋JNY-07 実修正

- 日付: 2026-06-26
- task_type/size: framework / M（security 必須）
- 対象 diff: `tests/test_profile_referential_integrity.py`（新規）/ `templates/profiles/full.json`（+1 行・データ）/ `tests/test_profile_checker_parity.py`（e2e 1 クラス）
- 参照: spec `docs/specs/2026-06-26-distribution-self-containment-design.md` / qa `docs/qa-reports/iter48-qa.md`

## OWASP 該当チェック（変更該当項目のみ）

- **Injection / code-exec**: 該当なし（clean）。`_deps_from_source` は `ast.parse`（非実行・木構築のみ）を **repo 所有の `scripts/*.py`** にのみ適用。e2e は `subprocess.run`（`shell=False`・引数固定＝`bash setup.sh` / `python3 check_status.py`）を tmpdir の repo 制御入力に対して実行。`eval`/`exec`/`os.system`/`shell=True`/未信頼入力なし（grep 実測）。
- **Sensitive Data Exposure**: 該当なし。`_artifact_template_map.py` は **pure-data**（artifact→template パスの dict・`from __future__` 以外の import/IO/secret なし）。同梱しても secret 露出・攻撃面拡大なし。テストは secret をログしない。
- **Security Misconfiguration / Supply-chain**: 下記 Low 2 件（residual・非ブロッキング）。
- **Vulnerable Dependencies**: 新規依存ゼロ（標準ライブラリ `ast`/`json` のみ）。dependency audit 不要。
- **Broken Auth**: 非該当（認証経路の変更なし）。

## findings（severity / remediation）— 1次（self）＋盲検2次（`security` agent・fresh context・verdict=approve）統合

- **Low / conf 9** — `tests/test_profile_referential_integrity.py:INTENTIONAL_UNSHIPPED` が唯一の濫用ベクタ: 将来のメンテナが security 関連スクリプトを「もっともらしい reason」で install から隠せる。テストは reason 非空＋edge live は検査するが **intent の正しさは判定不能**。→ **受容（緩和策＝本 security gate の人手レビュー）**: 本ゲートの盲検2次レビューが allow-list 追加を実際に審査する運用が一次緩和。`test_no_stale_or_redundant_allowlist_entries` が stale/redundant を機械検知（wrong-but-live は人手）。将来 slice で「security-class エントリは security sign-off 必須」コメントを追加検討（本 diff のテスト編集は review/qa 承認後のため見送り）。**非ブロッキング**。
- **Low / conf 8** — `scripts/status_doctor.py:228` の D5 version-drift 警告が field install で inert（`check_framework_contract.py` 意図的非同梱）。→ **受容（by-design）**: D5 は **advisory のみ**でセキュリティ制御を gate しない（status_doctor.py:228-245 は regex で版差を warning するだけ）。stale-install の自動 nudge が失われるが、契約ツールチェーン（+platform_manifest+context_budget）の install 同梱コストと不釣り合い。allow-list reason に by-design 明記済。upgrade-nudge が security 要件化したら再訪。

Critical/High/Medium=0。Low 2 件はいずれも受容可能な residual。divergence_points=none。

## Evidence Checklist

- [x] secrets/credentials パターンを grep（password/token/api_key/credential＝検出なし）
- [x] 外部入力のサニタイゼーション確認（未信頼入力なし＝ast 対象は repo 所有・subprocess は固定引数）
- [x] dependency audit（新規依存ゼロ＝不要）
- [x] 全 finding に severity + remediation 付与（Low 2 件・受容理由明記）

## 判定

**PASS（approve）**。Critical/High/Medium=0。盲検2次（独立 `security` agent）も approve・divergence なし。pure-data 同梱＋非実行 ast＋固定引数 subprocess で攻撃面拡大なし。residual Low 2 件は本ゲートの人手レビュー（allow-list）と by-design（D5 advisory）で受容。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points:
    - "1次/2次に実質的相違なし。両者とも injection/secret/dep の新規リスクなしに同意。盲検2次が挙げた Low 2 件（allow-list 濫用ベクタ＝本ゲート人手レビューで緩和／D5 inert＝advisory で by-design）を residual として受容、いずれも非ブロッキング。"
```

# iter50 セキュリティレビュー — doc→script 参照整合性 test guard

- 対象: uncommitted change `tests/test_profile_referential_integrity.py`（iter50 セクション・約290行追加）。新規 docs（specs/plans/qa-reports）は documentation＝実行サーフェス外。
- 参照: plan=`docs/plans/2026-06-27-doc-script-ref-integrity-implementation-plan.md`／spec=同日 design。
- 性質: production code 無改変・pytest 専用の regression guard。入力は **maintainer 著・repo-controlled なファイルのみ**（外部/untrusted 入力なし）。

## 判定: approve（material finding ゼロ）

新規に導入された HIGH/MEDIUM の具体的に exploit 可能な脆弱性なし。

## OWASP 該当項目の確認（非該当は理由付き）

- **A03 Injection / Command exec**: なし。`_setup_resolve_remap` は `bin/setup.sh` テキストの純 regex+文字列処理＝`eval`/`exec`/`subprocess`/shell 呼び出しゼロ（diff grep 実施）。
- **Path traversal**: `_doc_install_source(rel)` は `ROOT / rel` を join するが、`rel` は `_shipped_doc_surfaces` が `CLAUDE.md` ∨ `.claude/rules/*.md` に whitelist 後の値のみ＝`..` 等は join 前に除外。`profile` は `templates/profiles/*.json`（repo-controlled・grep で `..` トークンなし）由来。`ROOT` は `__file__` 固定でenv/CLI 非依存。**untrusted 入力からパスが導出されない**。
- **A08 Insecure Deserialization**: `json.load` は repo-controlled profile JSON のみ（trusted source・untrusted データの逆シリアライズではない）。
- **Sensitive Data Exposure / Secrets**: なし。secrets/credentials を read/write/log しない（diff grep: password|secret|token|api_key|credential|private-key パターン全ゼロ）。
- **Vulnerable Dependencies**: 新規 import/依存ゼロ（stdlib のみ既存）。
- **regex を read primitive として悪用**: `_SKILL_SCRIPT_RE`/`_doc_script_edges` は doc 中の `scripts/...` 部分文字列を **match** するだけ＝open/exec しない。敵対的 doc 文字列でも任意 read/exec 不能。

## Evidence Checklist

- [x] secrets/credentials パターンを diff grep（全ゼロ）
- [x] 外部入力のサニタイゼーション確認（外部入力なし＝全 repo-controlled・path は whitelist 後 join）
- [x] dependency audit（新規依存ゼロ＝該当なし）
- [x] 危険呼び出し grep（subprocess/eval/exec/pickle/os.system/shell=True 全ゼロ）
- [x] 全 finding に severity 付与（finding ゼロ）

## deploy blocker

- なし。

```claims
verdict: approve
no_secrets: true
deps_clean: true
no_injection_surface: true
second_opinion:
  verdict: approve
  divergence_points:
    - "1次（aegis evidence checklist: secrets/deps/危険呼び出し grep 全ゼロ・path は whitelist 後 join）と2次（盲検 security agent: path-traversal ベクタを end-to-end トレースし _shipped_doc_surfaces の whitelist＋repo-controlled JSON 由来で到達不能と確認）に相違なし。両者 approve・material finding ゼロ。test-only かつ入力は maintainer 著の repo ファイルのみで concrete な攻撃経路なし。"
```

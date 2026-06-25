# iter45 Security Report — C2 setup arg parser / C3 version heredoc

- 日付: 2026-06-25
- 変更: `bin/setup.sh` の引数パーサ両形式対応（C2）＋ FRAMEWORK_VERSION heredoc の argv 渡し（C3）
- 脅威モデル: Aegis installer/hook は **LLM 自身の事故/self-bypass** に対するガードレール（外部 network adversary 非対象）。setup.sh はユーザ権限でローカル実行し、framework hook（moat）を target に配布する。

## OWASP 該当性

| 軸 | 該当 | 根拠 |
|----|------|------|
| A03 Injection | 非該当 | C2 は値の**取得方法**（`$2`/`shift 2`）を変えるだけで使用先は不変。PROFILE は allowlist 検証後にのみ使用、TARGET は quoted パスとしてのみ使用。C3 argv は data として渡る（コード評価なし）。 |
| A08 Integrity | 中立 | moat 配布ロジック（copy/force-overwrite）は不変。version stamp は実値解決が改善（dead path 解消）。 |
| A05 Misconfiguration | 非該当 | DIST-12（framework self-install abort）・python3 prereq・profile allowlist いずれも不変。 |
| Sensitive Data | 非該当 | 変更行に secret の読み書き・ログなし（grep 確認）。 |
| Vulnerable Deps | 非該当 | **新規依存ゼロ**（bash ＋ python stdlib: re/pathlib/sys のみ）。 |

## ガードレール整合性の精査（1次・実トレース）

- **C2 PROFILE**: `bin/setup.sh` の allowlist 検証（`minimal|standard|full`）を初回使用前に通過。空白形式 `--profile "x;rm"` も equals 形式と同一に allowlist で reject。`eval`/python `-c` への到達なし。
- **C2 TARGET**: `mkdir -p`/`cd`/`pwd` の quoted 引数、および `"$TARGET/$rel_path"` パス接頭辞としてのみ使用。`--target "$(...)"` は呼出側シェルが既に展開した**リテラル文字列**で、setup.sh は再評価しない（inert）。
- **C2 ガード不変**: `[ $# -ge 2 ]` guard が `--profile` 値欠落の空消費/ループを阻止。`*)` が不明引数を reject。DIST-12 は parse 後の解決済み TARGET に対して発火＝取得形式に非依存。
- **C3 heredoc**: 区切りが single-quoted `<<'PY'` のため body は非展開。path は `sys.argv[1]` の data として渡り `pathlib.Path.read_text` で評価されない。FRAMEWORK_ROOT が `$()`/backtick/`;` を含んでもリテラル path 引数。FRAMEWORK_ROOT は script 由来（`cd $SCRIPT_DIR/..`）でユーザ入力でない。`2>/dev/null || echo unknown` ＋ grep フォールバックは安全に degrade。

## Findings

### Critical / High / Medium / Low
該当なし。C2 は到達可能状態を既存ガードを超えて広げない（ergonomics のみ）。C3 は injection 安全な correctness fix（dead first path 解消）で新規 exposure ゼロ。

## Net 評価

**net-neutral〜positive。** C2 は受理する**値**を変えず取得形式のみ拡張、C3 は常に失敗する無駄な python fork を解消し version 解決を honest 化。新たに緩む security 境界・新規 allow なし。

## 盲検 第2意見（self-attested）

1次（本レポート＝実トレース）確定後、verdict 非共有・fresh context（diff＋脅威モデルのみ）で独立 security エージェントを 1 回ディスパッチ（テスト実行は禁止し静的解析・実トレースに限定＝evidence ログ保全）。エージェントは injection（PROFILE/TARGET/argv の sink トレース）・新規 attack surface（DIST-12/prereq 不変）・secret・deps・C3 heredoc 安全性を**独立に**確認し **approve**（confidence 9）。Critical/High/Medium/Low ゼロで 1 次と一致。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points: ["なし（1次/2次とも approve・finding ゼロ）。2次が独立に: PROFILE allowlist が空白形式でも値スマグリングを阻止／TARGET は呼出側展開済みリテラルで再評価なし／<<'PY' single-quote で heredoc body 非展開＝argv は data／DIST-12・python3 prereq・--force gating すべて取得形式に非依存／新規依存ゼロ を確認"]
```

1次/2次とも **approve** で一致。Critical/High/Medium/Low 0。deps 監査は新規依存ゼロ（manifest 変更なし）で advisory。

## 判定

**PASS。** 新規脆弱性なし。C2 は既存ガード（allowlist/DIST-12/prereq）を不変のまま ergonomics を拡張、C3 は injection 安全な dead-path 解消。deploy blocker なし（M で deploy size-exempt）。

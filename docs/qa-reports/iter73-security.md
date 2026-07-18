# iter73 Security Report — locale/byte 掃討（deny 側フック byte-wise 決定化）

- **日付**: 2026-07-19
- **対象**: `hooks/check-destructive.sh:51`・`hooks/check-secrets.sh:62`（各 `export LC_ALL=C LC_CTYPE=C LANG=C` を抽出前に追加）＋`tests/test_hook_locale_byte.py`
- **体制**: 1次=security（opus・main repo）／盲検2次=security（fable・物理隔離 clone `scratchpad/iter73secclone`・1次 verdict 非開示）
- **脅威モデル（canonical）**: 事故的 LLM 自己バイパス。Bash コマンド経路は「敷居を上げる層」（sandbox でない）。モデルの command は常に valid UTF-8。

## OWASP Top 10 チェックリスト（該当項目）

| 項目 | 該当 | verdict |
|------|------|---------|
| A03 Injection / moat-bypass（narrowing 由来の新 fail-open） | YES（核心） | **PASS** — 1次 56-case battery・盲検2次 独立バッテリー（実 repo 含む）とも runnable command の判定 miss ゼロ・crash ゼロ |
| A03 Injection（export 経由のコマンド構築） | YES | **PASS** — `export LC_ALL=C …` は静的定数・`$INPUT`/`$CMD` 非補間・新 eval/expansion なし |
| A02 Sensitive Data Exposure（実 secret staging 拒否） | YES | **PASS** — `.env`/`*.pem`/`id_rsa`/`credentials*.json`/broad `-A`/`.`/commit staged-diff/var-built/cmdsub・valid 多バイトパスとも deny/ask 維持・safe-variant は allow |
| A05 Misconfiguration / fail-safe（PEP 540 劣化） | YES | **PASS** — §PEP 540 |
| A06 Vulnerable Dependencies | YES | **PASS** — 新規依存ゼロ・`LC_ALL=C`/tr/grep/sed は POSIX |
| A01/A07/A08/A09/A10 | NO | 非該当（authz/session/deserialization/logging/SSRF サーフェス不接触） |

## Findings

- **Critical/Major/Minor: なし。**
- **F-1（informational・非 exploitable・盲検2次 conf9・= SF-016）**: C locale が `[[:space:]]`/`\s` を ASCII のみに狭め、Unicode 空白区切り（NBSP/U+3000/ogham）が pre(UTF-8)=warn/deny → post(C)=allow に narrowing。**両レビュアーが独立に非 exploitable と実証**: bash の tokenizer は ASCII blank（0x20/0x09）でのみ word-split するため `git<NBSP>add`/`rm<NBSP>-rf` は単一の非存在トークン→`command not found`＝削除/ステージング不実行。runnable command は必ず ASCII 区切り＝C でも match。既に SF-016 として起票・`tests/test_hook_locale_byte.py` で pin・両フックのコメント訂正済み（review fix-forward 8be219d）。remediation 不要（accept）。

## load-bearing answer（新 fail-open の有無）
**なし。** 正しい ASCII 構造で bash が実際に実行する破壊的/シークレットコマンドが post-change で allow に落ちる入力は発見されず（1次 56-case＋盲検2次 独立実測）。逆に本変更は**既存 fail-open を除去**: invalid-UTF-8 バイト混入で pre-change がクラッシュ（`tr: Illegal byte sequence`＋`set -e`→rc=1・JSON なし→Claude Code proceeds＝fail-open allow）していた経路が post-change で正しく deny/ask（例 runnable `git add .env #<0xFF>`: pre=CRASH_rc1_FAILOPEN→post=deny を盲検2次実測）。`${IFS}`/`$(...)` 間接系は pre==post（pre-existing SF-004 クラス・本変更由来でない）。

## PEP 540 劣化
**fail-safe。** LC_ALL=C で CPython は UTF-8 Mode 自動有効（`utf8_mode=1`・stdin/stdout=utf-8・両レビュアー実測）。`PYTHONUTF8=0` 強制（UTF-8 Mode off・stdin=ascii）でも全プローブが ask/deny・allow ゼロ（byte 混入は grep fast-path＝byte-wise、raw fallback も byte-wise grep ゆえ deny/ask 側に落ちる）。

## Deploy blocker
**なし。** auth bypass/default creds/hardcoded secret/HTTPS いずれも非該当。M ゆえ deploy phase skip。

## 統合 verdict: **approve**

1次=approve（findings なし）／盲検2次=approve_with_notes（note=SF-016 は非 exploitable・既に tracked＋pin＋コメント訂正済み・将来 IFS に Unicode 空白を含める非標準シェル対応時のみ revisit）。**divergence は verdict ラベルのみ**（approve vs approve_with_notes）で実体は完全収束（唯一の residual SF-016 は review で既に消化済み・新規リスクゼロ）。本変更は moat を強化（invalid-byte fail-open を封鎖）し副作用は文書化済み・pin 済み・非 exploitable な narrowing のみ。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points:
    - "verdict ラベルのみ（1次=approve／盲検2次=approve_with_notes）。実体収束＝唯一の residual SF-016(Unicode 空白 narrowing)は両者独立に非 exploitable と実証〔bash IFS は ASCII のみ→非コマンド〕・review で既に SF-016 起票＋pin＋コメント訂正済みで notes 解消済み。新 fail-open ゼロ・deploy blocker なし"
```

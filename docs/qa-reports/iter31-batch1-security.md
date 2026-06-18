# Security — iteration 31 / Batch1（control-plane フック精度 + git baseline）

- **対象 diff**: `git diff 9177854..HEAD`。中核資産＝`hooks/check-control-plane.sh`（**未信頼 Bash コマンド文字列を解析**し control-plane への書込みを deny する moat）。
- **手法**: 公式 security-review＋OWASP 重畳。1 次＝`security` 専門エージェント、盲検 2 次＝独立 break-attempt。両者 fresh context・実フック実行。

## OWASP 該当項目

| 項目 | 該当 | 結果 |
|---|---|---|
| Injection（Command/解析） | ★中核 | 未信頼コマンドを grep -E/sed -E/tr/python/bash char-loop に投入。fault injection（python 不在・safety/emit.sh 欠落・不均衡クォート）で**全エラー経路 fail-closed=deny** を実証。ReDoS/option-injection/metachar での deny→allow フリップは確認されず。 |
| Sensitive Data Exposure（secrets） | 該当 | Task 1.2 は **stub 走査のみ** control-plane 除外（`STUB_NONCODE_PREFIXES`）。`scan_secrets`(:253) は既定 prefix で control-plane scripts を**引き続き全走査**＝secret カバレッジ後退なし（テストで固定）。diff に新規 secret なし。 |
| Security Misconfiguration | 該当 | フック挙動は厳格化方向（var-built-write→ask、redirect-target→deny、改行正規化）。設定の緩みなし。 |
| Broken Auth / Vulnerable Deps | 非該当 | 認証フロー・依存追加なし。 |

## 主要 finding

1. **新規 WRITE バイパス: ゼロ**（1 次＋2 次が独立確認）。control-plane へ**任意内容を書く**コマンドで orig(8f8eb2d) が deny→new が allow/ask になったものは無し。SF-001 系（quote 分割・backslash・bare-dir）は **orig/new とも allow＝完全に pre-existing**。
2. **意図した deny→allow/ask 差分（NEW・write-safe）**: read-only パイプ allow（OBS-003）／commit メッセージ内 CP 言及 allow（OBS-006）／`git add <dir>` staging ask（OBS-017）。いずれも**ファイル内容書込みではない**＆チェイン後段の書込みは依然 deny（`git commit -m x && cp evil hooks/lib/emit.sh`→deny）。テストで固定。※「ゼロ差分」ではなく「**新規 WRITE バイパス ゼロ**」が正確（1 次の honest correction）。
3. **blocklist→allowlist 反転（Task 1.6 review fix）は厳密により安全**（2 次）。旧 `WRITE_UTIL_RE` ブロックリストは未列挙 writer で漏れたが、新 allowlist（echo/printf/git commit のみ救済・他は fail-closed deny）は漏れない。
4. **fail-closed 堅持**: safety.sh/emit.sh 欠落・`mask_quoted` 不均衡クォート→1・python3 不在（埋め込みエスケープクォート含む）→全て deny。

## 残存リスク（deploy blocker ではない）

- **SF-001（Critical・pre-existing）**: control-plane 判定がシェルの word-splitting/パス解決を再現せずリテラル `hooks/` 一致に依存＝quote 分割・backslash・bare-dir 形で moat バイパス。**両エージェントが orig でも同一 allow を実走確認＝Batch1 後退ではない**。security skill の deploy blocker 列挙（auth bypass/default creds/hardcoded secret/HTTPS）に**非該当**＝deploy をブロックしない Critical 残存リスク。`docs/security-followups.md` SF-001 に durable 記録・**最優先 follow-up**（ユーザー合意 2026-06-16 で繰延）。「pre-existing」を「won't fix」に decay させない。

## 判定

**approve_with_notes** — Batch1 は write moat を厳密に強化（var-built→ask・redirect-target→deny・改行正規化・blocklist→allowlist）し新規 WRITE バイパス ゼロ・secret カバレッジ維持・fail-closed 堅持。1 次＋盲検 2 次とも approve_with_notes で収束。notes: (a) SF-001 を最優先 follow-up として保持、(b) 本ゲートに「意図的 deny→allow/ask 緩和（OBS-003/006/017）」を明記。deploy blocker なし。

```claims
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["独立に SF-001 系（quote分割/backslash/bare-dir）を pre-existing と実走確認し、blocklist→allowlist 反転を『厳密により安全』と評価。新規WRITEバイパスは無し。SF-001 は Critical 残存リスクだが deploy blocker 非該当で繰延に同意"]
```

# iteration 39 security — check-gate.sh テスト分離バグ修正（framework・M・test-only）

> 対象 diff: `git diff HEAD -- tests/test_failure_policy.py`（substantive は test のみ・本番 hook 不変）
> review: `docs/qa-reports/iter39-review.md` / plan: `docs/plans/2026-06-22-iter39-test-isolation-plan.md`

## スコープと結論

test-only 変更（本番 `check-gate.sh` 不変＝diff で確認）。**security🟢**（短絡せず正規実施・盲検 `security` エージェントで独立確認）。

## 検査項目

| 項目 | 結果 | 根拠 |
|------|------|------|
| テストコードの不安全パターン（injection 等） | **なし**（conf9） | `subprocess.run(["bash", str(path)], ...)` は arg-list・`shell=True` なし・payload は `json.dumps`（文字列補間なし）。temp は `mkdtemp`＋`addCleanup(rmtree)`。path traversal なし。 |
| lib コピー方式の安全性 | **copy2（safe）** | symlink でなく `shutil.copy2`＝iter36 Bug A（os.chmod の symlink 追従で実リポ mode 破壊）を回避。コピーした 4 lib は hook が source する 4 本と完全一致（検証済）。 |
| **セキュリティテスト coverage の退行** | **退行なし・むしろ強化**（conf9） | check-gate は「plan 未承認なら code 編集を deny」する security gate。旧 `_scenarios()` 行は `ROOT=SCRIPT_DIR/..` で live STATUS を読み運頼みに pass する false-positive。専用メソッドは temp-root COPY（`ROOT=scratch`）で**両極**を固定＝`approved→allow` ＋ **`pending→deny`（fail-closed の security-critical アサート）**。弱い luck-pass を実 fail-closed 証明に置換。 |
| auth / secrets / 機密露出 / 信頼境界 | **触れていない**（conf10） | 該当変更なし。 |
| secrets 混入 | **なし** | scan clean（変更行に secret パターンなし）。 |
| deps 監査 | N/A（Python・lockfile なし） | ack。 |
| deploy-blocker | なし | M は deploy size-skip。 |

## 盲検 第2意見（self-attested）

1次 verdict を渡さず（fresh context・diff＋context のみ）`security` エージェントを独立ディスパッチ。subprocess 形・lib コピー方式・両極アサートの非 vacuous 性・coverage 退行有無を独立検証し、broken-python3 env が実際に bash フォールバックを強制することも確認。

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  agent: security
  verdict: approve
  confidence: 9
  note: subprocess arg-list（shell なし）・copy2（symlink mode-flip 回避）・両極 pending→deny が non-vacuous な fail-closed 証明＝security gate coverage は強化。auth/secrets/信頼境界 非該当・secret scan clean。6/6 green・broken-python3 が bash fallback を強制を確認。
```

1次 verdict=approve／2次（盲検 security）verdict=approve＝**一致**。divergence なし。

## 判定

**PASS（security gate approvable・🟢 見込み）**。Critical/Major ゼロ。test-only でセキュリティサーフェスなし・security gate coverage はむしろ強化。secrets0・deploy-blocker0・deps N/A ack。1次・2次とも approve 一致。

# M4 security レポート（iteration 33・盲検2次独立レビュー）

対象: 観測 hook の fingerprint/marker を hot-path から外す（commits `457f632..HEAD`）。
脅威モデル: 本フレームワークの「judge カードが未テストコードを緑認証しない（silent-green 禁止）」の保護。STRIDE 該当＝evidence ログの Tampering/Repudiation。

## 独立レビュー（security エージェント・1次 verdict 非開示・diff/spec のみ）

**verdict: approve。** 4 方向から破壊を試み、全て fail-close を実走確認:

1. **`fp="skipped"` は構造的に緑不可能**: reader は `(d.get("fp") or "") != current`（`build-judge-card.py:234`）でゲートし、`current` は 64-hex 必須（`:220-222` `_HEX64.match` False→unverified）。`"skipped"` は非 hex＝`current=="skipped"` でない限り通らない（不可能）。既存 `fp="error"` と同じ壁。
2. **分類器の食い違いは構成上 fail-closed**: 危険方向（実 fp＋ok の誤緑）は runner エントリの fp/marker 計算が byte 不変（`evidence.sh:250-251`）ゆえ発生しない。新規面＝「recorder が非ランナー判定」経路は常に `fp="skipped"`。recorder が fp を支配→reader が `:234` で棄却。20 ケース parity（env 代入/サブシェル/`uv run`/区切り/DQ・SQ マスク/改行/**500 文字 truncation 境界 498・500**）0 mismatch。truncation 安全＝recorder は truncated cmd を分類（`:238→:249`）し reader も stored(≤500) cmd を分類＝同入力。
3. **bash 3.2.57（macOS 既定）/ `set -euo pipefail`**: 空 `AEGIS_TEST_RUNNER_REGEX`→`is_test_runner_cmd` は `"false"`・unbound crash なし（`[@]:-` 既定＋`${#_ge[@]} -gt 0` ガード）。reader 側も空配列で fail-closed＝両側 green 不可。不正 regex→`"false"`。`IS_TEST=$(…)` は set-e を踏まない。
4. **失敗パス（post-bash.sh status=fail）**: `IS_TEST` は ReAct ヒント文のみ駆動・認証に無関係。`append_evidence fail` は分類前に無条件記録。誤分類は coaching nudge を失うだけ。

`sed -E -e -e`＝旧2連パイプと s///g で byte 等価、`grep -E -e -e`＝旧ループと OR 等価。`test_fixtures_is_test_runner_cmd` が緑偽装ガード含め固定。evidence/hooks/parity 33 passed。

## 残余（非ブロッキング・pre-existing）

patterns.sh / fingerprint.sh が敵対的に改変されない前提に依存＝既存の accident-prevention（非敵対）threat model（`docs/security-followups.md` 記録）。本差分で不変。

## secrets / deps

- 追加行に secret パターンなし（fp/marker は内部値）。deps 変更なし。

## 判定: PASS

```claims
verdict: approve
tests_pass: true
no_stubs: true
no_secrets: true
deps_clean: true
second_opinion:
  verdict: approve
  divergence_points: none
```

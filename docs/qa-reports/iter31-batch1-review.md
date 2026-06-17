# Review — iteration 31 / Batch1（ドッグフード由来 改善：control-plane フック精度 + git baseline）

- **対象 diff**: `git diff 9177854..HEAD`（実装 6 タスク＋ミラー＋枠組み）。
- **対象コミット**: 52dff43(1.1) / 864786f(1.2) / 801bbaf(1.3) / c4db78d(1.4) / 6895cbf(1.5) / 6d1b938(1.6) ＋ レビュー fix 76112bc / 8f85a5b。
- **手法**: subagent-dev の phase-level review。security 盲検 break-attempt を 3 ラウンド（reviewer 1次＋reviewer-maintainability 独立2次、各 fresh context・実フック実行）。

## 対照表（plan タスク × 実装 × 状態）

| # | plan タスク | 実装ファイル | 状態 |
|---|---|---|---|
| 1.1 | setup baseline commit | `bin/setup.sh`, `tests/test_setup_baseline.py` | 実装済。clean-install→1 commit / 既存リポ→no-op / 無関係ファイル非ステージ / identity fallback（hermetic）検証済 |
| 1.2 | judge stub 走査のみ CP 除外 | `scripts/build-judge-card.py`, `tests/test_judge_card.py` | 実装済。`STUB_NONCODE_PREFIXES` は `scan_stubs` のみ。`scan_secrets` は全走査維持（後退ゼロ）をテストで固定 |
| 1.3 | 証拠スクリプト allowlist | `hooks/check-control-plane.sh`, `tests/test_control_plane_allowlist.py` | 実装済。bare allow / chain・redirect は deny 維持 |
| 1.4 | bare `git add <dir>` → ask | `hooks/check-control-plane.sh` | 実装済。`-A`/`-f`/`-Af`/chain/`git apply` は deny 維持 |
| 1.5 | read-only パイプ allow | `hooks/check-control-plane.sh` | 実装済。write セグメント/その他複合は deny。最終セグメント fail-open 修正済 |
| 1.6 | 書込み先 path のみ deny | `hooks/check-control-plane.sh` (+76112bc/8f85a5b) | 実装済（後述レビュー修正 2 件込み） |

全 6 タスク実装・スコープ逸脱なし・ミラー byte-identical。

## レビュー経緯と検出（重要）

3 ラウンドで 3 件の moat 穴を検出。うち **2 件は Batch1 由来の後退＝同セッション修正**、**1 件は pre-existing＝繰り延べ（SF-001）**。

1. **🔴→修正 ブロックリスト穴**（reviewer, conf 10）: 1.6 のステップ(c)が write ユーティリティの**ブロックリスト**だったため、未列挙の in-place writer（`perl -i`/`patch`/`awk`/`sponge`/`ed`…）＋クォート CP 宛先が allow。変更前は `"hooks/` リテラルで deny していた→**真の後退**。**アロウリスト化（echo/printf/git commit のみ緩和、他は fail-closed）で修正＝76112bc。**
2. **🔴→修正 改行バイパス**（reviewer, conf 10）: 改行が区切りとして扱われず、benign な1行目（echo 等）の後続行 writer＋クォート CP 宛先が allow。line-oriented grep が複合要因。**CMD 抽出直後に `\n`/`\r`→`;` 正規化（フレームワーク慣習に一致）で修正＝8f85a5b。**
3. **🟠 繰り延べ（SF-001・pre-existing）クォート/エスケープ トークン分割**（reviewer ＋ reviewer-maintainability が独立検出, conf 10）: `cp x hooks""/lib/emit.sh`、`"ho""oks/"`、`hooks\/lib` 等。判定がシェルの「クォート除去＋トークン連結」を再現しないため素通り。**変更前 8f8eb2d でも同一 allow を実測＝Batch1 後退ではない。** 重く・救済を壊しうるため独立タスクへ（`docs/security-followups.md` SF-001、ユーザー合意で繰り延べ）。

## 後退ゼロの証拠（orig 8f8eb2d vs new HEAD・実フック比較）

control-plane への**内容書込み**全ケースで、new が orig より緩いものは **0 件**:

| コマンド | ORIG | NEW |
|---|---|---|
| `> hooks/x.sh` / `cp x hooks/y` / `cp x "hooks/y"` / `mv a "scripts/b"` | deny | deny |
| `perl -i ... "hooks/lib/emit.sh"` / `sed -i ... "hooks/lib/emit.sh"` | deny | deny |
| `echo x > "hooks/lib/emit.sh"` / `tee "scripts/x"` | deny | deny |
| `echo ok⏎cp a "hooks/d.sh"` / `echo "$(rm hooks/lib/emit.sh)"` / `bash -c "x > hooks/y"` | deny | deny |
| `D=h; D=${D}ooks; cp /dev/null $D/lib/emit.sh` | ask | ask |

意図した緩和（後退でなく改善）: `git commit -m "...STATUS.md..."` / `echo "...scripts/..."` / `echo 'see hooks/' >> notes.txt` / `grep ... scripts/ | head` / 証拠スクリプト → deny→allow/ask。

## テスト evidence

- full suite **822 passed / 1 skip**（既知 flake 非発火）。
- moat 回帰: `test_control_plane_allowlist`(40) / `test_control_plane_var_expansion` / `test_patterns_parity` / `test_secrets_*` 緑。
- REDTEAM PoC **18/18 ＋ 5/5**。
- contract 全 profile（minimal/standard/full）/ drift / mirror identity / scaffold smoke（3 profile）全 PASS。
- TDD が着手前に 2 つの実バグを捕捉（1.5 パイプ最終セグメント fail-open、1.6 空マスク）。

## 第2意見（盲検・self-attested）

reviewer-maintainability を fresh context（diff ＋ spec/plan のみ、1次の verdict 非共有）で独立ディスパッチ。**独立に SF-001（クォート分割バイパス）を検出**＝1次と収束。Batch1 変更自体（後退ゼロ・目的達成）には相違なし。

## 判定

**approve_with_notes** — Batch1 の変更は仕様準拠・後退ゼロ・全 evidence 緑。Critical 2 件（Batch1 由来）は修正済み。残る SF-001 は **pre-existing**（Batch1 が悪化させていないことを実測）かつ重い独立修正のため、最優先 follow-up として `docs/security-followups.md` に durable 記録し繰り延べ（ユーザー合意）。

```claims
tests_pass: true
no_stubs: true
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["independently surfaced SF-001 (pre-existing quote/escape token-splitting bypass); agrees it is not a Batch1 regression and is deferred"]
```

# iter53 レビュー — 破壊的コマンド警告の日本語化＋ドリフトガード

- 対象: 破壊的コマンドの permission prompt（ask）reason を英語→日本語化し、英語回帰を防ぐドリフトガードを追加。判定 regex・ask 発火ロジックは無改変＝moat 不変。
- 参照: plan `docs/plans/2026-06-28-destructive-warning-japanese-implementation-plan.md` / spec `docs/specs/2026-06-28-destructive-warning-japanese-design.md`
- diff: `hooks/lib/patterns.sh`（WARN 配列18件）/ `hooks/check-destructive.sh`（inline rm -r＋抽出失敗フォールバック）/ `hooks/check-secrets.sh`（抽出失敗フォールバック）/ 新規 `tests/test_destructive_warning_language.py`（6 テスト）。

## 対照表（plan タスク → 実装 → 状態）

| # | plan タスク | 実装ファイル | 状態 | 備考 |
|---|------------|------------|------|------|
| 1 | WARN 配列18件日本語化＋ドリフトガード（RED→GREEN） | `hooks/lib/patterns.sh` / `tests/test_destructive_warning_language.py` | 完了 | LOWER 2＋CMD 16・regex 無改変・RED(failures=21,errors=0)→GREEN |
| 2 | inline rm -r WARN 日本語化＋発火テスト | `hooks/check-destructive.sh` / 同テスト | 完了 | `rm -rf /important`→ask＋`再帰削除` distinctive 検証 |
| 3 | 抽出失敗フォールバック2件日本語化＋behavioral 発火 | `hooks/check-destructive.sh` `hooks/check-secrets.sh` / 同テスト | 完了 | truncated payload で destructive/secrets 実発火・distinctive 検証 |

未着手タスクなし。

## findings（severity・confidence・disposition）

| severity | finding | 出所 | disposition |
|---|---|---|---|
| 🟡 Should (conf8) | `*_REGEX`↔`*_WARN` の件数パリティ未検証。将来 REGEX 追加で WARN を入れ忘れると `check-destructive.sh:104` の並列 index 参照が空＝危険文ゼロの `[careful] ` が発火し、配列ガードもハードコード件数も捕捉しない | grill-code | **修正済**: `test_warn_regex_parity` 追加（LOWER/CMD で `len(WARN)==len(REGEX)`） |
| 🟢 Minor (conf7) | `chmod -R` の訳が「元の権限は復元されません」＝過大表現（chmod は権限を控えていれば戻せる・rm/shred の不可逆とは異なる）。英語原文も不可逆とは言っていない | 盲検2次 (reviewer-testing) | **修正済**: 「元の権限を控えていないと戻せません」に訂正（正確化） |
| 🟢 Minor (conf8) | ハードコード件数（2/16）と `test_warn_regex_parity` が一部冗長 | 盲検2次 | **受容**: 両者は別失敗モードを捕捉（両配列が同時縮小は parity を素通りするがハードコード件数が捕捉） |
| 🟢 Minor (conf7) | `_has_japanese` は ≥1 JP 文字で合格＝半訳（`deletes ファイル`）を通す | grill-code | **受容**: 目的は「英語のみ警告の排除」＝完全英語回帰を捕捉。一行コメントで限界明示済 |
| 🟢 Minor (conf7) | `_has_japanese` は U+4E00–9FFF のみ＝CJK Ext A/B 非対象 | 盲検2次 | **受容**: 全 WARN は BMP 常用漢字。Ext 対応は YAGNI |

🔴 Critical・🟠 Major なし。

## moat 確認

- 判定ロジック無改変: `git diff hooks/lib/patterns.sh` の REGEX 行 diff ゼロ。WARN 値は `emit_ask "[careful] $WARN"` の引数として渡るのみで、条件分岐に使われない（判定汚染なし・2次が独立確認）。
- 既存 destructive/secrets/control テスト **88 passed**＝ask/allow 決定不変（behavioral 証拠）。
- 英語 pin grep NONE＝英語 WARN 本文を assert する既存テスト不在（無更新前提を担保）。
- emit.sh の JSON 透過: 日本語＋全角/半角括弧混在でも `json.loads()` 成功（層2/3 テスト実行が実証・2次も確認）。

## tests

- 新規 `tests/test_destructive_warning_language.py` **6 passed**（chmod 訂正・parity・distinctive 追加後・手動実行）。
- full suite は implement 時点で **1177 passed / 1 skipped**。以降の修正は同テストファイル＋patterns.sh（reason data・chmod 1行）のみ。**権威ある full suite 再走は qa ゲートで実施**（test 実行は qa の領分）。

## verdict

🟡 Should（parity）は実装内で解消。🟢 Minor の chmod 過大表現は正確化。残りは別失敗モード担保／YAGNI で受容。moat 不変（regex 無改変・判定汚染なし・88 既存テスト green）を3層で実証。**approve**。

```claims
verdict: approve
second_opinion:
  verdict: approve
  divergence_points:
    - "2次(reviewer-testing)は diff/spec/plan のみの fresh context で独立実行し、moat 不変・JSON 透過・層2/3 の意図分岐到達を自走テストで確認"
    - "2次が chmod 訳の severity 過大表現を独立指摘→正確化（元の権限を控えていないと戻せません）"
    - "2次が _has_japanese の CJK Ext 非対象とハードコード件数の冗長を指摘＝いずれも蓋然性低／別失敗モード担保で受容"
```

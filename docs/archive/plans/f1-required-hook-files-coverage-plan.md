# F1 修正計画: REQUIRED_HOOK_FILES が稼働 hook 4件を欠く

> 監査: `docs/functional-integrity-audit-report-2026-06-07.md` F1（P2）
> 種別: bugfix（framework・contract カバレッジ）

## 問題

`check_framework_contract.REQUIRED_HOOK_FILES` は12 hook（+lib/extract-input）のみ列挙し、
`check-cron-gate.sh` / `check-skill-gate.sh` / `check-task-created.sh` / `check-task-completed.sh` を欠く。
これらは hooks.template.json と example settings.json に登録され両ツリーに実在・稼働する PaC enforcement hook。

contract の「template 登録チェック」（L620-669）は required 集合を REQUIRED_HOOK_FILES から導出するため、
この4 hook が **template から登録解除されても fail しない**＝Skill/Cron/Task の enforcement が黙って無効化されうる。
コメントの「single source of truth」表記と実態が乖離。

## 修正方針

### (A) manifest に4 hook を追加
- `REQUIRED_HOOK_FILES` に4 hook（cron/skill/task-created/task-completed gate）を追加。
- `REQUIRED_EXAMPLE_FILES` に対応する example/hooks/ の4 hook を追加（既存12 hook と同じ扱いに揃える）。
- 4 hook は両ツリーに実在するため、追加しても contract は緑のまま（より厳格化されるだけ）。

### (B) 回帰防止: 両 manifest の不変条件テスト
`tests/test_hook_required_coverage.py`（新規・小）で **root と example の両方向**を守る:
- **B-1 root**: hooks.template.json が登録する hook ⊆ `REQUIRED_HOOK_FILES`（hooks/*.sh・**lib/ は除外**＝
  template は lib を登録しないため）。
- **B-2 example**: `examples/.../settings.json` が登録する hook ⊆ `REQUIRED_EXAMPLE_FILES` の example hooks。
  example も同型の穴を持つ（settings は16登録／REQUIRED_EXAMPLE_FILES は12）ため両方向を守らないと
  「example settings に足したが REQUIRED_EXAMPLE_FILES に足し忘れる」class が再発する。
- **B-3 向きは ⊆（= にしない理由）**: contract は既に**逆向き** `REQUIRED ⊆ registered`（L620-669）を強制
  しており、両者で実質 `==` をピン留めする。`==` を test 単体で課すと、「REQUIRED に在るが template 未登録
  （手動起動・別機構発火）の hook」という**正当な将来ケース**を誤検知するため、⊆ が future-robust。
- 現状は root で4 hook 不足 → **RED**。(A) 適用で root/example 両方向 **GREEN**。
- これにより「新 hook を登録したが manifest に足し忘れる」class を恒久封鎖（F1 自身がこの class の発生例）。
- パース: hooks.template.json/settings.json の hook 抽出は contract と同じ正規表現
  （`hooks/([a-z0-9_-]+\.sh)`）を使う旨をコメントで明記し、将来の乖離を防ぐ。

## TDD 手順

1. **RED**: (B) を追加 → 現状 REQUIRED_HOOK_FILES が4件不足で FAIL。
2. **GREEN**: (A) を適用 → 登録 hook ⊆ REQUIRED_HOOK_FILES が成立し PASS。
3. tier0(unittest)・contract(full/standard)・drift・全層 green 確認。

## 影響範囲・非影響

- 変更: `scripts/check_framework_contract.py`（REQUIRED_HOOK_FILES＋REQUIRED_EXAMPLE_FILES）／
  `tests/test_hook_required_coverage.py`（新規）。
- hook ファイル・template・example の中身は無変更（既に実在）。ミラー無影響。
- version: 版締めまで保留。

## 完了条件

- (B) が RED→GREEN。tier0・contract・drift・strict 全 green。
- grill-code 通過。

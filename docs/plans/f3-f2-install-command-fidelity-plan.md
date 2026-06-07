# F3+F2 修正計画: install コマンド配送の整合性

> 監査: `docs/functional-integrity-audit-report-2026-06-07.md` F3（P2）・F2（P2）
> 種別: bugfix（framework・install 配送）/ 設計判断なし → TDD

## 共通の根（F6 と同系）

setup.sh が「framework の進化に追従できず、install 先に正しいコマンド面を配送できていない」。
2つの症状を1ユニットで直す。

### F3: retro.md の scaffold-safe 変種が install に繋がらない

- retro.md は `MIRROR_ALLOWLIST`（drift）= {validate.md, **retro.md**} に入る**意図的 scaffold-safe 変種**を持つ
  （example 版＝「retro_report.py が無ければ手動要約に degrade」guard 付き）。
- だが setup.sh `resolve_source` は **validate.md だけ**を example 変種にマップし、retro.md は default
  （framework root 版＝無条件 `retro_report.py` 実行）を install。retro_report.py はどの profile にも無い
  ため full install で `/retro` がエラー。
- 不変条件: **MIRROR_ALLOWLIST のコマンドは全て resolve_source で example 変種に配送されねばならない**。
  現状 validate.md ✓ / retro.md ✗。

### F2: /judge が全 profile に無く install されない

- judge.md は contract 必須・README 記載（8コマンドの1つ）・root/example 同一。だが profile の
  required/recommended に無い。裏方 build-judge-card.py は full の recommended にある。
- full install で build-judge-card.py は届くのに `/judge`（B2 tri-state カードのプレビュー入口）が無い。

## 修正方針

### (A) F3: resolve_source に retro.md → example 変種マップを1行追加
validate.md と同じ扱い:
```sh
".claude/commands/retro.md")
  echo "$FRAMEWORK_ROOT/examples/minimal-project/.claude/commands/retro.md"; return ;;
```

### (B) F2: judge.md を full.json の `required` に追加（決定）
他7コマンド（status/gate/validate/recover/next/retro/tutorial）と同じ `required` 配列へ。README が
8コマンドとして数える中核なので `required` が妥当（recommended でなく）。standard には足さない（standard は
build-judge-card.py を配布しないため /judge が裏方不在で壊れる）。
- **なぜ contract/drift に無影響か**: `--profile=full` は profile JSON を消費せずハードコードの REQUIRED_* を
  見る。drift は profile required の framework root 存在のみ見る。judge.md は root 実在ゆえ両者緑のまま。

### (C) 回帰防止: scaffold smoke に command-surface 検証（不変条件を自己強制）
`eval_scaffold_smoke.py` に `verify_command_surface(target, profile)` を新設し、contract/hook 検証後に呼ぶ。
- **C-1** `check_reference_drift.MIRROR_ALLOWLIST` を **import**（単一真実源）。profile が install した
  allowlist コマンドは **installed == example 変種（byte）** を assert。→ 「allowlist ⊆ resolve_source 配線」を
  自己強制。将来 allowlist に足すだけで test が自動拡張＝F3 と同型の「足したが配線忘れ」class を封鎖。
  （ハードコードした `[validate, retro]` リストは使わない。再発防止にならないため。）
- **C-2** retro は加えて **installed が graceful guard 文字列 `available` を含む**ことを assert（byte 一致だけだと
  将来 example から guard が消えても通るため、degrade 性を意味的に保証）。
- **C-3** full は `.claude/commands/judge.md` 存在を assert（F2）。
- **C-4** 失敗は collect して列挙（RED で retro/judge 両方を可視化）。
- 補足: drift には scaffold-safe を表す集合が2つあり食い違う（`MIRROR_ALLOWLIST={validate,retro}` vs
  `check_example_commands:intentional_divergence={validate}`）。今回は触らず、新 finding 候補として report に記録。

## TDD 手順

1. **RED**: (C) を先に追加。現状 full scaffold で retro.md が framework 版＝example と byte 不一致 → FAIL。
   judge.md も不在 → FAIL。
2. **GREEN**: (A)(B) を適用 → full scaffold で retro=example変種・judge 存在 → PASS。
3. 全層 green 維持を確認。

## 影響範囲・非影響

- 変更: `bin/setup.sh`（resolve_source 1行）, `templates/profiles/full.json`（judge 追加）,
  `scripts/eval_scaffold_smoke.py`（verify_command_surface 追加）。
- **ミラー不要**: setup.sh / full.json / eval_scaffold_smoke は MIRROR 対象外。
- **version**: 版締めまで保留（F6 と同方針）。aegis 自身の STATUS も版締めでまとめて更新。
- drift/contract への影響: judge.md は root に実在しREADME記載済のため、full.json への追加で drift/contract は
  緑のまま（profile required は framework root に存在すれば良い）。

## 完了条件

- scaffold smoke の command-surface 検証が RED→GREEN。
- 実 full install で `/retro` が graceful 版・`/judge` が存在することを手動再確認。
- Layer 0 全 green 維持。grill-code 通過。

# F5+F7 修正計画: P3 polish

> 監査: `docs/functional-integrity-audit-report-2026-06-07.md` F5（P3）・F7（P3）
> 種別: docs/cosmetic（hard break なし）。TDD は対象外（prose / コメントのみ）。

## F5: 「artifact template を開く」指示の不整合

`.claude/skills/client-workflow/SKILL.md:90`「その後はフェーズに応じた artifact template だけを開く。」
だが setup.sh は `templates/*.template.md` を project に配布しない（CLAUDE/STATUS/LEARNINGS/CLIENT-*/
TRANSLATION-MAPPING のみ instantiate）。install 先にテンプレが無く、この指示が字義通り実行できない。
成果物作成自体は skill の構造記述から可能なので破綻はしない（P3）。

### 修正 (F5)
client-workflow:90 は **context-budget セクションのロード規律ヒューリスティック**（hard 指示ではない）。
予算メッセージを bloat させないよう **最小1語**に抑える: 「その後はフェーズに応じた artifact
（テンプレートがあればそれ）だけを開く。」。client-workflow は MIRROR 対象ゆえ**両 copy を同一文面**で編集。

## F7: drift の scaffold-safe 集合の二重・食い違い

`check_reference_drift.check_example_commands` の `intentional_divergence={"validate"}` と
`MIRROR_ALLOWLIST={validate,retro}` が食い違って見える。**だが両者は別概念**:
- `MIRROR_ALLOWLIST`: 内容/byte divergence の除外（root↔example が byte 違ってよい）。
- `intentional_divergence`(check_example_commands): **存在** divergence の除外（example にあって root に無くてよい）。

validate/retro は両方 root に存在するため、この存在チェックでは元々 flag されず、`{"validate"}` は
**vestigial**（効いていない）。retro を足して「揃える」のは**概念の混同**で誤り。

### 修正 (F7)
`intentional_divergence={"validate"}` は**誤り**: validate は example-only ではなく root にも実在するので、
この存在チェックでは元々除外不要（vestigial）。`{"validate"}` を残すと「validate は example-only」という
誤解を招く。→ **空集合 `set()` に修正**し、「これは example-ONLY コマンドの除外（現状ゼロ）であり、
MIRROR_ALLOWLIST（両ツリーに在り内容が違ってよい command）とは別概念」と明示するコメントを追加。
機能は不変（example の8 command は全て root に実在、空集合でも warnings ゼロ）。

## TDD / 検証

- prose とコメントのみ＝ロジック不変。RED/GREEN test は無し。
- 検証: drift（mirror-identity 含む）・contract・全層 green を維持（client-workflow mirror 一致を確認）。

## 影響範囲・非影響

- 変更: `.claude/skills/client-workflow/SKILL.md`（root）＋
  `examples/minimal-project/.claude/skills/client-workflow/SKILL.md`（mirror・byte 一致）＋
  `scripts/check_reference_drift.py`（コメントのみ）。
- ロジック・配布・契約への影響なし。version は版締めまで保留。

## 完了条件

- client-workflow root/example byte 一致で drift 緑。全層 green 維持。
- grill-code 通過（軽量）。

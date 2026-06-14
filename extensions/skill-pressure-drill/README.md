# skill-pressure-drill（拡張・手動 opt-in）

判断系 skill が adversarial なユーザ要求でも遵守されるかを、実 subagent で圧力テスト
する opt-in 足場。決定論の層1（skill behavior contract・`scripts/skill_behavior_manifest.py`）
を補完する層2。

## 位置づけ

- **manual opt-in**。`setup.sh --profile` には含めない（コア契約外）。
- 実エージェント実行はコスト/flake があるため CI には載せない。実走判断は運用者。
- 形式（シナリオ／レポート雛形）のみ `tests/test_skill_drill_format.py` が決定論検査する。

## 前提

- 実 subagent を起動できるライブ Claude Code セッション（Task/Agent ツール）。
- 対象 skill がロードされる aegis 環境（subagent への skill ロードは `WORKFLOW.md` 参照）。

## 構成

- `WORKFLOW.md` — 実行手順。
- `scenarios/*.md` — adversarial シナリオ（対象 skill・プロンプト・採点 rubric）。
- `REPORT.template.md` — 採点レポート雛形。

## 使い方

`WORKFLOW.md` に従う。

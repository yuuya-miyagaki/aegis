# skill 圧力ドリル 実行手順

> 実エージェントで skill の adversarial 遵守を検証する。手動・opt-in。CI には載せない。

## 前提

- 実 subagent を起動できるライブ Claude Code セッション。
- **対象 skill が subagent の context に確実に載ること。** Agent ツールで起動した
  subagent は aegis の phase 注入を受けないため、対象 skill が自動ロードされる保証は
  ない。これを担保しないと「skill 遵守」でなく素の Claude を測るだけになりドリルが
  無意味化する。最低限、subagent プロンプトに対象 `SKILL.md` の本文を同梱する
  （または skill がロードされる経路で起動する）こと。

## 手順

1. `scenarios/<x>.md` を 1 つ選び、`target_skill` と各セクションを読む。
2. **subagent を 1 つ dispatch** し、対象 `SKILL.md` 本文＋`adversarial_prompt` の本文を
   渡す（skill を context に載せる）。
   - 「これはテスト」「skill を守れ」等のメタ指示は**渡さない**（悟らせない）。
   - adversarial_prompt は実ユーザの依頼としてそのまま提示する。
3. subagent の応答・ツール使用を観測し、`expected_adherence` の PASS/FAIL 条件に
   照らして採点する。判定根拠（どの挙動が条件のどれに当たるか）を明記する。
4. `REPORT.template.md` を雛形に
   `docs/qa-reports/skill-drill-YYYY-MM-DD-<target_skill>.md` を作成する。
5. FAIL の場合、対象 skill の指示文を rationalization に抗えるよう補強する fix へ回す
   （RED→補強。superpowers writing-skills と同型）。

## 注意

- 採点は人手（オーケストレータ）の判断。ハーネスは強制しない。
- シナリオは運用で増やす。新規シナリオは本拡張の形式に従い、
  `tests/test_skill_drill_format.py` が形式を検査する。

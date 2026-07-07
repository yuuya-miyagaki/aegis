# セキュリティレビュー — iteration 62（委譲拘束 SoT 標準化・R1 文言層）

- date: 2026-07-07
- task: framework / L / v1.23.0 予定
- 対象 diff: .claude/rules/routing.md・4 SKILL.md・tests/test_skill_guidance_tokens.py・scripts/context-budgets.json（＋docs 簿記）

## OWASP Top 10 チェックリスト（該当項目のみ）

- [x] **Injection**: 該当なし — 実行コードの変更ゼロ（md/json/pytest のみ）。追加テキストはシェル・SQL・HTML に評価される経路なし。
- [x] **Sensitive Data Exposure**: 変更行の secrets スキャン実施 — credential/key/token 実体のヒットゼロ（パターン一致は「token pin」等のドリフト封鎖用語のみ）。
- [x] **Security Misconfiguration**: enforcement 面（hooks/・bin/）の変更ゼロ＝moat 不変。scripts/ の変更は context-budgets.json（データ registry）のみで、budget は**引き上げ方向**＝検査が緩むのは語数上限のみ・偽装は `test_real_repo_check_is_green` が検知（B1 mutant 6/7 で赤化実証）。tracked ファイルの実行属性変化なし（mode-flip ゼロ）。
- Broken Authentication / Vulnerable Dependencies: 該当なし（認証面なし・依存パッケージ変更なし）。

## Evidence Checklist

- [x] Grep で secrets/credentials パターンを検索した（変更行・ヒットゼロ）
- [x] 外部入力のサニタイゼーション: 該当なし（入力処理コードなし）
- [x] dependency audit: 依存変更なし（既知の deps advisory は従来どおり 🟡 ack 対象）
- [x] 全 finding に severity と remediation を付与した（下記）

## セキュリティ観点の分析（本変更の性質）

本 iter は**それ自体がセキュリティ強化**（iter60 事故クラス＝検証サブエージェントによる親 tree 破壊の文言層防御）。攻撃面の評価:

1. **防御の弱体化なし**: 既存 enforcement（patterns.sh 9パターン・snapshot 退行ガード・tamper-evidence）に無変更。追加は guidance prose と drift-pin テストのみ。
2. **新設 SoT の改竄耐性**: 6点目の2否定（modify/run）・コマンド列挙・汚染時プロトコル・無条件宣言・見出し一意性を pin 9本で封鎖。意味反転（may run 化）は B1 drill で赤化実証（mutant 1/11）。
3. **偽装耐性**: budget 簿記の過小偽装は real-repo check で赤化（mutant 6-7/11）。pin テスト自体の破壊も赤化（mutant 8-11/11）。
4. **文言層の限界（残留・受容）**: 親が拘束を委譲プロンプトに実際へ含めることはハーネス強制不能（self-attested）。機械層（iter61）・復旧層（snapshot）との3層防御で被覆済み＝全体レビュー R1 の設計どおり。

## Findings

- 1次: なし（Critical/Major/Minor ゼロ）。
- 残留リスク（受容・記録）: 上記4（文言層 self-attested）／deps 未 audit（変更なし・従来 🟡 ack）。

## 盲検2次の指摘と対応

- **Major-1（diff 外・drill runner の潜在欠陥が顕在化・ship 前対処済み）**: B1 drill の同バイト長 mutant（`1`→`2`）＋同秒 revert が macOS ミラーキャッシュ（com.apple.python）の pyc を汚染＝mtime/size 一致でキャッシュ有効判定→変異版バイトコードが実行され full suite が偽 RED 化（`test_sot_section_present_and_unique` 1 failed）。**対処＝`touch tests/test_skill_guidance_tokens.py` で mtime バンプ→キャッシュ無効化→19 passed 確認→full suite 再実走 recorded: green**。セキュリティ含意（同機構で偽 GREEN 方向の弱体化変異がソース無汚染で残留可能＝tamper-evidence バイパス経路）は本 iter の diff とは独立の drill runner 欠陥＝**恒久対策（子プロセスへ `PYTHONDONTWRITEBYTECODE=1`＋restore 後 mtime バンプ）を Phase 1-5（drill 強化）へ起票**。
- **Minor-1（residual・受容）**: 禁止列挙に `git switch` 欠落 — 機械層が branch switch を意図的に allow（誤爆ゼロ方針・patterns.sh の accepted residue）としており、列挙は機械層の ask 集合と整合。破壊形（`switch -f/--discard-changes`）は一般禁止句「MUST NOT modify existing files」が最終防衛線。列挙追加は pin token・4消費側・機械層 parity の同時更新が必要＝文言・機械の両層セットで別テーマ起票。
- **Minor-2（residual・受容）**: 「the assigned path」の指定責務が未定義（委譲プロンプトがパス非明示の場合の解釈余地）— 文言層の既知限界内。「委譲時に書込み先パスを必ず明示」の1文追加を同別テーマに含めて起票。
- Info: 上記以外ゼロ。budget 偽装なし（実測厳密一致）・enforcement 無変更・secrets ゼロ・盲検性維持を2次が独立確認。

## deploy blocker

なし（Major-1 は ship 前に解消済み・再現手順と対処を本レポートに記録）。

## 総合判定

- 判定: approved

## Claims（judge が機械読取する）

```claims
verdict: approve
second_opinion:
  verdict: approve_with_notes
  divergence_points: ["Major-1: drill の同長 mutant が pyc ミラーキャッシュ汚染→偽 RED（diff 外の runner 欠陥・touch+再record で ship 前解消・恒久対策は Phase 1-5 起票）", "Minor-1: 禁止列挙に git switch 欠落（機械層 allow と整合・一般禁止句が防衛線・別テーマ起票）", "Minor-2: assigned path の指定責務未定義（文言層限界内・同別テーマ起票）"]
```

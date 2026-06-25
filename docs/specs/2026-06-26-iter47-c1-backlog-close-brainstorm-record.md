# ブレインストーミング記録
<!-- 正本: brainstorming skill -->

## 日付

- 2026-06-26（iteration 47）

## テーマ

- full-review backlog 最後の残項目 **C1**（フック入力抽出・matcher の構造的留意点）を triage し、backlog 全体を triaged-complete としてクローズする。

## コンテキスト

- iter41-46 で full-review（2026-06-24）の項目を順次処理（D1-4/I1/I2=iter41・G1-3=iter42・I3=iter43・C5=iter44・C2/C3=iter45・C4/G4=iter46）。残るは C1 のみ。
- C1 は「MultiEdit バイパスは現行 platform で不成立」という**訂正 finding**で、残るのは 2 つの構造的留意点。

## 検討したアプローチと grill-premise の結論

grill-premise で「C1 は直す価値のある robustness/security 課題か」を一次情報（コード）で検証:

- **(1) `extract-input.sh:20` first-path-only**: `head -1` で最初の file_path/notebook_path のみ抽出。だが現行 built-in write tool は Edit/Write/NotebookEdit で**各 1 パス**、MultiEdit は廃止済。複数パスを渡す経路が無く**現状到達不能**。duplicate-key JSON も LLM の単一スキーマ tool 呼び出しでは生成不能（脅威モデル＝self-bypass の外）。
- **(2) matcher のツール名ホワイトリスト**（`platform_manifest.py:46` `KNOWN_TOOL_NAMES`）: 現行 write-tool は Edit/Write/NotebookEdit で**全カバー**＝漏れなし。しかも `stale_keys()`（180日・`PLATFORM_VERIFIED["tool_names"]="2026-06-14"`）が再検証を催促する機構が**既に存在**＝full-review の Fix 案（再検証時に write-tool 列挙）は部分的に機械化済み。

→ **結論: C1 は現状到達不能＋既存機構でカバー済み＝実コード修正は不要**（C4=NOT-A-VULN・G4=by-design に続く 3 件目の「by-design / not-reachable」帰着）。将来 multi-path write-tool が追加された時にのみ再評価が要る forward-looking robustness 項目。

## 決定

- 採用: **C1 を `docs/security-followups.md` に SF-009（forward-looking robustness・accepted residual）として記録し、full-review backlog 全体を triaged-complete としてクローズ**。コード変更なし。
- 不採用: (a) first-path-only の防御コード追加＝存在しない入力への防御で YAGNI・テスト不能。(b) matcher の動的列挙コード＝stale_keys 機構と重複。
- 右サイジング: **framework / S**（docs-only・trivial scope・1 SF 追記＋backlog 行更新の 2 docs ファイル・zero code/behavior/risk）。S フロー＝brainstorm→implement→review→ship（plan/qa/security/deploy 免除）。C4/G4（M）より低 stakes（verdict は code＋grill で確認済の forward-looking 整理）。

## スコープ境界

- やること: SF-009（C1 disposition）追記／full-review backlog 行を triaged-complete に更新／C1 finding に pointer。LEARNINGS に backlog 完了の振り返り 1 件。
- やらないこと: first-path-only の防御コード／matcher の動的列挙／新規ファイル／脅威モデル外の防御／README 変更。

## 未解決事項

- なし（grill-premise で verdict 確定）。次イテレーション以降の方向性（v0.13.0 残項目・future-proof 再アーキ・配布強化）は backlog クローズ後にユーザーと相談。

## 次のステップ

- [x] 設計ノート → `docs/specs/2026-06-26-iter47-c1-backlog-close-design.md`

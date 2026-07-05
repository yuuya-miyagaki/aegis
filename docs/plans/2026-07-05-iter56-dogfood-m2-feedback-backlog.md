# iter56 起票: ドッグフード二周目（M2）フィードバック反映 — バックログ

> **ステータス: 起票のみ（未着手）**。着手時に iteration rollover（`scripts/update-task.sh`・
> dev ゲート reset・iteration=56）と設計書（docs/specs/）→実装計画（docs/plans/）を作成すること。
> iter55 は push 済（origin/main=9578612・v1.16.0）。未 push は本起票コミットのみ。

## 一次情報（正本・yoga-tsukinowa-lp 側）

- 観測ログ: `~/Desktop/personal/yoga-tsukinowa-lp/DOGFOOD-M2-LOG.md`
- 教訓: `~/Desktop/personal/yoga-tsukinowa-lp/docs/LEARNINGS.md`（「フレームワーク改善」セクション）
- レトロ: `~/Desktop/personal/yoga-tsukinowa-lp/docs/retro-m2-2026-07-05.md`

## iter55 実効検証の結果（M2 で確定）

- **回帰 0 件・チェックリスト 6/6 ✅** — 一周目の戦闘1〜7 すべて実使用で解消を確認
  （戦闘1 stderr リダイレクト / 戦闘2・4 メタ文書 / 戦闘3 translation ref タイミング /
  戦闘5 update-task.sh / 戦闘6 チェーン専用文言 / 戦闘7 スクリプト allowlist）
- 戦闘7 のみ「hook は ALLOW・ファイル自体が scaffold 未同梱」という**別レイヤの drift** が露出（→候補⑥）
- M2 集計: 迷子 0・実質ゲート戦闘 0（新規 deny 3種はすべて文面 or `--` で即回避・進行を止めず）・
  人手介入 1 回・blocking 0・[P4] ブラウザ QA 見逃し 0・295 tests green（+103）・二周目完走
- iteration-2 機構（reset→再入→CHANGES.md→spec-delta 検査→再承認）は初実戦で設計どおり機能

## 候補6件

| # | テーマ | 優先度 | 種別 |
|---|--------|--------|------|
| ① | secrets hook の先頭ドット誤検知 | P1 | hook 判定バグ（moat） |
| ② | ドリル skip 経路の claims 検査 | P1 | skill×judge の契約矛盾 |
| ③ | verdict 名目差の 🟡 閾値 | P2 | judge 判定の段階化 |
| ④ | subagent-dev への共有テスト DB ルール | P2 | skill 追記のみ |
| ⑤ | spec-delta 🟢 通過時の1行出力 | P2 | 可視性（1行） |
| ⑥ | retro_report.py の scaffold 同梱漏れ | P1 | install 契約の穴 |

### ① secrets hook の先頭ドット誤検知 — P1

- **観測**: `git add .env.example`・`git add .gitignore` が「git add -A / git add . の可能性」
  として deny（M2 で2回再現）。`git add -- <file>` で回避可。subagent（T3）はこの deny で
  コミットを断念し親へエスカレーション（挙動自体は正しい）
- **根因（裏取り済）**: `hooks/check-secrets.sh:148` の広範 staging 検出
  `add[[:space:]]+(-a|--all|\.)` — 末尾の `\.` がトークン境界でアンカーされておらず、
  先頭ドットのファイル名（`.env.example` 等）に**前方一致**する。`--` 経由が通るのは
  `add` 直後のトークンが `--` になり正規表現に掛からないため
- **修正方向**: `\.` を「後続が空白 or 行末」に限定＋負例テスト
  （`.env.example`/`.gitignore` の個別 add は broad 扱いしない、`git add .`/`git add . foo` は維持）。
  **付随論点**: `.env.test` は safe-list（example/template/sample）対象外で恒久 deny
  （最初の `.env` 正規表現 `check-secrets.sh:140` に掛かる）。プレースホルダのみのテスト env を
  コミットする慣行と不整合だが、中身検査なしで `.env.test` を安全扱いにするのは危険側 —
  safe-list 追加は慎重に判断し、deny 維持なら文言に `git add -- <file>` 回避と理由を明記する案を推奨

### ② ドリル skip 経路の claims 検査 — P1

- **観測**: drill skip 時は `current_refs.qa` をハーネス生成の `test-strength.md` にする規約
  （qa-verification SKILL.md:127・154-155「さもないと完了時に証拠不足で弾かれる」）のため、
  claims ブロックを構造的に置けず judge が「claims 未提出」🟡 → 毎回 ack（QA レポート側に
  書いても judge は ref 先しか見ない）
- **根因（裏取り済）**: `scripts/build-judge-card.py:374-376` は ref 先の claims しか読まない。
  さらに **framework repo 自身は STATUS.md 罠(p) で「skip 時は claims 付き qa レポートを
  ref にする」運用を既に発見済み**で、配布 skill の指示（test-strength.md 固定）と矛盾している
- **修正方向（推奨）**: skill を罠(p) 運用に揃える — skip 時は claims 付き qa レポートを ref に
  し、TaskCompleted / contract の evidence 検査がそれを受理することをテストで確認。
  代替: judge が skip 検出時に `docs/qa-reports/` の qa レポート claims へフォールバック

### ③ verdict 名目差の 🟡 閾値 — P2

- **観測**: 1次=approve / 2次=approve_with_notes の**名目差**で「1次/2次 verdict 相違」🟡 が
  M2 で3ゲート連続発火 → 毎回 ack は形骸化リスク（実質的相違＝Critical/Major の有無や
  remediation 未実装を見ていない）
- **根因（裏取り済）**: `scripts/build-judge-card.py:380-385` が verdict 文字列の単純不一致で判定
- **修正方向**: {approve, approve_with_notes} 同士は「相違」としない段階化。ただし
  approve_with_notes の notes 放置を見逃さない設計とセット（notes 未解消の機械検出 or
  🟡 文言に notes 要旨を出す）。reject/blocked が絡む相違は従来どおり 🟡 維持

### ④ subagent-dev への共有テスト DB ルール — P2

- **観測**: 並行 implementer の integration テストが同一テスト DB（tsukinowa_test）で衝突し
  偽 fail（TRUNCATE の相互破壊。vitest の fileParallelism:false はプロセス内のみ有効）。
  現行の並列規則は「同一ファイル変更の禁止」だけで、**共有可変資源**を想定していない。
  「integration 実行タスクは wave あたり常に1体・unit のみのタスクと組む」運用で以降衝突ゼロ
- **修正方向**: `.claude/skills/subagent-dev/SKILL.md` の並列規則（Boundary Map）に
  共有可変資源（テスト DB・ポート・グローバル状態）の項を追記。標準＝integration 実行タスクは
  wave あたり1体、代替＝DB/スキーマの per-agent 分離を注記。ドキュメントのみ・実装変更なし

### ⑤ spec-delta 🟢 通過時の1行出力 — P2

- **観測**: iteration≥2 の CHANGES.md（spec-delta）検査は合格時に**無言**で通過するため、
  「検査が走って合格した」のか「対象外だった」のかを承認ログから区別できず、確認に
  check_status.py のコード読解が必要だった
- **根因（裏取り済）**: `scripts/check_status.py:150-162`（`_spec_delta_issues`）は合格時に
  空リストを返すのみで、ゲート承認フローに肯定出力がない
- **修正方向**: ゲート承認出力（update-gate.sh / check_status のゲート検査）で、required かつ
  合格時に `[spec-delta] CHANGES.md 検査 OK（iteration=N）` を1行出力（検査対象外の時は出さない）

### ⑥ retro_report.py の scaffold 同梱漏れ — P1

- **観測**: scripts-manifest.tsv に allow 記載（hook は ALLOW）だがインストール先にファイルが
  無く、/retro が手動フォールバックになった（M2 レトロで実測）
- **根因（裏取り済）**: `templates/profiles/full.json` の required+recommended は scripts 8本のみ。
  manifest の実行可クラス（allow|ask）12本のうち **retro_report.py・check_reference_drift.py・
  learnings_search.py・lint_names.py の4本が未配布**。iter55 の install 実発火テストは
  「hook が allow する」ことは検証したが「ファイルが存在する」ことは検証していない。
  なお `bin/setup.sh:158-159` は「retro_report.py 不在時に劣化動作する scaffold 変種の retro.md」を
  意図的に配布しており既知の劣化許容だった可能性がある — ただし full プロファイルの自己記述
  （"all files including … scripts"）と矛盾
- **修正方向（推奨）**: full プロファイルへ未配布4本を追加＋contract（check_scripts_manifest）に
  方向4「配布される skill/command md が参照する runnable スクリプトは、当該プロファイルが
  配布する」検査（または install 契約テスト）を追加。minimal/standard は現状維持
  （劣化変種がそのまま効く）

## 候補外・記録のみ（M2 の新規観測）

- grep 交替演算子（引用符内の `|`）が CHAIN_OPS 判定に当たり read-only grep でも deny
  （mask_quoted は mention 検査専用）。単一パターン分割で回避可・頻度が上がれば iter57+ で検討
- 原因不明の control-plane deny 1件（CP path 非含有の複合コマンド・resolver の fail-closed 推定・
  回避容易）
- repo 直下 prose carve-out が *.md 限定のため、plan ゲート pending 中の `.gitignore` 片付けが
  block（fail-closed として妥当・文面明快。頻度が上がれば拡張検討・conf5）
- qa-browser の途中停止の根治は未達（5項目分割＋SendMessage 再開で運用としては確立。
  「全項目完了まで最終報告を出さない」拘束の skill 昇格は retro Try#2 ＝委譲プロンプト改善として別途）
- judge「テスト未検証」deny 文面に是正手順（record-test-result.py）の案内がない／
  gate レポートテンプレに claims 雛形がない（③⑤と同系の可視性改善 — iter56 実装時に同梱を検討）

## 推奨着手順・規模

- **推奨**: P1（①⑥②）→ P2（③⑤④）の順で、全件独立のため 1 イテレーション一括が効率的
- **規模想定**: L（hooks/check-secrets.sh・scripts/build-judge-card.py・scripts/check_status.py
  または update-gate.sh・templates/profiles/full.json・contract/install テスト・
  subagent-dev / qa-verification SKILL.md ＋新規テスト複数 ＝ 6+ ファイル）。
  check-secrets の判定変更＝**moat 変更を含むため全ゲート必須**
- **前提**: なし（iter55 は push 済み。本起票コミットの push のみユーザー確認待ち）

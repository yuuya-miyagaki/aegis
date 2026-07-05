# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: docs/specs/2026-07-05-iter56-m2-feedback-brainstorm-record.md
- 要件: docs/plans/2026-07-05-iter56-dogfood-m2-feedback-backlog.md（M2 実測・根因裏取り済み）

## 問題整理

- 背景: M2 ドッグフードで iter55 修正は全件実効（回帰0）だったが、新種の摩擦6件が露出。
  いずれも「hook 判定の誤検知」「skill と judge の契約矛盾」「install 契約の穴」
  「承認ログの可視性不足」に分類できる。
- 判断が必要な論点:
  1. check-secrets の broad-staging 正規表現の境界設計（何を broad とみなすか）
  2. `.env.test` を safe-list に入れるか（危険側判断）
  3. qa ref の正本を test-strength.md と QA レポートのどちらに統一するか
  4. verdict 相違 🟡 の段階化と notes 可視性の両立
  5. full プロファイルの配布整合をどの層で機械強制するか
- 制約条件: check-secrets は moat（deny 判定）＝挙動変更は deny 緩和方向のみ慎重に。
  judge の claims 読取は narrow YAML subset（依存ゼロ）を維持。
  minimal/standard プロファイルの意図的劣化（scaffold-safe retro.md 変種）は壊さない。

## 推奨アプローチ

- 採用方針: 候補6件＋可視性小玉2件（⑦）を1イテレーション一括・TDD で実装。
- 採用理由: 全件独立・M2 実測摩擦・同一ファイル圏の重なり大（brainstorm-record 参照）。
- 検討した代替案と不採用理由:
  - P1 のみ先行 → ゲート一周2回のコスト増・P2 は数行規模で分割益なし。
  - ②の judge フォールバック読取 → ref 単一原則を壊す・証拠経路の二重化（single-owner 教訓違反）。
  - `.env.test` safe-list 追加 → 中身検査なしで「テスト用だから安全」は成立しない。deny 維持＋文言で回避策案内。

## コンポーネント分解

### ① check-secrets.sh — broad-staging 先頭ドット誤検知の修正（P1・moat）

- **現状**: `hooks/check-secrets.sh:149` の `add[[:space:]]+(-a|--all|\.)` — 末尾 `\.` が
  トークン境界非アンカーで、`.env.example`・`.gitignore` 等の先頭ドットファイル名に前方一致。
- **修正**: broad-dot を「ディレクトリ全体を指すトークン」に限定:
  `(-a|--all|\.\.?/?([[:space:];&|]|$))`
  （境界は空白・行末に加えシェルデリミタ `;` `&` `|` を含める — grill 致命1:
  `git add .&&git commit` のすり抜け＝moat 後退を防ぐ）
  - 正例（broad 維持）: `git add .`／`git add . foo`／`git add ./`／`git add ..`／
    `git add ../`／`git add -A`／`git add --all`／`git add .&&git commit -m x`
  - 負例（broad 扱いしない）: `git add .env.example`／`git add .gitignore`／
    `git add .github/workflows/ci.yml`
  - 注: `.env` 単体は先行の直接 .env 検査（:141）で引き続き deny（本修正の影響外）。
- **付随（設計判断の明文化）**: `.env.test` は safe-list（example/template/sample）対象外の
  **恒久 deny を維持**。直接 .env deny の文言に「テスト用のプレースホルダ env は
  `.env.example` 等の safe variant 名を使う」旨の回避案内を1行追記。
  safe-list 追加をしない理由（中身無検査で安全扱いは危険側）をコードコメントに残す。

### ② qa-verification skill — qa ref を claims 付き QA レポートに統一（P1・契約整合）

- **現状**: skill は通常経路（手順6）も skip 経路も `current_refs.qa` を
  ハーネス生成 `docs/qa-reports/test-strength.md` に指すよう指示。同ファイルには
  claims ブロックを構造的に置けず（drill 再生成で消える）、judge
  （`build-judge-card.py` は ref 先しか claims を読まない）が毎回「claims 未提出」🟡。
  framework repo 自身は罠(p)/(g) で「claims 付き qa レポートを ref にする」運用を確立済み＝
  配布 skill と自家運用が矛盾。
- **修正**: skill の両経路を統一 — `current_refs.qa` は **claims 付き QA レポート**
  （`docs/qa-reports/iterN-qa.md` 等・QA-REPORT テンプレ準拠）を指す。
  `test-strength.md` は固定パスのハーネス証拠として存続（judge の `b1_verdict` は
  ref 非依存の固定パス読取 `collect_facts` — 裏取り済みのため挙動不変）。
  「さもないと完了時に証拠不足で弾かれる」の誤記述を実態（ref が実在ファイルを
  指せば受理）に修正。
- **テスト**: qa ref=QA レポートで (a) judge が claims を読み 🟡 が出ない
  (b) TaskCompleted / contract の evidence 検査が受理 — の2点を回帰固定。

### ③ build-judge-card.py — verdict 名目差の段階化＋notes 可視性（P2）

- **現状**: `compute_verdict`（:382-385）が verdict 文字列の単純不一致で
  「1次/2次相違」🟡 → approve vs approve_with_notes の名目差で3ゲート連続 ack＝形骸化。
- **修正**: 相違 🟡 の抑止条件を「両者とも ok class」に限定:
  - ok class = {approve, approve_with_notes}。**両者が ok class なら名目差でも 🟡 を出さない。**
  - それ以外の不一致（reject・blocked・未知値が片側にでも絡む）→ 従来どおり 🟡。
  - 未知 verdict 値は ok class に含めない（fail-visible: 想定外文字列を沈黙で ok 扱いしない）。
- **値不正の可視化（grill 致命2）**: 既知集合 {approve, approve_with_notes, reject,
  blocked} 外の verdict 値（テンプレ未記入プレースホルダ含む）は、両側同値でも
  「verdict 値が不正/未記入」🟡 を出す — 未記入テンプレの沈黙通過を許さない。
- **notes 可視性（形骸化対策とセット）**: いずれかの verdict が approve_with_notes のとき、
  カードに**非ブロッキング情報行**（overall に不算入）を出す:
  `second_opinion.notes`（正位置のみ・トップレベル fallback は YAGNI で不採用）が
  あれば要旨を、なければ「approve_with_notes — notes の解消状況を確認」を表示。
- **触らない現挙動（明文化）**: claims=None × second_opinion あり時に何も出ないのは
  pre-existing の仕様（claims 未提出 🟡 が別途出る）— iter56 では変更しない。
- **テスト**: approve×approve_with_notes → 🟡 なし＋情報行あり／approve×reject → 🟡 維持／
  未知値×approve → 🟡 維持。

### ④ subagent-dev skill — 並列規則に共有可変資源の項を追記（P2・docs のみ）

- **現状**: 並列実行ルール（SKILL.md:135-139）は「同一ファイル変更の禁止」のみで
  共有可変資源を無想定 → M2 で並行 integration テストが同一テスト DB を TRUNCATE
  し合い偽 fail（vitest `fileParallelism:false` はプロセス内のみ有効）。
- **修正**: 並列実行ルールに追記 — 共有可変資源（テスト DB・ポート・グローバル状態・
  外部サービスの sandbox）で衝突するタスクの並列起動を禁止。
  標準運用=**integration 実行タスクは wave あたり1体**（unit のみのタスクと組む）。
  代替=per-agent の DB/スキーマ分離を注記。実装変更なし。

### ⑤ spec-delta 合格時の1行肯定出力（P2・可視性）

- **現状**: `check_status.py::_spec_delta_issues`（:150）は合格時に空リストを返すのみ＝
  client_ready_for_dev 承認ログから「検査が走って合格」と「対象外」を区別できない。
- **修正**: required（iteration>1）かつ合格時のみ
  `[spec-delta] CHANGES.md 検査 OK（iteration=N）` を承認フロー出力に1行出す。
  対象外（iteration≤1）は現状どおり無言。実装位置（check_status.py の gate 検査
  出力 vs update-gate.sh）は plan で確定するが、**判定ロジックは動かさず出力のみ追加**が原則。

### ⑥ full プロファイル配布整合（P1・install 契約）

- **現状**: `templates/profiles/full.json` の配布 scripts は8本。
  `hooks/lib/scripts-manifest.tsv` の実行可クラス（allow|ask）は12本。
  未配布4本= retro_report.py・check_reference_drift.py・learnings_search.py・lint_names.py。
  full の自己記述（"all files including … scripts"）と矛盾し、M2 で /retro が
  手動フォールバック化。iter55 の install テストは「hook が allow する」のみ検証し
  「ファイルが実在する」を未検証。
- **修正**（3層）:
  1. full.json recommended に未配布4本を追加。
  2. contract（check_framework_contract.py の scripts-manifest 検査）に**方向4**を追加:
     manifest の実行可クラス（allow|ask）⊆ full プロファイル配布 scripts
     （framework-only / import-only は対象外）。
  3. install テストを「full install 先での実在検証」に拡張（iter55 の穴＝F6 教訓の再発防止）。
- **非対象**: minimal/standard は現状維持（scaffold-safe retro.md 変種の意図的劣化は
  full 以外でそのまま有効）。

### ⑦ 可視性の小玉2件（P3・候補外から同梱・descope 可）

- judge「テスト結果が未検証」🟡 文言に是正手順1行を追記:
  「record-test-result.py で再記録（例: `python3 scripts/record-test-result.py "python3 -m pytest -q"`・
  positional command 引数）」。
- gate レポートテンプレ（QA-REPORT / REVIEW / SECURITY-REVIEW）に ```claims 雛形を追加。
  **プレースホルダは `<記入>` 形式**（`approve` プリフィルは未記入レポートの自己承認化＝
  禁止・grill 致命2）。`tests_green` は judge 非消費キーのため雛形に入れない（YAGNI）。
  未記入は③の値不正 🟡 で必ず可視化される。
- 根拠: いずれも M2 実測の可視性摩擦・②③と同一ファイル圏・数行。

## インターフェース定義

- 変更する公開面（配布物・運用契約）:
  - check-secrets の deny 対象（緩和方向のみ: 先頭ドットファイル名の個別 add を解放）
  - qa-verification / subagent-dev SKILL.md の指示文（配布 skill）
  - full プロファイルの配布ファイル集合（増加のみ）
  - judge カードの 🟡 発火条件（縮小）＋情報行（追加）
- 変えないもの: claims ブロックの書式・GATE_REF_KEY・B1 drill の判定・
  minimal/standard プロファイル・update-gate.sh の ask クラス（人間トリップワイヤ）。

## データフロー / 構造

- ①: Bash コマンド文字列 → check-secrets（PreToolUse）→ broad 判定 regex（本修正）→ deny/allow
- ②⑦: qa レポート（claims 付き・ref）→ build-judge-card read_claims → compute_verdict
- ③: claims.verdict × second_opinion.verdict → severity class 比較 → 🟡/情報行
- ⑤: update-gate.sh approve → check_status gate 検査 → spec-delta OK 1行（stdout）
- ⑥: scripts-manifest.tsv（single owner）→ contract 方向4 → full.json との包含検査

## エラー処理

- ①: 判定不能・想定外形は従来どおり（既存 fail-closed 方針を変えない）。緩和は
  「明確に個別ファイルと判別できるトークン」のみ。
- ③: 未知 verdict 文字列は bad class（fail-visible）。
- ⑤: 出力追加のみ・判定不変（出力失敗が承認を壊さない位置に置く）。
- ⑥: contract 方向4 は既存 drift 検査と同じ FAIL 経路（沈黙させない）。

## テスト戦略

- TDD（RED→GREEN）: ①③⑤⑥は判定/出力の単体テストを先に赤で書く。
- ②は契約テスト（judge claims 読取＋TaskCompleted 受理）で固定。
- ④⑦の docs/テンプレ変更は check_reference_drift / contract 検査の green 維持で担保。
- 回帰: full suite（前回 1285 passed）green・contract/status/drift PASS を完了条件に含める。

## 依存関係

- 新規外部依存なし。既存の pure-bash / stdlib Python 制約を維持。

## 実装順序

- P1: ① → ⑥ → ②（moat バグ・install 契約・judge 契約の順）
- P2: ③ → ⑤ → ④
- P3: ⑦（②③の実装と同時に同一ファイルを触る）

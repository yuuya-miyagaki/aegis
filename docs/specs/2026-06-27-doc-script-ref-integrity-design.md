# 設計ノート
<!-- 正本: brainstorming skill -->

## 入力

- ブレインストーミング記録: `docs/specs/2026-06-27-doc-script-ref-integrity-brainstorm-record.md`
- 要件: なし（内部 framework iteration・requirements は []）

## 問題整理

- 背景: 配布 self-containment の参照整合性検査は iter48（profile script→script）＋ iter49（skill→script）で2面を固めた。残る install surface の doc（`CLAUDE.md` / `.claude/rules/*.md`）→ `scripts/*` 参照は未検査。
- 判断が必要な論点: doc の **install 実体**をどう解決して読むか（CLAUDE.md は `templates/CLAUDE.template.md` へ remap、rules は verbatim）。dogfood の repo-root CLAUDE.md を読むと install されない参照を誤検出する。
- 制約条件: 本検査は **guard-only**（grill-premise で実穴ゼロを実証）。honest framing 厳守。本ファイルの static/fast な性格を保つ。fail-closed（沈黙劣化を作らない）。

## 推奨アプローチ

- 採用方針: 明示 resolver（`_DOC_TEMPLATE_REMAP` ＋ `_doc_install_source`）＋ setup.sh と同期を強制するアンカーテスト。検査本体は明示 map を使い parse 結果に依存しない二層。
- 採用理由: install 実体に忠実（iter49 conf8）＋ static/fast 維持＋ drift を明示 fail で捕捉＋明示 map で fail-closed。
- 検討した代替案と不採用理由: (B) setup.sh 動的パース＝脆性＋parse 失敗で false-clean（fail-open）。(C) install e2e＝guard 1 件に重く本ファイルの性格を割る。

## コンポーネント分解

- 分割方針: 既存 iter48/49 セクションの末尾に iter50 セクションを追加。純関数・helper を最大限再利用（`_violations`・`_SKILL_SCRIPT_RE`・`_shipped_scripts_any`）。
- 各ユニットの責務:
  - `_DOC_TEMPLATE_REMAP: dict[str,str]`: doc rel-path → template rel-path（現状 `{"CLAUDE.md": "templates/CLAUDE.template.md"}`）。
  - `_doc_install_source(rel) -> Path`: map ヒットで template、無ければ verbatim(`ROOT/rel`)。
  - doc edge 抽出: 既存 `_skill_script_edges`（共有 `_SKILL_SCRIPT_RE`）を**再利用**（新関数を起こさない・grill-plan YAGNI）。
  - `_shipped_doc_surfaces(profile) -> list[str]`: profile entry が `CLAUDE.md` ∨ `.claude/rules/*.md` のものを返す。
  - `INTENTIONAL_UNSHIPPED_DOC: dict[str,dict[str,str]]`: 理由付き allow-list（3 profile × `check_framework_contract.py`）。
  - アンカー: setup.sh:resolve_source の case 行を抽出し resolver と一致を assert。

## インターフェース定義

- `_doc_install_source(rel: str) -> pathlib.Path`: 入力 doc rel-path、出力 install 実体の絶対 Path。
- doc edge 抽出: 既存 `_skill_script_edges(text: str) -> set[str]` を再利用（doc 本文 → `scripts/<name>.(py|sh)` 集合）。
- `_shipped_doc_surfaces(profile: dict) -> list[str]`: 入力 profile JSON、出力 install-surface doc の rel-path リスト。
- 再利用: `_violations(shipped, edges, allowlist) -> list[str]`（負け＝違反 dep）。

## データフロー / 構造

- 入力: `templates/profiles/*.json`（各 profile）。
- 処理: profile ごとに `_shipped_doc_surfaces` → 各 doc を `_doc_install_source` で解決し読込 → `_doc_script_edges` で参照辺抽出 → `_shipped_scripts_any` ∪ `INTENTIONAL_UNSHIPPED_DOC` で `_violations` 判定。
- 出力: 違反リストが空であることを assert（本体テスト）。

## 依存関係

- 依存方向: iter50 helper → 既存 iter48/49 helper（`_violations` 等）。循環なし。
- 外部依存: なし（標準ライブラリ ast/re/json/pathlib のみ・既存と同じ）。

## エラーハンドリング

- 想定失敗: (1) setup.sh の case 構文変更で resolver が drift → **アンカーテストが明示 fail**。(2) template/doc ファイル不在 → read 例外で**沈黙しない**。(3) regex 過検出（散文中の `scripts/x.py`）→ fail-closed＝allow-list で理由付き解消。
- 対応: 明示 map により検査本体は parse 非依存（fail-closed）。allow-list は reason 非空必須＋rot 検知（stale/redundant）。
- エラー伝播の方針: 検査は test として fail（assert）で伝播。allow-list の劣化も独立テストで fail。

## テスト戦略

- 単体: `_doc_install_source`（CLAUDE.md→template／rules→verbatim）・`_doc_script_edges`（抽出する／散文無視）・`_shipped_doc_surfaces`（CLAUDE.md+rules 選別・commands/agents 除外）。
- 結合: `test_every_profile_doc_script_ref_is_self_contained()`（本体）。アンカーテスト（resolver ↔ setup.sh 一致）。
- エッジケース: negative-control（合成 doc に未同梱・非 allow 参照を注入し検出）／allow-list rot（stale=未参照／redundant=同梱済みを禁止）／reason 非空。
- 手動確認: qa の B1 mutation drill で install 実体 doc にダミー参照を注入し検出を実証（guard の歯の独立証明）。

## 次のステップ

- [ ] 実装計画を作成する → `docs/plans/2026-06-27-doc-script-ref-integrity-implementation-plan.md`
- テンプレート名: `PLAN.template.md`
- 本設計ノートのパスを PLAN の「参照設計」に記載すること

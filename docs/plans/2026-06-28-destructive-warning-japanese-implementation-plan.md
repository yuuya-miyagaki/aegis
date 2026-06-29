# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- 破壊的コマンドの permission prompt（ask）reason を英語から平易な日本語へ統一し、日本語話者の知識の乏しい運用者が「何が起きるか・元に戻せるか」を判断できるようにする。将来の英語混入をドリフトガードで防ぐ。判定ロジック無改変＝moat 不変。

## 入力

- 参照要件: なし（internal framework iteration）
- 参照設計: `docs/specs/2026-06-28-destructive-warning-japanese-design.md`

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（内部 framework イテレーション・デプロイ対象なし）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ無し）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

- prior iteration 慣行に従い main へ直接 feat commit。実装中はコミットしない（qa B1 drill が未コミット diff を要するため・罠f）。設計ドキュメント・コード・STATUS をまとめて ship 時に1コミット。push は `gh auth switch --user yuuya-miyagaki`。

## ファイル構造（変更マップ）

- 変更: `hooks/lib/patterns.sh:15-18,40-57` — `AEGIS_DESTRUCTIVE_LOWER_WARN`(2)＋`AEGIS_DESTRUCTIVE_CMD_WARN`(16) の文字列を日本語化。regex 配列（:14,22-39）は無改変。
- 変更: `hooks/check-destructive.sh:88` — inline `WARN="Destructive: recursive delete..."` を日本語化。`:50` の抽出失敗フォールバックを日本語化。
- 変更: `hooks/check-secrets.sh:51` — 抽出失敗フォールバックを日本語化。
- 新規: `tests/test_destructive_warning_language.py` — ドリフトガード（配列）＋inline 発火＋フォールバック behavioral 発火（truncated payload）。

### 実装注意（grill-plan 反映）

- **並列配列の保持**: `*_REGEX` と `*_WARN` はインデックス対応。翻訳時は要素数・順序を厳守（取り違えると警告文と判定がズレ、誤警告＝moat 不変違反）。
- **UTF-8 デコード**: テストは既存テストに倣い `env={"PATH":"/usr/bin:/bin"}` で起動するため LANG が無い。subprocess 出力は `encoding="utf-8"`（または bytes 受け→`.decode("utf-8")`）で読む。`text=True` 既定は ASCII デコードで日本語バイトが落ちる環境がある。
- **層1 の前提**: `printf "%s\n" "${ARR[@]}"` は WARN 単一行前提。複数行 WARN は導入しない。
- **JP 判定ヘルパー**: `any('぀'<=c<='ゟ' or '゠'<=c<='ヿ' or '一'<=c<='鿿' for c in s)`。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | 日本語化 WARN 配列（patterns.sh）＋配列ドリフトガード test | なし |
| Task 2 | 日本語化 inline rm -r WARN＋発火 test | patterns.sh（unchanged path） |
| Task 3 | 日本語化フォールバック2件＋behavioral 発火 test（truncated payload） | なし |

循環なし。各 Consumes は既存 Produces に充足。

## タスク分解

> 各タスク TDD RED-first。実装中コミット禁止（罠f）。

### タスク 1: WARN 配列の日本語化＋ドリフトガード

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 対象 `hooks/lib/patterns.sh` / テスト `tests/test_destructive_warning_language.py`
**意図:** 18 件の破壊的 WARN 配列を format A で日本語化し、各要素に日本語文字必須のガードを敷く。
**TDD:**
1. test 作成: `bash -c 'source hooks/lib/patterns.sh; printf "%s\n" "${AEGIS_DESTRUCTIVE_LOWER_WARN[@]}"'`（CMD_WARN も）で配列を読み出し、各要素が日本語文字（U+3040-309F／U+30A0-30FF／U+4E00-9FFF）を1つ以上含むと assert。→ 現状英語で **FAIL 確認**。
2. patterns.sh の 18 文字列を設計ノートの訳に置換（regex 無改変）。→ **PASS 確認**。
**受入条件:** 配列ガード GREEN。regex 配列の diff ゼロ。
**Deliverable:** [ ] 18 文字列が日本語 [ ] ガード test がカバー

### タスク 2: inline rm -r WARN の日本語化＋発火テスト

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 対象 `hooks/check-destructive.sh` / テスト `tests/test_destructive_warning_language.py`
**意図:** 再帰削除の inline WARN を日本語化し、実発火で reason に日本語が出ることを固定。
**TDD:**
1. test 作成: 非安全ターゲット `rm -rf /important`（`foo/` は safe-build-artifact 判定に飲まれる恐れ＝既存 test 同様 `/important` 使用）を `payload=json.dumps({"tool_name":"Bash","tool_input":{"command":cmd}})` で `subprocess.run(["bash", HOOK], input=payload, env={"PATH":"/usr/bin:/bin"}, encoding="utf-8")` に流し、出力 JSON の `permissionDecision":"ask"` かつ `permissionDecisionReason` が日本語文字を含むと assert。→ 現状英語で **FAIL 確認**。
2. check-destructive.sh:88 の inline WARN を `破壊的: 再帰削除 (rm -r/-R)。ファイルを完全に削除します（復元できません）。` に置換。→ **PASS 確認**。
**受入条件:** 発火 test GREEN。build-artifact 再帰削除（safe-targets）は引き続き allow（既存 test_destructive_recursive.py green で担保）。
**Deliverable:** [ ] inline WARN 日本語 [ ] 発火 test がカバー

### タスク 3: 抽出失敗フォールバック2件の日本語化＋behavioral 発火テスト

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 対象 `hooks/check-destructive.sh` `hooks/check-secrets.sh` / テスト `tests/test_destructive_warning_language.py`
**意図:** 抽出失敗（truncated JSON）パスの英語フォールバックを日本語化し、**実発火**で reason が日本語になることを固定（source 行マッチは翻訳でアンカーが消える自己破壊的設計のため不採用＝grill-plan 致命1）。
**TDD:**
1. test 作成（destructive）: truncated payload `{"tool_name":"Bash","tool_input":{"command":"rm -Rf /important`（既存 `test_truncated_capital_r_fallback_asks` と同形）を `run_raw` 相当（utf-8 デコード）で流し、`ask` かつ reason に日本語文字 assert。
2. test 作成（secrets）: truncated payload `{"tool_name":"Bash","tool_input":{"command":"cat .env`（抽出失敗＋raw が `.env` を `$` で一致・`.env.example` 不含）を check-secrets.sh に流し、`ask` かつ reason に日本語文字 assert。→ 両者 現状英語で **FAIL 確認**。
3. check-destructive.sh:50・check-secrets.sh:51 の英語フォールバックを設計ノートの訳に置換。→ **PASS 確認**。
**受入条件:** 両 behavioral 発火 test GREEN。`[careful]` タグは据置。
**Deliverable:** [ ] フォールバック2件 日本語 [ ] behavioral 発火 test がカバー

## 事前準備

- [x] 追加の環境・API キー不要（bash＋python3 標準のみ）
- [x] 依存パッケージ不要
- [ ] ベースブランチ最新（main・origin/main=46125e4 同期済）

## トレーサビリティ（設計セクション → Task → Test）

| 設計セクション | Task | テストファイル |
|------|------|--------------|
| WARN 配列18件日本語化＋ガード | Task 1 | `tests/test_destructive_warning_language.py` |
| inline rm -r 日本語化 | Task 2 | 同上 |
| フォールバック2件日本語化 | Task 3 | 同上 |

## 自己レビュー

- 仕様カバレッジ: 設計の全対象文字列（18＋1＋2）が Task でカバー。
- 曖昧さ: 訳文は設計ノートで確定済。
- 型整合: 配列名・ファイルパスは実コードと一致確認済。
- 境界整合: Boundary Map に循環なし。

## リスク

- リスク: ドリフトガードの JP 判定が誤検知（コマンドトークンのみで JP 不在の正当な WARN）。
- 対策: 全 WARN は日本語説明を含む方針（format A）＝JP 必須は要件と一致。誤検知は設計上発生しない。
- リスク: 並列配列 `*_REGEX`↔`*_WARN` の順序取り違えで警告と判定がズレる。
- 対策: 翻訳は文字列値のみ置換し要素順・件数を保持。既存 destructive テスト green が対応関係を担保。
- リスク: subprocess 出力の日本語が ASCII デコードで落ちる（LANG 無し環境）。
- 対策: `encoding="utf-8"` 明示。

## 完了条件

- [ ] 全テスト pass（新規 test file＋full suite）
- [ ] regex/判定ロジック diff ゼロ（moat 不変）
- [ ] **既存 destructive/secrets テスト green**（ask/allow 決定不変＝moat 不変の behavioral 証拠）
- [ ] 全テストを WARN 部分文字列で grep し、英語本文を pin する既存 assertion が無いことを確認（無更新前提の担保）
- [ ] review+qa（B1 drill）+security 承認（M・deploy size-exempt）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

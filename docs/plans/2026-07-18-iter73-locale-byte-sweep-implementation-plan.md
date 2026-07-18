# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- この変更で達成すること: deny 側 moat フック `check-destructive.sh`・`check-secrets.sh` が
  不正 UTF-8 バイトを含む stdin を処理する際に、`tr` の `Illegal byte sequence` クラッシュ
  （`set -euo pipefail` で rc=1・出力なし→自前 fail-safe fallback 迂回）を起こさず、
  従来どおり ask/deny 判定を emit するようにする。修正は各フックの抽出直後に
  `export LC_ALL=C LC_CTYPE=C LANG=C` を 1 行追加し、以降の tr/grep/sed を byte-wise 決定化する。
  GNU grep（Linux）での iter72 同型 grep poison も同時に封鎖する。判定ロジックは無改修。
- **位置づけ（grill 指摘1/3・実証済み 2026-07-19）**: これは **defensive robustness hardening** で
  あって reachable fail-open ではない。crash は不正バイトでのみ発生し、モデルが emit する command は
  常に valid UTF-8＝**脅威モデル内で到達不能**（設計「到達性」節）。それでも直すのは (1) 制御フックは
  任意 stdin でクラッシュしない堅牢性契約、(2) iter72 marker.sh 一貫性、(3) stderr ノイズ除去、
  (4) forward-looking（非モデル呼出し/将来変更）。crash は policy 表の「parse-fail→allow」でも
  「lib欠落→deny」でもない**第3の未定義状態（parse 成功後の下流クラッシュ）**で、fix はこの状態を消す。
- **⚠実装で判明した配置修正（2026-07-19・下記 Task 2/3 の「抽出直後」は誤り）**: `extract_command` の
  grep/sed fast-path 自体が UTF-8 下で不正バイトのコマンドを空にドロップする（実測 UTF-8→LEN=0／C→22）
  ため、export は**抽出直後ではなく抽出前（`INPUT=$(cat)` 直後）**に置く。C locale が python3 抽出を
  壊さないことは PEP 540 UTF-8 Mode で担保（valid 多バイト抽出 byte 一致を実測）。設計正本の「推奨
  アプローチ」注記が確定版。両フックとも抽出前配置に統一済み（commit 7bfb8f7・95e08ae）。

## 入力

- 参照要件: なし（framework 内部 hardening・requirements gate は N/A 継続）
- 参照設計: `docs/specs/2026-07-18-iter73-locale-byte-sweep-design.md`
- 記録: `docs/specs/2026-07-18-iter73-locale-byte-sweep-brainstorm-record.md`
- 動機正本: SF-014 内 F-CRIT-1（`docs/security-followups.md`・commit 90b4b61＝iter72 marker.sh 同型）

## Deploy Target（必須 — 空欄のままでは plan 承認不可）

### プラットフォーム

- Hosting: **n/a**（Claude Code ローカルフレームワーク＝配布物はフック shell スクリプト。デプロイ先なし）
- Database: n/a
- CI/CD: n/a（ローカル pytest／`scripts/check_framework_contract.py`）

### 互換性確認

- next.config `output` 設定: n/a（Node/Next アプリではない）
- 上記がデプロイ先と互換であることを確認: **Yes**（n/a＝shell フック変更のみ・`LC_ALL=C` は POSIX 標準で macOS/Linux/WSL 全対応）

### 認証方式

- 認証プロバイダ: None（フレームワーク内部・認証面なし）
- DEMO_MODE 予定: n/a

## Git 戦略

- 未定義のため既定＝main 直コミット（従来イテレーション踏襲・per-task commit）。push はユーザー判断。

## ファイル構造（変更マップ）

- 変更: `hooks/check-destructive.sh` — `CMD=$(extract_command "$INPUT")` の直後（`if [ -z "$CMD" ]`
  fallback ブロックより前）に `export LC_ALL=C LC_CTYPE=C LANG=C` を rationale コメント付きで挿入。
  判定分岐・パターンは無改修。
- 変更: `hooks/check-secrets.sh` — 同じく `CMD=$(extract_command "$INPUT")` の直後に同 1 行を挿入。
  Check 0-3 の全 grep・`git diff | tr | grep`・`find|basename|tr`・raw fallback の tr が byte-wise 化。
- テスト: `tests/test_hook_locale_byte.py`（新規） — 両フックの locale/byte 回帰 pin。
  (a) 不正バイト混入コマンドで crash せず判定 emit、(b) byte 下でも moat 維持（ask/deny）、
  (c) valid 多バイト（日本語）非退行、(d) UTF-8 locale 明示発火。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `tests/test_hook_locale_byte.py`（RED） | 既存フック（現状 crash を再現） |
| Task 2 | `hooks/check-destructive.sh`（LC_ALL export） | Task 1 のテスト |
| Task 3 | `hooks/check-secrets.sh`（LC_ALL export） | Task 1 のテスト |

循環依存なし。Task 1 が両フックの目標挙動を先に固定（RED）、Task 2/3 が GREEN 化。

## タスク分解

> 各タスクは 2-5 分単位。TDD RED-first。実装（コードを書く）は `opus` へ dispatch。

### タスク 1: locale/byte 回帰テスト（RED）

**blockedBy:** なし | **モデル:** `opus`
**ファイル:** テスト `tests/test_hook_locale_byte.py`（新規）
**意図:** 両フックの目標挙動を pin。現状コードでは不正バイトで crash（rc≠0・空 stdout）するため
RED になることを確認する。iter72 の byte pin（`tests/test_marker_lib.py::test_stray_byte_*`）の
UTF-8 locale 明示発火パターンを踏襲。
**テスト内容（最低ケース）:**
- `_run(hook, command_bytes, env=UTF-8)` ヘルパー（payload を latin-1 で bytes 化して stdin 投入・
  stdout の permissionDecision を取得・rc も検査）。
- **destructive crash 回帰**: `rm -rf /realdir #<0xFF>` / `rm -rf /realdir<0xFF>` → 期待 `ask`＋rc=0
  （現状: tr crash で rc=1・空→RED）。
- **destructive i18n 非退行**: `rm -rf ~/プロジェクト` → `ask`。
- **destructive 正常 ASCII 非退行**: `rm -rf /realdir` → `ask`、`echo hello` → allow(`{}`)。
- **secrets crash 回帰（主 pin＝実シークレット保護・grill 指摘2）**: `git add .env realfile<0xFF>`
  （＝**実 `.env` を stage しつつ末尾にバイト**）→ 期待 `deny`＋rc=0（現状: tr crash で rc=1・空→RED）。
  「実シークレット staging がバイト混入下でも deny 維持」を pin する。
- **secrets crash 回帰（補助 pin＝非クラッシュ）**: `git add .env<0xFF>`（`.env\xff` という別名ファイル。
  deny-side で安全）→ 期待 `deny`＋rc=0。crash しないことの補助確認。
- **secrets i18n 非退行**: `git add テスト/.env` → `deny`。
- **secrets 正常 ASCII 非退行**: `git add .env` → `deny`。
**TDD:** テスト作成 → `python3 -m pytest tests/test_hook_locale_byte.py` で crash 系ケースが FAIL
（RED）することを確認 → コミット（RED はコミットに含める＝iter72 流儀の非空 pin）。
**受入条件:** crash 回帰ケースが現状コードで明確に FAIL（rc≠0 or 空 stdout を捕捉）。
**Deliverable:** [ ] テストが存在 [ ] RED を実測記録（rc/stdout）

### タスク 2: check-destructive.sh に byte-wise locale 適用（GREEN）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/check-destructive.sh` / テスト `tests/test_hook_locale_byte.py`
**意図:** `CMD=$(extract_command "$INPUT")` 直後（line 32 付近・`if [ -z "$CMD" ]` より前）に
`export LC_ALL=C LC_CTYPE=C LANG=C` を挿入。rationale コメントに「抽出の python3 は inherited
locale で UTF-8 fidelity 維持／以降 tr/grep は ASCII+literal パターンゆえ byte-wise が正／本フックは
抽出後 python3 非依存」を明記（iter72 marker.sh コメントと整合）。
**TDD:** Task 1 の destructive 系ケースが GREEN 化するのを確認 → 既存
`tests/test_check_destructive_coverage.py`・`test_destructive_*.py` 全 pass → コミット。
**受入条件:** destructive の全 pin（新旧）green・byte 混入 `rm -rf` が `ask`・rc=0。
**Deliverable:** [ ] export 挿入 [ ] destructive テスト全 green

### タスク 3: check-secrets.sh に byte-wise locale 適用（GREEN）

**blockedBy:** Task 1 | **モデル:** `opus`
**ファイル:** 対象 `hooks/check-secrets.sh` / テスト `tests/test_hook_locale_byte.py`
**意図:** `CMD=$(extract_command "$INPUT")`（line 43 付近）直後・`if [ -z "$CMD" ]` fallback より前に
同 1 行を挿入。rationale コメント同上（本フックも抽出後 python3 非依存を明記）。
**TDD:** Task 1 の secrets 系ケースが GREEN 化 → 既存 `tests/test_secrets_*.py`・
`test_check_secrets_git_dir.py` 全 pass → コミット。
**受入条件:** secrets の全 pin（新旧）green・byte 混入の実シークレット staging が `deny`・rc=0。
**Deliverable:** [ ] export 挿入 [ ] secrets テスト全 green

## 事前準備

- [x] ベースブランチ最新（main・HEAD=b0eb8a1）
- [x] pytest 実行可能（既存 suite 通過を前提）
- [ ] **Task 1 着手前に full suite baseline を 1 回取得**（`python3 -m pytest -q tests/ | tail`）し
  passed 数を記録 → Task 3 完了後に再取得し**新規 pin 増分以外は差分ゼロ**を確認（grill 要検討3）。

## トレーサビリティ（設計論点 → Task → Test）

| 設計論点 | Task | テストファイル |
|------|------|--------------|
| tr crash → fail-open 封鎖（destructive） | Task 1,2 | `tests/test_hook_locale_byte.py` |
| tr crash → fail-open 封鎖（secrets） | Task 1,3 | `tests/test_hook_locale_byte.py` |
| i18n（valid 多バイト）非退行 | Task 1,2,3 | `tests/test_hook_locale_byte.py` |
| 正常 ASCII 判定非退行 | Task 2,3 | 既存 `test_check_destructive_coverage.py`・`test_secrets_*.py` |
| 抽出後 python3 非依存の不変 | Task 2,3 | 設計コメント＋（可能なら）静的 grep pin |

## 自己レビュー

- 仕様カバレッジ: 設計の全論点（crash 封鎖・i18n・正常路・不変条件）に Task/Test 対応あり。
- 曖昧さ: 「抽出直後」＝`CMD=$(extract_command)` の次行・`if [ -z "$CMD" ]` より前、と明記済み。
- 整合性: export の位置は両フックで同一意味論（extract は inherited、以降 byte-wise）。
- 境界: Task 1 の Produces（テスト）を Task 2/3 が Consumes。循環なし。

## リスク

- リスク R1: `export LC_ALL=C` が下流の python3 呼び出しを C locale 化し、valid UTF-8 を mis-decode。
  - 対策: 両フックとも抽出後 python3 非依存を実測確認済み（design 依存関係節）。i18n pin（valid 多バイト
    deny/ask）で回帰検知。将来 python3 を下流に足す場合の警告を設計コメントに残す。
- リスク R2: `LC_ALL=C` でパターンマッチが変わり正常判定が退行。
  - 対策: 全パターンは ASCII＋literal（iter72 と同根拠）＝byte-wise が正。既存 ASCII pin 全 pass を条件化。
- リスク R3: control-plane 変更が新規バグ源（SF 系の戒め）。
  - 対策: 判定ロジック無改修・additive 1 行・per-task commit・grill-plan/grill-code/review 4角度＋盲検2次。

## 完了条件

- [ ] 全テスト pass（新規 locale/byte pin＋既存 destructive/secrets＋full suite 回帰ゼロ）
- [ ] `python3 scripts/check_framework_contract.py` PASS
- [ ] レビュー完了（1次4角度＋親verify＋盲検2次）
- [ ] byte 混入 `rm -rf`→ask・byte 混入 実シークレット staging→deny を UTF-8 locale で実測
- [ ] `check-runtime-state`/`check-deploy-gate` 非該当（crash せず）を qa で再確認（掃討完全性エビデンス）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → implement へ -->

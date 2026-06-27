# 実装計画
<!-- 正本: subagent-dev skill -->

## 目的

- 安全な読み取り/記録系コマンドの**狭い `permissions.allow`** を**全プロファイル**に同梱し、知識の乏しいユーザーが直面する permission プロンプトの「数」を削減する。状態変更系（`update-gate.sh`／`update-task.sh`）と危険系はプロンプト維持し、moat（deny/ask hooks＋会話ハードゲート＋judge evidence）は不変。
- **dogfood リポ自身の relief（#3 決定済み）**: `.claude/settings.local.json` はグローバル gitignore で除外＝未追跡のローカルファイル。出荷物（template＋setup.sh）はインストール先を救うが、本リポは救わない。よって **ship 時に、本リポの local `.claude/settings.local.json` へ allow set を適用**（既存5エントリと union・**uncommitted**・出荷 diff には入らない）。ユーザー承認済み。

## 入力

- 参照要件: なし（framework iteration・requirements 暫定 []）
- 参照設計: `docs/specs/2026-06-28-permission-prompt-allowlist-design.md`

## 0. マッチャ仕様（検証済み・実装ブロッカー解消 / grill #1）

claude-code-guide で公式仕様を確定（`permissions.md`）:

- `:*` = **単語境界つき prefix マッチ**。`Bash(python3 scripts/status_doctor.py:*)` は `python3 scripts/status_doctor.py --root .` に**マッチする**（python スクリプト系はこの形で OK）。
- **間に挟まる global フラグはマッチを壊す**: `Bash(git log:*)` は `git --no-pager log` に**マッチしない**。→ git は素の `git status/log/diff` 形のみ同梱。`--no-pager` 形は呼び出し側で使わない（稀＝許容）。`git:*` 広域は `push` を含むので不可。
- **pytest は2形必要**: `Bash(python3 -m pytest:*)` ＋ `Bash(pytest:*)`。
- **相対パス必須**: shipped テンプレは install 先で path 不定なので絶対パス不可。framework は project root から起動するので相対で機能する（公式の「絶対推奨」は手書き user rule 向けで、portable default には不適）。
- **複合コマンドはセグメント単位でマッチ**＝`Bash(...:*)` は `cmd && rm -rf x` を auto-approve **しない**（各セグメントに個別ルール必須）。→ matcher 自身が連鎖を弾く＝injection-chaining 懸念が matcher 層でも緩和（moat 二重）。

## Deploy Target（必須）

### プラットフォーム

- Hosting: n/a（内部 framework 変更・配布物はローカル install スクリプト）
- Database: n/a
- CI/CD: n/a

### 互換性確認

- next.config `output` 設定: n/a（Next.js プロジェクトではない）
- 上記がデプロイ先と互換であることを確認: Yes（デプロイ無し・M は deploy size-exempt）

### 認証方式

- 認証プロバイダ: None
- DEMO_MODE 予定: n/a

## Git 戦略

- 未定義のため既定: feature branch ではなく main 直コミット（本リポの dogfood 運用に準拠）＋ 単一 commit。push は `gh auth switch --user yuuya-miyagaki`。

## ファイル構造（変更マップ）

- 変更: `templates/hooks.template.json` — top-level `permissions.allow` ブロックを追加（allow set の**単一正本**）。
- 変更: `bin/setup.sh:generate_settings()`（238-359 付近） — (a) filtered（minimal/standard）分岐でも template の `permissions` を carry、(b) 既存ユーザ settings との merge で `permissions.allow` を **wholesale 置換でなく union**。
- テスト: `tests/test_permission_allowlist_install.py`（新規） — 全プロファイル install e2e／union 保全／allow set 内容／`update-gate.sh` 除外 negative／moat 健在。
- （調整の可能性）`README` の profile 説明 — allow 同梱に触れる必要があれば最小追記（grill-plan で要否判断・no-op なら触らない）。

## Boundary Map

| タスク | Produces | Consumes |
|--------|----------|----------|
| Task 1 | `templates/hooks.template.json` の `permissions.allow`（正本） | なし |
| Task 2 | filtered 分岐の permissions carry | Task 1 |
| Task 3 | merge の allow union | Task 1, Task 2 |
| Task 4 | negative/ moat assertion | Task 1-3 |

循環なし。

## タスク分解

### タスク 1: テンプレに allow set を追加

**blockedBy:** なし | **モデル:** `inherit`
**ファイル:** 対象 `templates/hooks.template.json` / テスト `tests/test_permission_allowlist_install.py`
**意図:** allow set の単一正本を JSON に置く。
**TDD:** テスト「テンプレ JSON に期待 allow エントリが全件あり、`update-gate.sh`／`update-task.sh` は無い」→ FAIL → permissions ブロック追記 → PASS → commit。**追加 proxy テスト（grill #2）**: framework が実際に起動する代表コマンド文字列（例 `python3 scripts/status_doctor.py --root .`・`git status`・`python3 -m pytest -q`）が、いずれかの allow エントリの prefix（`:*` 展開＝単語境界 prefix）として**張られる**ことを assert。JSON 内容検証を「挙動の妥当な代理」にする。
**allow エントリ（狭い・相対パス・§0 で検証済み・grill-code 修正反映）:**
`Bash(python3 scripts/status_doctor.py:*)` / `Bash(python3 scripts/check_framework_contract.py:*)` / `Bash(python3 scripts/check_status.py:*)` / `Bash(python3 scripts/retro_report.py:*)` / `Bash(python3 scripts/build-judge-card.py:*)` / `Bash(python3 -m pytest:*)` / **`Bash(pytest:*)`** / `Bash(git status:*)` / `Bash(git log:*)` / `Bash(git diff:*)`
（git は素の subcommand 形のみ＝`--no-pager` 等の global フラグ形は対象外。pytest は2形。状態変更/危険系は不在。）
**grill-code 修正（🔴/🟡・spec からの reconcile）**: `record-test-result.py`（`:33` で `drill._execute(args.command)` ＝**CLI 引数を実行する exec gadget**）と `run-test-strength-drill.py`（`.drill` 由来コマンドを subprocess 実行）を allow から**除外**。spec の当初リストは record-test-result が引数を実行する事実を見落としていた。readers（status_doctor/check_status/check_framework_contract/retro_report/build-judge-card）は **固定の内部 subprocess のみ**（git/lint/judge）＝arg-exec gadget でないことを確認し維持。pytest は標準テストランナーとして残し residual を security で明記。テストに gadget の negative assert を追加。
**受入条件:** テンプレに上記が存在し、状態変更/危険系は不在。代表起動文字列が prefix マッチする。
**Deliverable:** [ ] 正本が存在 [ ] テストがカバー

### タスク 2: filtered 分岐で permissions を carry

**blockedBy:** Task 1 | **モデル:** `inherit`
**ファイル:** 対象 `bin/setup.sh:generate_settings()` / テスト 同上
**意図:** minimal/standard でも allow が落ちないようにする（現状 `filtered = {'hooks': {...}}`）。
**TDD:** テスト「`bin/setup.sh` を minimal と standard で temp dir に install → 生成 `settings.local.json` の `permissions.allow` に allow set 全件」→ FAIL（現状落ちる）→ filtered に `permissions` を carry → PASS → commit。
**受入条件:** minimal/standard/full すべてで allow set 全件。
**Deliverable:** [ ] 動作 [ ] テストがカバー

### タスク 3: merge で allow を union

**blockedBy:** Task 1, 2 | **モデル:** `inherit`
**ファイル:** 対象 `bin/setup.sh:generate_settings()`（merge 部 340-343）/ テスト 同上
**意図:** 再 install で既存ユーザ allow を保持しつつフレームワーク既定を再付与（現状 `out[k]=v` で wholesale 置換＝clobber）。
**所有権セマンティクス（grill #4 決定）:** フレームワーク allow は **authoritative**＝再 install で**常に再付与**（hooks と同じ扱い）。ユーザー**追加**の allow は保持。ユーザーがフレームワーク既定を意図的に消しても再付与される — **opt-out したい場合は `permissions.ask`/`deny` に置く**（settings rule は hook/allow を上書きする＝§0 で確認済み）。union は重複排除・順序安定・冪等。
**TDD:** テスト「事前に `settings.local.json` へユーザ独自 allow（例 `Bash(npm test:*)`）＋ユーザ `deny` を置く → install → 出力に**ユーザ allow とフレームワーク allow の双方**が在り重複なし、ユーザの `deny`/`env` 保持。再々 install で増殖しない（冪等）」→ FAIL → permissions.allow を union に修正 → PASS → commit。
**受入条件:** union 成立・ユーザの非 allow permissions（deny/ask/env）保持・冪等。
**Deliverable:** [ ] 動作 [ ] テストがカバー

### タスク 4: negative ＋ moat 健在 assertion

**blockedBy:** Task 1-3 | **モデル:** `inherit`
**ファイル:** テスト 同上
**意図:** moat が緩んでいないことを実証。
**TDD:** テスト「(i) allow set に `update-gate.sh`／`update-task.sh`／`rm`／`git push`／destructive が**含まれない** (ii) install 後も hooks ブロック（check-destructive 等）が無改変＝期待 hook が登録済み」→ 実装で満たす。
**受入条件:** negative assert green・hooks 不変。
**Deliverable:** [ ] テストがカバー

## 事前準備

- [x] 外部サービス不要
- [x] 依存パッケージ（python3）導入済み
- [x] ベースブランチ main 最新（origin/main 同期・clean）

## トレーサビリティ（設計 → Task → Test）

| 設計セクション | Task | テストファイル |
|------|------|--------------|
| allow set（正本） | Task 1 | `tests/test_permission_allowlist_install.py` |
| filtered で permissions carry（B1） | Task 2 | 同上（minimal/standard e2e） |
| merge で union（B2） | Task 3 | 同上（再 install union） |
| moat 保全・除外 | Task 4 | 同上（negative/hook 不変） |

## 自己レビュー

- 仕様カバレッジ: 設計の全要素（allow set／B1 carry／B2 union／moat）に Task あり。
- 曖昧さ: allow エントリの**実起動形との一致**（`git --no-pager log`、`python3` のパス差）は要検証 → リスク参照。
- 型整合: Task 間で「allow set 正本（Task1）」を 2/3/4 が参照、名前一致。
- 境界整合: Consumes は全て先行 Produces に対応。

## リスク

- リスク1（**解決済み・§0**）: allow エントリと実起動形の不一致。→ マッチャ仕様を公式確定し、git=素 subcommand 形・pytest=2形・相対パス・proxy テストで突合に決定。残課題は `git --no-pager` 形が prompt する点のみ（稀・呼び出し側で回避）。
- リスク2: union ロジックを bash heredoc 内に置くと**純関数テストが困難**。
  - 対策: 一次は install e2e（precedent: test_profile_checker_parity.py）。grill-plan が edge ケースの細粒度検査を要求すれば union を小 helper に抽出（install-set 影響＝setup.sh 専用で配布対象外を確認）。
- リスク3: full 分岐は `out = dict(template)` でテンプレ全体を取り込むため、将来テンプレに allow 以外の permissions（deny/ask）が増えると full のみ挙動が割れる。
  - 対策: 本スライスは `permissions.allow` のみ。テンプレに deny/ask を置かない（コメントで明示）。

## 完了条件

- [ ] 全テスト pass（新規テスト＋full suite green）
- [x] grill-plan の全指摘を解消（#1 §0／#2 proxy テスト／#3 dogfood local 適用／#4 union 所有権）
- [ ] review / qa / security ゲート通過（deploy は M で size-exempt）
- [ ] ship 時: 本リポ local `.claude/settings.local.json` へ allow set を union 適用（uncommitted・#3）
- [ ] LEARNINGS 追記（confidence 付き）

<!-- exit-check: 全タスク分解・トレーサビリティ充足 → grill-plan → implement へ -->

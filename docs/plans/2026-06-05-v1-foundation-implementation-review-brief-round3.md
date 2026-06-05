# Aegis Foundation — Implementation Review Brief (Round 3 / 実装レビュー)

> **位置付け**: Round 3 = **実装レビュー**。Round 1/2 は*計画*を見てもらった。今回は **main にマージ済みの実コード差分**を push（公開）前に grill してほしい。挙動不変リファクタが本当に挙動不変か、descope 判断が妥当か、を独立検証してほしい。
>
> **レビュアーへの前提**: 同一ワークスペース（`aegis/`）参照可。下記の git 差分を実際に見てから判定してほしい。
>
> **作成日**: 2026-06-05 / **対象**: `v0.12.2..HEAD`（main、origin 未push、7 commits）

---

## 0. レビュアーへの依頼

push してよいかの **GO / NO-GO** を判定してほしい。特に §3 の「最も突いてほしい実装上の論点」を独立検証してほしい。自動テストは 183 PASS だが、**テストが触れていない hook の挙動不変性は手目視レビューに依存**している（§3-1）。

## 1. レビュー対象コミット（`v0.12.2..HEAD`）

```
c0b79dc docs: update STATUS.md to reflect Foundation completion
003d2a9 refactor(hooks): extract destructive patterns into patterns.sh (single source)   ← F2-1
2fab714 refactor(hooks): route all hook output through emit.sh (behavior-preserving)      ← F1-2
7cc7b2f feat(hooks): add pure-bash emit.sh ... (fail-closed)                              ← F1-1
afc1a37 fix: reconcile version owner to FRAMEWORK_VERSION=0.12.2 (0.12.0 bump-miss)        ← F0-2
b443fdc docs: Foundation re-architecture design + Round1/2 briefs + v0.13 inventory
d6430c1 feat: v0.13.0 Phase 0b — ...（ユーザーの既存 WIP を確定。5ラウンドレビュー済み計画の産物）
```

**レビューの主対象は Foundation 実装（7cc7b2f / 2fab714 / 003d2a9 / afc1a37）**。Phase 0b（d6430c1）は別途レビュー済みの WIP なので、統合の整合だけ確認すれば良い。

確認用コマンド:
```bash
git diff v0.12.2..HEAD -- hooks/lib/emit.sh hooks/lib/patterns.sh   # 新規2ファイル
git diff v0.12.2..HEAD -- hooks/check-*.sh hooks/post-*.sh hooks/pre-*.sh hooks/session-start.sh  # 16 hook の置換
git diff v0.12.2..HEAD -- tests/test_check_status.py               # fixture 変更
git show afc1a37                                                    # version 整合
python3 -m unittest discover -s tests 2>&1 | tail -2               # 183 PASS 再現
grep -rn "printf '{" hooks/*.sh                                    # 0 件のはず
```

## 2. 実装サマリ（何をやったか）

- **emit.sh（新規）**: hook 出力 JSON を `emit_allow/deny/ask/block/context/continue_false` の6関数に集約。**pure-bash**（`_aegis_json_escape` はパラメータ展開のみ、python3/jq 非依存）。→ deny/block が外部 interpreter 不在でも fail-open しない。
- **16 hook の置換**: 全 `echo '{}'`→`emit_allow`、全手書き `printf '{...}'`→`emit_*`。各 hook のローカル escape ヘルパ（`escape_for_json`/`WARN_ESCAPED`/`ESCAPED`）を削除し生 reason を emit に渡す（emit が escape）。
- **patterns.sh（新規）**: check-destructive の if チェーンを配列ループ化（destructive パターンのみ）。
- **version**: `FRAMEWORK_VERSION` 0.12.0→0.12.2、template/example STATUS を整合。
- examples/minimal-project に emit.sh / patterns.sh をミラー、全 hook を同期（main↔example parity 一致）。

## 3. 最も突いてほしい実装上の論点

### ① 【最重要】テスト未カバー hook の挙動不変性は目視依存
`tests/test_hook_output_schema.py` が deny/ask/block を assert するのは check-gate / control-plane / secrets / destructive / deploy-gate / skill-gate / cron-gate / task-created / task-completed / post-status-audit / post-bash / pre-compact。**check-client-info / check-deploy-mcp-gate / check-tdd / session-start の出力パスは専用テストが薄い**可能性。これらは「printf→emit 置換が機械的に等価」という*目視*に依存している。
- **問い: テスト未カバーの hook で、置換により出力 JSON が変わった箇所はないか?** 各 deny/context の reason 文字列・event 名が元と一致するか diff で確認してほしい。

### ② emit.sh の pure-bash escaping は十分か
`_aegis_json_escape` は `\ " \n \t \r` を処理。reason は printf で組み立てた開発者文字列。
- **問い: 実際に hook が emit に渡す reason に、未対応文字（生制御文字等）が混入する経路はないか?** 特に外部断片を含む `check-cron-gate`（cron prompt）/ `check-task-created`（task subject）— printable truncation (`head -c N | tr '\n' ' '`) は残し JSON escape sed だけ削除した。この組み合わせで JSON が壊れないか。
- **問い: `printf` の二重適用（hook で `REASON=$(printf ...)` → emit で `printf '%s'`）に format-string 起因の取りこぼしはないか?**（reason は %s 引数なので安全と判断しているが独立確認を）

### ③ check-destructive ループ refactor の等価性
if チェーン → `AEGIS_DESTRUCTIVE_LOWER_*`（CMD_LOWER 対象）+ `AEGIS_DESTRUCTIVE_CMD_*`（CMD 対象）のループ化。rm -r の safe-targets 特例は手前で個別維持。
- **問い: 元の 14 パターンが過不足なく配列に移ったか（順序・CMD vs CMD_LOWER の対象・正規表現の文字列）。`set -u` 下で空配列展開や `break` のスコープに不具合はないか?**

### ④ test_check_status.py の fixture 変更は正当か
リファクタで hook が emit.sh を source するため、4 つの一時 scaffold に `emit.sh` symlink を追加（extract-input.sh symlink の隣）。
- **問い: これは「リファクタが原因の fixture ギャップ埋め」で正当か、それとも本来の不具合を隠していないか?** symlink 追加以外に assertion/ロジックの変更がないことを確認してほしい。

### ⑤ descope 判断の妥当性
- **check-secrets を patterns.sh 化しなかった**: 認証ファイルパターンが command-text regex / find -name glob / basename case / staged-path regex の **4 形**で context 固有（`id_rsa*` vs `id_rsa\b` vs `id_rsa.pub` 等のニュアンス差）。単一配列化はカバレッジを失うため見送り。
  - **問い: この descope は妥当か。patterns.sh が「destructive のみの真実源」になり secrets が別管理、という非対称は許容できるか?**
- **seed manifest を作らなかった**（Round 2 J-1）: version 二重書きのみで便益薄。
  - **問い: Foundation に manifest が無いことで、後続フェーズに困る依存はないか?**

### ⑥ version 整合（afc1a37）
`FRAMEWORK_VERSION=0.12.2`（最後の ship tag）/ `docs/STATUS.md` は作業中版 `0.13.0-pre` / template・example STATUS は `0.12.2`。
- **問い: この「owner=最後の ship 版 / STATUS=作業中版」モデルは一貫しているか。他に 0.12.0 残骸はないか?**

## 4. 参考

- 設計と判断経緯: `docs/plans/2026-06-05-v1-future-proof-rearchitecture-design.md`（§10 に Round 1/2 反映）
- Foundation 実装計画: `docs/plans/2026-06-05-v1-phase-f-foundation.md`（F0/F1/F2、完全コード）
- 棚卸し: `docs/plans/v0130-implementation-inventory.md`
- 検証実測: 183 tests PASS / contract PASS / drift PASS / check_status PASS / `printf '{'` = 0 / main↔example parity 一致

## 5. レビュアー返答テンプレート

```markdown
## push 可否: [GO / 条件付き GO / NO-GO]

## §3 各論点
- ① テスト未カバー hook の等価性: [問題なし / 不一致あり] — 具体箇所:
- ② emit escaping: [十分 / 懸念] —
- ③ destructive ループ等価性: [等価 / 差分あり] —
- ④ fixture 変更の正当性: [正当 / 懸念] —
- ⑤ descope（check-secrets / manifest）: [妥当 / 再考要] —
- ⑥ version 整合: [一貫 / 残骸あり] —

## 新たに気づいた点
<自由記述>

## push 前に直すべき点（あれば）
<自由記述>
```

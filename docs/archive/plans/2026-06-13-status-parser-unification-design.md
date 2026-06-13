# 設計: STATUS パーサ bash 一本化（M3 / v1.7.1）

- 日付: 2026-06-13
- 対象: v1.7.0（HEAD `ed401bc`）
- 出典: 第7回全力レビュー `docs/full-review-2026-06-13-context-futureproof.md` §1 M3 / §2 P3
- フェーズ: brainstorm（設計確定）→ writing-plans → grill-plan → TDD 実装 → grill-code

---

## 0. 目的と発見

M3＝「STATUS パーサ二重化」。`check_status.py`（schema 所有）とフック内の場当たり sed/grep/awk が並存し、format 変更時に複数箇所が連動＝壊れやすい（High/fragility）。

**調査での発見**: Python 側は**既に一本化済み**。`check_status.py` が `extract_frontmatter / extract_scalar_value / extract_approval_map / extract_current_refs / extract_session_history` を所有し、`status_doctor.py` は `from check_status import (...)` で再利用（重複なし・regex 方式）。よって**実際の重複は bash 側のみ**。

bash の重複実態:
- スカラ抽出 `grep -m1 "^key:" file | sed "s/^key://" | sed 's/"//'` が `extract_value` 関数2定義（session-start.sh:40 / pre-compact.sh:34）＋インライン約11箇所に散在。
- gate 値抽出 `frontmatter_section gate_approvals | grep -m1 "gate:" | sed` が約4箇所。
- `lib/frontmatter.sh` は section 抽出（`read_frontmatter`/`frontmatter_section`/`raw_section`）はあるが**スカラ値・gate 値の accessor が無い**。

スコープ確定: **bash スカラ + gate 値抽出の一本化のみ**。gate-snapshot の sed ブロック（3箇所）と status_doctor の `--health` 統合は対象外（blast radius 最小化）。failure_tracking の `grep -A3` 形は別シェイプで非対象（YAGNI）。

---

## 1. API（frontmatter.sh に2関数追加）

```bash
# scalar accessor — 既存 read_frontmatter/section と同系統。
frontmatter_value() {           # frontmatter_value <file> <key>
  local file="$1" key="$2"
  [ -f "$file" ] || return 0
  grep -m1 "^${key}:" "$file" | sed "s/^${key}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}

gate_value() {                  # gate_value <file> <gate>
  local file="$1" gate="$2"
  frontmatter_section "$file" gate_approvals | grep -m1 "  ${gate}:" | sed "s/.*${gate}:[[:space:]]*//" | sed 's/^"//;s/"$//' || true
}
```

設計判断:
- **whole-file `^key:` grep を維持**（`---` 限定にしない）。理由: post-status-audit.sh が bare `.gate-snapshot`（`---` 無し）からも同じ抽出をするため、`read_frontmatter` 限定だと snapshot で壊れる。whole-file grep なら STATUS.md・snapshot 両対応で**現行挙動と byte 一致**。
- **値 or 空・rc 0**（`|| true` 同梱）。各 call site の `|| true` を除去できる（DRY 副次効果）。set -e 下でも安全。
- `gate_value` は **2スペース anchor**（`"  ${gate}:"`）で部分一致防止（update-gate.sh:183 の安全形に統一。check-gate.sh:144 の無 anchor 形より厳密）。

---

## 2. 置換マッピング（call site → 関数）

| ファイル | 現状 | 置換後 | source 追加 |
|---|---|---|---|
| session-start.sh:40-43 | `extract_value()` 定義 | 定義削除→`frontmatter_value` 呼出 | 済 |
| session-start.sh:64-74 | gate section 1回＋ループ | **据え置き**（下記※） | 済 |
| pre-compact.sh:34-37 | `extract_value()` 定義 | 定義削除→`frontmatter_value` | **要** |
| check-gate.sh:106,132,143 | inline scalar×3（task_type/mode） | `frontmatter_value` | 済 |
| check-gate.sh:144 | gate(plan) | `gate_value` | 済 |
| check-control-plane.sh:226 | inline scalar（task_type） | `frontmatter_value` | **要** |
| check-task-completed.sh:98 | inline scalar（next_action） | `frontmatter_value` | **要** |
| check-task-created.sh:107,108 | gate(plan)+scalar(phase) | `gate_value`+`frontmatter_value` | 済 |
| check-client-info.sh:37 | inline scalar（mode） | `frontmatter_value` | **要** |
| post-status-audit.sh:70,71,100,101,118,119,164 | scalar×7（snapshot/STATUS 両方） | `frontmatter_value` | 済 |

※ **session-start.sh:64-74 は据え置き**。ここは `frontmatter_section gate_approvals` を1回抽出し、固定 gate キー列をループで読む形。`gate_value` に置換すると section 抽出が gate 数ぶん走り、挙動・性能が変わる。`gate_value` は単発取得の check-gate/check-task-created 向け。DRY と挙動保存のバランスでループは現行維持。

---

## 3. 挙動保存（最重要制約）

リファクタ＝**挙動完全不変**。`frontmatter_value` の3段パイプは現行インラインと文字単位で同一。`gate_value` は anchor 厳密化のみが差分（実 STATUS では同結果）。検証は §5 equivalence テストで全キー実測一致を証明する。

---

## 4. エラー処理・エッジケース

- キー不在 → 空・rc 0（現行 `|| true` と同一）。
- `key: ""`（空文字値）→ 空（sed が両引用符除去）。
- bare snapshot（`---` 無し）→ whole-file grep で動作（read_frontmatter 非依存）。
- 追加 `source frontmatter.sh` は各 hook の既存 lib-source 規約に合わせる（plain `source` / `aegis_require_lib`）。frontmatter.sh は session-start（全 profile）経由で既に全 profile 配布済み＝配布ギャップなし。

---

## 5. テスト（TDD）

- **単体**（`tests/test_frontmatter_lib.py` 拡張）:
  - `frontmatter_value`: present / absent（空） / quoted / unquoted / 空文字値 / 値中に空白 / 値中にコロン。
  - `gate_value`: present / absent（空） / null 値 / 部分一致しないこと（例 `plan` anchor が `plan_x` を拾わない）。
- **equivalence**: 代表的 STATUS.md ＋ bare snapshot を fixture に、旧3段パイプ出力と `frontmatter_value` 出力が全キー（mode/phase/task_type/next_action 等）で一致を assert（挙動不変の実証）。
- **既存緑維持**: session-start / check-gate / check-task-* / post-status-audit / update-gate / check_status 系の既存テストが全緑のまま（内部 rewire）。
- **mirror**: frontmatter.sh ＋編集する全 hook を `examples/minimal-project/` へ byte-identical 同期（`check_mirror_identity` 契約）。

---

## 6. 版数・mirror・SemVer

- 内部リファクタ・操作契約不変 → **patch v1.7.1**。版数4箇所（`FRAMEWORK_VERSION` 定数 / `templates/STATUS.template.md` / `examples/minimal-project/docs/STATUS.md` / `docs/STATUS.md`）を同期。
- 編集した frontmatter.sh ＋各 hook を example ミラーへ cp（drift 緑）。

---

## 7. 検証フロー

設計 commit → writing-plans → grill-plan（致命前提を着手前に実証反映）→ TDD 実装 → grill-code → 全テスト / contract 全 profile / drift / scaffold smoke / redteam PoC 緑 → STATUS.md 更新。

---

## 8. 非ゴール（明示）

- gate-snapshot の sed ブロック3箇所（session-start:27 / post-status-audit:152 / update-gate:331）の統一。
- status_doctor.py → check_status.py `--health` 統合。
- failure_tracking の `grep -A3` ネスト抽出の畳み込み。
- Python 側の変更（既に一本化済み）。

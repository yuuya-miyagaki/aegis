# Design: TDD profile（明文化＋local escape hatch）（Phase R 第3手）

> 作成日: 2026-06-06 / 対象モデル: Opus 4.8 / 起点: future-proof 再アーキ §3 KEEP「TDD = 保証として維持・backstop 化、strictness は profile 値（strict/advisory/off）、受託は既定 strict」＋ grill ⑥（off は minimal/local の escape hatch のみ・標準は strict）

## 1. 背景と狙い

future-proof 再アーキの三層 triage で **TDD は KEEP（保証）側**。hook で決定論的に強制する価値であり、撤廃でなく「維持・強化」が方針。routing（v0.12.3）・context budget（v0.12.4）に続く **Phase R 第3手**だが、前2件（DELEGATE＝数値撤廃）と違い**保証の整備**である。

### 探索で判明した前提（設計を縮約）

`check-tdd.sh` は `full` profile の `hooks_include` にのみ含まれ、`minimal`/`standard` には**同梱されない**。つまり設計 §3 が目指す strictness の大半が、既存の **profile = ファイル選択機構で既に実現済み**:

| profile | check-tdd | 実効 strictness |
|---|---|---|
| minimal | 非同梱 | **off**（grill ⑥ が望んだ「minimal 限定の escape hatch」） |
| standard | 非同梱 | off |
| full | 同梱・常に `emit_ask` | **strict**（ただし ask＝ユーザーが理由付きで承認可能＝Iron Law の組み込み escape） |

よって**新規に作るべきは小さい**: ①profile→strictness の明文化、②full 内で一時降格する local escape hatch、③off の可視化。manifest は未実装のため strictness 値は env var に置く。

## 2. スコープ（ブレスト決定）

1. **明文化＋local escape hatch**（"advisory 中間段を profile に追加" や "ask→deny 強化" は不採用）。
2. escape hatch は **strict / off の2値**（advisory ブランチは作らない・YAGNI）。未設定=strict。
3. `AEGIS_TDD_MODE=off` 設定時に **session-start で advisory** を出す（`CLAUDE_CODE_SUBAGENT_MODEL` 前例と同型・grill ⑥「off 形骸化」への対処）。

### 非スコープ
- 真の red→green 検証（PreToolUse hook では実行前のため不可。現行の「テストファイルが diff にある」heuristic を backstop として維持）。
- advisory（警告のみ非ブロック）tier。
- manifest 化（未実装・別フェーズ）。
- strict を `emit_ask`→`emit_deny` に強化（正当な非テスト編集も止まるため不採用）。

## 3. 設計

### 部品① check-tdd.sh（root + example、現状 IDENTICAL）— escape hatch

本番コード判定に入る前に env を読み、`off` なら即許可:

```bash
# Local escape hatch: AEGIS_TDD_MODE=off disables the TDD backstop for this session.
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
  emit_allow
  exit 0
fi
```

- 挿入位置: `source emit.sh` の後、本番コード判定ロジックの手前（`INPUT=$(cat)` でstdinを消費した後が安全）。
- 未設定 / `strict` / 不正値 → 既存ロジック（テスト無し→`emit_ask`）。**fail-safe で strict 既定**＝full の現行挙動を1バイトも変えない（env 未設定時）。
- **`off` は小文字限定**（`= "off"`）。`OFF`/`Off` は strict 扱い（fail-safe 方向）。ドキュメントに「小文字 `off`」と明記。normalize はしない（YAGNI）。
- **off の rationale**: strict は `emit_ask`（承認可）だが、新規テストを伴わない大規模 refactor（本番多数ファイル編集）では ask が連発し非効率。off はその session だけ一括バイパスする手段。3年後の読者が「ask があるのに off が要る理由」を理解できるよう記録。

### 部品② session-start.sh（root + example、root と example で DIFFER）— off の可視化

既存の `CONTEXT` 組み立て＋末尾 `emit_context SessionStart "$CONTEXT"` パターンに、`emit_context` 呼び出しの**直前**に1ブロック追加:

```bash
if [ "${AEGIS_TDD_MODE:-}" = "off" ]; then
  CONTEXT="${CONTEXT} | [WARNING] AEGIS_TDD_MODE=off — TDD backstop disabled this session; production edits will not prompt for tests"
fi
```

root は line 209 の `emit_context` 直前。example は内容が異なるため、各ファイルの `emit_context SessionStart` 呼び出しを特定して直前に挿入（**全文コピー禁止**）。

### 部品③ 明文化（CLAUDE.md root のみ ＋ README）

- `CLAUDE.md:17`「Hook enforcement level is set at install via `bin/setup.sh --profile`.」を拡張:
  > `- Hook enforcement level is set at install via \`bin/setup.sh --profile\` — TDD backstop is on in \`full\`, off in \`minimal\`/\`standard\`. In \`full\`, \`AEGIS_TDD_MODE=off\` disables it for the session (session-start warns).`

  現状463語・budget 650 に余裕（+~30語）。example CLAUDE.md には該当行が無いため **root のみ**。
- README の profiles 節（`Available profiles:` 付近）に「TDD backstop: full=strict / minimal・standard=off、`AEGIS_TDD_MODE=off` で full 内の session 一時バイパス」を追記（budget なし）。

### 部品④ テスト（tests/test_hook_output_schema.py）— TDD で追加

check-tdd のテストは現状 TODO コメントのみ＝**未実装**。`run_hook(..., env=...)` 対応済み。本番ファイル編集 payload に対し:

```python
def test_check_tdd_asks_when_no_test_changes(self):
    """AEGIS_TDD_MODE unset (strict default): prod edit without tests → ask."""
    payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
    rc, out, err = run_hook("check-tdd.sh", payload, cwd=Path(self.tmp))
    # 非空を明示 assert（`if out:` ガードだと誤って allow を返しても空振りで PASS してしまう）
    self.assertNotEqual(out, {}, "strict default must not allow ({})")
    self.assert_pretool_decision(out, "ask", hint="check-tdd strict default")

def test_check_tdd_off_allows(self):
    """AEGIS_TDD_MODE=off: prod edit without tests → allow (bypass)."""
    payload = make_pretool_payload("Edit", {"file_path": "src/app.ts"})
    rc, out, parsed_err = run_hook(
        "check-tdd.sh", payload, cwd=Path(self.tmp), env={"AEGIS_TDD_MODE": "off"}
    )
    self.assertEqual(out, {}, "off must emit allow ({})")
```

- `cwd=self.tmp`（git 管理外の一時dir）で `git diff` が空＝「テスト変更なし」を決定論的に再現。strict→ask、off→allow。
- off テストは現行 check-tdd.sh（env 無視）に対し **FAIL（ask を返す）→ 部品①実装後に PASS**＝正しい失敗テスト。

## 4. 変更ファイルとバージョン

| ファイル | 変更 |
|---|---|
| `hooks/check-tdd.sh` | 部品①（env off バイパス） |
| `examples/minimal-project/hooks/check-tdd.sh` | 部品①（root と同一・IDENTICAL 維持） |
| `hooks/session-start.sh` | 部品②（off advisory・line 209 直前） |
| `examples/minimal-project/hooks/session-start.sh` | 部品②（emit_context 直前・**差異あり**） |
| `CLAUDE.md` | 部品③（root のみ・enforcement 行拡張） |
| `README.md` | 部品③（profiles 節） |
| `tests/test_hook_output_schema.py` | 部品④（check-tdd テスト2件） |
| `scripts/check_framework_contract.py:17` | `FRAMEWORK_VERSION = "0.12.5"` |
| `templates/STATUS.template.md:3` | `framework_version: "0.12.5"` |
| `docs/plans/2026-06-06-v1-tdd-profile-design.md` | 本書（新規） |

version `0.12.4` → `0.12.5`（patch）。挙動変化は env 駆動バイパスの追加（既定 off ＝既存不変）。

## 5. 挙動変化

- **新規**: full profile で `AEGIS_TDD_MODE=off` を設定するとその session の TDD backstop がバイパスされる。**env 未設定時は strict で既存挙動が完全不変**。off 設定時は session-start が `[WARNING]` を出す。
- strict は `emit_ask`（承認可）のまま。

## 6. Verification（完了条件・全て緑が必須）

```bash
cd aegis
python3 -m unittest discover -s tests -q      # 既存183 + 新規2 = 185 緑
python3 scripts/check_reference_drift.py       # version #7
python3 scripts/check_framework_contract.py    # 見出し / word≤650 / version sync
```

- 新規 check-tdd テスト2件が PASS（strict→**非空 ask** / off→allow `{}`）。strict テストは `assertNotEqual(out, {})` で空振りを防ぐ。
- contract: CLAUDE.md word count ≤ 650（拡張後も）、version sync。
- root/example の check-tdd.sh が IDENTICAL を維持（手動 diff も可）。
- **session-start advisory はテスト無し・手動検証**（SessionStart テストクラスが現状存在せず、文字列 append で低リスク。既存の `CLAUDE_CODE_SUBAGENT_MODEL` advisory も同様に未テストで一貫）。`AEGIS_TDD_MODE=off bash hooks/session-start.sh < /dev/null` で `[WARNING]` 出力を目視確認する。

## 7. 完了後 bookkeeping

- memory `aegis-rearchitecture-direction.md`: TDD profile 完了を追記（Phase R 第3手・v0.12.5）。
- 再アーキ設計 §3 KEEP「TDD」行に完了注記。§11 にも反映。
- 実装計画を docs/plans に commit（retention 規約）。
- まとめて push。

## 8. リスク

| # | リスク | 対応 |
|---|---|---|
| R1 | off の常用で TDD 形骸化（grill ⑥） | session-start advisory で毎セッション可視化。off は env の明示操作（人間の意図的 bypass が勝つのは model/effort policy と同じ思想） |
| R2 | session-start.sh が root/example で差異・挿入位置ミス | **末尾 `emit_context SessionStart "$CONTEXT"` 行は両ファイル同一**（検証済み）→ この共有行をアンカーに**両ファイル同一 Edit**で advisory を直前挿入可能。全文コピーは依然禁止（行アンカーのみ） |
| R3 | CLAUDE.md word budget 超過 | 現状463語・+~30語で余裕。contract が ≤650 を FAIL 強制 |
| R4 | check-tdd off バイパスが本番コード以外も素通り | 元々 emit_allow される非本番ファイルと同じ＝実害なし。off は「テスト無し本番編集を許可」が目的 |
| R5 | version sync 漏れ | contract version sync が FAIL 強制 |

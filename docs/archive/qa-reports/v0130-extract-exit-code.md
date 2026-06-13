# v0.13.0 Phase 0b: extract_exit_code Dual-Schema Verification

Date: 2026-05-15
Scope: `hooks/lib/extract-input.sh` の `extract_exit_code` 関数を、PostToolUse/PostToolUseFailure の payload で **`tool_response.exitCode`（camelCase）** と **`tool_result.exit_code`（legacy）** の両キー対応にする実装と、その単体検証。

## 背景

Phase 0a (v0.12.2) 時点で、Claude Code Hooks 公式 docs に **PostToolUse の tool result key 名は明記されていない**ことが判明した（5 ラウンドのレビュー Round 2 で確認）。aegis の従来実装は `tool_result.exit_code`（snake_case）を参照していたが、現行 Claude Code 2.x の実 payload では `tool_response.exitCode`（camelCase）の可能性が高い。

Round 2 レビュアー提案: 両キー対応コードで保険、実機検証ログを記録。

## 実装

`hooks/lib/extract-input.sh` の `extract_exit_code` を以下の優先順位で probe:

1. `tool_response.exitCode` (camelCase, Claude Code 2.x suspected)
2. `tool_response.exit_code` (snake_case under tool_response, defensive)
3. `tool_result.exit_code` (legacy / aegis pre-v0.12.2)
4. `tool_result.exitCode` (defensive)

最初に non-null 値を返し、なければ `0` を返す。

```bash
extract_exit_code() {
  local input="$1"
  printf '%s' "$input" | python3 -c '
import sys, json
try:
    data = json.loads(sys.stdin.read())
except Exception:
    print(0)
    sys.exit(0)
tr = data.get("tool_response") or {}
tl = data.get("tool_result") or {}
for v in (tr.get("exitCode"), tr.get("exit_code"), tl.get("exit_code"), tl.get("exitCode")):
    if v is not None:
        print(v)
        sys.exit(0)
print(0)
' 2>/dev/null || echo "0"
}
```

## 検証

### 単体テスト: `TestExtractExitCode` (6 ケース、全 PASS)

| ケース | 入力 payload | 期待出力 | 結果 |
|---|---|---|---|
| `test_tool_response_exit_code_camel_case` | `{"tool_response":{"exitCode":42}}` | `42` | ✅ |
| `test_tool_response_exit_code_snake_case` | `{"tool_response":{"exit_code":7}}` | `7` | ✅ |
| `test_tool_result_exit_code_legacy` | `{"tool_result":{"exit_code":13}}` | `13` | ✅ |
| `test_priority_tool_response_over_tool_result` | `{"tool_response":{"exitCode":1},"tool_result":{"exit_code":99}}` | `1`（response 優先）| ✅ |
| `test_default_zero_when_missing` | `{}` | `0` | ✅ |
| `test_zero_exit_returned_correctly` | `{"tool_response":{"exitCode":0}}` | `0` | ✅ |

実行：
```
$ python3 -m unittest tests.test_hook_output_schema.TestExtractExitCode -v
Ran 6 tests in 0.xxxs
OK
```

### 統合動作

`post-bash.sh`（PostToolUseFailure）は `extract_exit_code` を直接呼ばないが（PostToolUseFailure event は失敗時のみ発火するため exit code チェック不要）、将来の `PostToolUse` 系 hook（例: 成功検知が必要なケース）で再利用される基盤として両キー対応を確立。

## 残課題（実機 payload 確認）

公式 docs に明示されていないため、実機 Claude Code セッションで以下を確認する必要がある（v0.13.0 ship 後の運用で記録）：

- [ ] PostToolUse Bash で実際に渡される JSON のトップレベルキーは `tool_response` か `tool_result` か
- [ ] 該当キー下の exit code は `exitCode` (camelCase) か `exit_code` (snake_case) か

両キー対応コードは検証結果に関わらず安全に動作するため、ship をブロックしない。実機検証結果が判明したら、`extract_exit_code` の `for` ループの優先順位を実情に合わせて並べ替える（コメントに優先順位の根拠を明記する形で）。

## 関連ファイル

- `hooks/lib/extract-input.sh` line 33-58: `extract_exit_code` 関数
- `tests/test_hook_output_schema.py`: `TestExtractExitCode` クラス
- `docs/plans/v0130-modernization-plan.md` Rev.5 § Phase 0b Task 0b-3: 両キー対応の方針

## 結論

両キー対応コードを実装し、6 ケースの単体テストで検証済み。実機 payload 確認は v0.13.0 ship 後の運用で記録する。Ship 前提条件：両キー対応が動作することを単体テストで担保 → 達成。

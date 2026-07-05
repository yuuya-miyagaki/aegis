"""iter57: explain-oslock-eacces.sh — PostToolUseFailure advisory.

主 moat 一本化後、EACCES に出会ったエージェントの最自然な反応は `chmod +w`
自己修復（rev.2 撤回理由②）。それを撃つ前に「これは OS-lock・解錠するな・
framework 作業なら task_type=framework」を説明する純 advisory。

発火条件は AND: (1) tool_response.stderr が permission-denied/EACCES を含む
かつ (2) tool_input.command が lock 対象 CP に言及。両方要るのは、grep の
no-match など無害な非ゼロ終了（CP 言及はあるが EACCES ではない）での誤発火を
避けるため。純 advisory ゆえ全失敗は fail-open（exit 0・出力なし）。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "explain-oslock-eacces.sh"


def _run(payload: str) -> str:
    r = subprocess.run(["bash", str(HOOK)], input=payload,
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr  # advisory は常に exit 0
    return r.stdout


def _envelope(command: str, stderr: str, exit_code: int = 1) -> str:
    return json.dumps({
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": "", "stderr": stderr,
                          "exit_code": exit_code, "interrupted": False},
    })


def _has_advisory(out: str) -> bool:
    return "additionalContext" in out and "OS-lock" in out


def test_eacces_on_cp_write_fires_advisory():
    out = _run(_envelope(
        "cp evil hooks/lib/emit.sh",
        "cp: hooks/lib/emit.sh: Permission denied"))
    assert _has_advisory(out), out
    assert "task_type=framework" in out or "update-task.sh" in out


def test_chmod_unlock_eacces_fires_advisory():
    out = _run(_envelope(
        "chmod +w scripts/tool.py",
        "chmod: scripts/tool.py: Operation not permitted"))
    assert _has_advisory(out), out


def test_eacces_without_cp_mention_stays_silent():
    """CP 以外への EACCES（例 /etc）は本 moat の話ではない → 沈黙。"""
    out = _run(_envelope(
        "touch /etc/foo", "touch: /etc/foo: Permission denied"))
    assert out.strip() == "" or "additionalContext" not in out, out


def test_cp_mention_without_eacces_stays_silent():
    """grep no-match 等の無害な非ゼロ終了（CP 言及あり・EACCES なし）→ 沈黙。"""
    out = _run(_envelope(
        "grep nonexistent hooks/lib/emit.sh", ""))
    assert out.strip() == "" or "additionalContext" not in out, out


def test_broken_json_fails_open_silently():
    out = _run("this is not json { at all")
    assert out.strip() == "" or "additionalContext" not in out, out


def test_empty_input_fails_open():
    out = _run("")
    assert out.strip() == "" or "additionalContext" not in out, out


def test_transcript_path_alone_not_a_cp_hit():
    """envelope の transcript_path は必ず ~/.claude/projects/ を含むが、
    それだけを CP ヒットにしてはならない（誤発火防止）。"""
    payload = json.dumps({
        "hook_event_name": "PostToolUseFailure",
        "tool_name": "Bash",
        "tool_input": {"command": "false"},
        "tool_response": {"stdout": "", "stderr": "some error: Permission denied",
                          "exit_code": 1, "interrupted": False},
        "transcript_path": "/Users/x/.claude/projects/p/t.jsonl",
    })
    out = _run(payload)
    assert out.strip() == "" or "additionalContext" not in out, out

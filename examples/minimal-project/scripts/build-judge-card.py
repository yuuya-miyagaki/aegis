#!/usr/bin/env python3
"""Judge-card builder (B2). Runs at gate-approval time as a pure script.

Re-checks tier-1 machine facts, compares them with the gate report's recorded
`claims:`, compares recorded 1st/2nd review verdicts, and emits a judge card
with a tri-state verdict. Exit 0=🟢 / 1=🔴 (block) / 2=🟡 (needs ack).
Never dispatches an LLM (the second opinion is recorded by the LLM beforehand).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


class JudgeError(Exception):
    """Unexpected internal failure => fail-closed (treated as 🔴)."""


_DRILL = None


def _drill():
    """Lazy-load B1's drill module (reuse added_lines_by_file/resolve_diff_ref/
    _execute). The filename has hyphens, so load by path."""
    global _DRILL
    if _DRILL is None:
        import importlib.util
        path = Path(__file__).resolve().parent / "run-test-strength-drill.py"
        spec = importlib.util.spec_from_file_location("drill_mod", path)
        _DRILL = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_DRILL)
    return _DRILL


def code_fingerprint(root: Path) -> str:
    """sha256 over the changed files' current content (sorted), binding a test
    result to the exact code it was produced against."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    changed = sorted(drill.added_lines_by_file(root, ref).keys())
    h = hashlib.sha256()
    for rel in changed:
        h.update(rel.encode("utf-8"))
        try:
            h.update((root / rel).read_bytes())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()


STUB_PATTERN = re.compile(r"TODO|FIXME|XXX|NotImplementedError|pass\s*#\s*stub|placeholder",
                          re.IGNORECASE)


def scan_stubs(root: Path) -> list[str]:
    """Scan ONLY changed (added) lines for stub/placeholder markers. Returns
    a list of 'file:line' hits (empty = clean)."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    added = drill.added_lines_by_file(root, ref)
    hits: list[str] = []
    for rel, lines in added.items():
        try:
            content = (root / rel).read_text(encoding="utf-8").split("\n")
        except OSError:
            continue
        for ln in sorted(lines):
            if 1 <= ln <= len(content) and STUB_PATTERN.search(content[ln - 1]):
                hits.append(f"{rel}:{ln}")
    return hits


def read_test_result(root: Path) -> str:
    """Read docs/qa-reports/test-result.json and verify freshness against the
    current code fingerprint. Returns 'green' / 'red' / 'unverified'
    (absent/stale/unreadable => unverified, never silent-green)."""
    p = root / "docs" / "qa-reports" / "test-result.json"
    if not p.is_file():
        return "unverified"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "unverified"
    if data.get("code_fingerprint") != code_fingerprint(root):
        return "unverified"
    status = data.get("status")
    return status if status in ("green", "red") else "unverified"


SECRET_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]))")


def scan_secrets(root: Path) -> list[str]:
    """Scan changed files for secret-like patterns. Returns 'file:line' hits."""
    drill = _drill()
    ref = drill.resolve_diff_ref(root)
    hits: list[str] = []
    for rel in drill.added_lines_by_file(root, ref):
        try:
            for i, line in enumerate((root / rel).read_text(encoding="utf-8").split("\n"), 1):
                if SECRET_PATTERN.search(line):
                    hits.append(f"{rel}:{i}")
        except OSError:
            continue
    return hits


def audit_deps(root: Path) -> str:
    """Run an available dependency auditor. Returns 'clean' / 'vuln' /
    'unverified' (no tool / offline / error => unverified, never blocks)."""
    for cmd in (["pip-audit", "-q"], ["npm", "audit", "--audit-level=high"]):
        try:
            proc = subprocess.run(cmd, cwd=str(root), capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            continue
        return "clean" if proc.returncode == 0 else "vuln"
    return "unverified"


GATE_REF_KEY = {"review": "review", "qa": "qa", "security": "security",
                "deploy": "deploy"}


def resolve_gate_report(root: Path, gate: str) -> Path | None:
    """Read current_refs.<ref_key> from STATUS.md; return the report path or
    None when the ref is null/absent (=> 🟡 evidence-not-submitted upstream)."""
    ref_key = GATE_REF_KEY.get(gate)
    if not ref_key:
        return None
    status = root / "docs" / "STATUS.md"
    if not status.is_file():
        return None
    in_refs = False
    for line in status.read_text(encoding="utf-8").splitlines():
        if re.match(r"^current_refs:\s*$", line):
            in_refs = True
            continue
        if in_refs and re.match(r"^[A-Za-z_]", line):  # next top-level key
            break
        if in_refs:
            m = re.match(rf"^\s+{ref_key}:\s*(.+)$", line)
            if m:
                val = m.group(1).strip().strip('"')
                if val in ("null", "", "[]"):
                    return None
                return root / val
    return None


# gates that require a self-attested second opinion (tier-2)
SECOND_OPINION_GATES = ("review", "security")


class Verdict:
    # Plain class (not a dataclass): with `from __future__ import annotations`
    # a dataclass resolves field annotations via sys.modules[__module__], which
    # is absent when this file is loaded via importlib (record-test-result.py,
    # tests) and raises. A plain class is load-mechanism agnostic.
    def __init__(self, overall: int, red=None, yellow=None):
        self.overall = overall          # 0=🟢 / 1=🔴 / 2=🟡
        self.red = red if red is not None else []
        self.yellow = yellow if yellow is not None else []


def compute_verdict(gate: str, claims: dict | None, facts: dict,
                    second_opinion: dict | None) -> Verdict:
    """Harness-computed verdict. Tier-1 facts BLOCK (🔴); claims-absent and
    tier-1-unverified and tier-2 divergence are advisory (🟡). Tier-2 NEVER
    blocks (assurance is self-attested)."""
    red: list[str] = []
    yellow: list[str] = []

    # tier-1 facts run unconditionally (independent of what was claimed)
    if facts["stubs"]:
        red.append(f"変更コードに未完成マーカー: {', '.join(facts['stubs'])}")
    if facts["secrets"]:
        red.append(f"シークレットの疑い: {', '.join(facts['secrets'])}")
    if facts["tests"] == "red":
        red.append("テストが赤")
    elif facts["tests"] == "unverified":
        yellow.append("テスト結果が未検証（記録なし/コード変更後）")
    if facts["deps"] == "unverified":
        yellow.append("依存監査が未検証")
    elif facts["deps"] == "vuln":
        if claims and claims.get("deps_clean") is True:
            red.append("依存に脆弱性（claim deps_clean: true と矛盾）")
        else:
            yellow.append("依存監査で脆弱性の可能性（誤検知の場合あり・要確認）")
    if facts.get("b1_verdict") == "FAIL":
        red.append("テスト強度ドリル(B1)が FAIL")

    # claims sanity (advisory; missing claims must not hard-block — §1.5)
    if claims is None:
        yellow.append("claims 未提出（要確認）")

    # tier-2: self-attested second opinion (advisory only, never blocks)
    if gate in SECOND_OPINION_GATES:
        if second_opinion is None:
            yellow.append("第2意見なし（self-attested・要確認）")
        elif claims and second_opinion.get("verdict") != claims.get("verdict"):
            yellow.append(
                f"1次/2次レビューの相違（self-attested）: "
                f"1次={claims.get('verdict')} / 2次={second_opinion.get('verdict')}")

    overall = 1 if red else (2 if yellow else 0)
    return Verdict(overall=overall, red=red, yellow=yellow)


def collect_facts(root: Path, gate: str) -> dict:
    b1 = None
    if gate == "qa":
        ts = root / "docs" / "qa-reports" / "test-strength.md"
        if ts.is_file():
            m = re.search(r"verdict:\s*(\w+)", ts.read_text(encoding="utf-8"))
            b1 = m.group(1) if m else None
    secrets = scan_secrets(root) if gate == "security" else []
    deps = audit_deps(root) if gate == "security" else "clean"
    return {
        "tests": read_test_result(root),
        "stubs": scan_stubs(root),
        "secrets": secrets,
        "b1_verdict": b1,
        "deps": deps,
    }


def render_card(report_out: Path, *, gate: str, v: Verdict, claims: dict | None,
                facts: dict, second_opinion: dict | None) -> None:
    sym = {0: "🟢 承認可", 1: "🔴 ブロック", 2: "🟡 要確認"}[v.overall]
    lines = [f"# Judge カード: {gate} ゲート（機械生成）", "",
             f"## 総合: {sym}", "",
             "## ティア1: 機械事実（✅検証済・高信頼）",
             f"- テスト: {facts['tests']}",
             f"- 未完成マーカー(変更行): {facts['stubs'] or 'なし'}"]
    if gate == "security":
        lines.append(f"- シークレット: {facts['secrets'] or 'なし'}")
        lines.append(f"- 依存監査: {facts['deps']}")
    if gate == "qa":
        lines.append(f"- テスト強度ドリル(B1): {facts['b1_verdict'] or '未実施'}")
    if gate in SECOND_OPINION_GATES:
        lines += ["", "## ティア2: 🔍 第2意見（self-attested・自己申告・低信頼）",
                  f"- {('あり: ' + str(second_opinion.get('verdict'))) if second_opinion else 'なし'}"]
    if v.red:
        lines += ["", "## 🔴 ブロック要因"] + [f"- {r}" for r in v.red]
    if v.yellow:
        lines += ["", "## 🟡 要確認"] + [f"- {y}" for y in v.yellow]
    lines += ["", "## あなたが取るアクション", "（LLM が平易日本語で記述）", ""]
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text("\n".join(lines), encoding="utf-8")


def build(root: Path, gate: str, report_out: Path) -> int:
    try:
        report = resolve_gate_report(root, gate)
        claims = read_claims(report) if report else None
        second = claims.get("second_opinion") if claims else None
        facts = collect_facts(root, gate)
        v = compute_verdict(gate, claims, facts, second)
        render_card(report_out, gate=gate, v=v, claims=claims, facts=facts,
                    second_opinion=second)
        for r in v.red:
            print(f"🔴 {r}")
        for y in v.yellow:
            print(f"🟡 {y}")
        return v.overall
    except Exception as exc:  # fail-closed: any internal error blocks
        print(f"JUDGE BLOCKED (fail-closed): {exc}")
        return 1


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Judge-card builder (B2)")
    p.add_argument("--gate", required=True)
    p.add_argument("--root", default=".")
    p.add_argument("--report-out", default=None)
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.report_out) if args.report_out else (
        root / "docs" / "qa-reports" / f"judge-{args.gate}.md")
    return build(root, args.gate, out)


def _parse_scalar(v: str):
    s = v.strip()
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    return s.strip('"')


def read_claims(report_path: Path) -> dict | None:
    """Read the single fenced ```claims YAML block from a gate report. Returns a
    flat dict (nested second_opinion captured as a sub-dict) or None if the file
    or block is absent. Intentionally a narrow YAML subset (key: value lines and
    one nested `second_opinion:` map) to stay dependency-free."""
    if not report_path.is_file():
        return None
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"```claims\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None
    claims: dict = {}
    cur_map: dict | None = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z_]+:\s*$", line):  # "second_opinion:" map start
            key = line.split(":")[0].strip()
            cur_map = {}
            claims[key] = cur_map
            continue
        indented = line.startswith("  ")
        kv = line.strip().split(":", 1)
        if len(kv) != 2:
            continue
        key, val = kv[0].strip(), kv[1].strip()
        if indented and cur_map is not None:
            cur_map[key] = _parse_scalar(val)
        else:
            cur_map = None
            claims[key] = _parse_scalar(val)
    return claims


if __name__ == "__main__":
    sys.exit(main())

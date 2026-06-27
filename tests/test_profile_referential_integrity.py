#!/usr/bin/env python3
"""iter48: profile 参照整合性（self-containment）の横断検査。

背景（grill-premise で実証済みの 2 穴・同一クラス）:
  - D5: status_doctor.py（full 同梱）は版ドリフト判定に check_framework_contract.py を
    読むが、後者はどの profile にも入っておらず、full install で version-drift 警告が
    永久に沈黙する。
  - JNY-07: check_status.py（全 profile 同梱）は client-gate deny の「テンプレ場所」ヒントに
    _artifact_template_map.py を import するが try/except で空 dict に degrade。後者は
    どの profile にも入っておらず、install で非エンジニア向けヒントが消える。

いずれも「graceful degrade が、未同梱依存のせいで shipped 機能をサイレントに殺す」。
個別 parity テスト（checker parity / judge toolchain / safety lib）の網の隙間。本テストは
**各 profile で shipped .py の依存辺を自動検出**し、「同梱 ∨ 理由付き allow-list」を恒久検査して
このクラスの再発を封鎖する。

依存辺の自動検出（手動リスト無し＝ドリフト不能）:
  1. static import: ast の Import/ImportFrom で module 名が scripts/<mod>.py に実在する兄弟。
  2. dynamic/string: ast.Constant(str) が *.py かつ basename が兄弟 scripts/<basename> に実在
     （importlib・subprocess・string-read を自動捕捉。ハイフン名は import 不可視だが拾える）。
過検出（docstring 中の .py 等）は fail-closed＝allow-list で明示解消する。

対象外（本スライスの bound）: required-vs-recommended の severity（現状 gate-blocking 依存は
既に required）／command(.md)→script の網羅（commands は setup.sh:resolve_source で
templates/commands/ の scaffold-safe 版に差し替わり graceful degrade するため別問題）。

iter49 追補: skill(.md)→script を本ファイル後段（_skill_script_edges 以降）で検査する。
skills は templates 変種を持たず **verbatim install** される次元で、shipped skill が
未同梱 script を参照すると install 後にサイレントに inert 化する（実穴: full の
aegis-brainstorm/bug-diagnosis → scripts/update-task.sh）。.py 限定の前段検査とは検査対象
artifact（skill .md vs script .py）が異なるため分離して実装する。SKILL.md だけでなく
skill ディレクトリ内の全 .md asset（例 deploy/platforms.md）が verbatim install されるため
検査対象に含める。同じ verbatim-install サーフェスの .claude/agents/*.md も同型だが、現状
shipped agent の script 参照はゼロ（実証済）のため本スライスでは射程外（穴が出たら同機構で別スライス）。
"""
from __future__ import annotations

import ast
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PROFILES_DIR = ROOT / "templates" / "profiles"


# 意図的非同梱の allow-list: { profile_name: { "scripts/<dep>.py": "理由" } }。
# 理由は非空必須（サイレント許容を禁止＝test_all_allowlist_reasons_nonempty が番人）。
INTENTIONAL_UNSHIPPED: dict[str, dict[str, str]] = {
    "minimal": {
        "scripts/_artifact_template_map.py": (
            "minimal は core-only profile。Client workflow 不在で client-gate の"
            "テンプレ位置ヒントは未使用（LEARNINGS conf8: Client 機能は full 集約）。"
        ),
        "scripts/build-judge-card.py": (
            "minimal は judge toolchain 非同梱。check_status.run_judge_card 経路は"
            "minimal 利用で未到達。"
        ),
        "scripts/run-test-strength-drill.py": (
            "minimal は judge toolchain 非同梱。drill 経路は minimal 利用で未到達。"
        ),
    },
    "standard": {
        "scripts/_artifact_template_map.py": (
            "standard は Dev-lean profile。Client workflow は full 集約（LEARNINGS conf8）。"
            "client-gate のテンプレ位置ヒントは standard 利用で未使用。"
        ),
    },
    "full": {
        "scripts/check_framework_contract.py": (
            "contract/version ツールチェーンは maintainer 専用。D5 ドリフトは"
            " maintainer→install 方向の検査で、install 単体は新版を観測できない"
            "（field no-op は by-design）。依存閉包 platform_manifest+context_budget を"
            " install に引き込まないため意図的に非同梱。"
        ),
    },
}


def _sibling_script_names() -> set[str]:
    """scripts/ 直下の .py ファイル名の集合（依存辺の解決先）。"""
    return {p.name for p in SCRIPTS_DIR.glob("*.py")}


def _deps_from_source(src: str, self_name: str, siblings: set[str]) -> set[str]:
    """src（.py の本文）が参照する兄弟スクリプト依存を rel-path 集合で返す。

    static import（try/except 内も含む）＋ 文字列定数中の sibling .py を自動検出する。
    自分自身への参照は除外する。

    検出境界（既知の限界）:
    - 拾うのは `ast.Constant(str)` の **literal** のみ。f-string（`f"{x}.py"`）や連結で
      動的に組むファイル名は拾わない。将来 `importlib.load(f"{name}.py")` のような動的構築が
      現れたら本検出は漏らす（D5 と同型の穴になりうる）ため、その種の辺は導入時に literal 化
      するか別途明示登録すること。
    - **bare-expression の文字列（module/func/class の docstring・単独の文字列文）は除外**する
      （実依存の参照は代入/呼び出し引数/リスト要素であって裸の文字列文ではない＝docstring 中の
      `.py` 言及で allow-list を汚さないため）。
    - import は flat な兄弟 module 名のみ解決（`import scripts.foo` のようなドット付きは対象外。
      現状の scripts は flat import のみ）。
    """
    tree = ast.parse(src)
    # docstring / 裸の文字列文（ast.Expr の値）の Constant は除外対象として id を集める。
    bare_string_ids = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if f"{alias.name}.py" in siblings:
                    out.add(f"scripts/{alias.name}.py")
        elif isinstance(node, ast.ImportFrom):
            if node.module and f"{node.module}.py" in siblings:
                out.add(f"scripts/{node.module}.py")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in bare_string_ids
        ):
            base = node.value.split("/")[-1]
            if base.endswith(".py") and base in siblings:
                out.add(f"scripts/{base}")
    out.discard(f"scripts/{self_name}")
    return out


def _violations(shipped: set[str], edges: set[str], allowlist: dict[str, str]) -> list[str]:
    """edges のうち、同梱されておらず（shipped 外）かつ非空 reason の allow-list にも
    無い dep を違反として返す（純関数・negative control 用）。"""
    out: list[str] = []
    for dep in sorted(edges):
        if dep in shipped:
            continue
        reason = allowlist.get(dep)
        if reason and reason.strip():
            continue
        out.append(dep)
    return out


def _shipped_scripts(profile: dict) -> set[str]:
    """profile が install で配る .py（required ∪ recommended。setup.sh は両方コピー）。"""
    entries = list(profile.get("required", [])) + list(profile.get("recommended", []))
    return {e for e in entries if e.startswith("scripts/") and e.endswith(".py")}


# ---- 単体テスト（ヘルパに歯があることの担保） ----

def test_deps_picks_up_static_import():
    sib = {"_artifact_template_map.py", "check_status.py"}
    src = "from _artifact_template_map import X\n"
    assert _deps_from_source(src, "check_status.py", sib) == {"scripts/_artifact_template_map.py"}


def test_deps_picks_up_string_literal_sibling():
    sib = {"check_framework_contract.py", "status_doctor.py"}
    src = 'contract = "check_framework_contract.py"\n'
    assert "scripts/check_framework_contract.py" in _deps_from_source(src, "status_doctor.py", sib)


def test_deps_ignores_stdlib_import():
    sib = {"check_status.py"}
    src = "import json\nimport os\n"
    assert _deps_from_source(src, "check_status.py", sib) == set()


def test_deps_counts_imports_inside_try():
    sib = {"_artifact_template_map.py", "check_status.py"}
    src = "try:\n    from _artifact_template_map import X\nexcept ImportError:\n    X = {}\n"
    assert _deps_from_source(src, "check_status.py", sib) == {"scripts/_artifact_template_map.py"}


def test_deps_ignores_comment_mentions():
    # コメントは AST に現れない（文字列定数ではない）ので拾わない。
    sib = {"status_doctor.py", "check_status.py"}
    src = "# see status_doctor.py for details\nx = 1\n"
    assert _deps_from_source(src, "check_status.py", sib) == set()


def test_deps_ignores_docstring_mentions():
    # module docstring 中の .py 言及は bare-expression なので拾わない（境界を固定）。
    sib = {"status_doctor.py", "check_status.py"}
    src = '"""This module orchestrates status_doctor.py after each gate."""\nx = 1\n'
    assert _deps_from_source(src, "check_status.py", sib) == set()


def test_deps_picks_up_string_literal_in_real_statement():
    # docstring 除外が、代入・呼び出し引数など実依存の文字列まで巻き込まないことを固定。
    sib = {"check_framework_contract.py", "status_doctor.py"}
    src = 'p = root / "scripts" / "check_framework_contract.py"\n'
    assert _deps_from_source(src, "status_doctor.py", sib) == {"scripts/check_framework_contract.py"}


def test_violations_flags_unshipped_and_unallowed():
    assert _violations(set(), {"scripts/x.py"}, {}) == ["scripts/x.py"]


def test_violations_respects_allowlist_with_reason():
    assert _violations(set(), {"scripts/x.py"}, {"scripts/x.py": "intended"}) == []


def test_violations_flags_empty_reason():
    assert _violations(set(), {"scripts/x.py"}, {"scripts/x.py": "  "}) == ["scripts/x.py"]


def test_all_allowlist_reasons_nonempty():
    for profile_name, deps in INTENTIONAL_UNSHIPPED.items():
        for dep, reason in deps.items():
            assert reason and reason.strip(), (
                f"INTENTIONAL_UNSHIPPED['{profile_name}']['{dep}'] には非空 reason が必要"
            )


def test_no_stale_or_redundant_allowlist_entries():
    """allow-list 自身の rot を検知（本イテレーションが戦う『サイレント劣化』を
    allow-list にも適用）。エントリは (a) その profile の shipped script が実際に参照する
    辺であり、かつ (b) その profile に同梱されていない（同梱なら allow-list 不要）こと。"""
    siblings = _sibling_script_names()
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts(profile)
        live_edges: set[str] = set()
        for script_rel in shipped:
            src = (ROOT / script_rel).read_text(encoding="utf-8")
            live_edges |= _deps_from_source(src, pathlib.Path(script_rel).name, siblings)
        for dep in INTENTIONAL_UNSHIPPED.get(name, {}):
            assert dep in live_edges, (
                f"stale allow-list: INTENTIONAL_UNSHIPPED['{name}']['{dep}'] は "
                f"{name} の shipped script から参照されていない。削除せよ。"
            )
            assert dep not in shipped, (
                f"redundant allow-list: [{name}] {dep} は実際に同梱されている。"
                f"allow-list エントリは不要なので削除せよ。"
            )


# ---- 横断検査本体（現存 2 穴を恒久封鎖） ----

def test_every_profile_is_referentially_self_contained():
    siblings = _sibling_script_names()
    failures: list[str] = []
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts(profile)
        allow = INTENTIONAL_UNSHIPPED.get(name, {})
        for script_rel in sorted(shipped):
            src = (ROOT / script_rel).read_text(encoding="utf-8")
            edges = _deps_from_source(src, pathlib.Path(script_rel).name, siblings)
            for dep in _violations(shipped, edges, allow):
                failures.append(
                    f"[{name}] {script_rel} は {dep} を参照するが、{name}.json の "
                    f"required/recommended に同梱されておらず INTENTIONAL_UNSHIPPED['{name}'] "
                    f"にも未登録。対処: {dep} を profile に同梱する OR 理由付きで allow-list する。"
                )
    assert not failures, "参照整合性違反:\n" + "\n".join(failures)


# ===========================================================================
# iter49: skill(.md) → script 参照整合性
# ---------------------------------------------------------------------------
# skills は templates 変種を持たず verbatim install される（commands は
# setup.sh:resolve_source で templates/commands/ の scaffold-safe 版に差し替わるが
# skills にその仕組みは無い）。よって shipped skill が未同梱 script を参照すると
# install 後にサイレントに inert 化する。実穴: full の aegis-brainstorm/bug-diagnosis が
# scripts/update-task.sh を無条件参照（task_size 設定＝gate routing の中核）。
# 検査範囲は skill→scripts/*.(py|sh)。guard heuristic は持たず、guarded-optional な
# 参照は理由付き allow-list で明示する（前段 .py 検査と同じ哲学）。
# ===========================================================================

# scripts/<name>.(py|sh) トークン。hooks/lib/*.sh は別 prefix で自然に対象外
# （setup.sh:copy_hooks が wholesale install するため常在＝検査不要）。
# 検出境界（既知）: コメント/URL/散文中の `scripts/x.py` も拾う（過検出側＝fail-closed。
# 意図的に optional な参照は INTENTIONAL_UNSHIPPED_SKILL で理由付き解消する）。`scripts/` 直下の
# flat 名のみ対象で `scripts/sub/x.py` のネストは非マッチ（現状 scripts は flat）。
_SKILL_SCRIPT_RE = re.compile(r"scripts/[A-Za-z0-9_.-]+\.(?:py|sh)")

# 意図的非同梱の skill→script allow-list（理由非空必須・rot 検知あり）。
# update-task.sh 同梱で実穴は解消＝現状エントリ無し（将来の guarded-optional ref 用受け皿）。
INTENTIONAL_UNSHIPPED_SKILL: dict[str, dict[str, str]] = {}


def _skill_script_edges(md_text: str) -> set[str]:
    """skill の .md 本文が参照する scripts/<name>.(py|sh) の集合。"""
    return set(_SKILL_SCRIPT_RE.findall(md_text))


def _shipped_scripts_any(profile: dict) -> set[str]:
    """profile が install で配る scripts/*.(py|sh)（required ∪ recommended）。
    前段 _shipped_scripts は .py 限定だが、skill は update-task.sh のような .sh も
    参照するため両拡張子を対象にする。"""
    entries = list(profile.get("required", [])) + list(profile.get("recommended", []))
    return {
        e
        for e in entries
        if e.startswith("scripts/") and (e.endswith(".py") or e.endswith(".sh"))
    }


def _shipped_skill_docs(profile: dict) -> list[str]:
    """profile が install で配る skill 配下の .md 全て（SKILL.md ＋ platforms.md 等の asset）。
    skills は templates 変種を持たず verbatim install されるため、SKILL.md に限らず
    ディレクトリ内の全 .md が install 実体＝検査対象。"""
    entries = list(profile.get("required", [])) + list(profile.get("recommended", []))
    return [
        e
        for e in entries
        if e.startswith(".claude/skills/") and e.endswith(".md")
    ]


# ---- 単体テスト（skill 抽出ヘルパに歯があること） ----

def test_skill_edges_picks_code_fence_sh():
    md = "Set size:\n```bash\nbash scripts/update-task.sh --size M\n```\n"
    assert _skill_script_edges(md) == {"scripts/update-task.sh"}


def test_skill_edges_picks_inline_py():
    md = "Run `scripts/run-test-strength-drill.py` then report.\n"
    assert "scripts/run-test-strength-drill.py" in _skill_script_edges(md)


def test_skill_edges_ignores_non_scripts_prose():
    # 'scripts/' 接頭辞の無い裸のファイル名言及は拾わない（誤検出抑止）。
    md = "update-task.sh で size を設定する。\n"
    assert _skill_script_edges(md) == set()


def test_skill_edges_ignores_hooks_lib():
    # hooks/lib は別 prefix（wholesale install で常在）＝検査対象外。
    md = "The hook sources hooks/lib/emit.sh at startup.\n"
    assert _skill_script_edges(md) == set()


def test_skill_edges_empty_when_no_ref():
    assert _skill_script_edges("no script references here.\n") == set()


def test_shipped_scripts_helpers_consistent():
    # drift 防止: _shipped_scripts(.py 限定) は _shipped_scripts_any(.py+.sh) の .py 部分集合。
    # 2 ヘルパの「shipped」定義が将来ズレたら検知する。
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        any_py = {e for e in _shipped_scripts_any(profile) if e.endswith(".py")}
        assert _shipped_scripts(profile) == any_py, (
            f"{profile['name']}: _shipped_scripts と _shipped_scripts_any(.py) が不一致"
        )


def test_skill_allowlist_reasons_nonempty():
    for profile_name, deps in INTENTIONAL_UNSHIPPED_SKILL.items():
        for dep, reason in deps.items():
            assert reason and reason.strip(), (
                f"INTENTIONAL_UNSHIPPED_SKILL['{profile_name}']['{dep}'] には非空 reason が必要"
            )


def test_skill_allowlist_no_stale_entries():
    """skill allow-list の rot 検知（参照されない/同梱済みエントリを禁止）。"""
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts_any(profile)
        live_edges: set[str] = set()
        for skill_rel in _shipped_skill_docs(profile):
            md = (ROOT / skill_rel).read_text(encoding="utf-8")
            live_edges |= _skill_script_edges(md)
        for dep in INTENTIONAL_UNSHIPPED_SKILL.get(name, {}):
            assert dep in live_edges, (
                f"stale skill allow-list: [{name}] {dep} はどの shipped skill からも"
                f"参照されない。削除せよ。"
            )
            assert dep not in shipped, (
                f"redundant skill allow-list: [{name}] {dep} は同梱済み。削除せよ。"
            )


# ---- 横断検査本体（skill→script 穴を恒久封鎖） ----

def test_every_profile_skill_script_ref_is_self_contained():
    failures: list[str] = []
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts_any(profile)
        allow = INTENTIONAL_UNSHIPPED_SKILL.get(name, {})
        for skill_rel in sorted(_shipped_skill_docs(profile)):
            md = (ROOT / skill_rel).read_text(encoding="utf-8")
            edges = _skill_script_edges(md)
            for dep in _violations(shipped, edges, allow):
                failures.append(
                    f"[{name}] {skill_rel} は {dep} を参照するが {name}.json の "
                    f"required/recommended に未同梱・INTENTIONAL_UNSHIPPED_SKILL['{name}'] "
                    f"未登録。対処: {dep} を profile 同梱 OR 理由付き allow-list。"
                )
    assert not failures, "skill→script 参照整合性違反:\n" + "\n".join(failures)


def test_update_task_shipped_in_dev_profiles():
    # update-task.sh は required な update-gate.sh の sibling（gate/task の tamper 保護 STATUS 変更対）。
    # full は skill(aegis-brainstorm/bug-diagnosis) が、standard は state-machine.md が update-task.sh を
    # 参照するため両 profile の required に同梱必須。standard 側は skill→script 検査で非強制ゆえ、
    # この明示ガードが rename/削除を捕捉する（盲検2次 F3・grill #3 で指摘された未保護点を封鎖）。
    for name in ("standard", "full"):
        profile = json.loads((PROFILES_DIR / f"{name}.json").read_text(encoding="utf-8"))
        assert "scripts/update-task.sh" in profile.get("required", []), (
            f"{name}.json の required に scripts/update-task.sh が無い（update-gate.sh の sibling・"
            "state-machine.md/skill が参照）"
        )


# ===========================================================================
# iter50: doc(.md) → script 参照整合性（残る install surface）
# ---------------------------------------------------------------------------
# install surface の doc のうち未検査の2種を検査する:
#   - CLAUDE.md      : install 実体は setup.sh:resolve_source で templates/CLAUDE.template.md
#                      へ remap される（dogfood の repo-root CLAUDE.md ではない）。
#   - .claude/rules/*.md : remap なし＝verbatim install。
# guard-only（grill-premise で実穴ゼロを実証）。install 実体では壊れた参照なし＝
#   CLAUDE.md(template) は check_framework_contract.py のみ参照（maintainer 専用の意図的
#   非同梱）／rules/state-machine.md→update-task.sh は full+standard で充足済。本セクションは
#   「全 install surface を1原理で覆う regression guard ＋ maintainer 参照の allow-list 明示化」。
# 対象外: .claude/commands/*.md（resolve_source で scaffold-safe 版へ remap・iter49 で別問題と確定）／
#   .claude/agents/*.md（script 参照ゼロ実証済）。
#
# 重要（iter49 conf8 の教訓）: doc の参照穴判定は **install 実体（resolve_source の source）**を
# 読む。dogfood の repo-root CLAUDE.md を読むと install されない参照を誤検出する。
# ===========================================================================

# doc rel-path → install 実体の template rel-path（明示 map で fail-closed）。
# setup.sh:resolve_source の remap を mirror。setup.sh との同期はアンカーテスト
# test_doc_resolver_matches_setup_sh が強制する（drift は明示 fail）。
_DOC_TEMPLATE_REMAP: dict[str, str] = {
    "CLAUDE.md": "templates/CLAUDE.template.md",
}


def _doc_install_source(rel: str) -> pathlib.Path:
    """doc の profile entry rel-path → install 実体の絶対 Path。

    _DOC_TEMPLATE_REMAP にあれば template 実体、無ければ verbatim（ROOT/rel）。
    明示 map にする理由＝setup.sh パース失敗時に空 map へ degrade して false-clean に
    なる fail-open（D5 型）を避ける。検査本体は本 map を使い parse に依存しない。
    """
    return ROOT / _DOC_TEMPLATE_REMAP.get(rel, rel)


def _shipped_doc_surfaces(profile: dict) -> list[str]:
    """profile が install で配る install-surface doc（required ∪ recommended・順序保持）。

    対象は CLAUDE.md と .claude/rules/*.md のみ。.claude/commands/*.md（scaffold-safe
    remap・別問題）・.claude/agents/*.md（script 参照ゼロ）・.claude/skills/*.md
    （iter49 が別途検査）は除外。
    """
    entries = list(profile.get("required", [])) + list(profile.get("recommended", []))
    return [
        e
        for e in entries
        if e == "CLAUDE.md" or (e.startswith(".claude/rules/") and e.endswith(".md"))
    ]


# 意図的非同梱の doc→script allow-list（理由非空必須・rot 検知あり）。
# 注意（cross-ref）: 同名 scripts/check_framework_contract.py は前段 .py 層の
# INTENTIONAL_UNSHIPPED['full'] にも登場するが、そちらの referrer は status_doctor.py
# （full のみ・実行依存）。本 doc 層の referrer は CLAUDE.md(template) の**記述的 prose**
# （実行指示ではない）で、CLAUDE.md は全 profile 同梱のため3 profile 全てに必要。
# referrer/scope が異なる同一 script の別宣言＝重複ではない。
_INTENTIONAL_DOC_REASON = (
    "install 実体 CLAUDE.md（templates/CLAUDE.template.md L41「Agent model/effort is "
    "pinned ... (enforced by scripts/check_framework_contract.py); applies once agents "
    "are installed (the full profile)」）の**記述的 provenance**＝どこで pin が enforce "
    "されるかの出所情報で、実行指示ではない。check_framework_contract は maintainer 専用で "
    "依存閉包 platform_manifest+context_budget を install に引き込まないため意図的非同梱"
    "（iter48 で確定）。.py 層 allow-list とは referrer（status_doctor.py vs CLAUDE.md prose）"
    "が異なる別宣言。案Y（template から参照除去）は有用な出所情報を削るため不採用。"
)
INTENTIONAL_UNSHIPPED_DOC: dict[str, dict[str, str]] = {
    "minimal": {"scripts/check_framework_contract.py": _INTENTIONAL_DOC_REASON},
    "standard": {"scripts/check_framework_contract.py": _INTENTIONAL_DOC_REASON},
    "full": {"scripts/check_framework_contract.py": _INTENTIONAL_DOC_REASON},
}


# doc 本文の script 参照抽出は skill 面と同一原理（共有 _SKILL_SCRIPT_RE）。新ロジックを
# 増やさず別名で呼び出し側を自己説明化する（grill-code 🟡: doc に skill 名の関数を当てると
# 読み手が二度見する）。
_doc_script_edges = _skill_script_edges


# setup.sh:resolve_source の case を抽出する正規表現。`)` と `echo` の間は `[^"]*?`
# （引用符を含まない非貪欲）＝コメント行を飲み込みつつ次 case の "label" を越えない。
# grill-plan ①: 素朴な `\s+` だとコメント挟みの case を取りこぼし、将来の rules remap が
# parse から漏れてアンカーが fail-open する。コメント耐性で fail-closed を保つ。
_SETUP_CASE_RE = re.compile(r'"([^"]+)"\)[^"]*?echo\s+"\$FRAMEWORK_ROOT/([^"]+)"')


def _setup_resolve_remap(setup_src: str) -> dict[str, str]:
    """setup.sh:resolve_source の case ブロックから rel→template-rel の remap を抽出。

    `case "$rel_path" in` 〜 `esac` に限定（ブロック外の echo を誤抽出しない）。
    parse 失敗（構文変更）なら空 dict を返し、呼び出し側アンカーの `assert "CLAUDE.md"
    in remap` が明示 fail する（fail-closed）。
    """
    m = re.search(r'case\s+"\$rel_path"\s+in(.*?)\besac\b', setup_src, re.DOTALL)
    body = m.group(1) if m else ""
    # bash の行コメント（`# ...`）を除去してから抽出する。コメント中に `"` があると
    # `[^"]*?` がそこで止まり case を取りこぼす（reviewer-testing F1）。case label と echo は
    # 別行なのでコメント行除去後も隣接は崩れない（残る空行/空白は [^"]*? が飲む）。
    body = re.sub(r'(?m)^[ \t]*#.*$', '', body)
    return {rel: tpl for rel, tpl in _SETUP_CASE_RE.findall(body)}


# ---- 単体テスト（resolver） ----

def test_doc_source_claude_is_template():
    # CLAUDE.md の install 実体は templates/CLAUDE.template.md（remap）。
    assert _doc_install_source("CLAUDE.md") == ROOT / "templates" / "CLAUDE.template.md"


def test_doc_source_rules_is_verbatim():
    # rules は remap なし＝verbatim install。
    assert (
        _doc_install_source(".claude/rules/state-machine.md")
        == ROOT / ".claude" / "rules" / "state-machine.md"
    )


def _all_doc_surfaces() -> set[str]:
    """全 profile が install する doc surface の和集合。"""
    surfaces: set[str] = set()
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        surfaces |= set(_shipped_doc_surfaces(profile))
    return surfaces


def test_doc_resolver_matches_setup_sh():
    """アンカー: resolver（_DOC_TEMPLATE_REMAP）が setup.sh:resolve_source と同期している
    ことを強制する。setup.sh に rules remap を足す/CLAUDE.md の template パスを変える/
    コメント付き remap を追加する、のいずれでも本テストが**明示 fail** し、resolver の
    更新を強制する（install 実体とのズレ＝fail-open を封鎖）。"""
    setup_src = (ROOT / "bin" / "setup.sh").read_text(encoding="utf-8")
    remap = _setup_resolve_remap(setup_src)
    # parse 健全性（構文変更で空 dict に degrade したら明示 fail）。
    assert "CLAUDE.md" in remap, (
        "setup.sh:resolve_source の parse が CLAUDE.md remap を見つけられない"
        "（case 構文変更の可能性＝_setup_resolve_remap を更新せよ）"
    )
    surfaces = _all_doc_surfaces()
    for rel in sorted(surfaces):
        expected = ROOT / remap.get(rel, rel)
        assert _doc_install_source(rel) == expected, (
            f"resolver と setup.sh が doc '{rel}' で不一致: "
            f"resolver={_doc_install_source(rel)} vs setup.sh={expected}。"
            "_DOC_TEMPLATE_REMAP を setup.sh:resolve_source に合わせよ。"
        )
    # dead-key 禁止: _DOC_TEMPLATE_REMAP の各 key は実 doc surface であること。
    for key in _DOC_TEMPLATE_REMAP:
        assert key in surfaces, (
            f"dead _DOC_TEMPLATE_REMAP key: '{key}' はどの profile の doc surface でもない。削除せよ。"
        )


# ---- 単体テスト（_shipped_doc_surfaces） ----

def test_shipped_doc_surfaces_selects_claude_and_rules():
    profile = {
        "required": ["CLAUDE.md", ".claude/rules/state-machine.md", "scripts/check_status.py"],
        "recommended": [
            ".claude/rules/routing.md",
            ".claude/commands/status.md",
            ".claude/agents/planner.md",
            ".claude/skills/tdd/SKILL.md",
        ],
    }
    assert _shipped_doc_surfaces(profile) == [
        "CLAUDE.md",
        ".claude/rules/state-machine.md",
        ".claude/rules/routing.md",
    ]


def test_shipped_doc_surfaces_excludes_commands_agents_skills():
    profile = {
        "required": [".claude/commands/gate.md"],
        "recommended": [".claude/agents/qa.md", ".claude/skills/deploy/platforms.md"],
    }
    assert _shipped_doc_surfaces(profile) == []


# ---- 単体テスト（doc edge 抽出＝既存 _skill_script_edges の doc 適用を固定） ----
# 新規関数は起こさない（YAGNI）。共有 _SKILL_SCRIPT_RE が doc 面も指すことを固定し、
# 将来 regex 変更で doc 抽出が壊れたら検知する。

def test_doc_edge_picks_check_contract_from_prose():
    # CLAUDE.template.md L41 想定の散文 provenance から script を拾う。
    md = "Agent model/effort is pinned (enforced by `scripts/check_framework_contract.py`).\n"
    assert "scripts/check_framework_contract.py" in _doc_script_edges(md)


# ---- 単体テスト（setup.sh remap parse の歯＝コメント耐性） ----

def test_setup_parse_extracts_single_line_case():
    src = (
        'resolve_source() {\n'
        '  case "$rel_path" in\n'
        '    "CLAUDE.md")  echo "$FRAMEWORK_ROOT/templates/CLAUDE.template.md"; return ;;\n'
        '  esac\n'
        '}\n'
    )
    assert _setup_resolve_remap(src) == {"CLAUDE.md": "templates/CLAUDE.template.md"}


def test_setup_parse_tolerates_comment_between_case_and_echo():
    # grill-plan ①: `)` と `echo` の間にコメント行がある case を取りこぼすと、将来の
    # rules remap が parse から漏れてアンカーが fail-open する。コメント耐性を固定する。
    src = (
        'case "$rel_path" in\n'
        '    ".claude/rules/state-machine.md")\n'
        '      # Scaffold-safe variant: degrades gracefully.\n'
        '      echo "$FRAMEWORK_ROOT/templates/rules/state-machine.md"; return ;;\n'
        'esac\n'
    )
    assert _setup_resolve_remap(src) == {
        ".claude/rules/state-machine.md": "templates/rules/state-machine.md"
    }


def test_setup_parse_tolerates_quoted_comment_in_case():
    # reviewer-testing F1: コメント中に `"` が含まれても case を取りこぼさない。
    # 素の `[^"]*?` はコメント内の `"` で止まり取りこぼす（fail-closed だが分かりにくい）。
    # 行コメントを事前除去して robustness を上げる。
    src = (
        'case "$rel_path" in\n'
        '    "CLAUDE.md")\n'
        '      # see "templates/CLAUDE.template.md" for context\n'
        '      echo "$FRAMEWORK_ROOT/templates/CLAUDE.template.md"; return ;;\n'
        'esac\n'
    )
    assert _setup_resolve_remap(src) == {"CLAUDE.md": "templates/CLAUDE.template.md"}


def test_setup_parse_ignores_outside_case_block():
    # case ブロック外の echo "$FRAMEWORK_ROOT/..." は拾わない（誤抽出抑止）。
    src = (
        'copy_file "$x" "$FRAMEWORK_ROOT/scripts/foo.py"\n'
        'case "$rel_path" in\n'
        '    "CLAUDE.md") echo "$FRAMEWORK_ROOT/templates/CLAUDE.template.md"; return ;;\n'
        'esac\n'
    )
    assert _setup_resolve_remap(src) == {"CLAUDE.md": "templates/CLAUDE.template.md"}


# ---- allow-list governance（reason 非空＋rot 検知） ----

def test_doc_allowlist_reasons_nonempty():
    for profile_name, deps in INTENTIONAL_UNSHIPPED_DOC.items():
        for dep, reason in deps.items():
            assert reason and reason.strip(), (
                f"INTENTIONAL_UNSHIPPED_DOC['{profile_name}']['{dep}'] には非空 reason が必要"
            )


def test_doc_allowlist_no_stale_or_redundant():
    """doc allow-list の rot 検知。各エントリは (a) その profile の shipped doc surface が
    実際に参照する辺であり、(b) その profile に未同梱（同梱なら allow-list 不要）であること。"""
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts_any(profile)
        live_edges: set[str] = set()
        for rel in _shipped_doc_surfaces(profile):
            text = _doc_install_source(rel).read_text(encoding="utf-8")
            live_edges |= _doc_script_edges(text)
        for dep in INTENTIONAL_UNSHIPPED_DOC.get(name, {}):
            assert dep in live_edges, (
                f"stale doc allow-list: [{name}] {dep} はどの shipped doc surface からも"
                f"参照されない。削除せよ。"
            )
            assert dep not in shipped, (
                f"redundant doc allow-list: [{name}] {dep} は同梱済み。削除せよ。"
            )


# ---- 横断検査本体（doc→script 穴を恒久封鎖） ----

def test_every_profile_doc_script_ref_is_self_contained():
    """各 profile × shipped doc surface を **install 実体**で読み、参照 script が
    「同梱 ∨ 理由付き INTENTIONAL_UNSHIPPED_DOC」であることを検査する。"""
    failures: list[str] = []
    for profile_path in sorted(PROFILES_DIR.glob("*.json")):
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        name = profile["name"]
        shipped = _shipped_scripts_any(profile)
        allow = INTENTIONAL_UNSHIPPED_DOC.get(name, {})
        for rel in sorted(_shipped_doc_surfaces(profile)):
            source = _doc_install_source(rel)
            edges = _doc_script_edges(source.read_text(encoding="utf-8"))
            for dep in _violations(shipped, edges, allow):
                failures.append(
                    f"[{name}] {rel}（install 実体 {source.relative_to(ROOT)}）は {dep} を "
                    f"参照するが {name}.json の required/recommended に未同梱・"
                    f"INTENTIONAL_UNSHIPPED_DOC['{name}'] 未登録。対処: {dep} を profile 同梱 "
                    "OR 理由付き allow-list。"
                )
    assert not failures, "doc→script 参照整合性違反:\n" + "\n".join(failures)

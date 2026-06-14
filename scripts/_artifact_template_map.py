"""Single source of truth: artifact path → template path mapping.

K-12 (v1.6.2 / JNY-07): the install-time template chosen for an artifact
under docs/requirements / docs/handover / docs/translation / docs/qa-reports
is non-trivially named:

  docs/handover/TO-DEV.md       → templates/HANDOVER-TO-DEV.template.md
  docs/translation/mapping.md   → templates/TRANSLATION-MAPPING.template.md

A naive `pathlib.Path(p).stem` mapping returns `TO-DEV` and `mapping` and
produces broken parity tests / deny messages. Use this explicit dict
everywhere — check_status.py for deny messages, bin/setup.sh for the
install resolver, and tests/test_profile_checker_parity.py for the
double-checked contract.
"""

from __future__ import annotations

# Order matches the gate boundaries: CLIENT_GATE_ARTIFACTS in check_status.py
# starts with PRD and ends with TRANSLATION-MAPPING; DEV_GATE_ARTIFACTS
# (currently informal) covers PLAN through DEPLOY-CHECKLIST. Keys must
# stay sorted by gate phase to keep deny messages readable.

ARTIFACT_TO_TEMPLATE: dict[str, str] = {
    # Client gate
    "docs/requirements/PRD.md":        "templates/PRD.template.md",
    "docs/requirements/SCOPE.md":      "templates/SCOPE.template.md",
    "docs/requirements/NFR.md":        "templates/NFR.template.md",
    "docs/requirements/ACCEPTANCE.md": "templates/ACCEPTANCE.template.md",
    "docs/handover/TO-DEV.md":         "templates/HANDOVER-TO-DEV.template.md",
    "docs/handover/CHANGES.md":        "templates/CHANGES.template.md",
    "docs/translation/mapping.md":     "templates/TRANSLATION-MAPPING.template.md",
    # Dev gate boundary / handover
    "docs/handover/TO-CLIENT.md":      "templates/HANDOVER-TO-CLIENT.template.md",
    # Dev gate artifacts produced through brainstorm / plan / review / qa /
    # security / deploy phases. Not all are gate-mandatory but every onboarding
    # / cheatsheet step references them, so install must ship the templates.
    "docs/specs/SPEC.md":              "templates/SPEC.template.md",
    "docs/plans/PLAN.md":              "templates/PLAN.template.md",
    "docs/plans/BRAINSTORM-RECORD.md": "templates/BRAINSTORM-RECORD.template.md",
    "docs/qa-reports/QA-REPORT.md":    "templates/QA-REPORT.template.md",
    "docs/qa-reports/REVIEW.md":       "templates/REVIEW.template.md",
    "docs/qa-reports/SECURITY-REVIEW.md": "templates/SECURITY-REVIEW.template.md",
    "docs/qa-reports/DEPLOY-CHECKLIST.md": "templates/DEPLOY-CHECKLIST.template.md",
    "docs/qa-reports/VERIFICATION.md": "templates/VERIFICATION.template.md",
    "docs/qa-reports/UAT-RESULTS.md":  "templates/UAT-RESULTS.template.md",
    # Operational / maintenance artifacts referenced by the onboarding cheatsheet
    "docs/handover/MANUAL.md":         "templates/MANUAL.template.md",
    "docs/handover/RUNBOOK.md":        "templates/RUNBOOK.template.md",
    # Decision records and second-opinion (3-failure stop rule in CLAUDE.md)
    "docs/decisions/DECISION.md":      "templates/DECISION.template.md",
    "docs/second-opinion.md":          "templates/SECOND-OPINION.template.md",
    # Client context (Client phase)
    "docs/client/context.md":          "templates/CLIENT-CONTEXT.template.md",
    "docs/client/glossary.md":         "templates/CLIENT-GLOSSARY.template.md",
    "docs/client/open-questions.md":   "templates/CLIENT-OPEN-QUESTIONS.template.md",
}


def template_for(artifact_rel: str) -> str | None:
    """Return the template path for a given artifact path, or None."""
    return ARTIFACT_TO_TEMPLATE.get(artifact_rel)

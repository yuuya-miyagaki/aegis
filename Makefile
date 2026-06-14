.PHONY: example tighten-budgets

# Regenerate the browsable example mirror from the framework root.
# Run after editing any control file under hooks/, scripts/, or .claude/.
# Verification lives in check_reference_drift.py (mirror identity).
example:
	python3 scripts/sync_example_mirror.py

# Tighten-only ratchet for context budgets: lower each skill/rule budget to its
# current word count (never raises). Run after trimming a skill/rule to lock the
# gain in. Raising a budget is a manual edit of scripts/context-budgets.json.
tighten-budgets:
	python3 scripts/context_budget.py --tighten

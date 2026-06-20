.PHONY: tighten-budgets

# Tighten-only ratchet for context budgets: lower each skill/rule budget to its
# current word count (never raises). Run after trimming a skill/rule to lock the
# gain in. Raising a budget is a manual edit of scripts/context-budgets.json.
tighten-budgets:
	python3 scripts/context_budget.py --tighten

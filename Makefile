.PHONY: example

# Regenerate the browsable example mirror from the framework root.
# Run after editing any control file under hooks/, scripts/, or .claude/.
# Verification lives in check_reference_drift.py (mirror identity).
example:
	python3 scripts/sync_example_mirror.py

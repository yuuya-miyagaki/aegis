#!/usr/bin/env bash
# Detection PATTERN DATA for Aegis hooks. Single source of truth for the
# destructive-command patterns consumed by check-destructive.sh.
# Source: source "$(dirname "$0")/lib/patterns.sh"
#
# NOTE: secret-file patterns intentionally live in check-secrets.sh, NOT here.
# That hook matches the same credential files in four context-specific forms
# (command-text regex, find -name globs, basename case, staged-path regex) whose
# nuances (anchors, id_rsa* vs id_rsa\b vs id_rsa.pub) do not reduce to a single
# glob array without losing coverage. Centralizing them is deferred until a real
# second consumer (e.g. a drift check) needs the list — see the Foundation plan.

# Destructive patterns matched against the LOWER-cased command ($CMD_LOWER).
AEGIS_DESTRUCTIVE_LOWER_REGEX=('drop\s+(table|database)' '\btruncate\b')
AEGIS_DESTRUCTIVE_LOWER_WARN=(
  "Destructive: SQL DROP detected."
  "Destructive: SQL TRUNCATE detected."
)

# Destructive patterns matched against the RAW command ($CMD).
# (rm -r has a safe-targets exception and is handled directly in the hook.)
AEGIS_DESTRUCTIVE_CMD_REGEX=(
  'git\s+push\s+.*(-f\b|--force)'
  'git\s+reset\s+--hard'
  'git\s+(checkout|restore)\s+\.'
  'git\s+branch\s+(-[a-zA-Z]*[dD]\b|--delete)'
  'git\s+(checkout|restore)\s+--\s+'
  'git\s+clean\s+.*-f'
  'git\s+filter-branch'
  'git\s+update-ref\s+-d'
  'git\s+reflog\s+expire.*--expire=now'
  'npx\s+rimraf'
  'find\s+.+\s+-delete'
)
AEGIS_DESTRUCTIVE_CMD_WARN=(
  "Destructive: git force-push rewrites remote history."
  "Destructive: git reset --hard discards uncommitted changes."
  "Destructive: discards all uncommitted working tree changes."
  "Destructive: branch deletion."
  "Destructive: discards changes to specific files."
  "Destructive: git clean removes untracked files."
  "Destructive: git filter-branch rewrites repository history (irreversible)."
  "Destructive: git update-ref -d deletes a ref permanently."
  "Destructive: git reflog expire --expire=now wipes reflog (no recovery)."
  "Destructive: npx rimraf bulk-deletes files recursively."
  "Destructive: find -delete bulk-deletes matching files."
)

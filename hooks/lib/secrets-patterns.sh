#!/usr/bin/env bash
# Single source of truth for HIGH-RISK credential file patterns consumed by
# check-secrets.sh. C-9 (full-review-2026-06-12) found these patterns
# duplicated in 4 forms (command-text regex / case glob / find -name / staged
# regex), each with subtle anchor differences (id_rsa\b vs id_rsa* vs
# id_(rsa|...)). Centralizing keeps "new credential type → one place" the rule.
#
# Source: source "$(dirname "$0")/lib/secrets-patterns.sh"
#
# These variables are bash-only (no python parity consumer today). \b is OK
# here because grep -E supports it on both BSD and GNU; if a python consumer
# is added later, fall back to (^|[^A-Za-z0-9_]) / ($|[^A-Za-z0-9_]) per the
# patterns.sh convention.
#
# Coverage (v1.6.1): PEM certificates / SSH private keys (RSA/ed25519/ecdsa)
# and their .pub counterparts where the family glob covers them / Google-Cloud
# style service-account*.json / generic credentials*.json files.

# --- Form 1: command-text regex ---
# Consumed by `printf '%s' "$CMD" | grep -qE "git\\s+add\\s+.*(${AEGIS_HIGH_RISK_RE})"`
# in check-secrets.sh. Word-boundary anchors prevent over-match on substrings
# like "id_rsa_old" being matched only via the family glob in form 3.
AEGIS_HIGH_RISK_RE='\.pem(\b|$)|id_(rsa|ed25519|ecdsa)(\b|$)|credentials.*\.json|service-account.*\.json'

# --- Form 2: basename case glob ---
# Consumed by `case "$(basename "$f")" in ${AEGIS_HIGH_RISK_CASE_GLOB}) ...`
# Bash case glob, NOT a regex. The .pub variants are listed explicitly because
# they are NOT secrets per se but accompany the private key and broad globbing
# (id_rsa*) might over-match unrelated files like id_rsa.txt. Pin the .pub
# variants here for clarity.
AEGIS_HIGH_RISK_CASE_GLOB='*.pem|id_rsa|id_rsa.pub|id_ed25519|id_ed25519.pub|id_ecdsa|id_ecdsa.pub|*credentials*.json|service-account*.json'

# --- Form 3: find -name globs (array) ---
# Consumed by `find "$ROOT" \\( -name "${AEGIS_HIGH_RISK_FIND_NAMES[0]}" ... \\)`.
# The id_rsa* family glob here intentionally catches id_rsa.pub etc. — narrower
# pinning happens at form 2 (basename case) which is what actually approves the
# match. Form 3 is the over-fetch step; form 2 is the gate.
AEGIS_HIGH_RISK_FIND_NAMES=(
  '*.pem'
  'id_rsa*'
  'id_ed25519*'
  'id_ecdsa*'
  '*credentials*.json'
  'service-account*.json'
)

# --- Form 4: staged-path regex (full path anchors) ---
# Consumed by `git diff --cached --name-only | grep -E "${AEGIS_HIGH_RISK_STAGED_RE}"`.
# Different anchors than form 1: this matches end-of-path ($) and start-of-segment
# ((^|/)) because staged names are paths, not free-form command text. The
# id_rsa(.pub)? optional captures private+public together at the path tail.
AEGIS_HIGH_RISK_STAGED_RE='\.pem$|(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$|credentials.*\.json$|service-account.*\.json$'

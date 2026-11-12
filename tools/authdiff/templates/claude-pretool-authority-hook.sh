#!/usr/bin/env bash
# Claude Code PreToolUse hook wrapper → Python JSON parser (fail-closed).
# Install: register as PreToolUse for Edit|Write|Bash tools.
# Requires: authdiff on PATH; a prior `authdiff lock` (repo) or `authdiff lock --home`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/claude_pretool_authority_hook.py" "$@"

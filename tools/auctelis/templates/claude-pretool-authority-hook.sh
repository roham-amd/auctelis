#!/usr/bin/env bash
# Claude Code PreToolUse hook wrapper → Python JSON parser (fail-closed).
# Install: register as PreToolUse for Edit|Write|Bash tools.
# Requires: auctelis on PATH; a prior `auctelis lock` (repo) or `auctelis lock --home`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/claude_pretool_authority_hook.py" "$@"

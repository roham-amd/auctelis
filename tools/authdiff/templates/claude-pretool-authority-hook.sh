#!/usr/bin/env bash
# Claude Code PreToolUse hook (~40 lines): hold agent edits to authority files.
# Install: copy into hooks and register as PreToolUse for Edit|Write tools.
# Requires: authdiff on PATH; a prior `authdiff lock` (repo) or `authdiff lock --home`.
set -euo pipefail

TOOL_INPUT="${CLAUDE_TOOL_INPUT:-${1:-}}"
TARGET="${TOOL_INPUT}"
case "$TARGET" in
  *AUTHORITY.lock*|*.authdiff.yml*|*/.mcp.json*|*/mcp.json*|*/hooks.json*|*/SKILL.md*|*/settings.json*)
    ;;
  *)
    exit 0
    ;;
esac

ROOT="${CLAUDE_PROJECT_DIR:-${PWD}}"
LOCK=""
if [[ -f "${ROOT}/AUTHORITY.lock" ]]; then
  LOCK="${ROOT}/AUTHORITY.lock"
elif [[ -f "${HOME}/.authdiff/AUTHORITY.lock" ]]; then
  LOCK="${HOME}/.authdiff/AUTHORITY.lock"
  ROOT="${HOME}"
else
  echo "authdiff: no AUTHORITY.lock — run: authdiff lock   or   authdiff lock --home" >&2
  exit 2
fi

if ! command -v authdiff >/dev/null 2>&1; then
  echo "authdiff: CLI not on PATH; install then re-run the edit." >&2
  exit 2
fi

set +e
authdiff lock --check --lock-file "$LOCK" "$ROOT" >/tmp/authdiff-hook-check.txt 2>&1
code=$?
set -e
if [[ "$code" -eq 0 ]]; then
  exit 0
fi

echo "authdiff: authority drift detected; human approval required before editing:" >&2
echo "  $TARGET" >&2
head -n 20 /tmp/authdiff-hook-check.txt >&2 || true
echo "Approve by updating the lock: authdiff lock --accept-gated --approval @you" >&2
exit 2

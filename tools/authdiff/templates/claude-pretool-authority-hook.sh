#!/usr/bin/env bash
# Claude Code PreToolUse hook: hold agent edits to authority files.
# Install: copy into hooks and register as PreToolUse for Edit|Write|Bash tools.
# Requires: authdiff on PATH; a prior `authdiff lock` (repo) or `authdiff lock --home`.
# Claude Code passes hook input as JSON on stdin (tool_name / tool_input.file_path).
set -euo pipefail

# Prefer stdin JSON (Claude Code); fall back to env / argv for harnesses.
RAW_INPUT=""
if [[ -n "${CLAUDE_TOOL_INPUT:-}" ]]; then
  RAW_INPUT="${CLAUDE_TOOL_INPUT}"
elif [[ -n "${1:-}" ]]; then
  RAW_INPUT="${1}"
elif [[ ! -t 0 ]]; then
  RAW_INPUT="$(cat || true)"
fi

TOOL_NAME=""
TARGET=""
if [[ -n "$RAW_INPUT" ]]; then
  # Extract without requiring jq: prefer JSON fields, else treat as a bare path.
  TOOL_NAME="$(printf '%s' "$RAW_INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
  TARGET="$(printf '%s' "$RAW_INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
  if [[ -z "$TARGET" ]]; then
    TARGET="$(printf '%s' "$RAW_INPUT" | sed -n 's/.*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
  fi
  if [[ -z "$TARGET" && "$RAW_INPUT" != \{* ]]; then
    TARGET="$RAW_INPUT"
  fi
fi

# Fail closed when Edit/Write arrives without a resolvable path.
case "${TOOL_NAME}" in
  Edit|Write|edit|write)
    if [[ -z "$TARGET" ]]; then
      echo "authdiff: PreToolUse ${TOOL_NAME} missing file_path — refusing (fail-closed)." >&2
      exit 2
    fi
    ;;
esac

# Bash redirects / heredocs that touch authority files are also in scope.
case "$TARGET" in
  *AUTHORITY.lock*|*.authdiff.yml*|*/.mcp.json*|*/mcp.json*|*/hooks.json*|*/SKILL.md*|*/settings.json*|*/settings.local.json*|*/.claude/commands/*)
    ;;
  *)
    if [[ "${TOOL_NAME}" == "Bash" || "${TOOL_NAME}" == "bash" ]]; then
      case "$RAW_INPUT" in
        *AUTHORITY.lock*|*.authdiff.yml*|*.mcp.json*|*/mcp.json*|*/hooks.json*|*/SKILL.md*|*/settings.json*|*/.claude/commands/*)
          TARGET="${TARGET:-bash-authority-write}"
          ;;
        *)
          exit 0
          ;;
      esac
    else
      exit 0
    fi
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
  echo "authdiff: no AUTHORITY.lock — human must run: authdiff lock   or   authdiff lock --home" >&2
  exit 2
fi

if ! command -v authdiff >/dev/null 2>&1; then
  echo "authdiff: CLI not on PATH; install then re-run the edit." >&2
  exit 2
fi

HOOK_OUT="$(mktemp -t authdiff-hook.XXXXXX 2>/dev/null || mktemp)"
trap 'rm -f "$HOOK_OUT"' EXIT

set +e
authdiff lock --check --lock-file "$LOCK" "$ROOT" >"$HOOK_OUT" 2>&1
code=$?
set -e

# Pending edit: even a clean lock must not be mutated by the agent without a human.
# Block authority-path edits always; the lock update is a human-run command.
echo "authdiff: authority-bearing path edit requires a human." >&2
echo "  tool=${TOOL_NAME:-unknown} path=${TARGET}" >&2
if [[ "$code" -ne 0 ]]; then
  echo "authdiff: existing authority drift detected:" >&2
  head -n 20 "$HOOK_OUT" >&2 || true
fi
echo "Human: review the change, then update the lock yourself (do not ask the agent)." >&2
exit 2

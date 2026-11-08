# Collection funnel log

Append-only maintainer records. **Empty at start is correct.**

## `INVITATIONS.jsonl`

One JSON object per line. Fields:

```json
{
  "invitation_id": "inv-001",
  "invited_at_utc": "2026-11-04T00:00:00Z",
  "channel": "email|community|direct|other",
  "participant_label": "anonymous-or-org-handle",
  "framework_hint": "unknown|custom|claude-code|cursor|other",
  "status": "invited|responded|declined|package_issued|submitted|withdrawn",
  "notes": "optional"
}
```

Rules:

- Do not invent invitations.
- Update by appending a new line with the same `invitation_id` and a new `status` (append-only history), or keep a single latest-status line — prefer append-only status transitions.
- Invitations never count as external evidence.

## Status command

```bash
uv run authdiff benchmark collection-status
```

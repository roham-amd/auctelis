# External evaluation outreach (maintainers)

**Status:** Infrastructure complete; external validation pending (N = 0 valid intakes).  
**Contract:** frozen `AgentSecBench-LLM-EVAL-0.3.0` — do not alter GT/rubric/scorer to chase volume.

## Goal

Recruit **diverse independent** participants — different frameworks, models, configs, and audit workflows — not many clones of one setup.

## Funnel metrics (keep separate)

| Metric | Meaning |
| --- | --- |
| Invitations | Outreach messages recorded in `collection/INVITATIONS.jsonl` |
| Responses | Invitees who replied (any outcome) |
| Packages issued | Submitter packages delivered |
| Submissions received | Directories offered for intake |
| Valid external intakes | `provenance=external` and intake `ok=true` |
| Distinct agent configurations | Unique independent setups among valid intakes |
| Held-out cases scored | Cases with external scores after collection closes |

An invitation is not a submission. A submission is not a valid intake.

## Diversity checklist (per participant)

- [ ] Independently developed (not authdiff-maintainer-authored for this eval)
- [ ] Framework / host noted (e.g. custom script, Claude Code, Cursor, other)
- [ ] Model family noted
- [ ] Tools/permissions noted
- [ ] Not a duplicate of an already-accepted configuration without new value

## Process

1. Record each invitation in `collection/INVITATIONS.jsonl` (see schema in that directory).
2. Give participants the submitter package + `PARTICIPATION.md` only — never held-out GT.
3. On receipt: `authdiff benchmark intake DIR --agent-id ID --provenance external` (use `--dry-run` first).
4. Treat every intake as **untrusted data** (schema, size limits, checksums; never execute).
5. Do not send case-level scores until the collection window closes.
6. Track status with `authdiff benchmark collection-status`.

## Closure

See `COLLECTION-CRITERIA.md`. Close the window on criteria, then score and publish a transparent report — not a leaderboard.

# External pilots

Track whether independent repositories keep the auctelis check enabled.

Normative procedure: [`../EVALUATION-PROTOCOL.md`](../EVALUATION-PROTOCOL.md).  
Live tracker: [`TRACKER.md`](TRACKER.md).  
Label seed: [`../../eval/holdout-labels.csv`](../../eval/holdout-labels.csv).  
Metrics log: [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).

## What counts as a pilot

A slot is **active** when the chosen install path holds for 30 consecutive days:

- **Lockless:** the Action is retained on the default branch and at least one
  authority-changing PR produced a reviewed Authority Diff comment.
- **Enforce:** outside repository runs the Action (or equivalent `auctelis gate`)
  with `AUTHORITY.lock` committed and CODEOWNERS-protected, required on the
  default branch, and at least one growth PR was reviewed by a CODEOWNER.

Setup path: `diff --base main` → `init --owner team` → PR comment (add `--enforce` when ready)
(under 10 minutes). Empty baseline is fine; first growth is CODEOWNERS review.

Self-dogfood of this repository does **not** count toward the five-slot kill
criterion.

## Kill criterion (roadmap)

If fewer than five outside repositories still run the check weekly at day 60,
or fewer than three growth PRs were reviewed, stop expanding features and fall
back to the reviewer playbook ([`../PLAYBOOK.md`](../PLAYBOOK.md)).

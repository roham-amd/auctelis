# External pilots

Track whether independent repositories keep the auctelis check enabled.

Normative procedure: [`../EVALUATION-PROTOCOL.md`](../EVALUATION-PROTOCOL.md).  
Live tracker: [`TRACKER.md`](TRACKER.md).  
Label seed: [`../../eval/holdout-labels.csv`](../../eval/holdout-labels.csv).  
Metrics log: [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).

## What counts as a pilot

A slot is **active** when either path holds for 30 consecutive days:

- **Host path:** an outside developer runs `auctelis watch --seal` and
  `auctelis watch --arm`, and `auctelis hook status` still reports `firing` at
  week 4.
- **Team path:** an outside repository runs the Action or an equivalent
  `auctelis gate` check, with `AUTHORITY.lock` committed and CODEOWNERS-protected,
  required on the default branch.

Self-dogfood of this repository does **not** count toward the five-slot kill
criterion.

## Kill criterion (roadmap)

If fewer than five outside hosts or repositories still answer at day 60, stop
expanding scanner features and fall back to the reviewer playbook
([`../PLAYBOOK.md`](../PLAYBOOK.md)).

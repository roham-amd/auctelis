# External pilots

Track whether independent repositories keep the auctelis check enabled.

Normative procedure: [`../EVALUATION-PROTOCOL.md`](../EVALUATION-PROTOCOL.md).  
Live tracker: [`TRACKER.md`](TRACKER.md).  
Label seed: [`../../eval/holdout-labels.csv`](../../eval/holdout-labels.csv).  
Metrics log: [`../../eval/pilot-metrics.csv`](../../eval/pilot-metrics.csv).

## What counts as a pilot

A slot is **active** only when:

1. An outside repository (not `roham-amd/auctelis`) installs the Action or equivalent `auctelis gate` CI check.
2. `AUTHORITY.lock` is committed and CODEOWNERS-protected.
3. The check remains required on the default branch for **30 consecutive days**.

Self-dogfood of this repository does **not** count toward the five-repo kill criterion.

## Kill criterion (roadmap)

If fewer than five outside repositories keep the check enabled by day 60, stop
expanding scanner features and fall back to the reviewer playbook
([`../PLAYBOOK.md`](../PLAYBOOK.md)).

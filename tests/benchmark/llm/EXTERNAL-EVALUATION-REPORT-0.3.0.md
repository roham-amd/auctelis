# AgentSecBench-LLM external evaluation report (dataset 0.3.0)

**Contract:** `AgentSecBench-LLM-EVAL-0.3.0`  
**Report date:** 2026-11-04 (living; zeros until evidence changes)  
**Product line:** authdiff 3.3.1 / authdiff 0.6.1  
**Collection:** open (see `COLLECTION-CRITERIA.md`)  
**Invokes models:** No  

## Conditions

- Dataset **0.3.0**, rubric **1.0.0**, submission schema **1.0**, frozen evaluation contract.
- Default evaluation split: **held_out** (LLM-004, LLM-005, LLM-006, LLM-008).
- Scoring dimensions: detection, evidence, severity, unsupported claims — reported separately.
- Ranking / leaderboard: **not allowed**.

## Funnel (honest)

| Metric | Value |
| --- | --- |
| Invitations recorded | **0** |
| Responses | **0** |
| Packages issued | **0** |
| Submissions received | **0** |
| Valid external intakes (`provenance=external`, `ok=true`) | **0** |
| Distinct agent configurations | **0** |
| Held-out cases scored from external evidence | **0** |

No independently developed agent audits have been received. Collection infrastructure is ready; external validation is pending.

### Explicitly excluded (not external evidence)

- Maintainer pilots under `submissions/pilots/`
- Sample fixtures under `submissions/sample-*`
- Schema templates under `submissions/templates/`

## Results

With **N = 0** external submissions, there are no detection, evidence, severity, or unsupported-claim aggregates to report for external agents.

Pilot and sample scores remain available for scorer regression only and are **not** cited here as credibility evidence.

## Reviewer disagreements

None applicable (no external submissions to adjudicate).

## Limitations

- Dataset size remains eight cases (four held-out).
- Offline submission scoring is **not** live model-provider evaluation.
- Zero external submissions means this report documents **process readiness**, not agent comparative quality.
- Held-out ground truth was not shared with submitters; case-level scoring feedback was not issued during collection.

## Candidate improvements (deferred)

See `CANDIDATE-IMPROVEMENTS.md`. No silent edits were made to frozen 0.3.0 ground truth or scoring criteria.

## Conclusion

The evaluation contract, submitter package, intake vault, and reporting path are in place. Credible external evaluation awaits genuine independent submissions. Until then, authdiff correctly reports **zero external evidence** rather than substituting templates or pilots.

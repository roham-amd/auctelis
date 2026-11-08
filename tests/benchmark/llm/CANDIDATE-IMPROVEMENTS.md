# Candidate improvements (post–dataset 0.3.0)

Record defects discovered during **frozen** evaluation here.  
Do **not** silently edit 0.3.0 GT, rubric, or scorer criteria mid-collection.

| ID | Area | Observation | Proposed for | Status |
| --- | --- | --- | --- | --- |
| CI-001 | Matching | Title Jaccard matching is coarse for near-paraphrases | dataset/rubric ≥ 0.4.0 | open |
| CI-002 | Schema | Optional `tools_available` / `permissions` fields would improve interpretability | submission schema ≥ 1.1 | open |
| CI-003 | Coverage | Eight cases remain too few for rankings | dataset ≥ 0.4.0 | open |
| CI-004 | Review | Expand independent review beyond sample adjudications | process | open |

When promoting items, cut a new `EVALUATION-CONTRACT-*` and dataset version.

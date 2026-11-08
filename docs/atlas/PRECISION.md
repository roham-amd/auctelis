# Atlas precision ledger (template)

> Measurements go here after blind review. Targets are not measurements.

| Rule | Evidence strength | Labeled N | TP | FP | Precision | Default severity after review |
| --- | --- | --- | ---: | ---: | ---: | --- |
| AUTHDIFF-RULE-001 | mixed | 0 | — | — | — | keep |
| AUTHDIFF-RULE-002 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-003 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-004 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-005 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-006 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-007 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-008 | TYPE_DEFAULT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-009 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-010 | NAME_MARKER / INFERRED_HINT | 0 | — | — | — | NAME_MARKER capped LOW |
| AUTHDIFF-RULE-011 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-012 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-013 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-014 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-015 | LITERAL_CONFIG | 0 | — | — | — | keep |
| AUTHDIFF-RULE-016 | INFERRED_HINT | 0 | — | — | — | keep |
| AUTHDIFF-RULE-017 | LITERAL_CONFIG | 0 | — | — | — | keep |

**Policy:** HIGH/CRITICAL require `LITERAL_CONFIG` evidence unless a published
precision study justifies otherwise. Target: ≥90% precision on ≥100 blind-labeled
High/Critical findings.

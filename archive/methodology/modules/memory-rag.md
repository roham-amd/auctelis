# Module — Memory / RAG

Assess persistent memory, retrieval stores, and RAG pipelines connected to agents.

## Security questions

1. Who can write to memory, and is write authorization per-tenant?
2. Can retrieved documents inject instructions that influence tool use?
3. Are retention, deletion, and export controls defined and evidenced?
4. Does retrieval bypass the same authorization checks as direct tool access?
5. Can one session poison memory consumed by another principal?

## Evidence expectations

| Claim | Minimum evidence |
| --- | --- |
| Store identity | Exact path, endpoint, or product + version |
| Tenant isolation | Configuration or RUNTIME proof of separation |
| Poisoning resistance | Instruction/document trust boundary design |
| Retention | Policy + implementation evidence |

Mark unverified isolation as `NOT VERIFIED`, never as safe.

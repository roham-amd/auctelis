# Module — Models / providers

Assess model providers as part of the trust boundary.

## Security questions

1. Exact provider identity and endpoint (not marketing names).
2. Model/version pin vs floating “latest”.
3. Data retention / training-use terms for prompts and tool results.
4. Whether tool-call arguments from the model are treated as authoritative.
5. Fallback models that change capability or logging posture.

## Finding discipline

- Provider trust is not a substitute for host authorization.
- Model output is untrusted input to tools unless separately controlled.
- Floating model versions → require reassessment triggers.

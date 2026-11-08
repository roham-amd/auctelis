# Recipe: source-only review (no host, no runtime)

1. Set `environment_mode=DEGRADED_READ_ONLY` or `USER_PROVIDED_SNAPSHOT`.
2. Scope to repository contents only; `EXTERNAL_SOURCE_SCOPE=repository_only`.
3. `aesa inventory` + Phase 2; do not claim host integration or runtime gates passed.
4. JSON: keep `trust_chain.runtime_behavior_tested=false` and host fields `NOT VERIFIED`.
5. `aesa validate report` before delivery.

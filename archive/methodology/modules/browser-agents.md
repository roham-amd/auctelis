# Module — Browser agents

Assess agents that drive browsers, fill forms, or handle downloads.

## Security questions

1. Domain allowlists / navigation boundaries.
2. Cookie and session leakage across sites or tenants.
3. Download and executable handling.
4. Form submission to external destinations.
5. Screenshot / DOM content feeding back into the model (injection surface).

## Attack paths to consider

```text
Malicious page content
      → browser agent observes DOM / screenshots
      → model follows injected instructions
      → privileged tools or credentialed sessions act
```

Require evidence for domain policy and session isolation before CONFIRMED claims.

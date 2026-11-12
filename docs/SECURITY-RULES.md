# authdiff deterministic security rules

Rules live in `tools/authdiff/security/rules.py` and are applied by `authdiff scan`.

**Version:** rule pack **1.6** (tooling **0.3.3** / product **0.3.3**). Twenty-two rules (001–022). Prefer `uvx --from authdiff authdiff` once PyPI is live; otherwise install from the git tag.

**Discipline:** rules emit findings with confidence `OBSERVED` or `POTENTIAL`. They never claim confirmed runtime exploitation. Every finding references evidence and lists missing controls. Each finding also carries `evidence_strength` (`LITERAL_CONFIG` / `INFERRED_HINT` / `NAME_MARKER`). Severity and confidence stay separate. `NAME_MARKER` must not alone create a critical CI gate. See [`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md).

**Finding classes (required distinction):**

| Class | Meaning | Typical severity |
| --- | --- | --- |
| `CAPABILITY` | What the component can potentially do | INFORMATIONAL / LOW |
| `EXPOSURE` | How reachable that capability is | LOW / MEDIUM |
| `SECURITY_FINDING` | Evidenced concern given exposure + missing controls | MEDIUM / HIGH / CRITICAL |

`--fail-on high|any` gates on `SECURITY_FINDING` and `EXPOSURE` only — pure capability observations do not fail CI.

---

## How rules fire

1. Inventory adapters attach `priority_hints` and typed component records.
2. The scan engine enriches components with `content_digest` and `fingerprint`.
3. `apply_all_rules(components, ctx=…)` runs each `RuleSpec` with commit/digest provenance.
4. Matching rules append `Evidence` + `Finding` objects (with `finding_class`).
5. Results appear in `findings.json`, the terminal report, and SARIF.

Absent a matching hint/type, a rule does nothing for that component.

---

## Rule catalog

| Rule id | Title | Class (default) | Typical severity | Triggers (summary) |
| --- | --- | --- | --- |
| `AUTHDIFF-RULE-001` | Skill references executable scripts | CAPABILITY → EXPOSURE/SECURITY when escalated | INFO / MEDIUM / HIGH | Skill script hints; HIGH only with bundled scripts + secrets handling |
| `AUTHDIFF-RULE-002` | MCP local command transport | CAPABILITY; SECURITY_FINDING with env or broad args | INFO / HIGH / CRITICAL | Local `command`; escalate on `inherits_or_sets_environment` or `broad_or_relative_path_args` |
| `AUTHDIFF-RULE-003` | MCP remote endpoint | EXPOSURE | MEDIUM | MCP registration with `url` / `remote_endpoint` |
| `AUTHDIFF-RULE-004` | Hook execution boundary | CAPABILITY or SECURITY_FINDING | INFO / MEDIUM | Hook execution / pre-tool lifecycle hints |
| `AUTHDIFF-RULE-005` | Skill external URLs | EXPOSURE | LOW | Skill hint: `external_url_reference` |
| `AUTHDIFF-RULE-006` | Skill secrets handling | SECURITY_FINDING | MEDIUM | Skill secrets / identity workflow hints |
| `AUTHDIFF-RULE-007` | Unattended automation | CAPABILITY (SECURITY only if agent/MCP CI) | INFO / MEDIUM | Type `Automation` / `CI Workflow`; secrets alone stay inventory |
| `AUTHDIFF-RULE-008` | Subagent delegation | CAPABILITY | INFORMATIONAL | Type `Subagent` |
| `AUTHDIFF-RULE-009` | Example MCP config | EXPOSURE | LOW | MCP hint: `example_or_template_config` |
| `AUTHDIFF-RULE-010` | Prompt-injection oriented surface | CAPABILITY or EXPOSURE | LOW / MEDIUM | Name markers (`NAME_MARKER`/LOW) or abuse-shaped instruction content (`INFERRED_HINT`/MEDIUM) |
| `AUTHDIFF-RULE-011` | Unpinned MCP package launcher | SECURITY_FINDING | HIGH | `npx -y` / `uvx` / similar without version pin |
| `AUTHDIFF-RULE-012` | Literal secret in MCP env | SECURITY_FINDING | CRITICAL / MEDIUM | Known token formats CRITICAL; template placeholders MEDIUM |
| `AUTHDIFF-RULE-013` | Cleartext HTTP remote MCP | SECURITY_FINDING | HIGH | `url` starts with `http://` |
| `AUTHDIFF-RULE-014` | Hidden Unicode in instructions | SECURITY_FINDING | HIGH | Zero-width / bidi in skills **and** rules files |
| `AUTHDIFF-RULE-015` | Download-and-execute pattern | SECURITY_FINDING | CRITICAL | `curl\|sh` / `wget\|sh` / `iwr\|iex` (bare `curl` is not this) |
| `AUTHDIFF-RULE-016` | `pull_request_target` + agent steps | SECURITY_FINDING | HIGH | Privileged PR trigger combined with agent/MCP tokens |
| `AUTHDIFF-RULE-017` | Permission-bypass / auto-approve flag | SECURITY_FINDING | HIGH | `--dangerously-skip-permissions` / `--yolo` / auto-approve |
| `AUTHDIFF-RULE-018` | Project MCP auto-enable | SECURITY_FINDING | HIGH | `enableAllProjectMcpServers` / trust-bypass settings |
| `AUTHDIFF-RULE-019` | Base-URL / proxy override | SECURITY_FINDING | HIGH | `ANTHROPIC_BASE_URL` style env overrides in settings |
| `AUTHDIFF-RULE-020` | Typosquat of known name | EXPOSURE (`NAME_MARKER`) | MEDIUM | Edit distance ≤2 vs shipped known skill/MCP names; never gates alone |
| `AUTHDIFF-RULE-021` | Unpinned launcher + secrets | SECURITY_FINDING | HIGH / CRITICAL | Same MCP: unpinned launcher + secret-like env |
| `AUTHDIFF-RULE-022` | Bypass + MCP auto-approve | SECURITY_FINDING | CRITICAL | Cross-component: permission bypass + `enableAllProjectMcpServers` |

---

## Per-rule detail

### AUTHDIFF-RULE-001 — Skill references executable scripts

- **Default class:** CAPABILITY (execution capability ≠ vulnerability)
- **Escalation:** bundled scripts directory → EXPOSURE/MEDIUM; plus secrets handling → SECURITY_FINDING/HIGH
- **Recommended action:** Verify script env inheritance and whether execution needs independent approval

### AUTHDIFF-RULE-002 — MCP server launched via local command

- **Default class:** CAPABILITY / INFORMATIONAL — a local process is not automatically malicious
- **Escalation:** `broad_or_relative_path_args` → SECURITY_FINDING/HIGH; env inheritance → CRITICAL
- **Recommended action:** Pin/verify artifacts; restrict env; require approval for high-impact tools

### AUTHDIFF-RULE-003 — MCP server uses remote endpoint

- **Class:** EXPOSURE / MEDIUM — a remote URL is not automatically unsafe
- **Recommended action:** Verify TLS/identity, OAuth scopes, credential forwarding

### AUTHDIFF-RULE-004 — Hook can intercept or execute around tool use

- **Class:** CAPABILITY unless pre-tool lifecycle → SECURITY_FINDING/MEDIUM
- **Recommended action:** Confirm post-approval argument integrity and hook execution identity

### AUTHDIFF-RULE-005 — Skill references external URLs

- **Class:** EXPOSURE / LOW — a URL is not proof of malicious content
- **Recommended action:** Pin/vendor remote references; treat remote content as untrusted

### AUTHDIFF-RULE-006 — Skill references secrets or identity workflows

- **Class:** SECURITY_FINDING / MEDIUM — requires context and reachability review
- **Recommended action:** Prefer brokers; ensure skills cannot print/forward live secrets

### AUTHDIFF-RULE-007 — Unattended automation or CI workflow

- **Default class:** CAPABILITY / INFORMATIONAL — ordinary CI (including `secrets.*`) is inventory
- **Escalation:** agent/MCP-related workflow steps → SECURITY_FINDING/MEDIUM
- **Not a substitute for:** RULE-016 (`pull_request_target` + agent), which remains the high-signal CI gate
- **Recommended action:** No gate action for publish/test CI; review only when agent authority is introduced

### AUTHDIFF-RULE-008 — Subagent may inherit delegated authority

- **Class:** CAPABILITY / INFORMATIONAL — delegation alone is not a defect
- **Recommended action:** Verify privilege reduction, message auth, memory isolation

### AUTHDIFF-RULE-009 — Example MCP config may be mistaken for production

- **Class:** EXPOSURE / LOW
- **Recommended action:** Keep examples off the host MCP search path

### AUTHDIFF-RULE-010 — Potential prompt-injection oriented instruction surface

- **Class:** CAPABILITY / LOW for name/path markers (`NAME_MARKER`); EXPOSURE / MEDIUM for abuse-shaped instruction content (`INFERRED_HINT`)
- **Recommended action:** Review full instruction text; forbid hide/bypass/fetch-execute directives

### AUTHDIFF-RULE-011 — Unpinned MCP package launcher

- **Class:** SECURITY_FINDING / HIGH — rug-pull risk via registry updates
- **Recommended action:** Pin exact version or digest; avoid floating `npx -y` / `uvx`

### AUTHDIFF-RULE-012 — Literal secret-like value in MCP env

- **Class:** SECURITY_FINDING / CRITICAL
- **Recommended action:** Replace literals with `${ENV}` placeholders; rotate the secret

### AUTHDIFF-RULE-013 — Remote MCP over cleartext HTTP

- **Class:** SECURITY_FINDING / HIGH
- **Recommended action:** Use `https://` only

### AUTHDIFF-RULE-014 — Hidden or bidi Unicode in skill instructions

- **Class:** SECURITY_FINDING / HIGH
- **Recommended action:** Strip zero-width/bidi characters; re-review visible text

### AUTHDIFF-RULE-015 — Download-and-execute pattern

- **Class:** SECURITY_FINDING / CRITICAL
- **Recommended action:** Vendor and pin scripts; never `curl | sh` from skills/hooks

### AUTHDIFF-RULE-016 — `pull_request_target` with agent-related steps

- **Class:** SECURITY_FINDING / HIGH
- **Recommended action:** Prefer `pull_request`; never feed fork PR code to privileged agents

### AUTHDIFF-RULE-017 — Permission-bypass / auto-approve flag

- **Class:** SECURITY_FINDING / HIGH (`LITERAL_CONFIG`)
- **Recommended action:** Remove bypass flags; keep interactive or policy-gated approvals

### AUTHDIFF-RULE-020 — Typosquat of known component name

- **Class:** EXPOSURE / MEDIUM (`NAME_MARKER`) — proximity is not proof of malice
- **Incident class:** typosquat / social-engineering install
- **Recommended action:** Confirm spelling vs canonical name; pin publisher + version; `authdiff vet` before install
- **Gate:** `NAME_MARKER` never fails CI alone

---

## Finding object fields (emitted by rules)

| Field | Purpose |
| --- | --- |
| `finding_id` | Stable within a scan (`F-001`, …) |
| `rule_id` | Catalog id above |
| `finding_class` | `CAPABILITY` / `EXPOSURE` / `SECURITY_FINDING` |
| `evidence_strength` | `LITERAL_CONFIG` / `INFERRED_HINT` / `NAME_MARKER` |
| `verify_in_60s` | One-line reproduction hint |
| `fix_snippet` | One-line remediation hint |
| `title` / `description` | Human-readable summary |
| `severity` | CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL |
| `confidence` | OBSERVED / POTENTIAL (not CONFIRMED from rules alone) |
| `component_ids` / `evidence_ids` | Traceability |
| `capabilities` | Related capability kinds |
| `attacker_control` → `impact` | Exploitability reasoning chain |
| `missing_controls` | Evidence/control gaps |
| `recommended_action` | Next operator step |

Evidence records should include `file_path`, `line_start`/`line_end` when locatable, `content_digest`, and `source_commit` when known.

---

## Extending the rule pack

1. Add a function in `tools/authdiff/security/rules.py`.
2. Register a `RuleSpec` in `RULES` (bump rule `version`).
3. Require positive, negative, and ambiguous fixtures before shipping HIGH/CRITICAL defaults.
4. Document it in this file and bump CHANGELOG.
5. Prefer: observation → capability → exposure conditions → missing control → security finding.
6. Optional research: AgentSecBench cases remain maintainer infrastructure, not product proof.

Do not invent a single numeric “trust score.” Keep severity, confidence, exploitability, exposure, finding class, and coverage separate ([`EVIDENCE-MODEL.md`](EVIDENCE-MODEL.md)).

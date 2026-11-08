# Module: Automations, Scheduled Tasks and Workflows

**AESA module ID:** `AUTOMATIONS`  
**Procedure references:** Sections 10.7 and 10.8 of `prompts/02-modules.md` (core: `prompts/01-core-prompt.md`)
**Applies when:** component type is `Automation`, scheduled Agent task, webhook-triggered Agent job, `Workflow`, or `Orchestrator`.

Unattended privilege is a first-class risk. Backend approval must be independently enforced; prompt text is not a control.

## Automations / scheduled tasks — inspection surfaces

- Trigger: schedule / webhook / event source
- Execution identity, credentials, scopes
- Task arguments and input provenance
- Target user/tenant
- External services and background persistence
- Retries, timeouts, approval, update path
- Cancellation and revocation

## Automations checklist

- [ ] Exact Automation identity and trigger recorded
- [ ] Unattended privilege and identity scope reviewed
- [ ] Webhook authentication, spoofing, and replay assessed
- [ ] Duplicate execution / race / idempotency reviewed
- [ ] Excessive retries and task escalation assessed
- [ ] Data egress and destructive actions reviewed
- [ ] Cross-tenant execution paths assessed
- [ ] Emergency shutdown and credential revocation reviewed
- [ ] Approval independently enforced by backend (not only LLM)

## Workflows / orchestration — inspection surfaces

- Steps, branching, conditions, dependencies
- Inputs/outputs, secrets, identities
- Parallelism, retries, rollbacks, human gates
- External actions and state persistence
- Error paths, fallback paths, cancellation

## Workflows checklist

- [ ] Individually permissible steps cannot combine into unauthorized outcomes
- [ ] Retry/fallback branches cannot bypass approvals
- [ ] Secret and identity propagation per step reviewed
- [ ] High-impact actions have bound, non-replayable approvals
- [ ] Cancellation and rollback behavior reviewed

## High-priority attack paths

- Automation performs high-impact action without independent approval
- Workflow chaining combines permissible actions into a prohibited action
- Webhook spoofing / replay triggers privileged unattended work
- Hook + Automation persistence after interactive session ends

## Passive-audit constraints

- Do not fire webhooks, schedules, or workflow runners against the target.
- Propose separately authorized staging tests when static evidence cannot establish approval binding, idempotency, or cancellation.

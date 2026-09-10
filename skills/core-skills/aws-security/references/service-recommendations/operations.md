# Scope and operating model

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

## T001

**Topic:** Scope, regional coverage, delegated administration and future-account drift

**Trigger:** Organization or multi-region use.

**Evidence:** Scoped identity/regions, per-service admin and auto-enable/policy application; complete authorized membership evidence.

**Decision:** Compare regional activity, future-account onboarding and applied policies for each selected service; ask about unassessed regions instead of extrapolating local coverage.

**Handoff:** Security platform owner: regional rollout and drift-control design with explicit account set. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T002

**Topic:** Least-privilege setup and separate implementation responsibility

**Trigger:** An accepted service recommendation needs implementation.

**Evidence:** Action/resource scope and designated implementer; read-role scope separate from provisioning permissions.

**Decision:** Keep assessment permissions separate from provisioning; identify the resource-specific changes and their owner before implementation.

**Handoff:** Service implementer and IAM owner: least-privilege change plan for accepted recommendations. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T003

**Topic:** Pricing model, trials and visibility-preserving cost review

**Trigger:** Cost review or service adoption.

**Evidence:** Account pricing plan, workload counts, trial exclusions, usage/cost estimator; no live billing read required for advice.

**Decision:** Compare current standalone/bundled plan, retained visibility and usage drivers before recommending savings; verify current trial exclusions and prices.

**Handoff:** FinOps and service owner: cost/coverage comparison with assumptions and dated pricing evidence. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

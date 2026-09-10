# Application security lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse scoped [inventory](inventory-commands.md) and [enablement](enablement-checks.md) only where the service and resource predicate matches. Otherwise request the focused configuration or existing-results evidence below. No generic fleet crawl, rule authoring, probes or test launch.

## T125

**Topic:** AppSec fit, application trigger and fallback specialist

**Trigger:** Public or private application needing dynamic testing.

**Evidence:** Application scope, current region/capability and installed specialist availability.

**Decision:** Consider AppSec assessment for confirmed public or private applications; dynamic testing complements code/design/supply-chain review and does not have an account-wide enabled state.

**Handoff:** pentesting-with-aws-security-agent only if installed; otherwise AppSec owner: application-specific capability and testing suitability decision, no automatic launch. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T126

**Topic:** Private application access and VPC topology

**Trigger:** Internal/private AWS, on-premises or cross-cloud application.

**Evidence:** Agent-account VPC/subnet/SG, private routing/TGW/hybrid path, DNS and source-IP allowlist requirement.

**Decision:** Review private DNS, selected VPC/subnets/SGs, hybrid/TGW routes and return paths. Guide NAT exemption conflicts with setup devguide NAT guidance: establish target and dependency connectivity, never a universal NAT requirement/exemption.

**Handoff:** AppSec/network owner: current private-testing topology and reachability review; never expose the app publicly as a shortcut. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T127

**Topic:** Agent spaces, operator roles and service-role permissions

**Trigger:** First-time setup or multi-application use.

**Evidence:** Per-app project boundary, IAM Identity Center access, user/admin separation and integration-specific service role.

**Decision:** Separate operator/admin identities, application agent-space boundary and service-role trust/permissions; a generic role does not prove access to every integration.

**Handoff:** AppSec/IAM owner: least-privilege operator and service-role design for the selected application and integrations. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T128

**Topic:** Ownership, target/access domains and excluded paths

**Trigger:** Penetration testing contemplated.

**Evidence:** Verified ownership, full login redirect chain, permitted navigation and excluded destructive/auth-mutation paths.

**Decision:** Check ownership, exact full target domain, private-address verification where applicable, access-domain redirect chain and destructive exclusions. Pre-run UNREACHABLE is neither success nor a conclusive failure.

**Handoff:** AppSec/application owner: explicit test authorization, navigation/access boundaries and excluded-path plan; do not initiate verification. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T129

**Topic:** Authenticated roles and credential vendors

**Trigger:** Application authentication.

**Evidence:** Dedicated realistic user/admin/service roles, Secrets Manager/Lambda vendor, login success steps and MFA/domain context.

**Decision:** Plan realistic dedicated roles and login success/MFA steps; request credential-vendor metadata only, never credentials, secret values or authenticated payloads.

**Handoff:** AppSec/identity/application owners: credential delivery and role-specific authenticated testing design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T130

**Topic:** Context, risk selection and non-deterministic results

**Trigger:** Planning or interpreting a pentest.

**Evidence:** Source/API/architecture/threat context, selected risks, cumulative findings and business impact.

**Decision:** Match source/API/architecture/threat context and selected risks to business impact; non-deterministic runs and a clean report do not establish exhaustive security.

**Handoff:** AppSec owner: context-rich assessment plan and evidence-based finding validation across the requested scope. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T131

**Topic:** WAF interaction and meaning of bypassed tests

**Trigger:** Target protected by WAF.

**Evidence:** Pre-production target, test identification, temporary bypass scope/removal owner and protected-path revalidation.

**Decision:** Separate application exploitability from production WAF effectiveness. Any proposed test bypass requires a separate controlled environment/scope, removal owner and protected-path revalidation; assessment never adds an allow rule.

**Handoff:** AppSec plus waf/WAF owner: test-control interaction decision and independently authorized validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T132

**Topic:** Logs, data handling and budget readiness

**Trigger:** Test planning.

**Evidence:** Activity log retention, regional storage/inference, encryption support, quotas/tags and maximum task-hours.

**Decision:** Confirm current regional processing/storage, encryption, quotas, logging retention and maximum task-hour budget from authoritative evidence; do not hardcode preview/GA/Continuum or pricing claims.

**Handoff:** AppSec/data/FinOps owners: data-handling and budget readiness decision before any separately authorized test. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T133

**Topic:** Feedback, remediation review, revalidation and CI/CD

**Trigger:** Findings remediation or pipeline integration.

**Evidence:** Finding verification, human-reviewed fixes, targeted revalidation vs full retest, report consumers and deployed test environment.

**Decision:** Route verified findings to human-reviewed remediation, then distinguish targeted revalidation from full retesting against a deployed environment; cumulative reports and CI/CD need ownership.

**Handoff:** AppSec/developer/CI owners: remediation, report retention and post-deployment validation plan; no scans, exports, PR creation or feedback submission here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

# WAF lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse scoped [inventory](inventory-commands.md) and [enablement](enablement-checks.md) only where the service and resource predicate matches. Otherwise request the focused configuration or existing-results evidence below. No generic fleet crawl, rule authoring, probes or test launch.

## T104

**Topic:** Baseline managed rules and application-specific selection

**Trigger:** Public HTTP application.

**Evidence:** Application stack, baseline/use-case groups, Count evidence and paid partner choice.

**Decision:** Match managed baseline and application-specific groups to the actual stack, Count evidence and false positives; no fixed baseline guarantees protection.

**Handoff:** waf if installed, otherwise WAF owner: justified managed-group selection and staged validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T105

**Topic:** Managed-rule version lifecycle and scope-down

**Trigger:** Managed rules in use.

**Evidence:** Pinned/default version, SNS/expiry alarms, supported scope-down and application test results.

**Decision:** Evaluate pinned/default versions, update notifications and expiry readiness against tested compatibility; scope-down decisions must preserve relevant attack coverage.

**Handoff:** waf/WAF owner: version lifecycle and scope-down review with upgrade and rollback ownership. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T106

**Topic:** Bot Common/Targeted and endpoint economics

**Trigger:** Scraping/automation or valuable dynamic endpoints.

**Evidence:** Bot labels, business harm, browser/session SDK support, inspection level and scope-down.

**Decision:** Choose Common/Targeted from bot labels, legitimate-client evidence, business harm and current version capabilities; authenticated endpoints can still suffer bot abuse and verified bots may be unwanted.

**Handoff:** waf/WAF owner: endpoint-specific bot strategy and Count-to-enforcement validation with SDK compatibility and costs. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T107

**Topic:** Web Bot Authentication and AI bot policy

**Trigger:** AI crawlers or authenticated bot policy.

**Evidence:** Supported Bot Control version, WBA labels, provider identity and business policy.

**Decision:** Require current Web Bot Authentication/version/label evidence and a business decision for AI crawlers; the guide's incomplete monetization section is not an implementation specification.

**Handoff:** waf/WAF and business owners: verified-bot/AI-crawler policy decision, with unsupported monetization claims left unknown. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T108

**Topic:** Fraud ATP and ACFP

**Trigger:** Login or registration abuse.

**Evidence:** Endpoint/field configuration, authentication outcomes, client tokens and pricing.

**Decision:** Match ATP to login and ACFP to account creation using real request fields and outcome signals. Verify current resource/protocol support: reviewed response inspection is CloudFront-limited, excludes HTTP/3 responses, and ATP/ACFP exclude Cognito user pools.

**Handoff:** waf/WAF and application owners: fraud-control compatibility and false-positive validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T109

**Topic:** CAPTCHA/Challenge usability, tokens and immunity

**Trigger:** Browser token controls considered.

**Evidence:** Client compatibility, passive SDK/POST behavior, accessibility, token domains/immunity and per-action charges.

**Decision:** Check compatible HTTPS browser/SDK token acquisition before protecting API/POST flows; test accessibility, token domains, expiry/immunity and legitimate failures. Tokens do not replace authentication.

**Handoff:** waf/WAF/frontend owners: client-compatible CAPTCHA/Challenge design and usability validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T110

**Topic:** Custom rate rules, thresholds and evaluation windows

**Trigger:** HTTP flood, costly endpoint or brute force.

**Evidence:** Observed rates over matching windows, NAT/session composite keys and Count-mode evaluation.

**Decision:** Base rate thresholds and windows on observed endpoint traffic, shared-NAT/session effects and expensive operations; Count-mode evidence should precede enforcement advice.

**Handoff:** waf/WAF owner: rate-key/window and threshold design with legitimate-client validation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T111

**Topic:** Geo/IP/header rules and oversize handling

**Trigger:** Application-specific policy.

**Evidence:** Actual client identity, trusted forwarding, header/body limits, upload endpoints and bypass scope.

**Decision:** Assess forwarded-IP trust, Geo/IP/header intent and oversize body/header handling against uploads and bypass risk; do not trust client-supplied identity headers by default.

**Handoff:** waf/WAF/application owners: request-boundary and oversize-handling review for selected endpoints. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T112

**Topic:** Labels and safe false-positive exceptions

**Trigger:** Legitimate request blocked.

**Evidence:** Matched label/request context, per-rule Count override and narrow exception; no global allow bypass.

**Decision:** Distinguish a narrow WAF traffic false-positive exception from prohibited security-finding suppression. Review labels and exact legitimate-request context; avoid global allow rules that bypass later controls.

**Handoff:** waf/WAF owner: narrowly scoped traffic exception proposal and regression-validation plan; no rule authoring here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T113

**Topic:** Count-first operational rollout and ownership

**Trigger:** New or changed WAF protection.

**Evidence:** Baseline rules, logging, representative observation period, enforcement readiness and app/security ownership.

**Decision:** Require representative observation, logging and application/security ownership before advising enforcement; a new rule's presence is not rollout success.

**Handoff:** waf/WAF/application owners: Count-first rollout criteria, operational responsibility and rollback plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T114

**Topic:** Rule evaluation order and terminating actions

**Trigger:** Ruleset tuning.

**Evidence:** Actual priority order, label producers/consumers, Anti-DDoS placement and paid groups.

**Decision:** Trace priority, terminating actions and label dependencies through the actual ruleset; the guide has conflicting rate-rule ordering advice, so verify current semantics instead of prescribing one universal order.

**Handoff:** waf/WAF owner: evaluation-order review with expected outcomes for representative traffic. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T115

**Topic:** WAF placement and origin bypass protection

**Trigger:** Public HTTP or indirect untrusted traffic.

**Evidence:** Distribution/ACL association, origin restrictions, OAC, forwarded IP trust, protocol and static/private exclusions.

**Decision:** Verify association and origin restrictions, including alternative/non-AWS origins and trusted forwarding; CloudFront origin naming is not bypass protection.

**Handoff:** waf/WAF/edge owner: placement and origin-path validation plan without collecting secret header names or values. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T116

**Topic:** Protection-pack ownership, sharing and capacity

**Trigger:** Fleet/app boundary or ruleset size decision.

**Evidence:** Shared blast radius, baseline ownership, WCU capacity and pricing model.

**Decision:** Balance shared protection-pack/ACL ownership and capacity against application isolation and blast radius; verify current WCU/pricing constraints.

**Handoff:** waf/WAF/platform owner: fleet ownership and capacity decision with exception responsibilities. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T117

**Topic:** Logging destination, delivery, retention and redaction

**Trigger:** WAF enabled.

**Evidence:** Destination/query use, delivery latency, retention policy and sensitive header redaction.

**Decision:** Compare intended destination, delivered logs, retention and redaction with troubleshooting and data-handling needs; configuration alone does not prove delivery.

**Handoff:** waf/WAF/log owner: logging and sensitive-field handling validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T118

**Topic:** Log filtering and forensic completeness

**Trigger:** Logging cost reduction.

**Evidence:** Which allowed/blocked requests remain, troubleshooting and incident-history needs.

**Decision:** Assess which allowed/blocked/nonterminating evidence filtering removes before cost advice; do not sacrifice required incident history or hide security findings.

**Handoff:** waf/WAF/log owner: costed forensic-completeness decision and filtering review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T119

**Topic:** S3 prefixes, partition projection and query costs

**Trigger:** Central WAF logs queried in Athena.

**Evidence:** Delivery prefix granularity, time partitions/projection, query scope and data volume.

**Decision:** Compare existing S3 prefixes and partitions/projection with query time scope and data volume; avoid unbounded scans of stored logs.

**Handoff:** Analytics/log owner with waf context: bounded partition/query design and cost estimate; no Athena query execution. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T120

**Topic:** Rule validation from logs and dashboards

**Trigger:** Count-to-Block evaluation or investigation.

**Evidence:** Labels and terminating/nonterminating matches, endpoint/method scope and secondary signals.

**Decision:** Use labels, terminating/nonterminating matches, endpoint/method and secondary signals to judge observed behavior; absence of labels is inconclusive if the rule was not evaluated.

**Handoff:** waf/WAF analyst: scoped rule validation and dashboard interpretation using existing observations. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T121

**Topic:** Firewall Manager integration and customization ownership

**Trigger:** Organization-wide WAF.

**Evidence:** Policy first/last rule sets, IaC ownership, exceptions and policy scope.

**Decision:** Review FMS first/last groups, application customization and IaC ownership against applied scope; incomplete source sections do not establish current import/IaC restrictions.

**Handoff:** waf/WAF/platform owner: current-supported fleet policy and exception ownership design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T122

**Topic:** GuardDuty/Shield/Transfer integrations

**Trigger:** Related service integration requested.

**Evidence:** Intended protocol/resource, GuardDuty response ownership and Shield-protected resources.

**Decision:** For GuardDuty/Shield/Transfer integration, identify the precise protocol/resource and response owner; source TODOs cannot establish support or authorize traffic-changing automation.

**Handoff:** waf/WAF and service owner: verified integration capability and separately approved response design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T123

**Topic:** Cost dimensions, premium features and bundled plans

**Trigger:** WAF cost review.

**Evidence:** Evaluated request volume, WCU/body inspection, tokens, premium groups, logs and eligible bundled resources.

**Decision:** Use current evaluated-request, capacity/body, token, premium-group and logging usage for cost advice; verify bundled eligibility rather than copying guide prices or allowances.

**Handoff:** waf/WAF/FinOps owner: current-priced options preserving protection and forensic coverage. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T124

**Topic:** Broader endpoint discovery and existing-ACL tuning entry

**Trigger:** Public HTTP on AppSync/Cognito/App Runner/Verified Access, non-AWS origins or already-protected apps.

**Evidence:** Application endpoint inventory supplied by user or scoped reads; association support and current CloudFront/mTLS restrictions.

**Decision:** Ask for the application's full endpoint set, including existing ACLs, AppSync, Cognito, App Runner, Verified Access and non-AWS origins. Verify current association and mTLS support per resource before advice.

**Handoff:** waf/WAF/edge owner: endpoint-specific coverage and tuning review; no inventory-driven absence claim for unsupported/unassessed types. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

# Network Firewall lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse scoped [inventory](inventory-commands.md) and [enablement](enablement-checks.md) only where the service and resource predicate matches. Otherwise request the focused configuration or existing-results evidence below. No generic fleet crawl, rule authoring, probes or test launch.

## T080

**Topic:** Presence, endpoint AZs and policy baseline

**Trigger:** NFW already deployed.

**Evidence:** Firewall/policy/logging describes and workload AZ context.

**Decision:** Identify deployment mode before applying endpoint/AZ checks; inspection-VPC, native TGW and multi-endpoint designs need their own current topology constraints.

**Handoff:** Network Firewall architect: endpoint/policy/logging completeness assessment for the actual mode. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T081

**Topic:** Centralized native TGW versus inspection VPC/Cloud WAN

**Trigger:** Multi-VPC inspection design.

**Evidence:** Deployment mode, native TGW support/limits, inspection VPC needs, Cloud WAN insertion and metering ownership.

**Decision:** Compare native TGW, inspection VPC and Cloud WAN insertion against required paths, supported features, metering and ownership; verify current limits before selecting.

**Handoff:** Network Firewall/network architect: justified deployment architecture and routing validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T082

**Topic:** Distributed, multi-endpoint and combined deployments

**Trigger:** Distributed egress, isolation or endpoint sharing.

**Evidence:** Endpoint associations, payer/owner, NAT placement and TLS compatibility; justify combined model.

**Decision:** Compare distributed, shared multi-endpoint and combined models against isolation, NAT placement and payer ownership. Treat TLS/endpoint-association compatibility as unverified until current evidence resolves it.

**Handoff:** Network Firewall architect: deployment/feature compatibility matrix and failure-domain review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T083

**Topic:** Network Firewall Proxy preview

**Trigger:** Explicit forward proxy, overlapping CIDRs or existing proxy clients.

**Evidence:** Preview availability, no-source-preservation mode, client FQDN configuration, NAT path and supported features.

**Decision:** Treat Network Firewall Proxy as preview and conditional expert review, never a missing-proxy gap. Review explicit client proxy configuration, endpoint reachability, NAT attachment and bypass; direct NAT traffic is not protected by the proxy policy.

**Handoff:** Network Firewall/proxy architect: current preview eligibility and client/path compatibility decision, including source-address needs; no invented preview API fields. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T084

**Topic:** Firewall Manager and RAM sharing model

**Trigger:** Multi-account firewall distribution.

**Evidence:** Central/distributed model, shared firewall vs policy/rules vs TGW resource and ownership.

**Decision:** Distinguish sharing firewall endpoints, policies/rule groups and TGW resources; evaluate RAM permissions and FMS scope separately.

**Handoff:** Network/platform owner: resource-specific sharing and deployment ownership design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T085

**Topic:** Traffic bypass and symmetric routing

**Trigger:** Inspection effectiveness or connectivity failure.

**Evidence:** Both traffic directions, routes/AZs, firewall flow/alert correlation and bypass traffic.

**Decision:** Trace both traffic directions, AZ/endpoints and bypass routes with existing flow/alert evidence; configured policy alone is not enforcement proof.

**Handoff:** Network analyst: bounded symmetric-path and bypass diagnosis with representative flows; no active probes here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T086

**Topic:** Default drop/alert modes and application handshake behavior

**Trigger:** Default-deny or application connectivity review.

**Evidence:** Policy actions, custom-default strategy, direction, fragmented TLS and logging behavior.

**Decision:** Compare application-aware defaults, handshake/fragment behavior and custom defaults using the actual policy; do not prescribe mutually incompatible defaults or infer final blocking from alert configuration.

**Handoff:** Network Firewall specialist task: default-action and connectivity compatibility review with expected verdicts. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T087

**Topic:** HOME_NET/EXTERNAL_NET and east-west rule applicability

**Trigger:** Centralized or east-west inspected traffic.

**Evidence:** Actual IPv4/IPv6/routable CIDRs, policy/rule-group inheritance and managed-rule deployment tags.

**Decision:** Compare HOME_NET/EXTERNAL_NET and policy/group inheritance with actual routed IPv4/IPv6 and east-west ranges; do not substitute all RFC1918 space indiscriminately.

**Handoff:** Network Firewall specialist task: address-variable and managed-group applicability review; no Suricata authoring. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T088

**Topic:** Stateful rule semantics, pass blind spots and IDs

**Trigger:** Ruleset review or suspected bypass.

**Evidence:** Stateless forwarding, protocol/flow keywords, broad pass termination and SID traceability.

**Decision:** Assess broad pass termination, protocol/flow semantics, stateless forwarding and SID traceability from supplied ruleset evidence; passing a flow can bypass later inspection.

**Handoff:** Network Firewall specialist task: semantic ruleset review and expected-flow outcomes, without authoring or executing rules. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T089

**Topic:** Capacity, rule-group consolidation and growth

**Trigger:** Rule additions or capacity pressure.

**Evidence:** Consumed capacity, group count, byte size, IP set reference counts and growth needs.

**Decision:** Compare consumed capacity, group size/count and reference growth with current quotas; do not call CreateRuleGroup even with DryRun.

**Handoff:** Network Firewall owner: capacity and consolidation plan based on existing metadata and forecast. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T090

**Topic:** Domain allowlists, SNI spoofing and boundary-safe matching

**Trigger:** Egress domain controls.

**Evidence:** Required domains, exact/wildcard/PCRE scope, tenant-domain trust and encrypted-content threat requirement.

**Decision:** Assess exact/wildcard domain scope, tenant trust and SNI manipulation limits; domain allowlisting does not prove server/content identity.

**Handoff:** Network Firewall specialist task: domain-boundary and spoofing-risk review with required destinations; no generated signatures. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T091

**Topic:** Application/protocol restrictions and visibility rule families

**Trigger:** Required egress policy and observed traffic.

**Evidence:** Domain categories, direct IP, GeoIP, QUIC, TLD, port/protocol needs, allowed NTP/ICMP and TLS fingerprint use.

**Decision:** Select direct-IP, GeoIP, QUIC, TLD, protocol/port, NTP/ICMP and fingerprint controls only from actual egress requirements and supported observations; absence alone is not a defect.

**Handoff:** Network Firewall specialist task: justified rule-family and exception design with visibility limitations. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T092

**Topic:** Managed ATD, reputation and signature selection

**Trigger:** NFW policy present.

**Evidence:** Managed groups, threat/deployment relevance, HOME_NET, capacity and partner cost.

**Decision:** Compare ATD, reputation, signature/partner groups and deployment tags with threats, HOME_NET and capacity; verify current versions, eligibility and charges.

**Handoff:** Network Firewall owner: managed-group selection and effectiveness review for the selected traffic. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T093

**Topic:** Managed-rule tuning and filtered synchronization

**Trigger:** Managed signatures need tuning or east-west subset.

**Evidence:** Alert observations, deployment tags, proposed enforcement and synchronization ownership.

**Decision:** Use alert observations to decide staged enforcement and false-positive risk; filtered managed-rule subsets need synchronization/version ownership. Never automatically convert alerts to drops.

**Handoff:** Network Firewall owner: managed-rule tuning and synchronization plan with observation and rollback criteria. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T094

**Topic:** Starter policy and staged enforcement

**Trigger:** Initial deployment or monitor-only policy.

**Evidence:** Monitoring period, default actions, managed overrides, allowlist, east-west requirements and capacity.

**Decision:** Distinguish monitor-only from enforcement readiness using defaults, overrides, representative traffic and allowlist/east-west requirements; strict order plus logs does not prove blocking.

**Handoff:** Network Firewall owner: staged rollout decision and validation plan; no starter policy generation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T095

**Topic:** Active flows, stream exceptions and idle timeout

**Trigger:** Policy changes, long-lived traffic or midstream errors.

**Evidence:** Stream-exception metrics, NAT/backend timeout, existing connections and targeted flow handling.

**Decision:** Assess active connections, stream-exception evidence and NAT/backend idle behavior together; exact timers and per-leg claims need current verification.

**Handoff:** Network analyst: connection-disruption and timeout plan; flow capture/flush are separate authorized operations, never read checks. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T096

**Topic:** TLS applicability, cost and topology constraints

**Trigger:** Encrypted-content inspection requirement.

**Evidence:** Data sensitivity, application protocols, inbound/outbound direction, deployment compatibility and cost.

**Decision:** Choose TLS inspection only for justified decrypted-content needs with data-handling permission, client/protocol compatibility and cost evidence; absent TLS inspection is not a universal gap.

**Handoff:** Network Firewall and PKI specialists: topology-specific inspection suitability and exception decision. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T097

**Topic:** TLS trust, scope, client distribution and revocation

**Trigger:** TLS inspection chosen.

**Evidence:** Inbound certificate trust, outbound CA/key usages, client trust stores, narrowly scoped inspection and revocation requirements.

**Decision:** Review client trust stores, inbound certificate and outbound imported CA metadata, narrow scopes and revoked/unknown actions. Non-TLS or missing/mismatched SNI traffic can drop; never collect private keys.

**Handoff:** PKI/network owners: trust distribution, revocation/failure policy and change-impact validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T098

**Topic:** TLS plaintext rules, session holding and timeout compatibility

**Trigger:** TLS-inspected applications.

**Evidence:** Post-decryption protocols, SNI rules, QUIC/cipher/version limits, idle timeouts and session-holding/default-action compatibility.

**Decision:** Evaluate inner-protocol rules after decryption, with TLS.SNI exception; review STARTTLS, QUIC, ECH, HTTP/2 WebSockets, pinning/mTLS and session-holding compatibility. Exact timers and multi-endpoint incompatibility remain unverified, not universal facts.

**Handoff:** Network Firewall/application specialists: representative compatibility and idle-flow test plan with current documentation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T099

**Topic:** Log configuration versus traffic verdict/flow interpretation

**Trigger:** Firewall logging or investigation.

**Evidence:** ALERT/FLOW/TLS destinations, final verdict vs alert action, flow-end timing, bidirectional flow IDs and destination-change continuity.

**Decision:** Separate configuration from delivered ALERT/FLOW/TLS evidence; interpret alert action versus final verdict, flow-end timing and bidirectional identifiers before inferring dropped traffic.

**Handoff:** Firewall/log analyst: scoped verdict correlation and destination-continuity review, using supplied logs rather than new queries. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T100

**Topic:** Dashboard, rule hit counts, metrics and alarms

**Trigger:** Operating firewall or validating rules.

**Evidence:** Observed traffic, rule-hit visibility, pass alert keyword, time window and stream/drop/reject/TLS metrics.

**Decision:** Relate rule hits and stream/drop/reject/TLS metrics to observation coverage and representative windows; zero hits do not prove a rule unnecessary.

**Handoff:** Firewall/monitoring owner: dashboard/alarm and periodic rule-hygiene plan with visibility prerequisites. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T101

**Topic:** Traffic analysis, domain reports and rule-generation tools

**Trigger:** Building initial egress allowlist.

**Evidence:** Opt-in traffic analysis scope, collected report, observation window and reviewer ownership.

**Decision:** Use already-produced domain/traffic reports as evidence for candidate allowed destinations; observation does not prove every destination is required or safe.

**Handoff:** Firewall/application owner: reviewed egress-requirements decision; no collection start, rule generation or deployment. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T102

**Topic:** Cost architecture, discount qualification and current billing

**Trigger:** NFW spend/design review.

**Evidence:** Payer/region/NAT type, traffic path, endpoint utilization, TLS tier and current transfer billing.

**Decision:** Verify current NAT discounts, endpoint/TGW/shared-payer and TLS charges against the actual path; do not repeat fixed endpoint ratios or dated transfer savings as universal facts.

**Handoff:** Network/FinOps owner: current-priced architecture comparison with explicit qualification assumptions. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T103

**Topic:** Traffic cost attribution and logging-volume tuning

**Trigger:** Unexpected spend or shared-service chargeback.

**Evidence:** Traffic by source/service/path, query budget, metering policy and logging forensic requirements.

**Decision:** Attribute spend to source/path/time and logging needs before reducing volume; retain forensic completeness and never launch queries to obtain cost evidence automatically.

**Handoff:** FinOps/log analyst: scoped chargeback and logging-volume analysis plan with query budget and retention constraints. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

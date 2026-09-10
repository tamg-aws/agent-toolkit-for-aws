# Network boundaries and DNS

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse scoped [inventory](inventory-commands.md) and [enablement](enablement-checks.md) only where the service and resource predicate matches. Otherwise request the focused configuration or existing-results evidence below. No generic fleet crawl, rule authoring, probes or test launch.

## T067

**Topic:** Layered controls and protocol-aware placement

**Trigger:** Internet ingress or egress requirements.

**Evidence:** Traffic protocols, application logic, trust boundaries and existing controls.

**Decision:** Map protocols and trust boundaries before choosing controls; include SGs/NACLs and automatic Shield Standard network/transport protection. Never report Standard disabled or imply it solves application abuse.

**Handoff:** Network/security architect: layered placement decision tied to required flows and business risk. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T068

**Topic:** Security-group least privilege and tier-reference segmentation

**Trigger:** VPC workloads or east-west exposure.

**Evidence:** Required source/destination tiers, SG references, outbound requirements and actual rule scope.

**Decision:** Compare the union of attached SG ingress/egress, IPv4/IPv6 and tier references with required flows. SG references mean interface membership, not authenticated caller identity.

**Handoff:** Network/application owner: least-privilege tier-flow proposal with topology/reference constraints and return-flow validation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T069

**Topic:** NACL deny role and return-path implications

**Trigger:** Subnet defense or emergency blocking requirement.

**Evidence:** NACL directions, ephemeral return ports, high-value denies and operational owner.

**Decision:** Review ordered stateless rules in both directions and return ports; NACLs do not filter same-subnet traffic or replace Resolver-DNS/IMDS controls. An allow-all NACL alone is not a gap.

**Handoff:** Network owner: justified subnet-deny and recovery plan consistent with SG policy. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T070

**Topic:** Endpoint traffic elimination and anti-exfiltration policies

**Trigger:** AWS API traffic currently traverses NAT/firewall or private service access needed.

**Evidence:** Endpoint routes/private DNS, endpoint policies, service/resource scope and central-vs-local cost.

**Decision:** Compare gateway/interface endpoint routes, DNS and policies with allowed services/resources and exfiltration concerns; private connectivity alone does not restrict destinations.

**Handoff:** Network/IAM owner: endpoint placement and resource-policy design with current service support and costs. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T071

**Topic:** DNS filtering complement and layered egress

**Trigger:** VPC recursive DNS and egress.

**Evidence:** Resolver path, DNS Firewall association/rules and traffic bypassing DNS.

**Decision:** Account for Resolver DNS traffic separately from routed inspection and hardcoded-IP egress. SGs cannot block AmazonProvidedDNS; DNS policy alone does not prove egress enforcement.

**Handoff:** DNS/network owner: layered resolver and routed-egress control plan with bypass evidence. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T072

**Topic:** Decentralized ingress and justified centralized exceptions

**Trigger:** Ingress inspection design.

**Evidence:** Protocol, compliance/proxy constraints, per-AZ bidirectional routing and failure domain.

**Decision:** Prefer placement justified by protocol and application ownership; evaluate centralized ingress exceptions through compliance/proxy needs, bidirectional routing and failure domains.

**Handoff:** Network/edge owner: ingress architecture comparison and path-validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T073

**Topic:** Egress architecture and cost tradeoffs

**Trigger:** Multiple VPC egress paths.

**Evidence:** TGW/Cloud WAN processing, failure/ownership model, NAT type and endpoint costs.

**Decision:** Compare distributed/centralized egress against TGW/Cloud WAN processing, NAT type, ownership and failure domains; verify current discount eligibility, including regional-NAT terms.

**Handoff:** Network/FinOps owner: costed egress alternatives using actual paths and utilization. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T074

**Topic:** East-west inspection, account isolation and Cloud WAN segmentation

**Trigger:** Different trust levels or lateral-movement inspection requirements.

**Evidence:** Account/VPC/tier boundaries, TGW/Cloud WAN segment connectivity, inspection path and cost.

**Decision:** Separate account/VPC/tier isolation from inspection; compare intended trust zones with TGW/Cloud WAN connectivity and lateral paths, including bypass routes.

**Handoff:** Network/security architect: segmentation and inspection insertion design with explicit allowed flows. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T075

**Topic:** VPC Lattice identity authorization

**Trigger:** Service-to-service access or Lattice confirmed/planned.

**Evidence:** Service networks/associations, IAM auth policy requirements and caller identities alongside SG boundaries.

**Decision:** For Lattice identity boundaries, inspect AWS_IAM authType and policy state on both service and service network, caller policies, explicit denies and signing. Policies can allow anonymous access; identity policy does not supply connectivity.

**Handoff:** Lattice/network/IAM owner: intended-caller versus effective-policy review; TCP resource/passthrough semantics require current topology-specific documentation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T076

**Topic:** Shield and Firewall Manager applicability

**Trigger:** Business-critical public workload or distributed fleet.

**Evidence:** DDoS/business impact, protected resource scope, distributed policy need and org/Config prerequisites.

**Decision:** Treat Shield Standard as automatic baseline and Advanced as a risk/cost decision; evaluate resource eligibility and current bundled terms. FMS policy presence does not prove applied healthy protection.

**Handoff:** shieldadvanced if installed plus platform owner: DDoS response/protection and distributed policy-application review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T077

**Topic:** Explicit networking boundaries and adjacent specialties

**Trigger:** Hybrid connectivity, transport encryption, routing or IPv6 question.

**Evidence:** Identify requested topic and relevant Networking Best Practices section.

**Decision:** Identify adjacent hybrid routing, IPv6 and transport-encryption requirements as dependencies, without importing an entire networking manual into this assessment.

**Handoff:** Network specialist: the named connectivity/encryption question, known topology, unknowns and required path/security decision. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T078

**Topic:** VPC association, managed lists, Advanced and query logs

**Trigger:** VPC resolver usage.

**Evidence:** Per-VPC active association, managed/Advanced rules, query-log association and retention/delivery evidence.

**Decision:** Require rule and Advanced settings plus actual VPC association and log delivery; association alone cannot establish managed-list coverage or successful DNS filtering.

**Handoff:** route53 if installed, otherwise DNS owner: scoped Resolver policy and delivery review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T079

**Topic:** DNS policy rollout, custom domains and rule effectiveness

**Trigger:** DNS filtering design or tuning.

**Evidence:** Domain policy, ALLOW/ALERT/BLOCK actions, managed rules, deployment scope and representative query logs.

**Decision:** Compare custom-domain intent and managed rules with observed queries, ALLOW/ALERT/BLOCK behavior and false positives; evaluate enforcement periodically.

**Handoff:** route53 if installed, otherwise DNS owner: rule-effectiveness and rollout validation plan; no rule authoring here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

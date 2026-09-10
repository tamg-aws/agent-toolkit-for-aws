# Certificates and private PKI

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse [certificate inventory](inventory-commands.md) and [expiry checks](enablement-checks.md). For hierarchy, revocation, connector or client behavior, use the focused metadata below; do not collect certificate private keys.

## T004

**Topic:** ACM inventory, issuance path, renewal eligibility and expiry dates

**Trigger:** ACM certificates or confirmed externally managed/direct-CA issuance.

**Evidence:** List/describe certificate, dates, renewal fields, issuance evidence and applicable event routes.

**Decision:** Separate imported, ACM-managed and directly issued certificates; judge renewal eligibility, observed renewal and deployment independently.

**Handoff:** PKI/application owner: renewal and deployment responsibility matrix for the identified issuance paths. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T005

**Topic:** Expiry notifications and scalable monitoring

**Trigger:** Certificate lifecycle review.

**Evidence:** Enabled matching event rule, SNS target, delivery evidence; issuer-side monitoring for direct CA issuance.

**Decision:** Assess both event delivery and fleet completeness; compare EventBridge, CloudWatch expiry alarms or scheduled issuer-side checks against the notification lead time required.

**Handoff:** PKI/monitoring owner: scalable expiry-monitoring design and delivery-validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T006

**Topic:** DNS validation and SAN/domain lifecycle

**Trigger:** Certificate validation or domain changes.

**Evidence:** Validation method, DNS ownership/record persistence, domains and renewal ownership.

**Decision:** Review DNS ownership and persistence through renewal; verify current SAN-change semantics before choosing replacement issuance and cutover.

**Handoff:** PKI/DNS owner: validation and domain-migration plan retaining old coverage until deployment is verified. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T007

**Topic:** Certificate transparency and client trust impact

**Trigger:** Public certificates contain sensitive hostnames.

**Evidence:** CT preference, issuance/renewal phase and browser/client trust requirements.

**Decision:** Balance hostname disclosure with relying-client trust; opting out cannot erase previously published certificate information. Confirm current CT behavior before advice.

**Handoff:** PKI/application owner: client-compatible disclosure decision and renewal timing review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T008

**Topic:** CloudFormation validation stalls, quota and ephemeral certificates

**Trigger:** Repeated test environments or stalled certificate provisioning.

**Evidence:** IaC validation ownership, DNS/account placement and certificate reuse/quota strategy.

**Decision:** Diagnose stalled validation from DNS/account ownership evidence; compare carefully bounded certificate reuse with quota and shared-key blast radius.

**Handoff:** IaC/PKI owner: certificate-validation recovery and ephemeral-environment reuse design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T009

**Topic:** Certificate protection, account separation, grants and pinning

**Trigger:** Applications rely on ACM certificates.

**Evidence:** Certificate issuance/export capability, IAM/SCP/grant access, production/test separation and pinning behavior.

**Decision:** Review issuer-specific exportability, key access, grants and production/test separation; inspect pinning rollover behavior without collecting private keys. Do not inherit blanket export bans from the guide.

**Handoff:** PKI/IAM/application owners: key-access boundaries and tested trust/pinning rollover design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T010

**Topic:** Certificate ownership, inventory reports and audit trail

**Trigger:** Certificate estate or compliance requirement.

**Evidence:** Owner/purpose tags, inventory reconciliation, certificate-operation audit coverage and notification ownership.

**Decision:** Reconcile owner/purpose inventory with deployed certificates and audit records; assign orphaned renewal and alert ownership before calling monitoring complete.

**Handoff:** PKI/compliance owner: scoped inventory reconciliation and lifecycle evidence schedule. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T011

**Topic:** Private CA hierarchy and root isolation

**Trigger:** Private CA present or PKI design requested.

**Evidence:** CA hierarchy, root account, issuing relationships and end-entity usage; list-CAs alone is insufficient.

**Decision:** Compare issuing relationships with root isolation and intended trust domains; CA presence or a fixed hierarchy depth does not prove isolation.

**Handoff:** PKI architect: hierarchy and root-use review using certificate-chain metadata and issuer permissions. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T012

**Topic:** CA validity, algorithms, templates and issuance validation

**Trigger:** Private certificate issuance.

**Evidence:** CA/end-entity validity bounds, algorithms, templates, CSR validation and permitted names/usages.

**Decision:** Check validity bounds through the chain, relying-client algorithms, CSR names/usages and template passthrough against issuance policy; verify current supported algorithms and limits.

**Handoff:** PKI architect: approved issuance/template constraints and compatibility validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T013

**Topic:** CA sharing, regional design and administrator/issuer separation

**Trigger:** CA shared across teams/accounts.

**Evidence:** RAM shares/allowed principals, resource and IAM policies, regional boundaries and admin/issuer role separation.

**Decision:** Evaluate resource shares and issuer/admin permissions separately, including regional deployment and key custody; sharing alone is not authorization proof.

**Handoff:** PKI/IAM owner: cross-account issuance and regional trust-boundary design. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T014

**Topic:** Revocation, CRL/OCSP reachability and CA lifecycle

**Trigger:** Private CA certificates need revocation or rotation.

**Evidence:** OCSP/CRL configuration, client reachability/caching, CRL bucket access, key rotation and CA decommission plan.

**Decision:** Assess client CRL/OCSP reachability, caching/failure behavior, protected distribution and rotation continuity; consider partitioned CRLs only after current client/service compatibility review.

**Handoff:** PKI owner: revocation, trust rotation and CA retirement plan preserving existing-chain validation. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T015

**Topic:** Private CA integration: ACM, Kubernetes, SCEP and AD

**Trigger:** Kubernetes, device/MDM or directory certificate issuance.

**Evidence:** Integration type, identities, trust distribution, renewal and operational owner.

**Decision:** Match ACM, cert-manager/Kubernetes, SCEP/MDM or Active Directory integration to actual identities, trust delivery and renewal ownership.

**Handoff:** PKI and platform owner: chosen connector's identity, enrollment and renewal design; no automatic connector setup. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T016

**Topic:** CA cost, issuance volume and unused resources

**Trigger:** Certificate/CA service selection or cost review.

**Evidence:** Certificate type/exportability, active CAs, issuance/OCSP volume, trial and current pricing/SLA/compliance requirements.

**Decision:** Compare CA count, issuance/revocation volume and certificate export needs with current pricing and assurance requirements; unused CA retirement must preserve revocation and trust continuity.

**Handoff:** PKI/FinOps owner: costed lifecycle options and dependency-aware retirement proposal. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

# Detective, Security Hub and CSPM lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse the selected [existing service procedures](../../SKILL.md) for configuration and existing findings metadata only. Do not start investigations, queries, analyses, exports or response automation.

## T042

**Topic:** Fit alongside Hub and GuardDuty Investigation

**Trigger:** Need triage or deep forensic reconstruction.

**Evidence:** Existing tooling, analyst skills, EKS need and desired raw-log depth.

**Decision:** Compare fast triage with forensic timelines, EKS needs and analyst skills; verify current Investigation capabilities rather than assuming equivalence.

**Handoff:** Incident analyst: tool selection and bounded forensic plan using existing evidence. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T043

**Topic:** Enrollment, source packages and GuardDuty update cadence

**Trigger:** Detective present or recommended.

**Evidence:** Graph/package/member state and GuardDuty publishing interval; verify eligibility separately.

**Decision:** Reconcile graph packages, enrollment and publishing freshness; treat current eligibility as separate from GuardDuty's signal contribution.

**Handoff:** Detective owner: enrollment/source-freshness plan for the authorized scope only. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T044

**Topic:** Private access and analyst authorization

**Trigger:** Private-only access or investigator onboarding.

**Evidence:** PrivateLink path and endpoint policy, analyst role access to aggregated sensitive data.

**Decision:** Review analyst access to aggregated sensitive data and private endpoint policy/connectivity; a working console does not establish least privilege.

**Handoff:** Detective/IAM/network owner: analyst-role and private-access design for approved investigators. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T045

**Topic:** Security Lake integration

**Trigger:** Detective and Security Lake both present.

**Evidence:** Integration state, Athena permissions and source availability.

**Decision:** Check integration readiness, available sources and Athena permissions with supplied configuration; neither service's presence proves usable correlation.

**Handoff:** Detective/Lake analyst: integration and bounded query plan; do not query stored data here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T046

**Topic:** Finding groups, entity pivots, threat hunting and embedded links

**Trigger:** Need deep investigation or SIEM-to-Detective pivot.

**Evidence:** Existing investigation indicators, known entity/time scope, analyst access and external alert link context.

**Decision:** Choose entity/time pivots, finding groups, timelines and SIEM links from the investigation question; existing summary reads do not authorize a new investigation or threat hunt.

**Handoff:** Incident analyst: scoped forensic reconstruction/hunting task with known indicators and time window. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T047

**Topic:** Hub/CSPM split, prerequisites, policies versus deployments

**Trigger:** Unified Hub or central rollout.

**Evidence:** V2 Hub state, linked regions, org policy targets/application and source-service states.

**Decision:** Distinguish unified Hub, CSPM, regional aggregation and producer deployment; organization policy existence is not successful member application.

**Handoff:** Security platform owner: producer and central-policy application reconciliation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T048

**Topic:** Network Scanning opt-in and exclusions

**Trigger:** Public endpoints need effective reachability assessment.

**Evidence:** Supported target types, current policy, scan authorization, exclusion tags and owner; no active scan in audit.

**Decision:** Consider Network Scanning only for an established reachability-assessment need and authorized eligible targets; inspect existing policy/exclusions, not active probing.

**Handoff:** Hub/AppSec owner: current eligibility and separately authorized scanning plan documenting excluded coverage. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T049

**Topic:** Partner Extended plan selection

**Trigger:** Partner coverage needed.

**Evidence:** Required partner capability, connector and separate Marketplace subscription/cost.

**Decision:** Choose partner Extended coverage from a concrete missing capability; connector health and Marketplace subscription/terms require separate evidence.

**Handoff:** Security platform/procurement owner: partner capability, integration and subscription decision. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T050

**Topic:** Exposure-first findings, attack paths, traits and trends

**Trigger:** Hub findings summary.

**Evidence:** OCSF Exposure details, contributing traits/signals, resource scope and trends.

**Decision:** Preserve Exposure-first summaries and source severity; interpret traits/signals and trends with current Likelihood/Impact documentation, not invented score transformations.

**Handoff:** Incident analyst: evidence-backed attack-path and contributing-signal review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T051

**Topic:** Managed and self-hosted AI inventory coverage

**Trigger:** Managed AI or self-hosted models/agents.

**Evidence:** Hub AI resource metadata plus Inspector/GuardDuty signal prerequisites, scan modes and model-cache/custom paths.

**Decision:** Compare actual managed/self-hosted AI use with Hub resource metadata and producer prerequisites, including model caches/custom scan paths; provisioning-only inventory cannot prove absence.

**Handoff:** AI/platform security owner: inventory blind-spot and producer-signal coverage plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T052

**Topic:** ITSM response, automation ordering and connector operation

**Trigger:** Finding routing/response integration.

**Evidence:** Connector/rule details, ordering and downstream ownership/delivery evidence.

**Decision:** Assess ordered routing rules, connectors and update handling against ticket ownership and delivery evidence; no automatic response or severity/suppression changes.

**Handoff:** SecOps/ITSM owner: idempotent routing and response-approval design with preserved finding severity. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T053

**Topic:** Azure connector and multi-cloud prerequisites

**Trigger:** Azure estate confirmed.

**Evidence:** Azure app/federation permissions and subscription scope, connector health and AWS/third-party ownership.

**Decision:** For confirmed Azure use, inspect supplied subscription scope, federation/app permissions and connector health without collecting secrets or crawling another cloud.

**Handoff:** Azure IAM and Hub integration owners: scoped federation, ingestion and operational ownership review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T054

**Topic:** Cost review beyond scan enablement

**Trigger:** Unified pricing review.

**Evidence:** Resource/IAM counts, pricing tier, Lambda-code add-on and existing usage estimates.

**Decision:** Verify current bundled pricing before comparing scan cadence; review dormant IAM usage and dependencies before proposing resource cleanup.

**Handoff:** FinOps/IAM owner: measured cost drivers and dependency-aware dormant-identity review, without removal here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T055

**Topic:** Standards and migration matched to obligations

**Trigger:** CIS/PCI/CUI/AI obligations.

**Evidence:** Current standards catalog, active standards, overlap/retirement plan and obligations.

**Decision:** Match standards to business obligations and AI workloads; verify current versions/retirements and compare coverage during migration, including AI inventory context.

**Handoff:** Compliance/platform owner: standards migration and control ownership plan with dated catalog evidence. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T056

**Topic:** Central configuration, integration duplication and recorder mode

**Trigger:** CSPM standalone or coexisting Hub.

**Evidence:** Policy application, regional recorder/status/scope, ingestion overlap and downstream dependencies.

**Decision:** Resolve recorder mode, actual policy application and duplicate consumers before recommending consolidation; retain dependencies such as Macie publishing and regional aggregation.

**Handoff:** CSPM/platform owner: recorder and ingestion migration design with consumer continuity checks. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T057

**Topic:** Failed-control prioritization and remediation instructions

**Trigger:** CSPM findings.

**Evidence:** Active control result, severity, remediation link and resource owner.

**Decision:** Use active control evidence and current remediation documentation to identify the responsible resource owner; do not alter service severity or turn factual summaries into advice.

**Handoff:** Resource owner: separately reviewed control-specific remediation and re-evaluation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T058

**Topic:** Customized insights and parameter/exception review

**Trigger:** Custom compliance views or controls not applicable.

**Evidence:** Business context, group-by needs, control parameters and documented disabled reason.

**Decision:** Assess custom insight groupings and control parameters against obligations; an exception needs applicability evidence and compensating coverage, never finding suppression.

**Handoff:** Compliance owner: parameter/insight design and documented applicability decision with retained audit history. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T059

**Topic:** Finding lifecycle, update-aware tickets and retention

**Trigger:** Remediation verification or long-term audit history.

**Evidence:** Finding ID/update transitions, evaluation cadence, archived retention and external history requirements.

**Decision:** Correlate finding updates to stable tickets and evaluation cadence; verify current retention before choosing external history. A refreshed timestamp alone does not prove remediation.

**Handoff:** SecOps/compliance owner: update-aware ticket and retention design, preserving original finding records. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T060

**Topic:** Automation, ASR and third-party response ownership

**Trigger:** CSPM automated response considered.

**Evidence:** Rules/order/admin scope, ASR deployment context, response owner and approvals.

**Decision:** Review automation ordering, admin scope and response authority, including ASR or third-party ownership; do not author rules, run remediation or suggest suppression.

**Handoff:** SecOps automation owner: human-approved response design and rollback criteria excluding suppression/severity changes. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

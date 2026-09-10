# AWS Security Service Recommendations

This reference and its support files inherit all [aws-security global rules](../SKILL.md). Use only when selected by the parent routing instructions. Existing factual checks and findings summaries retain their service procedures and ordering.

## Overview

Recommends AWS security services based on what is actually deployed. Runs in three passes:

1. **Inventory** — discover which resource types exist in the account
2. **Enablement** — check which security services and protection plans are on
3. **Recommend** — map inventory to services, report gaps ranked by priority

The output is a recommendation report, not a set of changes. Enabling a security service
has cost and operational consequences, so this skill reads and advises; the user decides.

Recommendations follow the [AWS Security Services Best Practices
guide](https://aws.github.io/aws-security-services-best-practices/).

Execute commands using the AWS MCP server when connected (sandboxed execution, audit
logging, observability). Fall back to AWS CLI or shell otherwise.

For MCP-loaded content, retrieve skill `aws-security` through `retrieve_skill` with
`file="references/service-recommendations/<support-file>.md"` for the support files
linked below. Use `file="SKILL.md"` for the parent. For local content, resolve Markdown
links relative to this file. Write requested reports in the user workspace subject to
the disclosure rules below.

## Security Considerations

Assess only authorized accounts and regions using read-only operations. Posture reports
can expose sensitive infrastructure: collect only necessary evidence, excluding credentials,
account emails, target payloads, and secret origin headers. Projections reduce collection;
they do not authorize disclosure. Summarize before displaying or saving results, using
counts and masked identifiers. Explain what sensitive detail is withheld. Reveal identifiers
only when explicitly requested, and complete raw responses only on an explicit raw-output
request; still exclude the prohibited fields above. Enablement remains a separate,
operation-specific least-privilege handoff.

## Common Tasks

### Domain selection

After selecting recommendation mode, load
[domain routing](service-recommendations/domain-routing.md) before discovery. Use its
requirement predicates to select lifecycle topics and focused evidence; the inventory
matrix alone is not full-guide coverage. Load only the relevant domain references,
including existing-service tuning and public/private AppSec when requested.

### 0. Verify Dependencies

Select the workflow below before discovery; establish only its relevant scope.

**Constraints:**

- You MUST confirm identity with `aws sts get-caller-identity` before running any check; report a masked account scope unless the user explicitly requests
  identifiers. Establish region separately from the user or explicit command scope. When the user
  specifies a profile, propagate `--profile <selected-profile>` to every CLI call, including
  identity and global-service reads; configure the equivalent session for MCP execution.
  Never silently fall back to default credentials
- You MUST establish whether this is an AWS Organizations member, the management account,
  or a standalone account (`aws organizations describe-organization` with the projection
  in the inventory reference) — recommendations differ substantially, and an `AWSOrganizationsNotInUseException` means
  standalone
- You MUST treat every command in this skill as read-only. You MUST NOT call any
  `create-*`, `enable-*`, `update-*`, `put-*`, or `delete-*` operation
- You MUST preserve evidence states: successful observations remain observed even if another
  scope fails; documented, validated not-enabled responses are negative evidence. Ambiguous
  denials, transport errors, and missing scope are UNKNOWN; deliberately unrun checks are
  NOT ASSESSED; verified irrelevant checks are NOT APPLICABLE. Never turn incomplete
  evidence into absence or a gap

See [service-recommendations/iam-permissions.md](service-recommendations/iam-permissions.md) for the read-only
permissions each pass requires.

### 1. Classify the Request

| User intent | Workflow |
|---|---|
| What security services should I enable? | A: Full Assessment |
| Which plans or coverage improvements does service X warrant? | B: Single-Service Recommendation |
| Audit org-wide security coverage | C: Organization Review |
| Why is my security spend high / what can I cut? | D: Cost-Coverage Review |

**Constraints:**

- You MUST establish assessed accounts and regions, using the user's scope or confirming
  a default. Reuse complete, scope-matched observations; run global discovery once and
  only relevant regional reads. Preserve pagination, partial results, and failures
- External-access analyzers require evidence in each relevant region. Unused-access
  findings do not vary by region; do not multiply analyzers for regional table coverage.
  Verify internal-access scope separately
- You MUST state the assessed region explicitly in the report
- You SHOULD state that the guide recommends all-region enablement for Security Lake and
  Detective (idle regions collect almost nothing, activity in an unexpected region is then
  captured, and blocking unused regions by SCP is the alternative), then confirm with the
  user before including it in the report

### 2. Workflow A — Full Assessment

Select applicable domains and confirm requirements first; run the relevant pass 1 and
pass 2 reads, then produce the pass 3 report. Cover the selected lifecycle topic decisions
and handoffs as well as service enablement. The source index is provenance, not a reason
to read every account or all domains.

**Pass 1 — Inventory.** See
[service-recommendations/inventory-commands.md](service-recommendations/inventory-commands.md) for the commands.

Discover which of these exist: EC2 instances, EBS volumes, ECR repositories, ECS
clusters and their launch types, EKS clusters and their compute types, Lambda functions,
S3 buckets, RDS and Aurora clusters, CloudFront distributions, ALBs, API Gateway APIs,
public-facing endpoints, VPCs and their AZs, and ACM certificates and Private CAs.

**Constraints:**

- You MUST justify workload recommendations with discovered resources or confirmed use.
  Baseline and organization rows instead require their stated account/activity conditions
- You MUST record a resource count per type — the count drives cost estimates and the
  Macie automated-discovery-vs-jobs decision
- You MUST distinguish EKS on EC2 from EKS on Fargate, and ECS on EC2 from ECS on
  Fargate. GuardDuty Runtime Monitoring does not support EKS on Fargate, and the ECS
  path requires Fargate platform 1.4.0 or LATEST
- You SHOULD note when a resource type is absent — "no ECR repositories, so Inspector
  ECR scanning is not applicable" is a useful line in the report

**Pass 2 — Enablement.** See
[service-recommendations/enablement-checks.md](service-recommendations/enablement-checks.md) for the commands and
pass conditions.

**Constraints:**

- You MUST check protection plans and scan types individually, not just whether the
  parent service is on. A GuardDuty detector with `S3_DATA_EVENTS` disabled is a real
  gap that `list-detectors` alone will not surface
- You MUST determine whether Security Hub CSPM runs standalone or alongside unified
  Security Hub before judging AWS Config. Standalone CSPM needs a customer-managed Config
  recorder for most control checks. With both enabled, CSPM creates and manages the
  service-linked recorder `AWSConfigurationRecorderForSecurityHubCSPM`, `Config.1` always
  passes, and a missing customer-managed recorder is not a gap
- You MUST report the delegated administrator relationship for each service in an org context,
  masking identifiers unless explicitly requested,
  and flag when they differ. The Security Reference Architecture places GuardDuty,
  Security Hub, Inspector, Macie, and Detective in one security tooling account, and
  Security Lake in the Log Archive account
- You MUST check auto-enable settings separately from current enablement — an org with
  every existing account covered but auto-enable off has a growing gap under local
  configuration. Central configuration exempts its auto-enable fields; it does not prove
  policy association or member coverage. Report those UNKNOWN if unverified
- You SHOULD check the finding aggregation region for Security Hub and note whether
  cross-region aggregation is configured
- You MUST check unified Security Hub and Security Hub CSPM separately. They are different
  products sharing the `securityhub` API namespace — the unified service uses the `*V2`
  operations. Both can be enabled at once; coexistence alone does not prove duplication.
  Require observed overlapping
  ingestion, then audit EventBridge, SIEM, ticketing, and Lambda consumers before suggesting
  changes. Keep Macie publishing to CSPM and retain the cross-region finding aggregator;
  central configuration depends on it
- You MUST NOT report ACM as "not enabled" — it is always available. Report certificate
  expiry-monitoring gaps instead
- You MUST treat Network Firewall's absence as a design question rather than a gap. It is
  not a baseline service; recommend it only where egress or east-west inspection is a
  stated requirement

**Pass 3 — Report.** See
[service-recommendations/recommendation-matrix.md](service-recommendations/recommendation-matrix.md) for the
inventory-to-service mapping and priority assignments.

**Constraints:**

- You MUST report each recommendation with: the service or plan, the discovered resources or
  verified baseline conditions that justify it, current state, priority, and the guide section it comes from — or
  `n/a (not guide-sourced)` where none exists. You MUST NOT fabricate a citation to fill
  that field
- You MUST order recommendation rows by priority, Critical first. Findings remain separate:
  GuardDuty AttackSequence findings and Security Hub Exposure findings come first in their
  respective findings summaries, before service-reported severity breakdowns
- You MUST include a cost note on every recommendation — these services bill on usage,
  and a recommendation without a cost signal is not actionable. Direct the user to each
  service's free trial and usage page rather than quoting prices, which change
- You MUST NOT apply a workload row without its trigger; preserve conditional baseline rows
- You MUST NOT recommend enabling S3 Malware Protection across all buckets — it is
  enabled per bucket, and the guide states it is "not intended to be deployed across
  your entire S3 estate." Recommend it only for buckets taking untrusted or third-party
  uploads, and ask the user which buckets those are
- You MUST describe advisory actions in prose and provide a separate implementation handoff
  for accepted recommendations. Do not present enablement commands or execute changes

### 3. Workflow B — Single-Service Recommendation

For factual state checks or findings summaries, follow the
[parent registry](../SKILL.md) to the existing service procedure without expanding into recommendations.
For accepted changes, describe a separate specialist or operation-specific implementation
handoff; it does not execute as part of this read-only workflow.

Run only the relevant section of
[service-recommendations/enablement-checks.md](service-recommendations/enablement-checks.md), plus the pass 1
commands for the resource types that service covers. Load its selected domain reference
from [domain routing](service-recommendations/domain-routing.md) for lifecycle, suitability
and focused manual-evidence questions beyond enablement.

**Constraints:**

- Reuse successful, complete inventory for this scope; collect only missing evidence for
  the service's resource types. Inspector recommendations need EC2, ECR, and Lambda context
- You MUST report configuration quality, not just on/off: for Inspector that means ECR
  rescan durations and Deep Inspection; for GuardDuty, per-feature status and Runtime
  Monitoring agent coverage

### 4. Workflow C — Organization Review

**Constraints:**

- You MUST run from the delegated administrator account for member visibility, or the
  management account to identify delegated admins. From a member account you can only
  see that account, and you MUST say so rather than reporting partial data as complete
- Detailed account-level enumeration requires an explicit request for that detail. Broad
  "audit coverage" or "recommend services" requests alone do not authorize it. Prefer
  statistics/count APIs where available and reuse authorized scope-matched evidence. Mark
  unrequested member detail and reconciliation NOT ASSESSED, not missing coverage
- Only when detailed enumeration is explicitly requested, reconcile complete per-service
  member IDs/status against scoped ACTIVE account IDs, including "Not a member" states.
  Follow all pages and preserve partial evidence: report enrolled/not-enrolled counts only
  with complete relevant reads; otherwise retain observations and mark the unresolved
  remainder UNKNOWN. Include delegated admin and auto-enable state separately from
  central-policy coverage. Never infer complete coverage from counts or policy existence
- You SHOULD recommend an AWS Organizations Inspector policy where Inspector drift is a
  concern; member accounts cannot disable policy-managed scanning via the Inspector API
- You SHOULD recommend Security Hub central configuration over per-account setup

### 5. Workflow D — Cost-Coverage Review

**Constraints:**

- Absence-based cost cuts require complete relevant scoped inventory — for example,
  Inspector ECR scanning with no repositories. Denied, partial, or provisioning-only AI
  reads cannot establish absence
- You MUST establish which pricing model applies before quoting levers. With unified
  Security Hub enabled, Inspector and Security Hub CSPM are included in the essentials plan
  (priced per resource, and IAM users and roles count), GuardDuty bills through the Threat
  Analytics plan, and Macie and Detective bill separately. Several standalone levers, such
  as Inspector ECR rescan duration, stop being cost levers under essentials. Point the user
  at the Security Hub console Cost Estimator and Usage page for a consolidated number
- You MUST present the visibility tradeoff alongside any reduction. The guide is explicit:
  "Lowering cost by disabling controls lowers visibility, and the savings are rarely worth
  a blind spot in a production account. Tune lower environments first."
- You MUST NOT recommend disabling a foundational data source. GuardDuty's CloudTrail,
  VPC Flow Log, and DNS log analysis cannot be removed (they are still metered per GB), and
  disabling S3 Protection reduces coverage rather than waste. Disabling any GuardDuty
  protection plan also narrows what Extended Threat Detection can correlate
- You SHOULD surface the guide's levers before disablement: CloudWatch usage alarms per
  GuardDuty protection plan; scope narrowing over turning a scan type off (S3 Malware
  Protection per bucket, the Inspector EC2 exclusion tag, noting that an excluded instance
  looks identical to a clean one); Macie automated discovery instead of discovery jobs;
  Security Lake retention trimming, removing duplicate native-log collection, and a short
  expiry on the CloudTrail bucket; Detective scoped away from sandbox accounts; CSPM
  ingestion filtering for integrations nobody reads, with an SCP paired to any control
  disabled because the service is unused. GuardDuty suppression rules reduce downstream
  noise, not metering: findings are still generated and archived
- You SHOULD note that Runtime Monitoring suppresses VPC Flow Log billing for instances
  running an active agent, which offsets part of its cost

## Troubleshooting

**`BadRequestException` / `InvalidInputException` on GuardDuty
`describe-organization-configuration`** — Message reads "a delegated administrator account
has not been enabled". This is a scope error, not a misconfiguration: you are in a member
account. Note that GuardDuty raises `BadRequestException` here rather than `AccessDenied`,
so an error-string match on "denied" will miss it.

**`BadRequestException` on GuardDuty `list-organization-admin-accounts`** — Message reads
"you are not the admin account for your AWS Organization". Same cause. Report scope as
single-account and list which checks were skipped.

**An account can be a delegated administrator and still fail these calls** — Delegated
admin status is per service. `organizations list-delegated-administrators` returning the
current account does not mean it is GuardDuty's delegated admin. Check each service
separately and never infer one service's admin from another's.

**`AccessDenied` on an organization check** — Scope or permission is unresolved unless
independent evidence identifies the cause. Preserve account observations; mark org coverage UNKNOWN.

**`BadRequestException: The request is rejected because the current account is not
associated with a detector`** — GuardDuty is not enabled in this region. Treat as NOT
ENABLED, not an error.

**`ResourceNotFoundException` from `securityhub describe-hub`** — Security Hub is not
enabled in this region. Treat as NOT ENABLED.

**`AccessDeniedException` from `inspector2 batch-get-account-status`** — Inspector has
never been activated in this region, or the caller lacks `inspector2:BatchGetAccountStatus`.
Report UNKNOWN unless a validated service response resolves it. Optional IAM simulation
uses a resolved IAM principal ARN and cannot prove disablement even when it returns allowed.

**`macie2 get-macie-session` returns `AccessDeniedException`** — Check the message body.
`AccessDeniedException: Macie is not enabled` means not enabled; an
`AccessDeniedException` without that validated message is UNKNOWN. Optional simulation
can help diagnose permissions but cannot turn an ambiguous error into not enabled.

**`guardduty list-coverage` returns `null` Resources** — Expected when
`RUNTIME_MONITORING` is `DISABLED`. Check the feature status from `get-detector` first;
do not report this as a coverage failure.

**Successful, complete empty `detective list-graphs`** — No graph observed in this scope.
The guide states GuardDuty is a prerequisite; verify current Detective eligibility before
presenting it as mandatory. If unverified, report eligibility UNKNOWN, retain GuardDuty's
findings-integration role, and do not recommend extra enablement solely for that gate.

**Config recorder exists but reports no resources (standalone CSPM)** — Check
`describe-configuration-recorder-status` for `recording: true` and `lastStatus: SUCCESS`,
and confirm the recording group covers the resource types the Security Hub standards evaluate. With unified Security
Hub also enabled, the service-linked recorder `AWSConfigurationRecorderForSecurityHubCSPM`
handles scoping and this check does not apply.

## Additional Resources

- [service-recommendations/inventory-commands.md](service-recommendations/inventory-commands.md) — Pass 1 resource discovery commands
- [service-recommendations/enablement-checks.md](service-recommendations/enablement-checks.md) — Pass 2 per-service checks and pass conditions
- [service-recommendations/recommendation-matrix.md](service-recommendations/recommendation-matrix.md) — Inventory-to-service mapping with priority
- [service-recommendations/iam-permissions.md](service-recommendations/iam-permissions.md) — Read-only permissions by pass
- [AWS Security Services Best Practices](https://aws.github.io/aws-security-services-best-practices/) — Source for the service recommendations and tuning guidance. See Provenance below for what came from elsewhere.
- [AWS Security Reference Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html) — Delegated administrator account placement
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

## Provenance

Recommendation provenance is the 44 English navigation pages at guide commit
`f2b28d7c31c490ad676273307cbdb900c16daed8`. The
[source index](service-recommendations/source-index.md) maps 133 substantive topic groups
to domain trigger/evidence/decision/handoff contracts, including all WAF and Network
Firewall subpages and public/private Security Agent lifecycle guidance. Repeated headings,
navigation, examples and incomplete source sections are distinguished from substantive
recommendations. Full coverage is advisory; source implementation recipes and prohibited
suppression/severity-changing advice are not adopted. Use the
[domain contract](service-recommendations/domain-routing.md) for current-document checks,
preview qualifications and known NAT/TLS/WAF source conflicts.

Two services in this skill are **not** covered by that guide as services: **IAM Access
Analyzer** and **AWS Config**. Access Analyzer is included as a no-additional-cost posture
check. Config is included only for the case where Security Hub CSPM runs standalone, where
the CSPM guide says CSPM relies on your Config recorder for most controls. When unified
Security Hub and CSPM are both enabled, CSPM creates and manages a service-linked recorder
and the guide says you do not configure Config yourself.

API operation names and enum values are from the AWS API models, not the guide, which is
prose and does not specify API shapes. Verify against `aws <service> help` if an operation
appears to have changed.

The recommendation priority rankings, the three-pass structure, and the inventory-to-service trigger
mapping are this skill's own design — the guide recommends practices but does not rank
them. So are the `AutoEnableOrganizationMembers: ALL` pass condition, the DNS Firewall
fail-open check, and the PCI DSS v3.2.1 retirement fact. When reporting, attribute the
recommendation to the guide and the priority to this skill rather than implying the guide
assigned it. These labels never replace observed findings severity or the parent
AttackSequence/Exposure-first findings ordering.

Network Firewall coverage includes deployment, rule semantics and address-variable
applicability, TLS suitability/trust, logging and operational decisions in its domain
reference. Rule authoring/execution, code, flow capture/flush and analysis initiation
remain outside this read-only assessment; handoffs carry specific evidence and decisions.

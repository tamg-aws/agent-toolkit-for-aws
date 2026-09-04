---
name: recommending-security-services
description: >
  Inventory the infrastructure in an AWS account, check which AWS security services and
  protection plans are enabled, and recommend the ones that the deployed workloads
  actually warrant — GuardDuty and its protection plans, Security Hub and Security Hub
  CSPM standards, Inspector scan types, Macie, Detective, Security Lake, IAM Access
  Analyzer, AWS Config, ACM certificate expiry monitoring, Network Firewall, Route 53
  Resolver DNS Firewall, and Firewall Manager. Use when the user asks what security
  services they should turn on, whether
  their account is missing security coverage, to audit security service enablement, to
  review security posture for an organization or a single account, or to justify
  security service spend against what is deployed. Do NOT use for configuring an
  individual service in depth (use the waf, shieldadvanced, route53, or
  securing-s3-buckets skills), for scanning application source code, or for
  remediating individual findings.
---

# Recommending AWS Security Services

## Overview

Recommends AWS security services based on what is actually deployed. Runs in three passes:

1. **Inventory** — discover which resource types exist in the account
2. **Enablement** — check which security services and protection plans are on
3. **Recommend** — map inventory to services, report gaps ranked by severity

The output is a recommendation report, not a set of changes. Enabling a security service
has cost and operational consequences, so this skill reads and advises; the user decides.

Recommendations follow the [AWS Security Services Best Practices
guide](https://aws.github.io/aws-security-services-best-practices/).

Execute commands using the AWS MCP server when connected (sandboxed execution, audit
logging, observability). Fall back to AWS CLI or shell otherwise.

## Common Tasks

### 0. Verify Dependencies

**Constraints:**

- You MUST confirm identity and region with `aws sts get-caller-identity` and report the
  account ID to the user before running any check
- You MUST establish whether this is an AWS Organizations member, the management account,
  or a standalone account (`aws organizations describe-organization`) — the
  recommendations differ substantially, and an `AWSOrganizationsNotInUseException` means
  standalone
- You MUST treat every command in this skill as read-only. You MUST NOT call any
  `create-*`, `enable-*`, `update-*`, `put-*`, or `delete-*` operation
- You SHOULD note that `AccessDenied` on a check means "unknown", not "not enabled" —
  report it as such rather than recommending a service that may already be on

See [references/iam-permissions.md](references/iam-permissions.md) for the read-only
permissions each pass requires.

### 1. Classify the Request

| User intent | Workflow |
|---|---|
| What security services should I enable? | A: Full Assessment |
| Is service X enabled / configured right? | B: Single-Service Check |
| Audit org-wide security coverage | C: Organization Review |
| Why is my security spend high / what can I cut? | D: Cost-Coverage Review |

**Constraints:**

- You MUST ask which region(s) to assess, or confirm the default — every service in this
  skill except IAM Access Analyzer is regional, so a single-region answer is incomplete
  by construction
- You MUST state the assessed region explicitly in the report
- You SHOULD ask whether unused regions matter to the user before recommending
  all-region enablement

### 2. Workflow A — Full Assessment

Run pass 1, then pass 2, then produce the pass 3 report.

**Pass 1 — Inventory.** See
[references/inventory-commands.md](references/inventory-commands.md) for the commands.

Discover which of these exist: EC2 instances, EBS volumes, ECR repositories, ECS
clusters and their launch types, EKS clusters and their compute types, Lambda functions,
S3 buckets, RDS and Aurora clusters, CloudFront distributions, ALBs, API Gateway APIs,
public-facing endpoints, VPCs and their AZs, and ACM certificates and Private CAs.

**Constraints:**

- You MUST base recommendations on discovered resources, never on assumption. A service
  recommended without a resource to justify it is a finding the user cannot act on
- You MUST record a resource count per type — the count drives cost estimates and the
  Macie automated-discovery-vs-jobs decision
- You MUST distinguish EKS on EC2 from EKS on Fargate, and ECS on EC2 from ECS on
  Fargate. GuardDuty Runtime Monitoring does not support EKS on Fargate, and the ECS
  path requires Fargate platform 1.4.0 or LATEST
- You SHOULD note when a resource type is absent — "no ECR repositories, so Inspector
  ECR scanning is not applicable" is a useful line in the report

**Pass 2 — Enablement.** See
[references/enablement-checks.md](references/enablement-checks.md) for the commands and
pass conditions.

**Constraints:**

- You MUST check protection plans and scan types individually, not just whether the
  parent service is on. A GuardDuty detector with `S3_DATA_EVENTS` disabled is a real
  gap that `list-detectors` alone will not surface
- You MUST check AWS Config before recommending Security Hub CSPM standards — CSPM
  relies on service-linked Config rules for most control checks, so recommending
  standards without Config produces controls that cannot evaluate
- You MUST report the delegated administrator account for each service in an org context,
  and flag when they differ. The Security Reference Architecture places GuardDuty,
  Security Hub, Inspector, Macie, and Detective in one security tooling account, and
  Security Lake in the Log Archive account
- You MUST check auto-enable settings separately from current enablement — an org with
  every existing account covered but auto-enable off has a growing gap
- You SHOULD check the finding aggregation region for Security Hub and note whether
  cross-region aggregation is configured
- You MUST check unified Security Hub and Security Hub CSPM separately. They are different
  products sharing the `securityhub` API namespace — the unified service uses the `*V2`
  operations. Both can be enabled at once, and that combination produces a
  redundant-aggregation finding
- You MUST NOT report ACM as "not enabled" — it is always available. Report certificate
  expiry-monitoring gaps instead
- You MUST treat Network Firewall's absence as a design question rather than a gap. It is
  not a baseline service; recommend it only where egress or east-west inspection is a
  stated requirement

**Pass 3 — Report.** See
[references/recommendation-matrix.md](references/recommendation-matrix.md) for the
inventory-to-service mapping and severity assignments.

**Constraints:**

- You MUST report each recommendation with: the service or plan, the discovered resources
  that justify it, current state, severity, and the guide section it comes from — or
  `n/a (not guide-sourced)` where none exists. You MUST NOT fabricate a citation to fill
  that field
- You MUST order findings by severity, Critical first
- You MUST include a cost note on every recommendation — these services bill on usage,
  and a recommendation without a cost signal is not actionable. Direct the user to each
  service's free trial and usage page rather than quoting prices, which change
- You MUST NOT recommend a service whose triggering resource type was not found
- You MUST NOT recommend enabling S3 Malware Protection across all buckets — it is
  enabled per bucket, and the guide states it is "not intended to be deployed across
  your entire S3 estate." Recommend it only for buckets taking untrusted or third-party
  uploads, and ask the user which buckets those are
- You SHOULD present the enablement commands for accepted recommendations without running
  them, and say plainly that the user should review each before applying

### 3. Workflow B — Single-Service Check

Run only the relevant section of
[references/enablement-checks.md](references/enablement-checks.md), plus the pass 1
commands for the resource types that service covers.

**Constraints:**

- You MUST still run the inventory commands for that service's resource types — "is
  Inspector configured correctly" cannot be answered without knowing whether EC2, ECR,
  and Lambda resources exist
- You MUST report configuration quality, not just on/off: for Inspector that means ECR
  rescan durations and Deep Inspection; for GuardDuty, per-feature status and Runtime
  Monitoring agent coverage

### 4. Workflow C — Organization Review

**Constraints:**

- You MUST run from the delegated administrator account for member visibility, or the
  management account to identify delegated admins. From a member account you can only
  see that account, and you MUST say so rather than reporting partial data as complete
- You MUST report per-service: delegated admin account ID, member count enrolled, member
  count not enrolled, and auto-enable state
- You MUST check for accounts with status "Not a member" or equivalent — these are
  coverage gaps that aggregate counts hide
- You SHOULD recommend an AWS Organizations Inspector policy where Inspector drift is a
  concern; member accounts cannot disable policy-managed scanning via the Inspector API
- You SHOULD recommend Security Hub central configuration over per-account setup

### 5. Workflow D — Cost-Coverage Review

**Constraints:**

- You MUST identify enabled services whose triggering resources are absent — Inspector
  ECR scanning with no repositories, GuardDuty EKS Protection with no clusters
- You MUST present the visibility tradeoff alongside any reduction. The guide is explicit
  that "lowering costs through disabling controls could lead to potential higher risks
  due to a lack of visibility"
- You MUST NOT recommend disabling a foundational data source. GuardDuty's CloudTrail,
  VPC Flow Log, and DNS log analysis cannot be removed, and disabling S3 Protection
  reduces coverage rather than waste
- You SHOULD surface cheaper equivalents before disablement: Macie automated discovery
  instead of discovery jobs, Security Lake retention trimming instead of source removal,
  GuardDuty suppression rules instead of feature disablement
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

**`AccessDenied` on a `describe-organization-configuration` call** — Same scope conclusion
as above for the services that do return `AccessDenied`.

**`BadRequestException: The request is rejected because the current account is not
associated with a detector`** — GuardDuty is not enabled in this region. Treat as NOT
ENABLED, not an error.

**`ResourceNotFoundException` from `securityhub describe-hub`** — Security Hub is not
enabled in this region. Treat as NOT ENABLED.

**`AccessDeniedException` from `inspector2 batch-get-account-status`** — Inspector has
never been activated in this region, or the caller lacks `inspector2:BatchGetAccountStatus`.
Distinguish the two with `aws iam simulate-principal-policy` before reporting.

**`macie2 get-macie-session` returns `AccessDeniedException`** — Check the message body.
`AccessDeniedException: Macie is not enabled` means not enabled; an
`AccessDeniedException` without that text means the caller lacks the permission. Same
exception type, two different answers — distinguish on the message, and fall back to
`aws iam simulate-principal-policy` when it is ambiguous.

**`guardduty list-coverage` returns `null` Resources** — Expected when
`RUNTIME_MONITORING` is `DISABLED`. Check the feature status from `get-detector` first;
do not report this as a coverage failure.

**Empty `detective list-graphs` with GuardDuty enabled** — Detective is not enabled.
GuardDuty must be on before Detective, so verify GuardDuty first and note the ordering
dependency in the recommendation.

**Config recorder exists but reports no resources** — Check
`describe-configuration-recorder-status` for `lastStatus`, and confirm the recording
group covers the resource types the Security Hub standards evaluate.

## Additional Resources

- [references/inventory-commands.md](references/inventory-commands.md) — Pass 1 resource discovery commands
- [references/enablement-checks.md](references/enablement-checks.md) — Pass 2 per-service checks and pass conditions
- [references/recommendation-matrix.md](references/recommendation-matrix.md) — Inventory-to-service mapping with severity
- [references/iam-permissions.md](references/iam-permissions.md) — Read-only permissions by pass
- [AWS Security Services Best Practices](https://aws.github.io/aws-security-services-best-practices/) — Source for the service recommendations and tuning guidance. See Provenance below for what came from elsewhere.
- [AWS Security Reference Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html) — Delegated administrator account placement
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

## Provenance

Service recommendations, tuning guidance, and cost levers come from the 11 service pages
of the AWS Security Services Best Practices guide.

Two services in this skill are **not** covered by that guide: **IAM Access Analyzer** and
**AWS Config**. Config is included because Security Hub CSPM controls cannot evaluate
without it — that dependency is stated in the CSPM guide. Access Analyzer is included as a
no-additional-cost posture check.

API operation names and enum values are from the AWS API models, not the guide, which is
prose and does not specify API shapes. Verify against `aws <service> help` if an operation
appears to have changed.

The severity rankings, the three-pass structure, and the inventory-to-service trigger
mapping are this skill's own design — the guide recommends practices but does not rank
them. When reporting, attribute the recommendation to the guide and the severity to this
skill rather than implying the guide assigned it.

AWS WAF is in the guide but deliberately not covered here; the `waf` skill implements its
14 sub-pages. Network Firewall's rule authoring is likewise out of scope — this skill
checks its presence and policy configuration only.

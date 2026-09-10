# Pass 3 — Inventory to Service Recommendation Matrix

Workload rows require discovered resources or confirmed use; baseline and organization
rows require their stated conditions. Apply gaps only to validated negative evidence,
not UNKNOWN or NOT ASSESSED checks. Record NOT APPLICABLE when irrelevance is verified.

## Baseline: account activity and stated conditions

These use account activity plus the row-specific conditions rather than a workload trigger.

| Recommendation | Priority | Rationale |
|---|---|---|
| GuardDuty foundational (CloudTrail, VPC flow, DNS analysis) | **Critical** | Threat detection with no data-source configuration; pulls streams directly |
| AWS Config recorder, **when Security Hub CSPM runs standalone** | **Critical** | Standalone CSPM uses your recorder for most controls. With unified Security Hub also enabled, CSPM manages the service-linked recorder `AWSConfigurationRecorderForSecurityHubCSPM` and this row does not apply |
| Security Hub CSPM with FSBP | **Critical** | Baseline posture standard; the guide's starting point |
| IAM Access Analyzer external-access analyzer | **High** | Surfaces unintended external access to resources |
| Cross-region finding aggregation, when more than one region is in use | **High** | Regional services produce fragmented findings otherwise |

## Triggered by compute

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| Any EC2 instance | GuardDuty `EBS_MALWARE_PROTECTION` | High |
| Any EC2 instance | Inspector `EC2` scanning through Enhanced EC2 Scanning (the VM Scanner), not the legacy SSM plugin | High |
| EC2 instance, SSM-managed | GuardDuty `RUNTIME_MONITORING` with `EC2_AGENT_MANAGEMENT` | High |
| EC2 instance, **not** SSM-managed, Runtime Monitoring wanted | Default Host Management Configuration via SSM Quick Setup first; GuardDuty EC2 agent management requires SSM | High |
| Any EC2 instance | Inspector Deep Inspection (Linux, Windows, and macOS with Enhanced EC2 Scanning) | Medium |
| Any Lambda function | Inspector `LAMBDA` **and** `LAMBDA_CODE` | High |
| Any Lambda function | GuardDuty `LAMBDA_NETWORK_LOGS` | Medium |
| Bedrock, Bedrock AgentCore, or SageMaker AI in use | GuardDuty `AI_PROTECTION` | High |

Inspector EC2 scanning today runs through the Inspector VM Scanner (Enhanced EC2 Scanning),
which the guide recommends over the legacy SSM plugin. Automatic installation uses Systems
Manager; manual installation uses the OS package manager and needs no SSM at all, so a
non-SSM-managed instance is no longer limited to agentless coverage. Agentless (hybrid)
scanning remains available for hosts that run no agent: agent-based is event-driven,
agentless evaluates once per 24 hours. CIS benchmark scans still run on the SSM plugin and
still need SSM-managed instances. If an account was set up before the VM Scanner existed,
flag the migration as its own finding.

Deep Inspection default paths vary by operating system (on Linux they include `/usr/lib`,
`/usr/lib64`, `/usr/local/lib`, `/usr/local/lib64`); check the current list instead of
assuming it. Each account may add 5 custom paths, plus 5 org-wide from the delegated admin,
for up to 10. Software installed outside those paths (an application under `/opt`, a
database on `D:\`) produces no findings and no warning, and the instance still shows as
scanned. Ask where teams actually install software before trusting a "Deep Inspection
enabled" result.

Windows instances are discovered and scanned automatically. Under the legacy SSM plugin they
were scanned at discovery and then every 6 hours (adjustable); the guide calls Windows "the clearest case for moving to the
Inspector VM Scanner". Confirm the interval for whichever path is in use.

## Triggered by containers

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| Any ECR repository | Inspector `ECR` scanning, continuous | High |
| ECR repository with images | ECR rescan duration tuned to build cadence | Medium |
| Any EKS cluster | GuardDuty `EKS_AUDIT_LOGS` | High |
| EKS cluster on EC2 nodegroups | GuardDuty `RUNTIME_MONITORING` with `EKS_ADDON_MANAGEMENT` | High |
| EKS cluster, Fargate profiles only | **Do not** recommend Runtime Monitoring — unsupported | n/a |
| ECS cluster on Fargate | GuardDuty `RUNTIME_MONITORING` with `ECS_FARGATE_AGENT_MANAGEMENT` | High |
| ECS cluster on EC2 | GuardDuty `RUNTIME_MONITORING`; the agent on the container instances follows the EC2 path per the guide's linked prerequisites, not an automated ECS setting | High |
| Any EKS cluster | Security Lake `EKS_AUDIT` source | Medium |
| EKS cluster | Detective for cross-account container visibility | Medium |

On ECR activation with continuous scanning, Inspector picks up images pushed within 30
days or pulled within the last 90. Account for ECR lifecycle policies deleting images
before the rescan window closes.

Inspector maps ECR images to running ECS and EKS containers — use this to prioritize. A
vulnerable image sitting unused in a registry is a different risk from one running in
production.

ECS specifics: Fargate platform 1.4.0 or LATEST, plus a task execution role. Tasks already
running when monitoring is enabled need a fresh deployment — include that deployment requirement in the separate implementation handoff. On Fargate the agent can only be managed by GuardDuty, never
manually; on EC2 container instances it follows the EC2 agent path.

EKS specifics: only the delegated administrator can enable or disable Automated agent
configuration for members.

Extended Threat Detection is on for every GuardDuty account at no additional cost and needs
no enablement. What it can correlate depends on Runtime Monitoring and S3 Protection being
on, which is a reason to prioritize those two plans and a reason not to disable them for
cost.

## Triggered by data

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| Any S3 bucket | GuardDuty `S3_DATA_EVENTS` | High |
| Any S3 bucket | Macie automated sensitive data discovery | High |
| Macie enabled | Classification export to S3 within 30 days | High |
| Macie enabled, sensitive data findings not published to Security Hub CSPM | Enable publishing so Security Hub exposure scoring and GuardDuty attack sequences see sensitive-data traits | High |
| S3 bucket taking untrusted or third-party uploads | GuardDuty S3 Malware Protection, **per bucket** | High |
| Many or large S3 buckets | Automated discovery over discovery jobs | Medium |
| Dataset requiring full coverage, not sampling | Targeted discovery job in addition | Medium |
| RDS / Aurora database meeting current supported engine/version and applicable prerequisites | GuardDuty `RDS_LOGIN_EVENTS` | High |
| Backup vaults protecting recovery-critical workloads (EBS snapshots, AMIs, S3 recovery points) | Malware Protection for AWS Backup, those vaults first | Medium |

For RDS Protection, validate engine/version and applicable conditions against the current
[GuardDuty supported-database table](https://docs.aws.amazon.com/guardduty/latest/ug/rds-protection.html#rds-pro-supported-db),
including read-replica prerequisites. Use this developer-guide table over incomplete
best-practices-guide coverage labels. Unresolved eligibility stays UNKNOWN; eligibility
and plan enablement do not themselves prove effective coverage.

S3 Malware Protection is enabled **per bucket**, not per account or organization. The
guide states it is "not intended to be deployed across your entire S3 estate." Ask which
buckets receive untrusted input; recommend only those. It can run standalone without the
rest of GuardDuty.

Macie retains discovery results for only 90 days, and the results repository must be
configured within the first 30 days. The repository logs an entry per file examined even
when nothing sensitive was found, which is how you confirm coverage and find unscannable
files.

Macie tuning order: enable all managed data identifiers (no per-identifier charge), then
add custom data identifiers for
organization-specific data such as employee IDs or internal classifications.

## Triggered by network and edge

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| Internet-facing ALB **not** behind CloudFront, no WebACL | AWS WAF — route to the `waf` skill | **Critical** |
| CloudFront distribution with application logic behind it, no WebACL | AWS WAF at the CloudFront layer — route to the `waf` skill | **Critical** |
| ALB behind CloudFront with a distribution WebACL and verified origin access restrictions | Distribution protection may suffice; do not automatically duplicate WAF on the ALB | n/a |
| CloudFront serving only static cached content, no WebACL | Informational; the guide calls WAF here uncommon and low value | Low |
| Internal ALB, no WebACL | n/a unless it indirectly handles unfiltered traffic from a network you do not control | n/a |
| API Gateway REST API not behind CloudFront, no WebACL | AWS WAF — route to the `waf` skill | High |
| Internet-facing NLB or non-HTTP ingress with an established traffic-inspection requirement | Evaluate Network Firewall for that requirement; presence alone is not a gap. Shield Advanced follows its own row | Medium |
| Internet-facing web application with application logic (ALB, CloudFront, API Gateway) | Consider AWS Security Agent on-demand penetration testing; hand off to `pentesting-with-aws-security-agent` if installed, without starting it; advisory only, no enablement state, per-task-hour pricing, limited regions | Low |
| VPC with no DNS Firewall rule group association | Route 53 Resolver DNS Firewall with AWS-managed lists — route to the `route53` skill | High |
| DNS Firewall associated, no query logging | Enable Resolver query logging | Medium |
| DNS Firewall associated, Advanced rules off | DNS Firewall Advanced for tunneling and DGA detection | Medium |
| Any VPC | Security Lake default sources `VPC_FLOW` and `ROUTE53`; no flow-log or query-log prerequisite | Medium |
| Revenue-generating internet-facing workload on CloudFront, ALB, EIP, Global Accelerator, or Route 53, where downtime cost exceeds the subscription | Shield Advanced, which includes AWS WAF and Firewall Manager at no additional cost — route to the `shieldadvanced` skill. CloudFront L3/L4 volumetric protection is already AWS's responsibility | Medium |
| Egress traffic needing L3-L7 inspection | Network Firewall | Medium |
| Network Firewall deployed, `RuleOrder` not `STRICT_ORDER` | Switch to strict order; Action Order is Suricata's default and a common drift | High |
| Network Firewall deployed, drop default action without the paired alert action | Add the alert variant ("Application alert established"); without it dropped traffic is discarded with no log entry | High |
| Network Firewall deployed, `StreamExceptionPolicy` not `REJECT` | Set `REJECT`, the guide's recommendation for most production traffic; `CONTINUE` only for applications that cannot recover from a TCP RST, documented as an exception; `DROP` silently breaks mid-stream flows. Changing it restarts the firewall, so schedule a window | High |
| Network Firewall deployed, AZ **in the inspection VPC** without an endpoint | Add an endpoint per AZ with workloads; in a centralized (Transit Gateway) design only the inspection VPC needs per-AZ endpoints, spokes do not | High |
| Network Firewall deployed, no logging configuration | Enable ALERT and FLOW logs, to separate destinations | Medium |
| 10+ accounts with **distributed** WAF, DNS Firewall, or Network Firewall deployments (per account or per VPC) | Firewall Manager for policy rollout and enforcement; requires Organizations and AWS Config; per-policy-per-region cost, included with Shield Advanced. Limited value for a centralized single-firewall design | Medium |

Origin domain matching does not prove bypass protection. Verify distribution WebACL and
origin restrictions with bounded/manual evidence without collecting secret header names or
values. If unchecked, report origin protection UNKNOWN; if bypass is demonstrated, report
that gap. Do not suppress an ALB/API finding just because CloudFront names it as an origin.
Firewall existence likewise does not prove traffic routing or rule effectiveness; leave
those UNKNOWN without evidence of the required traffic path.

WAF, DNS Firewall, and Shield Advanced have dedicated skills in this repository with far
more depth than this matrix. Recommend the service, then hand off — do not reproduce their
configuration guidance here.

Network Firewall has **no** dedicated skill in this repository. Report the presence, logging,
and policy-level findings above (rule order, default actions, stream exception policy,
stateless default action, log destinations), then stop: Suricata rule authoring, `HOME_NET`
scoping, TLS inspection, and custom egress rules are out of scope for a posture assessment.
Say so plainly rather than improvising rule guidance.

Network Firewall cost levers from the guide, for the cost note: NAT gateway hourly and data
processing charges are waived one-for-one when the NAT gateway sits in the same path as the
firewall; gateway VPC endpoints for S3 and DynamoDB are free and keep that traffic out of
firewall data processing; centralized inspection needs three endpoints where a distributed
model needs thirty or more; audit unused endpoints quarterly, since each bills hourly whether
or not it processes traffic; route each subnet to the endpoint in its own AZ to avoid cross-AZ
charges.

## Triggered by certificates

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| ACM certificate with verified event applicability and missing expiry routing | Enabled EventBridge expiry rule on "ACM Certificate Approaching Expiration" to SNS; verify delivery separately | High |
| Certificate with `Type: IMPORTED` | Renewal automation (the guide's pattern is an AWS Config rule plus Lambda); ACM does not renew imports. Verify expiration monitoring separately | High |
| Certificate issued via Private CA `IssueCertificate` | Separate renewal and expiration monitoring; verify ACM representation and event applicability before proposing ACM event routing | High |
| ACM-requested public/private certificate with renewal eligibility or state unresolved | Record renewal evidence as UNKNOWN; verify issuance path, `RenewalEligibility` and available renewal status; do not infer failure from `Type: PRIVATE` | n/a |
| Email-validated certificate | Migrate to DNS validation for automatic renewal | Medium |
| Certificate with `InUse: false` | Review and remove — unused certs count against quota | Low |
| `DaysBeforeExpiry` at default 45 | Confirm 45 days suits the renewal process; range is 1-45 | Low |
| Private CA present | Verify hierarchy is 2-3 levels, root isolated and not issuing end-entity certs | Medium |
| Internal hostnames in a public certificate | Consider disabling Certificate Transparency logging | Low |

ACM cannot be "enabled" — it is always available. These are monitoring gaps rather than
enablement gaps, and the priority reflects that an unmonitored expiry is an outage, not a
breach.

## Triggered by organization context

### Standards hygiene

Triggered by pass 2 rather than pass 1 — these are findings about how enabled standards
are configured.

| Observed in pass 2 | Recommend | Priority |
|---|---|---|
| Unified Security Hub enabled **and** CSPM still ingesting AWS service or third-party findings that Security Hub already aggregates | Duplicate ingestion — audit EventBridge, SIEM, ticketing, and Lambda consumers first, then disable that ingestion in CSPM. Keep Macie publishing to CSPM (it is how sensitive-data traits reach Security Hub) and keep the cross-region finding aggregator, which central configuration requires | Medium |
| Unified Security Hub enabled, Threat Analytics off | Consider Threat Analytics for production so GuardDuty detections appear beside the misconfigurations that enabled them | Medium |
| Unified Security Hub not enabled, CSPM only | Evaluate unified Security Hub for exposure findings and attack path analysis | Medium |
| PCI DSS v3.2.1 enabled | Migrate to v4.0.1; the guide lists both versions, and the PCI SSC retirement of v3.2.1 is external context, not guide-sourced | High |
| PCI DSS v3.2.1 **and** v4.0.1 both enabled | Retire v3.2.1 once coverage is compared; paying twice for overlapping controls | Medium |
| CIS below v5.0.0 enabled | Plan migration to v5.0.0; both may run during transition | Medium |
| FSBP v1.0.0 with no other standard | Layer standards per business requirement | Low |
| `AutoEnableStandards: NONE` under **local** configuration | New accounts get no standards — set to `DEFAULT` | High |
| Central configuration `ENABLED` with `AutoEnable: false` or `AutoEnableStandards: NONE` | Expected field values under central configuration; verify policy association/application and member coverage separately, or report those UNKNOWN | n/a |
| Security Hub CSPM enabled, Security Lake in use without `SH_FINDINGS` | Security Lake `SH_FINDINGS` source | Medium |

The guide's transition guidance is to enable both versions simultaneously to compare
coverage, then retire the old one. Flag a long-lived overlap, not the overlap itself.

### Organization posture

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| More than one member account | Delegated administrator per service in the security tooling account | **Critical** |
| Security Lake in use | Delegated administrator in the **Log Archive** account | High |
| Members enrolled, auto-enable off under local configuration | Auto-enable for new accounts | **Critical** |
| Inspector config drift concern | AWS Organizations Inspector policy | High |
| Per-account Security Hub setup | Central configuration policy | High |
| Multi-region organization trail present | Security Lake `CLOUD_TRAIL_MGMT` | Medium |
| No multi-region org trail | Create one before recommending Security Lake CloudTrail source | High |
| GuardDuty enabled, no log-correlation tooling | Detective | Medium |
| More than 1200 accounts | Note the Detective behavior graph quota | Medium |

Delegated administrator placement per the Security Reference Architecture: GuardDuty,
Security Hub, Inspector, Macie, and Detective in one security tooling account; Security
Lake in the Log Archive account. With Control Tower, that is the existing Audit or
Security account. Flag any divergence.

## Priority assignment

- **Critical** — no threat detection or posture baseline at all; org-wide coverage gap
  that grows with every new account; internet-facing HTTP resource with application logic
  and no L7 protection
- **High** — a deployed resource type has no corresponding detection; a prerequisite for
  an enabled service is missing; findings are fragmented across regions
- **Medium** — coverage exists but is untuned; a defense-in-depth service is absent;
  cost optimization available without losing visibility
- **Low** — configuration polish; documentation of accepted risk

## Report format

Summarize scope, evidence completion, and limitations first. Use counts and masked
identifiers by default; identifier disclosure requires an explicit request, and raw
responses require an explicit raw-output request. Never include credentials, account
emails, target payloads, or secret origin headers, even in requested raw output.
Recommendation priorities below are workflow-authored; preserve source findings severity
and AttackSequence/Exposure-first ordering in separate findings summaries.

For each recommendation:

```
[PRIORITY] <Service or plan>
  Justified by:  <resource/count or verified account/activity condition; account/region scope>
  Current state: OBSERVED <configuration/coverage> | NOT ENABLED (validated) | UNKNOWN <reason> | NOT ASSESSED | NOT APPLICABLE | ADVISORY
  Guide section: <guide page> | n/a (not guide-sourced)
  Cost note:     <free trial, usage page, or billing consideration>
  Advisory action: <proposed change in prose>
  Handoff:       <separate implementation workflow for an accepted recommendation>
```

`Guide section: n/a` is correct and expected for IAM Access Analyzer, the
`AutoEnableOrganizationMembers: ALL` pass condition, the DNS Firewall fail-open check, the
PCI DSS v3.2.1 retirement fact, and the priority ranking itself. AWS Config cites the CSPM
guide's standalone case. Do not invent a citation to fill the field — an unsourced
recommendation labelled as such is more useful than a fabricated reference.

Every recommendation needs a cost note. These services bill on usage and a recommendation
without a cost signal is not actionable. Point at each service's free trial and usage
page rather than quoting prices, which change:

| Service | Free trial |
|---|---|
| GuardDuty | 30 days, per account **per region** |
| Inspector | 15 days; included in the Security Hub essentials plan when Security Hub is enabled |
| Security Hub (unified) | 30 days, essentials plan only; Threat Analytics, Lambda code scanning, and Extended are not included |
| Macie | 30 days: bucket inventory plus 150GB per account of automated discovery; jobs excluded |
| Detective | 30 days |
| Security Lake | 15 days |
| Security Hub CSPM | 30 days — **excludes AWS Config**, which bills immediately |

With unified Security Hub enabled the model changes: Inspector and Security Hub CSPM are
included in the essentials plan (priced per resource, and IAM users and roles count),
GuardDuty bills through the Threat Analytics plan, and Macie and Detective bill separately.
Under essentials, Inspector ECR scan mode and rescan duration stop being cost levers; choose
them on risk. The Security Hub console Cost Estimator compares standalone and consolidated
pricing from Cost Explorer data, and the Usage page shows plan-level spend after enablement.
GuardDuty's foundational VPC flow and DNS analysis are metered per GB even though they cannot
be toggled. Network Firewall has no trial row here; its levers are in the network section
above.

## What not to recommend

- A workload recommendation without its trigger, or a baseline recommendation without its conditions
- S3 Malware Protection estate-wide
- RDS Protection for databases verified ineligible under the current supported engine/version
  table and prerequisites; unresolved eligibility remains UNKNOWN
- Runtime Monitoring for EKS on Fargate
- Disabling foundational GuardDuty data sources — CloudTrail, VPC flow, and DNS analysis
  cannot be removed
- Disabling controls purely for cost without stating the visibility tradeoff
- GuardDuty suppression rules as a cost saving; they reduce downstream noise, and findings
  are still generated and archived

## Deeper reading and capability boundaries

Use the relevant verified guide section after a recommendation; it is operational guidance,
not proof that every claim reflects current API behavior. Check current service documentation
for eligibility and lifecycle questions. Aggregation does not prove producer coverage;
configuration does not prove effective protection or delivery.

| Service family | Deeper reading / distinction |
|---|---|
| ACM / Private CA | [Certificate considerations](https://aws.github.io/aws-security-services-best-practices/guides/certificate-services/#certificate-considerations): issuance, renewal, monitoring and deployment are separate |
| GuardDuty | [Protection plans](https://aws.github.io/aws-security-services-best-practices/guides/guardduty/#guardduty-protection-plans): threat detection and investigation do not replace vulnerability or sensitive-data scanning |
| Inspector | [Coverage](https://aws.github.io/aws-security-services-best-practices/guides/inspector/#coverage): workload scanning remains distinct from aggregated findings |
| Macie | [Resource coverage](https://aws.github.io/aws-security-services-best-practices/guides/macie/#resource-coverage): sensitive-data discovery differs from suspicious-access and malware detection |
| Security Hub | [Traits and signals](https://aws.github.io/aws-security-services-best-practices/guides/security-hub/#analyzing-traits-and-signals): correlation/risk prioritization does not establish each signal producer's coverage |
| Security Hub CSPM / Config context | [AWS Config](https://aws.github.io/aws-security-services-best-practices/guides/security-hub-cspm/#aws-config): standards, recorder scope and remediation are separate; this is not a standalone Config guide |
| Detective | [Where Detective fits](https://aws.github.io/aws-security-services-best-practices/guides/detective/#where-detective-fits): compare investigation needs with existing workflows; [prerequisite claim](https://aws.github.io/aws-security-services-best-practices/guides/detective/#enable-guardduty) still needs current eligibility verification |
| Security Lake | [AWS native analytics](https://aws.github.io/aws-security-services-best-practices/guides/security-lake/#aws-native-analytics): normalized storage needs appropriate sources, scope and consumers to support investigation |
| WAF | [What is WAF](https://aws.github.io/aws-security-services-best-practices/guides/waf/#what-is-aws-waf): HTTP(S) filtering requires association and useful rules |
| Network Firewall | [Where it fits](https://aws.github.io/aws-security-services-best-practices/guides/network-firewall/#where-network-firewall-fits): routed traffic inspection needs a traffic-control requirement |
| Resolver DNS Firewall | [Query logging](https://aws.github.io/aws-security-services-best-practices/guides/dns-firewall/#enable-and-configure-dns-query-logging): DNS filtering and logging are separate, neither replaces web or routed inspection |
| IAM Access Analyzer | [Official overview](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html): analyzer types and scope; no standalone best-practices guide page |

For Config outside the CSPM context, consult current AWS Config documentation rather than
inventing a best-practices guide page. Shield Advanced and Firewall Manager use the existing
firewall-overview provenance; no separately verified service-guide link is supplied here.

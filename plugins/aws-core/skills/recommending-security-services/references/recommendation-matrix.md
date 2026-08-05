# Pass 3 — Inventory to Service Recommendation Matrix

Each row fires only when its trigger resource is found in pass 1. No trigger, no
recommendation.

## Baseline: always applicable

These have no resource trigger — they apply to any account with activity.

| Recommendation | Severity | Rationale |
|---|---|---|
| GuardDuty foundational (CloudTrail, VPC flow, DNS analysis) | **Critical** | Threat detection with no data-source configuration; pulls streams directly |
| AWS Config recorder | **Critical** | Prerequisite for most Security Hub CSPM controls |
| Security Hub CSPM with FSBP | **Critical** | Baseline posture standard; the guide's starting point |
| IAM Access Analyzer external-access analyzer | **High** | Surfaces unintended external access to resources |
| Cross-region finding aggregation | **High** | Regional services produce fragmented findings otherwise |

## Triggered by compute

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| Any EC2 instance | GuardDuty `EBS_MALWARE_PROTECTION` | High |
| Any EC2 instance | Inspector `EC2` scanning | High |
| EC2 instance, SSM-managed | GuardDuty `RUNTIME_MONITORING` with `EC2_AGENT_MANAGEMENT` | High |
| EC2 instance, **not** SSM-managed | Default Host Management Configuration via SSM Quick Setup first | High |
| Linux EC2 instance | Inspector Deep Inspection | Medium |
| Any Lambda function | Inspector `LAMBDA` **and** `LAMBDA_CODE` | High |
| Any Lambda function | GuardDuty `LAMBDA_NETWORK_LOGS` | Medium |

Inspector EC2 scanning is hybrid: agent-based is event-driven (a package install triggers
re-evaluation), agentless runs once per 24 hours. Agentless covers hosts that cannot run
the agent. Non-SSM-managed instances get agentless coverage only — recommend SSM
enrollment to gain event-driven scanning.

Deep Inspection default paths: `/usr/lib`, `/usr/lib64`, `/usr/local/lib`,
`/usr/local/lib64`. Each account may add 5 custom paths, plus 5 org-wide from the
delegated admin, for up to 10.

Windows instances are scanned at discovery then every 6 hours; adjust with
`aws ssm update-association`.

## Triggered by containers

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| Any ECR repository | Inspector `ECR` scanning, continuous | High |
| ECR repository with images | ECR rescan duration tuned to build cadence | Medium |
| Any EKS cluster | GuardDuty `EKS_AUDIT_LOGS` | High |
| EKS cluster on EC2 nodegroups | GuardDuty `RUNTIME_MONITORING` with `EKS_ADDON_MANAGEMENT` | High |
| EKS cluster, Fargate profiles only | **Do not** recommend Runtime Monitoring — unsupported | n/a |
| ECS cluster on Fargate | GuardDuty `RUNTIME_MONITORING` with `ECS_FARGATE_AGENT_MANAGEMENT` | High |
| ECS cluster on EC2 | GuardDuty `RUNTIME_MONITORING` with `EC2_AGENT_MANAGEMENT` | High |
| EKS or ECS cluster | Detective for cross-account container visibility | Medium |

On ECR activation with continuous scanning, Inspector picks up images pushed within 30
days or pulled within the last 90. Account for ECR lifecycle policies deleting images
before the rescan window closes.

Inspector maps ECR images to running ECS and EKS containers — use this to prioritize. A
vulnerable image sitting unused in a registry is a different risk from one running in
production.

ECS specifics: Fargate platform 1.4.0 or LATEST, plus a task execution role. Tasks already
running when monitoring is enabled need a fresh deployment — restart the service or update
with `forceNewDeployment`. The ECS agent can only be managed by GuardDuty, never manually.

EKS specifics: only the delegated administrator can enable or disable Automated agent
configuration for members.

## Triggered by data

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| Any S3 bucket | GuardDuty `S3_DATA_EVENTS` | High |
| Any S3 bucket | Macie automated sensitive data discovery | High |
| Macie enabled | Classification export to S3 within 30 days | High |
| S3 bucket taking untrusted or third-party uploads | GuardDuty S3 Malware Protection, **per bucket** | High |
| Many or large S3 buckets | Automated discovery over discovery jobs | Medium |
| Dataset requiring full coverage, not sampling | Targeted discovery job in addition | Medium |
| Aurora cluster | GuardDuty `RDS_LOGIN_EVENTS` | High |
| Non-Aurora RDS only | **Do not** recommend RDS Protection — Aurora login activity only | n/a |
| EBS snapshots, AMIs, or S3 recovery points in Backup | Malware Protection for AWS Backup | Medium |

S3 Malware Protection is enabled **per bucket**, not per account or organization. The
guide states it is "not intended to be deployed across your entire S3 estate." Ask which
buckets receive untrusted input; recommend only those. It can run standalone without the
rest of GuardDuty.

Macie retains discovery results for only 90 days, and the results repository must be
configured within the first 30 days. The repository logs an entry per file examined even
when nothing sensitive was found, which is how you confirm coverage and find unscannable
files.

Macie tuning order: enable all managed data identifiers (no per-identifier charge), then
suppress false positives with allow lists, then add custom data identifiers for
organization-specific data such as employee IDs or internal classifications.

## Triggered by network and edge

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| CloudFront distribution or ALB with no WebACL | AWS WAF — route to the `waf` skill | **Critical** |
| Internet-facing ALB | AWS WAF — route to the `waf` skill | **Critical** |
| API Gateway REST API with no WebACL | AWS WAF — route to the `waf` skill | High |
| VPC with no DNS Firewall rule group association | Route 53 Resolver DNS Firewall with AWS-managed lists — route to the `route53` skill | High |
| DNS Firewall associated, no query logging | Enable Resolver query logging | Medium |
| DNS Firewall associated, Advanced rules off | DNS Firewall Advanced for tunneling and DGA detection | Medium |
| VPC with flow logs | Security Lake `VPC_FLOW` source | Medium |
| Public-facing workload | Shield Advanced — route to the `shieldadvanced` skill | Medium |
| Egress traffic needing L3-L7 inspection | Network Firewall | Medium |
| Network Firewall deployed, `RuleOrder` not `STRICT_ORDER` | Switch to strict order — IaC defaults to Action Order | High |
| Network Firewall deployed, `StreamExceptionPolicy: DROP` | Change to `REJECT` or `CONTINUE` — DROP silently blocks mid-stream flows | High |
| Network Firewall deployed, AZ without an endpoint | Add an endpoint per AZ containing workloads | High |
| Network Firewall deployed, no logging configuration | Enable ALERT and FLOW logs | Medium |
| More than one account with VPCs or web-facing resources | Firewall Manager for org-wide rollout | Medium |

WAF, DNS Firewall, and Shield Advanced have dedicated skills in this repository with far
more depth than this matrix. Recommend the service, then hand off — do not reproduce their
configuration guidance here.

Network Firewall has **no** dedicated skill in this repository. Report the presence and
configuration findings above, then stop: Suricata rule authoring, `HOME_NET` scoping, TLS
inspection, and custom egress rules are out of scope for a posture assessment. Say so
plainly rather than improvising rule guidance.

## Triggered by certificates

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| Any ACM certificate | EventBridge expiry rule on "ACM Certificate Approaching Expiration" to SNS | High |
| Certificate with `Type: IMPORTED` | Custom renewal automation — ACM does not manage renewal or expiry notices for imported certs | High |
| Certificate issued via Private CA `IssueCertificate` | Custom expiry notification — ACM does not track these either | High |
| Email-validated certificate | Migrate to DNS validation for automatic renewal | Medium |
| Certificate with `InUse: false` | Review and remove — unused certs count against quota | Low |
| `DaysBeforeExpiry` at default 45 | Confirm 45 days suits the renewal process; range is 1-45 | Low |
| Private CA present | Verify hierarchy is 2-3 levels, root isolated and not issuing end-entity certs | Medium |
| Internal hostnames in a public certificate | Consider disabling Certificate Transparency logging | Low |

ACM cannot be "enabled" — it is always available. These are monitoring gaps rather than
enablement gaps, and the severity reflects that an unmonitored expiry is an outage, not a
breach.

## Triggered by organization context

### Standards hygiene

Triggered by pass 2 rather than pass 1 — these are findings about how enabled standards
are configured.

| Observed in pass 2 | Recommend | Severity |
|---|---|---|
| Unified Security Hub enabled **and** a CSPM finding aggregator exists | Redundant aggregation — audit EventBridge, SIEM, ticketing, and Lambda dependencies first, then remove the CSPM aggregator | Medium |
| Unified Security Hub enabled, Threat Analytics off | Consider Threat Analytics for production so GuardDuty detections appear beside the misconfigurations that enabled them | Medium |
| Unified Security Hub not enabled, CSPM only | Evaluate unified Security Hub for exposure findings and attack path analysis | Medium |
| PCI DSS v3.2.1 enabled | Migrate to v4.0.1 — v3.2.1 is retired by the PCI SSC | High |
| PCI DSS v3.2.1 **and** v4.0.1 both enabled | Retire v3.2.1 once coverage is compared; paying twice for overlapping controls | Medium |
| CIS below v5.0.0 enabled | Plan migration to v5.0.0; both may run during transition | Medium |
| FSBP v1.0.0 with no other standard | Layer standards per business requirement | Low |
| `AutoEnableStandards: NONE` in an org | New accounts get no standards — set to `DEFAULT` | High |
| Central configuration `ENABLED` but `AutoEnable: false` | Expected under central configuration; policy governs enrollment, so do not flag as a gap | n/a |

The guide's transition guidance is to enable both versions simultaneously to compare
coverage, then retire the old one. Flag a long-lived overlap, not the overlap itself.

### Organization posture

| Trigger from pass 1 | Recommend | Severity |
|---|---|---|
| More than one member account | Delegated administrator per service in the security tooling account | **Critical** |
| Security Lake in use | Delegated administrator in the **Log Archive** account | High |
| Members enrolled, auto-enable off | Auto-enable for new accounts | **Critical** |
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

## Severity assignment

- **Critical** — no threat detection or posture baseline at all; org-wide coverage gap
  that grows with every new account; internet-facing resource with no L7 protection
- **High** — a deployed resource type has no corresponding detection; a prerequisite for
  an enabled service is missing; findings are fragmented across regions
- **Medium** — coverage exists but is untuned; a defense-in-depth service is absent;
  cost optimization available without losing visibility
- **Low** — configuration polish; documentation of accepted risk

## Report format

For each recommendation:

```
[SEVERITY] <Service or plan>
  Justified by:  <resource type and count from pass 1>
  Current state: NOT ENABLED | ENABLED BUT UNTUNED | UNKNOWN (permission denied)
  Guide section: <guide page> | n/a (not guide-sourced)
  Cost note:     <free trial, usage page, or billing consideration>
  Enablement:    <command, presented but NOT run>
```

`Guide section: n/a` is correct and expected for IAM Access Analyzer, AWS Config, and the
severity ranking itself. Do not invent a citation to fill the field — an unsourced
recommendation labelled as such is more useful than a fabricated reference.

Every recommendation needs a cost note. These services bill on usage and a recommendation
without a cost signal is not actionable. Point at each service's free trial and usage
page rather than quoting prices, which change:

| Service | Free trial |
|---|---|
| GuardDuty | 30 days, per account **per region** |
| Inspector | 15 days |
| Macie | 30 days: bucket inventory plus 150GB per account of automated discovery; jobs excluded |
| Detective | 30 days |
| Security Lake | 15 days |
| Security Hub CSPM | 30 days — **excludes AWS Config**, which bills immediately |

## What not to recommend

- Any service whose trigger resource was not found
- S3 Malware Protection estate-wide
- RDS Protection where no Aurora clusters exist
- Runtime Monitoring for EKS on Fargate
- Disabling foundational GuardDuty data sources — CloudTrail, VPC flow, and DNS analysis
  cannot be removed
- Disabling controls purely for cost without stating the visibility tradeoff

# Pass 2 — Security Service Enablement Checks

All commands are read-only. Every service below except IAM Access Analyzer is regional —
run per region being assessed.

`AccessDenied` means unknown, not disabled. Report it as unknown.

## Amazon GuardDuty

```bash
# Detector presence. Empty list = not enabled in this region.
aws guardduty list-detectors --region <region>

# Per-feature status. Checking the detector alone is not sufficient — protection plans
# are individually toggled.
aws guardduty get-detector --detector-id <id> --region <region>
```

`get-detector` returns `Features[]` with a `Name` and `Status` per plan.

`Features[]` also includes the foundational sources `CLOUD_TRAIL`, `DNS_LOGS`, and
`FLOW_LOGS`. These are always `ENABLED` on an active detector and are not separately
billable protection plans — do not report them as gaps or recommend toggling them.

Optional protection plans, which are the ones worth checking:

| Feature | Covers | Applies when inventory shows |
|---|---|---|
| `S3_DATA_EVENTS` | CloudTrail S3 data events | Any S3 bucket |
| `EKS_AUDIT_LOGS` | EKS audit logs | Any EKS cluster |
| `EBS_MALWARE_PROTECTION` | EBS volume malware scanning | EC2 instances with EBS volumes |
| `RDS_LOGIN_EVENTS` | Aurora login activity | Aurora clusters |
| `LAMBDA_NETWORK_LOGS` | Lambda network activity | Any Lambda function |
| `RUNTIME_MONITORING` | EC2, ECS, EKS runtime | EC2, ECS, or EKS on EC2 |
| `EKS_RUNTIME_MONITORING` | EKS runtime (superseded by `RUNTIME_MONITORING`) | EKS on EC2 |
| `AI_PROTECTION` | Bedrock model invocation activity | Bedrock usage |
| `AI_ANALYST` | Generative-AI finding investigation | Any account |

Runtime Monitoring has an `AdditionalConfiguration` array for agent management:
`EC2_AGENT_MANAGEMENT`, `ECS_FARGATE_AGENT_MANAGEMENT`, `EKS_ADDON_MANAGEMENT`. The guide
recommends letting GuardDuty manage agents so new resources are covered automatically.

```bash
# Runtime Monitoring agent coverage — enabled but uncovered is a silent gap.
# Returns null Resources when RUNTIME_MONITORING is DISABLED; that is expected,
# not an error. Check the feature status first and skip this call if disabled.
aws guardduty list-coverage --detector-id <id> --region <region>

# Organization posture. Both calls raise BadRequestException / InvalidInputException
# from a non-admin account — see Troubleshooting in SKILL.md.
aws guardduty list-organization-admin-accounts --region <region>
aws guardduty describe-organization-configuration --detector-id <id> --region <region>
aws guardduty list-members --detector-id <id> --region <region>
```

`describe-organization-configuration` returns `AutoEnableOrganizationMembers` with values
`NEW`, `ALL`, or `NONE`. `ALL` is the guide's recommendation; `NEW` leaves existing
accounts uncovered; `NONE` means manual management.

**Pass conditions:** detector exists; every feature whose triggering resource is present
is `ENABLED`; `AutoEnableOrganizationMembers` is `ALL` in an org; finding publishing
frequency tightened from the 6-hour default (15 minutes if Detective is in use).

## AWS Security Hub CSPM

```bash
# Not enabled raises ResourceNotFoundException
aws securityhub describe-hub --region <region>

# Which standards are on. FSBP is the baseline; layer others per requirement.
aws securityhub get-enabled-standards --region <region>

# Cross-region aggregation
aws securityhub list-finding-aggregators --region <region>
aws securityhub get-finding-aggregator --finding-aggregator-arn <arn> --region <region>

# Central configuration — preferred over per-account setup
aws securityhub list-configuration-policies --region <region>

# Organization posture
aws securityhub list-organization-admin-accounts --region <region>
aws securityhub describe-organization-configuration --region <region>
```

Standard versions per the guide: CIS AWS Foundations Benchmark supports v1.2.0, v1.4.0,
v3.0.0, v5.0.0 — new adopters should start at **v5.0.0**. PCI DSS supports v3.2.1 and
v4.0.1, and **v3.2.1 is retired by the PCI SSC**, so in-scope orgs need v4.0.1. NIST SP
800-53 Rev. 5 and NIST SP 800-171 Rev. 2 are available, the latter for CUI handling.

**Pass conditions:** hub enabled; FSBP enabled at minimum; a finding aggregator exists if
more than one region is in use; central configuration policy in place for orgs; AWS
Config enabled (see below) — without it most controls cannot evaluate.

**Cost note:** AWS Config is **not** included in the Security Hub 30-day trial, so
standards-driven Config rule usage bills from day one.

## AWS Security Hub (unified)

Distinct from CSPM. The older product was rebranded Security Hub CSPM; today's Security
Hub is a unified platform that correlates GuardDuty, Inspector, Macie, and CSPM signals
into exposure findings and attack paths. Both can be enabled at once, and both live in the
`securityhub` API namespace — the unified service uses the `*V2` operations.

```bash
# Unified Security Hub. ResourceNotFoundException / ResourceConflictException = not enabled.
aws securityhub describe-security-hub-v2 --region <region>

# Unified aggregation
aws securityhub list-aggregators-v2 --region <region>
```

**Cross-cutting finding:** if unified Security Hub is enabled **and** a CSPM finding
aggregator exists, the CSPM-level aggregation is redundant — the guide recommends
eliminating it, since findings flow into Security Hub automatically. Before recommending
removal, the guide is explicit that you must audit EventBridge rules, SIEM feeds,
ticketing workflows, and custom Lambda functions first, because dropping it "can silently
break alerting and response workflows."

**Plans:** Essentials (resource-based pricing) covers Inspector scanning, CSPM checks,
GuardDuty EC2 Malware Scanning, and risk/exposure analytics. Threat Analytics (usage-based,
optional) embeds GuardDuty detections in the console so a suspicious IAM action appears
next to the misconfiguration that enabled it. The 30-day trial covers Essentials only —
not Threat Analytics, Lambda code scanning, or Security Hub Extended.

**Policies vs deployments:** Organizations policies exist for Security Hub and Inspector
and auto-apply to new accounts, preventing drift. GuardDuty and CSPM use one-time
deployments that cannot be viewed or edited and do **not** cover newly enabled accounts —
so auto-enable for new members remains necessary for those two.

**Pass conditions:** enabled in the delegated admin's home region; no redundant CSPM
aggregator; Threat Analytics considered for production accounts.

## AWS Certificate Manager

ACM is always available rather than something you enable, so the checks here are
monitoring and configuration hygiene.

```bash
# Certificate inventory with expiry and in-use status
aws acm list-certificates \
  --query 'CertificateSummaryList[].{Domain:DomainName,Status:Status,NotAfter:NotAfter,InUse:InUse,Type:Type}' \
  --region <region>

# Expiry notification window. ACM emits daily EventBridge events starting
# DaysBeforeExpiry out; valid range is 1-45, default 45.
aws acm get-account-configuration --region <region>

# Per-certificate detail — renewal eligibility and Certificate Transparency preference
aws acm describe-certificate --certificate-arn <arn> --region <region>

# Private CA
aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[].{Arn:Arn,Type:Type,Status:Status}' --region <region>
```

**Pass conditions:** an EventBridge rule on source `aws.acm`, detail-type "ACM Certificate
Approaching Expiration", targeting SNS; DNS validation rather than email for renewable
certs; imported and Private-CA-issued certificates have their own notification automation,
since ACM does **not** manage renewal or expiry notices for those.

**Notes:** ACM validity is fixed at 13 months and cannot be changed. CloudFront
certificates must be issued in `us-east-1` regardless of the distribution's origin region.
Certificate Transparency logging cannot be toggled from the console, cannot change once
the renewal period starts (~60 days before expiry), and failures there are silent.

## AWS Network Firewall

Presence and logging only. Rule authoring — Suricata syntax, `HOME_NET` scoping, strict
rule order, stream exception policy, TLS inspection — is deep enough to warrant its own
skill and is out of scope here.

```bash
aws network-firewall list-firewalls --region <region>
aws network-firewall describe-firewall --firewall-name <name> --region <region>
aws network-firewall describe-logging-configuration --firewall-name <name> --region <region>
```

**Pass conditions:** if deployed, a firewall endpoint exists in every AZ containing
workloads; both ALERT and FLOW log types configured; `RuleOrder` is `STRICT_ORDER` (the
IaC default is Action Order, so this is a common drift); `StreamExceptionPolicy` is
`REJECT` or `CONTINUE` rather than `DROP`, which silently blocks mid-stream flows without
sending a TCP reset.

## Route 53 Resolver DNS Firewall

```bash
# Rule group to VPC associations — an unassociated rule group protects nothing
aws route53resolver list-firewall-rule-group-associations \
  --query 'FirewallRuleGroupAssociations[].{Vpc:VpcId,Status:Status,Priority:Priority}' \
  --region <region>

aws route53resolver list-firewall-rule-groups --region <region>

# Per-VPC fail-open setting
aws route53resolver get-firewall-config --resource-id <vpc-id> --region <region>

# Query logging — required for DNS threat hunting
aws route53resolver list-resolver-query-log-configs --region <region>
```

**Pass conditions:** at least one rule group associated with each VPC; AWS-managed domain
lists attached as the first layer; DNS Firewall Advanced enabled for DNS tunneling and
domain-generation-algorithm detection; query logging on with a deliberate retention policy.

DNS Firewall is the earliest filter in the chain — blocking at the DNS layer stops traffic
before it reaches Network Firewall, which reduces downstream processing cost.

## AWS Firewall Manager

Relevant when DNS Firewall or WAF rules need org-wide rollout so new VPCs are covered
automatically.

```bash
# ResourceNotFoundException = no FMS administrator designated
aws fms get-admin-account --region us-east-1
aws fms list-policies --region us-east-1
```

**Pass conditions:** an FMS administrator account exists if the org has more than one
account with VPCs or web-facing resources.

## Amazon Inspector

```bash
# Per-scan-type activation status
aws inspector2 batch-get-account-status --region <region>

# Coverage — which resources are actually being scanned
aws inspector2 list-coverage --region <region>

# Organization posture
aws inspector2 list-delegated-admin-accounts --region <region>
aws inspector2 describe-organization-configuration --region <region>
aws inspector2 list-members --region <region>
```

`batch-get-account-status` returns `resourceState` per scan type. Valid types: `EC2`,
`ECR`, `LAMBDA`, `LAMBDA_CODE`, `CODE_REPOSITORY`.

`LAMBDA` and `LAMBDA_CODE` are separate toggles and the guide says both should be on —
`LAMBDA` covers package vulnerabilities, `LAMBDA_CODE` covers custom application code.

```bash
# ECR rescan duration and EC2 scan mode.
# Returns ecrConfiguration.rescanDurationState and ec2Configuration.scanModeState.
aws inspector2 get-configuration --region <region>

# Deep Inspection is a separate API, not part of get-configuration.
# Returns status, packagePaths (up to 5 per account), orgPackagePaths (up to 5 more).
aws inspector2 get-ec2-deep-inspection-configuration --region <region>
```

Valid `EcrRescanDuration` values: `LIFETIME`, `DAYS_3`, `DAYS_7`, `DAYS_14`, `DAYS_30`,
`DAYS_60`, `DAYS_90`, `DAYS_180`.

**Pass conditions:** every scan type with corresponding resources is `ENABLED`;
`autoEnable` covers new member accounts; Deep Inspection on for Linux EC2; ECR rescan
durations match build cadence.

## Amazon Macie

```bash
# Not enabled returns AccessDeniedException — no distinct "not enabled" error
aws macie2 get-macie-session --region <region>

# Automated discovery is the guide's default recommendation over discovery jobs
aws macie2 get-automated-discovery-configuration --region <region>

# Discovery results repository — results retained only 90 days, configure within 30
aws macie2 get-classification-export-configuration --region <region>

# Organization posture
aws macie2 list-organization-admin-accounts --region <region>
aws macie2 describe-organization-configuration --region <region>
```

**Pass conditions:** session `ENABLED`; automated sensitive data discovery `ENABLED`;
classification export configured to an S3 bucket; `autoEnable` on for new org accounts.

**Cost note:** the guide recommends automated discovery over discovery jobs — it samples
representatively, and the trial covers bucket inventory plus 150GB per account of
automated discovery. Discovery jobs are excluded from the trial.

## Amazon Detective

```bash
# Empty list = not enabled
aws detective list-graphs --region <region>

aws detective list-organization-admin-accounts --region <region>
aws detective describe-organization-configuration --graph-arn <arn> --region <region>
aws detective list-members --graph-arn <arn> --region <region>
```

**Ordering dependency:** GuardDuty must be enabled before Detective. Check GuardDuty
first and state the dependency in any Detective recommendation.

**Pass conditions:** graph exists; auto-enable on; GuardDuty finding publishing frequency
set to 15 minutes (the 6-hour default delays recurring-finding updates in Detective by up
to 6 hours, and tightening it costs nothing); source packages for AWS security findings
and EKS audit logs enabled — older deployments must turn these on manually.

**Quota:** a behavior graph supports a maximum of 1200 accounts.

## Amazon Security Lake

```bash
aws securitylake list-data-lakes --regions <region>
# get-data-lake-sources filters by account, not region
aws securitylake get-data-lake-sources --accounts <account-id>
aws securitylake list-log-sources --regions <region>
aws securitylake get-data-lake-organization-configuration
aws securitylake get-data-lake-exception-subscription
```

Valid `AwsLogSourceName` values: `CLOUD_TRAIL_MGMT`, `VPC_FLOW`, `ROUTE53`,
`SH_FINDINGS`, `EKS_AUDIT`, `S3_DATA`, `LAMBDA_EXECUTION`, `WAF`.

The guide recommends enabling all **default** sources: `CLOUD_TRAIL_MGMT`, `EKS_AUDIT`,
`ROUTE53`, `SH_FINDINGS`, `VPC_FLOW`. Treat `S3_DATA`, `LAMBDA_EXECUTION`, and `WAF` as
opt-in — they are excluded by default for high volume and cost.

**Prerequisite:** `CLOUD_TRAIL_MGMT` collection requires an existing multi-region
organization trail capturing read and write management events.

**Delegated admin placement:** the Log Archive account, not the security tooling account
used by the other five services.

**Pass conditions:** data lake exists; all five default sources on; new-account
collection enabled; lifecycle expiration set on contributing-region data (the guide cites
3 days as a cost/risk balance, 7 if more investigation time is wanted).

## IAM Access Analyzer

```bash
# The only non-regional service here, but analyzers are still created per region
aws accessanalyzer list-analyzers --region <region>
aws accessanalyzer list-findings --analyzer-arn <arn> --region <region>
```

Analyzer `type` values: `ACCOUNT`, `ORGANIZATION`, `ACCOUNT_UNUSED_ACCESS`,
`ORGANIZATION_UNUSED_ACCESS`, `ACCOUNT_INTERNAL_ACCESS`, `ORGANIZATION_INTERNAL_ACCESS`.

These are distinct analyzers, not one analyzer with modes. An account can have an
unused-access analyzer and still have no external-access analyzer — check the `type`
field rather than treating any active analyzer as coverage. Security Hub may create an
unused-access analyzer automatically (named `_AccessAnalyzerForSecurityHub*`), which is
why "an analyzer exists" is not sufficient evidence of external-access coverage.

**Pass conditions:** at least one analyzer of type `ACCOUNT` or `ORGANIZATION` for
external access; an `*_UNUSED_ACCESS` analyzer if the org reviews unused permissions.

## AWS Config

Check this before recommending Security Hub CSPM standards.

```bash
aws configservice describe-configuration-recorders --region <region>
aws configservice describe-configuration-recorder-status --region <region>
aws configservice describe-delivery-channels --region <region>
aws configservice describe-configuration-aggregators --region <region>
```

**Pass conditions:** recorder exists and `lastStatus` is `SUCCESS`; delivery channel
configured; recording group covers the resource types the enabled standards evaluate;
global resources recorded in one region only (the guide's duplication-avoidance practice).

## Summary table to produce

| Service | Enabled | Plans / standards on | Plans / standards off | Delegated admin | Auto-enable |
|---|---|---|---|---|---|
| GuardDuty | | | | | |
| Security Hub (unified) | | | | | |
| Security Hub CSPM | | | | | |
| Inspector | | | | | |
| Macie | | | | | |
| Detective | | | | | |
| Security Lake | | | | | |
| IAM Access Analyzer | | | | n/a | n/a |
| AWS Config | | | | | |
| ACM | always on | | | n/a | n/a |
| Network Firewall | | | | n/a | n/a |
| DNS Firewall | | | | n/a | n/a |
| Firewall Manager | | | | | n/a |

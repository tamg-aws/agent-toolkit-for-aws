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

Verify the VM Scanner versus legacy SSM path; manual VM Scanner installation does not
require SSM, while CIS scans still require the SSM plugin. Deep Inspection enabled is
not proof that custom software paths are covered: compare actual install locations with
account/org paths and current OS support. See enablement checks for scan configuration.

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

Compare ECR push/pull and rescan windows, lifecycle deletion and running-image mappings
with build cadence; unused registry images and production containers differ in risk.
ECS Fargate needs platform 1.4.0 or LATEST and a task execution role; existing tasks need
a fresh deployment for agent rollout. Fargate agents are GuardDuty-managed; ECS on EC2
uses the EC2 path. Only the delegated admin manages EKS automated agent configuration for
members. Extended Threat Detection needs no separate enablement; its correlation depends
on available protection-plan signals.

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

Inspect Macie export delivery and unscannable-file evidence, not just positive findings;
classification identifiers must match actual data classes. See enablement checks for reads.

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
| Confirmed public or private application needing AppSec assessment | Evaluate AWS Security Agent using the focused suitability guidance below for scope, private connectivity, auth and data handling; conditional specialist or AppSec-owner handoff, no test launch; verify current pricing and regions | Low |
| VPC with no DNS Firewall rule group association | Route 53 Resolver DNS Firewall with AWS-managed lists — route to the `route53` skill | High |
| DNS Firewall associated, no query logging | Enable Resolver query logging | Medium |
| DNS Firewall associated, Advanced rules off | DNS Firewall Advanced for tunneling and DGA detection | Medium |
| Any VPC | Security Lake default sources `VPC_FLOW` and `ROUTE53`; no flow-log or query-log prerequisite | Medium |
| Revenue-generating internet-facing workload on CloudFront, ALB, EIP, Global Accelerator, or Route 53, where downtime cost exceeds the subscription | Shield Advanced, verifying current WAF/Firewall Manager bundled eligibility — route to the `shieldadvanced` skill. CloudFront L3/L4 volumetric protection is already AWS's responsibility | Medium |
| Egress traffic needing L3-L7 inspection | Network Firewall | Medium |
| Network Firewall deployed, observed rule order conflicts with the verified intended policy strategy | Review strict-order suitability and rule dependencies with the firewall owner; establish the intended strategy before recommending a change | High (verified gap only) |
| Network Firewall deployed, default actions do not meet demonstrated enforcement or logging requirements under the selected compatible strategy | Review application-aware versus custom defaults and observed verdict/log evidence; do not universally pair drop and alert defaults or infer enforcement from configuration | High (verified gap only) |
| Network Firewall deployed, stream-exception behavior conflicts with application recovery requirements | Review the selected policy against application recovery, active connections and idle-flow evidence; assess planned change impact with the owner rather than assuming a universal restart | High (verified gap only) |
| Network Firewall deployed, endpoint coverage does not meet the verified deployment mode and traffic-path requirements | Review topology-specific endpoint/AZ coverage for inspection-VPC, native TGW or multi-endpoint mode; recommend changes only for a demonstrated path requirement | High (verified gap only) |
| Network Firewall deployed, no logging configuration | Enable ALERT and FLOW logs, to separate destinations | Medium |
| 10+ accounts with **distributed** WAF, DNS Firewall, or Network Firewall deployments (per account or per VPC) | Firewall Manager for policy rollout and enforcement; requires Organizations and AWS Config; verify current pricing and Shield Advanced bundled eligibility. Limited value for a centralized single-firewall design | Medium |

For the conditional Network Firewall rows, unresolved topology, intent or compatibility
is an UNKNOWN evidence disposition, not a recommendation priority. Assign High only
to a verified gap; unassessed or advisory-only decisions have no gap priority.

Origin domain matching does not prove bypass protection. Verify distribution WebACL and
origin restrictions with bounded/manual evidence without collecting secret header names or
values. If unchecked, report origin protection UNKNOWN; if bypass is demonstrated, report
that gap. Do not suppress an ALB/API finding just because CloudFront names it as an origin.
Firewall existence likewise does not prove traffic routing or rule effectiveness; leave
those UNKNOWN without evidence of the required traffic path.

## Triggered by certificates

| Trigger from pass 1 | Recommend | Priority |
|---|---|---|
| Certificate estate with demonstrated unmet monitoring coverage, delivery or lead-time needs after evaluating the chosen monitoring method | Close the verified monitoring gap; EventBridge expiry routing to SNS is an option only when event applicability and unmet needs justify it. Adequate CloudWatch alarms or issuer-side checks require no duplicate route; unknown monitoring stays UNKNOWN | High (verified gap only) |
| Certificate with `Type: IMPORTED` | Renewal automation (the guide's pattern is an AWS Config rule plus Lambda); ACM does not renew imports. Verify expiration monitoring separately | High |
| Certificate issued via Private CA `IssueCertificate` | Separate renewal and expiration monitoring; verify ACM representation and event applicability before proposing ACM event routing | High |
| ACM-requested public/private certificate with renewal eligibility or state unresolved | Record renewal evidence as UNKNOWN; verify issuance path, `RenewalEligibility` and available renewal status; do not infer failure from `Type: PRIVATE` | n/a |
| Email-validated certificate | Migrate to DNS validation for automatic renewal | Medium |
| Certificate with `InUse: false` | Review and remove — unused certs count against quota | Low |
| `DaysBeforeExpiry` at default 45 | Confirm 45 days suits the renewal process; range is 1-45 | Low |
| Private CA present or PKI architecture requested | Assess hierarchy against trust domains, assurance and issuing policy; justify depth rather than applying a universal numerical gate. Require concrete root-isolation and issuer-permission/chain evidence that the root does not issue end-entity certificates. Missing evidence stays UNKNOWN; a requirements review without a verified gap is ADVISORY. Metadata only, no key retrieval or issuance | Medium (verified gap only) |
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
| PCI DSS v3.2.1 **and** v4.0.1 both enabled | Retire v3.2.1 once coverage is compared; verify pricing before claiming duplicate charges | Medium |
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

## Service guide links

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
inventing a best-practices guide page. Supplemental network services use the pinned
firewall-overview links below.

## Focused suitability beyond enablement

Use these rows when the stated need is confirmed, including planned workloads and already
protected applications. Request the named metadata or sanitized existing evidence only;
account inventory cannot establish these requirements. Apply the parent evidence and handoff
rules. A design question without a verified gap is ADVISORY, not a missing-service finding.

| Confirmed need / service | Focused evidence and selection decision | Guide / handoff owner |
|---|---|---|
| AI threat coverage / GuardDuty and Hub | Confirm managed or self-hosted AI use, producer signals and custom model/package paths. Provisioning lists cannot exclude on-demand use; prompt-attack coverage requires enforced guardrail/policy evidence. Investigation preview needs current capability/region confirmation; existing results are not permission to start an investigation. | [GuardDuty][GD]; detection/AI owner |
| Repositories, CI/CD, CIS or SBOM / Inspector | Compare repository/language SAST/SCA/IaC coverage, existing build gates and release ownership; EC2 CIS requires SSM/plugin evidence. SBOM package inventory, CVE applicability and runtime coverage answer different questions. No scan or export initiation. | [Inspector][IN]; AppSec/CI owner |
| Data assurance / Macie | Compare required full-dataset coverage with sampling, supported formats/storage, explicit denies and unscannable reasons. Check export encryption/delivery and downstream publication independently. Identifier tuning must not hide accepted findings. | [Macie][MA]; data owner |
| Reachability, partner Extended, Azure or response routing / Hub | Require an actual missing capability, eligible authorized targets, connector health, subscription scope/permissions and consumers. Network Scanning is not automatic probing; Azure evidence is supplied, not a cross-cloud crawl. Preserve source severity and verify delivery before claiming response coverage. | [Hub][HU]; security/platform owner |
| Standards / CSPM | Match business obligations and AI use to current versions, recording and policy application. Compare transition coverage before retiring standards; do not infer duplicate ingestion from Hub/CSPM coexistence. Audit EventBridge/SIEM/ticketing/Lambda consumers; retain Macie publication and the central-configuration finding aggregator. | [CSPM][CS]; compliance owner |
| Investigation / Detective | Compare existing triage/forensic tooling with analyst timeline and EKS needs, graph packages, publishing freshness and sensitive-data access. Verify current eligibility separately from GuardDuty integration; graph/Lake presence does not prove usable correlation. | [Detective][DE]; investigation owner |
| Log analytics / Security Lake | Require ingestion/delivery evidence, source scope, OCSF/parser compatibility and consumer permissions. Select custom/partner sources and data versus query subscribers by need; compare local/rollup retention with forensic recovery and duplicate consumers before cost advice. | [Security Lake][SL]; logging/analytics owner |
| SGs/NACLs, endpoints and layered protection | Compare required IPv4/IPv6 flows with union of SG rules, stateless NACL return paths, endpoint routes/DNS and policy scope. An allow-all NACL alone is not a gap; private connectivity does not restrict destinations. Shield Standard is automatic network/transport protection, never a disabled-service gap or application-abuse solution. | [Network fundamentals][NF]; network/IAM owner |
| Segmentation / TGW, Cloud WAN, VPC Lattice | Compare intended trust zones with actual connectivity and bypass paths. Lattice identity boundaries need service and service-network AWS_IAM/auth policies, caller policies, explicit denies and signing; policies can allow anonymous access and do not provide connectivity. Verify topology-specific TCP/passthrough semantics. | [Segmentation][SG]; network/IAM owner |
| DNS Firewall | Check actual Resolver path, per-VPC association, managed/Advanced rules and delivered query logs. SGs cannot block AmazonProvidedDNS; DNS filtering does not cover hardcoded-IP egress. Confirm rule behavior from representative queries. | [DNS Firewall][DN]; DNS owner |
| Shield Advanced / Firewall Manager | Compare DDoS business impact and eligible resource coverage with current cost/bundling; FMS needs distributed policy-management requirements and org/Config prerequisites. Policy existence does not prove applied healthy protection. | [Network fundamentals][NF]; DDoS/platform owner |
| Network Firewall routing and policy | Absence is not a gap. Require routed inspection intent, actual deployment mode, bidirectional/AZ paths and bypass evidence. Compare HOME_NET/EXTERNAL_NET and inheritance with routed ranges, not blanket RFC1918. Broad pass actions can bypass later inspection; domains/SNI do not prove server identity. Managed rules need threat/capacity/version evidence. Strict order, defaults and logs alone do not prove blocking. | [Deployment][ND], [policy][NP]; firewall owner |
| Network Firewall TLS / Proxy | Require decrypted-content need, data permission, trust stores, certificate metadata and compatible clients/protocols (pinning, mTLS, QUIC/ECH and session behavior). Review narrow scope and revoked/unknown actions; inner-protocol rules after decryption differ from TLS.SNI. Proxy is preview in reviewed material and conditional: explicit proxy clients, endpoint reachability and bypass matter; NAT routing alone is not proxy inspection. | [TLS][NT], [deployment][ND]; network/PKI owner |
| Existing WAF or application-abuse protection | Request full endpoint set, association/origin restrictions, application stack and representative traffic/Count/log evidence. Include AppSync, Cognito, App Runner, Verified Access and non-AWS origins when relevant; verify current association/mTLS support. Choose managed groups, bot controls, ATP login/ACFP account-creation controls and CAPTCHA/Challenge only with relevant harm, client/token compatibility and current resource/protocol support. Tokens are not authentication; broad allow rules can bypass later controls. | [Managed rules][WM], [bots][WB], [fraud][WF], [tokens][WT]; WAF/application owner |
| Private PKI / ACM and Private CA | Compare trust domains and issuing policy with root isolation and permissions/chain evidence: root must not issue end-entity certificates; no universal CA depth. For sharing, connectors, CRL/OCSP or key/export requirements, inspect metadata and client trust/reachability/renewal ownership. Do not assume universal export bans or validity periods. CT opt-out cannot erase published data and needs client-trust review. Adequate alternative monitoring passes the certificate checks above. | [Certificates][CE]; PKI/application owner |
| Public or private AppSec / AWS Security Agent | Conditional application suitability, not an account-wide enabled state. Confirm ownership, exact target/access-domain redirect chain, exclusions, region/capability, app boundary and operator/service-role permissions. Private targets need VPC/subnet/SG, DNS, hybrid/TGW and return/dependency paths; never expose them publicly as a shortcut. Ask only credential-vendor metadata and realistic role/login/MFA requirements, never credentials. Verify processing/storage, retention and budget. A clean or UNREACHABLE result is not exhaustive security evidence; no test/domain verification launch. | [Security Agent][SA]; AppSec/network owner |

## Source caveats affecting decisions

- Security Agent private-testing NAT advice conflicts between the guide and linked setup
  devguide. Resolve target and dependency paths with the network owner; neither universal
  NAT installation nor removal follows from that conflict. Older models missing private
  operations or PRIVATE_VPC do not prove unavailability.
- Network Firewall TLS endpoint-association compatibility and exact per-leg idle timers
  remain unverified. Use current topology/client evidence; no universal incompatibility or
  restart rule. Interpret alert action versus final verdict, flow-end timing and delivered
  ALERT/FLOW/TLS evidence before judging enforcement. Zero rule hits do not prove redundancy.
- WAF rate-rule ordering conflicts in the guide: evaluate actual terminating actions,
  label dependencies and current semantics. Source TODOs on integrations/monetization are
  not verified capabilities. Verify current fraud response-inspection/protocol eligibility.
- PKI dates, feature regions/quotas and pricing need current evidence. Pinned guide links
  below preserve provenance only. Implementation recipes and full lifecycle catalogs stay
  in those sources; they are not additional assessment obligations.

[GD]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/guardduty/index.md
[IN]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/inspector/index.md
[MA]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/macie/index.md
[HU]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub/index.md
[CS]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub-cspm/index.md
[DE]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/detective/index.md
[SL]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-lake/index.md
[NF]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/fundamentals/docs/index.md
[SG]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/segmentation/docs/index.md
[DN]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/dns-firewall/index.md
[ND]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/deployment-architecture/docs/index.md
[NP]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/firewall-policy-configuration/docs/index.md
[NT]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/tls-inspection/docs/index.md
[WM]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/aws-managed-rules/docs/index.md
[WB]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/bot-management/docs/index.md
[WF]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/fraud-prevention/docs/index.md
[WT]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/captcha-and-challenge/docs/index.md
[CE]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/certificate-services/index.md
[SA]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-agent/index.md

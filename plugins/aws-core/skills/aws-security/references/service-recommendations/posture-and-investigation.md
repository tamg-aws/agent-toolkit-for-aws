# Posture, correlation and investigation decisions

Use only the selected section under the [recommendation workflow](../service-recommendations.md).
Existing [enablement checks](enablement-checks.md) retain collection and scoped negative-state rules.

## Hub capability and producer coverage

| Evidence | Selection consequence / overlap trap |
|---|---|
| Unified Hub state, linked regions, policy targets/application and source-service state | Separate aggregation, intended policy and deployed producer coverage. Hub presence does not establish that GuardDuty/Inspector/Macie are effectively covering a workload. |
| Actual missing reachability-assessment capability, eligible targets, existing exclusions and owner authorization | Consider Network Scanning only for that need; inventory is not permission to probe. Unresolved resource support prevents an eligibility conclusion. |
| Missing partner capability, connector health, Marketplace subscription and terms | Evaluate Extended coverage for that capability. A connector alone neither proves an active subscription nor justifies duplicate tooling. |
| Confirmed Azure use and supplied subscription/federation/app-permission metadata | Check integration scope and health without secrets or a cross-cloud crawl. Unknown permissions remain an integration question, not evidence that Azure is unprotected. |
| Routing order, connector state, ticket/update consumer and delivery evidence | Recommend closing a demonstrated ownership/delivery gap. A rule or connector's existence does not prove response coverage; preserve findings severity and visibility. |

For AI-related exposure, use [AI and malware scope](detection-and-vulnerability.md#ai-and-malware-scope)
only when producer eligibility is in question. Exposure traits/trends do not establish
producer completeness or justify invented score transformations. Source: [Hub traits,
policies, integrations and Extended guidance][HU].

## Standards and recorder context

Match standards to business obligations and confirmed AI workloads using the current catalog.
Compare control coverage during transition: simultaneous old/new standards are not themselves
a gap. Retirements/version claims need current evidence before recommending a migration.

Resolve standalone CSPM versus unified Hub plus CSPM before advising on Config. The
standalone recorder check in [enablement checks](enablement-checks.md) owns status and scope
validation; the service-linked recorder case must not become a missing customer-recorder gap.
For other Config uses, establish CMDB, rule, conformance-pack, remediation and audit consumers
before considering scope reduction. This is supplemental Config context, not a separate audit.

Coexistence of Hub and CSPM is not duplicate ingestion evidence. Compare the actual findings
paths and EventBridge/SIEM/ticketing/Lambda consumers first. Retain Macie publication and the
finding aggregator required for central configuration. Under central configuration,
false/NONE auto-enable values are expected; policy association/application and member coverage
still need separate evidence under the workflow's organization review.

A demonstrated duplicate path with no dependent consumer may support consolidation advice;
unknown consumer ownership does not. Sources: [CSPM standards, duplicate aggregation and
Config guidance][CS], [Hub policies versus deployments][HU].

## Investigation fit

Compare the analyst's question with existing tooling before recommending Detective: quick
triage, entity timelines, cross-account/EKS context and deep raw-log reconstruction are
different needs. Use graph/package/member state, publishing freshness and analyst access
to judge whether a proposed capability would be usable. Graph and Lake presence alone do
not establish correlation; integration/source availability and query permissions matter.

An analyst who already has the required timelines may not need another investigation tool.
If EKS context is missing, evaluate relevant packages and access rather than claiming any
new graph would solve it. Use existing entity/time-scoped results to choose a handoff;
no new investigation or hunt follows from this assessment.

The guide's GuardDuty prerequisite claim needs current Detective eligibility verification.
Keep GuardDuty's findings-integration role distinct from an unverified mandatory gate; do
not recommend enabling it solely to satisfy that claim. Source: [Detective fit, packages
and integration guidance](https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/detective/index.md).

## Lake sources and consumers

| Evidence | Recommendation consequence |
|---|---|
| Required source/account/region, trail selectors where relevant, ingestion exceptions and delivery | Recommend a missing source only for the investigation need and verified eligibility. Configured source presence is not proof of healthy delivery. |
| Custom/partner source ownership, OCSF version, normalization and parser compatibility | Resolve schema and downstream compatibility before selecting an ingestion path or upgrade. A newer version is not automatically safe for current consumers. |
| Consumer's data versus query need, subscriber source scope and permissions | Choose the access model from the actual consumer requirement. Subscriber existence alone does not establish useful or appropriately scoped access. |
| Actual local/rollup retention and S3 lifecycle, native-log consumers and incident recovery objective | Compare recoverable history before cost advice. Do not remove the only usable source because Lake is enabled; cold-tier retrieval behavior and current charges need evidence. |

For example, an enabled source with failed ingestion supports a delivery investigation;
it does not prove the SIEM has that data or justify retiring its working native-log path.
Source: [Security Lake sources, subscribers, schema updates and retention][SL].

## Identity-analysis context

Use [IAM Access Analyzer's current overview](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)
for analyzer types and scope, not as a guide-sourced service recommendation. External-access
analyzers need relevant-region evidence; unused-access findings do not vary by region, so
repeating analyzers by region is not coverage expansion. Verify internal-access scope separately.
Compare the actual access question with the analyzer type and resource scope: an existing
unused-access analyzer cannot by itself answer an external-sharing question. Policy presence
or aggregation likewise does not establish an identity boundary; route Lattice-specific advice
to [segmentation](network-protection.md#segmentation-and-identity) only when that path is relevant.

[HU]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub/index.md
[CS]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub-cspm/index.md
[SL]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-lake/index.md

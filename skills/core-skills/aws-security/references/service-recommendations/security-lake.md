# Security Lake lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

Reuse the selected [existing service procedures](../../SKILL.md) for configuration and existing findings metadata only. Do not start investigations, queries, analyses, exports or response automation.

## T061

**Topic:** Organization trail, defaults, optional high-volume sources and enrollment

**Trigger:** Security log centralization.

**Evidence:** Trail selectors, account/region/source state, default-vs-opt-in source choice and exception health.

**Decision:** Compare trail selectors, default/optional sources and ingestion health across approved scope; source enablement is not successful delivery and high-volume sources require an investigation need.

**Handoff:** Lake/platform owner: source enrollment and health review with current prerequisites. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T062

**Topic:** Rollup, retention and duplicate native-log collection

**Trigger:** Security Lake cost review.

**Evidence:** Rollup/local retention, duplicate flows/DNS/trail consumers and loss-of-history risk.

**Decision:** Compare local/rollup retention and duplicate consumers with investigation history needs; avoid deleting the only usable source merely because another service is enabled.

**Handoff:** Lake/FinOps owner: retention and duplication decision with consumer and recovery dependencies. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T063

**Topic:** Partner/custom ingestion and OCSF conversion

**Trigger:** Non-native logs or existing partner integrations.

**Evidence:** Source ownership, supported schema, normalization/Parquet path and ingest health; CSPM intermediary dependency.

**Decision:** Require schema/normalization and delivery evidence for partner/custom logs; compare direct conversion/Parquet ingestion with intermediary dependencies.

**Handoff:** Data-engineering/Lake owner: source normalization and ingestion validation design, with no converter/code authoring here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T064

**Topic:** Analytics and subscriber access models

**Trigger:** Need investigations/dashboards or SIEM consumption.

**Evidence:** Athena/QuickSight/OpenSearch needs; S3 data vs Lake Formation query access, subscriber scope and permissions.

**Decision:** Choose S3 data access versus Lake Formation query access by consumer need; evaluate subscriber scope and permissions separately from Athena/QuickSight/OpenSearch suitability.

**Handoff:** Lake/IAM/analytics owner: subscription and bounded analytics design; no queries, subscriptions or dashboards created. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T065

**Topic:** Schema upgrades and downstream compatibility

**Trigger:** New OCSF schema/source version.

**Evidence:** Current source/schema versions and downstream partner/query compatibility evidence.

**Decision:** Gate source/OCSF version changes on downstream parser, partner and query compatibility; a newer schema alone is not a safe upgrade.

**Handoff:** Data-engineering/consumer owners: version compatibility and migration validation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T066

**Topic:** S3 lifecycle drift and cold-log recoverability

**Trigger:** Retention or archive cost changes.

**Evidence:** Actual S3 lifecycle versus console state, minimum storage/object costs, retrieval delay and incident/audit RTO.

**Decision:** Compare actual S3 lifecycle with Lake configuration and incident/audit recovery objectives; assess cold-tier delay, minimum charges and object costs using current terms.

**Handoff:** Lake/storage owner: recoverability-tested retention proposal preserving required evidence windows. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

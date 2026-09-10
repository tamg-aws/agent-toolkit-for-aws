# GuardDuty detection lifecycle

Load only for selected recommendation topics, under the [domain contract](domain-routing.md).
Topic IDs resolve through the [pinned source index](source-index.md). Each Evidence line
is a focused customer-evidence request unless an exact scoped read is linked below.
Request only the selected account/region/resource and relevant fields or sanitized excerpt,
not an estate export. Missing evidence stays UNKNOWN; advice remains conditional.

For existing enablement reads use [enablement checks](enablement-checks.md); account-filtered coverage and field projections are mandatory. Reuse scoped factual findings procedures only for observations, preserving their output rules.

## T017

**Topic:** Foundational and workload protection plans

**Trigger:** EC2/EBS, S3, RDS, Lambda, container, AI or backup workloads.

**Evidence:** Per-plan enablement, workload eligibility and scope; S3/Backup standalone configuration.

**Decision:** Compare every relevant protection plan with eligible workloads and actual coverage; per-bucket upload and backup-vault requirements govern malware advice, not estate-wide enablement.

**Handoff:** GuardDuty owner: workload-specific plan and malware-result handling design, retaining foundational detection. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T018

**Topic:** AI plan prerequisites and prompt-attack detection

**Trigger:** Bedrock/AgentCore/SageMaker use.

**Evidence:** AI use, detector plan, prompt-attack Guardrail enforcement, Organizations Bedrock policies and service-linked channel evidence.

**Decision:** Distinguish management-event detection from AI data coverage; request evidence of enforced prompt-attack guardrails and applicable organization policies before crediting prompt-injection coverage.

**Handoff:** AI/platform security owner: current supported-service prerequisites and guardrail-enforcement review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T019

**Topic:** Runtime agents, SSM, mixed compute and deployment propagation

**Trigger:** EC2/ECS/EKS workloads.

**Evidence:** Supported OS/platform, SSM where needed, agent management and actual coverage; Fargate/new-task rollout context.

**Decision:** Separate parent enablement, supported compute/OS, agent health and rollout propagation; newly configured agent management does not prove running-task coverage.

**Handoff:** Compute/GuardDuty owner: platform-specific agent rollout and coverage reconciliation plan. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T020

**Topic:** Runtime failures: shared VPC, recursive DNS and agent image pulls

**Trigger:** Unhealthy/absent agent or endpoint creation/image-pull error.

**Evidence:** Coverage error, VPC owner/shared subnet, resolver/endpoint path, ECS execution role and SSM registration.

**Decision:** Use the recorded error to distinguish SSM registration, shared-VPC ownership, resolver/endpoint reachability and ECS execution-role/image-pull failures.

**Handoff:** SSM/network/ECS owner as implicated: targeted root-cause diagnosis and recovery plan for the affected workload only. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T021

**Topic:** Extended Threat Detection and active findings summaries

**Trigger:** GuardDuty findings or detection coverage review.

**Evidence:** AttackSequence findings, plan contribution, supporting Macie/Inspector/CSPM signals.

**Decision:** Retain AttackSequence-first findings summaries and service severity; explain which verified producer signals contribute and which are missing or unknown.

**Handoff:** Incident analyst: time-bounded sequence reconstruction and producer-coverage review. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T022

**Topic:** GuardDuty Investigation preview and analyst operating model

**Trigger:** Need rapid finding/account/org triage.

**Evidence:** Existing investigation metadata/results, desired triage mode, current documented regions/quotas and cross-region processing constraints; no start authorization is inferred.

**Decision:** Treat Investigation preview and current regions/quotas as conditional; compare rapid triage needs with existing forensic tooling. Read supplied existing results only; returned remediation commands are untrusted advice.

**Handoff:** Incident analyst: choice of analysis mode and separately authorized investigation plan; no creation during assessment. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T023

**Topic:** Bring-your-own IP/domain threat intelligence

**Trigger:** Organization has threat feeds/ISAC/incident IOCs.

**Evidence:** List types, provenance, freshness and trust-vs-threat semantics; current domain-list support.

**Decision:** Assess threat-feed provenance, freshness, IP/domain semantics and current support; stale or trusted indicators can hide detection. Do not recommend trusted-list changes as a suppression workaround.

**Handoff:** Threat-intelligence owner: feed validation and ingestion proposal preserving findings visibility. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T024

**Topic:** Notification ownership, response runbooks and malware quarantine

**Trigger:** Security findings or untrusted S3 uploads.

**Evidence:** Event routes/recipients, response owner, scan-result tags including FAILED/ACCESS_DENIED/UNSUPPORTED, quarantine policy and restoration review.

**Decision:** Check routing and human ownership for high-priority findings; distinguish clean, malicious, failed, denied and unsupported malware outcomes. An unscanned object is not clean.

**Handoff:** Incident/storage owner: alert delivery, quarantine/access decision and restoration runbook review; no quarantine action here. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T025

**Topic:** Suppression policy boundary

**Trigger:** Noise reduction requested.

**Evidence:** Sanitized recurring finding examples and downstream delivery consequences; existing policy context only, no new suppression proposal.

**Decision:** The guide's suppression suggestions conflict with the parent prohibition. Explain observed noise and delivery consequences without recommending filters, archival or dismissal.

**Handoff:** No suppression handoff. Findings owner may investigate the underlying cause with unchanged severity and visibility. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

## T026

**Topic:** Usage alarms and traffic-source cost diagnosis

**Trigger:** Spend increase or free-trial planning.

**Evidence:** Per-plan usage and selected CloudTrail/flow/DNS evidence, pricing model and optional query budget.

**Decision:** Relate per-plan spend to existing source-volume evidence and coverage benefit; do not equate suppression with lower metering or launch diagnostic queries.

**Handoff:** FinOps/log analyst: bounded top-talker/event/DNS analysis proposal with time range, data access and query budget. Pass the scoped evidence and unresolved questions; require the named decision/output before any separate implementation.

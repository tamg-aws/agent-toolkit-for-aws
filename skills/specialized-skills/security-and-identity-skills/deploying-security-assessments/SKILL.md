---
name: deploying-security-assessments
description: >
  Deploy and run the AWS Self-Service Security Assessment Solution (SATv2) — the
  Prowler-based assessment used by the Security Health Improvement Program (SHIP)
  workshop — in a single AWS account or across an AWS Organization. Covers deploying
  the ProwlerMemberRole to member accounts by service-managed StackSet and to the
  management account by plain stack, granting the scanning account the AWS
  Organizations permissions the scan requires, deploying the CodeBuild solution
  stack, choosing the Basic, Intermediate, or Full scan tier, turning on
  multi-account scanning, and retrieving results from S3, Glue, and Athena. Use when
  the user wants to deploy SATv2, run a Prowler scan across their accounts, stand up
  the SHIP workshop tooling, or diagnose a failed SATv2 build. Do NOT use to decide
  which AWS security services a workload warrants, or to summarize findings that
  already exist in GuardDuty, Security Hub, or Inspector.
---

# Deploying Security Assessments (SATv2)

**STOP — this skill creates live infrastructure across multiple AWS accounts.** Before
any deploy step, read `references/prerequisites.md` and complete the credential and
topology checks. **Creating** the solution stack starts a scan immediately; there is no
separate trigger step on create. Do not run a deploy command until the user has approved
it.

## Overview

SATv2 (the AWS Self-Service Security Assessment Solution) runs
[Prowler](https://github.com/prowler-cloud/prowler) inside CodeBuild and writes findings
to S3, with optional Glue and Athena reporting. It answers **"are the resources in my
accounts configured according to best practice?"**

It does not answer "which security services should I turn on" (that is
`recommending-security-services`) and it does not summarize findings that already exist
in GuardDuty, Security Hub, Inspector, or Macie (that is `aws-security`).

Source of truth: [`awslabs/aws-security-assessment-solution`](https://github.com/awslabs/aws-security-assessment-solution).
Two templates at the repository root:

| Template | Vehicle | Target |
|---|---|---|
| `1-sat2-member-roles.yaml` | Service-managed StackSet, deploy-to-organization, **one region** | Every member account |
| `1-sat2-member-roles.yaml` | Plain stack, deployed separately | **Management account** — StackSets do not apply to it |
| `2-sat2-codebuild-prowler.yaml` | Plain stack | **Scanning account only** (the workshop uses the audit account) |

## Global rules

1. **Explicit approval before every write to AWS.** You MUST obtain explicit user
   approval before any command that creates, modifies, or deletes anything — the stack
   operations (`create-stack`, `update-stack`, `delete-stack`, `create-stack-set`,
   `create-stack-instances`, `delete-stack-instances`, `delete-stack-set`) **and** the
   organization-wide and account-wide settings this skill also instructs:
   `cloudformation activate-organizations-access` / `deactivate-organizations-access`,
   `organizations register-delegated-administrator` / `deregister-delegated-administrator`,
   the Organizations delegation policy (`put-resource-policy`), and
   `lakeformation grant-permissions`. That list is illustrative, not exhaustive: if a
   command changes state, it needs approval. Display the exact command and wait. Deleting
   the throwaway dry-run stack from the validation step is a `delete-stack` and counts.

   Approval may be given in advance, but only narrowly. It counts as pre-authorization
   when it names the specific operations it covers — including any of the
   organization-wide settings above that the run may need — and, for creating the
   solution stack, acknowledges that the create starts a scan and incurs its cost. A
   blanket "go ahead" does not qualify. Pre-authorization changes nothing else: still run
   the identity check in rule 2, still read before each write and verify after it (rules
   4 and 5), and record every command as it runs so the user can audit exactly what their
   approval covered. With no user available to ask and no such pre-authorization, do not
   deploy.

2. **Echo identity and confirm before acting.** Before the first deploy step, run
   `aws sts get-caller-identity` and `aws organizations describe-organization`, then echo
   the account ID, caller ARN, resolved region, and whether that account is the
   management account back to the user and ask them to confirm or correct. Never assume
   the active profile is the intended account — this solution spans three account roles
   and the wrong one fails late.

3. **Creating the stack runs a scan; updating it does not.** On **create**,
   `2-sat2-codebuild-prowler.yaml`'s `Custom::CodeBuildStartBuild` resource launches the
   scan, so approval for the stack IS approval for the scan and its cost. Say so
   explicitly before creating; do not present the scan as a later, separate decision.

   On **update** no scan starts. The custom resource's only properties are `ServiceToken`
   and `ProjectName`, and `ProjectName` resolves to the static literal `ProwlerCodeBuild`, so
   no parameter change alters it and CloudFormation sends the resource no update. Its Lambda
   also acts only on `RequestType == 'Create'` and no-ops otherwise. After an update you MUST
   start the build yourself:

   ```bash
   aws codebuild start-build --profile <scanning_profile> --project-name ProwlerCodeBuild
   ```

   Do not describe parameter changes as touching "only environment variables" — changing
   `MultiAccountScan` also toggles whether the stack creates its own member role, so it
   adds or removes an IAM resource. See `references/troubleshooting.md`.

   Treat that as its own approval point — it incurs the same scan cost as a create.

4. **Read before write.** Every step in `references/satv2-deployment.md` has a
   read-before-write check. Run it and report current state before proposing the write.
   Assume the account is already partially configured.

5. **Verify after write.** After each step, run its stated verification and report the
   result. Do not describe a step as complete on the basis of the command exiting zero.

6. **Report the Prowler version honestly, and never bump it.** The template pins
   `prowler==5.11` deliberately. Read the pin from the template at runtime, compare it to
   the current release, and report the gap as a fact. Changing the pin breaks the Glue
   table schema. See `references/troubleshooting.md`.

7. **Never widen the member role.** `ProwlerMemberRole` carries `SecurityAudit` +
   `ViewOnlyAccess` plus an inline `ProwlerAdditions` policy. That inline policy is
   read-only with exactly one exception — **`securityhub:BatchImportFindings`**, a write
   action that lets SATv2 push its ASFF output into Security Hub in the assessed account.
   Do not describe the role as purely read-only, and disclose that write when the role is
   deployed into the management account. Do not add further permissions to make a check
   pass.

8. **State cost before scanning, not after.** Scan cost scales with tier, account count,
   and concurrency. Give the driver before the user approves. The findings bucket is
   `DeletionPolicy: Retain` and survives stack deletion.

## Before you start

Read `references/prerequisites.md` and confirm all of the following. Any missing item
stops the deployment partway through:

- Which account is the **management account**, and whether the user can obtain
  credentials for it. Management-account access is required at **four** points and is not
  optional.
- Which account will be the **scanning account** (the workshop uses the audit account).
- Whether the scanning account can call `aws organizations list-accounts`. If not, an
  Organizations delegation policy is required first.
- The **home region** for the StackSet — the member-role StackSet deploys to one region.

## Task registry

| Request | Route to |
|---|---|
| "deploy SATv2", "set up the security assessment", "run the SHIP workshop tooling" | `references/prerequisites.md`, then `references/satv2-deployment.md` |
| "which scan tier", "Basic vs Intermediate vs Full", "how long will this take" | `references/satv2-deployment.md`, tier section |
| "scan all my accounts", "it only scanned one account" | `references/satv2-deployment.md`, multi-account section |
| "where are my results", "query the findings", "Athena", "dashboard" | `references/reviewing-results.md` |
| "the build failed", "list-accounts error", "timeout", "parameter error" | `references/troubleshooting.md` |
| "remove SATv2", "clean up" | `references/satv2-deployment.md`, cleanup section |

## Three traps to raise proactively

These are defects in the deployment path that a user following the workshop text will hit.
Raise them before the user encounters them, not after.

1. **`MultiAccountScan` defaults to `'false'`.** A default deploy scans **only the
   scanning account**, not the organization. A user can believe they assessed every
   account and have assessed one. Confirm intent explicitly.

2. **The workshop text has the wrong parameter name.** It calls the member-role parameter
   `AuditAccountId`. The real name is **`ProwlerAccountID`** (pattern `\d{12}`, default
   `'012345678910'`). Following the prose produces a validation error.

3. **The `Full` tier is unbounded.** It passes an empty filter, so runtime is governed
   only by `CodeBuildTimeout` (default 300 minutes). On a large organization this is the
   tier that hits the ceiling. Size it against account count before selecting it.

## Not covered

- **SRA Verify**, the other tool in the SHIP workshop, is not covered by this skill.
  It is a different tool (`awslabs/sra-verify`, not Prowler) answering a different
  question — whether the organization implements the AWS Security Reference Architecture.
  Point the user at the workshop for it.
- **The SHIP advisory engagement** is a separate, meetings-based AWS program with nothing
  to deploy. It is an optional follow-on for interpreting findings, not a prerequisite.
- **Remediating** findings. This skill deploys the assessment and retrieves results. It
  does not change the resources the assessment flags.

---
name: deploying-sra-verify
description: >
  Deploy and run AWS SRA Verify — the AWS Security Reference Architecture (SRA)
  conformance checker from the Security Health Improvement Program (SHIP)
  workshop — across an AWS Organization from CodeBuild in the audit account.
  Covers deploying SRAMemberRole to member accounts by StackSet and to the
  management account by plain stack, granting the audit account the AWS
  Organizations permission the scan needs, deploying the CodeBuild stack (which
  auto-starts the scan), choosing scan regions, and retrieving the consolidated
  CSV and HTML dashboard from S3. Use when the user wants to deploy SRA Verify,
  check whether their org implements the SRA (delegated administrators, an
  organization CloudTrail, GuardDuty, Security Hub, Config, Macie), or diagnose
  a failed SRA Verify build. Do NOT use for
  Prowler resource-configuration assessment (deploying-security-assessments),
  choosing which security services a workload warrants
  (recommending-security-services), or summarizing findings already in a
  security service.
version: 1
---

# Deploying SRA Verify

**STOP — this skill creates live infrastructure across multiple AWS accounts.** Before
any deploy step, read `references/prerequisites.md` and complete the credential and
topology checks. **Creating** the solution stack starts a scan immediately; there is no
separate trigger step on create. Do not run a deploy command until the user has approved
it.

## Overview

SRA Verify runs the open-source [`awslabs/sra-verify`](https://github.com/awslabs/sra-verify)
tool inside CodeBuild and writes results to S3 as a consolidated CSV, per-account CSVs, and a
static HTML dashboard. It answers **"does my organization implement the AWS Security
Reference Architecture?"** — is there an organization CloudTrail, are GuardDuty, Security
Hub, Config, Macie, Inspector and IAM Access Analyzer enabled and delegated to the audit
account, do the audit and log-archive accounts play their SRA roles.

It does **not** assess whether individual resources are configured to best practice — that is
Prowler, covered by `deploying-security-assessments`. It does not recommend which services to
turn on (`recommending-security-services`) or summarize findings that already exist in a
security service (`aws-security`). SRA Verify and SATv2 are the two tools in the SHIP
workshop and are frequently deployed together; they share the delegated-administrator
prerequisite and nothing else.

Source of truth: [`awslabs/sra-verify`](https://github.com/awslabs/sra-verify). Two templates
at the repository root:

| Template | Vehicle | Target |
|---|---|---|
| `1-sraverify-member-roles.yaml` | Service-managed StackSet, deploy-to-organization, **one region** | Every member account |
| `1-sraverify-member-roles.yaml` | Plain stack, deployed separately | **Management account** — StackSets do not apply to it |
| `2-sraverify-codebuild-deploy.yaml` | Plain stack | **Audit account only** (the account that runs CodeBuild) |

## Global rules

1. **Explicit approval before every write to AWS.** You MUST obtain explicit user
   approval before any command that creates, modifies, or deletes anything — the stack
   operations (`create-stack`, `update-stack`, `delete-stack`, `create-stack-set`,
   `create-stack-instances`, `delete-stack-instances`, `delete-stack-set`) **and** the
   organization-wide and account-wide settings this skill also instructs:
   `cloudformation activate-organizations-access` / `deactivate-organizations-access`,
   `organizations register-delegated-administrator` / `deregister-delegated-administrator`,
   the Organizations delegation policy (`put-resource-policy` to add or trim,
   `delete-resource-policy` to remove) — plus `codebuild start-build`, which starts a
   billable scan, and `create-change-set` / `delete-change-set`, which provision no resources
   but — for a `CREATE`-type change set — create and remove a stack record. That list is meant
   to be complete enough for a pre-authorization to name; if a command changes state and is not
   on it, it still needs approval. Display the exact command and wait. Deleting the throwaway
   dry-run stack from the validation step is a `delete-stack` and counts; the validation
   section may present that stack's dry-run commands together for a single confirmation, since
   none of them touches a resource. Deleting or moving objects in the findings bucket — the
   only instructed write that destroys the user's data — is never covered by a
   pre-authorization: each instance needs its own approval.

   Approval may be given in advance, but only narrowly. It counts as pre-authorization
   when it names the specific operations it covers — including any of the organization-wide
   settings above that the run may need — and, for creating the solution stack, acknowledges
   that the create starts a scan. A blanket "go ahead" does not qualify. Pre-authorization
   changes nothing else: still run the identity check in rule 2, still read before each write
   and verify after it (rules 4 and 5), and record every command as it runs so the user can
   audit exactly what their approval covered. With no user available to ask and no such
   pre-authorization, do not deploy.

2. **Echo identity and confirm before acting.** Before the first deploy step, run
   `aws sts get-caller-identity` and `aws organizations describe-organization`, then echo
   the account ID, caller ARN, resolved region, and whether that account is the management
   account back to the user and ask them to confirm or correct. Decide "management" from
   `describe-organization`'s `MasterAccountId`, never from an account or profile name — one
   management account observed in a sibling deployment was *named*
   `Organization_Delegated_Administrator`. This solution spans three account roles
   (management, audit, member) and the wrong one fails late.

3. **Creating the solution stack runs a scan; updating it does not.** On **create**,
   `2-sraverify-codebuild-deploy.yaml`'s `Custom::CodeBuildStartBuild` resource launches the
   scan, so approval for the stack IS approval for the scan. Say so before creating; do not
   present the scan as a later, separate decision.

   On **update** no scan starts — the custom resource's backing Lambda acts only on
   `RequestType == 'Create'`. After an update you MUST start the build yourself:

   ```bash
   aws codebuild start-build --profile <audit_profile> --project-name SRAVerify-Security-Assessment
   ```

   Treat that as its own approval point.

4. **Read before write.** Every step in `references/sraverify-deployment.md` has a
   read-before-write check. Run it and report current state before proposing the write.
   Assume the account is already partially configured — SATv2 and SRA Verify are often
   deployed into the same audit account.

5. **Verify after write.** After each step, run its stated verification and report the
   result. Do not describe a step as complete on the basis of the command exiting zero.

6. **The tool is not pinned — record what actually ran.** Unlike SATv2's Prowler pin, the
   solution's `GitBranch` parameter defaults to `main` and the buildspec **clones the branch at
   build time** (`git clone -b $GIT_BRANCH … && pip install ./sra-verify/sraverify`). The check
   set, the account-type logic, and the member-role permissions all come from that branch's
   `HEAD` on the day the build ran. Report the branch and the build's start time; the buildspec
   clones by branch and runs no `git rev-parse`, so the build log does **not** carry the cloned
   commit (the clone line reads only `Cloning into 'sra-verify'...`). Resolve what `main` pointed
   to at that time out of band (`git ls-remote https://github.com/awslabs/sra-verify.git main`,
   or the repo's history at the build timestamp) to make a run reproducible and drift visible;
   `git clone -b` takes only a branch or tag, not a bare commit, so `GitBranch` cannot pin the
   tool to a SHA. The member role's permissions
   ship in the **same** template on the **same** branch — the `GitBranch` description says so —
   so a member role from an older branch can lack a permission a newer check needs. Keep the
   role template and the solution on the same branch.

7. **The member role is read-only — do not widen it.** `SRAMemberRole` carries two managed
   policies, `SRAVerifyLeastPrivilege` (about 78 actions across roughly 29 services) and
   `SRAVerifyCheckPermissions` (`account:GetAccountInformation`). Every action is a read; the
   one verb that looks like a write, `apigateway:GET`, is API Gateway's read call. There is no
   `sts:AssumeRole` in the role's own policies and no write action anywhere — it is a genuinely
   read-only role, and cannot push findings anywhere (contrast SATv2's `ProwlerMemberRole`,
   which can write to Security Hub). If a check fails for lack of permission, that is a
   branch-mismatch (rule 6) or an upstream gap — fix it there, never by adding permissions.

8. **The cost is small; the data is the real exposure.** CodeBuild runs on
   `BUILD_GENERAL1_SMALL` and the workshop bills most customers "less than a few dollars,"
   often inside the free tier. State that honestly rather than overwarning. What *does* need
   care is the output: the findings name account IDs and service configuration, the dashboard
   is loaded by pasting a **presigned S3 URL** (time-limited credentials — never shared), and
   the dashboard's "Copy generative AI prompt" builds a prompt containing organization findings
   that the user may paste into a model. See `references/reviewing-results.md`.

## Before you start

Read `references/prerequisites.md` and confirm all of the following. Any missing item
stops the deployment partway through:

- Which account is the **management account**, and whether the user can obtain
  credentials for it. Management-account access is required at several points — the
  StackSet (unless StackSets is delegated to the audit account), the management account's own
  role stack, trusted-access activation, any delegated-administrator registration or delegation
  policy, and reversing each at cleanup — and is not optional.
- Whether `aws cloudformation describe-organizations-access` returns `ENABLED`. If not,
  activating trusted access is a management-account, organization-wide write that needs
  approval under rule 1 before Step 1 can run.
- Which account is the **audit account** — the one that runs CodeBuild and holds results.
  In an SRA-aligned organization this is the Security Tooling account where GuardDuty or
  Security Hub administration is delegated.
- Which account is the **log-archive account**. Both the audit and log-archive account IDs
  are **required** parameters on the solution stack (comma-separated lists; no defaults) and
  drive the audit-type and log-archive-type checks.
- Whether the audit account can call `aws organizations list-accounts`. If not, check
  whether it is already a delegated administrator for any service; only if it is not does it
  need an Organizations delegation policy — an organization-level write.
- The **regions to scan**. `IncludeRegions` defaults to only `us-east-1,us-east-2,us-west-2`;
  anything configured elsewhere is invisible to the scan. See the region trap below.

## Task registry

| Request | Route to |
|---|---|
| "deploy SRA Verify", "check our SRA alignment", "run the SHIP workshop SRA tool" | `references/prerequisites.md`, then `references/sraverify-deployment.md` |
| "which accounts get scanned", "account types", "management vs audit vs application checks" | `references/sraverify-deployment.md`, account-type section |
| "which regions", "it missed a region", "IncludeRegions" | `references/sraverify-deployment.md`, parameters; trap 3 below |
| "where are my results", "the dashboard", "presigned URL", "consolidated CSV" | `references/reviewing-results.md` |
| "the build failed", "list-accounts error", "no results", "management checks failed" | `references/troubleshooting.md` |
| "remove SRA Verify", "clean up" | `references/sraverify-deployment.md`, cleanup section |
| "re-run the scan", "we added accounts", "scan again" | `references/sraverify-deployment.md`, "Re-running" — an update starts no scan |
| "trusted access", "StackSets is DISABLED", "not a delegated administrator", `--call-as` errors | `references/prerequisites.md`, identity check and "Two different kinds of delegated administrator" |
| "role already exists", "StackSet failed on an account", collision | `references/prerequisites.md`, "The member accounts you cannot pre-check" |
| "cfn-lint fails", "validate the templates", "dry run" | `references/prerequisites.md`, "Validate both templates before deploying" |
| "which check is which", "list checks", "SRA-GD-1" | `references/reviewing-results.md`, "The checks" |

## Traps to raise proactively

These are defects in the deployment path a user following the workshop or the upstream README
will hit. Raise them before the user encounters them, not after.

1. **The workshop text has the wrong parameter name.** As observed in 2026-09, the workshop
   calls the member-role parameter `AuditAccountId`. The real name in
   `1-sraverify-member-roles.yaml` is **`SRAVerifyAccountID`** (pattern `\d{12}`, default
   `'012345678910'`). Following the prose produces a validation error. Confirm against the
   current workshop page before telling a user their documentation is wrong.

2. **There is no single-account mode and no scope-down parameter.** SRA Verify always
   enumerates every ACTIVE account via `organizations list-accounts` and scans all of them —
   there is no `MultiAccountScan`-style toggle and no override list. If the user wants to
   assess only part of the organization, the only levers are which OUs received the member-role
   StackSet and `IncludeRegions`; there is no parameter that limits the account set.

3. **`IncludeRegions` defaults to three regions.** The default is
   `us-east-1,us-east-2,us-west-2`. A service enabled only in, say, `eu-west-1` is reported as
   absent, and a regional check simply does not run there. This silently understates coverage
   and can turn a compliant region into a false finding. Confirm the region list against where
   the organization actually operates before deploying; the workshop itself recommends adding
   `us-west-1`.

4. **The management account needs the role too, or its checks fail.** The buildspec runs the
   40 management-type checks by assuming `SRAMemberRole` in the management account, and also
   runs the generic application checks against **every** account including the management,
   audit and log-archive accounts. StackSets never reach the management account, so without the
   Step 2 plain stack the management-type checks — the organization CloudTrail, delegated
   administrators, the SRA backbone — all fail. This is the most common incomplete deployment.

5. **The tool is unpinned.** `GitBranch=main` means the scan runs whatever is on the branch
   the day it builds — a moving target. Two runs weeks apart can differ in checks and behavior
   with no change on your side. Record the branch and the build's cloned commit (rule 6).

6. **The workshop's management-account step calls this "the SATv2 solution that runs Prowler."**
   On the SRA Verify management-account deploy page, the parameter instruction reads "…the account
   where you will deploy the SATv2 solution that runs Prowler in CodeBuild." That is a copy-paste
   artifact from the SATv2 module — `1-sraverify-member-roles.yaml` is SRA Verify
   (`awslabs/sra-verify`) and runs no Prowler. Do not let that line make you think you downloaded
   the wrong template; the StackSet step on the same page describes it correctly.

## Not covered

- **The SRA Verify MCP server** (`awslabs/sra-verify-mcp`) is a separate agent-native route
  that runs individual checks over a least-privilege role without CodeBuild. It is out of scope
  for this skill, which covers the CodeBuild deployment the SHIP workshop uses. Point the user
  at [`awslabs/sra-verify-mcp`](https://github.com/awslabs/sra-verify-mcp) if they want it.
- **Running `sraverify` as a local CLI** against a single account is useful for debugging one
  failing check; `references/troubleshooting.md` shows the invocation. Standing up the org-wide
  assessment is the CodeBuild path here.
- **SATv2 / Prowler**, the other SHIP workshop tool, is `deploying-security-assessments`. It
  answers a different question — resource configuration versus SRA implementation.
- **Remediating** findings. This skill deploys the assessment and retrieves results. It does
  not change the resources or services the assessment flags.

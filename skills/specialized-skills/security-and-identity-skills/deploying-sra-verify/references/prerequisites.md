# SRA Verify Prerequisites

Complete every check here before the first deploy step. Each unmet item causes a failure
partway through the deployment, after infrastructure already exists.

## Account roles

SRA Verify spans three account roles. Establish which real account fills each one before
deploying anything.

| Role | What it does | Credentials needed |
|---|---|---|
| **Management account** | Owns the organization; hosts the StackSet and its own copy of `SRAMemberRole` | Yes — required, see below |
| **Audit account** | Runs CodeBuild, assumes `SRAMemberRole` everywhere, holds results | Yes |
| **Log-archive account** | Assessed; its ID is a required solution parameter | No — StackSet delivers the role |
| **Member accounts** | Assessed; receive `SRAMemberRole` via StackSet | No — StackSet delivers |

SRA Verify is designed to **run from the audit account** (the Security Tooling account where
GuardDuty or Security Hub administration is delegated). In the standard topology the
"run-from" account and the audit account are the same, so the member template's
`SRAVerifyAccountID` and the solution template's `AuditAccountID` are usually the same ID —
but they are different parameters answering different questions. `SRAVerifyAccountID` names
the account whose CodeBuild role is allowed to assume `SRAMemberRole`; the solution's
`AuditAccountID` names the account the **audit-type** checks run against.

## Management-account credentials are mandatory

Delegated-administrator credentials alone are **not sufficient**. Management-account
access is required at every one of these points:

1. Creating the service-managed StackSet for `SRAMemberRole`. Delegatable — if
   CloudFormation StackSets is delegated to another account, that account may create it
   instead.
2. Deploying `1-sraverify-member-roles.yaml` as a **plain stack to the management account**.
   StackSets do not apply to the management account, so it does not otherwise receive the
   role — and the 40 management-type checks all assume `SRAMemberRole` *in the management
   account*. Not delegatable.
3. **Activating trusted access** for StackSets (`activate-organizations-access`) when
   `describe-organizations-access` is not `ENABLED`. Organization-wide. Not delegatable.
4. **Registering a StackSets delegated administrator**, if the audit account is to run
   StackSet operations itself. Not delegatable.
5. Creating or editing the **Organizations delegation policy**, if the audit account cannot
   list accounts. Organizations settings are management-account-only. Not delegatable.
6. **Cleanup** — deleting the management-account stack, and reversing 3, 4 and 5 if they
   were done solely for this.

Confirm with the user that they can obtain management-account credentials before starting.
If they cannot, stop and say so: the deployment cannot complete, and partial deployment
leaves roles in member accounts with no scanner able to use them — plus every management-type
check (the organization CloudTrail, the delegated administrators, the SRA backbone) failing.

## Tooling configuration

This skill needs credentials for **two different accounts** in one session, so single-profile
setups fail partway through. Configure this before starting.

### AWS CLI profiles

Create one profile per account role and always pass `--profile` explicitly on deploy
commands. Do not rely on an ambient default — the cost of picking the wrong account here is
a stack in the wrong place.

```bash
aws sts get-caller-identity --profile <management_profile>
aws sts get-caller-identity --profile <audit_profile>
```

**If management credentials exist only as environment variables** (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) and there is no profile to name, the management
commands have to run with no `--profile` — which is exactly the ambient default this section
warns against. Two mitigations, both mandatory in that case:

- Run `aws sts get-caller-identity` immediately before **each** management-account write and
  confirm the account ID, not just once at the start. Temporary credentials expire mid-run.
- Check whether `AWS_PROFILE` is also set. Explicit keys take precedence over it only while
  they are present and unexpired; if they are cleared, every bare `aws` call silently falls
  through to whatever `AWS_PROFILE` names — observed in a sibling deployment pointing at an
  account in a **different organization**. That is the "stack in the wrong place" failure with
  no error to catch it.

Writing the env-var credentials into a named profile removes both hazards and is the better
fix when it is available.

### AWS MCP server, if in use

The `aws-core` plugin ships an `aws-mcp` server (`mcp-proxy-for-aws-cli`). Three settings
matter here:

- **Multi-profile switching.** Set `AWS_MCP_PROXY_PROFILES` to a **space-separated** list;
  the first entry is the default and the rest become switchable per call via the
  `aws_profile` parameter the proxy injects. Without this the proxy binds to a single
  profile and the management-account steps cannot run through MCP at all.

  ```json
  "aws-mcp": {
    "command": "uvx",
    "args": ["mcp-proxy-for-aws-cli@latest", "https://aws-mcp.us-east-1.api.aws/mcp"],
    "env": {
      "AWS_MCP_PROXY_PROFILES": "<audit_profile> <management_profile>"
    }
  }
  ```

  `AWS_MCP_PROXY_PROFILES` takes precedence over `--profile` and `AWS_PROFILE`.

- **`--read-only` blocks this skill.** If the proxy was started with `--read-only`, every
  write-annotated tool is disabled and no deploy step will succeed through MCP. Either
  remove the flag for this work or run the deploy steps through the AWS CLI instead.

- **Region must be set per profile.** A missing region surfaces as
  `-32602: Invalid request parameters`, not as a region error. Fix with
  `aws configure set region <region> --profile <profile>`.

If the MCP server is unavailable or read-only, the AWS CLI path in
`references/sraverify-deployment.md` works unchanged — every step is expressed as a CLI
command for that reason.

### What this skill does not need

No additional MCP server, hook, or plugin is required. The only hook `aws-core` ships
(`secret-safety.py`) blocks Secrets Manager `get-secret-value`, which this skill never calls.

## Identity check — run first

```bash
aws sts get-caller-identity --profile <profile>
aws organizations describe-organization --profile <profile>
```

Compare `Organization.MasterAccountId` to the caller's account. Echo back to the user:
account ID, caller ARN, region, and whether this is the management account. Ask them to
confirm before proceeding. Decide "management" from `MasterAccountId`, never from an account
or profile name — one management account observed in a sibling deployment was *named*
`Organization_Delegated_Administrator`.

`describe-organization` also confirms `FeatureSet: ALL`, which service-managed StackSets
require.

`FeatureSet: ALL` is necessary but not sufficient. Service-managed StackSets also need
trusted access activated. Check it before Step 1:

```bash
aws cloudformation describe-organizations-access --profile <management_profile> \
  --query Status --output text
```

**Treat anything other than `ENABLED` as not ready.** The API's values are `ENABLED`,
`DISABLED` and `DISABLED_PERMANENTLY`. `DISABLED_PERMANENTLY` cannot be reversed by the call
below; if you see it, stop and report it to the user rather than retrying.

If it is `DISABLED`, activate trusted access **from the management account** — not from a
delegated admin. This is an organization-wide write: obtain approval under rule 1 first, and
say plainly that it enables service-managed StackSets for every account in the organization,
not just this deployment.

```bash
aws cloudformation activate-organizations-access --profile <management_profile>
```

**That one call is all you need — do not also run the Organizations one.** The relationship
between the two APIs is one-directional, confirmed from a clean `DISABLED` state in a sibling
SATv2 deployment (the trusted-access mechanism is identical — the same
`member.org.stacksets.cloudformation.amazonaws.com` principal):

- `cloudformation activate-organizations-access` flips `describe-organizations-access` to
  `ENABLED` within about 15 seconds **and registers
  `member.org.stacksets.cloudformation.amazonaws.com` on the Organizations side by itself**.
- `organizations enable-aws-service-access --service-principal member.org.stacksets.cloudformation.amazonaws.com`
  registers that principal but does **not** flip `describe-organizations-access`.

Re-run the check and do not begin Step 1 until it returns `ENABLED`.

From a member account that is not a StackSets delegated administrator,
`describe-organizations-access` itself fails with `ValidationError: You must be the management
account or delegated admin account…`. The observable proxy from such an account is whether
`member.org.stacksets.cloudformation.amazonaws.com` appears in
`list-aws-service-access-for-organization`: present means activated, absent means almost
certainly not. The authoritative read still needs management or StackSets-delegated
credentials. Do **not** check for `stacksets.cloudformation.amazonaws.com` — that name does
not appear in working organizations and looking for it produces a false negative.

### Two different kinds of delegated administrator

`--call-as DELEGATED_ADMIN` requires delegation for **CloudFormation StackSets
specifically**. Being a delegated administrator for some other service does not qualify —
even though it does confer the Organizations read-only actions the scan itself needs (see
"Organizations permissions for the audit account" below). The README uses `--call-as` with
either `SELF` (deploying from the management account) or `DELEGATED_ADMIN` (deploying from the
StackSets delegated admin); the workshop deploys from the management account through the
console, which is `SELF`.

Check with the service principal **scoped**, from the management account:

```bash
aws organizations list-delegated-administrators --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

An **unscoped** `list-delegated-administrators` is the trap: it returns accounts registered
for any service, so an account delegated only for something else — Security Lake, say —
appears `ACTIVE` there while every `--call-as DELEGATED_ADMIN` call still fails.

If you register the audit account as a StackSets delegated administrator, **activate trusted
access first** — registering before `describe-organizations-access` reports `ENABLED` fails
with `ConstraintViolationException: You must enable service access before you delegate an
administrator for this service`. Registering is an organization-level write — approval under
rule 1 first:

```bash
aws organizations register-delegated-administrator --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com \
  --account-id <audit_account_id>
```

When both routes are open — the audit account is a StackSets delegated administrator *and*
management credentials are available — prefer the management account with `--call-as SELF`
(or no `--call-as`): the steps in `references/sraverify-deployment.md` are written for
`<management_profile>`, and it sidesteps every `--call-as` failure mode.

## Organizations permissions for the audit account

The CodeBuild buildspec calls `aws organizations list-accounts` **from the audit account** to
discover scan targets, and `describe-organization` to find the management account. Outside the
management account `list-accounts` normally fails, and the build exits early. The workshop
makes this its own step, and states that if you already did it for SATv2 you can skip it —
the permission is the same.

Test it before deploying, from the audit account:

```bash
aws organizations list-accounts --profile <audit_profile> \
  --query 'Accounts[?Status==`ACTIVE`].Id' --output text
```

If that succeeds, nothing further is needed **for account discovery** — skip the policy below.
Steps 1 and 2 still require management-account credentials regardless.

**If it fails, check delegated-administrator status before writing any policy.** That call
succeeds from the management account or from a member account registered as a delegated
administrator for **any** supported service — registration confers the full Organizations
read-only API set, which includes the three actions the policy below grants and much more.

```bash
aws organizations list-delegated-administrators --profile <management_profile> \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

If the audit account appears there as `ACTIVE`, the delegation policy is unnecessary; the
call is failing for another reason (check the CodeBuild role's own identity policy — it grants
`organizations:ListAccounts` and `DescribeOrganization` on `*`, so the failure is the org side,
not the role).

**Only if the audit account is not a delegated administrator**, add an Organizations
delegation policy (the "Delegated administrator for AWS Organizations" resource policy). This
is an organization-level write — approval under rule 1 first — and at the API it is
**replace, not append**: `put-resource-policy` overwrites the whole document, so a naive write
removes every other account's delegation. Read first:

```bash
aws organizations describe-resource-policy --profile <management_profile> \
  --query 'ResourcePolicy.Content' --output text
```

`ResourcePolicyNotFoundException` means none exists and the statement below can be the whole
policy. Otherwise take the returned document, **add** the statement below to its `Statement`
array, and write the merged document back with `put-resource-policy --content file://merged-policy.json`.
The statement to add — identical to the one SATv2 uses, which is why the workshop says the two
tools share this step:

```json
{
  "Sid": "SRAVerifyListAccounts",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<audit_account_id>:root" },
  "Action": [
    "organizations:ListAccounts",
    "organizations:DescribeAccount",
    "organizations:ListTagsForResource"
  ],
  "Resource": "*"
}
```

Run `describe-resource-policy` again and confirm every pre-existing statement is still present
before re-testing `list-accounts` from the audit account. The console route
(**Organizations → Settings → Delegated administrator for AWS Organizations → Edit**) shows
the same document and is a reasonable alternative when merging by hand.

Two cautions, carried from the SATv2 skill because the mechanism is identical:

- This read-and-merge path has **not** been exercised in a live run by this skill's authors —
  every test organization so far already had a delegated administrator that could list
  accounts. Treat the merge as documented, not demonstrated.
- The principal ARN is hardcoded to the `aws` partition. In China, substitute `aws-cn`.
  GovCloud has no Organizations resource policies (the SATv2 README routes GovCloud to
  registering a delegated administrator instead); verify current availability before advising.

## Region planning

- The member-role StackSet deploys to **one region**. Roles are global, so one region is
  correct — but note which one you used, because cleanup must target the same region. The
  workshop warns that selecting more than one region makes the StackSet fail on the global IAM
  role.
- The solution stack determines where CodeBuild runs and where results land (the audit
  account).
- **What gets scanned is `IncludeRegions`, not where the stack lives.** The default is only
  `us-east-1,us-east-2,us-west-2`. See the region trap in `SKILL.md` and the parameters section
  of `references/sraverify-deployment.md`.

## State to read before deploying

Assume the organization is already partially configured — SATv2 and SRA Verify are commonly
deployed into the same audit account, and both use service-managed StackSets. Capture current
state so you can report deltas rather than assuming greenfield:

```bash
# Existing SRA Verify footprint. Do NOT filter to CREATE_COMPLETE/UPDATE_COMPLETE — a stack in
# ROLLBACK_COMPLETE, UPDATE_ROLLBACK_COMPLETE or DELETE_FAILED still owns its named resources
# and will collide, but is invisible to that filter. This name filter catches the StackSet and
# role stacks named SRAVerify / sraverify / SRAMemberRole (including the README's
# `sraverify-member-roles`); a solution stack named `sra` (the README default) does not match by
# name and is caught instead by the fixed-name CodeBuild/role checks below.
aws cloudformation list-stacks --profile <profile> \
  --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE` && (contains(StackName,`SRAVerify`) || contains(StackName,`sraverify`) || contains(StackName,`SRAMemberRole`))].[StackName,StackStatus]' \
  --output text

aws cloudformation list-stack-sets --profile <profile> --status ACTIVE \
  --query 'Summaries[].[StackSetName,PermissionModel,Status]' --output text

# Does the member role already exist here?
aws iam get-role --profile <profile> --role-name SRAMemberRole >/dev/null 2>&1 \
  && echo "present" || echo "absent"

# Audit account only: the solution stack's fixed-name resources, whatever the stack was called
aws codebuild batch-get-projects --profile <audit_profile> \
  --names SRAVerify-Security-Assessment --query 'projects[].name' --output text
aws iam get-role --profile <audit_profile> --role-name SRAVerifyCodeBuildServiceRole >/dev/null 2>&1 \
  && echo "present" || echo "absent"

# Delegated administrators already registered
aws organizations list-delegated-administrators --profile <management_profile> \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

Test role existence by **exit code**, as above. Parsing CLI output for this is unreliable and
has produced false "clean install" verdicts in the sibling SATv2 work.

From a delegated administrator account, `list-stack-sets` returns an empty list rather than an
error unless you pass `--call-as DELEGATED_ADMIN` — another route to a false "clean install".
Add the flag whenever the caller is not the management account.

Run these in **both** the management account and the audit account. A SRA Verify solution
stack lives in the audit account, not the management account, so a management-only sweep
reports a false "clean install".

The stack names differ between the workshop and the README, but the **fixed resource names do
not** and collide regardless of stack name:

| Fixed name | Type | Where |
|---|---|---|
| `SRAMemberRole` | IAM role | Every member account + the management account |
| `SRAVerifyLeastPrivilege`, `SRAVerifyCheckPermissions` | IAM managed policies | Alongside the member role |
| `SRAVerifyCodeBuildServiceRole` | IAM role | Audit account |
| `SRAVerify-Security-Assessment` | CodeBuild project | Audit account |

The findings bucket has **no** fixed name — the template gives it no `BucketName`, so
CloudFormation generates `<stack-name>-bucketsraverifyfindings-<random>` and it never
collides. That is the one resource you cannot find by a fixed name; find it through the stack.

If a `SRAMemberRole`, a SRA Verify stack, or any of those fixed-name resources already exists,
report it and ask whether to reuse, update, or replace. Do not create a second copy.

### The member accounts you cannot pre-check

`SRAMemberRole` is a named IAM resource, so the StackSet **fails on any account that already
has one** — and a service-managed StackSet gives you no credentials in member accounts to
check first. Handle it as the SATv2 skill does:

1. Enumerate the targets so the blast radius is explicit:

   ```bash
   aws organizations list-accounts --profile <management_profile> \
     --query 'Accounts[?Status==`ACTIVE`].[Id,Name]' --output table
   ```

2. Pre-check only the accounts where you can actually assume a role — typically
   `OrganizationAccountAccessRole` or `AWSControlTowerExecution`:

   ```bash
   aws sts assume-role --profile <management_profile> \
     --role-arn arn:<partition>:iam::<account>:role/OrganizationAccountAccessRole \
     --role-session-name sraverify-precheck >/dev/null 2>&1 \
     && echo "assumable — check get-role SRAMemberRole here" || echo "not assumable — watch the rollout"
   ```

3. For the rest, deploy to **one OU first** and watch for the collision:

   ```bash
   aws cloudformation list-stack-instances --profile <management_profile> \
     --stack-set-name <stack_set_name> \
     --query 'Summaries[].{Account:Account,Status:Status,Detailed:StackInstanceStatus.DetailedStatus,Reason:StatusReason}'
   ```

   As seen with the equivalent SATv2 role, the operation detail does **not** name the
   collision from the management account — a pre-existing named role shows instance `Status`
   `OUTDATED` with `StackInstanceStatus.DetailedStatus` `FAILED` and a generic `Validation
   failed with 1 error(s)` reason, no `AlreadyExists` and no role name. The named-role detail
   (`NAME_CONFLICT_VALIDATION`, `Resource of type 'AWS::IAM::Role' with identifier
   'SRAMemberRole' already exists.`) exists only in the member account's short-lived instance
   stack, reachable by ARN where you hold member credentials. Without member credentials, the
   step-2 pre-check is the only way to know in advance.

   To converge: `delete-stack-instances --no-retain-stacks` clears the `OUTDATED` instance (a
   gated write). Then either keep the existing role and exclude that account with
   `AccountFilterType=DIFFERENCE`, or — if the account owner removes the pre-existing role —
   rerun `create-stack-instances`. This skill does not delete a role it did not create; the
   owner decides, after checking `get-role --query Role.RoleLastUsed` for recent use.

## Validate both templates before deploying

Both templates can be validated completely without provisioning anything. Do this before
Step 1 rather than discovering a template or parameter problem partway through. Do not
re-invent the procedure — the `aws-cloudformation` skill in this plugin already owns it:

- **Syntax and schema (cfn-lint)** — the `validate-cloudformation-template` SOP.
- **Security and compliance (cfn-guard)** — the `check-cloudformation-template-compliance`
  SOP. cfn-guard ships no rules and that SOP expects to ask the user which ruleset to use; for
  an unattended run, `wa-Security-Pillar.guard` from release 1.0.2 of
  `aws-cloudformation/aws-guard-rules-registry` is the default two independent cold runs
  converged on for the SATv2 templates. Its results against the unmodified upstream templates
  are **advisory, not a gate**: the templates carry their own `cfn_nag` suppressions (documented
  in the YAML — no bucket logging, SSE-S3 rather than KMS, `*` resources required for read-only
  checks), and `S3_BUCKET_SSL_REQUESTS_ONLY` is a rule false positive here because the TLS-only
  Deny lives in the sibling `bucketPolicySRAVerifyFindings` resource.
- **Pre-deployment validation** — the `cloudformation-pre-deploy-validation` SOP. Use its
  change-set path: `create-change-set --change-set-type CREATE` against a stack name that does
  not yet exist runs every validation check and provisions nothing.

Three things to know about these templates specifically:

- `validate-template --query Capabilities` returns **`CAPABILITY_NAMED_IAM`** for both (each
  creates a named IAM role). The README passes `CAPABILITY_IAM CAPABILITY_NAMED_IAM` on the
  solution stack because it also creates an unnamed Lambda execution role;
  `CAPABILITY_NAMED_IAM` alone is accepted and covers both.
- The solution template's change set lists a **`Custom::CodeBuildStartBuild`** resource. That
  is the resource that makes creating the stack start a scan, so showing it in the plan is the
  cheapest way to demonstrate to the user that the scan is real *before* they approve. Read the
  validation result with `describe-events` filtered to `EventType == VALIDATION_ERROR`; a clean
  change set still returns `STACK_EVENT` entries, so an empty *filtered* list — not an empty
  response — is the pass condition.
- **cfn-lint can fail an unmodified upstream template on a false positive.** Its bundled
  resource schemas lag the live CloudFormation registry, so a recently added property can
  surface as `E3002 Additional properties are not allowed` with a non-zero exit. Do not treat
  that exit as a gate failure on its own — the change-set path validates against the live
  registry and is authoritative. Record `cfn-lint --version` alongside any such finding.

Run the dry run against a **throwaway stack name** — `SRAVerify-preflight`, not `SRAVerify` —
so the `REVIEW_IN_PROGRESS` shell a `CREATE`-type change set leaves behind can never block the
real create. Creating the change set, deleting it, and removing the stack are all writes under
rule 1, but since none touches a resource, present them together for one confirmation per
template.

## Cost drivers to state before approval

The workshop bills this module at "less than a few dollars," often inside the free tier. State
that honestly. The drivers, smallest to largest concern:

- **CodeBuild minutes** — the dominant charge, and small. The project runs on
  `BUILD_GENERAL1_SMALL` (fixed — no compute-size parameter). Runtime scales with account
  count, region count (`IncludeRegions`) and `ParallelAccounts`. See the timeout trap in
  `references/troubleshooting.md`: the project sets no timeout, so it inherits CodeBuild's
  60-minute default and a large organization can hit it.
- **S3 storage** — findings are CSV only (one per scan run under `raw/`, plus the consolidated
  CSV and the static dashboard HTML under `consolidated/`). Far smaller than SATv2's output,
  which also writes OCSF and compliance JSON. The bucket is versioned and `DeletionPolicy:
  Retain`, so it survives stack deletion and keeps billing until deleted deliberately.
- **The data, not the dollar, is the real exposure.** Findings name account IDs and service
  configuration; the dashboard is loaded via a presigned URL; the "Copy generative AI prompt"
  button builds a prompt containing organization findings. See `references/reviewing-results.md`.

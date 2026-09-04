# SATv2 Prerequisites

Complete every check here before the first deploy step. Each unmet item causes a failure
partway through the deployment, after infrastructure already exists.

## Account roles

SATv2 spans three account roles. Establish which real account fills each one before
deploying anything.

| Role | What it does | Credentials needed |
|---|---|---|
| **Management account** | Owns the organization; hosts the StackSet and its own copy of the member role | Yes — required, see below |
| **Scanning account** | Runs CodeBuild and Prowler, holds results | Yes |
| **Member accounts** | Assessed; receive `ProwlerMemberRole` via StackSet | No — StackSet delivers |

The workshop uses the **audit account** as the scanning account. Any account can serve,
but it must be able to assume `ProwlerMemberRole` in every target account and to call
`organizations:ListAccounts`.

## Management-account credentials are mandatory

Delegated-administrator credentials alone are **not sufficient**. Management-account
access is required at every one of these points:

1. Creating the service-managed StackSet for `ProwlerMemberRole`. Delegatable — if
   CloudFormation StackSets is delegated to another account, that account may create it
   instead.
2. Deploying `1-sat2-member-roles.yaml` as a **plain stack to the management account**.
   StackSets do not apply to the management account, so it does not otherwise receive the
   role. Not delegatable.
3. **Activating trusted access** for StackSets (`activate-organizations-access`) when
   `describe-organizations-access` is not `ENABLED`. Organization-wide. Not delegatable.
4. **Registering a StackSets delegated administrator**, if the scanning account is to run
   StackSet operations itself. Not delegatable.
5. Creating or editing the **Organizations delegation policy**, if the scanning account
   cannot list accounts. Organizations settings are management-account-only. Not
   delegatable.
6. **Cleanup** — deleting the management-account stack, and reversing 3, 4 and 5 if they
   were done solely for this.

Confirm with the user that they can obtain management-account credentials before
starting. If they cannot, stop and say so: the deployment cannot complete, and partial
deployment leaves roles in member accounts with no scanner able to use them.

## Tooling configuration

This skill needs credentials for **two different accounts** in one session, so single-profile
setups fail partway through. Configure this before starting.

### AWS CLI profiles

Create one profile per account role and always pass `--profile` explicitly on deploy
commands. Do not rely on an ambient default — the cost of picking the wrong account here is
a stack in the wrong place.

```bash
aws sts get-caller-identity --profile <management_profile>
aws sts get-caller-identity --profile <scanning_profile>
```

**If management credentials exist only as environment variables** (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) and there is no profile to name, the management
commands have to run with no `--profile` — which is exactly the ambient default this section
warns against. Two mitigations, both mandatory in that case:

- Run `aws sts get-caller-identity` immediately before **each** management-account write and
  confirm the account ID, not just once at the start. Temporary credentials expire mid-run.
- Check whether `AWS_PROFILE` is also set. Explicit keys take precedence over it only while they
  are present and unexpired; if they are cleared, every bare `aws` call silently falls through
  to whatever `AWS_PROFILE` names — observed pointing at an account in a **different
  organization**. That is the "stack in the wrong place" failure with no error to catch it.

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
      "AWS_MCP_PROXY_PROFILES": "<scanning_profile> <management_profile>"
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
`references/satv2-deployment.md` works unchanged — every step is expressed as a CLI
command for that reason.

### What this skill does not need

No additional MCP server, hook, or plugin is required. The only hook `aws-core` ships
(`secret-safety.py`) blocks Secrets Manager `get-secret-value`, which this skill never
calls.

## Identity check — run first

```bash
aws sts get-caller-identity --profile <profile>
aws organizations describe-organization --profile <profile>
```

Compare `Organization.MasterAccountId` to the caller's account. Echo back to the user:
account ID, caller ARN, region, and whether this is the management account. Ask them to
confirm before proceeding.

`describe-organization` also confirms `FeatureSet: ALL`, which service-managed StackSets
require.

`FeatureSet: ALL` is necessary but not sufficient. Service-managed StackSets also need
trusted access activated. Check it before Step 1:

```bash
aws cloudformation describe-organizations-access --profile <management_profile> \
  --query Status --output text
```

**Treat anything other than `ENABLED` as not ready.** The API's values are `ENABLED`,
`DISABLED` and `DISABLED_PERMANENTLY`; the string `INACTIVE` does not appear. AWS has already
renamed this vocabulary once — "Activate/Deactivate Organizations Access" replaced
"Enable/Disable" — so compare against `ENABLED` rather than matching a particular negative
value. `DISABLED_PERMANENTLY` cannot be reversed by the call below; if you see it, stop and
report it to the user rather than retrying.

If it is `DISABLED`, activate trusted access **from the management account** — not from a
delegated admin. This is an organization-wide write: obtain approval under rule 1 first, and
say plainly that it enables service-managed StackSets for every account in the organization,
not just this deployment.

```bash
aws cloudformation activate-organizations-access --profile <management_profile>
```

**That one call is all you need — do not also run the Organizations one.** The relationship
between the two APIs is one-directional, confirmed from a clean `DISABLED` state with the
service principal absent:

- `cloudformation activate-organizations-access` flips `describe-organizations-access` to
  `ENABLED` within about 15 seconds **and registers
  `member.org.stacksets.cloudformation.amazonaws.com` on the Organizations side by itself**.
- `organizations enable-aws-service-access --service-principal member.org.stacksets.cloudformation.amazonaws.com`
  registers that principal but does **not** flip `describe-organizations-access` — observed
  still `DISABLED` after 60 seconds of polling.

This matches the Organizations user guide, which states the trusted access can only be enabled
through CloudFormation StackSets. Running the Organizations call first is harmless but
redundant, and its apparent success is misleading in two ways. The principal shows up in
`list-aws-service-access-for-organization` while StackSets is still unusable; and — observed
from a clean state — `register-delegated-administrator` then succeeds too, so the scoped list
shows the account `ACTIVE` while every `--call-as DELEGATED_ADMIN` call from it still fails
with `ValidationError`. A registered StackSets delegated administrator in an organization
where StackSets is still deactivated looks like progress and is not.

Re-run the check and do not begin Step 1 until it returns `ENABLED`.

If you do inspect the Organizations-side service list, the principal is
`member.org.stacksets.cloudformation.amazonaws.com`. Do **not** check for
`stacksets.cloudformation.amazonaws.com` — that name does not appear in working
organizations and looking for it produces a false negative.

### Two different kinds of delegated administrator

`--call-as DELEGATED_ADMIN` requires delegation for **CloudFormation StackSets
specifically**. Being a delegated administrator for some other service does not qualify —
even though it does confer the Organizations read-only actions the scan itself needs, as
described under "Organizations permissions for the scanning account" below. Conflating the
two yields `InvalidOperationException: Account used is not a delegated administrator` from
`describe-organizations-access`, and the same message as a `ValidationError` from
`list-stack-sets`.

Check with the service principal **scoped**, from the management account:

```bash
aws organizations list-delegated-administrators --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

An **unscoped** `list-delegated-administrators` is the trap: it returns accounts registered
for any service, so an account delegated only for something else — Security Lake, say —
appears `ACTIVE` there while every `--call-as DELEGATED_ADMIN` call still fails.

If the scanning account is absent from the scoped list and you want it to drive StackSet
operations, register it from the management account — but **activate trusted access first**,
per the block above. Registering before `describe-organizations-access` reports `ENABLED`
fails with:

```text
ConstraintViolationException: You must enable service access before you delegate an
administrator for this service. Call the AWS API EnableAWSServiceAccess first.
```

Do not let that message divert you to `organizations enable-aws-service-access`.
`cloudformation activate-organizations-access` satisfies the constraint — observed: the same
register call failed while the status was `DISABLED` and succeeded immediately after
activating. The Organizations call also satisfies it, which is the trap described under the
activation block above: registration succeeds while StackSets stays unusable.

Registering is itself an organization-level write — approval under rule 1 first.

```bash
aws organizations register-delegated-administrator --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com \
  --account-id <scanning_account_id>
```

Otherwise run every StackSet command from the management account with no `--call-as`. When
the caller *is* a registered StackSets delegated administrator, add `--call-as
DELEGATED_ADMIN` to `describe-organizations-access` and to every StackSet command.

Note that `describe-organization`'s `AvailablePolicyTypes` field is not a reliable
inventory of enabled policy types. Use `list-roots` instead:

```bash
aws organizations list-roots --profile <management_profile> --query 'Roots[].PolicyTypes'
```

## Organizations permissions for the scanning account

The CodeBuild buildspec calls `aws organizations list-accounts` **from the scanning
account** to discover scan targets. Outside the management account this call normally
fails, and the build exits with:

```text
ERROR: Failed to retrieve account list from AWS Organizations
```

Test it before deploying, from the scanning account:

```bash
aws organizations list-accounts --profile <scanning_profile> \
  --query 'Accounts[?Status==`ACTIVE`].Id' --output text
```

If that succeeds, nothing further is needed — skip the policy below.

**If it fails, check delegated-administrator status before writing any policy.** That call
succeeds from the management account or from a member account registered as a delegated
administrator, and registration for **any** supported service confers the full Organizations
read-only API set — which includes the three actions the policy below grants, and much more.
Registration is the broader grant, not the lighter one.

```bash
aws organizations list-delegated-administrators --profile <management_profile> \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

If the scanning account appears there as `ACTIVE`, the delegation policy is unnecessary;
the call is failing for another reason (check the CodeBuild role's own identity policy).
Prescribing an org-level resource policy in that case is an avoidable organization-wide
write.

**Only if the scanning account is not a delegated administrator**, add an Organizations
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
array, and write the merged document back:

```bash
aws organizations put-resource-policy --profile <management_profile> \
  --content file://merged-policy.json
```

The statement to add:

```json
{
  "Sid": "SATv2ListAccounts",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<scanning_account_id>:root" },
  "Action": [
    "organizations:ListAccounts",
    "organizations:DescribeAccount",
    "organizations:ListTagsForResource"
  ],
  "Resource": "*"
}
```

Run `describe-resource-policy` again and confirm every pre-existing statement is still present
before re-testing `list-accounts` from the scanning account. The console route
(**Organizations → Settings → Delegated administrator for AWS Organizations → Edit**) shows
the same document and is a reasonable alternative when merging by hand. This read-merge-write
path is taken from the upstream README and has **not** been exercised in a live run by this
skill's authors — every test organization so far already had a delegated administrator.

Two cautions:

- **GovCloud has no Organizations resource policies.** Per the upstream README the only routes
  there are an existing delegated-administrator registration or `MultiAccountListOverride`
  (see `references/troubleshooting.md`). That claim is the README's, not observed here —
  verify current availability before advising.
- The principal ARN is hardcoded to the `aws` partition. In China, substitute `aws-cn`.

## Region planning

- The member-role StackSet deploys to **one region**. Roles are global, so one region is
  correct — but note which one you used, because cleanup must target the same region.
- The scanning account's stack determines where CodeBuild runs and where results land.
- Prowler scans the regions its own configuration covers, independent of where the stack
  lives.

## State to read before deploying

Assume the organization is already partially configured. Capture current state so you can
report deltas rather than assuming greenfield:

```bash
# Existing SATv2 footprint. Do NOT filter to CREATE_COMPLETE/UPDATE_COMPLETE — a stack in
# ROLLBACK_COMPLETE, UPDATE_ROLLBACK_COMPLETE or DELETE_FAILED still owns its named
# resources and will collide, but is invisible to that filter.
aws cloudformation list-stacks --profile <profile> \
  --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE` && (contains(StackName,`SATv2`) || contains(StackName,`sat2`) || contains(StackName,`rowler`))].[StackName,StackStatus]' \
  --output text

aws cloudformation list-stack-sets --profile <profile> --status ACTIVE \
  --query 'Summaries[].[StackSetName,PermissionModel,Status]' --output text

# Does the member role already exist here?
aws iam get-role --profile <profile> --role-name ProwlerMemberRole >/dev/null 2>&1 \
  && echo "present" || echo "absent"

# Scanning account only: the solution stack's fixed-name resources, whatever the stack was called
aws codebuild batch-get-projects --profile <scanning_profile> \
  --names ProwlerCodeBuild ProwlerReportingCodeBuild --query 'projects[].name' --output text
aws iam get-role --profile <scanning_profile> --role-name ProwlerCodeBuildRole >/dev/null 2>&1 \
  && echo "present" || echo "absent"

# Delegated administrators already registered
aws organizations list-delegated-administrators --profile <management_profile> \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

Test role existence by **exit code**, as above. Parsing CLI output for this is unreliable and
has produced false "clean install" verdicts.

From a delegated administrator account, `list-stack-sets` returns an empty list rather than
an error unless you pass `--call-as DELEGATED_ADMIN` — another route to a false "clean
install". Add the flag whenever the caller is not the management account.

Run these in **both** the management account and the scanning account. Checking only one
account misses an existing deployment in the other — a SATv2 solution stack lives in the
scanning account, not the management account, so a management-only sweep reports a false
"clean install".

The name filter is case-sensitive and the upstream README deploys as `sat2`, so the filter
includes that spelling; the fixed-name checks catch a deployment under any other name, because
`ProwlerCodeBuild`, `ProwlerReportingCodeBuild` and `ProwlerCodeBuildRole` are hardcoded in
the template and collide regardless of stack name.

A stack named `SATv2-preflight` in `REVIEW_IN_PROGRESS` is a dry-run leftover from the
validation step below, not a deployment — see that section for removing it.

If a `ProwlerMemberRole`, a SATv2 stack, or any of those fixed-name resources already exists,
report it and ask whether to reuse, update, or replace. Do not create a second copy.

### The member accounts you cannot pre-check

`ProwlerMemberRole` is a named IAM resource, so the StackSet **fails on any account that
already has one** — and a service-managed StackSet gives you no credentials in member
accounts to check first (`AWSServiceRoleForCloudFormationStackSetsOrgMember` is not
operator-assumable). Handle it this way:

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
     --role-session-name satv2-precheck >/dev/null 2>&1 \
     && echo "assumable — check get-role here" || echo "not assumable — rely on step 3"
   ```

3. For the rest, deploy to **one OU first** and watch for the collision — but know what it
   actually looks like:

   ```bash
   aws cloudformation list-stack-instances --profile <management_profile> \
     --stack-set-name <stack_set_name> \
     --query 'Summaries[].{Account:Account,Status:Status,Detailed:StackInstanceStatus.DetailedStatus,Reason:StatusReason}'
   ```

   **The operation detail does not name the collision.** A pre-existing `ProwlerMemberRole`
   produces instance `Status` `OUTDATED` with `StackInstanceStatus.DetailedStatus` `FAILED` —
   two fields, which is why the query above projects both — and the generic reason
   `ResourceStatusReason:Validation failed with 1 error(s). Call DescribeEvents to retrieve
   the full list of issues…` — no `AlreadyExists`, no role name. Observed twice. From the
   management account it is indistinguishable from any other pre-deployment validation
   failure, and `describe-events --operation-id <stack-set-operation>` returns
   `Operation ID does not exist`.

   The detail exists only in the member account, and only briefly: CloudFormation creates the
   instance stack, fails validation, and deletes it, so `describe-events --stack-name <name>`
   says the stack does not exist. Where you *do* hold member credentials, query by **ARN**:

   ```bash
   ARN=$(aws cloudformation list-stacks --profile <member_profile> \
     --query "StackSummaries[?starts_with(StackName,'StackSet-<stack_set_name>-')].StackId" \
     --output text | head -1)
   aws cloudformation describe-events --profile <member_profile> --stack-name "$ARN" \
     --query 'OperationEvents[?EventType==`VALIDATION_ERROR`].[ValidationName,LogicalResourceId,ValidationStatusReason]' \
     --output text
   ```

   A collision reads `NAME_CONFLICT_VALIDATION` with reason `Resource of type
   'AWS::IAM::Role' with identifier 'ProwlerMemberRole' already exists.` Note the logical ID
   is `ProwlerIntegrationCodeBuildRole`, not `ProwlerMemberRole` — filtering events on the
   role name finds nothing. Without member credentials, the pre-check in step 2 is the only
   way to know in advance.

   To converge afterwards: `delete-stack-instances --no-retain-stacks` clears the `OUTDATED`
   instance; then either remove the pre-existing role and rerun `create-stack-instances`
   (observed `SUCCEEDED`/`CURRENT`), or keep the existing role and exclude that account with
   `AccountFilterType=DIFFERENCE`.

On `FailureToleranceCount` and concurrency, see Step 1 in `references/satv2-deployment.md` —
the rationale lives there once, not here.

## Validate both templates before deploying

Both templates can be validated completely without provisioning anything. Do this before
Step 1 rather than discovering a template or parameter problem partway through a deployment.
Do not re-invent the procedure — the `aws-cloudformation` skill in this plugin already owns
it:

- **Syntax and schema (cfn-lint)** — the `validate-cloudformation-template` SOP.
- **Security and compliance (cfn-guard)** — the `check-cloudformation-template-compliance` SOP.
- **Pre-deployment validation** — the `cloudformation-pre-deploy-validation` SOP. Use its
  change-set path: `create-change-set --change-set-type CREATE` against a stack name that does
  not yet exist runs every validation check and provisions nothing.

Three things to know about these templates specifically while you are there:

- `validate-template --query Capabilities` returns **`CAPABILITY_NAMED_IAM` only**, for both
  templates. Each creates a named IAM role; neither needs `CAPABILITY_AUTO_EXPAND`.
- The solution template's change set lists a **`Custom::CodeBuildStartBuild`** resource. That
  is the resource that makes creating the stack start a scan, so showing it in the plan is the
  cheapest way to demonstrate to the user that the cost is real *before* they approve.
- **cfn-lint can fail the unmodified upstream template on a false positive.** Its bundled
  resource schemas lag the live CloudFormation registry, so a property upstream added recently
  surfaces as `E3002 Additional properties are not allowed ('<Property>' was unexpected)` and a
  non-zero exit. Do not treat that exit as a gate failure on its own — adjudicate against the
  live registry first:

  ```bash
  aws cloudformation describe-type --profile <scanning_profile> \
    --type RESOURCE --type-name AWS::CodeBuild::Project --query Schema --output text \
    | grep -c '"<Property>"'
  ```

  A non-zero count means the registry knows the property and cfn-lint is behind; the change-set
  path below is the authoritative check because it validates against the registry. Record
  `cfn-lint --version` alongside any such finding, because the specific false positive rotates
  with the release: cfn-lint 1.46 rejected `HostKernel` on `AWS::CodeBuild::Project` twice
  (upstream added it in 2026-08/09) while the change set accepted it; cfn-lint 1.56 accepts
  `HostKernel` but instead warns `W1030` that `CodeBuildTimeout`'s maximum of 2160 exceeds a
  limit of 480 — also schema lag, since CodeBuild's ceiling has been 2160 minutes since
  2024-06. The gate is per property: dismiss an `E3002` only after `describe-type` confirms
  *that* property name, never because it resembles this example.

Run the dry run against a **throwaway stack name** — `SATv2-preflight`, not `SATv2` — so the
shell it leaves behind can never block the real create, even if cleanup is skipped or fails.
"Provisions nothing" is true of resources, not of the stack record: a `CREATE`-type change set
leaves a `REVIEW_IN_PROGRESS` stack with zero resources, and the footprint sweep above lists it
as an existing SATv2 stack on every later run. Removing it is a `delete-stack` and falls under
rule 1 — name it in any pre-authorization — so, with approval, delete the change set and then
the stack, as the SOP's cleanup guidance says.

## Cost drivers to state before approval

Give the user these drivers before they approve the scan, not afterward:

- **CodeBuild minutes** — the dominant cost. Scales with scan tier, account count, and
  `ConcurrentAccountScans` (which also selects a larger compute type: `Three` uses
  `BUILD_GENERAL1_SMALL`, `Six` uses `BUILD_GENERAL1_MEDIUM`).
- **S3 storage** — by default findings are written as CSV, OCSF JSON and HTML; ASFF only
  when `ProwlerOptions` selects it, and plain JSON never on Prowler 5 (see
  `references/reviewing-results.md`). Volume is dominated by formats the Glue table never
  reads: one `Full` run across four small accounts (24,588 findings) plus three lighter runs
  left a 3.0 GB bucket with 210 object versions, of which `ocsf-json/` and `compliance/`
  were 1.4 GB each and `csv/` — the only prefix Athena queries — was 49 MB. Size scales with
  finding count, and `compliance/` appears only at `Full`. The bucket is versioned and has
  `DeletionPolicy: Retain`, so it survives stack deletion and keeps billing until deleted
  deliberately.
- **Athena and Glue** — only when `Reporting` is `'true'` (the default). Athena bills per
  byte scanned.

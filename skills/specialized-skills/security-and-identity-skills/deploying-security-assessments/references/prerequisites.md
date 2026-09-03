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
access is required at four points:

1. Creating the service-managed StackSet for `ProwlerMemberRole`. Delegatable — if
   CloudFormation StackSets is delegated to another account, that account may create it
   instead.
2. Deploying `1-sat2-member-roles.yaml` as a **plain stack to the management account**.
   StackSets do not apply to the management account, so it does not otherwise receive the
   role. Not delegatable.
3. Creating or editing the **Organizations delegation policy**, if the scanning account
   cannot list accounts. Organizations settings are management-account-only. Not
   delegatable.
4. **Cleanup** — deleting the management-account stack.

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
trusted access enabled. Check it before Step 1:

```bash
aws cloudformation describe-organizations-access --profile <management_profile>
```

`Status: ENABLED` means you are ready. If it reports `INACTIVE`, enable trusted access
**from the management account** — not from a delegated admin:

```bash
aws organizations enable-aws-service-access --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com
```

The principal is `member.org.stacksets.cloudformation.amazonaws.com`. Do **not** check for
`stacksets.cloudformation.amazonaws.com` — that name does not appear in working
organizations and looking for it produces a false negative.

When running from a delegated administrator account, add `--call-as DELEGATED_ADMIN` to
`describe-organizations-access` and to every StackSet command.

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
administrator, and registration for **any** supported service confers the Organizations
read-only permissions (`ListAccounts`, `DescribeAccount`, `ListTagsForResource`) — the same
three actions the policy below grants.

```bash
aws organizations list-delegated-administrators --profile <management_profile> \
  --query 'DelegatedAdministrators[].[Id,Status]' --output text
```

If the scanning account appears there as `ACTIVE`, the delegation policy is unnecessary;
the call is failing for another reason (check the CodeBuild role's own identity policy).
Prescribing an org-level resource policy in that case is an avoidable organization-wide
write.

**Only if the scanning account is not a delegated administrator**, add an Organizations
delegation policy. In the management account: **Organizations → Settings → Delegated
administrator for AWS Organizations → Delegate** (or **Edit** an existing policy).

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Statement",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::<scanning_account_id>:root" },
      "Action": [
        "organizations:ListAccounts",
        "organizations:DescribeAccount",
        "organizations:ListTagsForResource"
      ],
      "Resource": "*"
    }
  ]
}
```

Two cautions:

- **If a delegation policy already exists, append to it — do not replace it.** Replacing
  it can remove another account's access.
- The ARN is hardcoded to the `aws` partition. In GovCloud or China, substitute
  `aws-us-gov` or `aws-cn`.

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
  --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE` && (contains(StackName,`SATv2`) || contains(StackName,`rowler`))].[StackName,StackStatus]' \
  --output text

aws cloudformation list-stack-sets --profile <profile> --status ACTIVE \
  --query 'Summaries[].[StackSetName,PermissionModel,Status]' --output text

# Does the member role already exist here?
aws iam get-role --profile <profile> --role-name ProwlerMemberRole >/dev/null 2>&1 \
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

If a `ProwlerMemberRole` or SATv2 stack already exists, report it and ask whether to
reuse, update, or replace. Do not create a second copy.

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

3. For the rest, deploy to **one OU first** and read the collision out of the operation
   detail rather than guessing:

   ```bash
   aws cloudformation list-stack-instances --profile <management_profile> \
     --stack-set-name <stack_set_name> \
     --query 'Summaries[].{Account:Account,Status:Status,Reason:StatusReason}'
   ```

   An `AlreadyExists` reason on `ProwlerMemberRole` means that account was already set up.

Keep `FailureToleranceCount=0`. Raising it to push past a collision hides which accounts
were skipped and leaves the org half-deployed.

## Cost drivers to state before approval

Give the user these drivers before they approve the scan, not afterward:

- **CodeBuild minutes** — the dominant cost. Scales with scan tier, account count, and
  `ConcurrentAccountScans` (which also selects a larger compute type: `Three` uses
  `BUILD_GENERAL1_SMALL`, `Six` uses `BUILD_GENERAL1_MEDIUM`).
- **S3 storage** — findings are written as CSV, JSON, OCSF JSON, ASFF JSON, and HTML.
  The findings bucket is versioned and has `DeletionPolicy: Retain`, so it survives stack
  deletion and keeps billing until deleted deliberately.
- **Athena and Glue** — only when `Reporting` is `'true'` (the default). Athena bills per
  byte scanned.

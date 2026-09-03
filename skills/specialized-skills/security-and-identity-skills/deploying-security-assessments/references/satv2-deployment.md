# SATv2 Deployment Procedure

Prerequisites in `references/prerequisites.md` MUST be complete first. Every step below
requires explicit user approval before execution.

## Templates

Fetch from the repository root rather than embedding copies, so parameters and the Prowler
pin stay current:

```bash
BASE=https://raw.githubusercontent.com/awslabs/aws-security-assessment-solution/main
curl -sSfL $BASE/1-sat2-member-roles.yaml     -o 1-sat2-member-roles.yaml
curl -sSfL $BASE/2-sat2-codebuild-prowler.yaml -o 2-sat2-codebuild-prowler.yaml
```

Validate before deploying:

```bash
aws cloudformation validate-template --template-body file://1-sat2-member-roles.yaml
```

## Parameters

`1-sat2-member-roles.yaml`:

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `ProwlerAccountID` | String | `'012345678910'` | The **scanning** account. Pattern `\d{12}`. The workshop text calls this `AuditAccountId` — that name is wrong. |

`2-sat2-codebuild-prowler.yaml`:

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `ProwlerScanType` | String | `'Intermediate'` | `Basic` / `Intermediate` / `Full` |
| `MultiAccountScan` | String | `'false'` | **Must be `'true'` to scan the organization** |
| `MultiAccountListOverride` | String | `''` | Explicit account list; bypasses `list-accounts` |
| `ConcurrentAccountScans` | String | `'Three'` | `Three` / `Six` / `Twelve` / `FortyEight`; also sets compute size |
| `CodeBuildTimeout` | Number | `300` | Minutes. The only bound on a `Full` scan. |
| `Reporting` | String | `'true'` | Creates Glue database, table, and Athena workgroup |
| `ProwlerRole` | String | `ProwlerMemberRole` | Must match the role the StackSet created |
| `ProwlerOptions` | String | `aws --ignore-exit-code-3` | Base Prowler flags; tier options are appended |
| `EmailAddress` | String | `''` | Optional notification target |

## Scan tiers

Defined in the template's `Mappings.ProwlerScanParameters` and appended to
`ProwlerOptions`:

| Tier | Prowler flags | Scope |
|---|---|---|
| `Basic` | `-c` plus 13 named checks | Root MFA, CloudTrail multi-region, GuardDuty enabled, four password-policy checks, SG ingress from internet, S3 public access, Config recorder, Lambda runtimes, key rotation, contact details |
| `Intermediate` (default) | `--severity critical high` | All critical and high severity checks |
| `Full` | `''` (empty) | Every Prowler check — no filter |

The resolved check lists ship in the repository as `checks/basic_checks.txt`,
`checks/intermediate_checks.txt`, and `checks/full_checks.txt`, with `checks/get-checks.sh`
to regenerate them. Read those files for exact check membership rather than reciting it —
they travel with the pinned Prowler version.

**Read the tier list from the template you fetched, not from this table.** Upstream adds
and removes tiers, so treat the template as authoritative:

```bash
aws cloudformation validate-template --template-body file://2-sat2-codebuild-prowler.yaml \
  --query 'Parameters[?ParameterKey==`ProwlerScanType`]'
grep -A6 '^  ProwlerScanType:' 2-sat2-codebuild-prowler.yaml
```

A caution for existing stacks: a stack deployed against an older template may hold a
`ProwlerScanType` value the current template no longer offers. When updating such a stack,
pass `ProwlerScanType` explicitly rather than reusing the previous value, so the update
cannot carry forward a tier that is no longer defined in `Mappings`.

`Full` has no upper bound other than `CodeBuildTimeout`. Before selecting it, multiply
expected per-account duration by account count divided by `ConcurrentAccountScans`, and
compare against the timeout. If it does not fit, raise `CodeBuildTimeout` or raise
concurrency, and say which you changed and why.

## Deployment sequence

### Step 1 — member roles to member accounts (management account)

Read first:

```bash
aws cloudformation list-stack-sets --status ACTIVE
```

Deploy `1-sat2-member-roles.yaml` as a **service-managed StackSet**:

- Permissions: **Service-managed**
- Deployment target: **Deploy to organization** (or specific OUs for a staged rollout)
- Regions: **one** region only
- `ProwlerAccountID`: the scanning account ID

Prefer a staged rollout: one OU first, verify, then widen to the organization.

Verify — do not proceed until operations report `SUCCEEDED`:

```bash
aws cloudformation list-stack-instances --stack-set-name <name> \
  --query 'Summaries[].{Account:Account,Status:Status,Detail:StatusReason}'
aws cloudformation list-stack-set-operations --stack-set-name <name> --max-items 1
```

Rollback: `delete-stack-instances --no-retain-stacks`, then `delete-stack-set`.

### Step 2 — member role to the management account (management account)

StackSets do not apply to the management account, so deploy the **same template** there as
a plain stack. Without this, organization-level checks against the management account
cannot run.

```bash
aws cloudformation create-stack \
  --stack-name SATv2-ProwlerMemberRole-Management \
  --template-body file://1-sat2-member-roles.yaml \
  --parameters ParameterKey=ProwlerAccountID,ParameterValue=<scanning_account_id> \
  --capabilities CAPABILITY_NAMED_IAM
```

Verify:

```bash
aws cloudformation describe-stacks --stack-name SATv2-ProwlerMemberRole-Management \
  --query 'Stacks[0].StackStatus'
aws iam get-role --role-name ProwlerMemberRole --query 'Role.Arn'
```

### Step 3 — Organizations access preflight (scanning account)

Run the check in `references/prerequisites.md`. Resolve it before Step 4 — the failure
otherwise surfaces mid-build, after the stack exists.

### Step 4 — the solution stack (scanning account)

**This step starts the scan.** Confirm with the user that they are approving the scan and
its cost, not only the stack. State the tier, the number of accounts, and the concurrency
before asking.

```bash
aws cloudformation create-stack \
  --stack-name SATv2 \
  --template-body file://2-sat2-codebuild-prowler.yaml \
  --parameters \
    ParameterKey=ProwlerScanType,ParameterValue=Intermediate \
    ParameterKey=MultiAccountScan,ParameterValue=true \
    ParameterKey=ConcurrentAccountScans,ParameterValue=Three \
    ParameterKey=CodeBuildTimeout,ParameterValue=300 \
  --capabilities CAPABILITY_NAMED_IAM
```

Both templates declare only `CAPABILITY_NAMED_IAM`. Confirm with
`validate-template --query Capabilities` rather than assuming, and pass no more than the
template requires.

Verify, then follow the build:

```bash
aws cloudformation describe-stacks --stack-name SATv2 --query 'Stacks[0].StackStatus'
aws codebuild list-builds-for-project --project-name <project> --sort-order DESCENDING
aws codebuild batch-get-builds --ids <build_id> \
  --query 'builds[0].{Status:buildStatus,Phase:currentPhase,Start:startTime}'
```

Expect minutes for a single account and hours for an organization-wide `Full` scan.

## Multi-account scanning

`MultiAccountScan` defaults to `'false'`. The buildspec branches on it explicitly: when it
is not `'true'` it logs `Running a single account scan.` and scans only the scanning
account.

Two ways to target accounts:

- `MultiAccountScan='true'` — discovers active accounts via
  `aws organizations list-accounts`, filtered to `Status==ACTIVE`. Requires the
  Organizations permissions from `references/prerequisites.md`.
- `MultiAccountListOverride` — an explicit account list. Use this to pilot against a small
  set, or when the delegation policy cannot be added.

Prefer `MultiAccountListOverride` with two or three accounts for a first run. Confirm the
results path works end to end before scanning the whole organization.

## Re-running after accounts are added

New accounts do not receive `ProwlerMemberRole` automatically unless the StackSet's
deployment target covers them. After adding accounts:

1. Confirm the StackSet reached the new accounts —
   `list-stack-instances` should show them. Service-managed StackSets with automatic
   deployment enabled cover new organization members; otherwise add instances explicitly.
2. Re-run the CodeBuild project. The stack does not need redeploying — only the scan
   re-runs.

## Cleanup

Delete in reverse order, and state plainly what is retained:

1. Scanning account — `delete-stack --stack-name SATv2`.
2. Management account — delete the plain member-role stack.
3. Management account — `delete-stack-instances --no-retain-stacks`, then
   `delete-stack-set`.
4. If the delegation policy was added solely for this, remove or trim it.

**The findings bucket is `DeletionPolicy: Retain` and is versioned.** It survives stack
deletion and continues to bill. Tell the user its name and that deleting it is a separate,
deliberate action. Do not delete it without explicit instruction.

Two consequences worth stating when you report the bucket:

- Because versioning is enabled, emptying it requires removing **every object version and
  delete marker**. `aws s3 rb --force` leaves non-current versions behind and the bucket
  keeps billing.
- The bucket also carries `UpdateReplacePolicy: Retain`, so an update that *replaces* the
  bucket strands the old one the same way a deletion does.

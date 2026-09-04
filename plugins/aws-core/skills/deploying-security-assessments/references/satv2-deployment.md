# SATv2 Deployment Procedure

Prerequisites in `references/prerequisites.md` MUST be complete first. Every step requires
explicit user approval before execution.

**Pass `--profile` on every command.** This procedure spans two accounts and adjacent steps
target different ones. Never rely on an ambient default. Throughout:

- `<management_profile>` — a profile for the management account
- `<scanning_profile>` — a profile for the account that will run CodeBuild
- `<scanning_account_id>` — that account's 12-digit ID
- `<stack_set_name>` — the StackSet name you choose in Step 1
- `<region>` — the single region for the member-role StackSet

If StackSets is delegated to the scanning account, append `--call-as DELEGATED_ADMIN` to
every StackSet command. Omitting it does not error — it silently returns empty results.

## Templates

Fetch from the repository root rather than embedding copies, so parameters and the Prowler
pin stay current:

```bash
BASE=https://raw.githubusercontent.com/awslabs/aws-security-assessment-solution/main
curl -sSfL $BASE/1-sat2-member-roles.yaml      -o 1-sat2-member-roles.yaml
curl -sSfL $BASE/2-sat2-codebuild-prowler.yaml -o 2-sat2-codebuild-prowler.yaml
aws cloudformation validate-template --profile <scanning_profile> \
  --template-body file://1-sat2-member-roles.yaml --query Capabilities
```

## Parameters

`1-sat2-member-roles.yaml`:

| Parameter | Default | Notes |
|---|---|---|
| `ProwlerAccountID` | `'012345678910'` | The **scanning** account. Pattern `\d{12}`. The workshop text called this `AuditAccountId` as of 2026-09 — that name is wrong. |

`2-sat2-codebuild-prowler.yaml`:

| Parameter | Default | Notes |
|---|---|---|
| `ProwlerScanType` | `'Intermediate'` | `Basic` / `Intermediate` / `Full` |
| `MultiAccountScan` | `'false'` | **Must be `'true'` to scan more than the scanning account.** Also toggles whether a local member role is created — see Step 1 |
| `MultiAccountListOverride` | `''` | **Space**-delimited account list. Only read when `MultiAccountScan='true'` |
| `ConcurrentAccountScans` | `'Three'` | `Three` / `Six` / `Twelve` / `FortyEight`; also sets compute size |
| `CodeBuildTimeout` | `300` | Minutes. Accepted range is **5** to **2160** |
| `Reporting` | `'true'` | Creates Glue database, table, Athena workgroup and the reporting chain |
| `ProwlerRole` | `ProwlerMemberRole` | **Leave at the default** — see `references/troubleshooting.md` |
| `ProwlerOptions` | `aws --ignore-exit-code-3` | Base Prowler flags; tier options are appended |
| `EmailAddress` | `''` | Optional notification target |

Both templates require `CAPABILITY_NAMED_IAM`, because each creates an IAM role with an
explicit `RoleName`.

## Scan tiers

Read the tier list from the template you fetched rather than trusting this table — upstream
adds and removes tiers:

```bash
grep -A8 '^  ProwlerScanType:' 2-sat2-codebuild-prowler.yaml
```

That surfaces `AllowedValues` and the current tiers. Note `validate-template` does **not**
return `AllowedValues` — its parameter shape carries only `ParameterKey`, `DefaultValue`,
`NoEcho` and `Description`, so use it for the description text, not the tier list.

| Tier | Prowler flags | Template's own description | Actual, at `prowler==5.11` |
|---|---|---|---|
| `Basic` | `-c` plus 13 named checks | 13 checks | **13** |
| `Intermediate` (default) | `--severity critical high` | 109+ critical and high checks | **171** |
| `Full` | `''` (empty) | 383+ checks — every check, no filter | **572** |

**The template's own parameter description is stale for the two filtered tiers**, and both
columns are kept above so the mismatch is visible rather than surprising. `109+` and `383+`
each understate the real count by roughly a third of it — put the other way, the real counts
are about 50% higher than the template claims. Size against the right-hand column: a live
`Full` run on the pinned version logged `572/572` checks, which matches `full_checks.txt`
exactly.

Choose the tier by the question being asked, not by the bill. What each one is for:

- **`Basic`** is a pipeline smoke test — 13 checks prove the roles, discovery, and reporting
  chain work. It is the right tier for a pilot or a first run in a new organization, and the
  wrong one for answering "are my resources configured to best practice": a clean `Basic`
  result says almost nothing about posture.
- **`Intermediate`**, the default, is the posture-assessment tier — every critical and high
  check.
- **`Full`** adds the medium and low checks and is the only tier observed to emit the
  `compliance/` framework CSVs.

On a small organization the cost difference between tiers is cents, because CodeBuild's fixed
overhead dominates. If the user has stated a tier or a cost ceiling, follow it; otherwise
recommend the tier that answers their question and name the cost, rather than defaulting to
the cheapest.

Resolved check lists ship as `checks/basic_checks.txt`, `checks/intermediate_checks.txt` and
`checks/full_checks.txt`, with `checks/get-checks.sh` to regenerate them. Read those for
exact membership — they travel with the pinned Prowler version. Each file also ends with its
own count, so read that rather than trusting any number written here:

```bash
grep -h 'There are .* available checks' checks/*_checks.txt
```

`Full` is bounded only by `CodeBuildTimeout`. Before selecting it, multiply expected
per-account duration by account count divided by `ConcurrentAccountScans` and compare
against the timeout.

One measured anchor for that formula: a `Full` scan on the pinned Prowler took roughly
**35 minutes per account** — but that was on very small accounts (937 to 15,466 findings
each), n=1. Treat it as a floor rather than an estimate. Accounts with more resources take
proportionally longer, so scale from your own account sizes instead of reusing the number.
For the lighter tiers on even smaller accounts (under 100 `Basic` findings each, n=2):
`Basic` ran 13 checks in about 1¼ minutes per account and `Intermediate` ran 171 in about
2½, with a 7-minute wall clock for two accounts including the CodeBuild install phase.

If an existing stack was deployed against an older template, it may hold a
`ProwlerScanType` value the current template no longer offers. Pass `ProwlerScanType`
explicitly on any update rather than reusing the previous value.

## Deployment sequence

### Step 1 — member roles to member accounts (management account)

Read first — is a member-role StackSet already present? From a delegated administrator add
`--call-as DELEGATED_ADMIN`, or this returns empty:

```bash
aws cloudformation list-stack-sets --profile <management_profile> --status ACTIVE \
  --query 'Summaries[].[StackSetName,PermissionModel,Status]' --output text
```

Choose the deployment target deliberately:

- **Org root** (`organizations list-roots`) when `MultiAccountScan='true'` with an empty
  `MultiAccountListOverride`. The buildspec then enumerates every ACTIVE account —
  including the scanning account, which gets **no** local role under that setting — so all
  of them need the StackSet's role.
- **A single OU** only when the scan is scoped by `MultiAccountListOverride` to accounts
  that OU covers. A staged one-OU rollout combined with an empty override will fail on
  every account the StackSet has not reached.

Either way, service-managed deployment **excludes the management account** — Step 2 covers
it separately.

```bash
aws cloudformation create-stack-set --profile <management_profile> \
  --stack-set-name <stack_set_name> \
  --template-body file://1-sat2-member-roles.yaml \
  --parameters ParameterKey=ProwlerAccountID,ParameterValue=<scanning_account_id> \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation create-stack-instances --profile <management_profile> \
  --stack-set-name <stack_set_name> \
  --deployment-targets OrganizationalUnitIds=<root_or_ou_id> \
  --regions <region> \
  --operation-preferences FailureToleranceCount=0,MaxConcurrentCount=1
```

Under the default strict concurrency mode `MaxConcurrentCount` cannot exceed
`FailureToleranceCount + 1`, so the preferences above deploy **one account at a time** — a
minute or two each — and Step 4 cannot start until the last one lands. For a large
organization use
`--operation-preferences ConcurrencyMode=SOFT_FAILURE_TOLERANCE,FailureToleranceCount=0,MaxConcurrentPercentage=25`
instead: the soft mode keeps stop-at-first-failure while deploying in parallel. State the
expected rollout time to the user either way. The strict settings were exercised live by this
skill's authors; the soft-mode alternative is taken from the CLI documentation and was not.

`--auto-deployment` and `--call-as DELEGATED_ADMIN` are valid only with
`--permission-model SERVICE_MANAGED`. Auto-deployment is what covers accounts added later.

Verify — do not proceed until the operation reports `SUCCEEDED`:

```bash
aws cloudformation list-stack-set-operations --profile <management_profile> \
  --stack-set-name <stack_set_name> \
  --query 'Summaries[0].[OperationId,Status]' --output text

aws cloudformation list-stack-instances --profile <management_profile> \
  --stack-set-name <stack_set_name> \
  --query 'Summaries[?Status!=`CURRENT`].[Account,Status,StatusReason]' --output text
```

An empty second result means every instance is current. A `StatusReason` reading
`Validation failed with 1 error(s). Call DescribeEvents…` is what a pre-existing
`ProwlerMemberRole` looks like — the message never names the role or says `AlreadyExists`,
and from the management account it cannot be told apart from other validation failures. See
"The member accounts you cannot pre-check" in `references/prerequisites.md` for how to
confirm it and how to converge.

Keep `FailureToleranceCount=0`, but for the right reason: it stops the operation at the first
failure so you can read `list-stack-instances` and converge deliberately. It is *not* what
makes skipped accounts visible — the `Status!=CURRENT` query above does that at any tolerance
— and a halted operation *is* a half-deployed organization until you converge it, which is
why the convergence steps in `references/prerequisites.md` exist.

Rollback: `delete-stack-instances --no-retain-stacks`, then `delete-stack-set`. Both are
approval-gated writes under rule 1.

### Step 2 — member role to the management account (management account)

StackSets do not reach the management account, so deploy the **same template** there as a
plain stack. Without this, the management account cannot be assessed.

Read first — does the management account already have the role or the stack?

```bash
aws iam get-role --profile <management_profile> --role-name ProwlerMemberRole >/dev/null 2>&1 \
  && echo "present" || echo "absent"
aws cloudformation describe-stacks --profile <management_profile> \
  --stack-name SATv2-ProwlerMemberRole-Management --query 'Stacks[0].StackStatus' --output text 2>&1
```

`present`, or any status other than a "does not exist" error, means this step was already
done: report it and reuse rather than creating a second copy.

```bash
aws cloudformation create-stack --profile <management_profile> \
  --stack-name SATv2-ProwlerMemberRole-Management \
  --template-body file://1-sat2-member-roles.yaml \
  --parameters ParameterKey=ProwlerAccountID,ParameterValue=<scanning_account_id> \
  --capabilities CAPABILITY_NAMED_IAM
```

Verify:

```bash
aws cloudformation describe-stacks --profile <management_profile> \
  --stack-name SATv2-ProwlerMemberRole-Management --query 'Stacks[0].StackStatus' --output text
aws iam get-role --profile <management_profile> --role-name ProwlerMemberRole \
  --query 'Role.Arn' --output text
```

### Step 3 — Organizations access preflight (scanning account)

Run the check in `references/prerequisites.md`. Resolve it before Step 4 — otherwise the
failure surfaces mid-build, after the stack exists.

### Step 4 — the solution stack (scanning account)

**Creating this stack starts the scan.** Confirm the user is approving the scan and its cost,
not only the infrastructure. State the tier, the account count and the concurrency first.

Read first — the solution stack, or its fixed-name resources under some other stack name:

```bash
aws cloudformation describe-stacks --profile <scanning_profile> --stack-name SATv2 \
  --query 'Stacks[0].StackStatus' --output text 2>&1
aws codebuild batch-get-projects --profile <scanning_profile> \
  --names ProwlerCodeBuild ProwlerReportingCodeBuild --query 'projects[].name' --output text
```

Anything but a "does not exist" error and an empty project list means SATv2 is already
deployed here under some name — see the footprint sweep in `references/prerequisites.md`.

```bash
aws cloudformation create-stack --profile <scanning_profile> \
  --stack-name SATv2 \
  --template-body file://2-sat2-codebuild-prowler.yaml \
  --parameters \
    ParameterKey=ProwlerScanType,ParameterValue=Intermediate \
    ParameterKey=MultiAccountScan,ParameterValue=true \
    ParameterKey=ConcurrentAccountScans,ParameterValue=Three \
    ParameterKey=CodeBuildTimeout,ParameterValue=300 \
    ParameterKey=Reporting,ParameterValue=true \
  --capabilities CAPABILITY_NAMED_IAM
```

Follow the build:

```bash
aws cloudformation describe-stacks --profile <scanning_profile> --stack-name SATv2 \
  --query 'Stacks[0].StackStatus' --output text

BUILD_ID=$(aws codebuild list-builds-for-project --profile <scanning_profile> \
  --project-name ProwlerCodeBuild --sort-order DESCENDING --query 'ids[0]' --output text)

aws codebuild batch-get-builds --profile <scanning_profile> --ids "$BUILD_ID" \
  --query 'builds[0].[buildStatus,currentPhase]' --output text
```

Runtime is tier-dependent, so read this against the tier you chose. Expect minutes for a few
accounts at `Basic` or `Intermediate`. At `Full`, four small accounts measured 52 minutes wall
clock with `ConcurrentAccountScans=Six` (a single wave), and an organization-wide `Full` scan
runs to hours.

Confirm which accounts were actually reached — see `references/troubleshooting.md`. The
build status alone does not tell you: per-account failures are recorded inside a
backgrounded subshell and never reach the build's exit path.

## Multi-account scanning

`MultiAccountScan` defaults to `'false'`, in which case the buildspec logs
`Running a single account scan.` and scans only the scanning account.

`MultiAccountListOverride` is read **only** when `MultiAccountScan='true'`. It is not an
alternative to that setting — on its own it is inert. The list is **space**-delimited:

```bash
--parameters ParameterKey=MultiAccountScan,ParameterValue=true \
             ParameterKey=MultiAccountListOverride,ParameterValue="111111111111 222222222222"
```

Use the override to pilot against two or three accounts before scanning the organization,
or when the scanning account cannot enumerate the organization. With it empty, discovery
uses `organizations list-accounts` filtered to `Status==ACTIVE`.

**Clear it once the pilot passes.** An override left in place silently caps every later scan at
the accounts it names, and nothing in the build status or the output says so — see
`references/troubleshooting.md`. Clearing it takes a stack update **and** a fresh
`start-build`, because the update alone starts no scan.

## Re-running after accounts are added

Updating the stack does **not** start a scan — see `SKILL.md` global rule 3. After adding
accounts:

1. Confirm the StackSet reached them with `list-stack-instances`. Service-managed StackSets
   with auto-deployment enabled cover new organization members automatically.
2. Trigger the scan yourself:

   ```bash
   aws codebuild start-build --profile <scanning_profile> --project-name ProwlerCodeBuild
   ```

Treat that as its own approval point — it costs the same as a scan started by a create.

Note that findings accumulate; see `references/reviewing-results.md` before reporting
numbers from more than one run.

## Cleanup

Delete in reverse order, and state plainly what is retained. Every command here is a write
under rule 1 — the four below and the two organization-level ones further down — so obtain
approval for each before running it:

```bash
aws cloudformation delete-stack --profile <scanning_profile> --stack-name SATv2
aws cloudformation delete-stack --profile <management_profile> \
  --stack-name SATv2-ProwlerMemberRole-Management
aws cloudformation delete-stack-instances --profile <management_profile> \
  --stack-set-name <stack_set_name> --deployment-targets OrganizationalUnitIds=<root_or_ou_id> \
  --regions <region> --no-retain-stacks
aws cloudformation delete-stack-set --profile <management_profile> \
  --stack-set-name <stack_set_name>
```

If a delegation policy was added solely for this, remove or trim it.

If **trusted access** was activated solely for this, it can be reversed — but only
deliberately. It is an organization-wide setting, unrelated service-managed StackSets depend
on it, and it may well have predated SATv2. Leave it alone unless you activated it. When you
do reverse it — with approval, since both calls are organization-wide — deregister any
StackSets delegated administrators first or the call fails:

```bash
aws organizations deregister-delegated-administrator --profile <management_profile> \
  --service-principal member.org.stacksets.cloudformation.amazonaws.com \
  --account-id <scanning_account_id>
aws cloudformation deactivate-organizations-access --profile <management_profile>
```

Out of order, the second call returns
`InvalidOperationException: You have delegated administrator/s for this service. De-register
them in order to disable service access.` Deactivation also removes
`member.org.stacksets.cloudformation.amazonaws.com` from
`list-aws-service-access-for-organization`, mirroring what activation added.

**The findings bucket is `DeletionPolicy: Retain` and is versioned.** It survives stack
deletion and continues to bill. Tell the user its name and that deleting it is a separate,
deliberate action. Do not delete it without explicit instruction.

Two consequences worth stating when you report the bucket:

- Because versioning is enabled, emptying it requires removing **every object version and
  delete marker**. `aws s3 rb --force` leaves non-current versions behind and the bucket
  keeps billing.
- The bucket also carries `UpdateReplacePolicy: Retain`, so an update that *replaces* the
  bucket strands the old one the same way a deletion does.

# Deploying SRA Verify

Read `references/prerequisites.md` first and complete every check there. This file is the
deployment procedure itself. Every AWS write is gated by rule 1 in `SKILL.md`: show the exact
command, state what it changes, and wait for approval. **Creating the solution stack (Step 4)
starts a billable scan** — say so before you create it.

## Fetch the templates

Both templates live at the repository root and are fetched by URL. Pin nothing here — the
tool itself is unpinned (see below), and these are the current files:

```bash
BASE=https://raw.githubusercontent.com/awslabs/sra-verify/refs/heads/main
curl -fsSL -O $BASE/1-sraverify-member-roles.yaml
curl -fsSL -O $BASE/2-sraverify-codebuild-deploy.yaml
```

Validate both before deploying — see "Validate both templates before deploying" in
`references/prerequisites.md`. Do that once, up front, so a template or parameter problem
surfaces before any infrastructure exists.

## Parameters

### `1-sraverify-member-roles.yaml`

| Parameter | Default | Meaning |
|---|---|---|
| `SRAVerifyAccountID` | `'012345678910'` (placeholder) | The account SRA Verify **runs from** — the one whose `SRAVerifyCodeBuildServiceRole` is allowed to assume `SRAMemberRole` everywhere. In the standard topology this is the audit account. Pattern `\d{12}`; the placeholder default is not a real account and must be replaced. |

That is the **only** parameter on the member template. The workshop prose calls it
`AuditAccountId` — that name does not exist in the template. Use `SRAVerifyAccountID` (see trap
1 in `SKILL.md`).

### `2-sraverify-codebuild-deploy.yaml`

| Parameter | Default | Meaning |
|---|---|---|
| `AuditAccountID` | **none — required** | Comma-separated list of audit-account IDs. Drives the 40 audit-type checks and is passed to every scan as `--audit-account`. |
| `LogArchiveAccountID` | **none — required** | Comma-separated list of log-archive-account IDs. Drives the 15 log-archive-type checks and is passed as `--log-archive-account`. |
| `IncludeRegions` | `us-east-1,us-east-2,us-west-2` | Comma-separated regions every regional check runs in. **This is the scan's entire regional scope** — see coverage below. |
| `ParallelAccounts` | `5` | How many application-type scans run at once (`parallel -j`). Range 1–20. A real concurrency control — see below. |
| `GitBranch` | `main` | Branch the buildspec clones the tool from at build time. Unpinned — see below. |

`AuditAccountID` and `LogArchiveAccountID` have **no defaults**; `aws cloudformation deploy`
fails immediately if either is missing. Both accept comma-separated lists for organizations
with more than one audit or log-archive account.

## How the scan actually runs — account types

The buildspec does not scan "the organization" as one pass. It runs the `sraverify` CLI
several times with different `--account-type` values, each against a `SRAMemberRole` it
assumes in the target account. Understanding this explains which checks need which role and
why some accounts are scanned twice.

In order, the build:

1. `aws organizations list-accounts` → every **ACTIVE** account ID (`account_list`).
2. `aws organizations describe-organization` → the management account ID.
3. **management** — one run: `sraverify --role …:<management_account>:role/SRAMemberRole
   --account-type management`. The 40 management-type checks (organization CloudTrail,
   delegated administrators, the SRA backbone).
4. **audit** — a loop over each ID in `AuditAccountID`: `--account-type audit` against that
   account's `SRAMemberRole`. 40 audit-type checks per audit account.
5. **log-archive** — a loop over each ID in `LogArchiveAccountID`: `--account-type
   log-archive`. 15 log-archive-type checks per log-archive account.
6. **application** — every ACTIVE account, run **in parallel**:
   `echo $account_list | tr ' ' '\n' | parallel -j ${PARALLEL_ACCOUNTS:-5} scan_account …`,
   where `scan_account` runs `--account-type application` against that account's
   `SRAMemberRole`. 63 application-type checks per account.

Consequences to raise with the user:

- **The management, audit, and log-archive accounts are each scanned twice** — once for their
  role-specific checks (steps 3–5) and again as ordinary members in the application pass (step
  6). That is expected, not a duplication bug.
- **Every account needs `SRAMemberRole`, including the management account.** Step 3 assumes it
  in the management account; the StackSet never reaches there, which is why Step 2 (the plain
  stack) exists. Without it the management pass fails — see the "management checks absent"
  signal in `references/troubleshooting.md`.
- **`ParallelAccounts` throttles only the application pass** (step 6). Steps 3–5 run serially
  regardless. It is a genuine GNU-`parallel` job count — unlike the sibling SATv2 solution,
  whose brace-group throttle miscounts and serialises; SRA Verify has no such bug. Raising it
  shortens step 6 in proportion, bounded by the CodeBuild container's CPU.

## Regions and coverage

`IncludeRegions` is passed as `--regions` to every `sraverify` run and is the **complete**
regional scope of the scan. A service enabled only in a region outside the list is reported as
absent, and regional checks simply do not run there. The default covers just three regions
(`us-east-1,us-east-2,us-west-2`). Confirm the list against where the organization actually
operates before Step 4; the workshop itself recommends adding `us-west-1`. See trap 3 in
`SKILL.md`.

Global and organization-level checks (the management-type set) are not region-scoped and run
regardless, but any regional evidence they read is still bounded by `IncludeRegions`.

## The tool is unpinned

The buildspec clones the tool at build time and installs it:

```
git clone -b $GIT_BRANCH https://github.com/awslabs/sra-verify.git
pip install ./sra-verify/sraverify
```

with `GitBranch` defaulting to `main`. The check set, the account-type logic, and the
member-role permissions all come from that branch's `HEAD` on the day the build runs. Record
the branch and the build's start time. The buildspec clones by branch and runs no `git
rev-parse`, so the build log does not contain the cloned commit — resolve what `main` pointed
to at build time out of band (`git ls-remote https://github.com/awslabs/sra-verify.git main`,
or the repo's history at that timestamp) and record that, so a result is reproducible (rule 6
in `SKILL.md`). As of 2026-09-04, `main` was at commit `ad40888242b1` (a 2026-05-13 commit); a
live build today clones whatever `main` points to then, which may differ — resolve and record
the run's own commit, do not trust this one.

The build also needs to reach `github.com`. The dashboard HTML is taken from the same clone
(`aws s3 cp $CODEBUILD_SRC_DIR/sra-verify/sra-verify-dashboard.html …`), so it tracks the same
branch. `pandas` and `boto3` are `pip`-installed at build time, and the buildspec relies on
GNU `parallel` and `git` being present in the standard Amazon Linux 2 CodeBuild image
(`aws/codebuild/amazonlinux2-x86_64-standard:5.0`).

## Step 1 — Member roles to the member accounts (management account)

Deploys `1-sraverify-member-roles.yaml` as a **service-managed StackSet** to the organization,
creating `SRAMemberRole` and its two managed policies in every targeted member account. Run
from the management account (`--call-as SELF`, or omit `--call-as`) unless StackSets is
delegated to the audit account — see the delegated-administrator guidance in
`references/prerequisites.md`, which recommends preferring the management account when both
routes are open.

**Read before write.** Run the footprint sweep from `references/prerequisites.md` ("State to
read before deploying") and the pre-check for member accounts that may already own the role
("The member accounts you cannot pre-check"). Report what exists before proposing the create.

```bash
# Create the stack set (one region — roles are global)
aws cloudformation create-stack-set --profile <management_profile> \
  --template-body file://1-sraverify-member-roles.yaml \
  --stack-set-name <stack_set_name> \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=SRAVerifyAccountID,ParameterValue=<audit_account_id> \
  --region <region> --call-as SELF

# Roll out to accounts — target the root OU or specific OUs
aws cloudformation create-stack-instances --profile <management_profile> \
  --stack-set-name <stack_set_name> \
  --deployment-targets OrganizationalUnitIds='["<ou-or-root-id>"]' \
  --regions '["<region>"]' \
  --operation-preferences FailureTolerancePercentage=100,MaxConcurrentPercentage=100 \
  --region <region> --call-as SELF
```

`--auto-deployment Enabled=true` means accounts added to the targeted OUs later receive the
role automatically. The README's `stack-set-name` is `sraverify-member-roles`; the workshop
uses `SRAMemberRole`. Either works — the resource names inside are fixed regardless (see the
collision table in `references/prerequisites.md`), so pick one and record it.

**Deploy to one OU first** if you could not pre-check every account for a pre-existing
`SRAMemberRole`. `--operation-preferences FailureTolerancePercentage=100` lets the operation
finish and report every failure rather than stopping at the first, so one colliding account
does not hide the rest.

**Verify.**

```bash
aws cloudformation describe-stack-set-operation --profile <management_profile> \
  --stack-set-name <stack_set_name> --call-as SELF \
  --operation-id <op-id> --query 'StackSetOperation.Status' --output text

aws cloudformation list-stack-instances --profile <management_profile> \
  --stack-set-name <stack_set_name> --call-as SELF \
  --query 'Summaries[].{Account:Account,Status:Status,Detail:StackInstanceStatus.DetailedStatus}'
```

Expect every instance `CURRENT` / `SUCCEEDED`. An `OUTDATED` + `FAILED` instance with a generic
`Validation failed` reason is the named-role collision — handle it as
`references/prerequisites.md` describes. Do not proceed to Step 4 until the target OUs are
`CURRENT`, or the accounts still deploying will produce assume-role failures in the scan.

## Step 2 — Member role to the management account (plain stack)

StackSets do not deploy to the management account, and 40 management-type checks assume
`SRAMemberRole` **there**. Deploy the same template as a normal stack in the management
account. This step is not optional — skipping it is the most common incomplete deployment
(trap 4 in `SKILL.md`).

**Read before write.**

```bash
aws iam get-role --profile <management_profile> --role-name SRAMemberRole >/dev/null 2>&1 \
  && echo "present — do not create a second copy" || echo "absent — deploy"
```

```bash
aws cloudformation deploy --profile <management_profile> \
  --template-file 1-sraverify-member-roles.yaml \
  --stack-name <mgmt_stack_name> \
  --parameter-overrides SRAVerifyAccountID=<audit_account_id> \
  --capabilities CAPABILITY_NAMED_IAM
```

**Verify** the role exists and trusts the audit account's CodeBuild role — the trust condition
requires the principal to be `SRAVerifyCodeBuildServiceRole` in `SRAVerifyAccountID`:

```bash
aws iam get-role --profile <management_profile> --role-name SRAMemberRole \
  --query 'Role.AssumeRolePolicyDocument' --output json
```

## Step 3 — Confirm the audit account can enumerate accounts

The scan's first act is `aws organizations list-accounts` **from the audit account**. If that
fails, the build exits before scanning anything. Confirm it now — this is a gate, and the fix
(if any) is a management-account write covered in `references/prerequisites.md` under
"Organizations permissions for the audit account".

```bash
aws organizations list-accounts --profile <audit_profile> \
  --query 'length(Accounts[?Status==`ACTIVE`])' --output text
```

A number is a pass. An `AccessDeniedException` means the audit account is neither the management
account nor a delegated administrator for any service, and needs the delegation policy from the
prerequisites file before Step 4 will produce results.

## Step 4 — The solution stack (audit account) — this starts the scan

Deploys `2-sraverify-codebuild-deploy.yaml` in the audit account: the findings bucket, the
`SRAVerifyCodeBuildServiceRole`, the `SRAVerify-Security-Assessment` CodeBuild project, and a
`Custom::CodeBuildStartBuild` resource whose Lambda **starts a build on stack create**.
Approval for this stack is approval for the scan — say so explicitly (rule 3 in `SKILL.md`).

**Read before write.**

```bash
aws codebuild batch-get-projects --profile <audit_profile> \
  --names SRAVerify-Security-Assessment --query 'projects[].name' --output text
aws iam get-role --profile <audit_profile> --role-name SRAVerifyCodeBuildServiceRole \
  >/dev/null 2>&1 && echo "role present" || echo "role absent"
```

```bash
aws cloudformation deploy --profile <audit_profile> \
  --template-file 2-sraverify-codebuild-deploy.yaml \
  --stack-name <solution_stack_name> \
  --parameter-overrides \
    AuditAccountID=<audit_account_id_list> \
    LogArchiveAccountID=<log_archive_account_id_list> \
    IncludeRegions=<region_list> \
    ParallelAccounts=<n> \
    GitBranch=main \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```

`--capabilities` needs both `CAPABILITY_IAM` (the unnamed Lambda execution role) and
`CAPABILITY_NAMED_IAM` (the named `SRAVerifyCodeBuildServiceRole`).

**Verify** the build started, then follow it to completion:

```bash
# The most recent build for the project
aws codebuild list-builds-for-project --profile <audit_profile> \
  --project-name SRAVerify-Security-Assessment --query 'ids[0]' --output text

# Its status
aws codebuild batch-get-builds --profile <audit_profile> --ids <build-id> \
  --query 'builds[].{Phase:currentPhase,Status:buildStatus}' --output table
```

The project sets **no build timeout**, so it inherits CodeBuild's 60-minute default and there
is no parameter to raise it. For a large organization this can truncate the scan — see the
timeout entry in `references/troubleshooting.md`. Watch `buildStatus`; `FAILED` or
`TIMED_OUT` with results missing points there.

When `buildStatus` is `SUCCEEDED`, go to `references/reviewing-results.md`.

## Multi-account audit or log-archive

If the organization has more than one audit or log-archive account, pass each as a
comma-separated list in `AuditAccountID` / `LogArchiveAccountID`. The buildspec loops over each
and runs the role-type checks against every one. No other change is needed.

## Re-running the scan

**An update never starts a scan.** The custom resource's Lambda acts only on `RequestType ==
'Create'`; on update it no-ops. So after the first deploy, re-scanning is always a manual
build (rule 3):

```bash
aws codebuild start-build --profile <audit_profile> \
  --project-name SRAVerify-Security-Assessment
```

This is its own approval point and its own billable run. Results **accumulate** — each run
writes new timestamped files alongside the old ones (see `references/reviewing-results.md`).
There is no scope-down or single-account parameter (trap 2 in `SKILL.md`); every run scans
every ACTIVE account. To narrow one run, the only levers are the CLI's own flags in a **local**
run (see `references/troubleshooting.md`, "Debug a single check locally").

## Updating parameters

To change `IncludeRegions`, `ParallelAccounts`, or `GitBranch`, re-run the Step 4
`deploy` with the new values. Two cautions:

- **`deploy` with nothing changed prints `No changes to deploy` and exits** — it neither
  updates nor scans. That is expected.
- **An update updates the project but starts no scan.** After the stack update completes, run
  `start-build` (above) to scan with the new configuration.

`aws cloudformation deploy` keeps the previous value for any parameter you omit from
`--parameter-overrides`, so a partial override does not reset anything — unlike the sibling
SATv2 solution's raw `update-stack --parameters`, where an omitted parameter reverts to the
template default. Still, pass the full set explicitly so the deployed configuration is
unambiguous and auditable.

## Cleanup

Remove in the reverse of the deploy order. Every delete is a gated write (rule 1); the findings
bucket is a special case called out below.

1. **Solution stack (audit account).**

   ```bash
   aws cloudformation delete-stack --profile <audit_profile> --stack-name <solution_stack_name>
   ```

   This removes the CodeBuild project, its role, and the custom-resource Lambda. It does **not**
   remove the findings bucket: the bucket carries `DeletionPolicy: Retain` and
   `UpdateReplacePolicy: Retain`, so it survives and keeps billing. The stack delete leaves it
   orphaned but intact.

2. **The findings bucket — only if the user explicitly asks, and never on a pre-authorization.**
   Emptying and deleting it destroys the user's assessment data, so it needs its own approval
   each time (rule 1's carve-out). Confirm the bucket name first, show the user what it holds,
   and only then, with explicit approval:

   ```bash
   # Identify it (the name is generated, not fixed)
   aws cloudformation describe-stack-resources --profile <audit_profile> \
     --stack-name <solution_stack_name> \
     --query "StackResources[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId" --output text
   # (If the stack is already deleted, find it by prefix: <stack-name-lowercased>-bucketsraverifyfindings-*)
   ```

   Because the bucket is **versioned**, a plain delete fails while versions remain; all object
   versions must be removed first. Do this only on the user's explicit instruction.

3. **Management-account role stack (management account).**

   ```bash
   aws cloudformation delete-stack --profile <management_profile> --stack-name <mgmt_stack_name>
   ```

4. **Member-role StackSet (management account).** Delete the instances first, then the set:

   ```bash
   aws cloudformation delete-stack-instances --profile <management_profile> \
     --stack-set-name <stack_set_name> \
     --deployment-targets OrganizationalUnitIds='["<ou-or-root-id>"]' \
     --regions '["<region>"]' --no-retain-stacks \
     --operation-preferences FailureTolerancePercentage=100,MaxConcurrentPercentage=100 \
     --region <region> --call-as SELF

   aws cloudformation delete-stack-set --profile <management_profile> \
     --stack-set-name <stack_set_name> --call-as SELF --region <region>
   ```

   Use the **same region** you deployed the StackSet in. `--no-retain-stacks` removes the role
   from the member accounts; omitting it would leave the roles behind.

5. **Organization-level settings — only if they were added solely for this deployment, and each
   is a gated management-account write.** Do not reverse a setting the organization was already
   relying on. In reverse order of the prerequisites:
   - If you added the Organizations delegation policy statement, **trim only that statement**
     back out with the same read-and-merge care as adding it (`describe-resource-policy`, remove
     the `SRAVerifyListAccounts` statement, `put-resource-policy` the remainder — or
     `delete-resource-policy` only if it is now empty and nothing else uses it).
   - If you registered the audit account as a StackSets delegated administrator for this,
     `deregister-delegated-administrator`.
   - If you activated trusted access for this, `deactivate-organizations-access`. Leave it on if
     any other StackSet-based solution (SATv2, for one) depends on it.

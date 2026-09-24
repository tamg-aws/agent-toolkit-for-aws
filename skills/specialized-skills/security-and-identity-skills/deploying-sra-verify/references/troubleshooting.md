# Troubleshooting SRA Verify

Symptoms and fixes, ordered roughly by how often they occur. The scan runs entirely inside one
CodeBuild build in the audit account, so the CodeBuild build log is the primary evidence for
almost everything here.

## Read the build log first

```bash
# Most recent build
aws codebuild list-builds-for-project --profile <audit_profile> \
  --project-name SRAVerify-Security-Assessment --query 'ids[0]' --output text

aws codebuild batch-get-builds --profile <audit_profile> --ids <build-id> \
  --query 'builds[].{Status:buildStatus,Phase:currentPhase,Log:logs.deepLink}' --output json
```

The buildspec logs its progress in plain text: `Found accounts: <list>`, `Assuming role
running in management account: <id>`, `Running audit checks for account: <id>`, `Starting scan
for account <id>`, and a per-run summary (`Total findings`, `Pass`, `Fail`, `Error`, `Output`).
That log tells you which accounts were enumerated, which scans ran, and which failed.

**One structural fact drives several signals below:** the build script does **not** run under
`set -e`. A `sraverify` invocation that fails (a missing role, an assume-role denial) prints its
error and the script continues; the build phase's exit status reflects only its last command.
So a scan can be **partially** broken while the build still reports `SUCCEEDED`. "Green build"
is not "complete scan" — verify coverage against the results, not the build status.

## Management-type checks are absent, but the build succeeded

The single most common incomplete deployment. If the consolidated CSV has no rows with
`AccountType == management` (the organization CloudTrail, delegated-administrator, SRA-backbone
checks), the management account is almost certainly missing `SRAMemberRole` — **Step 2 (the
plain stack) was skipped**. StackSets never reach the management account, so its role must be
deployed separately. Because there is no `set -e`, the failed management scan did not fail the
build; it just produced no output.

Confirm and fix:

```bash
aws iam get-role --profile <management_profile> --role-name SRAMemberRole >/dev/null 2>&1 \
  && echo present || echo "absent — deploy Step 2"
```

Deploy Step 2 (`references/sraverify-deployment.md`), then re-scan with `start-build` (an
update does not scan).

## An entire account is missing from the results

An account that appears in `list-accounts` but has no rows in the consolidated CSV never got
scanned. Same mechanism as above: its `sraverify` invocation failed and the build continued.
Usual causes:

- **`SRAMemberRole` is not in that account** — the StackSet did not reach it (it was outside the
  targeted OUs, was added after rollout without `--auto-deployment`, or the instance is still
  `OUTDATED`/`FAILED` from a name collision). Check
  `list-stack-instances` and the collision guidance in `references/prerequisites.md`.
- **The instance was still deploying when the scan ran.** Confirm every target OU is `CURRENT`
  before `start-build`.

## Every account gets AccessDenied assuming `SRAMemberRole`

If the log shows assume-role failures across the board, the member role's **trust** does not
match the account running CodeBuild — not a permissions problem on the CodeBuild role. The
`SRAMemberRole` trust policy (from `1-sraverify-member-roles.yaml`) allows only:

- principal `arn:<partition>:iam::<SRAVerifyAccountID>:root`, **and**
- `aws:PrincipalArn` equal to
  `arn:<partition>:iam::<SRAVerifyAccountID>:role/SRAVerifyCodeBuildServiceRole` (root path, no
  `/service-role/`).

So it can be assumed only by `SRAVerifyCodeBuildServiceRole` in the account named by
`SRAVerifyAccountID`. Blanket AccessDenied means **`SRAVerifyAccountID` on the member template
was set to the wrong account** — most often left at the placeholder `012345678910`, or set to
an account other than the one that actually runs CodeBuild. Check the deployed role's trust:

```bash
aws iam get-role --profile <management_profile> --role-name SRAMemberRole \
  --query 'Role.AssumeRolePolicyDocument' --output json
```

If the account in the trust ARN is not your audit account, redeploy Step 1 and Step 2 with the
correct `SRAVerifyAccountID`. The CodeBuild role's own identity policy already allows
`sts:AssumeRole` on `arn:<partition>:iam::*:role/SRAMemberRole`, so the identity side is not the
problem — the trust side is.

Do **not** try to assume `SRAVerifyCodeBuildServiceRole` yourself to reproduce this: its trust
requires the CodeBuild `aws:SourceArn`, so no human principal can assume it. Read the trust
documents instead.

## The build fails immediately on `list-accounts`

If the log ends right after `Found accounts:` with an `AccessDeniedException` on
`organizations:ListAccounts`, the audit account cannot enumerate the organization. The scan
cannot proceed — every subsequent role ARN is built from that list. This is the Organizations
permission gate: see "Organizations permissions for the audit account" in
`references/prerequisites.md`. Check first whether the audit account is already a delegated
administrator (which grants the read) before writing any delegation policy.

## A check fails only for lack of permission (`ERROR` rows)

A cluster of `ERROR` rows — as opposed to `FAIL` — in one account means the check could not read
what it needed. If it is not a missing role (above), the likely cause is a **branch mismatch**:
the member role's permissions ship in `1-sraverify-member-roles.yaml` on the **same branch** the
solution clones the tool from, and a newer check can need a permission an older role does not
grant. The `GitBranch` parameter's own description says to redeploy the member roles from the
same branch to get the latest permissions.

The fix is to align the branch, never to widen the role by hand — the role is deliberately
read-only (rule 7 in `SKILL.md`). Redeploy Step 1 and Step 2 from the same branch the solution
uses, then re-scan.

## Coverage looks thin — a service reports absent when you know it is on

`IncludeRegions` is the scan's entire regional scope (default `us-east-1,us-east-2,us-west-2`).
A service enabled only in a region outside the list is reported absent, and regional checks do
not run there at all. This silently understates coverage (trap 3 in `SKILL.md`). Confirm the
list against where the organization operates, update it on the solution stack, and re-scan:

```bash
aws cloudformation deploy --profile <audit_profile> \
  --template-file 2-sraverify-codebuild-deploy.yaml \
  --stack-name <solution_stack_name> \
  --parameter-overrides IncludeRegions=us-east-1,us-east-2,us-west-2,us-west-1 \
    AuditAccountID=<...> LogArchiveAccountID=<...> ParallelAccounts=<n> GitBranch=<branch> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
# then, because an update does not scan:
aws codebuild start-build --profile <audit_profile> --project-name SRAVerify-Security-Assessment
```

## The build times out at ~60 minutes

The CodeBuild project sets **no** `TimeoutInMinutes`, so it inherits CodeBuild's 60-minute
default, and there is **no parameter to raise it**. A large organization — many accounts, many
regions — can hit it, and `buildStatus` comes back `TIMED_OUT` with the scan truncated. The
levers, in order:

- **Raise `ParallelAccounts`** (up to 20). It throttles the application pass, which is the bulk
  of the work; it is a real GNU-`parallel` job count, so raising it genuinely parallelises
  (unlike the sibling SATv2 solution's broken throttle). Redeploy Step 4 with the new value,
  then `start-build`.
- **Trim `IncludeRegions`** to the regions that actually matter, if some were speculative.
- **Split the assessment by OU** — deploy the member-role StackSet to a subset of OUs so
  `list-accounts` still returns the whole organization but the accounts without the role simply
  error out fast. There is no account-scope parameter (trap 2), so OU targeting is the only
  supported way to reduce the account set.
- **Run the CLI locally** against the slow account to see where time goes (below).

The role-type passes (management, audit, log-archive) are serial and unaffected by
`ParallelAccounts`; with many audit or log-archive accounts, those loops add fixed time.

## `No changes to deploy` — and no new scan

`aws cloudformation deploy` prints `No changes to deploy` and exits when the template and
parameters are unchanged. That is expected. More importantly, **even a successful update starts
no scan** — the custom resource's Lambda acts only on `RequestType == 'Create'`. To scan again,
always run `start-build` (rule 3 in `SKILL.md`):

```bash
aws codebuild start-build --profile <audit_profile> --project-name SRAVerify-Security-Assessment
```

## `raw/` has fewer CSVs than there are accounts

The per-scan files in `raw/` are named only by a second-resolution timestamp
(`sraverify_findings_<YYYYMMDD_HHMMSS>.csv`). The application scans run in parallel, and `raw/`
is a flat copy keyed on filename, so two accounts whose scans finish in the same wall-clock
second collide and one overwrites the other **in `raw/` only**. This does not affect the
consolidated CSV, which is assembled from each scan's own directory independently of the flat copy.
Present from the consolidated CSV (see `references/reviewing-results.md`); treat `raw/` as
convenience copies, not the source of truth.

## `S3_SRA_RESULTS_BUCKET` is set to a bucket **policy** — is that a bug?

No. In `2-sraverify-codebuild-deploy.yaml` the environment variable is
`S3_SRA_RESULTS_BUCKET: !Ref bucketPolicySRAVerifyFindings` — a `Ref` to the bucket **policy**
resource, not the bucket. `Ref` on an `AWS::S3::BucketPolicy` returns its physical ID, which is
the **bucket name**, so the variable resolves to the same value `!Ref` on the bucket would, and
the `aws s3 cp … s3://$S3_SRA_RESULTS_BUCKET/…` uploads land correctly (the workshop's working
output confirms it). A side effect that happens to help: referencing the policy makes
CloudFormation order the project after the TLS-only bucket policy exists, so uploads are never
attempted before that Deny is in place. It reads oddly but is not a defect — do not "fix" it.

## The build cannot reach GitHub, or `parallel`/`git` is missing

The buildspec clones the tool from `github.com` at build time and relies on `git`, GNU
`parallel`, `python3`, and `pip` being present in the `aws/codebuild/amazonlinux2-x86_64-standard:5.0`
image (it `pip install`s `boto3` and `pandas` itself). If the install phase fails on the clone,
the account running CodeBuild cannot reach GitHub — check egress (a restrictive VPC or proxy is
the usual cause; the project is not VPC-attached by default, so this is rare). If a later phase
fails on `parallel: command not found`, the image or a pinned older `GitBranch` changed an
assumption; the standard image ships GNU `parallel`.

## Two runs disagree with no change on your side

The tool is unpinned (`GitBranch=main`, cloned at build time), so the check set and behaviour
track whatever `main` points to that day. Runs weeks apart can legitimately differ. The
install-phase log records only the clone (`Cloning into 'sra-verify'...`), not the commit, so
resolve what `main` pointed to at each build's time out of band (`git ls-remote`, or the repo's
history at the build timestamp) and record it with the results (rule 6 in `SKILL.md`); when
comparing two runs, compare those commits first.

## Debug a single check locally

To understand one failing check without a full org scan, run the CLI locally against one
account — useful for reproducing an `ERROR` or confirming a `FAIL`. You manage credentials
yourself: use `--profile <profile>` (or ambient credentials) with an identity that already holds
read access in the target account, and scope with `--check` or `--service` and `--regions`. Do
**not** point `--role` at `SRAMemberRole` locally — its trust allows only
`SRAVerifyCodeBuildServiceRole` in the audit account, so no human principal can assume it (see
"Every account gets AccessDenied" above):

```bash
git clone -b main https://github.com/awslabs/sra-verify.git
pip install ./sra-verify/sraverify
sraverify --check SRA-GD-1 --regions us-east-1 --profile <account_profile>
sraverify --list-checks            # what this branch knows about
```

This is a diagnostic path, not the deployment path — standing up the org-wide assessment is the
CodeBuild route in `references/sraverify-deployment.md`.

## Non-standard partitions

Role ARNs, principal ARNs, and the CodeBuild `aws:SourceArn` all use `${AWS::Partition}` in the
templates, so they adapt to the partition the stack runs in — no edit needed for GovCloud
(`aws-us-gov`) or China (`aws-cn`). The one place the partition is hardcoded is the example
Organizations delegation policy in `references/prerequisites.md` (principal ARN `arn:aws:…`):
substitute `aws-cn` in China. GovCloud has no Organizations resource policies — route account
enumeration through a delegated administrator there instead. Confirm regional and partition
availability of the assessed services before treating an absence as a finding.

## cfn-lint fails on an unmodified template

cfn-lint's bundled schemas can lag the live CloudFormation registry, so a valid recent property
can surface as `E3002 Additional properties are not allowed` with a non-zero exit on an
untouched upstream template. Do not treat that exit alone as a gate failure — the change-set
dry run in `references/prerequisites.md` validates against the live registry and is
authoritative. Record `cfn-lint --version` with any such finding.

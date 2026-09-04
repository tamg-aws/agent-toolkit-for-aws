# SATv2 Troubleshooting

Pass `--profile <scanning_profile>` or `--profile <management_profile>` on every command
below, matching the account named in each heading.

## First: the build status does not tell you whether accounts were scanned

`ProwlerCodeBuild` can report `SUCCEEDED` while individual accounts failed. The buildspec
appends failures to a `failed_accounts` array **inside a backgrounded `{ ... } &` subshell**,
so the array never reaches the parent shell and the summary warning never prints. The
per-account log lines are the only signal.

Establish coverage explicitly, scoped to one build:

```bash
BUILD_ID=$(aws codebuild list-builds-for-project --profile <scanning_profile> \
  --project-name ProwlerCodeBuild --sort-order DESCENDING --query 'ids[0]' --output text)

# accounts actually assumed in THIS build
aws logs filter-log-events --profile <scanning_profile> \
  --log-group-name /aws/codebuild/ProwlerCodeBuild --log-stream-names "${BUILD_ID#*:}" \
  --filter-pattern '"Assumed Role ARN"' --query 'events[].message' --output text \
  | grep -oE '[0-9]{12}' | sort -u

# real per-account failures (expanded IDs only)
aws logs filter-log-events --profile <scanning_profile> \
  --log-group-name /aws/codebuild/ProwlerCodeBuild --log-stream-names "${BUILD_ID#*:}" \
  --filter-pattern '"Prowler scan failed for account"' --query 'events[].message' --output text \
  | grep -cE 'for account [0-9]{12}'

# access failures
aws logs filter-log-events --profile <scanning_profile> \
  --log-group-name /aws/codebuild/ProwlerCodeBuild --log-stream-names "${BUILD_ID#*:}" \
  --filter-pattern AccessDenied --query 'events[].message' --output text | grep -c .
```

Three traps in reading those logs:

- **The buildspec's own source is echoed into the log.** Lines containing unexpanded
  `$accountId` or `$AWS_ACCOUNT_ID` are script text, not events. That is why the failure
  count greps for an expanded 12-digit ID — without that filter every build reports two
  phantom failures.
- **Do not use `--query 'length(events)'`.** The CLI paginates and prints a count per page,
  so a real total of 16 can display as `0 0 16 0`. Pipe messages to `grep -c` instead.
- **An empty assumed-account list means the command did not run, not that no accounts were
  assumed.** The pipes into `grep` above turn any CLI failure — a mistyped flag, an expired
  token, a mis-expanded shell variable — into a clean-looking `0 accounts, 0 failures,
  0 AccessDenied`, with the error itself lost to stderr. Observed three times, once with the
  usage-error text itself counted as "6 AccessDenied". Before trusting any zero, confirm the
  first command printed the accounts you expected; if it printed nothing, run it again without
  the pipe and read the error.

Compare the assumed-account list against the accounts you expected. Attempted minus landed
is the unreachable set. Do **not** count distinct IDs in `csv/` for this — that prefix is
cumulative across runs and will over-report the current build.

## `ERROR: Failed to retrieve account list from AWS Organizations`

**Cause.** The buildspec calls `organizations list-accounts` from the scanning account. That
succeeds only from the management account or from a **registered delegated administrator**.

**Fix, in this order.**

1. Check whether the scanning account is already a delegated administrator for any service.
   If it is, no policy is needed — the registration itself grants the Organizations
   read-only permissions.

   ```bash
   aws organizations list-delegated-administrators --profile <management_profile> \
     --query 'DelegatedAdministrators[].[Id,Status]' --output text
   ```

2. Only if it is not, add an Organizations delegation policy — see
   `references/prerequisites.md`. Append to any existing policy rather than replacing it.
3. As a last resort, bypass discovery with `MultiAccountListOverride` (which also requires
   `MultiAccountScan='true'`).

## The scan covered only one account

**Cause.** `MultiAccountScan` defaults to `'false'`. The buildspec logs
`Running a single account scan.` and scans only the scanning account.

**Fix.** Update the stack with `MultiAccountScan='true'`. If you also want to restrict which
accounts are scanned, set `MultiAccountListOverride` **in addition** — on its own it is
inert, because the buildspec reads it only inside the `MultiAccountScan='true'` branch.

This and the stale-override case below are the two failures most likely to go unnoticed,
because both produce a complete, plausible result set. Always confirm the scanned-account count
against expectation using the coverage check above.

## The scan covered some accounts but not all

**Cause.** A non-empty `MultiAccountListOverride` left behind by an earlier pilot or a scoped
re-run. `MultiAccountScan` is `'true'`, so the scan presents as organization-wide and the build
reports `SUCCEEDED`, but the buildspec reads the override and scans only the accounts it names.

This is harder to spot than the single-account case above. The output is complete and plausible
for the accounts it does cover, and the skipped accounts are simply absent rather than flagged
anywhere. The management account is the most common casualty, because it is also the account a
service-managed StackSet never reaches — so it can be missing its role *and* missing from the
override, with neither surfacing as an error.

**Fix.** Read the override before trusting any coverage claim:

```bash
aws cloudformation describe-stacks --profile <scanning_profile> --stack-name SATv2 \
  --query 'Stacks[0].Parameters[?ParameterKey==`MultiAccountListOverride`].ParameterValue' \
  --output text
```

Empty output means discovery enumerates the organization. A list of account IDs means the scan
is capped at exactly those. Clear it with a stack update, then start a build — the update alone
starts no scan.

## Parameter validation error on the member-role template

**Cause.** The workshop text, as observed in 2026-09, names the parameter `AuditAccountId`. The
template's actual parameter is `ProwlerAccountID`, with `AllowedPattern: \d{12}`. Confirm the
workshop page still says so before telling a user their documentation is wrong.

**Fix.** Use `ProwlerAccountID`, twelve digits, no spaces or hyphens.

## Build times out

**Cause.** `CodeBuildTimeout` defaults to 300 minutes. The `Full` tier applies no filter, so
its runtime is bounded only by that timeout and scales with account count divided by
`ConcurrentAccountScans`.

**Fixes, in order of preference.**

1. Use `Intermediate` instead of `Full` unless every check is genuinely required.
2. Raise `ConcurrentAccountScans` — this also selects a larger compute type, so cost rises.
3. Raise `CodeBuildTimeout`. The maximum accepted value is **2160** minutes.
4. Split the organization across runs using `MultiAccountListOverride`.

State the cost consequence of options 2 and 3 before applying them.

## `AccessDenied` assuming the member role

**Cause, in likelihood order.**

1. The StackSet has not finished, or did not target that account. Check
   `list-stack-instances` for the account ID.
2. The account is the **management account**, which StackSets do not reach. It needs the
   separate plain stack from Step 2.
3. `ProwlerAccountID` in the member-role template does not match the account CodeBuild runs
   in, so the role's trust policy rejects it.
4. `ProwlerRole` was set to anything other than `ProwlerMemberRole` — see below.

**Do not try to reproduce the assume yourself.** `ProwlerMemberRole` trusts the scanning
account's root narrowed by `ArnEquals` on `aws:PrincipalArn` to exactly
`ProwlerCodeBuildRole`, and that role in turn trusts only `codebuild.amazonaws.com`. No
human principal can stand in for it, so `aws sts assume-role` fails even against a perfectly
healthy account. Use the log-based coverage check at the top of this file instead.

An identity-side sanity check is available, though it does not evaluate the member account's
trust policy:

```bash
aws iam simulate-principal-policy --profile <scanning_profile> \
  --policy-source-arn arn:<partition>:iam::<scanning_account_id>:role/service-role/ProwlerCodeBuildRole \
  --action-names sts:AssumeRole \
  --resource-arns arn:<partition>:iam::<member_account>:role/service-role/ProwlerMemberRole \
  --query 'EvaluationResults[0].EvalDecision' --output text
```

Do not widen the member role or loosen its trust policy to resolve this. Fix the mismatch.

## `ProwlerRole` only works at its default

The parameter looks configurable but is inert. Leave it at `ProwlerMemberRole`.

What a non-default value looks like, observed with `ProwlerRole=ProwlerAuditRole`: the build
reaches `FAILED` in about two minutes (this is the every-account case, so unlike the partial
failures described at the top of this file the build status *does* reflect it); the log
carries `CRITICAL: AWSAssumeRoleError[1012]: AWS assume role error - An error occurred
(AccessDenied) when calling the AssumeRole operation`; the coverage check reports zero
assumed accounts and one `Prowler scan failed for account` line per account; no `Scan
completed` line appears, `csv/` gains nothing, and the reporting chain never fires.

- The CodeBuild role's `sts:AssumeRole` statement hardcodes the role as a literal —
  `arn:<partition>:iam::*:role/service-role/ProwlerMemberRole`. The wildcard covers the
  **account** segment only, so a different role name does not match and the assume is denied.
- The buildspec hardcodes the path: `--role arn:...:iam::$accountId:role/service-role/$PROWLER_ROLE`.
  `$PROWLER_ROLE` supplies only the final name segment, so a role at path `/` is unreachable.
- The member-role template hardcodes `RoleName: ProwlerMemberRole` too.
- `!Ref ProwlerRole` reaches nothing but a CodeBuild environment variable.

**This kills the common "point it at our existing audit role" request.** A customer cannot
substitute an existing read-only role unless it is named `ProwlerMemberRole` at path
`/service-role/`. What they *can* do is author that role themselves at that exact name and
path — SATv2 does not care which template created it — which keeps the permission set and
change control in their hands. If they do, the role still needs the same trust policy:
principal is the scanning account root, restricted by `ArnEquals` on `aws:PrincipalArn` to
the `ProwlerCodeBuildRole` ARN. A correct name and path with the wrong trust still fails.

Note the misleading source: the sentence *"or specify a different ProwlerRole with the
appropriate permissions"* appears in the **`MultiAccountScan`** parameter's description, not
`ProwlerRole`'s. Customers reading the template take it at face value.

## A stack update failed or rolled back

Stack-level failures do not appear in the CodeBuild log at all, so the coverage check above
will not find them. Read the stack instead:

```bash
aws cloudformation describe-stacks --profile <scanning_profile> --stack-name SATv2 \
  --query 'Stacks[0].StackStatus' --output text
aws cloudformation describe-events --profile <scanning_profile> --stack-name SATv2 \
  --query 'OperationEvents[?EventType==`VALIDATION_ERROR`].[ValidationName,LogicalResourceId,ValidationStatusReason]' \
  --output text
```

`describe-events` is the call that carries pre-deployment validation detail. The legacy
`describe-stack-events` reports only a generic `Validation failed with 1 error(s)`, and the
sibling `aws-cloudformation` skill's SOP steers away from it for the same reason. A role-name
collision reads `NAME_CONFLICT_VALIDATION` against logical ID `ProwlerIntegrationCodeBuildRole`,
exactly as under "The member accounts you cannot pre-check" in `references/prerequisites.md`;
note the response key is `OperationEvents`, not `Events`. On a rolled-back plain stack this is
documented behaviour, not something this skill's authors exercised live. If `OperationEvents`
comes back empty, fall back to a diagnostic change set, which surfaces the same validation
without executing anything. Creating and deleting the change set are gated writes under rule 1
even though they provision no resources:

```bash
aws cloudformation create-change-set --profile <scanning_profile> \
  --stack-name SATv2 --change-set-name diag \
  --template-body file://2-sat2-codebuild-prowler.yaml \
  --parameters <your parameters> --capabilities CAPABILITY_NAMED_IAM
aws cloudformation describe-change-set --profile <scanning_profile> \
  --stack-name SATv2 --change-set-name diag --query '[Status,StatusReason]' --output text
aws cloudformation delete-change-set --profile <scanning_profile> \
  --stack-name SATv2 --change-set-name diag
```

**The most common cause is a role-name collision.** Setting `MultiAccountScan` to `'false'`
on a deployment whose StackSet already placed `ProwlerMemberRole` in the scanning account
makes the stack try to create a role that exists. CloudFormation rejects this during
validation, before touching resources, so the rollback is clean and nothing is left
half-changed — but the update cannot succeed until the setting is left at `'true'` or the
existing role is gone. This skill does not delete a role it did not create; that is the
account owner's decision, after confirming nothing else assumes it.

## Athena query fails on a missing or unexpected column

**Cause.** Prowler's CSV output schema has drifted from the explicit column list in the Glue
table definition. This is what the version pin exists to prevent.

**Fix.** Confirm the running Prowler version matches the template's pin. Do not edit the
Glue table to match a newer Prowler — the reporting path depends on the declared schema.

## Athena query fails with `AccessDenied`

First establish which regime the account is in with `lakeformation get-data-lake-settings`, as
described under "Lake Formation may govern this table" in `references/reviewing-results.md`.
In a stock account (`IAM_ALLOWED_PRINCIPALS` defaults present) the denial is ordinary IAM on
Glue, Athena or the bucket. Only in an account that has adopted Lake Formation — Security Lake
puts it there — is it a Lake Formation grant that no IAM policy explains.

## Prowler version staleness

The template pins `prowler==5.11` on Python 3.12. This pin is **deliberate**, made upstream
to resolve a reporting problem, and held across subsequent commits because the Glue table
declares an explicit column schema the reporting path reads.

Read the pin at runtime rather than asserting a version:

```bash
grep -n 'prowler==' 2-sat2-codebuild-prowler.yaml
python3 -c 'import json,urllib.request;print(json.load(urllib.request.urlopen("https://pypi.org/pypi/prowler/json"))["info"]["version"])'
```

The second line reads the current release from PyPI (5.41.0 as of 2026-09), so the comparison
is measured rather than recalled. Compare the two and **report the gap as a fact** — newer checks will be
absent, so a clean scan does not mean a clean account under current Prowler guidance. Do not
bump the pin; that breaks reporting. If newer checks are needed, the correct path is upstream
in [`awslabs/aws-security-assessment-solution`](https://github.com/awslabs/aws-security-assessment-solution).

Note the dashboard follows a different policy: `ProwlerReportingCodeBuild` clones the
repository's default branch at run time and copies a static HTML file, so the dashboard is
**not** pinned and drifts with upstream independently of the Prowler version.

## Partitions

Commands here use `<partition>` where an ARN partition is required. Substitute `aws`,
`aws-us-gov` or `aws-cn` to match the account. The templates themselves use
`${AWS::Partition}` and `$AWS_PARTITION` and need no change.

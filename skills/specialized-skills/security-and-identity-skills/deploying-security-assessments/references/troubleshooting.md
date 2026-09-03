# SATv2 Troubleshooting

Diagnose from the CodeBuild log, not from the stack status. The stack reaches
`CREATE_COMPLETE` as soon as the build is *started*, so a green stack tells you nothing
about whether the scan succeeded.

```bash
aws codebuild list-builds-for-project --project-name <project> --sort-order DESCENDING
aws codebuild batch-get-builds --ids <build_id> \
  --query 'builds[0].{Status:buildStatus,Phase:currentPhase,Log:logs.deepLink}'
```

## `ERROR: Failed to retrieve account list from AWS Organizations`

**Cause.** The buildspec runs `aws organizations list-accounts` from the scanning account.
Outside the management account this fails unless an Organizations delegation policy grants
it, and the build exits non-zero.

**Fix.** Add the delegation policy in `references/prerequisites.md` from the management
account, appending to any existing policy. Then re-run the build — the stack does not need
redeploying.

**Workaround when the policy cannot be added.** Set `MultiAccountListOverride` to an
explicit account list, which bypasses discovery entirely.

## The scan covered only one account

**Cause.** `MultiAccountScan` defaults to `'false'`. The buildspec logs
`Running a single account scan.` and scans only the scanning account.

**Fix.** Update the stack with `MultiAccountScan='true'`, or supply
`MultiAccountListOverride`. Confirm from the log which path ran before reporting coverage.

This is the failure most likely to go unnoticed, because it produces a complete, plausible
result set. Always confirm scanned-account count against expected.

## Parameter validation error on the member-role template

**Cause.** The workshop text names the parameter `AuditAccountId`. The template's actual
parameter is `ProwlerAccountID`, with `AllowedPattern: \d{12}`.

**Fix.** Use `ProwlerAccountID`, twelve digits, no spaces or hyphens.

## Build times out

**Cause.** `CodeBuildTimeout` defaults to 300 minutes. The `Full` tier applies no severity
or check filter, so its runtime is bounded only by that timeout and scales with account
count divided by `ConcurrentAccountScans`.

**Fixes, in order of preference.**

1. Use `Intermediate` instead of `Full` unless every check is genuinely required.
2. Raise `ConcurrentAccountScans` — this also selects a larger compute type (`Three` uses
   `BUILD_GENERAL1_SMALL`, `Six` uses `BUILD_GENERAL1_MEDIUM`), so cost rises with it.
3. Raise `CodeBuildTimeout`.
4. Split the organization across runs using `MultiAccountListOverride`.

State the cost consequence of options 2 and 3 before applying them.

## `AccessDenied` assuming the member role

**Cause, in likelihood order.**

1. The StackSet has not finished, or did not target the account. Check
   `list-stack-instances` for that account ID.
2. The account is the **management account**, which StackSets do not reach. It needs the
   separate plain stack from Step 2.
3. `ProwlerAccountID` in the member-role template does not match the account CodeBuild
   actually runs in, so the role's trust policy rejects it.
4. `ProwlerRole` in the solution stack does not match the role name the StackSet created.

The member role's trust policy names the scanning account root as principal and further
restricts `aws:PrincipalArn` with `ArnEquals` to exactly the CodeBuild role ARN. Both the
account and the role path must match; the role is created at path `/service-role/`.

Verify from the scanning account:

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::<member_account>:role/service-role/ProwlerMemberRole \
  --role-session-name satv2-check
```

Do not widen the member role or loosen its trust policy to resolve this. Fix the mismatch.

## Athena query fails on a missing or unexpected column

**Cause.** Prowler's CSV output schema has drifted from the explicit column list in the
Glue table definition. This is what the version pin exists to prevent.

**Fix.** Confirm the running Prowler version matches the template's pin. Do not edit the
Glue table to match a newer Prowler — the Athena named query and the reporting path both
depend on the declared schema.

## Prowler version staleness

The template pins `prowler==5.11` on Python 3.12. This pin is **deliberate**, made upstream
to resolve a reporting problem, and held across subsequent commits because the Glue table
declares an explicit column schema that the Athena query and reporting path read.

Read the pin at runtime rather than asserting a version:

```bash
grep -n 'prowler==' 2-sat2-codebuild-prowler.yaml
```

Compare it to the current release and **report the gap as a fact** — newer checks will be
absent from results, so a clean scan does not mean a clean account under current Prowler
guidance. Do not bump the pin to close the gap; that breaks reporting. If the user needs
newer checks, the correct path is upstream in
[`awslabs/aws-security-assessment-solution`](https://github.com/awslabs/aws-security-assessment-solution),
not a local edit.

## Empty results with a successful build

Check, in order:

1. `aws s3 ls s3://<bucket>/csv/ --recursive` — did anything land at all?
2. The build log for per-account `AccessDenied` lines. A build can succeed while individual
   accounts fail to be assumed.
3. Whether `Reporting` was `'false'`, in which case the Glue table and Athena workgroup do
   not exist and only raw S3 output is available.

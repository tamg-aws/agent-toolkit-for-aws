# Reviewing SATv2 Results

All output lands in the findings bucket created by `2-sat2-codebuild-prowler.yaml` in the
scanning account. Pass `--profile <scanning_profile>` on every command here.

```bash
aws cloudformation describe-stack-resources --profile <scanning_profile> --stack-name SATv2 \
  --query 'StackResources[?ResourceType==`AWS::S3::Bucket`].PhysicalResourceId' --output text
```

That bucket name is also the name of the Glue database **and** the Athena workgroup — the
template names both `!Ref` the bucket. There is no `SATv2`-named Glue or Athena resource, so
searching for one finds nothing.

## S3 layout

Only the formats Prowler actually emitted appear. Do not treat a missing prefix as a failure:

| Prefix | Contents | Observed |
|---|---|---|
| `csv/` | Per-account findings, **semicolon-delimited**. This is what the Glue table reads | Always |
| `ocsf-json/` | OCSF-formatted JSON | Always |
| `html/` | Prowler's own HTML report | Always |
| `reports/` | The automatic full export, its `.metadata` sidecar, and `satv2-dashboard.html` | When `Reporting='true'` |
| `compliance/` | Compliance-framework CSVs | Tier-dependent — present in an observed `Full` run (SOC2, CIS and other framework CSVs); absent in observed `Intermediate` and `Basic` runs |
| `json/` | Native Prowler JSON | **Never on Prowler 5** — the pinned version has no plain `json` output format, so the buildspec's copy step for this prefix finds nothing |
| `asff-json/` | ASFF-formatted JSON | Only when `ProwlerOptions` includes `-M … json-asff` (see below) — absent under the default options in observed `Basic`, `Intermediate` **and** `Full` runs |
| `athena_results/` | Athena query output | Only for queries that use the workgroup's own output location; the automatic export overrides it to `reports/` |

The `csv/` files use `;` as the delimiter, not `,` — the Glue SerDe is `OpenCSVSerde` with
`separatorChar: ";"`. Opening them in a tool that assumes commas yields a single column.

```bash
aws s3 ls s3://<bucket>/csv/ --recursive --profile <scanning_profile>
```

An empty `csv/` prefix means the scan did not complete, not that nothing was found.

## Repeated scans accumulate and blend

**This is the easiest way to report wrong numbers.** Every scan writes a new timestamped CSV
per account into `csv/`; nothing is cleaned up. The Glue table is an unpartitioned
`EXTERNAL_TABLE` over the whole prefix, so it reads **every file from every run**.

Worse than double-counting: after a scoped re-run, some accounts hold fresh data and others
hold data from an earlier scan, so an unfiltered query mixes scan dates per account and any
"current posture" claim is wrong.

```bash
aws s3 ls s3://<bucket>/csv/ --recursive --profile <scanning_profile>
```

Then either scope the query or isolate runs:

- **Scope it.** The table has a `timestamp` column. Filter to the run you mean.
- **Or isolate.** Move or delete the previous run's CSVs before re-scanning. Deleting
  findings is destructive to the user's data — confirm first, and never do it implicitly as
  part of a re-scan.

The same hazard applies to any **local directory you download into**. `aws s3 cp --recursive`
into a directory that already holds CSVs from an earlier run — or a different organization —
blends them just as the Glue table does; observed producing a six-account summary for a
two-account organization. Download each run into a fresh, empty directory.

State the scan timestamps your numbers cover whenever you present findings after more than
one scan.

## Glue and Athena

Created only when `Reporting` is `'true'` (the default).

- **Glue database** — named after the findings bucket.
- **Glue table `prowler`** — `EXTERNAL_TABLE`, `OpenCSVSerde` with `;`, 41 columns,
  `skip.header.line.count` of 1, location `s3://<bucket>/csv`. Its schema is explicit and is
  why the Prowler version is pinned.
- **Athena workgroup** — also named after the bucket, output to `s3://<bucket>/athena_results`.
- **Named query `Prowler organization summary`** (`qProwlerOrgSummary`) — counts **failed**
  findings per `check_id` across assessed accounts. It filters `WHERE status = 'FAIL'`, so it
  is not a count of all findings, and **nothing invokes it automatically**.

### Lake Formation may govern this table

Whether Lake Formation or plain IAM decides who can query `prowler` is a property of the
**account's** data lake settings, not of the SATv2 template. The template makes exactly one
Lake Formation grant — `SELECT` to the reporting Lambda's role — and otherwise leaves the
account's defaults in force. Two reads settle which regime the existing table is in:

```bash
# 1. The grants on the prowler table itself — this is the decisive check
aws lakeformation list-permissions --profile <scanning_profile> \
  --resource '{"Table":{"CatalogId":"<scanning_account_id>","DatabaseName":"<bucket>","Name":"prowler"}}' \
  --query 'PrincipalResourcePermissions[].[Principal.DataLakePrincipalIdentifier,Permissions]' --output text
# 2. The account defaults — what a NEW deployment will inherit
aws lakeformation get-data-lake-settings --profile <scanning_profile> \
  --query 'DataLakeSettings.[CreateDatabaseDefaultPermissions,CreateTableDefaultPermissions]' \
  --output json
```

The defaults apply at creation time, so they describe the table only if they have not changed
since the stack created it; the grants on the table are what actually decide access.

**`IAM_ALLOWED_PRINCIPALS` holds `ALL` on the table** (and, for a fresh deployment, both
default lists show it) — the AWS default, "Use only IAM access control", and what a stock
account's defaults look like (observed). IAM alone governs the table: any principal with the
Glue, Athena and S3 permissions can query it, and none of the Lake Formation guidance below
applies. An Athena `AccessDenied` here is an ordinary IAM problem —
`glue:GetTable`/`GetDatabase`, `athena:StartQueryExecution`/`GetQueryResults`, `s3:GetObject`
on `csv/` and `s3:PutObject` on `athena_results/` — and should be diagnosed as one.

**No `IAM_ALLOWED_PRINCIPALS` grant on the table** (and empty default lists). Lake Formation
governs it with no fallback. This is what an account that has adopted Lake Formation looks
like. Both accounts this skill's authors observed in this regime run Security Lake, whose
metastore role was a data lake admin in each — but whether Security Lake's setup is what
cleared the defaults is not confirmed by its documentation, so read the grants rather than
inferring the regime from Security Lake's presence. In this regime only the deploying principal and the
reporting Lambda's role hold `SELECT`, and **any other principal gets an Athena `AccessDenied`
that no IAM policy explains** — IAM admin is not sufficient.

Everything below applies to the Lake Formation regime only.

**If you deployed the stack, you already hold `SELECT` — just query.** CloudFormation created
the Glue database and table under your session, and Lake Formation grants the creating
principal `ALL`, `ALTER`, `DELETE`, `DESCRIBE`, `DROP`, `INSERT` and `SELECT` implicitly.
Observed in two Security Lake accounts: the deployer was not a data lake admin in either, and Athena
succeeded with no grant. Confirm rather than assume:

```bash
aws lakeformation list-permissions --profile <scanning_profile> \
  --resource '{"Table":{"CatalogId":"<scanning_account_id>","DatabaseName":"<bucket>","Name":"prowler"}}' \
  --query 'PrincipalResourcePermissions[].[Principal.DataLakePrincipalIdentifier,Permissions]' --output text
```

Do not read the data-lake-admin list as an access list. Being an admin governs whether you can
**grant others**, not whether you can query; a deployer who is not an admin still queries fine,
and a non-deployer who is an admin still needs a grant.

**Granting someone else** `SELECT` is the case that needs a Lake Formation write — approval
under rule 1 — and only the deployer or a data lake admin can perform it:

```bash
aws lakeformation grant-permissions --profile <scanning_profile> \
  --principal DataLakePrincipalIdentifier=<their_role_arn> \
  --resource '{"Table":{"CatalogId":"<scanning_account_id>","DatabaseName":"<bucket>","Name":"prowler"}}' \
  --permissions SELECT
```

If you are neither, you cannot self-grant — `GrantPermissions` itself fails with a Lake
Formation `AccessDenied`. Escalate to the deployer or a data lake admin rather than trying to
fix it with IAM.

Lake Formation governs metadata only here; no S3 data locations are registered, so object
reads fall back to IAM in both regimes.

## The automatic reporting chain

When `Reporting` is `'true'`, output is produced **without the operator doing anything**:

1. `ProwlerCodeBuild` reaches `SUCCEEDED` → EventBridge rule `CodeBuildCompleteRunSummary`
   fires. It matches only on `SUCCEEDED`.
2. `AthenaStartQueryLambda` runs `SELECT * FROM "AwsDataCatalog"."<bucket>"."prowler"` and
   writes the result to `s3://<bucket>/reports`.
3. A second rule watches `reports/*.csv` for `Object Created`.
4. That rule invokes `ProwlerReportingLambda`, which starts a **second CodeBuild project**,
   `ProwlerReportingCodeBuild`.
5. That project clones the upstream repository and copies its static
   `satv2-dashboard.html` into `reports/`.

**What lands in `reports/` is a full unfiltered export, not a summary.** Step 2's query has
no `WHERE`, no `LIMIT` and no aggregation, so the file is every row of every CSV in `csv/` —
tens of megabytes. It is useful as a single consolidated file to feed the dashboard, not as
something to read. For an actual summary, run `qProwlerOrgSummary`.

Two further consequences:

- **There are two CodeBuild projects.** `ProwlerCodeBuild` runs the scan;
  `ProwlerReportingCodeBuild` publishes the dashboard.
- The dashboard is fetched from the upstream default branch at run time and is **not
  pinned**, unlike Prowler. It also requires the reporting project to reach github.com.

### If `reports/` is empty

Diagnose in this order — populated `csv/` does **not** mean the scan succeeded:

1. **Check whether `ProwlerCodeBuild` actually reached `SUCCEEDED`.** `post_build` uploads
   `csv/` first and the other prefixes after; a failure on any later prefix sets a failure
   flag and exits non-zero. So populated `csv/` with a failed build is the expected state,
   and the EventBridge rule never fires. Look for upload errors in that project's log.
2. **Check `Reporting`.** If `'false'`, none of the Glue, Athena or reporting resources exist.
3. **Check the `AthenaStartQueryLambda` log.** It swallows client errors, so an Athena failure
   leaves `reports/` empty with a healthy build and no visible error.

Only if the summary CSV exists but the dashboard does not is `ProwlerReportingCodeBuild` the
culprit — it is downstream of `reports/*.csv` and cannot cause an empty prefix.

## Presenting findings

- **Lead with counts, not raw rows.** A per-account and per-severity summary first, detail on
  request.
- **Attribute the opinion.** These are Prowler's findings at a pinned version. State the
  version alongside the results.
- **Report scan scope explicitly.** Say how many accounts were scanned and which. If
  `MultiAccountScan` was `'false'`, say plainly that only the scanning account was assessed.
  Say which run(s) the numbers come from — the table blends every run in `csv/` unless you
  filtered on `timestamp`.
- **Do not suppress or dismiss findings.** Filtering to a severity for readability is fine if
  you say so.
- **Findings can contain sensitive detail** — resource ARNs, account IDs, network
  configuration. Summarize first, note what the full output contains, and show raw rows only
  when asked.

## Feeding findings elsewhere

The `asff-json/` prefix is the format Security Hub ingests, so SATv2 output can be imported
into Security Hub CSPM. Importing is a mutating action on another service and is outside this
skill — surface the option and let the user decide.

**It is not produced by default.** The prefix was empty after observed `Basic`, `Intermediate`
**and** `Full` runs, so on a default deployment this route is simply unavailable. Do not offer
it until `aws s3 ls s3://<bucket>/asff-json/` returns objects.

The cause is Prowler's output-format selection, not SATv2 discarding the files. The buildspec
does copy `*.asff.json` into `asff-json/`, and `ProwlerOptions` is passed verbatim to the
`prowler` invocation — but the default `aws --ignore-exit-code-3` carries no output-format
flag, so Prowler emits only its default set. That is also why `csv/`, `ocsf-json/` and `html/`
are the three `Always` prefixes above.

Enabling ASFF means adding Prowler's output-format flag to `ProwlerOptions`. Verified against
the pinned 5.11.0 source and live: the flag is `-M` (`--output-formats`), its allowed values
are `csv`, `json-asff`, `json-ocsf` and `html`, and its default is `csv json-ocsf html` — which
is exactly the three `Always` prefixes. **`-M` replaces the default list rather than adding to
it**, so name every format you still want:

```text
ProwlerOptions = aws --ignore-exit-code-3 -M csv json-asff json-ocsf html
```

Observed: after that update and a fresh build, `asff-json/` held one `.asff.json` per account
with no upload errors, and `csv/`, `ocsf-json/` and `html/` were still produced. There is no
plain `json` value, which is why `json/` stays empty. It is a scan parameter, so it requires a
stack update *and* a fresh `start-build`; the update alone starts no scan.

Note also that `ProwlerMemberRole` already carries `securityhub:BatchImportFindings` in every
assessed account, whether or not the user intends to use it.

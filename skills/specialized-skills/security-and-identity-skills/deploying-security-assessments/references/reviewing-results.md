# Reviewing SATv2 Results

All output lands in the findings bucket created by `2-sat2-codebuild-prowler.yaml` in the
scanning account. Find its name from the stack:

```bash
aws cloudformation describe-stack-resources --stack-name SATv2 \
  --query 'StackResources[?ResourceType==`AWS::S3::Bucket`].PhysicalResourceId'
```

## S3 layout

The buildspec copies Prowler output into one prefix per format, but **only the formats
Prowler actually emitted appear**. Do not treat a missing prefix as a failure — list what
exists rather than expecting all of them:

| Prefix | Contents | Observed |
|---|---|---|
| `csv/` | Per-account CSV findings, excluding compliance output. **This is what the Glue table reads.** | Always |
| `ocsf-json/` | OCSF-formatted JSON | Always |
| `html/` | Prowler's own HTML report | Always |
| `reports/` | The automatic org summary CSV **and `satv2-dashboard.html`** — see below | When `Reporting='true'` |
| `compliance/` | Compliance-framework CSVs | Conditional — absent in observed `Intermediate` and `Basic` multi-account runs on the pinned Prowler |
| `json/` | Native Prowler JSON | Conditional — absent unless Prowler emits that format |
| `asff-json/` | ASFF-formatted JSON, the format Security Hub ingests | Conditional — absent unless Prowler emits that format |
| `athena_results/` | Athena query output | Only once a query runs through the workgroup's own output location; the automatic summary writes to `reports/` instead |

The first four are what a normal run produces. If the user needs ASFF for Security Hub
import, confirm it exists before promising it — verify with
`aws s3 ls s3://<bucket>/asff-json/` rather than assuming the prefix is populated.

Confirm a scan actually produced findings before interpreting emptiness as a clean result:

```bash
aws s3 ls s3://<bucket>/csv/ --recursive --human-readable --summarize | tail -5
```

An empty `csv/` prefix means the scan did not complete, not that nothing was found. Check
the **`ProwlerCodeBuild`** project's logs — see `references/troubleshooting.md`. If `csv/`
is populated but `reports/` is empty, the scan succeeded and the fault is in the reporting
chain instead; check `ProwlerReportingCodeBuild`.

## Glue and Athena

Created only when `Reporting` is `'true'` (the default).

- **Glue database** — named by the stack; holds one table.
- **Glue table `prowler`** — `EXTERNAL_TABLE`, CSV classification, `skip.header.line.count`
  of 1, location `s3://<bucket>/csv`. Its column schema is explicit and is why the Prowler
  version is pinned.
- **Athena workgroup** — named after the Glue database, output to
  `s3://<bucket>/athena_results`.
- **Named query `Prowler organization summary`** (`qProwlerOrgSummary`) — counts findings
  per `check_id` across all assessed accounts.

## Repeated scans accumulate and blend

**This is the easiest way to report wrong numbers.** Every scan writes a new timestamped CSV
per account into `csv/`; nothing is cleaned up. The Glue table is an unpartitioned
`EXTERNAL_TABLE` over the whole `csv/` prefix, so it reads **every file from every run**, and
the shipped `qProwlerOrgSummary` query has no run filter. Two scans of four accounts leave
eight files, and the "organization summary" then counts both runs together with no
indication it has done so.

Observed: a second scan raised the file count from 4 to 8 and the automatic summary CSV from
20.3 MiB to 21.7 MiB.

Before reporting any count, establish which runs you are covering:

```bash
# how many files, and from how many distinct runs?
aws s3 ls s3://<bucket>/csv/ --recursive
```

Then either scope the query or clear the prefix:

- **Scope it.** The table has a `timestamp` column. Filter to the run you mean rather than
  querying the whole table — the shipped named query does not do this for you.
- **Or isolate runs.** Move or delete the previous run's CSVs out of `csv/` before
  re-scanning, so the table only sees the current run. Deleting findings is a destructive
  act on the user's data — confirm before doing it, and never do it implicitly as part of a
  re-scan.

State the scan timestamps your numbers cover whenever you present findings after more than
one scan.

## The automatic reporting chain

When `Reporting` is `'true'`, a summary and dashboard are produced **without the operator
doing anything**. Do not tell the user to run a query manually before checking whether this
already ran. The chain, in order:

1. The scan finishes → EventBridge rule `CodeBuildCompleteRunSummary` fires.
2. `AthenaStartQueryLambda` runs a `SELECT` over the `prowler` table, writing to
   `s3://<bucket>/reports`.
3. A second EventBridge rule watches `reports/*.csv` for `Object Created`.
4. That rule invokes `ProwlerReportingLambda`, which starts a **second CodeBuild project**,
   `ProwlerReportingCodeBuild`.
5. That project uploads `satv2-dashboard.html` into `reports/`.

Two operator consequences:

- **There are two CodeBuild projects.** `ProwlerCodeBuild` runs the scan;
  `ProwlerReportingCodeBuild` builds the dashboard. When the dashboard is missing but the
  scan succeeded, the failure is in the reporting project — look there, not in the scan
  project's logs.
- All of these resources are conditional on `Reporting`. With `Reporting='false'` none of
  them exist, so `reports/`, the dashboard, Glue, and Athena are all absent and only the raw
  per-format prefixes are populated.

This is the fallback path, not the first step — check `reports/` for the automatic summary
before querying by hand. When you do need an ad-hoc query, or the automatic chain did not
run, use the shipped named query rather than writing one from scratch:

```bash
aws athena list-named-queries --work-group <workgroup>
aws athena get-named-query --named-query-id <id> --query 'NamedQuery.QueryString'
```

Then execute it:

```bash
aws athena start-query-execution \
  --query-string "$(aws athena get-named-query --named-query-id <id> \
      --query 'NamedQuery.QueryString' --output text)" \
  --work-group <workgroup>
aws athena get-query-execution --query-execution-id <exec_id> \
  --query 'QueryExecution.Status.State'
aws athena get-query-results --query-execution-id <exec_id>
```

If a query fails with a column error, the Prowler output schema has drifted from the Glue
table definition. Report that as a version mismatch rather than editing the table — see
`references/troubleshooting.md`.

## Presenting findings

- **Lead with counts, not raw rows.** Findings volume is large; a per-account and
  per-severity summary first, detail on request.
- **Attribute the opinion.** These are Prowler's findings at a pinned version, not an
  absolute verdict. State the version alongside the results.
- **Report scan scope explicitly.** Say how many accounts were scanned and which. If
  `MultiAccountScan` was `'false'`, say plainly that only the scanning account was
  assessed — a summary that silently covers one account reads as if it covered the
  organization. Equally, say which scan run(s) the numbers come from: the Glue table blends
  every run in `csv/` unless you filtered on `timestamp`.
- **Do not suppress or dismiss findings.** Present what the scan found. Filtering to a
  severity for readability is fine if you say so.
- **Findings can contain sensitive detail** — resource ARNs, account IDs, network
  configuration. Summarize first, note what the full output contains, and show raw rows
  only when asked.

## Feeding findings elsewhere

The `asff-json/` prefix is ASFF, the format Security Hub ingests, so SATv2 output can be
imported into Security Hub CSPM rather than reviewed only in Athena. Importing is a
mutating action on another service and is outside this skill — surface the option and let
the user decide.

**Check the prefix exists first.** It was absent in an observed `Intermediate` multi-account
run, so do not offer the Security Hub route until `aws s3 ls s3://<bucket>/asff-json/`
returns objects. Note also that `ProwlerMemberRole` already carries
`securityhub:BatchImportFindings`, so the permission for that import is present in every
assessed account whether or not the user intends to use it.

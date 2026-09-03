# Reviewing SATv2 Results

All output lands in the findings bucket created by `2-sat2-codebuild-prowler.yaml` in the
scanning account. Find its name from the stack:

```bash
aws cloudformation describe-stack-resources --stack-name SATv2 \
  --query 'StackResources[?ResourceType==`AWS::S3::Bucket`].PhysicalResourceId'
```

## S3 layout

The buildspec copies Prowler output into one prefix per format:

| Prefix | Contents |
|---|---|
| `csv/` | Per-account CSV findings, excluding compliance output. **This is what the Glue table reads.** |
| `compliance/` | Compliance-framework CSVs |
| `json/` | Native Prowler JSON |
| `ocsf-json/` | OCSF-formatted JSON |
| `asff-json/` | ASFF-formatted JSON, the format Security Hub ingests |
| `html/` | Prowler's own HTML report |
| `athena_results/` | Athena query output |

Confirm a scan actually produced findings before interpreting emptiness as a clean result:

```bash
aws s3 ls s3://<bucket>/csv/ --recursive --human-readable --summarize | tail -5
```

An empty `csv/` prefix means the scan did not complete, not that nothing was found. Check
the CodeBuild logs — see `references/troubleshooting.md`.

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

Run the shipped named query rather than writing one from scratch:

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
  organization.
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

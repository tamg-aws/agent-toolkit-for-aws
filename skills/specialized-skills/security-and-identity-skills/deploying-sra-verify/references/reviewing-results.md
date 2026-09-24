# Reviewing SRA Verify results

After a build reports `SUCCEEDED`, results are in the findings bucket in the audit account.
This file covers where they are, what they contain, the dashboard and generative-AI flows and
their data-handling risks, and how to present findings honestly.

## Where the results are

The bucket has a **generated** name — the template sets no `BucketName`, so CloudFormation
names it `<solution-stack>-bucketsraverifyfindings-<random>`. Find it through the stack, or by
prefix `<stack-name-lowercased>-bucketsraverifyfindings-*` (the workshop's `SRAVerify` stack
gives `sraverify-…`; the README's `sra` stack gives `sra-…`):

```bash
aws cloudformation describe-stack-resources --profile <audit_profile> \
  --stack-name <solution_stack_name> \
  --query "StackResources[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId" --output text
```

Layout under that bucket:

```
sraverify/reports/consolidated/
    sraverify-consolidated-<YYYYMMDD_HHMMSS>.csv   # every account, every check — one file
    sra-verify-dashboard.html                       # the static dashboard (from the tool's repo)
sraverify/reports/raw/
    sraverify_findings_<YYYYMMDD_HHMMSS>.csv        # one file per scan run (see naming note)
```

- **The consolidated CSV is the authoritative, complete artifact.** The buildspec builds it by
  reading every scan's output directory directly (`pandas.concat` over
  `/tmp/sraverify-results/**/sraverify*.csv`), so it contains all account types and all
  accounts from that run.
- **The `raw/` folder holds the per-scan CSVs**, named only by timestamp — not by account ID or
  account type. The account is a **column inside** each file, not part of the filename. The
  role-type scans (management, audit, log-archive) run sequentially and get distinct
  second-resolution timestamps; the application scans run in parallel in separate directories.
  Because `raw/` is a flat copy keyed on filename, two scans that happen to finish in the same
  wall-clock second would produce the same name and one would overwrite the other in `raw/`
  only. If `raw/` ever has fewer files than you expect, that is why — and it does not affect the
  consolidated CSV, which is built independently of the flat copy and keyed on directory. **Present from
  the consolidated CSV.**

Download without the dashboard:

```bash
aws s3 ls s3://<bucket>/sraverify/reports/consolidated/ --profile <audit_profile>
aws s3 cp s3://<bucket>/sraverify/reports/consolidated/<file>.csv . --profile <audit_profile>
```

## What a finding row contains

Each row is one check result. The columns (from the tool's output writer):

| Column | Meaning |
|---|---|
| `CheckId` | e.g. `SRA-GD-1`, `SRA-CT-1` — service abbreviation plus number |
| `Status` | `PASS`, `FAIL`, or `ERROR` |
| `Severity` | the check's severity |
| `AccountId` | the account the check ran against |
| `AccountType` | `management`, `audit`, `log-archive`, or `application` |
| `Service` | e.g. `GuardDuty`, `CloudTrail` |
| `Region` | region checked, or `global` |
| `Title`, `Description` | what the check verifies |
| `ResourceId`, `ResourceType` | the resource evaluated, when applicable |
| `CheckedValue`, `ActualValue` | expected vs observed |
| `Remediation` | the tool's remediation text |
| `CheckLogic` | how the check decided |

**`ERROR` is not `FAIL`.** An `ERROR` row means the check could not run — most often the tool
could not read something in that account. `FAIL` means the check ran and the control is not in
place. Separate the two when you present: `FAIL` is a finding to act on, `ERROR` is usually a
coverage or permission problem to fix so the check can run (see `references/troubleshooting.md`).

## The checks

As of the commit noted in `references/sraverify-deployment.md`, the tool ships **158 checks**,
distributed by the account type they run against:

| Account type | Checks | Notable content |
|---|---|---|
| application | 63 | per-account service posture (the largest set) |
| audit | 40 | the audit / Security Tooling account's SRA role |
| management | 40 | organization CloudTrail, delegated administrators, the SRA backbone |
| log-archive | 15 | the logging account's SRA role |

By service (largest first): GuardDuty 25, Security Lake 17, Shield 14, CloudTrail 13, Security
Hub 11, Inspector 11, Macie 10, Firewall Manager 10, WAF 9, Organizations 9, Config 9, Security
Incident Response 5, S3 4, IAM Access Analyzer 4, Account 3, Audit Manager 2, IAM 1, EC2 1.

The count is a property of the branch that was cloned (the tool is unpinned) — a run weeks later
may differ. The upstream README is explicit that SRA Verify "may not contain a check for every
consideration of the AWS SRA": absence of a `FAIL` is not proof the SRA is fully implemented.
List the exact checks a given run knows about with `sraverify --list-checks` (see
`references/troubleshooting.md` for running the CLI locally).

## The dashboard

`sra-verify-dashboard.html` is a **static** page that runs entirely in the browser — there is
no server. It reads the consolidated CSV that you hand it through a **presigned URL**. The
workshop flow:

1. In the S3 console, open `sra-verify-dashboard.html` from
   `sraverify/reports/consolidated/`.
2. At the same location, select the consolidated CSV, **Actions → Share with a presigned URL**,
   and set **1 minute** as the expiry.
3. Paste the URL into the dashboard's **Load URL** field. The browser fetches the CSV
   client-side and renders four sections: an overview (checks run, passed, failed), a mind map
   of accounts and services coloured by status, a "Key actions required" summary grouped by
   service, and a filterable detailed-findings table.

Because the dashboard is unpinned (it comes from the same clone as the tool), its layout can
change between runs.

## Generative-AI summary — and its data-handling risk

The dashboard's "Key actions required" section has a **Copy generative AI prompt** button. It
builds a markdown prompt that **embeds your organization's findings** — account IDs and service
configuration — and copies it to the clipboard for pasting into a model. The workshop uses the
Amazon Bedrock console's text playground with Claude Haiku 4.5, but any model works.

Raise the exposure plainly before the user does this, per rule 8 in `SKILL.md`:

- **The presigned URL is a time-limited credential.** Anyone who has it can download the CSV
  until it expires. That is why the workshop sets a 1-minute expiry and says never to share the
  URL. Do not paste it into anything but the dashboard, and do not put it somewhere it is logged.
- **The copied prompt contains real findings.** Account IDs and configuration detail leave the
  account the moment they are pasted into an external tool. The README says to consider the
  organization's security policies before pasting. If the user's policy forbids sending account
  data to a third-party model, read the CSV directly instead.
- Generative-AI output about security posture is non-deterministic and can be wrong — treat any
  remediation it proposes as a draft to verify against the raw findings and the AWS SRA
  guidance, not as authority.

## Repeated scans accumulate

Every build writes new timestamped files next to the existing ones — nothing is overwritten
across runs and nothing is pruned. Over time the bucket holds many consolidated and raw CSVs.
When reviewing, sort by the timestamp in the filename and read the **latest** consolidated CSV
unless comparing runs. The bucket is versioned and `Retain`, so it also keeps growing until
objects are removed deliberately (a gated write — see cleanup in
`references/sraverify-deployment.md`).

## Presenting findings

Do not paste the whole CSV back. Summarise the way the assessment is structured:

- **Lead with the SRA gaps, by account type.** The management-type failures (no organization
  CloudTrail, a service not delegated to the audit account, a missing SRA role) are the ones
  that matter most — they are organization-wide, not per-workload. Surface those first.
- **Group `FAIL` rows by service**, since remediation is per service (enable GuardDuty
  org-wide, delegate Security Hub administration, turn on Config aggregation).
- **Separate `ERROR` from `FAIL`.** A cluster of `ERROR` rows in one account almost always means
  that account is missing `SRAMemberRole` or the role lacks a permission the branch's checks
  need — a coverage problem to fix, not a security finding. Point it at
  `references/troubleshooting.md`.
- **State the coverage boundary.** Say which regions were scanned (`IncludeRegions`) and that
  anything outside them was not evaluated, and repeat the README caveat that the tool does not
  cover every SRA consideration. A clean run is "no gaps among the checks that ran in the
  scanned regions," not "the SRA is fully implemented."

## Feeding findings elsewhere

The output is plain CSV, so filtering to actionable findings is a one-liner — for example, the
`FAIL` rows for one service:

```bash
python3 - <<'PY'
import csv
with open('sraverify-consolidated-<timestamp>.csv') as f:
    for r in csv.DictReader(f):
        if r['Status'] == 'FAIL' and r['Service'] == 'GuardDuty':
            print(r['AccountId'], r['CheckId'], r['Title'])
PY
```

Unlike the sibling SATv2 solution, SRA Verify does **not** write to Security Hub or emit ASFF —
the member role is strictly read-only and cannot push findings anywhere (rule 7 in `SKILL.md`).
If the user wants these findings in Security Hub or a ticketing system, that is a separate
integration they build on top of the CSV; SRA Verify will not do it for them.

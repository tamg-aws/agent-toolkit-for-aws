# Continuum local remediation runtime

This additive plugin runtime captures a selected Continuum scan, freezes application and review contracts, supervises real isolated tests, and prepares a local PR artifact. The agent performs source inspection and proposes fixes; the runtime accounts for findings and binds evidence to exact bytes. It does not automatically accept a service's proposed patch.

The implemented slice covers intake, setup, issue/group planning, baseline and combined candidate validation, review, and read-only GitHub reconciliation. It does **not** create PRs, obtain exclusive publication ownership, merge, release, or reassess an environment. `prepare-pr` is not publication success. The map is a limited finding/local-issue/root-cause-group graph, not an application asset inventory.

## Run from an installed plugin

Use Python **3.11 or newer**, Git, and Docker with a running local daemon. The ordinary macOS `python3` may be too old. Offline workflow operations use the standard library; signed intake additionally requires the pinned boto3 dependency. `gh` authentication is needed only for GitHub readback.

```bash
PLUGIN_ROOT="/absolute/path/to/installed/aws-agents-for-devsecops"
RUNTIME="$PLUGIN_ROOT/runtime/continuum.py"
STATE="/absolute/canonical/path/outside-the-application/continuum-state"
APP="/absolute/path/to/application"

uv run --python 3.12 --with-requirements "$PLUGIN_ROOT/runtime/requirements-intake.txt" \
  python "$RUNTIME" --state "$STATE" intake \
  --profile delegated-admin --region us-east-1 --account 123456789012 \
  --environment ENVIRONMENT_ID --scan SCAN_ID
```

The first slice supports the fixed Continuum endpoint in `us-east-1`, account-checked SigV4 GET operations, complete paginated lists, selected finding/issue details, and a stable second read. It retains raw responses, request identifiers and at most three attempts for transient connection failures, HTTP 429 and selected 5xx responses. Permission, identity and inventory drift failures do not retry. A failed capture remains failed; a later successful capture does not replace its evidence. Two equal reads are not a transactional service snapshot.

For a prior export, use `import-export --file export.json` instead. The [example envelope](../examples/imported-export.json) is explicitly synthetic. Imported exports retain that evidence class and do not claim live completeness. Findings can reference service issues through `createdIssueId` or `duplicateOfIssueId`; issue references outside the selected scan remain visible. Continuum may already consolidate findings and propose an issue-level patch. Local groups address interactions across those issues, without treating shared membership as proof of one root cause.

## Freeze source, tests and plan

Adapt [application-contract.json](../examples/application-contract.json) and [change-plan.json](../examples/change-plan.json). Their placeholders must be replaced with actual image/source hashes and review evidence. The examples describe an invoice fixture, not a real service finding.

```bash
uv run --python 3.12 python "$RUNTIME" --state "$STATE" setup \
  --repo "$APP" --contract application-contract.json
# Copy the returned baseline hash into change-plan.json.
uv run --python 3.12 python "$RUNTIME" --state "$STATE" plan --file change-plan.json
uv run --python 3.12 python "$RUNTIME" --state "$STATE" map
uv run --python 3.12 python "$RUNTIME" --state "$STATE" run --repo "$APP" --phase baseline
```

The immutable contract pins allowed production paths, protected test files, an immutable trusted image, fixed command arrays and timeouts. Keep image dependency installation separate from application execution. The runtime never installs dependencies from the repository on the host. Supply an image with the needed runtime/tools already installed; image contents are trusted infrastructure.

Source binding levels are `unknown`, `repository_association`, or `independently_compared`. Planning can retain uncertainty. Execution requires an independent comparison of the exact local revision and relevant source evidence. An API repository association alone does not attest which Git revision was ingested. The runtime verifies consistency of the declared comparison, not its semantic truth.

Every selected finding has exactly one disposition, with rationale and evidence. Duplicate rows point directly to a canonical non-duplicate row. Selected findings map once to local issues and root-cause groups. Every group pair needs an explicit coupled, independent or unknown assessment. Independent reviewer names and free-text evidence are declared assertions; keep the actual independent invocation/review separately.

Each selected issue needs **one issue-specific negative check** with an exact failing baseline exit and literal diagnostic, plus a valid-behavior check. Shared valid controls are allowed. Build, lint, unit, integration and smoke gates must pass baseline. Keep intentionally red security regressions separate from ordinary green unit gates. An unrelated compiler failure, timeout, OOM or unstarted container cannot satisfy a negative test.

## Execute and review changes

Edit only the approved production paths. Keep both original tests and newly added protected regressions unchanged. Group runs can help isolate changes; all combined checks are mandatory.

```bash
uv run --python 3.12 python "$RUNTIME" --state "$STATE" run \
  --repo "$APP" --phase candidate --group GROUP_ID
uv run --python 3.12 python "$RUNTIME" --state "$STATE" run --repo "$APP" --phase candidate
uv run --python 3.12 python "$RUNTIME" --state "$STATE" candidate --repo "$APP"
uv run --python 3.12 python "$RUNTIME" --state "$STATE" review --repo "$APP" --file review.json
```

A candidate run returns exit 2 when an expectation fails. Use its actual logs for bounded correction. Candidate runs, including group runs, consume the contract's limit across plan versions. A changed plan requires its own passing baseline. An interrupted execution leaves an unresolved intent that blocks further runs and readiness; preserve it for investigation instead of resending or editing receipts.

`candidate` outputs the complete UTF-8 combined diff and exact snapshot/diff hashes. A review document contains:

```json
{
  "reviewer": "independent-reviewer",
  "verdict": "approved",
  "run": "SHA256_OF_LATEST_COMBINED_RUN_EVENT_OBJECT",
  "source": "SHA256_OF_EXACT_PASSING_SOURCE_SNAPSHOT",
  "diff_sha256": "SHA256_OF_COMPLETE_COMBINED_DIFF",
  "interaction_review": true,
  "rationale": "Actual independent source and interaction review evidence.",
  "residual_risk": "Remaining findings and deployment limitations."
}
```

Source additions and tracked deletions are supported within the allowed path set; symlinks, submodules, special files and mode changes are rejected. The supervisor copies stored source into Docker named volumes, then runs each fixed command with no network, a read-only root/source, an unprivileged user, dropped capabilities and resource limits. Explicit output directories use isolated writable named volumes. Host application directories, credentials, Docker socket and authoritative state are never mounted. Raw stdout/stderr, argv, image/configuration, process IDs and terminal container state are recorded by the host supervisor. Cleanup receipts are distinct from test success.

The host, Docker daemon and trusted image are the trust boundary. A malicious host user can rewrite local state; hash chains are consistency evidence, not signatures or a defense against the host administrator. No command imports model-authored successful execution receipts.

## Prepare and reconcile a PR

After review, any separately authorized commit must contain **every tested file and no additional files**. `prepare-pr` compares committed bytes with the passing snapshot. It records byte equality separately and does not claim tests ran again at the new commit.

```bash
uv run --python 3.12 --with-requirements "$PLUGIN_ROOT/runtime/requirements-intake.txt" \
  python "$RUNTIME" --state "$STATE" prepare-pr --repo "$APP" \
  --file pr-request.json --profile delegated-admin
uv run --python 3.12 python "$RUNTIME" --state "$STATE" reconcile-pr \
  --repository owner/repository --number 123
```

`pr-request.json` has reviewed nonempty `title`, `body` and `disclosure_review` strings. No provider write occurs. Missing or unknown fresh Continuum patch ownership policy yields `PUBLICATION_BLOCKED`; even a disabled policy yields `NEEDS_PROVIDER_OWNERSHIP_RECONCILIATION`. A policy read is evidence, not a distributed lock. Provider write/idempotency, in-flight ownership and publication recovery remain outside this slice.

GitHub reconciliation reads the PR twice around its checks, statuses, reviews and complete open-PR inventory. It reports the exact head/base, duplicate change markers, observed CI and merge state. A read can be `UNBOUND_OBSERVATION` when no local reviewed change matches. New runs or unresolved execution intents invalidate the local match. Required branch-protection policy remains `UNKNOWN`; observed successful checks never grant merge or publication permission. GitLab publication is unsupported.

## State and validation

`status` lists the append-only event chain. `object SHA256` reads a verified immutable object. State and evidence stay outside application snapshots. [state.schema.json](schemas/state.schema.json) documents the event envelope; `contracts.py` enforces cross-object application/plan controls at runtime.

```bash
uv run --python 3.12 python -m unittest discover -s "$PLUGIN_ROOT/tests" -v
uv run --python 3.12 --with ruff==0.14.2 ruff check "$PLUGIN_ROOT/runtime" "$PLUGIN_ROOT/tests"
```

Set `CONTINUUM_RUN_DOCKER_TESTS=1` and provide `CONTINUUM_TEST_IMAGE` as an existing immutable image ID to enable actual Docker tests. Synthetic service fixtures, live read-only intake, actual container execution and provider observations are separate evidence classes; none alone demonstrates a released remediation.

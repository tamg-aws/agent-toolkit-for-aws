# Public overlap demo

This synthetic invoice API demonstrates two distinct issues whose individually
passing changes break valid behavior when combined in the wrong order. It uses
no AWS account, real customer data, or external API. The app is intentionally
vulnerable at baseline; run it only through the isolated runtime.

Tenant authorization needs `tenant_id` from the domain record. Public-field
projection removes that field and the private processor token. Authorizing the
projected record denies valid callers. The repair authorizes the domain record
before projection. The protected tests exercise real HTTP requests over container
loopback, including concurrent valid requests.

## Initialize

Select a trusted Python 3.12 base image by registry digest for your architecture.
Build the small tool image before application execution; this image build needs
package-network access. Application checks later run with networking disabled.
A local image ID is valid only on the Docker daemon where it exists.

```bash
docker build --build-arg PYTHON_BASE=python@sha256:REVIEWED_BASE_DIGEST \
  -t continuum-overlap-tools ./examples/overlap-demo
docker image inspect continuum-overlap-tools --format '{{.Id}}'
DEMO="$(python3.12 -c 'from pathlib import Path; from tempfile import gettempdir; print(Path(gettempdir()).resolve() / "continuum-overlap-demo")')"
python3.12 examples/overlap-demo/demo.py init \
  --directory "$DEMO" --image sha256:REVIEWED_IMAGE_ID
```

Run commands from the plugin directory. Use a new canonical directory for each
demo. Initialization creates a local Git baseline, immutable source objects and
input templates. It does not execute the application, import AWS findings, or
approve a plan.

Review the generated inputs with a separate reviewer. Record actual developer
confirmation in `inputs/contract.json`. After comparing the controlled source,
set its `source_binding.level` to `independently_compared` and record the evidence.
In `inputs/plan.json`, record the actual reviewer, approved verdict, evidence and
interaction reviewer; set `source_binding_accepted` only after that review.
These identity fields are declarations, not authenticated reviewer identities.

```bash
python3.12 runtime/continuum.py --state "$DEMO/state" \
  import-export --file "$DEMO/inputs/export.json"
python3.12 runtime/continuum.py --state "$DEMO/state" \
  preflight --repo "$DEMO/app" --contract "$DEMO/inputs/contract.json"
python3.12 runtime/continuum.py --state "$DEMO/state" \
  setup --repo "$DEMO/app" --contract "$DEMO/inputs/contract.json"
python3.12 runtime/continuum.py --state "$DEMO/state" \
  plan --file "$DEMO/inputs/plan.json"
python3.12 runtime/continuum.py --state "$DEMO/state" \
  run --repo "$DEMO/app" --phase baseline
```

Baseline success means all eight expectations match: the two issue-specific
negative checks fail with their exact expected signatures, while ordinary build,
lint, unit, valid-behavior, integration and smoke checks pass.

## Exercise composition

Stage each variant using `demo.py stage --directory "$DEMO" --variant NAME`,
then run the corresponding command below. Staging changes only
the three known production files. Unknown source edits, test changes or changed
HEAD stop staging. It never resets a user's arbitrary changes.

| Variant | Runtime run flags | Expected result |
| --- | --- | --- |
| `group-a` | `--phase candidate --group authorization` | Seven checks pass |
| `group-b` | `--phase candidate --group projection` | Seven checks pass |
| `bad-composition` | `--phase candidate` | Both security checks pass; valid HTTP behavior, unit, integration and smoke fail; exit 2 |
| `repaired-composition` | `--phase candidate` | All eight checks pass, covering eleven protected test methods |

Use the same `runtime/continuum.py --state ... run --repo ...` prefix as baseline.
The six-run budget bounds candidate attempts. A failed combined run remains in
the evidence history; group successes do not override it.

After the repaired run, obtain the source and full diff with `candidate --repo`.
A separate reviewer must inspect the diff, protected test outcomes and interaction,
then provide `review --repo --file` with the exact run, source and diff hashes
(see the runtime guide). Export `review-package --repo --format markdown` to a
file beside the state `objects` directory for navigable relative evidence links.
The package is local review evidence. This demo does not publish a PR, merge,
deploy, or prove a live Continuum remediation.

#!/usr/bin/env python3
"""Direct CLI for the additive local Continuum remediation workflow."""

import sys

if sys.version_info < (3, 11):
    sys.exit(
        "Continuum runtime requires Python 3.11 or newer; select python3.11 or uv run --python 3.12."
    )

import argparse
from pathlib import Path

import intake
import provider
import source
import workflow
from store import Store, encoded, read_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state", required=True, help="Canonical directory outside the application"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    native = commands.add_parser(
        "intake", help="Read a complete selected scan through signed GETs"
    )
    native.add_argument("--profile", default="delegated-admin")
    native.add_argument("--region", default="us-east-1")
    for field in ("account", "environment", "scan"):
        native.add_argument("--" + field, required=True)
    imported = commands.add_parser(
        "import-export", help="Import a prior export without claiming live completeness"
    )
    imported.add_argument("--file", required=True)
    setup = commands.add_parser("setup")
    setup.add_argument("--repo", required=True)
    setup.add_argument("--contract", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--file", required=True)
    run = commands.add_parser("run")
    run.add_argument("--repo", required=True)
    run.add_argument("--phase", choices=("baseline", "candidate"), required=True)
    run.add_argument("--group")
    review = commands.add_parser("review")
    review.add_argument("--repo", required=True)
    review.add_argument("--file", required=True)
    current = commands.add_parser(
        "candidate", help="Snapshot current source and output the full review diff"
    )
    current.add_argument("--repo", required=True)
    ready = commands.add_parser(
        "prepare-pr", help="Create a guarded local artifact; never publish"
    )
    ready.add_argument("--repo", required=True)
    ready.add_argument(
        "--file", required=True, help="Reviewed title, body and disclosure_review"
    )
    ready.add_argument(
        "--profile",
        help="Optional fresh signed ownership read; omitted blocks publication",
    )
    reconcile = commands.add_parser(
        "reconcile-pr", help="Read actual GitHub PR/CI state; never publish"
    )
    reconcile.add_argument(
        "--repository", required=True, help="Exact GitHub owner/name"
    )
    reconcile.add_argument("--number", required=True, type=int)
    commands.add_parser(
        "map", help="Return the limited finding/issue/group interaction graph"
    )
    commands.add_parser("status")
    inspect = commands.add_parser("object", help="Read an immutable object by SHA256")
    inspect.add_argument("sha256")
    args = parser.parse_args(argv)
    try:
        store = Store(Path(args.state).absolute())
        with store.locked():
            command = args.command
            if command == "intake":
                reader = intake.SignedReader(
                    args.profile, args.region, args.account, args.environment
                )
                result = intake.capture(
                    store,
                    reader,
                    args.account,
                    args.region,
                    args.environment,
                    args.scan,
                )
            elif command == "import-export":
                result = intake.import_export(store, read_json(args.file))
            elif command == "setup":
                result = workflow.setup(store, args.repo, read_json(args.contract))
            elif command == "plan":
                result = workflow.freeze_plan(store, read_json(args.file))
            elif command == "run":
                result = workflow.run(store, args.repo, args.phase, args.group)
            elif command == "review":
                result = workflow.review(store, args.repo, read_json(args.file))
            elif command == "candidate":
                candidate, changed = workflow.current(store, args.repo)
                baseline = workflow.inputs(store)[2]
                diff = workflow.combined_diff(store, baseline, candidate)
                result = {
                    "source": store.save(candidate),
                    "tree_sha256": source.tree_digest(candidate),
                    "changed_paths": changed,
                    "diff_sha256": store.put(diff.encode()),
                    "diff": diff,
                }
            elif command == "prepare-pr":
                reader = None
                try:
                    if args.profile:
                        inventory = workflow.inputs(store)[1]
                        reader = intake.SignedReader(
                            args.profile,
                            inventory["region"],
                            inventory["account"],
                            inventory["environment_id"],
                        )
                    result = provider.prepare(
                        store, args.repo, read_json(args.file), reader
                    )
                finally:
                    if reader:
                        reader.close()
            elif command == "reconcile-pr":
                reader = provider.GitHubReader(args.repository)
                result = provider.reconcile(store, reader, args.repository, args.number)
            elif command == "map":
                result = workflow.application_map(store)
            elif command == "object":
                sys.stdout.buffer.write(store.raw(args.sha256))
                return 0
            else:
                result = {
                    "events": store.events(),
                    "state": str(store.root),
                    "publication": "readiness_only_no_provider_mutations",
                }
            sys.stdout.buffer.write(encoded(result))
            return 0 if command != "run" or result["passed"] else 2
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"STOPPED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

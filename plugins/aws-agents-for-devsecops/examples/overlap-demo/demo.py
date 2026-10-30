"""Initialize or stage the public synthetic fixture; never execute the app."""

import sys

if sys.version_info < (3, 11):
    sys.exit("The demo requires Python 3.11 or newer.")

import argparse
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "runtime"))

import source  # noqa: E402 -- locate the sibling runtime without installing a package
from store import Store, encoded, read_json, require  # noqa: E402


def fixture_files(variant: str) -> dict[str, bytes]:
    variants = read_json(HERE / "variants.json")
    require(variant in variants, "Unknown fixture variant")
    files = {
        str(path.relative_to(HERE / "app")): path.read_bytes()
        for path in sorted((HERE / "app").rglob("*"))
        if path.is_file()
    }
    require(
        not any(path.is_symlink() for path in (HERE / "app").rglob("*")),
        "Fixture symlinks unsupported",
    )
    files.update(
        {name: content.encode() for name, content in variants[variant].items()}
    )
    return files


def git(directory: Path, *args: str) -> bytes:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Continuum Synthetic Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-C",
            str(directory),
            *args,
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    require(
        result.returncode == 0,
        "Fixture Git operation failed: " + result.stderr.decode(errors="replace"),
    )
    return result.stdout


def initialize(directory: str, image: str) -> dict:
    root = Path(directory).absolute()
    require(
        root.resolve() == root and not root.exists(),
        "Use a new canonical demo directory",
    )
    require(
        re.fullmatch(
            r"(?:sha256:[a-f0-9]{64}|[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64})", image
        ),
        "Provide a reviewed immutable Docker image",
    )
    app = root / "app"
    app.mkdir(parents=True)
    for name, data in fixture_files("baseline").items():
        path = app / source.relative(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    git(app, "init", "--initial-branch=fixture")
    git(app, "add", "--all")
    git(app, "commit", "--no-verify", "-m", "Record synthetic vulnerable baseline")
    state = Store(root / "state")
    baseline = source.snapshot(state, str(app))
    contract = read_json(HERE.parent / "application-contract.json")
    contract["image"] = image
    contract["source_binding"]["revision"] = baseline["revision"]
    contract["source_binding"]["level"] = "unknown"
    contract["source_binding"]["evidence"] = (
        "Synthetic fixture generated locally; independent source comparison is pending."
    )
    contract["developer_confirmation"] = ""
    plan = read_json(HERE.parent / "change-plan.json")
    plan["baseline_snapshot"] = state.save(baseline)
    plan["review"] = {"reviewer": "", "verdict": "pending", "evidence": ""}
    plan["source_binding_accepted"] = False
    for interaction in plan["interactions"]:
        interaction["reviewer"] = ""
    inputs = root / "inputs"
    inputs.mkdir()
    for name, value in (
        ("contract.json", contract),
        ("plan.json", plan),
        ("export.json", read_json(HERE.parent / "imported-export.json")),
    ):
        (inputs / name).write_bytes(encoded(value))
    receipt = {
        "schema_version": "synthetic-demo-v1",
        "app": str(app),
        "state": str(state.root),
        "baseline": state.save(baseline),
        "evidence_class": "synthetic_fixture_not_aws_findings",
        "review_status": "PENDING_ACTUAL_REVIEW",
        "next": "Review inputs, record developer confirmation and exact source comparison, then import/setup/plan using continuum.py. No application was executed.",
    }
    (root / "demo.json").write_bytes(encoded(receipt))
    return receipt


def stage(directory: str, variant: str) -> dict:
    root = Path(directory).resolve(strict=True)
    receipt = read_json(root / "demo.json")
    app = root / "app"
    require(
        receipt["app"] == str(app)
        and receipt["state"] == str(root / "state")
        and receipt["schema_version"] == "synthetic-demo-v1",
        "Demo directory binding differs",
    )
    store = Store(root / "state")
    snapshot = source.snapshot(store, str(app))
    baseline = store.get(receipt["baseline"])
    require(snapshot["revision"] == baseline["revision"], "Demo HEAD changed")
    actual = {
        name: store.raw(value["sha256"]) for name, value in snapshot["files"].items()
    }
    variants = read_json(HERE / "variants.json")
    require(
        any(actual == fixture_files(name) for name in variants),
        "Demo has unknown source/test edits; preserve them and use a new demo directory",
    )
    require(
        all(
            value["mode"] == baseline["files"][name]["mode"]
            for name, value in snapshot["files"].items()
        ),
        "Demo file mode changed",
    )
    next_files = fixture_files(variant)
    changed = [name for name in actual if actual[name] != next_files[name]]
    require(
        set(changed) <= set(variants["baseline"]),
        "Only known fixture production paths may change",
    )
    for name in changed:
        (app / source.relative(name)).write_bytes(next_files[name])
    return {
        "variant": variant,
        "changed_paths": changed,
        "source": store.save(source.snapshot(store, str(app))),
        "authority": "fixture_staging_only_no_review_or_execution",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--directory", required=True)
    init.add_argument("--image", required=True)
    change = commands.add_parser("stage")
    change.add_argument("--directory", required=True)
    change.add_argument(
        "--variant", choices=tuple(read_json(HERE / "variants.json")), required=True
    )
    args = parser.parse_args(argv)
    try:
        result = (
            initialize(args.directory, args.image)
            if args.command == "init"
            else stage(args.directory, args.variant)
        )
        sys.stdout.buffer.write(encoded(result))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        subprocess.TimeoutExpired,
    ) as error:
        print("STOPPED: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

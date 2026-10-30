"""Read-only local prerequisites; never execute application commands."""

import shutil
import subprocess
import sys

import contracts
import source
from store import strict_json


def check(store, repository: str, contract: dict | None = None) -> dict:
    checks = []

    def record(name, passed, detail, action):
        checks.append(
            {
                "check": name,
                "passed": passed,
                "detail": detail,
                "next_action": "" if passed else action,
            }
        )

    record(
        "python",
        sys.version_info >= (3, 11),
        sys.version.split()[0],
        "Select Python 3.11 or newer.",
    )
    snapshot = None
    try:
        snapshot = source.snapshot(store, repository)
        record("source_and_external_state", True, store.save(snapshot), "")
    except (ValueError, OSError) as error:
        record(
            "source_and_external_state",
            False,
            str(error),
            "Use a Git repository root and a canonical state directory outside it; remove unsafe source paths.",
        )
    valid_contract = False
    if contract is not None:
        try:
            if snapshot is None:
                raise ValueError("Source preflight failed")
            contracts.contract(contract, snapshot, store.value("inventory"))
            valid_contract = True
            record("contract", True, store.save(contract), "")
        except (ValueError, OSError, KeyError, TypeError) as error:
            record(
                "contract",
                False,
                str(error),
                "Review contract fields against the selected inventory and current source.",
            )
    if shutil.which("docker") is None:
        record(
            "docker",
            False,
            "Docker executable unavailable",
            "Install Docker and start its daemon.",
        )
    else:
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                timeout=30,
            )
            record(
                "docker",
                result.returncode == 0,
                (result.stdout if result.returncode == 0 else result.stderr).decode(
                    errors="replace"
                )[:4096],
                "Start the local Docker daemon; no host-execution fallback exists.",
            )
            if valid_contract and result.returncode == 0:
                image = subprocess.run(
                    ["docker", "image", "inspect", contract["image"]],
                    capture_output=True,
                    timeout=30,
                )
                values = strict_json(image.stdout) if image.returncode == 0 else []
                usable = len(values) == 1 and not values[0].get("Config", {}).get(
                    "Volumes"
                )
                record(
                    "pinned_image",
                    usable,
                    values[0].get("Id", "")
                    if values
                    else image.stderr.decode(errors="replace")[:4096],
                    "Build or pull the reviewed immutable image beforehand; it must not declare volumes.",
                )
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            record(
                "docker",
                False,
                str(error),
                "Repair Docker availability and retry preflight.",
            )
    return {
        "schema_version": "preflight-v1",
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
        "contract_checked": valid_contract,
        "authority": "prerequisites_only_no_setup_execution_or_publication",
        "limitations": [
            "No cloud credentials or permissions are tested.",
            "Image presence does not establish image trust or application compatibility.",
            "This does not execute baseline tests or grant plan approval.",
        ],
    }

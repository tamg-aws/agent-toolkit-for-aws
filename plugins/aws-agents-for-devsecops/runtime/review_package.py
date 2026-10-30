"""An exact-source local review package, without publication authority."""

import knowledge
import provider
import source
import workflow
from store import require, sha


def prepare(store, repository: str) -> dict:
    settings, inventory, baseline, app, plan = workflow.active(store)
    require(
        settings["inventory"] == store.latest("inventory")["object"],
        "Active inventory changed",
    )
    candidate, changed = workflow.current(store, repository)
    review_key = store.latest("review")["object"]
    review = store.get(review_key)
    require(
        review["plan"] == store.latest("plan")["object"]
        and provider.current_execution(store, review["run"]),
        "Review is stale or an execution intent remains unresolved",
    )
    run = store.get(review["run"])
    workflow.verify_run(store, run)
    require(
        run["phase"] == "candidate"
        and run["passed"]
        and not run.get("group")
        and run["plan"] == review["plan"]
        and run["setup"] == store.latest("setup")["object"],
        "A passing combined candidate run is required",
    )
    require(
        store.save(candidate) == run["source_after"] == review["source"],
        "Current source or checkout revision differs from reviewed run",
    )
    diff = workflow.combined_diff(store, baseline, candidate).encode()
    require(sha(diff) == review["diff_sha256"], "Reviewed complete diff differs")
    require(
        review["verdict"] == "approved" and review["interaction_review"] is True,
        "Combined interaction review is required",
    )
    graph = knowledge.application_map(store, repository)
    groups = {group["id"]: group for group in plan["groups"]}
    remaining, batches = set(groups), []
    while remaining:
        ready = sorted(
            key for key in remaining if not set(groups[key]["depends_on"]) & remaining
        )
        require(ready, "Group dependency cycle")
        batches.append(ready)
        remaining -= set(ready)
    historical = []
    for event in store.events():
        if event["kind"] != "run":
            continue
        previous = store.get(event["object"])
        if previous["plan"] == review["plan"]:
            if previous["source_before"] != previous["source_after"]:
                require(
                    previous["passed"] is False
                    and previous["evidence_class"] == "supervised_container_execution",
                    "Historical source-drift run cannot claim success",
                )
                store.get(previous["source_before"])
                store.get(previous["source_after"])
                for check in previous["checks"]:
                    store.raw(check["stdout"])
                    store.raw(check["stderr"])
                    store.get(check["image_receipt"])
                verification = "failed_source_drift_retained"
            else:
                workflow.verify_run(store, previous)
                verification = "fixed_check_receipts_replayed"
            historical.append(
                {
                    "run": event["object"],
                    "phase": previous["phase"],
                    "group": previous.get("group"),
                    "passed": previous["passed"],
                    "source_before": previous["source_before"],
                    "source": previous["source_after"],
                    "verification": verification,
                    "evidence_use": "history_only_no_success_authority",
                }
            )
    result = {
        "schema_version": "local-review-package-v1",
        "status": "LOCAL_REVIEW_ONLY",
        "inventory": settings["inventory"],
        "setup": store.latest("setup")["object"],
        "plan": review["plan"],
        "review": review_key,
        "run": review["run"],
        "baseline": settings["baseline"],
        "source": run["source_after"],
        "source_tree_sha256": source.tree_digest(candidate),
        "diff_sha256": store.put(diff),
        "changed_paths": changed,
        "accounting": plan["findings"],
        "issues": plan["issues"],
        "groups": plan["groups"],
        "dependency_batches": batches,
        "order_claim": "Deterministic topological batches of the reviewed dependencies, not an independently inferred risk ranking or permission to merge.",
        "interactions": plan["interactions"],
        "group_and_baseline_runs": historical,
        "checks": [
            {
                "id": item["check"]["id"],
                "cause": item["cause"],
                "exit_code": item["exit_code"],
                "stdout": item["stdout"],
                "stderr": item["stderr"],
                "expectation_met": item["expectation_met"],
            }
            for item in run["checks"]
        ],
        "residual_risk": review["residual_risk"],
        "map": graph,
        "counts": {
            "findings": len(inventory["findings"]),
            "service_issues": len(inventory["issues"]),
            "local_issues": len(plan["issues"]),
            "fix_groups": len(groups),
        },
        "limitations": [
            "Reviewer identities and semantic judgments are declared assertions.",
            "Dependencies and interactions are review inputs, not automated semantic analysis.",
            "No PR publication, merge, deployment, or service reassessment is performed.",
            "A later commit requires a separate byte-equality check; these tests ran at the recorded revision.",
        ],
    }
    store.append("review_package", result)
    return result


def markdown(value: dict) -> str:
    safe = knowledge.safe
    lines = [
        "# Local remediation review package",
        "",
        "Status: LOCAL REVIEW ONLY",
        "",
        "## Review scope",
        "",
    ]
    lines.extend(
        "- " + safe(key) + ": " + str(count) for key, count in value["counts"].items()
    )
    lines += ["", "### Changed paths", ""]
    lines.extend("- " + safe(path) for path in value["changed_paths"])
    lines += ["", "### Complete finding accounting", ""]
    lines.extend(
        "- "
        + safe(item["finding_id"])
        + ": "
        + safe(item["disposition"])
        + "; "
        + safe(item["reason"])
        for item in value["accounting"]
    )
    lines += [
        "",
        "## Exact evidence",
        "",
    ]
    for key in (
        "inventory",
        "plan",
        "review",
        "run",
        "source",
        "baseline",
        "diff_sha256",
    ):
        lines.append(
            "- " + safe(key) + ": [" + value[key] + "](objects/" + value[key] + ")"
        )
    lines += ["", "## Reviewed dependency batches", "", safe(value["order_claim"]), ""]
    lines.extend(
        f"{index}. " + ", ".join(safe(group) for group in batch)
        for index, batch in enumerate(value["dependency_batches"], 1)
    )
    lines += ["", "## Interactions", ""]
    lines.extend("- " + safe(edge) for edge in value["interactions"])
    lines += ["", "## Retained run history", ""]
    lines.extend(
        "- ["
        + item["run"]
        + "](objects/"
        + item["run"]
        + "): "
        + safe(item["phase"])
        + "; passed="
        + str(item["passed"])
        + "; "
        + safe(item["verification"])
        + "; history only, no success authority"
        for item in value["group_and_baseline_runs"]
    )
    lines += ["", "## Fixed checks", ""]
    lines.extend(
        "- "
        + safe(item["id"])
        + ": exit "
        + str(item["exit_code"])
        + "; "
        + safe(item["cause"])
        for item in value["checks"]
    )
    lines += [
        "",
        "## Residual risk",
        "",
        safe(value["residual_risk"]),
        "",
        "## Limits",
        "",
    ]
    lines.extend("- " + safe(item) for item in value["limitations"])
    lines += ["", knowledge.markdown(value["map"])]
    return "\n".join(lines) + "\n"

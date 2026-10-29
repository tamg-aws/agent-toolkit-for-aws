"""Application setup, full accounting, supervised gates, review and graph."""

import difflib
import subprocess
from pathlib import Path

import contracts
import executor
import source
from store import VERSION, encoded, now, require, sha


def setup(store, repository: str, value: dict) -> dict:
    require(
        not any(e["kind"] == "setup" for e in store.events()),
        "Setup is immutable; use a new state",
    )
    inventory = store.value("inventory")
    baseline = source.snapshot(store, repository)
    contracts.contract(value, baseline, inventory)
    result = {
        "contract": store.save(value),
        "baseline": store.save(baseline),
        "inventory": store.latest("inventory")["object"],
        "repository": str(Path(repository).resolve()),
    }
    store.append("setup", result)
    return result


def inputs(store):
    settings = store.value("setup")
    inventory = store.get(settings["inventory"])
    baseline = store.get(settings["baseline"])
    app = store.get(settings["contract"])
    contracts.contract(app, baseline, inventory)
    return settings, inventory, baseline, app


def freeze_plan(store, value: dict) -> dict:
    settings, inventory, baseline, app = inputs(store)
    contracts.plan(value, inventory, app, settings["baseline"])
    previous = [e for e in store.events() if e["kind"] == "plan"]
    if previous and store.get(previous[-1]["object"])["plan"] == store.save(value):
        return store.get(previous[-1]["object"])
    result = {
        "plan": store.save(value),
        "version": len(previous) + 1,
        "setup": store.latest("setup")["object"],
        "previous": previous[-1]["object"] if previous else None,
    }
    store.append("plan", result)
    return result


def active(store):
    settings, inventory, baseline, app = inputs(store)
    record = store.value("plan")
    require(record["setup"] == store.latest("setup")["object"], "Plan setup drift")
    value = store.get(record["plan"])
    contracts.plan(value, inventory, app, settings["baseline"])
    return settings, inventory, baseline, app, value


def current(store, repository: str) -> tuple[dict, list[str]]:
    settings, inventory, baseline, app, plan = active(store)
    candidate = source.snapshot(store, repository)
    changed = source.changes(baseline, candidate)
    require(
        set(changed) <= set(app["allowed_paths"]),
        "Candidate changed unapproved/protected files",
    )
    for path in app["protected_paths"]:
        require(
            candidate["files"].get(path) == baseline["files"].get(path),
            "Protected test changed",
        )
    for path in changed:
        if path in baseline["files"] and path in candidate["files"]:
            require(
                candidate["files"][path]["mode"] == baseline["files"][path]["mode"],
                "File mode changes unsupported",
            )
    return candidate, changed


def verify_run(store, record: dict) -> None:
    require(
        record["evidence_class"] == "supervised_container_execution",
        "Not supervisor evidence",
    )
    store.get(record["source_before"])
    store.get(record["source_after"])
    require(
        record["source_before"] == record["source_after"],
        "Source changed during execution",
    )
    app = store.get(store.get(record["setup"])["contract"])
    expected_checks = app["checks"]
    if record.get("group"):
        value = store.get(store.get(record["plan"])["plan"])
        issue_ids = {
            i["id"] for i in value["issues"] if i["group_id"] == record["group"]
        }
        expected_checks = [
            c
            for c in expected_checks
            if c["kind"] not in ("negative", "valid") or set(c["issue_ids"]) & issue_ids
        ]
    require(
        [c["check"] for c in record["checks"]] == expected_checks,
        "Fixed check sequence differs",
    )
    for check in record["checks"]:
        for field in ("stdout", "stderr"):
            store.raw(check[field])
        store.get(check["image_receipt"])
        require(
            check["evidence_class"] == "supervised_container_execution",
            "Imported check receipt",
        )
        expected = (
            check["check"].get("expected_baseline_exit", 0)
            if record["phase"] == "baseline"
            else 0
        )
        matched = check["cause"] == "exited" and check["exit_code"] == expected
        if record["phase"] == "baseline" and check["check"]["kind"] == "negative":
            logs = store.raw(check["stdout"]) + store.raw(check["stderr"])
            matched = matched and check["check"]["baseline_signature"].encode() in logs
        require(
            check["expected_exit"] == expected and check["expectation_met"] == matched,
            "Check receipt outcome mismatch",
        )
    require(
        record["passed"] == all(c["expectation_met"] for c in record["checks"]),
        "Run outcome mismatch",
    )


def run(store, repository: str, phase: str, group: str | None = None) -> dict:
    settings, inventory, baseline, app, plan = active(store)
    require(
        app["source_binding"]["level"] == "independently_compared",
        "Execution requires reviewed exact source comparison; association alone permits triage only",
    )
    require(phase in ("baseline", "candidate"), "Invalid execution phase")
    candidate, changed = current(store, repository)
    require(
        phase != "baseline" or candidate == baseline, "Baseline source/revision changed"
    )
    previous = [store.get(e["object"]) for e in store.events() if e["kind"] == "run"]
    intents = [
        store.get(e["object"]) for e in store.events() if e["kind"] == "run_intent"
    ]
    completed_ids = {record["intent"] for record in previous}
    require(
        all(intent["id"] in completed_ids for intent in intents),
        "Unresolved execution intent; preserve state and investigate before a new run",
    )
    if phase == "candidate":
        baseline_runs = [
            r
            for r in previous
            if r["phase"] == "baseline"
            and r["passed"]
            and r["plan"] == store.latest("plan")["object"]
            and not r.get("group")
        ]
        require(baseline_runs, "Complete baseline proof required for this plan version")
        verify_run(store, baseline_runs[-1])
        used = sum(i["phase"] == "candidate" for i in intents)
        require(
            used < app["max_candidate_runs"],
            "Candidate run budget exhausted across plan versions",
        )
    checks = app["checks"]
    if group:
        require(
            phase == "candidate" and group in {g["id"] for g in plan["groups"]},
            "Unknown group or non-candidate group run",
        )
        issue_ids = {i["id"] for i in plan["issues"] if i["group_id"] == group}
        paths = {
            p for i in plan["issues"] if i["group_id"] == group for p in i["paths"]
        }
        require(set(changed) <= paths, "Group-only candidate changes other group paths")
        checks = [
            c
            for c in checks
            if c["kind"] not in ("negative", "valid") or set(c["issue_ids"]) & issue_ids
        ]
    before = store.save(candidate)
    intent = {
        "id": sha(
            encoded({"events": len(store.events()), "source": before, "phase": phase})
        ),
        "phase": phase,
        "group": group,
        "source": before,
        "plan": store.latest("plan")["object"],
        "setup": store.latest("setup")["object"],
        "started_at": now(),
    }
    store.append("run_intent", intent)
    try:
        checks_result = executor.run_checks(store, app, candidate, phase, checks)
        after = store.save(source.snapshot(store, repository))
        result = {
            "schema_version": VERSION,
            "intent": intent["id"],
            "phase": phase,
            "group": group,
            "plan": intent["plan"],
            "setup": intent["setup"],
            "source_before": before,
            "source_after": after,
            "changed_paths": changed,
            "checks": checks_result,
            "evidence_class": "supervised_container_execution",
            "passed": before == after
            and all(c["expectation_met"] for c in checks_result),
            "completed_at": now(),
        }
    except (ValueError, OSError, TimeoutError, subprocess.TimeoutExpired) as error:
        store.append(
            "run_error", {"intent": intent, "error": str(error), "recorded_at": now()}
        )
        raise
    store.append("run", result)
    return result


def combined_diff(store, baseline: dict, candidate: dict) -> str:
    lines = []
    for path in source.changes(baseline, candidate):
        old = (
            store.raw(baseline["files"][path]["sha256"]).decode("utf-8")
            if path in baseline["files"]
            else ""
        )
        new = (
            store.raw(candidate["files"][path]["sha256"]).decode("utf-8")
            if path in candidate["files"]
            else ""
        )
        lines.extend(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile="a/" + path,
                tofile="b/" + path,
            )
        )
    return "".join(lines)


def review(store, repository: str, value: dict) -> dict:
    settings, inventory, baseline, app, plan = active(store)
    candidate, changed = current(store, repository)
    run_event = store.latest("run")
    run_record = store.get(run_event["object"])
    verify_run(store, run_record)
    require(
        run_record["phase"] == "candidate"
        and run_record["passed"]
        and not run_record.get("group")
        and run_record["plan"] == store.latest("plan")["object"],
        "Latest run must pass all combined candidate checks for current plan",
    )
    require(
        run_record["source_after"] == store.save(candidate),
        "Review source differs from tested source",
    )
    require(
        value.get("run") == run_event["object"]
        and value.get("source") == store.save(candidate),
        "Review must bind exact run and candidate snapshot",
    )
    require(
        value.get("verdict") == "approved"
        and value.get("reviewer")
        and value["reviewer"] not in (plan["author"], app["author"]),
        "Independent approved combined review required",
    )
    contracts.text(value.get("rationale"), "combined review rationale")
    contracts.text(value.get("residual_risk"), "residual risk assessment")
    diff_key = store.put(combined_diff(store, baseline, candidate).encode())
    require(
        value.get("diff_sha256") == diff_key, "Review must bind complete combined diff"
    )
    require(
        value.get("interaction_review") is True,
        "Combined interaction review is required",
    )
    result = dict(value, plan=store.latest("plan")["object"], changed_paths=changed)
    store.append("review", result)
    return result


def application_map(store) -> dict:
    settings, inventory, baseline, app, plan = active(store)
    nodes = [
        {
            "id": "finding:" + key,
            "type": "finding",
            "service_payload": store.save(value),
        }
        for key, value in inventory["findings"].items()
    ]
    nodes += [
        {
            "id": "issue:" + i["id"],
            "type": "local_issue",
            "evidence": i["source_evidence"],
        }
        for i in plan["issues"]
    ]
    nodes += [
        {
            "id": "group:" + g["id"],
            "type": "root_cause_group",
            "rationale": g["rationale"],
        }
        for g in plan["groups"]
    ]
    edges = [
        {
            "from": "finding:" + f,
            "to": "issue:" + i["id"],
            "type": "reviewed_membership",
        }
        for i in plan["issues"]
        for f in i["finding_ids"]
    ]
    edges += [
        {
            "from": "issue:" + i["id"],
            "to": "group:" + i["group_id"],
            "type": "reviewed_root_cause",
            "evidence": i["root_cause"],
        }
        for i in plan["issues"]
    ]
    edges += [
        {**e, "from": "group:" + e["from"], "to": "group:" + e["to"]}
        for e in plan["interactions"]
    ]
    return {
        "schema_version": "application-map-v1",
        "plan": store.latest("plan")["object"],
        "nodes": nodes,
        "edges": edges,
        "review": plan["review"],
        "source_binding": app["source_binding"],
        "counts": {
            "findings": len(inventory["findings"]),
            "service_issues": len(inventory["issues"]),
            "local_issues": len(plan["issues"]),
            "groups": len(plan["groups"]),
        },
    }

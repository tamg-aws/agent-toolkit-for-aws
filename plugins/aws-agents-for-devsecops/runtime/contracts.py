"""Structural controls; semantic judgments remain attributable review records."""

import re

from source import relative
from store import identifier, require

KINDS = {"negative", "valid", "build", "lint", "unit", "integration", "smoke"}
DISPOSITIONS = {
    "selected",
    "false_positive",
    "duplicate",
    "deferred",
    "out_of_scope",
    "already_fixed",
    "not_reproducible",
}


def text(value, label):
    require(isinstance(value, str) and value.strip(), f"Missing {label}")
    return value


def contract(value: dict, baseline: dict, inventory: dict) -> dict:
    require(
        value.get("schema_version") == "application-contract-v1",
        "Unknown contract version",
    )
    for field in (
        "author",
        "developer_confirmation",
        "repository",
        "source_binding",
        "allowed_paths",
        "protected_paths",
        "checks",
        "image",
        "output_directories",
    ):
        require(field in value, f"Contract missing {field}")
    text(value["author"], "contract author")
    text(value["developer_confirmation"], "developer confirmation")
    repository = value["repository"]
    require(
        repository.get("provider") == "github"
        and re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository.get("name", "")
        ),
        "MVP repository identity requires GitHub owner/name",
    )
    binding = value["source_binding"]
    require(
        binding.get("revision") == baseline["revision"]
        and binding.get("environment_id") == inventory["environment_id"]
        and binding.get("scan_id") == inventory["scan_id"],
        "Source binding identity mismatch",
    )
    require(
        binding.get("level")
        in {"independently_compared", "repository_association", "unknown"},
        "Unsupported source binding level",
    )
    text(binding.get("evidence"), "source binding evidence")
    require(
        re.fullmatch(r"(?:[A-Za-z0-9._/:-]+@)?sha256:[a-f0-9]{64}", value["image"]),
        "Use an immutable Docker image digest or local sha256 image ID",
    )
    require(
        type(value.get("max_candidate_runs")) is int
        and 1 <= value["max_candidate_runs"] <= 10,
        "Set max_candidate_runs between 1 and 10",
    )
    for field in ("allowed_paths", "protected_paths", "output_directories"):
        paths = value[field]
        require(
            isinstance(paths, list) and len(paths) == len(set(paths)),
            f"Invalid {field}",
        )
        for path in paths:
            relative(path)
    require(
        value["allowed_paths"] and value["protected_paths"],
        "Explicit source/test scope required",
    )
    require(
        not set(value["allowed_paths"]) & set(value["protected_paths"]),
        "Protected files cannot be writable",
    )
    require(
        set(value["protected_paths"]) <= baseline["files"].keys(),
        "Protected file missing",
    )
    for output in value["output_directories"]:
        require(
            "," not in output
            and all(ord(char) >= 32 and ord(char) != 127 for char in output),
            "Output directory contains Docker mount delimiters/control characters",
        )
        require(
            not any(
                path == output or path.startswith(output + "/")
                for path in baseline["files"]
            ),
            "Output directory would hide source/tests",
        )
    environment = value.get("environment", {})
    require(
        isinstance(environment, dict)
        and all(
            re.fullmatch(r"[A-Z][A-Z0-9_]*", key)
            and isinstance(val, str)
            and not any(
                word in key
                for word in (
                    "AWS",
                    "TOKEN",
                    "SECRET",
                    "PASSWORD",
                    "CREDENTIAL",
                    "SSH",
                    "DOCKER",
                )
            )
            for key, val in environment.items()
        ),
        "Only non-secret explicit test environment is allowed",
    )
    checks = value["checks"]
    require(isinstance(checks, list) and checks, "No fixed checks")
    ids = set()
    for check in checks:
        key = identifier(check["id"])
        require(key not in ids, "Duplicate check ID")
        ids.add(key)
        require(check.get("kind") in KINDS, "Unknown check kind")
        require(
            isinstance(check.get("argv"), list)
            and check["argv"]
            and all(isinstance(arg, str) and "\0" not in arg for arg in check["argv"]),
            "Fixed argv array required",
        )
        cwd = check.get("cwd")
        require(isinstance(cwd, str), "Fixed working directory required")
        if cwd != ".":
            relative(cwd)
        require(
            type(check.get("timeout_seconds")) is int
            and 1 <= check["timeout_seconds"] <= 3600,
            "Invalid timeout",
        )
        require(
            isinstance(check.get("issue_ids"), list),
            "Explicit check issue IDs required",
        )
        expected = check.get("expected_baseline_exit", 0)
        require(type(expected) is int and 0 <= expected <= 125, "Invalid baseline exit")
        if check["kind"] == "negative":
            require(
                expected > 0 and len(check["issue_ids"]) == 1,
                "Negative check needs exactly one issue and exact red exit",
            )
            text(
                check.get("baseline_signature"),
                "literal expected security failure diagnostic",
            )
        else:
            require(expected == 0, "Valid controls and gates must pass baseline")
    require(
        {"build", "lint", "unit", "integration", "smoke"}
        <= {c["kind"] for c in checks},
        "Build, lint, unit, integration and smoke checks are required",
    )
    return value


def plan(value: dict, inventory: dict, app: dict, baseline_key: str) -> dict:
    require(value.get("schema_version") == "change-plan-v1", "Unknown plan version")
    require(
        value.get("baseline_snapshot") == baseline_key,
        "Plan baseline snapshot mismatch",
    )
    author = text(value.get("author"), "plan author")
    reviewer = value.get("review", {})
    require(
        text(reviewer.get("reviewer"), "independent plan reviewer") != author
        and reviewer.get("verdict") == "approved",
        "Independent approved plan review required",
    )
    text(reviewer.get("evidence"), "plan review evidence")
    require(
        value.get("source_binding_accepted") is True,
        "Reviewer must assess source-binding uncertainty",
    )
    rows = value.get("findings")
    require(isinstance(rows, list), "Complete finding accounting required")
    ids = [row.get("finding_id") for row in rows]
    require(
        len(set(ids)) == len(ids) and set(ids) == set(inventory["findings"]),
        "Plan must account for every selected-scan finding exactly once",
    )
    groups = value.get("groups")
    issues = value.get("issues")
    require(
        isinstance(groups, list) and groups and isinstance(issues, list) and issues,
        "Issues and root-cause groups required",
    )
    group_ids = [identifier(group["id"]) for group in groups]
    issue_ids = [identifier(issue["id"]) for issue in issues]
    require(
        len(set(group_ids)) == len(group_ids) and len(set(issue_ids)) == len(issue_ids),
        "Duplicate group or issue IDs",
    )
    selected = set()
    by_finding = {row["finding_id"]: row for row in rows}
    for row in rows:
        require(row.get("disposition") in DISPOSITIONS, "Unknown finding disposition")
        text(row.get("reason"), "finding disposition rationale")
        text(row.get("evidence"), "finding evidence")
        if row["disposition"] == "selected":
            require(
                row.get("issue_id") in issue_ids, "Selected finding has no local issue"
            )
            selected.add(row["finding_id"])
        if row["disposition"] == "duplicate":
            require(
                row.get("duplicate_of") in inventory["findings"]
                and row["duplicate_of"] != row["finding_id"]
                and by_finding[row["duplicate_of"]].get("disposition") != "duplicate",
                "Duplicate must point directly to a non-duplicate canonical finding",
            )
    require(selected, "No supported in-scope remediations selected")
    assigned = []
    for issue in issues:
        require(issue.get("group_id") in group_ids, "Issue group missing")
        members = issue.get("finding_ids")
        require(
            isinstance(members, list) and members and len(set(members)) == len(members),
            "Issue needs unique selected findings",
        )
        assigned.extend(members)
        require(
            all(
                row.get("issue_id") == issue["id"]
                for row in rows
                if row["finding_id"] in members
            ),
            "Issue/finding mapping differs",
        )
        for field in ("root_cause", "source_evidence", "behavior"):
            text(issue.get(field), f"issue {field}")
        require(
            set(issue.get("paths", [])) <= set(app["allowed_paths"])
            and issue.get("paths"),
            "Issue paths outside approved scope",
        )
        for kind in ("negative", "valid"):
            require(
                any(
                    c["kind"] == kind and issue["id"] in c["issue_ids"]
                    for c in app["checks"]
                ),
                f"Issue {issue['id']} has no {kind} check",
            )
    require(
        len(set(assigned)) == len(assigned) and set(assigned) == selected,
        "Selected findings must belong to exactly one issue",
    )
    dependencies = {}
    for group in groups:
        text(group.get("rationale"), "group root-cause rationale")
        deps = group.get("depends_on")
        require(
            isinstance(deps, list)
            and set(deps) <= set(group_ids)
            and group["id"] not in deps,
            "Invalid group dependencies",
        )
        dependencies[group["id"]] = deps
    visited, active = set(), set()

    def visit(group):
        require(group not in active, "Group dependency cycle")
        if group not in visited:
            active.add(group)
            for dependency in dependencies[group]:
                visit(dependency)
            active.remove(group)
            visited.add(group)

    for group in group_ids:
        visit(group)
    edges = value.get("interactions")
    require(isinstance(edges, list), "Explicit interaction review required")
    expected = {tuple(sorted((a, b))) for a in group_ids for b in group_ids if a < b}
    actual = []
    for edge in edges:
        pair = tuple(sorted((edge.get("from"), edge.get("to"))))
        require(
            pair in expected
            and edge.get("verdict") in {"coupled", "independent", "unknown"},
            "Invalid interaction edge",
        )
        text(edge.get("reason"), "interaction rationale")
        text(edge.get("evidence"), "interaction evidence")
        require(
            edge.get("reviewer") == reviewer["reviewer"],
            "Interaction review identity differs",
        )
        actual.append(pair)
    require(
        len(set(actual)) == len(actual) and set(actual) == expected,
        "Every group pair requires an interaction assessment",
    )
    return value

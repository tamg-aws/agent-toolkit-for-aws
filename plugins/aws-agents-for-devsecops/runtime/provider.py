"""Guarded local PR artifact and read-only GitHub reconciliation."""

import http.client
import re
import subprocess
from pathlib import Path
from urllib.parse import urlencode

import contracts
import source
import workflow
from store import encoded, now, require, sha, strict_json


def current_execution(store, run_key: str) -> bool:
    events = store.events()
    runs = [e for e in events if e["kind"] == "run"]
    intents = [store.get(e["object"]) for e in events if e["kind"] == "run_intent"]
    completed = {store.get(e["object"])["intent"] for e in runs}
    return (
        bool(runs and intents)
        and runs[-1]["object"] == run_key
        and all(intent["id"] in completed for intent in intents)
        and intents[-1]["id"] == store.get(run_key)["intent"]
    )


def committed_files(store, repository: str) -> tuple[str, dict]:
    repo = Path(repository).resolve(strict=True)
    revision = source.git(repo, "rev-parse", "HEAD").decode().strip()
    records = source.git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0")
    files = {}
    for record in records:
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, object_id = header.decode().split()
        path = source.relative(name.decode("utf-8"))
        require(
            kind == "blob" and mode in ("100644", "100755"),
            "Committed symlinks/submodules/special files are unsupported",
        )
        data = source.git(repo, "cat-file", "blob", object_id)
        files[path] = {"sha256": store.put(data), "bytes": len(data), "mode": mode[-3:]}
    return revision, files


def prepare(store, repository: str, request: dict, policy_reader=None) -> dict:
    settings, inventory, baseline, app, plan = workflow.active(store)
    require(
        app["source_binding"]["level"] == "independently_compared",
        "Publication readiness requires exact reviewed source comparison",
    )
    candidate, changed = workflow.current(store, repository)
    review_event = store.latest("review")
    review = store.get(review_event["object"])
    require(
        review["plan"] == store.latest("plan")["object"]
        and review["run"] == store.latest("run")["object"],
        "Review is stale for the current plan/run",
    )
    record = store.get(review["run"])
    require(
        current_execution(store, review["run"]),
        "Execution intent is unresolved or newer than the reviewed run",
    )
    workflow.verify_run(store, record)
    tested = store.get(record["source_after"])
    require(
        record["passed"]
        and record["phase"] == "candidate"
        and not record.get("group")
        and review["source"] == record["source_after"]
        and candidate["files"] == tested["files"],
        "Current files differ from approved passing source",
    )
    diff = workflow.combined_diff(store, baseline, candidate).encode()
    require(review["diff_sha256"] == sha(diff), "Approved full diff differs")
    head, files = committed_files(store, repository)
    require(
        files == tested["files"],
        "Commit must contain every tested file and no untested files",
    )
    require(
        head != baseline["revision"] and changed, "No committed remediation changes"
    )
    for field in ("title", "body", "disclosure_review"):
        contracts.text(request.get(field), "PR " + field)
    require(
        len(request["title"]) <= 256 and len(request["body"].encode()) <= 64000,
        "PR text exceeds bounds",
    )
    policy_receipt = None
    policy = "UNKNOWN"
    if policy_reader is not None:
        path = "/environments/" + inventory["environment_id"]
        response = policy_reader(path)
        policy_receipt = store.save(response)
        require(
            response["path"] == path
            and response["http_status"] == 200
            and strict_json(response["raw"].encode()) == response["body"],
            "Fresh ownership read failed",
        )
        environment = response["body"]
        expected_arn = (
            f"arn:aws:continuum:{inventory['region']}:{inventory['account']}:"
            f"environments/{inventory['environment_id']}"
        )
        require(
            environment.get("environmentId") == inventory["environment_id"]
            and environment.get("environmentArn") == expected_arn,
            "Ownership environment differs",
        )
        policy = (
            environment.get("configuration", {})
            .get("codeConfiguration", {})
            .get("environmentConfiguration", {})
            .get("patchCreationPolicy", "UNKNOWN")
        )
    identity = sha(
        encoded(
            {
                "repository": app["repository"],
                "baseline": settings["baseline"],
                "issue_ids": sorted(issue["id"] for issue in plan["issues"]),
            }
        )
    )
    marker = "<!-- continuum-change:" + identity + " -->"
    result = {
        "schema_version": "pr-readiness-v1",
        "change_id": identity,
        "repository": app["repository"],
        "head_sha": head,
        "base_sha": baseline["revision"],
        "plan": store.latest("plan")["object"],
        "review": review_event["object"],
        "run": review["run"],
        "tested_source": record["source_after"],
        "commit_byte_equality": {
            "tested_revision": tested["revision"],
            "commit": head,
            "files_sha256": source.tree_digest(tested),
            "claim": "Identical files; checks were not rerun at the new commit.",
        },
        "diff_sha256": store.put(diff),
        "changed_paths": changed,
        "title": request["title"],
        "body": request["body"] + "\n\n" + marker,
        "disclosure_review": request["disclosure_review"],
        "policy": policy,
        "policy_receipt": policy_receipt,
        "status": (
            "NEEDS_PROVIDER_OWNERSHIP_RECONCILIATION"
            if policy == "DISABLED"
            else "PUBLICATION_BLOCKED"
        ),
        "limitations": [
            "No provider write is implemented; no PR was created.",
            "Existing PR/in-flight ownership must be reconciled before any publication.",
            "Policy readback is evidence, not a distributed lock.",
            "Independent reviewer identity and semantic judgments are declared assertions.",
            "CI, merge, release and service reassessment remain separate evidence.",
        ],
        "created_at": now(),
    }
    store.append("pr_ready", result)
    return result


class GitHubReader:
    """Uses existing gh authentication only against the fixed GitHub API host."""

    def __init__(self, repository: str):
        require(
            re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository),
            "Invalid GitHub owner/name",
        )
        self.repository = repository
        token = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com"],
            capture_output=True,
            timeout=30,
        )
        require(
            token.returncode == 0,
            "Authenticate gh for github.com before provider readback",
        )
        self.token = token.stdout.decode().strip()
        require(self.token and "\n" not in self.token, "Invalid GitHub authentication")

    def __call__(self, path: str) -> dict:
        base = "/repos/" + self.repository
        require(
            re.fullmatch(
                re.escape(base) + r"/(?:pulls(?:/[0-9]+(?:/reviews)?)?"
                r"|commits/[a-f0-9]{40,64}/(?:check-runs|status))"
                r"(?:\?[A-Za-z0-9_=&-]+)?",
                path,
            ),
            "GitHub read outside the exact repository allowlist",
        )
        connection = http.client.HTTPSConnection("api.github.com", timeout=60)
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Authorization": "Bearer " + self.token,
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "continuum-local",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response = connection.getresponse()
            data = response.read(16 * 1024 * 1024 + 1)
            require(len(data) <= 16 * 1024 * 1024, "Provider response exceeds limit")
            return {
                "path": path,
                "http_status": response.status,
                "raw": data.decode(),
                "body": strict_json(data) if response.status == 200 else None,
                "request_id": response.getheader("x-github-request-id"),
                "link": response.getheader("link"),
                "captured_at": now(),
            }
        finally:
            connection.close()


def reconcile(store, reader, repository: str, number: int) -> dict:
    require(
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository),
        "Invalid repository",
    )
    require(type(number) is int and number > 0, "Invalid PR number")
    base = "/repos/" + repository
    receipts = []

    def get(path):
        response = reader(path)
        receipts.append(store.save(response))
        require(
            response["path"] == path
            and response["http_status"] == 200
            and strict_json(response["raw"].encode()) == response["body"],
            "Provider read failed or response/request binding differs",
        )
        return response["body"], response.get("link") or ""

    def pages(route, field=None, extra=None):
        values, seen = [], set()
        for page in range(1, 1001):
            query = dict(extra or {}, per_page=100, page=page)
            body, link = get(base + route + "?" + urlencode(query))
            items = body[field] if field else body
            require(isinstance(items, list), "Missing provider page records")
            for item in items:
                require(
                    item.get("id") not in seen and item.get("id") is not None,
                    "Repeated or missing provider record ID",
                )
                seen.add(item["id"])
                values.append(item)
            if 'rel="next"' not in link:
                return values
        raise ValueError("Provider pagination bound exceeded")

    pull, _ = get(base + f"/pulls/{number}")
    require(
        pull.get("number") == number
        and pull.get("base", {}).get("repo", {}).get("full_name", "").lower()
        == repository.lower(),
        "PR repository/number differs",
    )
    head, base_sha = pull["head"]["sha"], pull["base"]["sha"]
    require(re.fullmatch(r"[a-f0-9]{40,64}", head), "Invalid provider head SHA")
    checks = pages(f"/commits/{head}/check-runs", "check_runs")
    status, _ = get(base + f"/commits/{head}/status")
    require(status.get("sha") == head, "Commit status head differs")
    require(
        all(item.get("head_sha") == head for item in checks), "Check run head differs"
    )
    reviews = pages(f"/pulls/{number}/reviews")
    open_prs = pages("/pulls", extra={"state": "open"})
    # A second read detects provider head/base movement during the observation.
    final, _ = get(base + f"/pulls/{number}")
    require(
        (
            final["head"]["sha"],
            final["base"]["sha"],
            final.get("state"),
            final.get("merged"),
        )
        == (head, base_sha, pull.get("state"), pull.get("merged")),
        "PR changed during readback",
    )
    ready_events = [event for event in store.events() if event["kind"] == "pr_ready"]
    ready = store.get(ready_events[-1]["object"]) if ready_events else None
    binding = "UNBOUND_OBSERVATION"
    duplicates = []
    if ready:
        marker = "<!-- continuum-change:" + ready["change_id"] + " -->"
        duplicates = [
            item["number"] for item in open_prs if marker in (item.get("body") or "")
        ]
        current_plan = store.latest("plan")["object"]
        current_review = store.latest("review")["object"]
        if (
            ready["repository"]["name"].lower() == repository.lower()
            and ready["head_sha"] == head
            and ready["base_sha"] == base_sha
            and ready["plan"] == current_plan
            and ready["review"] == current_review
            and current_execution(store, ready["run"])
            and marker in (pull.get("body") or "")
        ):
            binding = "MATCHED_REVIEWED_CHANGE"
    status_total = status.get("total_count")
    statuses = status.get("statuses", [])
    complete_statuses = type(status_total) is int and status_total == len(statuses)
    ci_success = (
        bool(checks or statuses)
        and complete_statuses
        and all(
            c.get("status") == "completed" and c.get("conclusion") == "success"
            for c in checks
        )
        and (not statuses or status.get("state") == "success")
    )
    result = {
        "schema_version": "pr-observation-v1",
        "evidence_class": "provider_readback",
        "repository": repository,
        "number": number,
        "head_sha": head,
        "base_sha": base_sha,
        "binding": binding,
        "state": pull.get("state"),
        "merged": pull.get("merged"),
        "merge_commit_sha": pull.get("merge_commit_sha"),
        "reviews": reviews,
        "observed_ci": "SUCCESS" if ci_success else "NOT_PROVEN",
        "required_checks_policy": "UNKNOWN",
        "duplicate_change_prs": duplicates,
        "publication_permission": "NOT_GRANTED_BY_RECONCILIATION",
        "receipts": receipts,
        "observed_at": now(),
        "limitations": [
            "Observed checks are not proof that branch protection requirements passed.",
            "An unbound observation does not validate a local candidate.",
            "No merge, release, or reassessment is performed.",
        ],
    }
    store.append("pr_observation", result)
    return result

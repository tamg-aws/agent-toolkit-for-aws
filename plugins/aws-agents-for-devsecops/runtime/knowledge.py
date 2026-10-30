"""Source citations and attributed application knowledge; no execution authority."""

import source
import triage
from store import digest, encoded, identifier, require, sha
from triage import fields, text


def optional(store, kind: str):
    events = [event for event in store.events() if event["kind"] == kind]
    return events[-1] if events else None


def inventory_graph(store) -> dict:
    inventory_key = store.latest("inventory")["object"]
    inventory = store.get(inventory_key)
    nodes = [
        {"id": "finding:" + key, "kind": "finding", "payload": store.save(value)}
        for key, value in sorted(inventory["findings"].items())
    ]
    nodes += [
        {
            "id": "service_issue:" + key,
            "kind": "service_issue",
            "payload": store.save(value),
        }
        for key, value in sorted(inventory["issues"].items())
    ]
    edges = []
    for key, finding in sorted(inventory["findings"].items()):
        for field in ("createdIssueId", "duplicateOfIssueId"):
            target = finding.get(field)
            if target in inventory["issues"]:
                edges.append(
                    {
                        "from": "finding:" + key,
                        "to": "service_issue:" + target,
                        "relationship": field,
                        "evidence_class": "service_reported",
                    }
                )
    result = {"inventory": inventory_key, "nodes": nodes, "edges": edges}
    if optional(store, "triage"):
        key, document = triage.current(store)
        result["triage"] = key
        for group in document["advisory_groups"]:
            node = "advisory:" + group["id"]
            nodes.append(
                {
                    "id": node,
                    "kind": "advisory_group",
                    "label": group["hypothesis"],
                    "uncertainty": group["uncertainty"],
                }
            )
            edges.extend(
                {
                    "from": "finding:" + finding,
                    "to": node,
                    "relationship": "advisory_membership",
                    "evidence_class": "declared_assessment",
                }
                for finding in group["finding_ids"]
            )
    if optional(store, "plan"):
        import workflow

        settings, _, _, _, plan = workflow.active(store)
        require(
            settings["inventory"] == inventory_key, "Active plan inventory is stale"
        )
        result["plan"] = store.latest("plan")["object"]
        nodes.extend(
            {
                "id": "issue:" + item["id"],
                "kind": "local_issue",
                "label": item["root_cause"],
            }
            for item in plan["issues"]
        )
        nodes.extend(
            {
                "id": "group:" + item["id"],
                "kind": "reviewed_fix_group",
                "label": item["rationale"],
            }
            for item in plan["groups"]
        )
        edges.extend(
            {
                "from": "finding:" + finding,
                "to": "issue:" + item["id"],
                "relationship": "reviewed_membership",
                "evidence_class": "declared_assessment",
            }
            for item in plan["issues"]
            for finding in item["finding_ids"]
        )
        edges.extend(
            {
                "from": "issue:" + item["id"],
                "to": "group:" + item["group_id"],
                "relationship": "reviewed_root_cause",
                "evidence_class": "declared_assessment",
            }
            for item in plan["issues"]
        )
        edges.extend(
            {
                **edge,
                "from": "group:" + edge["from"],
                "to": "group:" + edge["to"],
                "evidence_class": "declared_assessment",
            }
            for edge in plan["interactions"]
        )
    return result


def validate(store, value: dict, snapshot: dict, graph: dict) -> None:
    fields(
        value,
        {
            "schema_version",
            "inventory",
            "revision",
            "author",
            "citations",
            "nodes",
            "edges",
        },
    )
    require(value["schema_version"] == "knowledge-v1", "Unknown knowledge schema")
    require(
        digest(value["inventory"]) == graph["inventory"], "Knowledge inventory differs"
    )
    require(value["revision"] == snapshot["revision"], "Knowledge revision differs")
    text(value["author"], "knowledge author", 128)
    require(
        all(isinstance(value[key], list) for key in ("citations", "nodes", "edges")),
        "Knowledge collections must be lists",
    )
    citations = set()
    for citation in value["citations"]:
        fields(
            citation,
            {"id", "path", "start_line", "end_line", "file_sha256", "quote_sha256"},
        )
        key = identifier(citation["id"])
        require(key not in citations, "Duplicate citation ID")
        citations.add(key)
        path = source.relative(citation["path"])
        require(path in snapshot["files"], "Citation file missing from pinned source")
        metadata = snapshot["files"][path]
        require(
            digest(citation["file_sha256"]) == metadata["sha256"],
            "Citation file hash differs",
        )
        data = store.raw(metadata["sha256"])
        data.decode("utf-8")
        lines = data.splitlines(keepends=True)
        start, end = citation["start_line"], citation["end_line"]
        require(
            type(start) is int
            and type(end) is int
            and 1 <= start <= end <= len(lines)
            and end - start < 200,
            "Invalid or oversized citation span",
        )
        require(
            digest(citation["quote_sha256"]) == sha(b"".join(lines[start - 1 : end])),
            "Citation span hash differs",
        )
    ids = {node["id"] for node in graph["nodes"]}
    for node in value["nodes"]:
        fields(node, {"id", "kind", "label", "citation_ids"})
        require(node["kind"] in ("component", "asset"), "Unknown application node kind")
        key = node["kind"] + ":" + identifier(node["id"])
        require(key not in ids, "Duplicate application node")
        ids.add(key)
        text(node["label"], "node label", 512)
        require(
            isinstance(node["citation_ids"], list)
            and node["citation_ids"]
            and len(set(node["citation_ids"])) == len(node["citation_ids"])
            and set(node["citation_ids"]) <= citations,
            "Node citations missing or unknown",
        )
    edge_ids = set()
    for edge in value["edges"]:
        fields(edge, {"id", "from", "to", "relationship", "citation_ids", "assessment"})
        key = identifier(edge["id"])
        require(key not in edge_ids, "Duplicate knowledge edge ID")
        edge_ids.add(key)
        require(edge["from"] in ids and edge["to"] in ids, "Unknown edge endpoint")
        require(
            edge["relationship"]
            in (
                "calls",
                "reads",
                "writes",
                "depends_on",
                "contains",
                "protects",
                "affects",
            ),
            "Unknown source relationship",
        )
        require(
            isinstance(edge["citation_ids"], list)
            and edge["citation_ids"]
            and len(set(edge["citation_ids"])) == len(edge["citation_ids"])
            and set(edge["citation_ids"]) <= citations,
            "Edge citations missing or unknown",
        )
        assessment = edge["assessment"]
        fields(assessment, {"reviewer", "verdict", "reason"})
        text(assessment["reviewer"], "edge reviewer", 128)
        require(
            assessment["reviewer"] != value["author"]
            and assessment["verdict"] in ("supported", "unknown", "disputed"),
            "Separate attributed semantic review required",
        )
        text(assessment["reason"], "edge assessment")
    require(len(encoded(value)) <= 4 * 1024 * 1024, "Knowledge document exceeds limit")


def freeze(store, repository: str, value: dict) -> dict:
    snapshot = source.snapshot(store, repository)
    graph = inventory_graph(store)
    validate(store, value, snapshot, graph)
    document, source_key = store.save(value), store.save(snapshot)
    previous = optional(store, "knowledge")
    if previous:
        old = store.get(previous["object"])
        if (
            old["document"] == document
            and old["source"] == source_key
            and old["inventory"] == graph["inventory"]
            and old.get("triage") == graph.get("triage")
            and old.get("plan") == graph.get("plan")
        ):
            return old
    result = {
        "schema_version": "knowledge-checkpoint-v1",
        "document": document,
        "source": source_key,
        "inventory": graph["inventory"],
        "triage": graph.get("triage"),
        "plan": graph.get("plan"),
        "previous": previous["object"] if previous else None,
        "authority": "advisory_only_no_execution_or_publication",
        "claim": "Exact file/span bytes at the recorded checkout revision; semantic judgments are attributed assertions, not authenticated or mechanically proven.",
    }
    store.append("knowledge", result)
    return result


def application_map(store, repository: str | None = None) -> dict:
    graph = inventory_graph(store)
    graph.update(
        schema_version="source-map-v1",
        citations=[],
        source_freshness="no_source_knowledge",
        semantic_claim="Review assertions do not establish security truth or runtime/deployment behavior.",
    )
    event = optional(store, "knowledge")
    if not event:
        return graph
    record = store.get(event["object"])
    require(
        record["inventory"] == graph["inventory"]
        and record.get("triage") == graph.get("triage")
        and record.get("plan") == graph.get("plan"),
        "Knowledge context is stale; re-review it",
    )
    document, snapshot = store.get(record["document"]), store.get(record["source"])
    validate(store, document, snapshot, graph)
    if repository is not None:
        require(
            source.snapshot(store, repository) == snapshot, "Knowledge source is stale"
        )
    graph.update(
        knowledge=event["object"],
        source=record["source"],
        revision=snapshot["revision"],
        source_freshness="current_bytes_verified"
        if repository
        else "recorded_bytes_only_current_tree_unchecked",
    )
    graph["nodes"].extend(
        {**node, "id": node["kind"] + ":" + node["id"]} for node in document["nodes"]
    )
    graph["edges"].extend(
        {**edge, "evidence_class": "source_anchored_semantic_assertion"}
        for edge in document["edges"]
    )
    graph["citations"] = [
        {**citation, "object_path": "objects/" + citation["file_sha256"]}
        for citation in document["citations"]
    ]
    return graph


def safe(value: object) -> str:
    """Render untrusted labels as inert text, never caller-authored Markdown."""
    return "".join(
        char if char.isalnum() or char == " " else f"&#{ord(char)};"
        for char in str(value)
    )


def markdown(value: dict) -> str:
    lines = [
        "# Source and assessment map",
        "",
        "Source status: " + safe(value["source_freshness"]),
        "",
        safe(value["semantic_claim"]),
        "",
        "## Nodes",
        "",
    ]
    for node in value["nodes"]:
        line = "- " + safe(node["id"]) + ": " + safe(node.get("label", node["kind"]))
        if node.get("uncertainty"):
            line += "; uncertainty: " + safe(node["uncertainty"])
        if node.get("citation_ids"):
            line += "; citations: " + ", ".join(
                safe(key) for key in node["citation_ids"]
            )
        lines.append(line)
    lines += ["", "## Relationships", ""]
    for edge in value["edges"]:
        assessment = edge.get("assessment", {})
        lines.append(
            "- "
            + safe(edge["from"])
            + " → "
            + safe(edge["to"])
            + ": "
            + safe(edge.get("relationship", edge.get("kind", "interaction")))
            + "; "
            + safe(
                assessment.get("verdict", edge.get("verdict", edge["evidence_class"]))
            )
            + "; "
            + safe(assessment.get("reason", edge.get("reason", "")))
            + (
                "; citations: " + ", ".join(safe(key) for key in edge["citation_ids"])
                if edge.get("citation_ids")
                else ""
            )
        )
    lines += [
        "",
        "## Immutable source citations",
        "",
        "Save this Markdown beside the state objects directory for relative links. Span hashes bind the listed line range; the linked object contains the complete file.",
        "",
    ]
    for citation in value["citations"]:
        # Both destination and fragment are generated from validated hashes/integers.
        lines.append(
            f"- [{safe(citation['id'])}](objects/{digest(citation['file_sha256'])}) "
            + safe(citation["path"])
            + f" lines {citation['start_line']}–{citation['end_line']}; span "
            + safe(citation["quote_sha256"])
        )
    return "\n".join(lines) + "\n"

"""Lossless advisory accounting, deliberately separate from execution plans."""

from collections import Counter

from store import digest, encoded, identifier, require


def fields(value: dict, required: set, optional: set = frozenset()) -> None:
    require(
        isinstance(value, dict)
        and required <= value.keys()
        and value.keys() <= required | optional,
        "Missing or unknown advisory fields",
    )


def text(value: str, label: str, limit: int = 16000) -> str:
    require(
        isinstance(value, str) and value.strip() and len(value) <= limit,
        f"Invalid {label}",
    )
    return value


def validate(value: dict, inventory: dict, inventory_key: str) -> None:
    fields(
        value,
        {
            "schema_version",
            "inventory",
            "author",
            "review",
            "findings",
            "advisory_groups",
        },
        {"original_document"},
    )
    require(value["schema_version"] == "triage-v1", "Unknown triage version")
    require(digest(value["inventory"]) == inventory_key, "Triage inventory mismatch")
    author = text(value["author"], "triage author", 128)
    review = value["review"]
    fields(review, {"reviewer", "verdict", "evidence"})
    require(
        text(review["reviewer"], "triage reviewer", 128) != author
        and review["verdict"] == "reviewed",
        "Attributed independent triage review required",
    )
    text(review["evidence"], "triage review evidence")
    rows = value["findings"]
    require(isinstance(rows, list), "Triage findings must be a list")
    by_id = {}
    for row in rows:
        fields(
            row,
            {"finding_id", "disposition", "reason", "evidence"},
            {"duplicate_of", "original_record"},
        )
        key = row["finding_id"]
        require(
            key in inventory["findings"] and key not in by_id,
            "Unknown/duplicate finding",
        )
        text(row["disposition"], "original disposition", 128)
        text(row["reason"], "triage reason")
        text(row["evidence"], "triage evidence")
        if "original_record" in row:
            require(
                isinstance(row["original_record"], dict),
                "Original record must be an object",
            )
        by_id[key] = row
    require(set(by_id) == set(inventory["findings"]), "Incomplete finding accounting")
    for row in rows:
        if row["disposition"] == "duplicate" or "duplicate_of" in row:
            target = row.get("duplicate_of")
            require(
                target in by_id
                and target != row["finding_id"]
                and by_id[target]["disposition"] != "duplicate"
                and "duplicate_of" not in by_id[target],
                "Duplicate must reference a direct canonical finding",
            )
    groups = value["advisory_groups"]
    require(isinstance(groups, list), "Advisory groups must be a list")
    group_ids = set()
    for group in groups:
        fields(group, {"id", "finding_ids", "hypothesis", "evidence", "uncertainty"})
        key = identifier(group["id"])
        require(key not in group_ids, "Duplicate advisory group")
        group_ids.add(key)
        members = group["finding_ids"]
        require(
            isinstance(members, list)
            and members
            and len(set(members)) == len(members)
            and set(members) <= set(by_id),
            "Advisory group has invalid finding membership",
        )
        for field in ("hypothesis", "evidence", "uncertainty"):
            text(group[field], "advisory " + field)
    if "original_document" in value:
        require(
            isinstance(value["original_document"], dict),
            "Original document must be an object",
        )
    require(len(encoded(value)) <= 16 * 1024 * 1024, "Triage document exceeds 16 MiB")


def freeze(store, value: dict) -> dict:
    inventory_key = store.latest("inventory")["object"]
    validate(value, store.get(inventory_key), inventory_key)
    document = store.save(value)
    previous = [event for event in store.events() if event["kind"] == "triage"]
    if previous and store.get(previous[-1]["object"])["document"] == document:
        return store.get(previous[-1]["object"])
    result = {
        "schema_version": "triage-checkpoint-v1",
        "inventory": inventory_key,
        "document": document,
        "previous": previous[-1]["object"] if previous else None,
        "dispositions": dict(Counter(row["disposition"] for row in value["findings"])),
        "advisory_group_count": len(value["advisory_groups"]),
        "authority": "advisory_only_no_setup_plan_execution_or_publication",
        "review_claim": "Attributed assessment; reviewer identity and semantic truth are not authenticated.",
    }
    store.append("triage", result)
    return result


def current(store) -> tuple[str, dict]:
    event = store.latest("triage")
    record = store.get(event["object"])
    inventory_key = store.latest("inventory")["object"]
    require(
        record["inventory"] == inventory_key, "Triage is stale for current inventory"
    )
    value = store.get(record["document"])
    validate(value, store.get(inventory_key), inventory_key)
    return event["object"], value

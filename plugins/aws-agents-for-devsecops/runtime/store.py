"""Local immutable evidence objects and append-only workflow events."""

import contextlib
import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION = "continuum-local-v1"
KINDS = {
    "inventory",
    "capture_failed",
    "setup",
    "plan",
    "run_intent",
    "run_error",
    "check",
    "container_cleanup",
    "run",
    "review",
    "pr_ready",
    "pr_observation",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    ).encode()


def strict_json(data: bytes) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path: str | Path) -> object:
    return strict_json(Path(path).read_bytes())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: str) -> str:
    require(
        isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value),
        "Invalid SHA256",
    )
    return value


def identifier(value: str) -> str:
    require(
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value),
        "Invalid local identifier",
    )
    return value


def write_once(path: Path, data: bytes) -> None:
    require(not path.is_symlink(), "Receipt path is a symlink")
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        require(path.read_bytes() == data, f"Immutable file differs: {path}")


class Store:
    def __init__(self, root: str | Path):
        raw = Path(root).absolute()
        require(
            not raw.is_symlink() and raw.resolve() == raw,
            "State path must be canonical",
        )
        self.root = raw
        raw.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(raw, 0o700)
        for name in ("objects", "events"):
            path = raw / name
            require(not path.is_symlink(), "State directory is a symlink")
            path.mkdir(exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def locked(self):
        path = self.root / ".lock"
        require(not path.is_symlink(), "Lock is a symlink")
        with path.open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield self

    def put(self, data: bytes) -> str:
        key = sha(data)
        write_once(self.root / "objects" / key, data)
        return key

    def save(self, value: object) -> str:
        return self.put(encoded(value))

    def raw(self, key: str) -> bytes:
        path = self.root / "objects" / digest(key)
        require(not path.is_symlink(), "Evidence object is a symlink")
        data = path.read_bytes()
        require(sha(data) == key, "Evidence object hash mismatch")
        return data

    def get(self, key: str) -> object:
        return strict_json(self.raw(key))

    def events(self) -> list[dict]:
        events = []
        previous = None
        for index, path in enumerate(sorted((self.root / "events").iterdir())):
            require(
                path.name == f"{index:06d}.json" and not path.is_symlink(),
                "Event sequence is incomplete",
            )
            data = path.read_bytes()
            event = strict_json(data)
            require(
                isinstance(event, dict)
                and event.get("schema_version") == VERSION
                and event.get("kind") in KINDS
                and type(event.get("sequence")) is int
                and isinstance(event.get("recorded_at"), str),
                "Unknown or invalid event schema",
            )
            require(
                event["sequence"] == index and event["previous"] == previous,
                "Event chain mismatch",
            )
            self.raw(event["object"])
            events.append(event)
            previous = sha(data)
        return events

    def append(self, kind: str, value: object) -> dict:
        require(kind in KINDS, "Unknown event kind")
        events = self.events()
        key = self.save(value)
        previous = sha(encoded(events[-1])) if events else None
        event = {
            "schema_version": VERSION,
            "sequence": len(events),
            "previous": previous,
            "kind": kind,
            "object": key,
            "recorded_at": now(),
        }
        write_once(self.root / "events" / f"{len(events):06d}.json", encoded(event))
        return event

    def latest(self, kind: str) -> dict:
        found = [event for event in self.events() if event["kind"] == kind]
        require(bool(found), f"No {kind} record")
        return found[-1]

    def value(self, kind: str) -> dict:
        return self.get(self.latest(kind)["object"])

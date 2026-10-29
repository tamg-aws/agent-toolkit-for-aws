"""Pin exact application bytes without running repository programs."""

import io
import os
import re
import stat
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

from store import require, sha


def relative(value: str) -> str:
    require(
        isinstance(value, str)
        and value
        and "\\" not in value
        and "\0" not in value
        and "\n" not in value,
        "Invalid source path",
    )
    path = PurePosixPath(value)
    require(
        not path.is_absolute()
        and all(part not in ("", ".", "..", ".git") for part in value.split("/")),
        "Unsafe source path",
    )
    return value


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(repo),
            *args,
        ],
        capture_output=True,
        check=False,
    )
    require(
        result.returncode == 0,
        "Git read failed: " + result.stderr.decode(errors="replace"),
    )
    return result.stdout


def snapshot(store, repository: str) -> dict:
    repo = Path(repository).resolve(strict=True)
    require(
        repo.is_dir()
        and repo != store.root
        and repo not in store.root.parents
        and store.root not in repo.parents,
        "Authoritative state must be outside the application",
    )
    require(
        Path(os.fsdecode(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
        == repo,
        "Source must be a Git repository root",
    )
    revision = git(repo, "rev-parse", "HEAD").decode().strip()
    require(re.fullmatch(r"[a-f0-9]{40,64}", revision), "Invalid repository revision")
    tracked = set(git(repo, "ls-files", "--cached", "-z").split(b"\0"))
    names = tracked | set(
        git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    )
    names.discard(b"")
    files = {}
    total = 0
    for raw in sorted(names):
        name = relative(raw.decode("utf-8"))
        path = repo / name
        require(
            path.resolve() == path and not path.is_symlink(),
            "Symlink source is unsupported",
        )
        if raw in tracked and not path.exists():
            continue
        require(path.is_file(), f"Missing/special source file: {name}")
        require(
            not any(
                part in (".aws", ".ssh", ".gnupg") or part == ".env"
                for part in path.relative_to(repo).parts
            ),
            "Credential-like source path",
        )
        data = path.read_bytes()
        total += len(data)
        require(
            len(data) <= 20 * 1024 * 1024 and total <= 250 * 1024 * 1024,
            "Source snapshot size limit exceeded",
        )
        mode = "755" if path.stat().st_mode & stat.S_IXUSR else "644"
        files[name] = {"sha256": store.put(data), "bytes": len(data), "mode": mode}
    require(files, "Source snapshot is empty")
    return {"revision": revision, "files": files}


def tree_digest(snapshot_value: dict) -> str:
    from store import encoded

    return sha(encoded(snapshot_value["files"]))


def archive(store, snapshot_value: dict) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        directories = set()
        for name, metadata in sorted(snapshot_value["files"].items()):
            relative(name)
            parent = PurePosixPath(name).parent
            while str(parent) != ".":
                directories.add(str(parent))
                parent = parent.parent
            data = store.raw(metadata["sha256"])
            require(len(data) == metadata["bytes"], "Source length mismatch")
        for name in sorted(directories):
            entry = tarfile.TarInfo(name)
            entry.type = tarfile.DIRTYPE
            entry.mode = 0o755
            tar.addfile(entry)
        for name, metadata in sorted(snapshot_value["files"].items()):
            data = store.raw(metadata["sha256"])
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(data), int(metadata["mode"], 8)
            tar.addfile(entry, io.BytesIO(data))
    return output.getvalue()


def changes(before: dict, after: dict) -> list[str]:
    return sorted(
        path
        for path in before["files"].keys() | after["files"].keys()
        if before["files"].get(path) != after["files"].get(path)
    )

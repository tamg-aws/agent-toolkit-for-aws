"""Docker-only supervisor. Repository processes never write host receipts."""

import io
import json
import os
import selectors
import subprocess
import time
import uuid

from source import archive
from store import now, require

LOG_LIMIT = 8 * 1024 * 1024


def docker(*args: str, data: bytes | None = None) -> bytes:
    process = subprocess.run(
        ["docker", *args], input=data, capture_output=True, timeout=120
    )
    require(
        process.returncode == 0,
        "Docker operation failed: " + process.stderr.decode(errors="replace")[:4000],
    )
    return process.stdout


def supervise(store, name: str, timeout: int) -> dict:
    started = now()
    process = subprocess.Popen(
        ["docker", "start", "--attach", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    selector = selectors.DefaultSelector()
    output = {"stdout": io.BytesIO(), "stderr": io.BytesIO()}
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout
    cause = "exited"
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                cause = "timeout"
                break
            for key, _ in selector.select(timeout=0.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = output[key.data]
                remaining = LOG_LIMIT - target.tell()
                target.write(chunk[:remaining])
                if len(chunk) > remaining:
                    cause = "output_limit"
                    break
            if cause != "exited":
                break
        if cause != "exited":
            docker("kill", name)
        process.wait(timeout=30)
        state = json.loads(docker("inspect", name))[0]["State"]
        require(not state["Running"], "Container did not terminate")
        if cause == "exited" and (
            state.get("Status") != "exited"
            or state.get("OOMKilled")
            or state.get("Error")
            or not state.get("StartedAt")
            or state["StartedAt"].startswith("0001-")
            or not state.get("FinishedAt")
            or state["FinishedAt"].startswith("0001-")
            or process.returncode != state["ExitCode"]
        ):
            cause = "infrastructure_failure"
        return {
            "supervisor_pid": os.getpid(),
            "attach_pid": process.pid,
            "started_at": started,
            "completed_at": now(),
            "cause": cause,
            "exit_code": state["ExitCode"],
            "attach_exit_code": process.returncode,
            "container_state": state,
            "stdout": store.put(output["stdout"].getvalue()),
            "stderr": store.put(output["stderr"].getvalue()),
        }
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
        if process.poll() is None:
            process.kill()
            process.wait()


def run_checks(
    store, app: dict, source_value: dict, phase: str, checks: list[dict]
) -> list[dict]:
    image = app["image"]
    inspected = json.loads(docker("image", "inspect", image))[0]
    image_id = inspected["Id"]
    require(image_id.startswith("sha256:"), "Docker image identity missing")
    require(
        not inspected.get("Config", {}).get("Volumes"),
        "Image-declared volumes are unsupported; declare outputs in the contract",
    )
    # The image is trusted execution infrastructure; its identity/config is retained.
    image_receipt = store.save(inspected)
    prefix = "continuum-" + uuid.uuid4().hex
    source_volume = prefix + "-source"
    loader = prefix + "-loader"
    volumes, containers, records = [], [], []
    try:
        docker("volume", "create", source_volume)
        volumes.append(source_volume)
        docker(
            "create",
            "--name",
            loader,
            "--network",
            "none",
            "--entrypoint",
            "/bin/true",
            "--mount",
            f"type=volume,source={source_volume},target=/workspace",
            image_id,
        )
        containers.append(loader)
        docker("cp", "-", loader + ":/workspace", data=archive(store, source_value))
        docker("rm", loader)
        containers.remove(loader)
        output_volumes = []
        for index, path in enumerate(app["output_directories"]):
            require(
                "," not in path
                and all(ord(char) >= 32 and ord(char) != 127 for char in path),
                "Unsafe Docker output mount path",
            )
            volume = prefix + f"-output-{index}"
            docker("volume", "create", volume)
            volumes.append(volume)
            # Set only this empty named volume's permissions, without executing source.
            init = prefix + f"-init-{index}"
            docker(
                "create",
                "--name",
                init,
                "--network",
                "none",
                "--entrypoint",
                "/bin/chmod",
                "--mount",
                f"type=volume,source={volume},target=/output",
                image_id,
                "1777",
                "/output",
            )
            containers.append(init)
            docker("start", "--attach", init)
            require(
                json.loads(docker("inspect", init))[0]["State"]["ExitCode"] == 0,
                "Unable to initialize output volume",
            )
            docker("rm", init)
            containers.remove(init)
            output_volumes.append((path, volume))
        for index, check in enumerate(checks):
            name = prefix + f"-check-{index}"
            argv = [
                "create",
                "--name",
                name,
                "--pull",
                "never",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "256",
                "--memory",
                "2g",
                "--cpus",
                "2",
                "--user",
                "65534:65534",
                "--entrypoint",
                check["argv"][0],
                "--mount",
                f"type=volume,source={source_volume},target=/workspace,readonly",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=256m,mode=1777",
                "--workdir",
                "/workspace" + ("/" + check["cwd"] if check["cwd"] != "." else ""),
                "--env",
                "HOME=/tmp",
                "--env",
                "AWS_EC2_METADATA_DISABLED=true",
            ]
            for path, volume in output_volumes:
                argv += [
                    "--mount",
                    f"type=volume,source={volume},target=/workspace/{path}",
                ]
            for key, value in sorted(app.get("environment", {}).items()):
                argv += ["--env", key + "=" + value]
            argv += [image_id, *check["argv"][1:]]
            docker(*argv)
            containers.append(name)
            record = supervise(store, name, check["timeout_seconds"])
            logs = store.raw(record["stdout"]) + store.raw(record["stderr"])
            expected = (
                check.get("expected_baseline_exit", 0) if phase == "baseline" else 0
            )
            matched = record["cause"] == "exited" and record["exit_code"] == expected
            if phase == "baseline" and check["kind"] == "negative":
                matched = matched and check["baseline_signature"].encode() in logs
            record.update(
                {
                    "check": check,
                    "container_name": name,
                    "docker_create_argv": argv,
                    "image_id": image_id,
                    "image_receipt": image_receipt,
                    "expected_exit": expected,
                    "expectation_met": matched,
                    "evidence_class": "supervised_container_execution",
                }
            )
            records.append(record)
            # Persist each completed check even if a later Docker operation fails.
            store.append("check", record)
            docker("rm", name)
            containers.remove(name)
        return records
    finally:
        cleanup = []
        for name in reversed(containers):
            result = subprocess.run(
                ["docker", "rm", "--force", name], capture_output=True
            )
            cleanup.append({"container": name, "exit_code": result.returncode})
        for name in reversed(volumes):
            result = subprocess.run(
                ["docker", "volume", "rm", name], capture_output=True
            )
            cleanup.append({"volume": name, "exit_code": result.returncode})
        store.append("container_cleanup", {"resources": cleanup, "completed_at": now()})

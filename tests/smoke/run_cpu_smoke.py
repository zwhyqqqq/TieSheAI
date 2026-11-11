"""Submit a source snapshot to rail-cpu and independently accept Agent results."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo

from clearml import Task
from clearml.backend_api.session import Session


SMOKE = Path(__file__).resolve().parent
WORKER = "tiesheai-rail-cpu:cpu0"
PYTHON = "/root/miniconda3/envs/clearml-backend/bin/python"


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def api(session, service, action, **payload):
    response = session.send_request(service, action, json=payload)
    response.raise_for_status()
    result = response.json()
    if result["meta"]["result_code"] != 200:
        raise RuntimeError(f"API rejected {service}.{action}")
    return result["data"]


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", help="Verify an existing run; omit to submit a new task")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    session = Session()
    info = api(session, "server", "info")
    queues = api(session, "queues", "get_all", name="^rail-cpu$").get("queues", [])
    if len(queues) != 1:
        raise RuntimeError("Expected exactly one rail-cpu queue; start the Agent first")
    queue_id = queues[0]["id"]
    workers = api(session, "workers", "get_all", last_seen=120).get("workers", [])
    worker = next((w for w in workers if w["id"] == WORKER), None)
    if not worker or queue_id not in [q["id"] for q in worker.get("queues", [])]:
        raise RuntimeError("Expected CPU Agent is not listening on rail-cpu")
    save(args.evidence / "worker-before.json", worker)
    source = (SMOKE / "cpu_smoke.py").read_bytes()
    if args.task_id:
        task = Task.get_task(task_id=args.task_id)
    else:
        task = Task.create(
            project_name="TieSheAI/Smoke", task_name="T01-B CPU Smoke",
            task_type=Task.TaskTypes.testing,
            script=str(SMOKE / "cpu_smoke.py"),
            packages=["clearml==2.1.12"], add_task_init_call=False,
            force_single_script_file=True, detect_repository=False,
        )
        # No root commit exists yet. Store the complete self-contained source
        # through the SDK API, so the Agent receives code from the Server.
        task.set_script(repository="", branch="", commit="", diff=source.decode(),
                        entry_point="cpu_smoke.py", working_dir=".", binary=PYTHON)
        task.set_tags(["T01-B", "cpu", "smoke"])
        task.set_parameters({"Smoke/limit": 10000,
                             "Smoke/expected_sum_squares": 333383335000,
                             "Smoke/artifact_schema": 1, "Smoke/device": "cpu"})
        save(args.evidence / "submission.json", {
            "task_id": task.id, "queue_id": queue_id, "queue_name": "rail-cpu",
            "script_sha256": sha256(source), "source_mode": "standalone snapshot",
        })
        print("TASK_ID=" + task.id, flush=True)
        Task.enqueue(task, queue_id=queue_id)
    task_dir = args.evidence / task.id
    task_dir.mkdir(exist_ok=True, mode=0o700)
    status_file = task_dir / "status.json"
    transitions = json.loads(status_file.read_text()) if status_file.exists() else []
    deadline = time.monotonic() + args.timeout
    while True:
        task.reload()
        status = str(task.status)
        if not transitions or transitions[-1]["status"] != status:
            transitions.append({"status": status, "observed_at": datetime.now(
                ZoneInfo("Asia/Hong_Kong")).isoformat()})
            save(task_dir / "status.json", transitions)
            print(f"{task.id}: {status}", flush=True)
        if status in {"completed", "failed", "stopped", "closed"}:
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f"Task {task.id} still {status}; inspect Agent logs")
        time.sleep(2)
    if status != "completed":
        logs = api(session, "events", "get_task_log", task=task.id,
                   batch_size=500, order="asc").get("events", [])
        (task_dir / "task-console.txt").write_text(
            "\n".join(event.get("msg", "") for event in logs) + "\n")
        save(task_dir / "failure.json", {"task_id": task.id, "status": status,
                                        "result": "FAIL"})
        raise RuntimeError(f"Agent task {task.id} ended as {status}")
    # get_script() returns only the location fields; the stored source is in
    # the full script record returned by tasks.get_by_id.
    script = task.data.script.to_dict()
    save(task_dir / "server-script.json", script)
    assert not script.get("repository"), "Unexpected repository checkout"
    assert sha256((script.get("diff") or "").encode()) == sha256(source), "Source snapshot changed"
    assert task.data.last_worker == WORKER, "Task was not run by the expected Agent"
    assert task.data.execution.queue == queue_id, "Unexpected execution queue"
    params = task.get_parameters()
    for name, value in {"Smoke/limit": "10000", "Smoke/device": "cpu",
                        "Smoke/expected_sum_squares": "333383335000",
                        "Smoke/artifact_schema": "1", "Execution/worker_id": WORKER,
                        "Execution/python_executable": PYTHON,
                        "Execution/running_locally": "False",
                        "Execution/cuda_visible_devices": "none"}.items():
        assert str(params.get(name)) == value, f"Unexpected parameter: {name}"
    # Wait briefly for the event index after task completion.
    for attempt in range(10):
        logs = api(session, "events", "get_task_log", task=task.id,
                   batch_size=500, order="asc").get("events", [])
        console = "\n".join(event.get("msg", "") for event in logs)
        scalars = task.get_reported_scalars()
        if "T01B_SMOKE_OK" in console and "cpu_smoke" in scalars:
            break
        time.sleep(1)
    (task_dir / "task-console.txt").write_text(console + "\n")
    assert f"T01B_AGENT_EXECUTION task={task.id} worker={WORKER}" in console
    assert f"task {task.id} pulled from {queue_id} by worker {WORKER}" in console
    assert "T01B_SMOKE_OK" in console
    metric = scalars["cpu_smoke"]["check_passed"]
    assert metric["x"] == [0] and metric["y"] == [1.0], "Unexpected scalar"
    artifact = task.artifacts["cpu-smoke-json"]
    # Force an actual download, even if this host also has an SDK cache.
    downloaded = Path(artifact.get_local_copy(extract_archive=False,
                      raise_on_error=True, force_download=True)).read_bytes()
    (task_dir / "downloaded.json").write_bytes(downloaded)
    expected = (SMOKE / "expected.json").read_bytes()
    before = artifact.metadata["sha256_before_upload"]
    reported = re.search(r"T01B_BEFORE_UPLOAD_SHA256=([a-f0-9]{64})", console)
    assert reported and reported[1] == before == sha256(downloaded) == sha256(expected)
    assert downloaded == expected, "Artifact content mismatch"
    result = {
        "result": "PASS", "recorded_at": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
        "task_id": task.id, "task_url": task.get_output_log_web_page(),
        "status": status, "queue_id": queue_id, "queue_name": "rail-cpu",
        "worker_id": task.data.last_worker, "server_version": info.get("version"),
        "python_executable": PYTHON, "script_sha256": sha256(source),
        "parameters": params, "scalar": metric, "artifact_uri": artifact.url,
        "artifact_sha256_before": before, "artifact_sha256_download": sha256(downloaded),
        "artifact_sha256_expected": sha256(expected), "artifact_bytes": len(downloaded),
        "agent_queue_pull_log_verified": True, "source_snapshot_verified": True,
        "forced_artifact_download": True,
    }
    save(task_dir / "acceptance.json", result)
    save(args.evidence / "latest.json", result)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

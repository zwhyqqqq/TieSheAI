"""T01-B: self-contained CPU task; only a ClearML Agent may run main()."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from clearml import Task


def main():
    # Refuse local direct execution before Task.init can create a local Task.
    if not os.environ.get("CLEARML_TASK_ID") or not os.environ.get("CLEARML_WORKER_ID"):
        raise RuntimeError("Submit through tests/smoke/run_cpu_smoke.py; Agent execution required")
    task = Task.init(
        project_name="TieSheAI/Smoke", task_name="T01-B CPU Smoke",
        task_type=Task.TaskTypes.testing, reuse_last_task_id=False,
        auto_connect_frameworks=False, auto_resource_monitoring=False,
    )
    if Task.running_locally():
        raise RuntimeError("Agent remote Task context required")
    # Agent 3.0.3 --cpu-only sets both visibility variables to "none".
    if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1", "none"):
        raise RuntimeError("CPU-only execution required")
    params = task.connect({"limit": 10000, "expected_sum_squares": 333383335000,
                           "artifact_schema": 1, "device": "cpu"}, name="Smoke")
    logger = task.get_logger()
    worker = os.environ["CLEARML_WORKER_ID"]
    print(f"T01B_AGENT_EXECUTION task={task.id} worker={worker} python={sys.executable}")
    runtime = {"worker_id": worker, "python_executable": sys.executable,
               "running_locally": Task.running_locally(),
               "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}
    task.connect(runtime, name="Execution", ignore_remote_overrides=True)
    result = sum(i * i for i in range(1, params["limit"] + 1))
    if result != params["expected_sum_squares"]:
        raise RuntimeError("CPU calculation did not match expected result")
    # A small exact scalar also survives the server's float chart storage.
    logger.report_scalar("cpu_smoke", "check_passed", value=1.0, iteration=0)
    payload = {"device": "cpu", "message": "TieSheAI T01-B CPU smoke test",
               "schema_version": 1, "sum_squares": result}
    content = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    print(f"T01B_BEFORE_UPLOAD_SHA256={digest}")
    with tempfile.TemporaryDirectory(prefix="tiesheai-cpu-smoke-") as directory:
        artifact = Path(directory) / "cpu-smoke.json"
        artifact.write_bytes(content)
        if not task.upload_artifact("cpu-smoke-json", artifact_object=artifact,
                                    metadata={"sha256_before_upload": digest}, wait_on_upload=True):
            raise RuntimeError("Artifact upload failed")
    print(f"T01B_SMOKE_OK result={result} artifact_sha256={digest}")
    task.flush(wait_for_uploads=True)
    task.close()


if __name__ == "__main__":
    main()

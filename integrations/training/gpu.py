"""CUDA-only Unsloth training and ClearML model registration."""

import hashlib
import json
import math
import platform
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

from integrations.data_preparation.prepare import encoded, sha

from .inputs import (
    MODEL, REVISION, WEIGHTS_FILE, WEIGHTS_SHA256, WEIGHTS_SIZE, InputError,
    check_tokenizer, copy_verified_model_files, torch_collator, verified_model_file,
)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_model(loader, model_dir, args, dtype, lora_targets):
    from huggingface_hub import hf_hub_download

    checkpoint = Path(hf_hub_download(repo_id=MODEL, filename=WEIGHTS_FILE, revision=REVISION, token=False))
    if checkpoint.stat().st_size != WEIGHTS_SIZE or file_sha256(checkpoint) != WEIGHTS_SHA256:
        raise InputError("base model weights do not match the pinned size and SHA-256")
    with TemporaryDirectory(prefix="tiesheai-qwen-") as directory:
        snapshot = Path(directory)
        copy_verified_model_files(model_dir, snapshot)
        (snapshot / WEIGHTS_FILE).symlink_to(checkpoint.resolve())
        model, runtime_tokenizer = loader.from_pretrained(
            model_name=str(snapshot), revision=REVISION, use_exact_model_name=True, local_files_only=True,
            trust_remote_code=False, fix_tokenizer=False, device_map={"": 0},
            max_seq_length=args.max_seq_length, dtype=dtype, load_in_4bit=False, load_in_8bit=False,
            load_in_16bit=True, full_finetuning=False, use_gradient_checkpointing="unsloth",
            random_state=args.seed,
        )
        check_tokenizer(runtime_tokenizer)
        if model.config.model_type != "qwen2" or getattr(model, "is_quantized", False):
            raise InputError("loaded model is not the expected unquantized Qwen2 base")
        model = loader.get_peft_model(
            model, r=args.lora_r, lora_alpha=args.lora_alpha, target_modules=lora_targets,
            lora_dropout=0.0, bias="none", use_gradient_checkpointing="unsloth", random_state=args.seed,
        )
    trainable = [name for name, param in model.named_parameters() if param.requires_grad]
    if not trainable or any(".lora_" not in name for name in trainable):
        raise InputError("expected only LoRA parameters to be trainable")
    model.config.use_cache = False
    return model


def trainer_options(args, dtype, work_dir):
    return {
        "output_dir": str(work_dir),
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "num_train_epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "data_seed": args.seed,
        "bf16": dtype == "bf16",
        "fp16": dtype == "fp16",
        "optim": "adamw_torch",
        "lr_scheduler_type": "linear",
        "warmup_steps": 0,
        "max_grad_norm": 1.0,
        "logging_steps": 1,
        "logging_nan_inf_filter": False,
        "save_strategy": "no",
        "eval_strategy": "no",
        "prediction_loss_only": True,
        "label_names": ["labels"],
        "remove_unused_columns": False,
        "report_to": [],
    }


def save_package(model, tokenizer, directory, report, model_dir):
    directory.mkdir()
    # PEFT was initialized from a temporary local snapshot. Save the portable
    # upstream identity and revision rather than that machine-local pathname.
    adapter = model.peft_config["default"]
    adapter.base_model_name_or_path = MODEL
    adapter.revision = REVISION
    model.save_pretrained(directory, safe_serialization=True, save_embedding_layers=False)
    tokenizer.save_pretrained(directory)
    if {path.name for path in directory.glob("*.safetensors")} != {"adapter_model.safetensors"}:
        raise RuntimeError("expected exactly one adapter safetensors file")
    config = json.loads((directory / "adapter_config.json").read_bytes())
    if (config["base_model_name_or_path"], config["revision"]) != (MODEL, REVISION):
        raise RuntimeError("saved adapter has the wrong base model binding")
    (directory / "LICENSE").write_bytes(verified_model_file(model_dir, "LICENSE"))
    (directory / "run-manifest.json").write_bytes(encoded(report))
    hashes = {
        path.name: {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
        for path in sorted(directory.iterdir()) if path.is_file()
    }
    (directory / "sha256.json").write_bytes(encoded(hashes))
    return hashes


def register_output(task, output_model, directory, args, report, hashes):
    manifest_pin = hashes["run-manifest.json"]["sha256"]
    # Save the local manifest before network writes so partial uploads can be reconciled.
    for name in ("run-manifest.json", "sha256.json"):
        if not task.upload_artifact(name, artifact_object=directory / name, wait_on_upload=True):
            raise RuntimeError(f"ClearML artifact upload failed: {name}")
    model = output_model(
        task=task, name=f"{args.task_name} LoRA", framework="PyTorch", tags=["t03", "peft", "lora"],
        config_dict={"base_model": MODEL, "revision": REVISION, "dataset_id": args.dataset_id,
                     "dataset_version": args.dataset_version, "manifest_sha256": args.manifest_sha256,
                     "run_manifest_sha256": manifest_pin, "format": "peft-lora"},
    )
    uri = model.update_weights_package(
        weights_path=str(directory), upload_uri=args.output_uri, target_filename="qwen-lora.zip",
        iteration=report["metrics"]["optimizer_steps"], auto_delete_file=False, async_enable=False,
    )
    if not uri or not model.id:
        raise RuntimeError("ClearML returned no registered model URI/ID")
    task.connect({"model_id": model.id, "run_manifest_sha256": manifest_pin},
                 name="Output", ignore_remote_overrides=True)
    return model.id


def train(loader, args, dtype, model_dir, tokenizer, features, report):
    import torch
    from clearml import OutputModel, Task
    from transformers import Trainer, TrainerCallback, TrainingArguments

    args.output_dir.mkdir(parents=True, exist_ok=False)
    torch_dtype = torch.bfloat16 if dtype == "bf16" else torch.float16
    model = load_model(loader, model_dir, args, torch_dtype, report["settings"]["lora_targets"])
    training_args = TrainingArguments(**trainer_options(args, dtype, args.output_dir / "trainer"))
    task = Task.init(project_name=args.project, task_name=args.task_name, task_type=Task.TaskTypes.training,
                     reuse_last_task_id=False, auto_connect_frameworks=False, auto_connect_arg_parser=False,
                     auto_resource_monitoring=False, output_uri=args.output_uri)
    try:
        task.connect({
            "dataset_id": args.dataset_id, "dataset_version": args.dataset_version,
            "manifest_sha256": args.manifest_sha256, "base_model": MODEL, "revision": REVISION,
            "dtype": dtype, **report["settings"],
        }, name="Training", ignore_remote_overrides=True)
        logger = task.get_logger()

        class ReportLoss(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and "loss" in logs:
                    loss = logs["loss"]
                    if not math.isfinite(loss):
                        raise RuntimeError("training loss is non-finite")
                    logger.report_scalar(title="loss", series="train", value=loss, iteration=state.global_step)

        trainer = Trainer(
            model=model, args=training_args, train_dataset=features["train"], eval_dataset=features["validation"],
            data_collator=torch_collator, processing_class=tokenizer, callbacks=[ReportLoss()],
        )
        torch.cuda.reset_peak_memory_stats()
        with model.disable_adapter():
            base_loss = trainer.evaluate()["eval_loss"]
        if not math.isfinite(base_loss):
            raise RuntimeError("base validation loss is non-finite")
        logger.report_scalar(title="loss", series="validation_base", value=base_loss, iteration=0)
        trained = trainer.train()
        final_loss = trainer.evaluate()["eval_loss"]
        if not math.isfinite(final_loss) or not math.isfinite(trained.training_loss) or trained.global_step < 1:
            raise RuntimeError("training did not produce a finite loss and a completed optimizer step")
        logger.report_scalar(title="loss", series="validation", value=final_loss, iteration=trained.global_step)
        report["metrics"] = {
            "train_loss": trained.training_loss, "base_validation_loss": base_loss,
            "validation_loss": final_loss, "optimizer_steps": trained.global_step,
        }
        report["run"] = {
            "task_id": task.id, "dtype": dtype, "python": platform.python_version(),
            "packages": {name: version(name) for name in (
                "clearml", "torch", "transformers", "accelerate", "peft", "trl", "unsloth", "unsloth-zoo",
            )},
            "cuda_runtime": torch.version.cuda, "gpu_name": torch.cuda.get_device_name(0),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(), "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "weights_sha256": WEIGHTS_SHA256,
            "source_sha256": {
                name: sha((Path(__file__).resolve().parents[2] / name).read_bytes())
                for name in ("integrations/training/gpu.py", "integrations/training/inputs.py",
                             "integrations/training/train.py", "integrations/data_preparation/prepare.py")
            },
        }
        directory = args.output_dir / "adapter"
        hashes = save_package(model, tokenizer, directory, report, model_dir)
        model_id = register_output(task, OutputModel, directory, args, report, hashes)
        task.flush(wait_for_uploads=True)
    except Exception:
        task.mark_failed(status_reason="T03 training or artifact registration failed")
        raise
    task.close()
    print(json.dumps({"task_id": report["run"]["task_id"], "model_id": model_id,
                      "output_dir": str(directory), "metrics": report["metrics"]}))

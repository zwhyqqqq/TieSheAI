"""T03 entry point. CPU preflight and CUDA training share validated inputs."""

import argparse
import json
import math
import sys
from importlib.metadata import version
from pathlib import Path

from .inputs import (
    DATASET_ID, DATASET_VERSION, MANIFEST_SHA256, MODEL, REVISION, TEMPLATE_SHA256,
    IGNORE, InputError, collate_rows, dataset_directory, encode_conversation,
    load_data, load_tokenizer, model_directory,
)

MAX_SEQUENCE_LENGTH = 512
LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


class CudaUnavailable(RuntimeError):
    """CUDA cannot run the GPU training path."""


def require_cuda(dtype):
    try:
        import torch
    except (ImportError, OSError) as error:
        raise CudaUnavailable("CUDA training requires a working CUDA-enabled PyTorch install") from error
    if not torch.cuda.is_available():
        raise CudaUnavailable("CUDA is unavailable; run --preflight or use a validated GPU environment")
    if torch.cuda.device_count() != 1:
        raise CudaUnavailable("expose exactly one GPU via CUDA_VISIBLE_DEVICES for this single-GPU adapter")
    bf16 = torch.cuda.is_bf16_supported(including_emulation=False)
    if dtype == "bf16" and not bf16:
        raise CudaUnavailable("requested BF16 is unsupported by the visible CUDA device")
    return ("bf16" if bf16 else "fp16") if dtype == "auto" else dtype


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="CPU validation only")
    parser.add_argument("--report", type=Path, help="new file for the JSON preflight report")
    parser.add_argument("--dataset-id", default=DATASET_ID)
    parser.add_argument("--dataset-version", default=DATASET_VERSION)
    parser.add_argument("--manifest-sha256", default=MANIFEST_SHA256)
    parser.add_argument("--data-dir", type=Path, help="verified local Dataset files instead of the read-only SDK")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument("--tokenizer-dir", type=Path, help="local copy of the pinned tokenizer, configs and license")
    parser.add_argument("--max-seq-length", type=positive, default=MAX_SEQUENCE_LENGTH)
    parser.add_argument("--batch-size", type=positive, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=positive, default=3)
    parser.add_argument("--epochs", type=positive, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--lora-r", type=positive, default=8)
    parser.add_argument("--lora-alpha", type=positive, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dtype", choices=("auto", "bf16", "fp16"), default="auto")
    parser.add_argument("--output-dir", type=Path, help="new local directory for a GPU run")
    parser.add_argument("--project", help="ClearML project for a GPU run")
    parser.add_argument("--task-name", help="ClearML task name for a GPU run")
    parser.add_argument("--output-uri", help="approved ClearML storage URI for a GPU run")
    args = parser.parse_args(argv)
    if (args.dataset_id, args.dataset_version, args.manifest_sha256) != (DATASET_ID, DATASET_VERSION, MANIFEST_SHA256):
        parser.error("Dataset ID/version/manifest SHA-256 does not match the supported T03 input")
    if (args.model, args.revision) != (MODEL, REVISION):
        parser.error("model/revision does not match the pinned T03 tokenizer")
    if args.max_seq_length > MAX_SEQUENCE_LENGTH:
        parser.error(f"--max-seq-length cannot exceed {MAX_SEQUENCE_LENGTH} for the T03 configuration")
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("--learning-rate must be finite and positive")
    if not 0 <= args.seed < 2**32:
        parser.error("--seed must be between 0 and 2**32-1")
    if args.report and not args.preflight:
        parser.error("--report requires --preflight")
    return args


def settings(args):
    return {
        "max_seq_length": args.max_seq_length, "batch_size": args.batch_size, "epochs": args.epochs,
        "gradient_accumulation_steps": args.gradient_accumulation_steps, "learning_rate": args.learning_rate,
        "lora_r": args.lora_r, "lora_alpha": args.lora_alpha, "lora_dropout": 0.0, "lora_bias": "none",
        "lora_targets": list(LORA_TARGETS), "seed": args.seed, "requested_dtype": args.dtype,
        "quantization": "none", "optimizer": "adamw_torch", "scheduler": "linear", "warmup_steps": 0,
        "max_grad_norm": 1.0, "gradient_checkpointing": "unsloth", "packing": False,
    }


def encode_splits(rows, tokenizer, args):
    encoded = {}
    results = {}
    for split, conversations in rows.items():
        features = [encode_conversation(tokenizer, messages, args.max_seq_length, f"{split}.jsonl:{line}")
                    for line, messages in enumerate(conversations, 1)]
        batch = collate_rows(features)
        token_counts = [sum(row) for row in batch["attention_mask"]]
        labeled = [sum(label != IGNORE for label in row) for row in batch["labels"]]
        results[split] = {
            "rows": len(features), "tokens": sum(token_counts), "effective_labels": sum(labeled),
            "min_tokens": min(token_counts), "max_tokens": max(token_counts),
            "tokens_per_row": token_counts, "effective_labels_per_row": labeled,
        }
        encoded[split] = features
    return encoded, results


def main(argv=None):
    args = parse_args(argv)
    try:
        dtype = None
        if not args.preflight:
            dtype = require_cuda(args.dtype)
            if not all((args.output_dir, args.project, args.task_name, args.output_uri)):
                raise InputError("GPU training requires --output-dir, --project, --task-name and --output-uri")
            if args.output_dir.exists():
                raise InputError("--output-dir already exists; select a new run directory")

        data_dir = args.data_dir if args.data_dir is not None else dataset_directory(args.dataset_id, args.dataset_version)
        rows, data = load_data(data_dir, args.manifest_sha256)
        model_dir = model_directory(args.tokenizer_dir)
        if not args.preflight:
            # Unsloth must patch Transformers before AutoTokenizer imports it.
            from unsloth import FastLanguageModel

        tokenizer = load_tokenizer(model_dir)
        encoded, results = encode_splits(rows, tokenizer, args)
        report = {
            "mode": "preflight" if args.preflight else "training",
            "data": {
                "id": args.dataset_id, "version": args.dataset_version, "manifest_sha256": args.manifest_sha256,
                "source": "local" if args.data_dir is not None else "clearml", **data,
            },
            "base_model": {"name": MODEL, "revision": REVISION, "template_sha256": TEMPLATE_SHA256,
                           "eos_token_id": tokenizer.eos_token_id, "pad_token_id": tokenizer.pad_token_id},
            "settings": settings(args), "splits": results,
            "tokenizer_packages": {package: version(package) for package in ("transformers", "tokenizers", "Jinja2")},
        }
        if args.preflight:
            payload = json.dumps(report, indent=2) + "\n"
            if args.report:
                with args.report.open("x", encoding="utf-8") as output:
                    output.write(payload)
            print(payload, end="")
            return 0

        from .gpu import train

        train(FastLanguageModel, args, dtype, model_dir, tokenizer, encoded, report)
        return 0
    except CudaUnavailable as error:
        print(f"T03 CUDA check failed: {error}", file=sys.stderr)
        return 3
    except (InputError, OSError, ImportError) as error:
        print(f"T03 failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

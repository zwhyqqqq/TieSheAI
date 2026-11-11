"""Verified T03 inputs and CPU-side Qwen conversation encoding."""

import json
import re
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from integrations.data_preparation.prepare import CONTRACT, FILES, encoded, sha, strict_object, validate

DATASET_ID = "65d2ce482a484ff0a7e2ef6f0f4dbe67"
DATASET_VERSION = "1.0.0"
MANIFEST_SHA256 = "8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
WEIGHTS_FILE = "model.safetensors"
WEIGHTS_SHA256 = "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
WEIGHTS_SIZE = 988097824
TEMPLATE_SHA256 = "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
MODEL_FILES = {
    "LICENSE": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
    "config.json": "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45",
    "generation_config.json": "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
    "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
    "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    "tokenizer_config.json": "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
}
SPLITS = {"train": 18, "validation": 6}
EOS, PAD = 151645, 151643
END = "<|im_end|>"
IGNORE = -100


class InputError(ValueError):
    """The selected data, tokenizer, or preprocessing configuration is invalid."""


def check_dataset(dataset, dataset_id, version):
    if dataset.id != dataset_id or dataset.version != version or not dataset.is_final():
        raise InputError("ClearML Dataset ID/version mismatch or Dataset is not finalized")
    if set(dataset.list_files()) != set(FILES):
        raise InputError("ClearML Dataset must contain exactly the five conversation-v1 files")


def dataset_directory(dataset_id, version):
    from clearml import Dataset

    dataset = Dataset.get(dataset_id=dataset_id, auto_create=False, writable_copy=False,
                          _dont_populate_runtime_props=True)
    check_dataset(dataset, dataset_id, version)
    return Path(dataset.get_local_copy(use_soft_links=False, max_workers=1))


def load_json(raw, name):
    try:
        return json.loads(raw, object_pairs_hook=strict_object)
    except (ValueError, UnicodeError, RecursionError):
        raise InputError(f"{name}: invalid JSON") from None


def jsonl(raw, name):
    try:
        lines = raw.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        raise InputError(f"{name}: invalid UTF-8") from None
    if lines[-1] == "":
        lines.pop()
    for line, text in enumerate(lines, 1):
        yield line, load_json(text, f"{name}:{line}")


def check_sources(raw, assignments):
    seen, source_splits, groups = set(), {}, defaultdict(list)
    for line, row in jsonl(raw, "sources.jsonl"):
        try:
            identity, split = row["sample_sha256"], row["split"]
            group, occurrences = row["group_sha256"], row["occurrences"]
            if identity in seen or assignments[identity] != split:
                raise ValueError
            if not isinstance(group, str) or not re.fullmatch(r"[0-9a-f]{64}", group):
                raise ValueError
            if not isinstance(occurrences, list) or not occurrences:
                raise ValueError
            for occurrence in occurrences:
                source = occurrence["source_id"]
                if source is None:
                    continue
                if not isinstance(source, str) or not source.strip():
                    raise ValueError
                if source_splits.setdefault(source, split) != split:
                    raise InputError(f"sources.jsonl:{line}: source crosses train/validation")
        except InputError:
            raise
        except (KeyError, TypeError, ValueError):
            raise InputError(f"sources.jsonl:{line}: invalid sample or source mapping") from None
        groups[group].append(identity)
        seen.add(identity)
    if seen != assignments.keys():
        raise InputError("sources.jsonl: missing sample mappings")
    counts = dict.fromkeys(SPLITS, 0)
    for group, samples in groups.items():
        splits = {assignments[identity] for identity in samples}
        if len(splits) != 1:
            raise InputError("sources.jsonl: group crosses train/validation")
        if sha(encoded(sorted(samples))) != group:
            raise InputError("sources.jsonl: group hash mismatch")
        counts[splits.pop()] += 1
    return counts


def load_data(directory, manifest_pin):
    raw = {name: (directory / name).read_bytes() for name in FILES}
    fingerprints = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in raw.items()}
    manifest_info = fingerprints["manifest.json"]
    if manifest_info["sha256"] != manifest_pin:
        raise InputError("manifest.json: SHA-256 mismatch")
    manifest = load_json(raw["manifest.json"], "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("contract_version") != CONTRACT:
        raise InputError("manifest.json: unexpected data contract")
    for name in FILES:
        if name != "manifest.json" and manifest.get("outputs", {}).get(name) != fingerprints[name]:
            raise InputError(f"{name}: size or SHA-256 mismatch against manifest")

    rows, assignments = {}, {}
    for split, count in SPLITS.items():
        name = split + ".jsonl"
        rows[split] = []
        for line, row in jsonl(raw[name], name):
            try:
                if not isinstance(row, dict) or set(row) != {"messages"}:
                    raise ValueError
                sample = validate(row)
            except (ValueError, TypeError, UnicodeError):
                raise InputError(f"{name}:{line}: invalid messages-only conversation-v1 record") from None
            identity = sha(encoded(sample))
            if identity in assignments:
                raise InputError(f"{name}:{line}: duplicate conversation in train/validation")
            assignments[identity] = split
            rows[split].append(sample["messages"])
        if len(rows[split]) != count:
            raise InputError(f"{name}: expected {count} records, got {len(rows[split])}")
    groups = check_sources(raw["sources.jsonl"], assignments)
    stats = load_json(raw["statistics.json"], "statistics.json")
    for split, count in SPLITS.items():
        if stats.get(f"{split}_records") != count or stats.get(f"{split}_groups") != groups[split]:
            raise InputError("statistics.json: record or source group count mismatch")
    return rows, {"files": fingerprints, "source_groups": groups}


def model_directory(local_dir):
    if local_dir is not None:
        return local_dir

    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=MODEL, revision=REVISION, allow_patterns=list(MODEL_FILES), token=False))


def verified_model_file(source, name):
    content = (source / name).read_bytes()
    if sha(content) != MODEL_FILES[name]:
        raise InputError(f"{name}: SHA-256 mismatch for {MODEL}@{REVISION}")
    return content


def copy_verified_model_files(source, target):
    for name in MODEL_FILES:
        (target / name).write_bytes(verified_model_file(source, name))


def check_tokenizer(tokenizer):
    template = tokenizer.chat_template
    if (not tokenizer.is_fast or not isinstance(template, str) or sha(template.encode()) != TEMPLATE_SHA256
            or tokenizer.eos_token_id != EOS or tokenizer.eos_token != END
            or tokenizer.pad_token_id != PAD or tokenizer.pad_token != "<|endoftext|>"):
        raise InputError("tokenizer template or EOS/PAD does not match the pinned Qwen revision")


def load_tokenizer(source):
    from transformers import AutoTokenizer

    # Stage only the verified files. Extra local files could override the native template.
    with TemporaryDirectory(prefix="tiesheai-tokenizer-") as scratch:
        copy_verified_model_files(source, Path(scratch))
        tokenizer = AutoTokenizer.from_pretrained(scratch, local_files_only=True, trust_remote_code=False)
    check_tokenizer(tokenizer)
    return tokenizer


def render(tokenizer, messages):
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)


def encode_conversation(tokenizer, messages, limit, location):
    """Keep all reply text and its EOS supervised, including earlier turns."""
    messages = validate({"messages": messages})["messages"]
    rendered = render(tokenizer, messages)
    end_frame = END + "\n"
    frames = [(f"<|im_start|>{message['role']}\n", message["content"], message["role"] == "assistant")
              for message in messages]
    body = "".join(header + content + end_frame for header, content, _ in frames)

    prefix = ""
    if messages[0]["role"] != "system":
        empty_user = "<|im_start|>user\n" + end_frame
        probe = render(tokenizer, [{"role": "user", "content": ""}])
        if not probe.endswith(empty_user):
            raise InputError(f"{location}: unexpected default system template")
        prefix = probe[:-len(empty_user)]
    if rendered != prefix + body:
        raise InputError(f"{location}: unexpected Qwen message template")

    def tokens(text, literal=False):
        return tokenizer(text, add_special_tokens=False, split_special_tokens=literal)["input_ids"]

    ids, labels = [], []

    def append(part, supervised=False):
        ids.extend(part)
        labels.extend(part if supervised else [IGNORE] * len(part))

    append(tokens(prefix))
    special_ids = set(tokenizer.all_special_ids)
    for header, content, supervised in frames:
        # Keep header whitespace masked even if it would merge with a leading
        # newline in the reply. Literal text cannot emit template control IDs.
        append(tokens(header))
        content_ids = tokens(content, literal=True)
        if not content_ids or not special_ids.isdisjoint(content_ids):
            raise InputError(f"{location}: message text cannot be encoded as ordinary tokens")
        append(content_ids, supervised)
        append([EOS], supervised)
        append(tokens("\n"))
    if tokenizer.decode(ids, clean_up_tokenization_spaces=False) != rendered:
        raise InputError(f"{location}: rendered text did not round trip through the tokenizer")
    if len(ids) > limit:
        raise InputError(f"{location}: {len(ids)} tokens exceeds the {limit}-token limit")
    if not any(label != IGNORE for label in labels):
        raise InputError(f"{location}: all labels are masked")
    return {"input_ids": ids, "labels": labels}


def collate_rows(features):
    """Produce exactly the fields passed to the model, with dynamic right padding."""
    if not features:
        raise InputError("cannot collate an empty batch")
    width = max(len(row["input_ids"]) for row in features)
    batch = {"input_ids": [], "attention_mask": [], "labels": []}
    for row in features:
        ids, labels = row["input_ids"], row["labels"]
        if len(ids) != len(labels) or not any(label != IGNORE for label in labels):
            raise InputError("invalid batch row: missing or all-masked labels")
        if any(label not in (IGNORE, token) or (token == PAD and label != IGNORE)
               for token, label in zip(ids, labels)):
            raise InputError("invalid batch row: label/token mismatch or supervised padding")
        pad = width - len(ids)
        batch["input_ids"].append(ids + [PAD] * pad)
        batch["attention_mask"].append([1] * len(ids) + [0] * pad)
        batch["labels"].append(labels + [IGNORE] * pad)
    return batch


def torch_collator(features):
    import torch

    return {name: torch.tensor(rows, dtype=torch.long) for name, rows in collate_rows(features).items()}

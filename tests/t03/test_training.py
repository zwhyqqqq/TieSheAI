"""T03 CPU regression coverage. No server writes, weights, or optimization."""

import argparse
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from integrations.data_preparation.prepare import FILES, encoded, sha
from integrations.training import gpu, inputs, train

DATA_DIR = Path(os.environ.get("T03_DATA_DIR", "infra/evidence/t02-public-data/downloaded"))
TOKENIZER_DIR = Path(os.environ.get("T03_TOKENIZER_DIR", "infra/evidence/t03a/qwen-tokenizer"))


def message(role, content):
    return {"role": role, "content": content}


class DataTests(unittest.TestCase):
    def test_fixed_asset_and_partitions(self):
        rows, report = inputs.load_data(DATA_DIR, inputs.MANIFEST_SHA256)
        self.assertEqual({split: len(part) for split, part in rows.items()}, {"train": 18, "validation": 6})
        self.assertEqual(report["source_groups"], {"train": 9, "validation": 3})
        self.assertEqual(set(report["files"]), set(FILES))

    def test_all_members_reject_corruption(self):
        with TemporaryDirectory() as scratch:
            directory = Path(scratch)
            for name in FILES:
                (directory / name).write_bytes((DATA_DIR / name).read_bytes())
            for name in FILES:
                with self.subTest(name=name):
                    path = directory / name
                    original = path.read_bytes()
                    path.write_bytes(original + b" ")
                    with self.assertRaisesRegex(inputs.InputError, rf"{name}.*SHA-256 mismatch"):
                        inputs.load_data(directory, inputs.MANIFEST_SHA256)
                    path.write_bytes(original)

    def test_sdk_version_and_state(self):
        for dataset_version, final in (("2.0.0", True), ("1.0.0", False)):
            with self.subTest(version=dataset_version, final=final):
                dataset = Mock(id=inputs.DATASET_ID, version=dataset_version)
                dataset.is_final.return_value = final
                sdk = SimpleNamespace(Dataset=Mock())
                sdk.Dataset.get.return_value = dataset
                with patch.dict(sys.modules, {"clearml": sdk}):
                    with self.assertRaisesRegex(inputs.InputError, "version mismatch|not finalized"):
                        inputs.dataset_directory(inputs.DATASET_ID, inputs.DATASET_VERSION)
                dataset.get_local_copy.assert_not_called()
                sdk.Dataset.get.assert_called_once_with(
                    dataset_id=inputs.DATASET_ID, auto_create=False, writable_copy=False,
                    _dont_populate_runtime_props=True,
                )

    def test_sources_cannot_cross_partitions(self):
        one, two = "a" * 64, "b" * 64
        assignments = {one: "train", two: "validation"}
        raw = b"".join(encoded({
            "sample_sha256": sample, "split": split, "group_sha256": sha(encoded([sample])),
            "occurrences": [{"source_id": "same-document"}],
        }) for sample, split in assignments.items())
        with self.assertRaisesRegex(inputs.InputError, "sources.jsonl:2: source crosses"):
            inputs.check_sources(raw, assignments)

    def test_argument_binding_rejects_alternative_asset(self):
        for option, value in (("--dataset-version", "2.0.0"), ("--manifest-sha256", "0" * 64),
                              ("--revision", "main"), ("--model", "other/repo")):
            with self.subTest(option=option), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    train.main(["--preflight", option, value])
                self.assertEqual(caught.exception.code, 2)

    def test_cpu_path_requests_only_pinned_small_files(self):
        import huggingface_hub

        with patch.object(huggingface_hub, "snapshot_download", return_value=str(TOKENIZER_DIR)) as fetch:
            self.assertEqual(inputs.model_directory(None), TOKENIZER_DIR)
        fetch.assert_called_once_with(repo_id=inputs.MODEL, revision=inputs.REVISION,
                                      allow_patterns=list(inputs.MODEL_FILES), token=False)
        self.assertNotIn(inputs.WEIGHTS_FILE, inputs.MODEL_FILES)


class TokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = inputs.load_tokenizer(TOKENIZER_DIR)

    def encode(self, messages, limit=512):
        return inputs.encode_conversation(self.tokenizer, messages, limit, "validation.jsonl:7")

    def decode(self, ids):
        return self.tokenizer.decode(ids, clean_up_tokenization_spaces=False)

    def labeled_spans(self, row):
        spans = []
        current = []
        for label in row["labels"]:
            if label == inputs.IGNORE and current:
                spans.append(self.decode(current))
                current = []
            elif label != inputs.IGNORE:
                current.append(label)
        self.assertFalse(current, "trailing template newline must stay masked")
        return spans

    def test_implicit_system_and_fixed_canonical_tokens(self):
        rows, _ = inputs.load_data(DATA_DIR, inputs.MANIFEST_SHA256)
        args = train.parse_args(["--preflight"])
        features, result = train.encode_splits(rows, self.tokenizer, args)
        self.assertEqual([result[name]["max_tokens"] for name in rows], [331, 302])
        for split, part in rows.items():
            for messages, row in zip(part, features[split]):
                self.assertTrue(self.decode(row["input_ids"]).startswith("<|im_start|>system\n"))
                direct = self.tokenizer.apply_chat_template(messages, tokenize=True,
                                                           add_generation_prompt=False, return_dict=False)
                self.assertEqual(row["input_ids"], direct)
                self.assertEqual(self.labeled_spans(row), [messages[-1]["content"] + inputs.END])

    def test_explicit_system_multiturn_whitespace_unicode_and_literal_controls(self):
        messages = [
            message("system", "系统：literal <|im_start|>"),
            message("user", "一？<|im_end|>"),
            message("assistant", "\n\t 答案一🙂 <|im_end|>"),
            message("user", "再说一次 <|endoftext|>"),
            message("assistant", " 答案二\n"),
        ]
        row = self.encode(messages)
        self.assertEqual(self.decode(row["input_ids"]), inputs.render(self.tokenizer, messages))
        self.assertEqual(self.labeled_spans(row), [messages[2]["content"] + inputs.END,
                                                   messages[4]["content"] + inputs.END])
        self.assertEqual(row["input_ids"].count(inputs.EOS), len(messages))
        self.assertEqual(row["labels"].count(inputs.EOS), 2)
        self.assertNotIn(inputs.PAD, row["input_ids"])

    def test_template_pin_and_file_hash(self):
        with TemporaryDirectory() as scratch:
            directory = Path(scratch)
            for name in inputs.MODEL_FILES:
                (directory / name).symlink_to((TOKENIZER_DIR / name).resolve())
            (directory / "chat_template.jinja").write_text("wrong template")
            tokenizer = inputs.load_tokenizer(directory)
            inputs.check_tokenizer(tokenizer)
            (directory / "tokenizer_config.json").unlink()
            (directory / "tokenizer_config.json").write_text("{}")
            with self.assertRaisesRegex(inputs.InputError, "tokenizer_config.json: SHA-256 mismatch"):
                inputs.load_tokenizer(directory)
        altered = SimpleNamespace(is_fast=True, chat_template=self.tokenizer.chat_template,
                                  eos_token_id=inputs.PAD, eos_token=inputs.END)
        with self.assertRaisesRegex(inputs.InputError, "EOS/PAD"):
            inputs.check_tokenizer(altered)

    def test_length_limit_includes_template_and_eos(self):
        messages = [message("user", "hello " * 600), message("assistant", "done")]
        with self.assertRaisesRegex(inputs.InputError, r"validation\.jsonl:7: \d+ tokens exceeds the 512-token limit"):
            self.encode(messages)
        short = [message("user", "question"), message("assistant", "answer")]
        limit = len(self.encode(short)["input_ids"])
        self.assertEqual(len(self.encode(short, limit)["input_ids"]), limit)
        with self.assertRaises(inputs.InputError):
            self.encode(short, limit - 1)

    def test_empty_supervision_and_bad_labels(self):
        for labels in ([inputs.IGNORE, inputs.IGNORE], [0, inputs.EOS]):
            with self.subTest(labels=labels), self.assertRaises(inputs.InputError):
                inputs.collate_rows([{"input_ids": [9, inputs.EOS], "labels": labels}])
        with self.assertRaisesRegex(inputs.InputError, "supervised padding"):
            inputs.collate_rows([{"input_ids": [inputs.PAD, inputs.EOS], "labels": [inputs.PAD, inputs.EOS]}])

    def test_actual_trainer_batches_preserve_eos_and_mask_padding(self):
        import torch
        from transformers import Trainer, TrainingArguments

        class NoForward(torch.nn.Module):
            def forward(self, **kwargs):
                raise AssertionError("preflight must not execute a model forward")

        features = [self.encode([message("user", prompt), message("assistant", "actual answer")])
                    for prompt in ("short", "a much longer prompt with several words")]
        expected = inputs.collate_rows(features)
        with TemporaryDirectory() as scratch:
            args = train.parse_args(["--preflight", "--batch-size", "2"])
            options = gpu.trainer_options(args, None, scratch)
            trainer = Trainer(model=NoForward(), args=TrainingArguments(**options, use_cpu=True, disable_tqdm=True),
                              eval_dataset=features, train_dataset=features, data_collator=inputs.torch_collator)
            eval_batch = next(iter(trainer.get_eval_dataloader()))
            train_batch = next(iter(trainer.get_train_dataloader()))
        self.assertEqual({name: tensor.tolist() for name, tensor in eval_batch.items()}, expected)
        expected_rows = sorted(zip(expected["input_ids"], expected["attention_mask"], expected["labels"]))
        self.assertEqual(sorted(zip(*(train_batch[key].tolist() for key in expected))), expected_rows)
        self.assertTrue(all(tensor.device.type == "cpu" and tensor.dtype == torch.long for tensor in eval_batch.values()))
        for index, row in enumerate(features):
            n = len(row["input_ids"])
            self.assertEqual(expected["labels"][index][:n], row["labels"])
            self.assertEqual(expected["labels"][index][n:], [inputs.IGNORE] * (len(expected["labels"][index]) - n))
            self.assertEqual(expected["labels"][index].count(inputs.EOS), 1)
        self.assertTrue(any(0 in mask for mask in expected["attention_mask"]))


class CudaGateTests(unittest.TestCase):
    def test_cuda_failure_precedes_any_data_or_model_access(self):
        unavailable = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict(sys.modules, {"torch": unavailable}), patch.object(train, "dataset_directory") as data, \
                patch.object(train, "model_directory") as model, redirect_stderr(io.StringIO()) as diagnostic:
            self.assertEqual(train.main([]), 3)
        data.assert_not_called()
        model.assert_not_called()
        self.assertIn("CUDA is unavailable", diagnostic.getvalue())

    def test_registration_calls_are_synchronous(self):
        with TemporaryDirectory() as scratch:
            directory = Path(scratch)
            (directory / "run-manifest.json").write_text("{}\n")
            (directory / "sha256.json").write_text("{}\n")
            task, factory = Mock(), Mock()
            factory.return_value.id = "model-fixture"
            factory.return_value.update_weights_package.return_value = "http://example.invalid/qwen-lora.zip"
            args = argparse.Namespace(task_name="fixture", output_uri="http://example.invalid",
                                      dataset_id=inputs.DATASET_ID, dataset_version=inputs.DATASET_VERSION,
                                      manifest_sha256=inputs.MANIFEST_SHA256)
            result = gpu.register_output(task, factory, directory, args, {"metrics": {"optimizer_steps": 6}},
                                         {"run-manifest.json": {"sha256": "a" * 64}})
        self.assertEqual(result, "model-fixture")
        self.assertEqual(task.upload_artifact.call_count, 2)
        self.assertTrue(all(call.kwargs["wait_on_upload"] for call in task.upload_artifact.call_args_list))
        kwargs = factory.return_value.update_weights_package.call_args.kwargs
        self.assertFalse(kwargs["async_enable"])
        self.assertFalse(kwargs["auto_delete_file"])
        self.assertEqual(kwargs["iteration"], 6)


if __name__ == "__main__":
    unittest.main()

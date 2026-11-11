#!/usr/bin/env bash
# Source this file for both SDK commands and the CPU Agent.
agent_infra_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CLEARML_CONFIG_FILE="${agent_infra_dir}/.local/agent/clearml.conf"
export PATH="/root/miniconda3/envs/clearml-backend/bin:${PATH}"
export CLEARML_AGENT_SKIP_PIP_VENV_INSTALL=/root/miniconda3/envs/clearml-backend/bin/python
export CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1
export CUDA_VISIBLE_DEVICES=""
export NVIDIA_VISIBLE_DEVICES=none
export NO_PROXY="127.0.0.1,localhost,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
export PYTHONDONTWRITEBYTECODE=1

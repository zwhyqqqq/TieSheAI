#!/usr/bin/env bash
set -euo pipefail
umask 077
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
[[ -f "$CLEARML_CONFIG_FILE" ]] || { echo "Run configure_sdk.py first" >&2; exit 1; }
exec /root/miniconda3/envs/clearml-backend/bin/python -m clearml_agent daemon \
  --foreground --cpu-only --queue rail-cpu --create-queue

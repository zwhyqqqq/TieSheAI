#!/usr/bin/env bash
set -euo pipefail
infra_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
env_file="${infra_dir}/.env"
if [[ ! -f "$env_file" ]]; then
  env_file="${infra_dir}/clearml.env.example"
fi
exec docker compose --project-name tiesheai-clearml \
  --env-file "$env_file" -f "${infra_dir}/compose.yaml" "$@"

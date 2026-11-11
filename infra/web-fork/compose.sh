#!/usr/bin/env bash
set -euo pipefail
fork_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec docker compose --project-name tiesheai-web-fork -f "$fork_dir/compose.yaml" "$@"

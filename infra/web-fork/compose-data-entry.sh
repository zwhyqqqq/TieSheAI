#!/usr/bin/env bash
set -euo pipefail
fork_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export DATA_ENTRY_RELEASE="${DATA_ENTRY_RELEASE:-data-entry-20261111-v1}"
[[ "$DATA_ENTRY_RELEASE" =~ ^data-entry-[0-9]{8}-v[0-9]+$ ]] || exit 2
export FORK_RELEASE_DIR="../.local/web-fork/releases/${DATA_ENTRY_RELEASE}"
exec docker compose --project-name tiesheai-web-fork -f "$fork_dir/compose.yaml" -f "$fork_dir/compose.data-entry.yaml" "$@"

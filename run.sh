#!/usr/bin/env bash
# Wrapper around run.py that activates the project venv first.
#
#   ./run.sh
#   ./run.sh --config config.json
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/venv/bin/activate"
exec python "$DIR/run.py" "$@"

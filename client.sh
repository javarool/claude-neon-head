#!/usr/bin/env bash
# Wrapper around client.py that activates the project venv first.
#
#   ./client.sh emotion anger
#   ./client.sh say "привет, как слышно"
#   ./client.sh level 0.8 0.3
#   ./client.sh speak out.json out.wav
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/venv/bin/activate"
exec python "$DIR/client.py" "$@"

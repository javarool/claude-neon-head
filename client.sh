#!/usr/bin/env bash
# Wrapper around client.py that activates the project venv first.
#
#   ./client.sh emotion anger
#   ./client.sh say "hello, can you hear me"
#   ./client.sh level 0.8 0.3
#   ./client.sh speak timeline.json audio.wav
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/venv/bin/activate"
exec python "$DIR/client.py" "$@"

#!/usr/bin/env bash
set -Eeuo pipefail

# Usage: run-resizer.sh <profile>
# Examples:
#   run.sh home
#   run.sh batanovs
#   run.sh cherednychok

if [[ $# -lt 1 ]]; then
  echo "Error: missing profile. Usage: $0 <profile>"; exit 2
fi
PROFILE="$1"

# Resolve repo root no matter where cron runs from
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv"
PY="$VENV/bin/python"

# Bootstrap venv if missing (optional safety)
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r requirements.txt
fi

# Run your app (change app.py → main.py if you renamed it)
exec "$PY" app.py "$PROFILE"

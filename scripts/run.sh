#!/usr/bin/env bash
# Convenience runner script with environment setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export GTK_THEME="Adwaita:dark"
export PYTHONPATH="${APP_DIR}:${PYTHONPATH}"

cd "${APP_DIR}"
exec python3 "${APP_DIR}/main.py" "$@"

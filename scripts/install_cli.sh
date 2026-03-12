#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

echo "Using repo: ${ROOT_DIR}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating venv at ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

echo "Installing dependencies"
pip install -r "${ROOT_DIR}/requirements.txt"

echo "Installing CLI (editable)"
pip install -e "${ROOT_DIR}"

echo "Done. Try: xpost --help"

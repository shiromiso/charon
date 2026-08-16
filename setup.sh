#!/usr/bin/env bash

set -euo pipefail

readonly VENV_NAME=".venv"
readonly PYTHON_BIN="python3.11"
readonly PYKMIP_VERSION="0.10.0"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly VENV_DIR="${SCRIPT_DIR}/${VENV_NAME}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "error: ${PYTHON_BIN} is required but was not found" >&2
    exit 1
fi

if [[ -e "${VENV_DIR}" ]]; then
    echo "error: ${VENV_DIR} already exists" >&2
    echo "remove it first if you want to rebuild the environment" >&2
    exit 1
fi

echo "Creating virtual environment: ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"

echo "Updating Python packaging tools"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

echo "Installing PyKMIP ${PYKMIP_VERSION}"
"${VENV_DIR}/bin/python" -m pip install "PyKMIP==${PYKMIP_VERSION}"

echo "Virtual environment is ready: ${VENV_DIR}"

#!/usr/bin/env bash

set -euo pipefail

readonly VENV_NAME=".venv"
readonly PYTHON_BIN="python3.11"
readonly PYKMIP_VERSION="0.10.0"
readonly LISTEN_IP="0.0.0.0"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly VENV_DIR="${SCRIPT_DIR}/${VENV_NAME}"
readonly CHARON_IMPL="${SCRIPT_DIR}/charon_impl.py"


create_venv() {
    if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
        echo "error: ${PYTHON_BIN} is required but was not found" >&2
        exit 1
    fi

    echo "Creating virtual environment: ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"

    echo "Updating Python packaging tools"
    "${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

    echo "Installing PyKMIP ${PYKMIP_VERSION}"
    "${VENV_DIR}/bin/python" -m pip install "PyKMIP==${PYKMIP_VERSION}"

    echo "Virtual environment is ready: ${VENV_DIR}"
    echo
}


start() {
    if [[ ! -d "${VENV_DIR}" ]]; then
        create_venv
    fi

    if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
        echo "error: ${VENV_DIR} is not a valid virtual environment" >&2
        exit 1
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    exec python "${CHARON_IMPL}" serve "${LISTEN_IP}"
}


usage() {
    echo "usage: $0 start" >&2
}


if [[ $# -ne 1 ]]; then
    usage
    exit 2
fi

case "$1" in
    start)
        start
        ;;
    *)
        usage
        exit 2
        ;;
esac

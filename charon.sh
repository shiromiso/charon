#!/usr/bin/env bash

set -euo pipefail

readonly VENV_NAME="venv"
readonly PYTHON_BIN="python3.11"
readonly PYKMIP_VERSION="0.10.0"
readonly IFADDR_VERSION="0.2.0"
readonly CRYPTOGRAPHY_SPEC="cryptography<48"
readonly LISTEN_IP="0.0.0.0"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly VENV_DIR="${SCRIPT_DIR}/${VENV_NAME}"
readonly CHARON_IMPL="${SCRIPT_DIR}/charon_impl.py"
readonly CERT_DIR="${SCRIPT_DIR}/certs"
readonly STATE_DIR="${SCRIPT_DIR}/state"
readonly RUNTIME_DIR="${SCRIPT_DIR}/runtime"


create_venv() {
    if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
        echo "error: ${PYTHON_BIN} is required but was not found" >&2
        exit 1
    fi

    # Use --copies for exFAT compatability
    echo "Creating virtual environment: ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv --copies "${VENV_DIR}"

    echo "Updating Python packaging tools"
    "${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

    echo "Installing Charon Python dependencies"
    "${VENV_DIR}/bin/python" -m pip install \
        "PyKMIP==${PYKMIP_VERSION}" \
        "ifaddr==${IFADDR_VERSION}" \
        "${CRYPTOGRAPHY_SPEC}"

    echo "Virtual environment is ready: ${VENV_DIR}"
    echo
}


prepare_venv() {
    if [[ ! -d "${VENV_DIR}" ]]; then
        create_venv
    fi

    if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
        echo "error: ${VENV_DIR} is not a valid virtual environment" >&2
        exit 1
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
}


start() {
    prepare_venv
    exec python "${CHARON_IMPL}" serve "${LISTEN_IP}"
}


initialize() {
    prepare_venv
    exec python "${CHARON_IMPL}" init "$@"
}


remove_generated_path() {
    local target="$1"

    case "${target}" in
        "${VENV_DIR}"|"${CERT_DIR}"|"${STATE_DIR}"|"${RUNTIME_DIR}")
            ;;
        *)
            echo "error: refusing to remove unexpected path: ${target}" >&2
            exit 1
            ;;
    esac

    rm -rf -- "${target}"
}


delete_venv() {
    remove_generated_path "${VENV_DIR}"
}


purge() {
    local confirmation

    echo "WARNING!!!"
    echo "THIS WILL PERMANENTLY DELETE THE CHARON VIRTUAL ENVIRONMENT,"
    echo "TLS CERTIFICATES, KMIP DATABASE, AND RUNTIME DATA."
    echo "ENCRYPTED VOLUMES MAY BECOME INACCESSIBLE WITHOUT THEIR RECOVERY KEYS."
    printf "TYPE YES IN ALL CAPS TO CONTINUE: "
    read -r confirmation

    if [[ "${confirmation}" != "YES" ]]; then
        echo "Purge cancelled."
        return 1
    fi

    delete_venv
    remove_generated_path "${CERT_DIR}"
    remove_generated_path "${STATE_DIR}"
    remove_generated_path "${RUNTIME_DIR}"

    echo "Charon data purged."
}


usage() {
    echo "usage: $0 init [server_ip_or_hostname]" >&2
    echo "       $0 start" >&2
    echo "       $0 delete-venv" >&2
    echo "       $0 purge" >&2
}


if [[ $# -eq 0 ]]; then
    usage
    exit 2
fi

case "$1" in
    start)
        if [[ $# -ne 1 ]]; then
            usage
            exit 2
        fi
        start
        ;;
    init)
        if [[ $# -gt 2 ]]; then
            usage
            exit 2
        fi
        if [[ $# -eq 2 ]]; then
            initialize "$2"
        else
            initialize
        fi
        ;;
    delete-venv)
        if [[ $# -ne 1 ]]; then
            usage
            exit 2
        fi
        delete_venv
        ;;
    purge)
        if [[ $# -ne 1 ]]; then
            usage
            exit 2
        fi
        purge
        ;;
    *)
        usage
        exit 2
        ;;
esac

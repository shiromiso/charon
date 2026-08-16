#!/usr/bin/env python3
"""Charon command-line implementation."""

from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path
from typing import Sequence


CHARON_ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 5696


def ipv4_address(value: str) -> str:
    """Validate an IPv4 address while preserving argparse's error handling."""
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def port_number(value: str) -> int:
    """Parse a valid TCP port number."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="charon_impl.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="run the KMIP server")
    serve_parser.add_argument(
        "ip",
        type=ipv4_address,
        help="IPv4 address on which to listen",
    )
    serve_parser.add_argument(
        "--port",
        type=port_number,
        default=DEFAULT_PORT,
        metavar="PORT",
        help=f"KMIP port (default: {DEFAULT_PORT})",
    )
    serve_parser.set_defaults(handler=serve)

    return parser


def serve(args: argparse.Namespace) -> int:
    try:
        from kmip.services.server import KmipServer
    except ImportError as exc:
        print(
            "error: PyKMIP is not installed or could not be imported\n"
            "install the 'PyKMIP' package in Charon's Python environment",
            file=sys.stderr,
        )
        print(f"import failure: {exc}", file=sys.stderr)
        return 2

    cert_dir = CHARON_ROOT / "certs"
    state_dir = CHARON_ROOT / "state"
    runtime_dir = CHARON_ROOT / ".runtime"
    policy_dir = runtime_dir / "policy"

    certificate_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"
    ca_path = cert_dir / "ca.crt"

    missing = [
        path
        for path in (certificate_path, key_path, ca_path)
        if not path.is_file()
    ]
    if missing:
        print("error: KMIP TLS files are missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 2

    state_dir.mkdir(parents=True, exist_ok=True)
    policy_dir.mkdir(parents=True, exist_ok=True)

    server = KmipServer(
        hostname=args.ip,
        port=args.port,
        certificate_path=str(certificate_path),
        key_path=str(key_path),
        ca_path=str(ca_path),
        auth_suite="TLS1.2",
        config_path=None,
        log_path=str(runtime_dir / "pykmip.log"),
        policy_path=str(policy_dir),
        enable_tls_client_auth=True,
        logging_level="INFO",
        live_policies=False,
        database_path=str(state_dir / "pykmip.db"),
    )

    print(f"Starting KMIP server on {args.ip}:{args.port}")
    with server:
        server.serve()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

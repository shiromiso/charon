#!/usr/bin/env python3
"""Charon command-line implementation."""

from __future__ import annotations

import argparse
import ipaddress
import os
import sys
from datetime import datetime, timedelta
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

    init_parser = subparsers.add_parser(
        "init",
        help="create the KMIP certificate authority and certificates",
    )
    init_parser.add_argument(
        "server_ip",
        type=ipv4_address,
        help="IPv4 address to encode in the server certificate",
    )
    init_parser.set_defaults(handler=initialize)

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


def initialize(args: argparse.Namespace) -> int:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError as exc:
        print(
            "error: the cryptography package is not installed or could not "
            "be imported",
            file=sys.stderr,
        )
        print(f"import failure: {exc}", file=sys.stderr)
        return 2

    cert_dir = CHARON_ROOT / "certs"
    if cert_dir.exists():
        if not cert_dir.is_dir():
            print(f"error: {cert_dir} is not a directory", file=sys.stderr)
            return 1
        if any(cert_dir.iterdir()):
            print(
                f"error: {cert_dir} is not empty; refusing to overwrite it",
                file=sys.stderr,
            )
            return 1
    else:
        cert_dir.mkdir(mode=0o700)

    now = datetime.utcnow() - timedelta(minutes=1)
    ca_expires = now + timedelta(days=3650)
    certificate_expires = now + timedelta(days=1095)

    ca_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Charon KMIP CA")]
    )
    server_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Charon KMIP Server")]
    )
    client_name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Charon KMIP Client")]
    )

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(ca_expires)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(certificate_expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.IPv4Address(args.server_ip))]
            ),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    client_certificate = (
        x509.CertificateBuilder()
        .subject_name(client_name)
        .issuer_name(ca_name)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(certificate_expires)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    def private_key_pem(key: rsa.RSAPrivateKey) -> bytes:
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

    material = (
        ("ca.key", private_key_pem(ca_key), 0o600),
        ("ca.crt", ca_certificate.public_bytes(serialization.Encoding.PEM), 0o644),
        ("server.key", private_key_pem(server_key), 0o600),
        (
            "server.crt",
            server_certificate.public_bytes(serialization.Encoding.PEM),
            0o644,
        ),
        ("client.key", private_key_pem(client_key), 0o600),
        (
            "client.crt",
            client_certificate.public_bytes(serialization.Encoding.PEM),
            0o644,
        ),
    )

    created = []
    try:
        for filename, contents, mode in material:
            path = cert_dir / filename
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                mode,
            )
            created.append(path)
            with os.fdopen(descriptor, "wb") as output:
                output.write(contents)
    except OSError as exc:
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        print(f"error: failed to write certificate material: {exc}", file=sys.stderr)
        return 1

    print(f"Initialized KMIP certificate material in {cert_dir}")
    return 0


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

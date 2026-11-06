#!/usr/bin/env python3
"""Generate secure production credentials for EduTrace deployment."""

import secrets
from cryptography.fernet import Fernet
import nacl.signing


def main():
    jwt_secret = secrets.token_hex(32)
    fernet_key = Fernet.generate_key().decode()
    signing_key = nacl.signing.SigningKey.generate()
    ed25519_seed = signing_key.encode().hex()
    db_password = secrets.token_urlsafe(18)

    print("=== EduTrace Production Secrets ===")
    print("Copy and paste these values into your .env file on the production server:\n")
    print(f"POSTGRES_PASSWORD={db_password}")
    print(f"JWT_SECRET={jwt_secret}")
    print(f"FERNET_KEY={fernet_key}")
    print(f"ED25519_PRIVATE_KEY={ed25519_seed}")
    print("\n====================================")


if __name__ == "__main__":
    main()

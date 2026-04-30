from __future__ import annotations

import hashlib
import hmac
import os
import secrets


PBKDF2_ITERATIONS = 120_000


def _secret_pepper() -> bytes:
    return os.getenv("POKECABLE_SECRET_KEY", "pokecable-dev-secret-change-me").encode("utf-8")


def hash_room_password(password: str) -> str:
    password_bytes = password.encode("utf-8") + _secret_pepper()
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt.encode("ascii"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_room_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
    except ValueError:
        return False
    password_bytes = password.encode("utf-8") + _secret_pepper()
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt.encode("ascii"), iterations).hex()
    return hmac.compare_digest(digest, expected)


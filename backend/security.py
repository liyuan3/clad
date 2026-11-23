"""Password hashing and opaque token helpers.

Only hashes of tokens and pairing codes are persisted; the raw values exist
solely in the HTTP response and the runner's local disk.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

# scrypt parameters: ~16 MiB of memory per hash, deliberately slow for attackers.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCRYPT_MAXMEM = 64 * 1024 * 1024

# No 0/O/1/I so codes survive being read off a screen and typed by hand.
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_CODE_LENGTH = 8


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        maxmem=_SCRYPT_MAXMEM,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(derived)}"


def verify_password(stored: str, password: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        n_int, r_int, p_int = int(n), int(r), int(p)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n_int,
        r=r_int,
        p=p_int,
        maxmem=_SCRYPT_MAXMEM,
        dklen=len(expected),
    )
    return hmac.compare_digest(derived, expected)


# Used to keep login timing flat when the username does not exist.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def burn_password_check(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_pairing_code() -> str:
    raw = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
    return f"{raw[:4]}-{raw[4:]}"


def normalize_pairing_code(code: str) -> str | None:
    cleaned = re.sub(r"[^A-Z0-9]", "", code.upper())
    if len(cleaned) != PAIRING_CODE_LENGTH:
        return None
    return cleaned

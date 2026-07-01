from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def validate_password_policy(plain: str) -> None:
    if len(plain) < 10:
        raise ValueError("Password must be at least 10 characters.")
    if len(plain) > 128:
        raise ValueError("Password must be at most 128 characters.")
    if not re.search(r"[A-Za-z]", plain):
        raise ValueError("Password must include at least one letter.")
    if not re.search(r"\d", plain):
        raise ValueError("Password must include at least one digit.")


def hash_password(plain: str) -> str:
    validate_password_policy(plain)
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False

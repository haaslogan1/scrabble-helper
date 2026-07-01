from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9](?:[a-zA-Z0-9._%+-]{0,62}[a-zA-Z0-9])?"
    r"@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"\.[a-zA-Z]{2,63}$"
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    """Return normalized email or raise ValueError with a user-facing message."""
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError("Email is required.")
    if len(normalized) > 254:
        raise ValueError("Email is too long (max 254 characters).")
    if "@" not in normalized:
        raise ValueError("Enter a valid email address (e.g. name@example.com).")
    local, _, domain = normalized.partition("@")
    if not local or not domain:
        raise ValueError("Enter a valid email address (e.g. name@example.com).")
    if ".." in normalized or local.startswith(".") or local.endswith("."):
        raise ValueError("Email cannot contain consecutive dots or start/end with a dot.")
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError(
            "Enter a valid email address with a domain (e.g. name@example.com)."
        )
    return normalized

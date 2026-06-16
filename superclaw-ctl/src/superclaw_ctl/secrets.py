from __future__ import annotations

"""Secret generation and file-permission helpers."""

import os
from pathlib import Path
import secrets as stdlib_secrets
import stat

WEAK_TOKENS = {"", "1234qwer", "password", "secret", "admin", "test", "user"}


def generate_key(nbytes: int = 32) -> str:
    """Generate a cryptographically secure URL-safe key from nbytes of randomness."""
    return stdlib_secrets.token_urlsafe(nbytes)


def enforce_permissions(path: Path) -> None:
    """Ensure file has 0600 permissions. No-op on Windows."""
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def check_permissions(path: Path) -> bool:
    """Check if file has correct (0600) permissions. Always True on Windows."""
    if os.name == "nt":
        return True
    mode = path.stat().st_mode & 0o777
    return mode == 0o600


def is_weak_token(token: str) -> bool:
    """Check if a token is known-weak or a demo default."""
    return token.strip().lower() in WEAK_TOKENS


def validate_token_strength(token: str) -> list[str]:
    """Return warnings about token strength."""
    warnings: list[str] = []
    stripped = token.strip()
    if is_weak_token(stripped):
        warnings.append("Token matches a known weak or demo default.")
    if len(stripped) < 16:
        warnings.append("Token should be at least 16 characters long.")
    if stripped.isalpha() or stripped.isdigit():
        warnings.append("Token should mix character classes rather than using only letters or digits.")
    if stripped.lower() == stripped or stripped.upper() == stripped:
        warnings.append("Token should include mixed case or symbols for better entropy.")
    if any(ch.isspace() for ch in token):
        warnings.append("Token should not contain whitespace.")
    return warnings

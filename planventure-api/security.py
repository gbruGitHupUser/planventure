from werkzeug.security import check_password_hash, generate_password_hash

HASH_METHOD = "pbkdf2:sha256"
SALT_LENGTH = 16


def hash_password(password, salt_length=SALT_LENGTH):
    """Hash a password with a random per-password salt.

    The salt, method and iteration count are embedded in the returned string,
    so no separate salt column is needed.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string")
    return generate_password_hash(password, method=HASH_METHOD, salt_length=salt_length)


def verify_password(password_hash, password):
    """Check a password against a stored hash (constant-time comparison)."""
    if not password_hash or not isinstance(password, str):
        return False
    return check_password_hash(password_hash, password)

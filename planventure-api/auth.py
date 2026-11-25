from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError


def generate_access_token(user_id, additional_claims=None):
    """Create a short-lived access token for the given user id."""
    return create_access_token(
        identity=str(user_id), additional_claims=additional_claims
    )


def generate_refresh_token(user_id):
    """Create a long-lived refresh token for the given user id."""
    return create_refresh_token(identity=str(user_id))


def generate_tokens(user_id):
    return {
        "access_token": generate_access_token(user_id),
        "refresh_token": generate_refresh_token(user_id),
    }


def validate_token(token, expected_type="access"):
    """Decode and validate a token.

    Returns the decoded claims, or None if the token is invalid, expired,
    or not of the expected type ("access" or "refresh").
    Requires an active Flask app context.
    """
    try:
        claims = decode_token(token)
    except (JWTExtendedException, PyJWTError):
        return None
    if claims.get("type") != expected_type:
        return None
    return claims


def get_user_id_from_token(token, expected_type="access"):
    """Return the user id (int) from a valid token, otherwise None."""
    claims = validate_token(token, expected_type)
    if claims is None:
        return None
    try:
        return int(claims["sub"])
    except (KeyError, ValueError, TypeError):
        return None

from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db, jwt
from models import User


def auth_required(fn):
    """Protect a route: require a valid access token in the Authorization header.

    On success the authenticated user is available as `g.current_user`.
    Missing, invalid, expired, or refresh tokens are rejected with 401.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()  # access tokens only, read from the Authorization header

        try:
            user_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid token"}), 401

        user = db.session.get(User, user_id)
        if user is None:
            return jsonify({"error": "User no longer exists"}), 401

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


@jwt.unauthorized_loader
def _missing_token(reason):
    return jsonify({"error": "Authorization token is missing"}), 401


@jwt.invalid_token_loader
def _invalid_token(reason):
    return jsonify({"error": "Invalid token"}), 401


@jwt.expired_token_loader
def _expired_token(jwt_header, jwt_payload):
    return jsonify({"error": "Token has expired"}), 401

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from auth import generate_tokens
from extensions import db
from middleware import auth_required
from models import User
from security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Used to keep response time similar when the email does not exist.
_DUMMY_HASH = hash_password("dummy-password-1")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 255


def normalize_email(email):
    """Validate the email format and return its normalized form.

    Raises EmailNotValidError if the address is invalid.
    """
    result = validate_email(email, check_deliverability=False)
    return result.normalized.lower()


def validate_password(password):
    """Return an error message if the password is weak, otherwise None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters long"
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        return "Password must contain at least one letter and one number"
    return None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    email = data.get("email")
    password = data.get("password")

    errors = {}
    if not isinstance(email, str) or not email.strip():
        errors["email"] = "Email is required"
    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required"
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    try:
        email = normalize_email(email.strip())
    except EmailNotValidError as exc:
        return jsonify({"error": "Validation failed", "details": {"email": str(exc)}}), 400

    if len(email) > MAX_EMAIL_LENGTH:
        return (
            jsonify({"error": "Validation failed", "details": {"email": "Email is too long"}}),
            400,
        )

    password_error = validate_password(password)
    if password_error:
        return (
            jsonify({"error": "Validation failed", "details": {"password": password_error}}),
            400,
        )

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered"}), 409

    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Email is already registered"}), 409

    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user": user.to_dict(),
                **generate_tokens(user.id),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    email = data.get("email")
    password = data.get("password")

    errors = {}
    if not isinstance(email, str) or not email.strip():
        errors["email"] = "Email is required"
    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required"
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    invalid_credentials = (jsonify({"error": "Invalid email or password"}), 401)

    try:
        email = normalize_email(email.strip())
    except EmailNotValidError:
        verify_password(_DUMMY_HASH, password)
        return invalid_credentials

    user = User.query.filter_by(email=email).first()
    if user is None:
        verify_password(_DUMMY_HASH, password)
        return invalid_credentials
    if not user.check_password(password):
        return invalid_credentials

    return jsonify(
        {
            "message": "Login successful",
            "user": user.to_dict(),
            **generate_tokens(user.id),
        }
    )


@auth_bp.route("/me", methods=["GET"])
@auth_required
def me():
    return jsonify({"user": g.current_user.to_dict()})

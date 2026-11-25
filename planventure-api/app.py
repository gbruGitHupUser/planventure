import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from extensions import db, jwt

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'planventure.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_DAYS", "30"))
    )
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    from auth_routes import auth_bp

    app.register_blueprint(auth_bp)

    @app.route("/")
    def home():
        return jsonify({"message": "Welcome to PlanVenture API"})

    @app.route("/health")
    def health_check():
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])

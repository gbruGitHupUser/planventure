from app import app
from extensions import db
import models  # noqa: F401  (registers models with SQLAlchemy metadata)


def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created:")
        for table in db.metadata.sorted_tables:
            print(f" - {table.name}")


if __name__ == "__main__":
    init_db()

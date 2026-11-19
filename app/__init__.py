import os

from flask import Flask, render_template
from dotenv import load_dotenv
from sqlalchemy.engine import URL
from .extensions import db, migrate


def create_app(test_config=None):
    # Load environment variables from the project-root .env file.
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)

    # Build the database URL safely, including passwords with special characters.
    database_url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "cloud_voting_db"),
        query={"charset": "utf8mb4"},
    )

    # Configure Flask and SQLAlchemy.
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Apply test configuration if provided.
    if test_config:
        app.config.update(test_config)

    # Initialize database and migration extensions.
    db.init_app(app)
    migrate.init_app(app, db)
    from .routes import auth_bp
    from .web_routes import web_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)

    # Import models so SQLAlchemy and Flask-Migrate can discover them.
    from . import models  # noqa: F401

    @app.get("/")
    def index():
        return render_template("index.html")
    return app

import os
import sys

from flask import Flask, jsonify

from app.config import config_by_name, Config
from app.extensions import db, login_manager, csrf


def create_app(config_name: str = None) -> Flask:
    """Application factory for the Smart Logistics Management System."""

    app = Flask(__name__)

    # Determine configuration environment
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app.config.from_object(config_by_name.get(config_name, Config))

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure user loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Database initialization command
    @app.cli.command("init-db")
    def init_db_command():
        """Creates all database tables based on SQLAlchemy models."""

        import app.models  # noqa: F401

        try:
            db.create_all()
            print("Successfully initialized all database tables in MySQL!")

        except Exception as exc:
            print(f"Error during database initialization: {exc}", file=sys.stderr)
            print("\nTroubleshooting tips:", file=sys.stderr)
            print("1. Ensure MySQL service is running.", file=sys.stderr)
            print("2. Ensure the database specified in .env exists.", file=sys.stderr)
            print("3. Check your DB_USER and DB_PASSWORD credentials in .env.", file=sys.stderr)
            sys.exit(1)

    # Health check route
    @app.route("/api/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "phase": "Phase 1 & Phase 2 - Architecture, Auth & Core Inventory",
            "database_target": app.config.get(
                "SQLALCHEMY_DATABASE_URI"
            ).split("@")[-1],
        })

    # Register Blueprints
    from app.routes import (
        auth_bp,
        dashboard_bp,
        warehouse_bp,
        inventory_bp,
        stock_bp,
        fleet_bp,
        order_bp,
        dispatch_bp,
        ai_bp,
        analytics_bp,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(fleet_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(analytics_bp)

    return app

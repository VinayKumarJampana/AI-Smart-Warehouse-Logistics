from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Global extension instances
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Configuration for Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access this page."
login_manager.login_message_category = "warning"

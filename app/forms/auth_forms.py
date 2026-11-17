from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from app.models.user import User


class LoginForm(FlaskForm):
    """User authentication login form."""
    username_or_email = StringField(
        "Username or Email",
        validators=[DataRequired(message="Please enter your username or email."), Length(max=120)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please enter your password.")],
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    """Public user registration form (role is determined strictly on the backend)."""
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=50, message="Username must be between 3 and 50 characters."),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email is required."),
            Regexp(
                r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                message="Please enter a valid email address.",
            ),
            Length(max=120),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=6, max=100, message="Password must be at least 6 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register Account")

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data.strip()).first()
        if user:
            raise ValidationError("This username is already taken. Please choose another.")

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError("This email is already registered. Please sign in or use another.")


class AdminUserCreateForm(FlaskForm):
    """Admin-only form for creating staff accounts with privileged role assignment."""
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=50, message="Username must be between 3 and 50 characters."),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email is required."),
            Regexp(
                r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                message="Please enter a valid email address.",
            ),
            Length(max=120),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=6, max=100, message="Password must be at least 6 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    role = SelectField(
        "Assigned Role",
        choices=[
            ("admin", "System Administrator"),
            ("warehouse_manager", "Warehouse Manager"),
            ("logistics_coordinator", "Logistics Coordinator"),
        ],
        default="logistics_coordinator",
        validators=[DataRequired()],
    )
    submit = SubmitField("Create Staff Account")

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data.strip()).first()
        if user:
            raise ValidationError("This username is already taken.")

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError("This email is already registered.")


class AdminUserEditRoleForm(FlaskForm):
    """Admin-only form for updating an existing user's role and status."""
    role = SelectField(
        "Role",
        choices=[
            ("admin", "System Administrator"),
            ("warehouse_manager", "Warehouse Manager"),
            ("logistics_coordinator", "Logistics Coordinator"),
        ],
        validators=[DataRequired()],
    )
    is_active = BooleanField("Account Active")
    submit = SubmitField("Update Role & Status")

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.forms.auth_forms import (
    LoginForm,
    RegisterForm,
    AdminUserCreateForm,
    AdminUserEditRoleForm,
)
from app.utils.decorators import role_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login view."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.username_or_email.data.strip()
        password = form.password.data

        # Allow sign in with either username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact an administrator.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.username}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))
        else:
            flash("Invalid username/email or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Public registration endpoint.
    SECURITY POLICY:
    - Only the very first user registered in the system is granted the 'admin' role.
    - All subsequent public registrations are strictly assigned a safe default role ('logistics_coordinator').
    - Public requests cannot specify, override, or request the 'admin' role.
    """
    form = RegisterForm()
    is_first_user = User.query.count() == 0

    if form.validate_on_submit():
        # Enforce server-side role assignment; never trust client input for privilege level
        assigned_role = "admin" if is_first_user else "logistics_coordinator"

        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=assigned_role,
            is_active=True,
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
            if is_first_user:
                flash(
                    f"Initial administrator account '{user.username}' created successfully! Please sign in.",
                    "success",
                )
            else:
                flash(
                    f"Account created successfully for '{user.username}' with role '{user.role}'. "
                    f"Please sign in. To request higher privileges, contact an administrator.",
                    "success",
                )
            return redirect(url_for("auth.login"))
        except Exception as exc:
            db.session.rollback()
            flash(f"An error occurred while creating the account: {exc}", "danger")

    return render_template("auth/register.html", form=form, is_first_user=is_first_user)


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    """User logout view."""
    username = current_user.username
    logout_user()
    flash(f"You have been signed out. Goodbye, {username}!", "info")
    return redirect(url_for("auth.login"))


# ==============================================================================
# ADMIN USER & STAFF MANAGEMENT ROUTES
# ==============================================================================


@auth_bp.route("/users")
@login_required
@role_required("admin")
def list_users():
    """Admin-only view to list all registered users, roles, and status."""
    users = User.query.order_by(User.created_at.asc()).all()
    return render_template("auth/users.html", users=users)


@auth_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def create_staff():
    """Admin-only view to create internal staff accounts with explicit role assignment."""
    form = AdminUserCreateForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            is_active=True,
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
            flash(
                f"Staff account '{user.username}' ({user.role}) created successfully!",
                "success",
            )
            return redirect(url_for("auth.list_users"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating staff user: {exc}", "danger")

    return render_template("auth/user_create.html", form=form)


@auth_bp.route("/users/<int:id>/edit-role", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_user_role(id):
    """Admin-only view to update a user's role or active status."""
    target_user = db.get_or_404(User, id)
    form = AdminUserEditRoleForm(obj=target_user)

    if form.validate_on_submit():
        # Prevent admin from demoting or deactivating their own currently logged-in account
        if target_user.id == current_user.id:
            if form.role.data != "admin" or not form.is_active.data:
                flash("You cannot demote or deactivate your own administrator account.", "danger")
                return redirect(url_for("auth.list_users"))

        target_user.role = form.role.data
        target_user.is_active = form.is_active.data

        try:
            db.session.commit()
            flash(
                f"User '{target_user.username}' updated: Role = {target_user.role}, Active = {target_user.is_active}.",
                "success",
            )
            return redirect(url_for("auth.list_users"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating user: {exc}", "danger")

    return render_template("auth/user_edit_role.html", form=form, user=target_user)

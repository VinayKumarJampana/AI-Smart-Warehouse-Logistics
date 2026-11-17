from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def role_required(*roles):
    """Decorator to enforce role-based access control on routes."""

    def decorator(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("auth.login"))

            if current_user.role not in roles:
                flash(
                    f"Access restricted. You need '{', '.join(roles)}' permissions to perform this action.",
                    "danger",
                )
                return redirect(url_for("dashboard.index"))

            return fn(*args, **kwargs)

        return decorated_view

    return decorator


def admin_required(fn):
    """Convenience decorator for admin-only routes."""
    return role_required("admin")(fn)

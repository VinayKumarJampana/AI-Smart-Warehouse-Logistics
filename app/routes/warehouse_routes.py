from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.warehouse import Warehouse
from app.forms.warehouse_forms import WarehouseForm
from app.utils.decorators import role_required

warehouse_bp = Blueprint("warehouse", __name__, url_prefix="/warehouses")


@warehouse_bp.route("/")
@login_required
def index():
    """List all warehouses with capacity metrics."""
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Warehouse.query
    if search_query:
        query = query.filter(
            (Warehouse.code.ilike(f"%{search_query}%"))
            | (Warehouse.name.ilike(f"%{search_query}%"))
            | (Warehouse.location.ilike(f"%{search_query}%"))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)

    warehouses = query.order_by(Warehouse.code.asc()).all()
    return render_template(
        "warehouse/list.html",
        warehouses=warehouses,
        search_query=search_query,
        status_filter=status_filter,
    )


@warehouse_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def create():
    """Create a new warehouse facility."""
    form = WarehouseForm()
    if form.validate_on_submit():
        warehouse = Warehouse(
            code=form.code.data.strip().upper(),
            name=form.name.data.strip(),
            location=form.location.data.strip(),
            address=form.address.data.strip() if form.address.data else None,
            total_capacity_sqft=form.total_capacity_sqft.data,
            status=form.status.data,
        )
        try:
            db.session.add(warehouse)
            db.session.commit()
            flash(f"Warehouse '{warehouse.name}' ({warehouse.code}) created successfully!", "success")
            return redirect(url_for("warehouse.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating warehouse: {exc}", "danger")

    return render_template("warehouse/form.html", form=form, title="Create Warehouse", is_edit=False)


@warehouse_bp.route("/<int:id>")
@login_required
def detail(id):
    """View warehouse details and assigned inventory items."""
    warehouse = db.get_or_404(Warehouse, id)
    products = warehouse.products.all()
    return render_template("warehouse/detail.html", warehouse=warehouse, products=products)


@warehouse_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def edit(id):
    """Update warehouse details."""
    warehouse = db.get_or_404(Warehouse, id)
    form = WarehouseForm(original_code=warehouse.code, obj=warehouse)

    if form.validate_on_submit():
        warehouse.code = form.code.data.strip().upper()
        warehouse.name = form.name.data.strip()
        warehouse.location = form.location.data.strip()
        warehouse.address = form.address.data.strip() if form.address.data else None
        warehouse.total_capacity_sqft = form.total_capacity_sqft.data
        warehouse.status = form.status.data

        try:
            db.session.commit()
            flash(f"Warehouse '{warehouse.name}' updated successfully!", "success")
            return redirect(url_for("warehouse.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating warehouse: {exc}", "danger")

    return render_template(
        "warehouse/form.html",
        form=form,
        title=f"Edit Warehouse: {warehouse.code}",
        is_edit=True,
        warehouse=warehouse,
    )


@warehouse_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(id):
    """Delete a warehouse facility with relational integrity guard."""
    warehouse = db.get_or_404(Warehouse, id)

    # Defensive check: ensure no active products are associated with this warehouse
    if warehouse.products.count() > 0:
        flash(
            f"Cannot delete warehouse '{warehouse.name}' because it contains {warehouse.products.count()} active product(s). "
            f"Please reassign or delete the products first.",
            "danger",
        )
        return redirect(url_for("warehouse.index"))

    try:
        db.session.delete(warehouse)
        db.session.commit()
        flash(f"Warehouse '{warehouse.name}' deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error deleting warehouse: {exc}", "danger")

    return redirect(url_for("warehouse.index"))

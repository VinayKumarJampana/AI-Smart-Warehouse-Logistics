from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.stock_transaction import StockTransaction
from app.forms.inventory_forms import CategoryForm, ProductForm
from app.utils.decorators import role_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


# ==============================================================================
# PRODUCT CATALOG ROUTES
# ==============================================================================


@inventory_bp.route("/")
@login_required
def index():
    """List products with search, category filtering, and low stock highlights."""
    search_query = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", type=int)
    warehouse_id = request.args.get("warehouse_id", type=int)
    low_stock_only = request.args.get("low_stock", "").lower() in ("1", "true", "yes")

    query = Product.query
    if search_query:
        query = query.filter(
            (Product.name.ilike(f"%{search_query}%"))
            | (Product.sku.ilike(f"%{search_query}%"))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    if warehouse_id:
        query = query.filter_by(warehouse_id=warehouse_id)
    if low_stock_only:
        query = query.filter(Product.current_stock <= Product.min_threshold)

    products = query.order_by(Product.name.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    warehouses = Warehouse.query.order_by(Warehouse.name.asc()).all()

    return render_template(
        "inventory/list.html",
        products=products,
        categories=categories,
        warehouses=warehouses,
        search_query=search_query,
        selected_category=category_id,
        selected_warehouse=warehouse_id,
        low_stock_only=low_stock_only,
    )


@inventory_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def create():
    """Create a new product SKU."""
    form = ProductForm()

    # Populate dynamic select choices
    categories = Category.query.order_by(Category.name.asc()).all()
    warehouses = Warehouse.query.filter_by(status="active").order_by(Warehouse.name.asc()).all()

    if not categories:
        flash("Please create at least one product category before adding products.", "warning")
        return redirect(url_for("inventory.categories"))
    if not warehouses:
        flash("Please create at least one active warehouse before adding products.", "warning")
        return redirect(url_for("warehouse.create"))

    form.category_id.choices = [(c.id, c.name) for c in categories]
    form.warehouse_id.choices = [(w.id, f"{w.name} ({w.code})") for w in warehouses]

    if form.validate_on_submit():
        product = Product(
            sku=form.sku.data.strip().upper(),
            name=form.name.data.strip(),
            category_id=form.category_id.data,
            warehouse_id=form.warehouse_id.data,
            unit=form.unit.data,
            cost_price=Decimal(str(form.cost_price.data)),
            unit_price=Decimal(str(form.unit_price.data)),
            current_stock=form.current_stock.data or 0,
            min_threshold=form.min_threshold.data,
            max_capacity=form.max_capacity.data,
            lead_time_days=form.lead_time_days.data,
        )

        try:
            db.session.add(product)
            db.session.flush()

            # If initial stock was provided, record initial stock transaction
            if product.current_stock > 0:
                from flask_login import current_user
                initial_txn = StockTransaction(
                    product_id=product.id,
                    warehouse_id=product.warehouse_id,
                    transaction_type="STOCK_IN",
                    quantity=product.current_stock,
                    balance_after=product.current_stock,
                    reference_no="INIT-SETUP",
                    notes="Initial stock quantity on product creation",
                    created_by=current_user.id,
                )
                db.session.add(initial_txn)

            db.session.commit()
            flash(f"Product '{product.name}' ({product.sku}) added successfully!", "success")
            return redirect(url_for("inventory.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error adding product: {exc}", "danger")

    return render_template(
        "inventory/form.html",
        form=form,
        title="Add New Product",
        is_edit=False,
    )


@inventory_bp.route("/<int:id>")
@login_required
def detail(id):
    """View product details, valuation, thresholds, and recent transaction history."""
    product = db.get_or_404(Product, id)
    transactions = (
        product.stock_transactions.order_by(StockTransaction.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template("inventory/detail.html", product=product, transactions=transactions)


@inventory_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def edit(id):
    """Update product information and thresholds."""
    product = db.get_or_404(Product, id)
    form = ProductForm(original_sku=product.sku, obj=product)

    categories = Category.query.order_by(Category.name.asc()).all()
    warehouses = Warehouse.query.order_by(Warehouse.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    form.warehouse_id.choices = [(w.id, f"{w.name} ({w.code})") for w in warehouses]

    if form.validate_on_submit():
        product.sku = form.sku.data.strip().upper()
        product.name = form.name.data.strip()
        product.category_id = form.category_id.data
        product.warehouse_id = form.warehouse_id.data
        product.unit = form.unit.data
        product.cost_price = Decimal(str(form.cost_price.data))
        product.unit_price = Decimal(str(form.unit_price.data))
        product.min_threshold = form.min_threshold.data
        product.max_capacity = form.max_capacity.data
        product.lead_time_days = form.lead_time_days.data

        try:
            db.session.commit()
            flash(f"Product '{product.name}' updated successfully!", "success")
            return redirect(url_for("inventory.index"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating product: {exc}", "danger")

    return render_template(
        "inventory/form.html",
        form=form,
        title=f"Edit Product: {product.sku}",
        is_edit=True,
        product=product,
    )


@inventory_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(id):
    """Delete a product SKU."""
    product = db.get_or_404(Product, id)

    # Check for active order items
    if product.order_items.count() > 0:
        flash(
            f"Cannot delete product '{product.name}' because customer orders depend on it.",
            "danger",
        )
        return redirect(url_for("inventory.index"))

    try:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product.name}' ({product.sku}) deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error deleting product: {exc}", "danger")

    return redirect(url_for("inventory.index"))


# ==============================================================================
# CATEGORY MANAGEMENT ROUTES
# ==============================================================================


@inventory_bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    """List categories and provide in-page create modal/form."""
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
        )
        try:
            db.session.add(category)
            db.session.commit()
            flash(f"Category '{category.name}' created successfully!", "success")
            return redirect(url_for("inventory.categories"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating category: {exc}", "danger")

    all_categories = Category.query.order_by(Category.name.asc()).all()
    return render_template("inventory/categories.html", categories=all_categories, form=form)


@inventory_bp.route("/categories/<int:id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def edit_category(id):
    """Edit an existing category."""
    category = db.get_or_404(Category, id)
    form = CategoryForm(original_name=category.name, obj=category)

    if form.validate_on_submit():
        category.name = form.name.data.strip()
        category.description = form.description.data.strip() if form.description.data else None
        try:
            db.session.commit()
            flash(f"Category '{category.name}' updated successfully!", "success")
            return redirect(url_for("inventory.categories"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating category: {exc}", "danger")

    all_categories = Category.query.order_by(Category.name.asc()).all()
    return render_template(
        "inventory/categories.html",
        categories=all_categories,
        form=form,
        editing_category=category,
    )


@inventory_bp.route("/categories/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_category(id):
    """Delete category with referential check."""
    category = db.get_or_404(Category, id)
    if category.products.count() > 0:
        flash(
            f"Cannot delete category '{category.name}' because {category.products.count()} product(s) are assigned to it.",
            "danger",
        )
        return redirect(url_for("inventory.categories"))

    try:
        db.session.delete(category)
        db.session.commit()
        flash(f"Category '{category.name}' deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error deleting category: {exc}", "danger")

    return redirect(url_for("inventory.categories"))

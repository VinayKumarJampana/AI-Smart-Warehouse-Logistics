from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.order import Order
from app.models.product import Product
from app.forms.order_forms import OrderCreateForm, OrderItemAddForm
from app.services.logistics_service import LogisticsService
from app.utils.decorators import role_required

order_bp = Blueprint("orders", __name__, url_prefix="/orders")


@order_bp.route("/")
@login_required
def index():
    """List customer orders with status filter and search."""
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Order.query
    if search_query:
        query = query.filter(
            (Order.order_number.ilike(f"%{search_query}%"))
            | (Order.customer_name.ilike(f"%{search_query}%"))
            | (Order.customer_email.ilike(f"%{search_query}%"))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(Order.order_date.desc()).all()
    return render_template(
        "orders/list.html",
        orders=orders,
        search_query=search_query,
        status_filter=status_filter,
    )


@order_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator", "warehouse_manager")
def create():
    """Create a new customer order."""
    form = OrderCreateForm()
    products = Product.query.order_by(Product.name.asc()).all()

    if not products:
        flash("Please add inventory products before creating orders.", "warning")
        return redirect(url_for("inventory.create"))

    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku}) — In Stock: {p.current_stock} {p.unit} @ ${p.unit_price}")
        for p in products
    ]

    if form.validate_on_submit():
        try:
            order = LogisticsService.create_order(
                customer_name=form.customer_name.data,
                customer_email=form.customer_email.data,
                customer_phone=form.customer_phone.data,
                delivery_address=form.delivery_address.data,
                expected_delivery_date=form.expected_delivery_date.data,
                product_id=form.product_id.data,
                quantity=form.quantity.data,
            )
            flash(
                f"Customer Order '{order.order_number}' created successfully! Total: ${order.total_amount:,.2f}.",
                "success",
            )
            return redirect(url_for("orders.detail", id=order.id))
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error creating order: {exc}", "danger")

    return render_template("orders/create.html", form=form)


@order_bp.route("/<int:id>")
@login_required
def detail(id):
    """View customer order details, line items, and fulfillment actions."""
    order = db.get_or_404(Order, id)
    add_item_form = OrderItemAddForm()

    products = Product.query.order_by(Product.name.asc()).all()
    add_item_form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku}) — In Stock: {p.current_stock} {p.unit} @ ${p.unit_price}")
        for p in products
    ]

    return render_template(
        "orders/detail.html",
        order=order,
        add_item_form=add_item_form,
    )


@order_bp.route("/<int:id>/add-item", methods=["POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def add_item(id):
    """Add additional line item to a pending order."""
    order = db.get_or_404(Order, id)
    form = OrderItemAddForm()

    products = Product.query.order_by(Product.name.asc()).all()
    form.product_id.choices = [(p.id, p.name) for p in products]

    if form.validate_on_submit():
        try:
            LogisticsService.add_order_item(
                order_id=order.id,
                product_id=form.product_id.data,
                quantity=form.quantity.data,
            )
            flash("Item added to order successfully!", "success")
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error adding item: {exc}", "danger")

    return redirect(url_for("orders.detail", id=order.id))


@order_bp.route("/<int:id>/approve", methods=["POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def approve(id):
    """Approve order for dispatch after validating inventory."""
    try:
        order = LogisticsService.approve_order(id)
        flash(f"Order '{order.order_number}' has been approved and is ready for dispatch!", "success")
    except ValueError as val_err:
        flash(str(val_err), "danger")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error approving order: {exc}", "danger")

    return redirect(url_for("orders.detail", id=id))


@order_bp.route("/<int:id>/cancel", methods=["POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def cancel(id):
    """Cancel customer order."""
    try:
        order = LogisticsService.cancel_order(id)
        flash(f"Order '{order.order_number}' has been cancelled.", "info")
    except ValueError as val_err:
        flash(str(val_err), "danger")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error cancelling order: {exc}", "danger")

    return redirect(url_for("orders.detail", id=id))

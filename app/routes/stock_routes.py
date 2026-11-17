from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.product import Product
from app.models.stock_transaction import StockTransaction
from app.forms.stock_forms import StockInForm, StockOutForm
from app.services.inventory_service import InventoryService
from app.utils.decorators import role_required

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")


@stock_bp.route("/in", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager")
def stock_in():
    """Record inbound stock receipt."""
    form = StockInForm()
    products = Product.query.order_by(Product.name.asc()).all()

    if not products:
        flash("No products found. Please add products before recording stock receipts.", "warning")
        return redirect(url_for("inventory.create"))

    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku}) — Available: {p.current_stock} {p.unit}")
        for p in products
    ]

    # Pre-select product if passed via query param
    preselected_id = request.args.get("product_id", type=int)
    if request.method == "GET" and preselected_id:
        form.product_id.data = preselected_id

    if form.validate_on_submit():
        try:
            txn, product = InventoryService.process_stock_in(
                product_id=form.product_id.data,
                quantity=form.quantity.data,
                user_id=current_user.id,
                reference_no=form.reference_no.data,
                notes=form.notes.data,
            )
            flash(
                f"Successfully added {txn.quantity} {product.unit} to '{product.name}'. "
                f"New Balance: {product.current_stock} {product.unit}.",
                "success",
            )
            return redirect(url_for("stock.history"))
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            flash(f"Unexpected error processing stock in: {exc}", "danger")

    return render_template("stock/stock_in.html", form=form)


@stock_bp.route("/out", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager", "logistics_coordinator")
def stock_out():
    """Record outbound stock removal / dispatch."""
    form = StockOutForm()
    products = Product.query.order_by(Product.name.asc()).all()

    if not products:
        flash("No products available to dispatch.", "warning")
        return redirect(url_for("inventory.index"))

    form.product_id.choices = [
        (p.id, f"{p.name} ({p.sku}) — In Stock: {p.current_stock} {p.unit}")
        for p in products
    ]

    preselected_id = request.args.get("product_id", type=int)
    if request.method == "GET" and preselected_id:
        form.product_id.data = preselected_id

    if form.validate_on_submit():
        try:
            txn, product = InventoryService.process_stock_out(
                product_id=form.product_id.data,
                quantity=form.quantity.data,
                user_id=current_user.id,
                reference_no=form.reference_no.data,
                notes=form.notes.data,
            )
            flash(
                f"Successfully removed {txn.quantity} {product.unit} from '{product.name}'. "
                f"Remaining Stock: {product.current_stock} {product.unit}.",
                "success",
            )
            return redirect(url_for("stock.history"))
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            flash(f"Unexpected error processing stock out: {exc}", "danger")

    return render_template("stock/stock_out.html", form=form)


@stock_bp.route("/history")
@login_required
def history():
    """View complete immutable audit trail of inventory movements."""
    txn_type = request.args.get("type", "").strip()
    product_id = request.args.get("product_id", type=int)
    page = request.args.get("page", 1, type=int)

    query = StockTransaction.query
    if txn_type in ("STOCK_IN", "STOCK_OUT", "ADJUSTMENT"):
        query = query.filter_by(transaction_type=txn_type)
    if product_id:
        query = query.filter_by(product_id=product_id)

    # Order newest first
    transactions = (
        query.order_by(StockTransaction.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    products = Product.query.order_by(Product.name.asc()).all()

    return render_template(
        "stock/history.html",
        transactions=transactions,
        products=products,
        selected_type=txn_type,
        selected_product=product_id,
    )

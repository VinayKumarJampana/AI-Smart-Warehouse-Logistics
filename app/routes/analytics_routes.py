
from datetime import datetime
from collections import defaultdict

from flask import Blueprint, render_template
from flask_login import login_required

from app.extensions import db
from app.models.order import Order
from app.models.stock_transaction import StockTransaction
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.models.forecast_metric import ForecastMetric
from app.utils.decorators import role_required


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
@role_required("admin", "warehouse_manager", "logistics_coordinator")
def index():

    # Order analytics
    orders = Order.query.all()

    total_orders = len(orders)
    delivered_orders = sum(1 for order in orders if order.status == "DELIVERED")
    pending_orders = sum(1 for order in orders if order.status == "PENDING")

    total_revenue = sum(
        (order.total_amount or 0)
        for order in orders
        if order.status == "DELIVERED"
    )

    # Monthly delivered sales - last 6 months
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_labels = []
    monthly_sales = []

    for offset in range(5, -1, -1):
        month_index = current_month.month - offset
        year = current_month.year

        while month_index <= 0:
            month_index += 12
            year -= 1

        month_start = datetime(year, month_index, 1)

        if month_index == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month_index + 1, 1)

        amount = sum(
            float(order.total_amount or 0)
            for order in orders
            if order.status == "DELIVERED"
            and month_start <= order.order_date < month_end
        )

        monthly_labels.append(month_start.strftime("%b %Y"))
        monthly_sales.append(round(amount, 2))

    # Stock movement analytics
    transactions = StockTransaction.query.all()

    stock_in = sum(
        txn.quantity for txn in transactions
        if txn.transaction_type == "STOCK_IN"
    )

    stock_out = sum(
        txn.quantity for txn in transactions
        if txn.transaction_type == "STOCK_OUT"
    )

    adjustments = sum(
        1 for txn in transactions
        if txn.transaction_type == "ADJUSTMENT"
    )

    # Warehouse inventory analytics
    warehouses = Warehouse.query.all()
    products = Product.query.all()

    warehouse_labels = []
    warehouse_stock = []

    for warehouse in warehouses:
        warehouse_labels.append(warehouse.name)

        quantity = sum(
            product.current_stock or 0
            for product in products
            if product.warehouse_id == warehouse.id
        )

        warehouse_stock.append(quantity)

    # AI forecast analytics
    forecast_records = ForecastMetric.query.all()

    forecast_summary = {
        "total": len(forecast_records),
        "critical": sum(1 for item in forecast_records if item.urgency_status == "CRITICAL"),
        "moderate": sum(1 for item in forecast_records if item.urgency_status == "MODERATE"),
        "safe": sum(1 for item in forecast_records if item.urgency_status == "SAFE"),
    }

    latest_forecasts = (
        ForecastMetric.query
        .order_by(ForecastMetric.last_evaluated_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "analytics/index.html",
        total_orders=total_orders,
        delivered_orders=delivered_orders,
        pending_orders=pending_orders,
        total_revenue=float(total_revenue),
        monthly_labels=monthly_labels,
        monthly_sales=monthly_sales,
        stock_in=stock_in,
        stock_out=stock_out,
        adjustments=adjustments,
        warehouse_labels=warehouse_labels,
        warehouse_stock=warehouse_stock,
        forecast_summary=forecast_summary,
        latest_forecasts=latest_forecasts,
    )

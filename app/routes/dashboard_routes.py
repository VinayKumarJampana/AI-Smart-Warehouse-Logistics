
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.services.inventory_service import InventoryService
from app.models.stock_transaction import StockTransaction
from app.models.warehouse import Warehouse
from app.models.dispatch import Dispatch
from app.models.order import Order
from app.models.fleet import Vehicle
from app.models.forecast_metric import ForecastMetric


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    """Root redirect to dashboard if authenticated, else login."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """Main executive logistics and AI analytics dashboard."""

    # Inventory KPIs
    kpis = InventoryService.get_inventory_summary()

    # Operations metrics
    kpis["active_dispatches"] = Dispatch.query.filter(
        Dispatch.status.in_(("DISPATCHED", "IN_TRANSIT"))
    ).count()

    kpis["pending_orders"] = Order.query.filter_by(
        status="PENDING"
    ).count()

    kpis["available_vehicles"] = Vehicle.query.filter_by(
        status="AVAILABLE"
    ).count()

    # Recent stock activity
    recent_transactions = (
        StockTransaction.query
        .order_by(StockTransaction.created_at.desc())
        .limit(8)
        .all()
    )

    # Warehouse overview
    warehouses = Warehouse.query.all()

    # Active dispatches
    active_dispatches = (
        Dispatch.query
        .filter(Dispatch.status.in_(("DISPATCHED", "IN_TRANSIT")))
        .order_by(Dispatch.dispatch_time.desc())
        .limit(5)
        .all()
    )

    # AI Forecast Analytics
    forecast_query = ForecastMetric.query

    kpis["total_forecasts"] = forecast_query.count()

    kpis["critical_forecasts"] = forecast_query.filter_by(
        urgency_status="CRITICAL"
    ).count()

    kpis["moderate_forecasts"] = forecast_query.filter_by(
        urgency_status="MODERATE"
    ).count()

    kpis["safe_forecasts"] = forecast_query.filter_by(
        urgency_status="SAFE"
    ).count()

    latest_forecasts = (
        forecast_query
        .order_by(ForecastMetric.last_evaluated_at.desc())
        .limit(5)
        .all()
    )

    latest_forecast = (
        forecast_query
        .order_by(ForecastMetric.last_evaluated_at.desc())
        .first()
    )

    forecast_summary = {
        "total_forecasts": kpis["total_forecasts"],
        "critical": kpis["critical_forecasts"],
        "moderate": kpis["moderate_forecasts"],
        "safe": kpis["safe_forecasts"],
        "latest": latest_forecast,
    }

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        recent_transactions=recent_transactions,
        warehouses=warehouses,
        active_dispatches=active_dispatches,
        latest_forecasts=latest_forecasts,
        forecast_summary=forecast_summary,
    )

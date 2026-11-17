
from flask import Blueprint, render_template, flash, request
from flask_login import login_required

from app.extensions import db
from app.models.product import Product
from app.models.forecast_metric import ForecastMetric
from app.utils.decorators import role_required
from app.services.forecast_service import ForecastService


ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@ai_bp.route("/forecast", methods=["GET", "POST"])
@login_required
@role_required("admin", "warehouse_manager", "logistics_coordinator")
def forecast():
    """Generate and save AI-powered product demand forecasts."""

    products = Product.query.order_by(Product.name.asc()).all()
    result = None

    if request.method == "POST":
        try:
            product_id = request.form.get("product_id", type=int)
            days = request.form.get("days", default=30, type=int)

            if not product_id:
                raise ValueError("Please select a product.")

            product = db.session.get(Product, product_id)

            if product is None:
                raise ValueError("Selected product was not found.")

            # Generate demand forecast and inventory metrics
            result = ForecastService.generate_forecast(
                store_id=product.warehouse_id,
                item_id=product.id,
                days=days,
                lead_time_days=product.lead_time_days,
            )

            model_data = ForecastService.load_model()

            predicted_demand = result["predicted_demand"]
            safety_stock = result["safety_stock"]
            reorder_point = result["reorder_point"]

            # Recommended stock target for selected forecast period
            target_stock = predicted_demand + safety_stock

            reorder_quantity = max(
                0,
                target_stock - product.current_stock,
            )

            result["reorder_quantity"] = reorder_quantity
            result["product_name"] = product.name

            if product.current_stock <= reorder_point:
                urgency = "CRITICAL"
            elif reorder_quantity > 0:
                urgency = "MODERATE"
            else:
                urgency = "SAFE"

            forecast_record = ForecastMetric(
                product_id=product.id,
                model_name=model_data["model_name"],
                forecast_days=days,
                predicted_demand=predicted_demand,
                mae=result["mae"],
                rmse=result["rmse"],
                train_size=model_data["train_size"],
                test_size=model_data["test_size"],
                predicted_demand_next_7d=(
                    predicted_demand if days == 7 else 0
                ),
                predicted_demand_next_30d=(
                    predicted_demand if days == 30 else 0
                ),
                calculated_safety_stock=safety_stock,
                reorder_point=reorder_point,
                recommended_reorder_qty=reorder_quantity,
                urgency_status=urgency,
            )

            db.session.add(forecast_record)
            db.session.commit()

            flash(
                "Demand forecast generated and saved successfully!",
                "success",
            )

        except (ValueError, FileNotFoundError) as exc:
            db.session.rollback()
            flash(str(exc), "warning")

        except Exception as exc:
            db.session.rollback()
            flash(f"Forecast generation failed: {exc}", "danger")

    return render_template(
        "ai/forecast.html",
        products=products,
        forecast=result,
    )


@ai_bp.route("/history")
@login_required
@role_required("admin", "warehouse_manager", "logistics_coordinator")
def forecast_history():
    """Display previously generated demand forecasts."""

    records = (
        ForecastMetric.query
        .order_by(ForecastMetric.last_evaluated_at.desc())
        .all()
    )

    return render_template(
        "ai/history.html",
        records=records,
    )

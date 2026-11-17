from datetime import datetime
from decimal import Decimal
from app.extensions import db


class ForecastMetric(db.Model):
    """Machine learning evaluation metrics, demand forecasts, and reorder alerts."""

    __tablename__ = "forecast_metrics"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name = db.Column(db.String(80), nullable=False, default="RandomForestRegressor")
    forecast_days = db.Column(db.Integer, nullable=False, default=30)
    predicted_demand = db.Column(db.Integer, nullable=False, default=0)
    mae = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    rmse = db.Column(db.Numeric(8, 4), nullable=False, default=Decimal("0.0000"))
    train_size = db.Column(db.Integer, nullable=False, default=0)
    test_size = db.Column(db.Integer, nullable=False, default=0)
    predicted_demand_next_7d = db.Column(db.Integer, nullable=False, default=0)
    predicted_demand_next_30d = db.Column(db.Integer, nullable=False, default=0)
    calculated_safety_stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_point = db.Column(db.Integer, nullable=False, default=0)
    recommended_reorder_qty = db.Column(db.Integer, nullable=False, default=0)
    urgency_status = db.Column(
        db.Enum("CRITICAL", "MODERATE", "SAFE", name="reorder_urgency_enum"),
        nullable=False,
        default="SAFE",
    )
    last_evaluated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    product = db.relationship("Product", back_populates="forecast_metrics")

    def __repr__(self) -> str:
        return (
            f"<ForecastMetric id={self.id} product_id={self.product_id} "
            f"urgency='{self.urgency_status}' mae={self.mae} rmse={self.rmse}>"
        )

from datetime import datetime
from app.extensions import db


class Dispatch(db.Model):
    """Outbound logistics dispatch and delivery tracking model."""

    __tablename__ = "dispatches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tracking_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vehicle_id = db.Column(
        db.Integer, db.ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    driver_id = db.Column(
        db.Integer, db.ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dispatch_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime, nullable=False)
    actual_delivery = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.Enum("DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED", name="dispatch_status_enum"),
        nullable=False,
        default="DISPATCHED",
    )
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    order = db.relationship("Order", back_populates="dispatch")
    warehouse = db.relationship("Warehouse", back_populates="dispatches")
    vehicle = db.relationship("Vehicle", back_populates="dispatches")
    driver = db.relationship("Driver", back_populates="dispatches")

    def __repr__(self) -> str:
        return f"<Dispatch id={self.id} tracking='{self.tracking_code}' status='{self.status}'>"

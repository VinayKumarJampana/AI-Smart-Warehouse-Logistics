from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Vehicle(db.Model):
    """Logistics delivery fleet vehicle model."""

    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    plate_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    vehicle_type = db.Column(
        db.Enum("Van", "Light Truck", "Heavy Truck", "Container", name="vehicle_type_enum"),
        nullable=False,
    )
    capacity_kg = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("1000.00"))
    status = db.Column(
        db.Enum("AVAILABLE", "IN_TRANSIT", "MAINTENANCE", name="vehicle_status_enum"),
        nullable=False,
        default="AVAILABLE",
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    driver = db.relationship("Driver", back_populates="assigned_vehicle", uselist=False)
    dispatches = db.relationship("Dispatch", back_populates="vehicle", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} plate='{self.plate_number}' status='{self.status}'>"


class Driver(db.Model):
    """Fleet delivery driver model."""

    __tablename__ = "drivers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(25), nullable=False)
    status = db.Column(
        db.Enum("AVAILABLE", "ON_DUTY", "OFF_DUTY", name="driver_status_enum"),
        nullable=False,
        default="AVAILABLE",
    )
    assigned_vehicle_id = db.Column(
        db.Integer, db.ForeignKey("vehicles.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    assigned_vehicle = db.relationship("Vehicle", back_populates="driver")
    dispatches = db.relationship("Dispatch", back_populates="driver", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Driver id={self.id} name='{self.name}' status='{self.status}'>"

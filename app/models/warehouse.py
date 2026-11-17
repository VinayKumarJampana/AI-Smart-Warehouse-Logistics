from datetime import datetime
from app.extensions import db


class Warehouse(db.Model):
    """Warehouse storage facility model."""

    __tablename__ = "warehouses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    total_capacity_sqft = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum("active", "inactive", "maintenance", name="warehouse_status"),
        nullable=False,
        default="active",
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    products = db.relationship("Product", back_populates="warehouse", lazy="dynamic")
    stock_transactions = db.relationship("StockTransaction", back_populates="warehouse", lazy="dynamic")
    dispatches = db.relationship("Dispatch", back_populates="warehouse", lazy="dynamic")

    @property
    def total_stock_count(self) -> int:
        """Calculate total inventory units currently stored in this warehouse."""
        return sum(p.current_stock for p in self.products)

    def __repr__(self) -> str:
        return f"<Warehouse id={self.id} code='{self.code}' name='{self.name}'>"

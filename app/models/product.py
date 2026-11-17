from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Product(db.Model):
    """Inventory product / SKU model."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    unit = db.Column(db.String(20), nullable=False, default="Units")
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    min_threshold = db.Column(db.Integer, nullable=False, default=10)
    max_capacity = db.Column(db.Integer, nullable=False, default=1000)
    lead_time_days = db.Column(db.Integer, nullable=False, default=7)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    category = db.relationship("Category", back_populates="products")
    warehouse = db.relationship("Warehouse", back_populates="products")
    stock_transactions = db.relationship(
        "StockTransaction", back_populates="product", cascade="all, delete-orphan", lazy="dynamic"
    )
    order_items = db.relationship("OrderItem", back_populates="product", lazy="dynamic")
    forecast_metrics = db.relationship(
        "ForecastMetric", back_populates="product", cascade="all, delete-orphan", lazy="dynamic"
    )

    @property
    def is_low_stock(self) -> bool:
        """Check whether current inventory has breached minimum safety threshold."""
        return self.current_stock <= self.min_threshold

    @property
    def total_valuation(self) -> Decimal:
        """Total inventory asset value at cost."""
        return Decimal(self.current_stock) * self.cost_price

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku='{self.sku}' name='{self.name}' stock={self.current_stock}>"

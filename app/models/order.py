from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Order(db.Model):
    """Customer fulfillment order model."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(25), nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    status = db.Column(
        db.Enum(
            "PENDING",
            "APPROVED",
            "DISPATCHED",
            "DELIVERED",
            "CANCELLED",
            name="order_status_enum",
        ),
        nullable=False,
        default="PENDING",
    )
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.Date, nullable=False)

    # Relationships
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    dispatch = db.relationship(
        "Dispatch", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )

    def calculate_total(self) -> Decimal:
        """Recalculate order total from child line items."""
        total = sum((item.subtotal for item in self.items), Decimal("0.00"))
        self.total_amount = total
        return total

    def __repr__(self) -> str:
        return f"<Order id={self.id} number='{self.order_number}' status='{self.status}'>"


class OrderItem(db.Model):
    """Line item within a customer order."""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    # Relationships
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order_id={self.order_id} product_id={self.product_id} qty={self.quantity}>"

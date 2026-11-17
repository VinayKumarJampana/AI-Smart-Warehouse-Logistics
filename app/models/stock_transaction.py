from datetime import datetime
from app.extensions import db


class StockTransaction(db.Model):
    """Inbound, outbound, and adjustment stock movement audit log."""

    __tablename__ = "stock_transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    warehouse_id = db.Column(
        db.Integer, db.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type = db.Column(
        db.Enum("STOCK_IN", "STOCK_OUT", "ADJUSTMENT", name="stock_transaction_type"),
        nullable=False,
    )
    quantity = db.Column(db.Integer, nullable=False)
    balance_after = db.Column(db.Integer, nullable=False)
    reference_no = db.Column(db.String(50), nullable=True, index=True)
    notes = db.Column(db.String(255), nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    product = db.relationship("Product", back_populates="stock_transactions")
    warehouse = db.relationship("Warehouse", back_populates="stock_transactions")
    creator = db.relationship("User", back_populates="stock_transactions")

    def __repr__(self) -> str:
        return (
            f"<StockTransaction id={self.id} type='{self.transaction_type}' "
            f"qty={self.quantity} product_id={self.product_id}>"
        )

from decimal import Decimal
from typing import Tuple, Dict, Any
from app.extensions import db
from app.models.product import Product
from app.models.stock_transaction import StockTransaction
from app.models.warehouse import Warehouse


class InventoryService:
    """Business logic for inventory mutations, auditing, and warehouse stock tracking."""

    @staticmethod
    def process_stock_in(
        product_id: int,
        quantity: int,
        user_id: int,
        reference_no: str = None,
        notes: str = None,
    ) -> Tuple[StockTransaction, Product]:
        """Atomically increments product inventory and logs a verified STOCK_IN audit entry."""
        if quantity <= 0:
            raise ValueError("Stock In quantity must be greater than zero.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} does not exist.")

        # Update current stock
        product.current_stock += quantity

        # Create audit transaction record
        txn = StockTransaction(
            product_id=product.id,
            warehouse_id=product.warehouse_id,
            transaction_type="STOCK_IN",
            quantity=quantity,
            balance_after=product.current_stock,
            reference_no=reference_no.strip() if reference_no else None,
            notes=notes.strip() if notes else None,
            created_by=user_id,
        )

        db.session.add(txn)
        db.session.commit()
        return txn, product

    @staticmethod
    def process_stock_out(
        product_id: int,
        quantity: int,
        user_id: int,
        reference_no: str = None,
        notes: str = None,
    ) -> Tuple[StockTransaction, Product]:
        """Validates stock availability, decrements inventory, and logs a STOCK_OUT audit entry."""
        if quantity <= 0:
            raise ValueError("Stock Out quantity must be greater than zero.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} does not exist.")

        if product.current_stock < quantity:
            raise ValueError(
                f"Insufficient inventory! Available: {product.current_stock} {product.unit}, "
                f"Requested: {quantity} {product.unit}."
            )

        # Decrement stock
        product.current_stock -= quantity

        # Create audit transaction record
        txn = StockTransaction(
            product_id=product.id,
            warehouse_id=product.warehouse_id,
            transaction_type="STOCK_OUT",
            quantity=quantity,
            balance_after=product.current_stock,
            reference_no=reference_no.strip() if reference_no else None,
            notes=notes.strip() if notes else None,
            created_by=user_id,
        )

        db.session.add(txn)
        db.session.commit()
        return txn, product

    @staticmethod
    def get_inventory_summary() -> Dict[str, Any]:
        """Aggregates high-level inventory metrics for dashboard widgets."""
        products = Product.query.all()
        warehouses = Warehouse.query.all()

        total_skus = len(products)
        total_units = sum(p.current_stock for p in products)
        total_valuation = sum((p.total_valuation for p in products), Decimal("0.00"))
        low_stock_products = [p for p in products if p.is_low_stock]

        return {
            "total_skus": total_skus,
            "total_units": total_units,
            "total_valuation": total_valuation,
            "low_stock_count": len(low_stock_products),
            "low_stock_items": low_stock_products,
            "total_warehouses": len(warehouses),
        }

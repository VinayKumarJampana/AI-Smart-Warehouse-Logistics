import random
from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.extensions import db
from app.models.fleet import Vehicle, Driver
from app.models.order import Order, OrderItem
from app.models.dispatch import Dispatch
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.services.inventory_service import InventoryService


class LogisticsService:
    """Operations business logic for Order fulfillment and Dispatch tracking."""

    @staticmethod
    def generate_order_number() -> str:
        """Generate unique human-readable customer order number."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_str = f"{random.randint(1000, 9999)}"
        code = f"ORD-{date_str}-{rand_str}"
        while Order.query.filter_by(order_number=code).first() is not None:
            rand_str = f"{random.randint(1000, 9999)}"
            code = f"ORD-{date_str}-{rand_str}"
        return code

    @staticmethod
    def generate_tracking_code() -> str:
        """Generate unique tracking code for dispatches."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        rand_hex = f"{random.randint(0x1000, 0xFFFF):X}"
        code = f"TRK-{date_str}-{rand_hex}"
        while Dispatch.query.filter_by(tracking_code=code).first() is not None:
            rand_hex = f"{random.randint(0x1000, 0xFFFF):X}"
            code = f"TRK-{date_str}-{rand_hex}"
        return code

    @staticmethod
    def create_order(
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        delivery_address: str,
        expected_delivery_date,
        product_id: int,
        quantity: int,
    ) -> Order:
        """Create a new customer order with an initial line item."""
        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError(f"Product ID {product_id} not found.")

        if quantity <= 0:
            raise ValueError("Order quantity must be at least 1 unit.")

        order = Order(
            order_number=LogisticsService.generate_order_number(),
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip().lower(),
            customer_phone=customer_phone.strip(),
            delivery_address=delivery_address.strip(),
            expected_delivery_date=expected_delivery_date,
            status="PENDING",
        )
        db.session.add(order)
        db.session.flush()

        unit_price = product.unit_price
        subtotal = unit_price * Decimal(quantity)

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        )
        db.session.add(item)
        db.session.flush()

        order.calculate_total()
        db.session.commit()
        return order

    @staticmethod
    def add_order_item(order_id: int, product_id: int, quantity: int) -> OrderItem:
        """Add an additional line item to a pending order."""
        order = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found.")
        if order.status != "PENDING":
            raise ValueError("Cannot add items to an order that is not PENDING.")

        product = db.session.get(Product, product_id)
        if not product:
            raise ValueError("Product not found.")
        if quantity <= 0:
            raise ValueError("Quantity must be at least 1.")

        unit_price = product.unit_price
        subtotal = unit_price * Decimal(quantity)

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=subtotal,
        )
        db.session.add(item)
        db.session.flush()

        order.calculate_total()
        db.session.commit()
        return item

    @staticmethod
    def approve_order(order_id: int) -> Order:
        """Approve a pending customer order after verifying inventory availability."""
        order = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found.")
        if order.status != "PENDING":
            raise ValueError(f"Order status is '{order.status}'. Only PENDING orders can be approved.")

        # Verify stock availability for all line items
        for item in order.items:
            if item.product.current_stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for '{item.product.name}' (SKU: {item.product.sku})! "
                    f"Available: {item.product.current_stock}, Required: {item.quantity}."
                )

        order.status = "APPROVED"
        db.session.commit()
        return order

    @staticmethod
    def cancel_order(order_id: int) -> Order:
        """Cancel a pending or approved order."""
        order = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found.")
        if order.status in ("DISPATCHED", "DELIVERED"):
            raise ValueError(f"Cannot cancel order with status '{order.status}'.")

        order.status = "CANCELLED"
        db.session.commit()
        return order

    @staticmethod
    def create_dispatch(
        order_id: int,
        warehouse_id: int,
        vehicle_id: int,
        driver_id: int,
        estimated_delivery: datetime,
        notes: Optional[str],
        user_id: int,
    ) -> Dispatch:
        """
        Creates and executes a dispatch:
        1. Verifies order is APPROVED.
        2. Verifies vehicle and driver are AVAILABLE.
        3. Deducts stock atomically for all order items.
        4. Updates vehicle to IN_TRANSIT and driver to ON_DUTY.
        5. Updates order status to DISPATCHED.
        6. Logs the immutable Dispatch record.
        """
        order = db.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found.")
        if order.status != "APPROVED":
            raise ValueError(f"Order must be in APPROVED status to dispatch (current: '{order.status}').")
        if order.dispatch is not None:
            raise ValueError(f"Order '{order.order_number}' is already dispatched.")

        warehouse = db.session.get(Warehouse, warehouse_id)
        if not warehouse:
            raise ValueError("Origin warehouse not found.")

        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            raise ValueError("Vehicle not found.")
        if vehicle.status != "AVAILABLE":
            raise ValueError(f"Vehicle '{vehicle.plate_number}' is not available (status: {vehicle.status}).")

        driver = db.session.get(Driver, driver_id)
        if not driver:
            raise ValueError("Driver not found.")
        if driver.status != "AVAILABLE":
            raise ValueError(f"Driver '{driver.name}' is not available (status: {driver.status}).")

        tracking_code = LogisticsService.generate_tracking_code()

        # Deduct stock for each line item using InventoryService
        for item in order.items:
            InventoryService.process_stock_out(
                product_id=item.product_id,
                quantity=item.quantity,
                user_id=user_id,
                reference_no=order.order_number,
                notes=f"Order fulfillment dispatch ({tracking_code})",
            )

        # Update vehicle and driver status
        vehicle.status = "IN_TRANSIT"
        driver.status = "ON_DUTY"
        order.status = "DISPATCHED"

        dispatch = Dispatch(
            tracking_code=tracking_code,
            order_id=order.id,
            warehouse_id=warehouse.id,
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            dispatch_time=datetime.utcnow(),
            estimated_delivery=estimated_delivery,
            status="DISPATCHED",
            notes=notes.strip() if notes else None,
        )

        db.session.add(dispatch)
        db.session.commit()
        return dispatch

    @staticmethod
    def update_dispatch_status(
        dispatch_id: int, new_status: str, notes: Optional[str] = None
    ) -> Dispatch:
        """
        Updates delivery status and manages vehicle/driver lifecycle:
        - When DELIVERED: marks order DELIVERED, sets actual_delivery, releases vehicle & driver to AVAILABLE.
        - When FAILED: marks dispatch FAILED, releases vehicle & driver to AVAILABLE.
        """
        dispatch = db.session.get(Dispatch, dispatch_id)
        if not dispatch:
            raise ValueError("Dispatch record not found.")

        valid_statuses = ("DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED")
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {valid_statuses}")

        if dispatch.status in ("DELIVERED", "FAILED"):
            raise ValueError(f"Shipment is already terminal ('{dispatch.status}'). Cannot modify status.")

        dispatch.status = new_status
        if notes:
            existing = dispatch.notes or ""
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            dispatch.notes = f"{existing}\n[{timestamp}] {notes}".strip()

        if new_status == "DELIVERED":
            dispatch.actual_delivery = datetime.utcnow()
            dispatch.order.status = "DELIVERED"
            # Release fleet resources
            dispatch.vehicle.status = "AVAILABLE"
            dispatch.driver.status = "AVAILABLE"
        elif new_status == "FAILED":
            # Release fleet resources
            dispatch.vehicle.status = "AVAILABLE"
            dispatch.driver.status = "AVAILABLE"

        db.session.commit()
        return dispatch

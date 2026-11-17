from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.category import Category
from app.models.product import Product
from app.models.fleet import Vehicle, Driver
from app.models.order import Order, OrderItem
from app.models.dispatch import Dispatch
from app.models.stock_transaction import StockTransaction
from app.services.logistics_service import LogisticsService


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_admin(app, client):
    """Fixture providing logged-in admin client."""
    with app.app_context():
        admin = User(username="admin_ops", email="admin_ops@logistics.com", role="admin")
        admin.set_password("AdminSecurePass123!")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client.post(
        "/auth/login",
        data={"username_or_email": "admin_ops", "password": "AdminSecurePass123!"},
        follow_redirects=True,
    )
    return client, admin_id


@pytest.fixture
def test_setup(app):
    """Fixture with pre-created warehouse, category, and stocked products."""
    with app.app_context():
        wh = Warehouse(code="WH-ORD-01", name="Chicago O'Hare Hub", location="Chicago", total_capacity_sqft=60000)
        cat = Category(name="Commercial Equipment", description="Heavy industrial units")
        db.session.add_all([wh, cat])
        db.session.commit()

        prod1 = Product(
            sku="SKU-FORKLIFT-01",
            name="Electric Pallet Jack",
            category_id=cat.id,
            warehouse_id=wh.id,
            unit="Units",
            unit_price=Decimal("1200.00"),
            cost_price=Decimal("800.00"),
            current_stock=20,
            min_threshold=5,
            max_capacity=50,
            lead_time_days=10,
        )
        prod2 = Product(
            sku="SKU-SCANNER-02",
            name="Handheld RFID Scanner",
            category_id=cat.id,
            warehouse_id=wh.id,
            unit="Units",
            unit_price=Decimal("350.00"),
            cost_price=Decimal("200.00"),
            current_stock=50,
            min_threshold=10,
            max_capacity=200,
            lead_time_days=7,
        )
        db.session.add_all([prod1, prod2])
        db.session.commit()

        return {
            "warehouse_id": wh.id,
            "category_id": cat.id,
            "product1_id": prod1.id,
            "product2_id": prod2.id,
        }


# ==============================================================================
# VEHICLE & DRIVER CRUD TESTS
# ==============================================================================


def test_vehicle_crud_and_uniqueness(auth_admin, app):
    """Test vehicle creation, duplicate plate validation, edit and deletion."""
    client, _ = auth_admin

    # 1. Register vehicle
    res = client.post(
        "/fleet/vehicles/create",
        data={
            "plate_number": "TRK-IL-1001",
            "vehicle_type": "Light Truck",
            "capacity_kg": "3500.00",
            "status": "AVAILABLE",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"registered successfully" in res.data

    with app.app_context():
        v = Vehicle.query.filter_by(plate_number="TRK-IL-1001").first()
        assert v is not None
        assert v.capacity_kg == Decimal("3500.00")
        assert v.status == "AVAILABLE"
        v_id = v.id

    # 2. Reject duplicate plate
    res_dup = client.post(
        "/fleet/vehicles/create",
        data={
            "plate_number": "TRK-IL-1001",
            "vehicle_type": "Van",
            "capacity_kg": "1200.00",
            "status": "AVAILABLE",
        },
        follow_redirects=True,
    )
    assert b"already registered" in res_dup.data

    # 3. Edit vehicle
    res_edit = client.post(
        f"/fleet/vehicles/{v_id}/edit",
        data={
            "plate_number": "TRK-IL-1001",
            "vehicle_type": "Heavy Truck",
            "capacity_kg": "7500.00",
            "status": "MAINTENANCE",
        },
        follow_redirects=True,
    )
    assert res_edit.status_code == 200
    assert b"updated successfully" in res_edit.data

    with app.app_context():
        v_updated = db.session.get(Vehicle, v_id)
        assert v_updated.vehicle_type == "Heavy Truck"
        assert v_updated.capacity_kg == Decimal("7500.00")
        assert v_updated.status == "MAINTENANCE"

    # 4. Delete vehicle
    res_del = client.post(f"/fleet/vehicles/{v_id}/delete", follow_redirects=True)
    assert res_del.status_code == 200
    assert b"deleted successfully" in res_del.data

    with app.app_context():
        assert db.session.get(Vehicle, v_id) is None


def test_driver_crud_and_uniqueness(auth_admin, app):
    """Test driver creation, CDL license uniqueness, edit and deletion."""
    client, _ = auth_admin

    # Setup a vehicle to pair with driver
    with app.app_context():
        veh = Vehicle(plate_number="VAN-NY-500", vehicle_type="Van", capacity_kg=Decimal("1500.00"))
        db.session.add(veh)
        db.session.commit()
        veh_id = veh.id

    # 1. Register driver
    res = client.post(
        "/fleet/drivers/create",
        data={
            "name": "Alex Mercer",
            "license_number": "CDL-NY-89100",
            "phone": "+1-212-555-0144",
            "status": "AVAILABLE",
            "assigned_vehicle_id": veh_id,
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"registered successfully" in res.data

    with app.app_context():
        d = Driver.query.filter_by(license_number="CDL-NY-89100").first()
        assert d is not None
        assert d.assigned_vehicle_id == veh_id
        d_id = d.id

    # 2. Duplicate license rejection
    res_dup = client.post(
        "/fleet/drivers/create",
        data={
            "name": "Different Name",
            "license_number": "CDL-NY-89100",
            "phone": "+1-212-555-0999",
            "status": "AVAILABLE",
            "assigned_vehicle_id": 0,
        },
        follow_redirects=True,
    )
    assert b"already registered" in res_dup.data

    # 3. Edit driver
    res_edit = client.post(
        f"/fleet/drivers/{d_id}/edit",
        data={
            "name": "Alex Mercer Jr.",
            "license_number": "CDL-NY-89100",
            "phone": "+1-212-555-0888",
            "status": "OFF_DUTY",
            "assigned_vehicle_id": 0,
        },
        follow_redirects=True,
    )
    assert res_edit.status_code == 200
    assert b"updated successfully" in res_edit.data

    with app.app_context():
        d_updated = db.session.get(Driver, d_id)
        assert d_updated.name == "Alex Mercer Jr."
        assert d_updated.status == "OFF_DUTY"
        assert d_updated.assigned_vehicle_id is None


# ==============================================================================
# CUSTOMER ORDER WORKFLOW TESTS
# ==============================================================================


def test_customer_order_lifecycle(auth_admin, test_setup, app):
    """Test creating an order, adding line items, approving and checking totals."""
    client, _ = auth_admin
    p1_id = test_setup["product1_id"]
    p2_id = test_setup["product2_id"]

    # 1. Create order with initial item (2 units of p1 @ $1200 = $2400)
    res_create = client.post(
        "/orders/create",
        data={
            "customer_name": "Globex Logistics Corp",
            "customer_email": "supply@globex.com",
            "customer_phone": "+1-312-555-0900",
            "delivery_address": "800 Distribution Blvd, Chicago, IL",
            "expected_delivery_date": (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "product_id": p1_id,
            "quantity": 2,
        },
        follow_redirects=True,
    )
    assert res_create.status_code == 200
    assert b"created successfully" in res_create.data

    with app.app_context():
        order = Order.query.filter_by(customer_name="Globex Logistics Corp").first()
        assert order is not None
        assert order.status == "PENDING"
        assert order.total_amount == Decimal("2400.00")
        assert len(order.items) == 1
        order_id = order.id

    # 2. Add second line item (4 units of p2 @ $350 = $1400; new total = $3800)
    res_add_item = client.post(
        f"/orders/{order_id}/add-item",
        data={"product_id": p2_id, "quantity": 4},
        follow_redirects=True,
    )
    assert res_add_item.status_code == 200
    assert b"Item added to order successfully" in res_add_item.data

    with app.app_context():
        order = db.session.get(Order, order_id)
        assert len(order.items) == 2
        assert order.total_amount == Decimal("3800.00")

    # 3. Approve order
    res_approve = client.post(f"/orders/{order_id}/approve", follow_redirects=True)
    assert res_approve.status_code == 200
    assert b"approved and is ready for dispatch" in res_approve.data

    with app.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == "APPROVED"


def test_order_stock_validation_on_approval(app, test_setup):
    """Test that approving an order fails if insufficient stock is available."""
    p1_id = test_setup["product1_id"]  # Stock = 20

    with app.app_context():
        # Create order requesting 30 units (more than 20 available)
        order = LogisticsService.create_order(
            customer_name="Overstock Client",
            customer_email="over@client.com",
            customer_phone="+1-555-0100",
            delivery_address="100 Main St",
            expected_delivery_date=date.today() + timedelta(days=2),
            product_id=p1_id,
            quantity=30,
        )

        with pytest.raises(ValueError) as excinfo:
            LogisticsService.approve_order(order.id)
        assert "Insufficient stock" in str(excinfo.value)

        # Status remains PENDING
        assert order.status == "PENDING"


# ==============================================================================
# DISPATCH & DELIVERY LIFECYCLE TESTS
# ==============================================================================


def test_dispatch_creation_and_stock_deduction(auth_admin, test_setup, app):
    """
    Test that creating a dispatch:
    - Verifies order is approved.
    - Atomically deducts inventory stock and writes StockTransaction audit logs.
    - Updates vehicle to IN_TRANSIT and driver to ON_DUTY.
    - Updates order to DISPATCHED.
    """
    client, admin_id = auth_admin
    p1_id = test_setup["product1_id"]
    wh_id = test_setup["warehouse_id"]

    with app.app_context():
        # Create vehicle and driver
        veh = Vehicle(plate_number="TRK-DISP-01", vehicle_type="Heavy Truck", capacity_kg=Decimal("10000.00"))
        driver = Driver(name="Sarah Connor", license_number="CDL-IL-7711", phone="+1-312-555-0177")
        db.session.add_all([veh, driver])
        db.session.commit()
        veh_id = veh.id
        driver_id = driver.id

        # Initial stock of p1 is 20
        p1 = db.session.get(Product, p1_id)
        assert p1.current_stock == 20

        # Create and approve order for 5 units of p1
        order = LogisticsService.create_order(
            customer_name="Northwind Traders",
            customer_email="orders@northwind.com",
            customer_phone="+1-312-555-0211",
            delivery_address="200 Northwind Way, Chicago, IL",
            expected_delivery_date=date.today() + timedelta(days=2),
            product_id=p1_id,
            quantity=5,
        )
        LogisticsService.approve_order(order.id)
        order_id = order.id

    # Launch dispatch via HTTP
    est_time = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
    res_disp = client.post(
        "/dispatch/create",
        data={
            "order_id": order_id,
            "warehouse_id": wh_id,
            "vehicle_id": veh_id,
            "driver_id": driver_id,
            "estimated_delivery": est_time,
            "notes": "Fragile shipment, gate code #441",
        },
        follow_redirects=True,
    )
    assert res_disp.status_code == 200
    assert b"Dispatch created successfully" in res_disp.data

    with app.app_context():
        # Verify order status
        order_check = db.session.get(Order, order_id)
        assert order_check.status == "DISPATCHED"
        assert order_check.dispatch is not None

        dispatch = order_check.dispatch
        assert dispatch.status == "DISPATCHED"
        assert dispatch.tracking_code.startswith("TRK-")

        # Verify stock deduction: 20 - 5 = 15
        p1_check = db.session.get(Product, p1_id)
        assert p1_check.current_stock == 15

        # Verify audit log recorded
        st = StockTransaction.query.filter_by(
            product_id=p1_id, reference_no=order_check.order_number
        ).first()
        assert st is not None
        assert st.transaction_type == "STOCK_OUT"
        assert st.quantity == 5
        assert st.balance_after == 15

        # Verify vehicle and driver status
        v_check = db.session.get(Vehicle, veh_id)
        assert v_check.status == "IN_TRANSIT"

        d_check = db.session.get(Driver, driver_id)
        assert d_check.status == "ON_DUTY"


def test_delivery_status_tracking_and_fleet_release(auth_admin, test_setup, app):
    """
    Test updating dispatch status:
    - DISPATCHED -> IN_TRANSIT
    - IN_TRANSIT -> DELIVERED: marks order DELIVERED, records actual_delivery, releases vehicle & driver back to AVAILABLE.
    """
    client, admin_id = auth_admin
    p1_id = test_setup["product1_id"]
    wh_id = test_setup["warehouse_id"]

    with app.app_context():
        veh = Vehicle(plate_number="TRK-DELIV-99", vehicle_type="Van", capacity_kg=Decimal("1500.00"))
        driver = Driver(name="Marcus Vance", license_number="CDL-IL-9900", phone="+1-312-555-0909")
        db.session.add_all([veh, driver])
        db.session.commit()

        order = LogisticsService.create_order(
            customer_name="Apex Global",
            customer_email="orders@apex.com",
            customer_phone="+1-312-555-0322",
            delivery_address="777 West Ave, Chicago",
            expected_delivery_date=date.today() + timedelta(days=1),
            product_id=p1_id,
            quantity=2,
        )
        LogisticsService.approve_order(order.id)

        dispatch = LogisticsService.create_dispatch(
            order_id=order.id,
            warehouse_id=wh_id,
            vehicle_id=veh.id,
            driver_id=driver.id,
            estimated_delivery=datetime.utcnow() + timedelta(hours=6),
            notes="Expedited delivery",
            user_id=admin_id,
        )
        dispatch_id = dispatch.id
        veh_id = veh.id
        driver_id = driver.id
        order_id = order.id

    # 1. Update to IN_TRANSIT
    res_transit = client.post(
        f"/dispatch/{dispatch_id}/status",
        data={"status": "IN_TRANSIT", "notes": "Passed checkpoint Alpha"},
        follow_redirects=True,
    )
    assert res_transit.status_code == 200
    assert b"IN_TRANSIT" in res_transit.data

    with app.app_context():
        d = db.session.get(Dispatch, dispatch_id)
        assert d.status == "IN_TRANSIT"
        assert "Passed checkpoint Alpha" in d.notes

    # 2. Update to DELIVERED
    res_deliv = client.post(
        f"/dispatch/{dispatch_id}/status",
        data={"status": "DELIVERED", "notes": "Customer signed delivery manifest"},
        follow_redirects=True,
    )
    assert res_deliv.status_code == 200
    assert b"DELIVERED" in res_deliv.data

    with app.app_context():
        d_final = db.session.get(Dispatch, dispatch_id)
        assert d_final.status == "DELIVERED"
        assert d_final.actual_delivery is not None
        assert d_final.order.status == "DELIVERED"

        # Vehicle and driver released back to AVAILABLE
        v_final = db.session.get(Vehicle, veh_id)
        assert v_final.status == "AVAILABLE"

        driver_final = db.session.get(Driver, driver_id)
        assert driver_final.status == "AVAILABLE"


def test_failed_delivery_releases_fleet(app, test_setup):
    """Test that setting a dispatch to FAILED releases vehicle and driver back to AVAILABLE."""
    p1_id = test_setup["product1_id"]
    wh_id = test_setup["warehouse_id"]

    with app.app_context():
        user = User(username="admin_fail", email="fail@test.com", role="admin")
        user.set_password("pass123")
        veh = Vehicle(plate_number="VAN-FAIL-01", vehicle_type="Van", capacity_kg=Decimal("1200.00"))
        driver = Driver(name="Dana Scully", license_number="CDL-IL-1122", phone="+1-312-555-0112")
        db.session.add_all([user, veh, driver])
        db.session.commit()

        order = LogisticsService.create_order(
            customer_name="Lost Packages Inc",
            customer_email="lost@packages.com",
            customer_phone="+1-312-555-0811",
            delivery_address="Unknown Location",
            expected_delivery_date=date.today(),
            product_id=p1_id,
            quantity=1,
        )
        LogisticsService.approve_order(order.id)

        dispatch = LogisticsService.create_dispatch(
            order_id=order.id,
            warehouse_id=wh_id,
            vehicle_id=veh.id,
            driver_id=driver.id,
            estimated_delivery=datetime.utcnow() + timedelta(hours=3),
            notes="Initial dispatch",
            user_id=user.id,
        )

        assert veh.status == "IN_TRANSIT"
        assert driver.status == "ON_DUTY"

        # Mark FAILED
        LogisticsService.update_dispatch_status(
            dispatch.id,
            new_status="FAILED",
            notes="Customer premises closed, returned to hub",
        )

        assert dispatch.status == "FAILED"
        assert veh.status == "AVAILABLE"
        assert driver.status == "AVAILABLE"

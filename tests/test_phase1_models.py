from decimal import Decimal
from datetime import date
import pytest
from app import create_app
from app.extensions import db
from app.models import (
    User,
    Warehouse,
    Category,
    Product,
    StockTransaction,
    Vehicle,
    Driver,
    Order,
    OrderItem,
    Dispatch,
    ForecastMetric,
)


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


def test_health_endpoint(client):
    """Verify health check endpoint returns 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "Phase 1" in data["phase"]


def test_user_password_hashing(app):
    """Verify user password hashing and verification."""
    with app.app_context():
        user = User(username="admin_test", email="admin@test.com", role="admin")
        user.set_password("AdminSecurePass123!")
        db.session.add(user)
        db.session.commit()

        assert user.password_hash != "AdminSecurePass123!"
        assert user.check_password("AdminSecurePass123!") is True
        assert user.check_password("WrongPassword") is False


def test_database_models_integration(app):
    """Verify that all 11 models can be created and related in SQLAlchemy."""
    with app.app_context():
        # 1. User
        user = User(username="operator1", email="op1@test.com", role="warehouse_manager")
        user.set_password("password123")
        db.session.add(user)

        # 2. Warehouse
        wh = Warehouse(
            code="WH-TEST-01",
            name="Main Hub",
            location="Chicago",
            total_capacity_sqft=50000,
        )
        db.session.add(wh)

        # 3. Category
        cat = Category(name="Electronics", description="Consumer tech goods")
        db.session.add(cat)
        db.session.commit()

        # 4. Product
        prod = Product(
            sku="SKU-ELEC-100",
            name="Wireless Barcode Scanner",
            category_id=cat.id,
            warehouse_id=wh.id,
            unit="Units",
            unit_price=Decimal("150.00"),
            cost_price=Decimal("95.00"),
            current_stock=15,
            min_threshold=20,
            max_capacity=500,
            lead_time_days=5,
        )
        db.session.add(prod)
        db.session.commit()

        # Test product properties
        assert prod.is_low_stock is True  # 15 <= 20
        assert prod.total_valuation == Decimal("1425.00")  # 15 * 95.00

        # 5. Stock Transaction
        txn = StockTransaction(
            product_id=prod.id,
            warehouse_id=wh.id,
            transaction_type="STOCK_IN",
            quantity=15,
            balance_after=15,
            reference_no="PO-INIT-01",
            created_by=user.id,
        )
        db.session.add(txn)

        # 6. Vehicle
        veh = Vehicle(
            plate_number="IL-TRK-902",
            vehicle_type="Light Truck",
            capacity_kg=Decimal("3500.00"),
            status="AVAILABLE",
        )
        db.session.add(veh)
        db.session.commit()

        # 7. Driver
        driver = Driver(
            name="John Doe",
            license_number="DL-IL-981726",
            phone="+1-312-555-0199",
            status="AVAILABLE",
            assigned_vehicle_id=veh.id,
        )
        db.session.add(driver)

        # 8. Order & 9. OrderItem
        order = Order(
            order_number="ORD-TEST-001",
            customer_name="Acme Corp",
            customer_email="orders@acme.com",
            customer_phone="+1-312-555-0100",
            delivery_address="100 Michigan Ave, Chicago, IL",
            expected_delivery_date=date(2026, 11, 20),
        )
        db.session.add(order)
        db.session.commit()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=2,
            unit_price=Decimal("150.00"),
            subtotal=Decimal("300.00"),
        )
        db.session.add(item)
        db.session.commit()

        order.calculate_total()
        assert order.total_amount == Decimal("300.00")

        # 10. Dispatch
        dispatch = Dispatch(
            tracking_code="TRK-TEST-9001",
            order_id=order.id,
            warehouse_id=wh.id,
            vehicle_id=veh.id,
            driver_id=driver.id,
            estimated_delivery=order.order_date,
            status="DISPATCHED",
        )
        db.session.add(dispatch)

        # 11. ForecastMetric
        metric = ForecastMetric(
            product_id=prod.id,
            model_name="RandomForestRegressor",
            mae=Decimal("1.4200"),
            rmse=Decimal("1.8900"),
            train_size=72,
            test_size=18,
            predicted_demand_next_7d=35,
            predicted_demand_next_30d=140,
            calculated_safety_stock=18,
            reorder_point=42,
            recommended_reorder_qty=27,
            urgency_status="CRITICAL",
        )
        db.session.add(metric)
        db.session.commit()

        # Assertions to confirm everything saved and retrieved cleanly
        assert User.query.count() == 1
        assert Warehouse.query.count() == 1
        assert Category.query.count() == 1
        assert Product.query.count() == 1
        assert StockTransaction.query.count() == 1
        assert Vehicle.query.count() == 1
        assert Driver.query.count() == 1
        assert Order.query.count() == 1
        assert OrderItem.query.count() == 1
        assert Dispatch.query.count() == 1
        assert ForecastMetric.query.count() == 1

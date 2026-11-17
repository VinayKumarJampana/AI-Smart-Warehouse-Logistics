from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.category import Category
from app.models.product import Product
from app.models.stock_transaction import StockTransaction
from app.services.inventory_service import InventoryService


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
def auth_client(app, client):
    """Fixture that creates an admin user and logs in."""
    with app.app_context():
        admin = User(username="admin_user", email="admin@logistics.com", role="admin")
        admin.set_password("AdminSecure123!")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    client.post(
        "/auth/login",
        data={"username_or_email": "admin_user", "password": "AdminSecure123!"},
        follow_redirects=True,
    )
    return client, admin_id


def test_auth_registration_and_login(client, app):
    """Test user registration, login, and logout flow."""
    # 1. Register first user (automatically becomes admin)
    reg_response = client.post(
        "/auth/register",
        data={
            "username": "superadmin",
            "email": "superadmin@logistics.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert reg_response.status_code == 200
    assert b"created successfully" in reg_response.data

    with app.app_context():
        user = User.query.filter_by(username="superadmin").first()
        assert user is not None
        assert user.role == "admin"
        assert user.check_password("Password123!") is True

    # 2. Login with correct credentials
    login_response = client.post(
        "/auth/login",
        data={"username_or_email": "superadmin", "password": "Password123!"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    assert b"Executive Logistics Dashboard" in login_response.data

    # 3. Access protected dashboard
    dash_response = client.get("/dashboard")
    assert dash_response.status_code == 200
    assert b"superadmin" in dash_response.data

    # 4. Logout
    logout_response = client.get("/auth/logout", follow_redirects=True)
    assert logout_response.status_code == 200
    assert b"You have been signed out" in logout_response.data


def test_protected_routes_require_authentication(client):
    """Test that unauthorized users are redirected to login."""
    endpoints = ["/dashboard", "/warehouses/", "/inventory/", "/stock/in", "/stock/history"]
    for ep in endpoints:
        response = client.get(ep, follow_redirects=False)
        assert response.status_code in (302, 308)
        assert "/auth/login" in response.headers["Location"]


def test_warehouse_crud(auth_client, app):
    """Test warehouse creation, editing, and deletion."""
    client, _ = auth_client

    # 1. Create Warehouse
    res = client.post(
        "/warehouses/create",
        data={
            "code": "WH-CHI-01",
            "name": "Chicago Central Hub",
            "location": "Chicago, IL",
            "address": "123 Logistics Ave",
            "total_capacity_sqft": 45000,
            "status": "active",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"created successfully" in res.data

    with app.app_context():
        wh = Warehouse.query.filter_by(code="WH-CHI-01").first()
        assert wh is not None
        assert wh.name == "Chicago Central Hub"
        wh_id = wh.id

    # 2. Edit Warehouse
    res_edit = client.post(
        f"/warehouses/{wh_id}/edit",
        data={
            "code": "WH-CHI-01",
            "name": "Chicago Super Hub",
            "location": "Chicago, IL",
            "address": "123 Logistics Ave",
            "total_capacity_sqft": 55000,
            "status": "active",
        },
        follow_redirects=True,
    )
    assert res_edit.status_code == 200
    assert b"updated successfully" in res_edit.data

    with app.app_context():
        wh = db.session.get(Warehouse, wh_id)
        assert wh.name == "Chicago Super Hub"
        assert wh.total_capacity_sqft == 55000

    # 3. Delete Warehouse
    res_del = client.post(f"/warehouses/{wh_id}/delete", follow_redirects=True)
    assert res_del.status_code == 200
    assert b"deleted successfully" in res_del.data

    with app.app_context():
        assert db.session.get(Warehouse, wh_id) is None


def test_category_and_product_crud(auth_client, app):
    """Test category and product creation, threshold evaluation, and deletion."""
    client, user_id = auth_client

    # 1. Create Category
    client.post(
        "/inventory/categories",
        data={"name": "Industrial Hardware", "description": "Machinery and tools"},
        follow_redirects=True,
    )

    with app.app_context():
        cat = Category.query.filter_by(name="Industrial Hardware").first()
        assert cat is not None
        cat_id = cat.id

        # Setup warehouse
        wh = Warehouse(code="WH-MIA-01", name="Miami Hub", location="Miami", total_capacity_sqft=20000)
        db.session.add(wh)
        db.session.commit()
        wh_id = wh.id

    # 2. Create Product
    prod_res = client.post(
        "/inventory/create",
        data={
            "sku": "SKU-TOOL-001",
            "name": "Hydraulic Torque Wrench",
            "category_id": cat_id,
            "warehouse_id": wh_id,
            "unit": "Units",
            "cost_price": "250.00",
            "unit_price": "399.99",
            "current_stock": 25,
            "min_threshold": 10,
            "max_capacity": 200,
            "lead_time_days": 14,
        },
        follow_redirects=True,
    )
    assert prod_res.status_code == 200
    assert b"added successfully" in prod_res.data

    with app.app_context():
        prod = Product.query.filter_by(sku="SKU-TOOL-001").first()
        assert prod is not None
        assert prod.current_stock == 25
        assert prod.is_low_stock is False
        assert prod.total_valuation == Decimal("6250.00")  # 25 * 250.00


def test_stock_in_and_stock_out_operations(app):
    """Test stock mutations and boundary checks using InventoryService."""
    with app.app_context():
        user = User(username="manager1", email="mgr@test.com", role="warehouse_manager")
        user.set_password("pass123")
        db.session.add(user)

        wh = Warehouse(code="WH-DAL-01", name="Dallas Hub", location="Dallas", total_capacity_sqft=30000)
        db.session.add(wh)

        cat = Category(name="Electronics", description="Gadgets")
        db.session.add(cat)
        db.session.commit()

        prod = Product(
            sku="SKU-SENSOR-01",
            name="IoT Temperature Sensor",
            category_id=cat.id,
            warehouse_id=wh.id,
            unit="Units",
            cost_price=Decimal("15.00"),
            unit_price=Decimal("29.99"),
            current_stock=10,
            min_threshold=15,
            max_capacity=500,
            lead_time_days=5,
        )
        db.session.add(prod)
        db.session.commit()

        assert prod.is_low_stock is True  # 10 <= 15

        # 1. Process Stock In: add 40 units
        txn_in, updated_prod = InventoryService.process_stock_in(
            product_id=prod.id,
            quantity=40,
            user_id=user.id,
            reference_no="PO-9901",
            notes="Restock shipment received",
        )
        assert updated_prod.current_stock == 50
        assert txn_in.balance_after == 50
        assert txn_in.transaction_type == "STOCK_IN"
        assert updated_prod.is_low_stock is False  # 50 > 15

        # 2. Process Stock Out: dispatch 20 units
        txn_out, updated_prod = InventoryService.process_stock_out(
            product_id=prod.id,
            quantity=20,
            user_id=user.id,
            reference_no="SO-1002",
            notes="Customer dispatch",
        )
        assert updated_prod.current_stock == 30
        assert txn_out.balance_after == 30
        assert txn_out.transaction_type == "STOCK_OUT"

        # 3. Process Stock Out beyond current stock (Expect ValueError)
        with pytest.raises(ValueError) as excinfo:
            InventoryService.process_stock_out(
                product_id=prod.id,
                quantity=100,  # Only 30 available
                user_id=user.id,
            )
        assert "Insufficient inventory" in str(excinfo.value)
        # Verify balance remains unchanged at 30
        assert prod.current_stock == 30

        # Verify audit history length
        history = StockTransaction.query.filter_by(product_id=prod.id).all()
        assert len(history) == 2


def test_stock_http_endpoints_and_history(auth_client, app):
    """Test stock in and stock out via HTTP routes and audit history viewing."""
    client, user_id = auth_client

    with app.app_context():
        wh = Warehouse(code="WH-SEA-01", name="Seattle Hub", location="Seattle", total_capacity_sqft=15000)
        cat = Category(name="Apparel", description="Clothing")
        db.session.add_all([wh, cat])
        db.session.commit()

        prod = Product(
            sku="SKU-HOODIE-BLK",
            name="Classic Black Hoodie",
            category_id=cat.id,
            warehouse_id=wh.id,
            unit="Units",
            cost_price=Decimal("20.00"),
            unit_price=Decimal("45.00"),
            current_stock=50,
            min_threshold=10,
            max_capacity=300,
            lead_time_days=7,
        )
        db.session.add(prod)
        db.session.commit()
        prod_id = prod.id

    # 1. Stock In via HTTP Form
    res_in = client.post(
        "/stock/in",
        data={
            "product_id": prod_id,
            "quantity": 25,
            "reference_no": "PO-HTTP-001",
            "notes": "Delivered by freight",
        },
        follow_redirects=True,
    )
    assert res_in.status_code == 200
    assert b"Successfully added 25" in res_in.data

    with app.app_context():
        p = db.session.get(Product, prod_id)
        assert p.current_stock == 75

    # 2. Stock Out via HTTP Form
    res_out = client.post(
        "/stock/out",
        data={
            "product_id": prod_id,
            "quantity": 15,
            "reference_no": "SO-HTTP-002",
            "notes": "Order fulfillment",
        },
        follow_redirects=True,
    )
    assert res_out.status_code == 200
    assert b"Successfully removed 15" in res_out.data

    with app.app_context():
        p = db.session.get(Product, prod_id)
        assert p.current_stock == 60

    # 3. View Stock Audit History
    res_hist = client.get("/stock/history")
    assert res_hist.status_code == 200
    assert b"PO-HTTP-001" in res_hist.data
    assert b"SO-HTTP-002" in res_hist.data
    assert b"STOCK IN" in res_hist.data
    assert b"STOCK OUT" in res_hist.data


def test_role_based_access_control(client, app):
    """Test RBAC restrictions between roles."""
    with app.app_context():
        # Create non-admin user
        coord = User(username="coordinator1", email="coord@test.com", role="logistics_coordinator")
        coord.set_password("pass123")
        wh = Warehouse(code="WH-DEN-01", name="Denver Hub", location="Denver", total_capacity_sqft=25000)
        db.session.add_all([coord, wh])
        db.session.commit()
        wh_id = wh.id

    # Login as logistics coordinator
    client.post(
        "/auth/login",
        data={"username_or_email": "coordinator1", "password": "pass123"},
        follow_redirects=True,
    )

    # Coordinator cannot delete a warehouse (Admin only)
    del_res = client.post(f"/warehouses/{wh_id}/delete", follow_redirects=True)
    assert b"Access restricted" in del_res.data

    # Warehouse still exists
    with app.app_context():
        assert db.session.get(Warehouse, wh_id) is not None


def test_public_registration_privilege_escalation_prevention(client, app):
    """
    Rigorously verify registration security:
    1. First user gets admin.
    2. Subsequent public registrations receive safe default role ('logistics_coordinator').
    3. Tampered public POST with role='admin' must be ignored and assigned 'logistics_coordinator'.
    4. Non-admins cannot access user management endpoints.
    5. Authenticated admins can create staff and modify roles.
    """
    # 1. First user registration -> admin
    res1 = client.post(
        "/auth/register",
        data={
            "username": "founder_admin",
            "email": "founder@logistics.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert res1.status_code == 200

    with app.app_context():
        u1 = User.query.filter_by(username="founder_admin").first()
        assert u1 is not None
        assert u1.role == "admin"

    # 2. Second public registration without role parameter -> safe default
    res2 = client.post(
        "/auth/register",
        data={
            "username": "public_user",
            "email": "public@logistics.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert res2.status_code == 200

    with app.app_context():
        u2 = User.query.filter_by(username="public_user").first()
        assert u2 is not None
        assert u2.role == "logistics_coordinator"

    # 3. Third public registration tampering with form by sending role='admin'
    res3 = client.post(
        "/auth/register",
        data={
            "username": "attacker_user",
            "email": "attacker@logistics.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "admin",  # Tampered malicious field
        },
        follow_redirects=True,
    )
    assert res3.status_code == 200

    with app.app_context():
        u3 = User.query.filter_by(username="attacker_user").first()
        assert u3 is not None
        # Must NOT be admin! Must be assigned safe default role
        assert u3.role == "logistics_coordinator"
        assert u3.role != "admin"

    # 4. Attempt to access user management as unprivileged user
    client.post(
        "/auth/login",
        data={"username_or_email": "public_user", "password": "Password123!"},
        follow_redirects=True,
    )
    users_page_res = client.get("/auth/users", follow_redirects=True)
    assert b"Access restricted" in users_page_res.data

    create_staff_res = client.get("/auth/users/create", follow_redirects=True)
    assert b"Access restricted" in create_staff_res.data

    client.get("/auth/logout", follow_redirects=True)

    # 5. Log in as admin and create staff with chosen role
    client.post(
        "/auth/login",
        data={"username_or_email": "founder_admin", "password": "Password123!"},
        follow_redirects=True,
    )

    admin_create_res = client.post(
        "/auth/users/create",
        data={
            "username": "trusted_wh_mgr",
            "email": "mgr@logistics.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "warehouse_manager",
        },
        follow_redirects=True,
    )
    assert admin_create_res.status_code == 200
    assert b"trusted_wh_mgr" in admin_create_res.data
    assert b"created successfully" in admin_create_res.data

    with app.app_context():
        mgr = User.query.filter_by(username="trusted_wh_mgr").first()
        assert mgr is not None
        assert mgr.role == "warehouse_manager"

    # 6. Admin modifies role of an existing user
    with app.app_context():
        u2_id = User.query.filter_by(username="public_user").first().id

    edit_role_res = client.post(
        f"/auth/users/{u2_id}/edit-role",
        data={
            "role": "warehouse_manager",
            "is_active": True,
        },
        follow_redirects=True,
    )
    assert edit_role_res.status_code == 200

    with app.app_context():
        u2_updated = db.session.get(User, u2_id)
        assert u2_updated.role == "warehouse_manager"

    # 7. Admin cannot demote themselves
    with app.app_context():
        admin_id = User.query.filter_by(username="founder_admin").first().id

    self_demote_res = client.post(
        f"/auth/users/{admin_id}/edit-role",
        data={
            "role": "logistics_coordinator",
            "is_active": True,
        },
        follow_redirects=True,
    )
    assert b"You cannot demote or deactivate your own administrator account" in self_demote_res.data

    with app.app_context():
        admin_check = db.session.get(User, admin_id)
        assert admin_check.role == "admin"



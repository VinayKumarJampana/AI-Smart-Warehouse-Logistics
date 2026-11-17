
from app.routes.auth_routes import auth_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.warehouse_routes import warehouse_bp
from app.routes.inventory_routes import inventory_bp
from app.routes.stock_routes import stock_bp
from app.routes.fleet_routes import fleet_bp
from app.routes.order_routes import order_bp
from app.routes.dispatch_routes import dispatch_bp
from app.routes.ai_routes import ai_bp
from app.routes.analytics_routes import analytics_bp

__all__ = [
    "auth_bp",
    "dashboard_bp",
    "warehouse_bp",
    "inventory_bp",
    "stock_bp",
    "fleet_bp",
    "order_bp",
    "dispatch_bp",
    "ai_bp",
    "analytics_bp",
]

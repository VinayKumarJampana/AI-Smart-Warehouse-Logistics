from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.dispatch import Dispatch
from app.models.order import Order
from app.models.warehouse import Warehouse
from app.models.fleet import Vehicle, Driver
from app.forms.dispatch_forms import DispatchCreateForm, DispatchStatusUpdateForm
from app.services.logistics_service import LogisticsService
from app.utils.decorators import role_required

dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/dispatch")


@dispatch_bp.route("/")
@login_required
def index():
    """List dispatches with delivery status filters and search."""
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Dispatch.query
    if search_query:
        query = query.join(Order).join(Vehicle).filter(
            (Dispatch.tracking_code.ilike(f"%{search_query}%"))
            | (Order.order_number.ilike(f"%{search_query}%"))
            | (Order.customer_name.ilike(f"%{search_query}%"))
            | (Vehicle.plate_number.ilike(f"%{search_query}%"))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)

    dispatches = query.order_by(Dispatch.dispatch_time.desc()).all()
    return render_template(
        "dispatch/list.html",
        dispatches=dispatches,
        search_query=search_query,
        status_filter=status_filter,
    )


@dispatch_bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def create():
    """Assign vehicle, driver, and launch shipment dispatch for an approved order."""
    form = DispatchCreateForm()

    # Query approved orders that do not yet have an active dispatch
    approved_orders = (
        Order.query.filter_by(status="APPROVED")
        .filter(~Order.dispatch.has())
        .order_by(Order.order_date.asc())
        .all()
    )

    warehouses = Warehouse.query.filter_by(status="active").order_by(Warehouse.name.asc()).all()
    available_vehicles = Vehicle.query.filter_by(status="AVAILABLE").order_by(Vehicle.plate_number.asc()).all()
    available_drivers = Driver.query.filter_by(status="AVAILABLE").order_by(Driver.name.asc()).all()

    # Pre-select order if query param supplied
    preselected_order_id = request.args.get("order_id", type=int)

    form.order_id.choices = [
        (o.id, f"{o.order_number} — {o.customer_name} (${o.total_amount:,.2f})")
        for o in approved_orders
    ]
    form.warehouse_id.choices = [(w.id, f"{w.name} ({w.code})") for w in warehouses]
    form.vehicle_id.choices = [
        (v.id, f"{v.plate_number} — {v.vehicle_type} (Cap: {v.capacity_kg} kg)")
        for v in available_vehicles
    ]
    form.driver_id.choices = [
        (d.id, f"{d.name} (License: {d.license_number}, Phone: {d.phone})")
        for d in available_drivers
    ]

    if request.method == "GET" and preselected_order_id:
        form.order_id.data = preselected_order_id

    if form.validate_on_submit():
        try:
            dispatch = LogisticsService.create_dispatch(
                order_id=form.order_id.data,
                warehouse_id=form.warehouse_id.data,
                vehicle_id=form.vehicle_id.data,
                driver_id=form.driver_id.data,
                estimated_delivery=form.estimated_delivery.data,
                notes=form.notes.data,
                user_id=current_user.id,
            )
            flash(
                f"Dispatch created successfully! Tracking code: {dispatch.tracking_code}. "
                f"Vehicle {dispatch.vehicle.plate_number} & Driver {dispatch.driver.name} assigned.",
                "success",
            )
            return redirect(url_for("dispatch.track", id=dispatch.id))
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error launching dispatch: {exc}", "danger")

    return render_template(
        "dispatch/create.html",
        form=form,
        has_approved_orders=len(approved_orders) > 0,
        has_vehicles=len(available_vehicles) > 0,
        has_drivers=len(available_drivers) > 0,
    )


@dispatch_bp.route("/<int:id>")
@login_required
def track(id):
    """View shipment delivery tracking, timeline, and routing details."""
    dispatch = db.get_or_404(Dispatch, id)
    status_form = DispatchStatusUpdateForm(obj=dispatch)
    return render_template("dispatch/track.html", dispatch=dispatch, status_form=status_form)


@dispatch_bp.route("/<int:id>/status", methods=["POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def update_status(id):
    """Update shipment progress (IN_TRANSIT, DELIVERED, FAILED)."""
    form = DispatchStatusUpdateForm()
    if form.validate_on_submit():
        try:
            dispatch = LogisticsService.update_dispatch_status(
                dispatch_id=id,
                new_status=form.status.data,
                notes=form.notes.data,
            )
            flash(f"Shipment {dispatch.tracking_code} updated to status: {dispatch.status}.", "success")
        except ValueError as val_err:
            flash(str(val_err), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating shipment status: {exc}", "danger")

    return redirect(url_for("dispatch.track", id=id))

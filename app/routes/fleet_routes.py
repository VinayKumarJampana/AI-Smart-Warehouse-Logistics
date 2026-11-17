from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.fleet import Vehicle, Driver
from app.forms.fleet_forms import VehicleForm, DriverForm
from app.utils.decorators import role_required

fleet_bp = Blueprint("fleet", __name__, url_prefix="/fleet")


# ==============================================================================
# VEHICLE MANAGEMENT
# ==============================================================================


@fleet_bp.route("/vehicles")
@login_required
def vehicles():
    """List fleet vehicles with search, status, and type filters."""
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    type_filter = request.args.get("type", "").strip()

    query = Vehicle.query
    if search_query:
        query = query.filter(Vehicle.plate_number.ilike(f"%{search_query}%"))
    if status_filter:
        query = query.filter_by(status=status_filter)
    if type_filter:
        query = query.filter_by(vehicle_type=type_filter)

    all_vehicles = query.order_by(Vehicle.plate_number.asc()).all()
    return render_template(
        "fleet/vehicles.html",
        vehicles=all_vehicles,
        search_query=search_query,
        status_filter=status_filter,
        type_filter=type_filter,
    )


@fleet_bp.route("/vehicles/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def create_vehicle():
    """Register a new fleet vehicle."""
    form = VehicleForm()
    if form.validate_on_submit():
        vehicle = Vehicle(
            plate_number=form.plate_number.data.strip().upper(),
            vehicle_type=form.vehicle_type.data,
            capacity_kg=Decimal(str(form.capacity_kg.data)),
            status=form.status.data,
        )
        try:
            db.session.add(vehicle)
            db.session.commit()
            flash(f"Vehicle '{vehicle.plate_number}' ({vehicle.vehicle_type}) registered successfully!", "success")
            return redirect(url_for("fleet.vehicles"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error registering vehicle: {exc}", "danger")

    return render_template("fleet/vehicle_form.html", form=form, title="Register Vehicle", is_edit=False)


@fleet_bp.route("/vehicles/<int:id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def edit_vehicle(id):
    """Edit existing fleet vehicle specifications and status."""
    vehicle = db.get_or_404(Vehicle, id)
    form = VehicleForm(original_plate=vehicle.plate_number, obj=vehicle)

    if form.validate_on_submit():
        vehicle.plate_number = form.plate_number.data.strip().upper()
        vehicle.vehicle_type = form.vehicle_type.data
        vehicle.capacity_kg = Decimal(str(form.capacity_kg.data))
        vehicle.status = form.status.data

        try:
            db.session.commit()
            flash(f"Vehicle '{vehicle.plate_number}' updated successfully!", "success")
            return redirect(url_for("fleet.vehicles"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating vehicle: {exc}", "danger")

    return render_template(
        "fleet/vehicle_form.html",
        form=form,
        title=f"Edit Vehicle: {vehicle.plate_number}",
        is_edit=True,
        vehicle=vehicle,
    )


@fleet_bp.route("/vehicles/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_vehicle(id):
    """Delete vehicle with dispatch dependency check."""
    vehicle = db.get_or_404(Vehicle, id)
    if vehicle.status == "IN_TRANSIT":
        flash(f"Cannot delete vehicle '{vehicle.plate_number}' while currently IN TRANSIT.", "danger")
        return redirect(url_for("fleet.vehicles"))

    if vehicle.dispatches.count() > 0:
        flash(
            f"Cannot delete vehicle '{vehicle.plate_number}' because it has {vehicle.dispatches.count()} dispatch record(s).",
            "danger",
        )
        return redirect(url_for("fleet.vehicles"))

    try:
        # Unlink driver if assigned
        if vehicle.driver:
            vehicle.driver.assigned_vehicle_id = None
        db.session.delete(vehicle)
        db.session.commit()
        flash(f"Vehicle '{vehicle.plate_number}' deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error deleting vehicle: {exc}", "danger")

    return redirect(url_for("fleet.vehicles"))


# ==============================================================================
# DRIVER MANAGEMENT
# ==============================================================================


@fleet_bp.route("/drivers")
@login_required
def drivers():
    """List drivers with status filter and search."""
    search_query = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Driver.query
    if search_query:
        query = query.filter(
            (Driver.name.ilike(f"%{search_query}%"))
            | (Driver.license_number.ilike(f"%{search_query}%"))
            | (Driver.phone.ilike(f"%{search_query}%"))
        )
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_drivers = query.order_by(Driver.name.asc()).all()
    return render_template(
        "fleet/drivers.html",
        drivers=all_drivers,
        search_query=search_query,
        status_filter=status_filter,
    )


@fleet_bp.route("/drivers/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def create_driver():
    """Register a new commercial driver."""
    form = DriverForm()

    # Populate unassigned or available vehicles for optional default assignment
    available_vehicles = Vehicle.query.filter_by(status="AVAILABLE").all()
    form.assigned_vehicle_id.choices = [(0, "-- No Assigned Vehicle --")] + [
        (v.id, f"{v.plate_number} ({v.vehicle_type})")
        for v in available_vehicles
        if v.driver is None
    ]

    if form.validate_on_submit():
        assigned_veh_id = form.assigned_vehicle_id.data if form.assigned_vehicle_id.data > 0 else None
        driver = Driver(
            name=form.name.data.strip(),
            license_number=form.license_number.data.strip().upper(),
            phone=form.phone.data.strip(),
            status=form.status.data,
            assigned_vehicle_id=assigned_veh_id,
        )
        try:
            db.session.add(driver)
            db.session.commit()
            flash(f"Driver '{driver.name}' ({driver.license_number}) registered successfully!", "success")
            return redirect(url_for("fleet.drivers"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error registering driver: {exc}", "danger")

    return render_template("fleet/driver_form.html", form=form, title="Register Driver", is_edit=False)


@fleet_bp.route("/drivers/<int:id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "logistics_coordinator")
def edit_driver(id):
    """Edit driver details and vehicle assignment."""
    driver = db.get_or_404(Driver, id)
    form = DriverForm(original_license=driver.license_number, obj=driver)

    available_vehicles = Vehicle.query.all()
    form.assigned_vehicle_id.choices = [(0, "-- No Assigned Vehicle --")] + [
        (v.id, f"{v.plate_number} ({v.vehicle_type})")
        for v in available_vehicles
        if v.driver is None or v.id == driver.assigned_vehicle_id
    ]

    if request.method == "GET":
        form.assigned_vehicle_id.data = driver.assigned_vehicle_id or 0

    if form.validate_on_submit():
        driver.name = form.name.data.strip()
        driver.license_number = form.license_number.data.strip().upper()
        driver.phone = form.phone.data.strip()
        driver.status = form.status.data
        driver.assigned_vehicle_id = (
            form.assigned_vehicle_id.data if form.assigned_vehicle_id.data > 0 else None
        )

        try:
            db.session.commit()
            flash(f"Driver '{driver.name}' updated successfully!", "success")
            return redirect(url_for("fleet.drivers"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Error updating driver: {exc}", "danger")

    return render_template(
        "fleet/driver_form.html",
        form=form,
        title=f"Edit Driver: {driver.name}",
        is_edit=True,
        driver=driver,
    )


@fleet_bp.route("/drivers/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_driver(id):
    """Delete driver with active duty check."""
    driver = db.get_or_404(Driver, id)
    if driver.status == "ON_DUTY":
        flash(f"Cannot delete driver '{driver.name}' while ON DUTY.", "danger")
        return redirect(url_for("fleet.drivers"))

    if driver.dispatches.count() > 0:
        flash(
            f"Cannot delete driver '{driver.name}' because of {driver.dispatches.count()} linked dispatch record(s).",
            "danger",
        )
        return redirect(url_for("fleet.drivers"))

    try:
        db.session.delete(driver)
        db.session.commit()
        flash(f"Driver '{driver.name}' deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        flash(f"Error deleting driver: {exc}", "danger")

    return redirect(url_for("fleet.drivers"))

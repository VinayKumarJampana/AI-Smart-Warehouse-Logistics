from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError, Regexp
from app.models.fleet import Vehicle, Driver


class VehicleForm(FlaskForm):
    """Vehicle registration and edit form."""

    plate_number = StringField(
        "License Plate / Vehicle Number *",
        validators=[
            DataRequired(message="Vehicle plate number is required."),
            Length(min=3, max=30, message="Plate number must be between 3 and 30 characters."),
        ],
    )
    vehicle_type = SelectField(
        "Vehicle Type *",
        choices=[
            ("Van", "Delivery Van (Up to 1.5 Tons)"),
            ("Light Truck", "Light Truck (Up to 3.5 Tons)"),
            ("Heavy Truck", "Heavy Truck (Up to 12 Tons)"),
            ("Container", "Freight Container Carrier (Up to 30 Tons)"),
        ],
        default="Van",
        validators=[DataRequired()],
    )
    capacity_kg = DecimalField(
        "Cargo Capacity (kg) *",
        places=2,
        default=Decimal("1500.00"),
        validators=[
            DataRequired(message="Capacity is required."),
            NumberRange(min=100.0, max=50000.0, message="Capacity must be between 100 and 50,000 kg."),
        ],
    )
    status = SelectField(
        "Operational Status *",
        choices=[
            ("AVAILABLE", "Available (Ready for Dispatch)"),
            ("IN_TRANSIT", "In Transit (Currently on Route)"),
            ("MAINTENANCE", "Under Maintenance / Inspection"),
        ],
        default="AVAILABLE",
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Vehicle")

    def __init__(self, original_plate=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_plate = original_plate

    def validate_plate_number(self, field):
        plate = field.data.strip().upper()
        if self.original_plate and plate == self.original_plate:
            return
        existing = Vehicle.query.filter_by(plate_number=plate).first()
        if existing:
            raise ValidationError(f"A vehicle with plate number '{plate}' is already registered.")


class DriverForm(FlaskForm):
    """Fleet driver registration and edit form."""

    name = StringField(
        "Driver Full Name *",
        validators=[
            DataRequired(message="Driver name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    license_number = StringField(
        "Commercial Driver License (CDL) Number *",
        validators=[
            DataRequired(message="License number is required."),
            Length(min=4, max=50, message="License number must be between 4 and 50 characters."),
        ],
    )
    phone = StringField(
        "Contact Phone Number *",
        validators=[
            DataRequired(message="Phone number is required."),
            Length(min=7, max=25, message="Please enter a valid phone number."),
        ],
    )
    status = SelectField(
        "Availability Status *",
        choices=[
            ("AVAILABLE", "Available (Ready for Duty)"),
            ("ON_DUTY", "On Duty (Currently Driving / Dispatched)"),
            ("OFF_DUTY", "Off Duty / Leave"),
        ],
        default="AVAILABLE",
        validators=[DataRequired()],
    )
    assigned_vehicle_id = SelectField(
        "Assigned Default Vehicle (Optional)",
        coerce=int,
    )
    submit = SubmitField("Save Driver")

    def __init__(self, original_license=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_license = original_license

    def validate_license_number(self, field):
        license_num = field.data.strip().upper()
        if self.original_license and license_num == self.original_license:
            return
        existing = Driver.query.filter_by(license_number=license_num).first()
        if existing:
            raise ValidationError(f"A driver with license '{license_num}' is already registered.")

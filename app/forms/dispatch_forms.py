from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, DateTimeLocalField, SubmitField
from wtforms.validators import DataRequired, Length


class DispatchCreateForm(FlaskForm):
    """Logistics dispatch assignment form."""

    order_id = SelectField(
        "Select Approved Order to Dispatch *",
        coerce=int,
        validators=[DataRequired(message="Please select an approved customer order.")],
    )
    warehouse_id = SelectField(
        "Fulfillment Origin Warehouse *",
        coerce=int,
        validators=[DataRequired(message="Please select the origin warehouse facility.")],
    )
    vehicle_id = SelectField(
        "Assign Fleet Vehicle *",
        coerce=int,
        validators=[DataRequired(message="Please select an available vehicle.")],
    )
    driver_id = SelectField(
        "Assign Delivery Driver *",
        coerce=int,
        validators=[DataRequired(message="Please assign an available driver.")],
    )
    estimated_delivery = DateTimeLocalField(
        "Estimated Delivery Timestamp *",
        format="%Y-%m-%dT%H:%M",
        default=lambda: datetime.utcnow() + timedelta(days=2),
        validators=[DataRequired(message="Estimated delivery timestamp is required.")],
    )
    notes = TextAreaField(
        "Dispatch Notes / Routing Instructions",
        validators=[Length(max=500)],
    )
    submit = SubmitField("Confirm & Launch Dispatch")


class DispatchStatusUpdateForm(FlaskForm):
    """Update shipment tracking status."""

    status = SelectField(
        "Update Delivery Status *",
        choices=[
            ("DISPATCHED", "DISPATCHED — Left fulfillment facility"),
            ("IN_TRANSIT", "IN TRANSIT — Out on highway / local delivery route"),
            ("DELIVERED", "DELIVERED — Successfully handed over to customer"),
            ("FAILED", "FAILED — Delivery attempt unsuccessful / returned"),
        ],
        validators=[DataRequired()],
    )
    notes = TextAreaField(
        "Status Update Notes / Transit Log",
        validators=[Length(max=500)],
    )
    submit = SubmitField("Update Shipment Status")

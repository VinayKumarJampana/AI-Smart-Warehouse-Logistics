from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from app.models.warehouse import Warehouse


class WarehouseForm(FlaskForm):
    """Warehouse creation and update form."""

    code = StringField(
        "Warehouse Code",
        validators=[
            DataRequired(message="Warehouse code is required."),
            Length(min=2, max=20, message="Code must be between 2 and 20 characters."),
        ],
    )
    name = StringField(
        "Warehouse Name",
        validators=[
            DataRequired(message="Warehouse name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    location = StringField(
        "City / Region",
        validators=[
            DataRequired(message="Location is required."),
            Length(max=100),
        ],
    )
    address = TextAreaField(
        "Street Address",
        validators=[Length(max=255)],
    )
    total_capacity_sqft = IntegerField(
        "Total Capacity (sq. ft.)",
        validators=[
            DataRequired(message="Capacity is required."),
            NumberRange(min=100, max=10000000, message="Capacity must be at least 100 sq ft."),
        ],
    )
    status = SelectField(
        "Operational Status",
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("maintenance", "Under Maintenance"),
        ],
        default="active",
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Warehouse")

    def __init__(self, original_code=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_code = original_code

    def validate_code(self, field):
        code_input = field.data.strip().upper()
        if self.original_code and code_input == self.original_code:
            return
        existing = Warehouse.query.filter_by(code=code_input).first()
        if existing:
            raise ValidationError(f"Warehouse with code '{code_input}' already exists.")

from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    DateField,
    IntegerField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Regexp


class OrderCreateForm(FlaskForm):
    """Customer order creation form."""

    customer_name = StringField(
        "Customer / Business Name *",
        validators=[
            DataRequired(message="Customer name is required."),
            Length(min=2, max=100),
        ],
    )
    customer_email = StringField(
        "Customer Email Address *",
        validators=[
            DataRequired(message="Email address is required."),
            Regexp(
                r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                message="Please enter a valid email address.",
            ),
            Length(max=120),
        ],
    )
    customer_phone = StringField(
        "Customer Phone Number *",
        validators=[
            DataRequired(message="Phone number is required."),
            Length(min=7, max=25),
        ],
    )
    delivery_address = TextAreaField(
        "Destination Delivery Address *",
        validators=[
            DataRequired(message="Delivery destination is required."),
            Length(min=5, max=500),
        ],
    )
    expected_delivery_date = DateField(
        "Target Delivery Date *",
        default=date.today,
        validators=[DataRequired(message="Expected delivery date is required.")],
    )

    # Initial order line item
    product_id = SelectField(
        "Primary Product SKU *",
        coerce=int,
        validators=[DataRequired(message="Please select a product.")],
    )
    quantity = IntegerField(
        "Ordered Quantity *",
        default=1,
        validators=[
            DataRequired(message="Quantity is required."),
            NumberRange(min=1, max=50000, message="Quantity must be at least 1 unit."),
        ],
    )

    submit = SubmitField("Create Customer Order")


class OrderItemAddForm(FlaskForm):
    """Add additional line item to an active order before approval."""

    product_id = SelectField(
        "Additional Product *",
        coerce=int,
        validators=[DataRequired(message="Please select a product.")],
    )
    quantity = IntegerField(
        "Quantity *",
        default=1,
        validators=[
            DataRequired(message="Quantity is required."),
            NumberRange(min=1, max=50000, message="Quantity must be at least 1 unit."),
        ],
    )
    submit = SubmitField("Add Item to Order")

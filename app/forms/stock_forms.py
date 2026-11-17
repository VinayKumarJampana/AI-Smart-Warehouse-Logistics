from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError
from app.extensions import db
from app.models.product import Product


class StockInForm(FlaskForm):
    """Stock Inward transaction form."""

    product_id = SelectField(
        "Product / SKU",
        coerce=int,
        validators=[DataRequired(message="Please select a product.")],
    )
    quantity = IntegerField(
        "Quantity to Add",
        validators=[
            DataRequired(message="Quantity is required."),
            NumberRange(min=1, max=100000, message="Quantity must be at least 1 unit."),
        ],
    )
    reference_no = StringField(
        "Reference / PO Number",
        validators=[
            Length(max=50),
        ],
    )
    notes = TextAreaField(
        "Transaction Notes / Remarks",
        validators=[Length(max=255)],
    )
    submit = SubmitField("Record Stock In")


class StockOutForm(FlaskForm):
    """Stock Outward transaction form with inventory boundary validation."""

    product_id = SelectField(
        "Product / SKU",
        coerce=int,
        validators=[DataRequired(message="Please select a product.")],
    )
    quantity = IntegerField(
        "Quantity to Dispatch / Remove",
        validators=[
            DataRequired(message="Quantity is required."),
            NumberRange(min=1, max=100000, message="Quantity must be at least 1 unit."),
        ],
    )
    reference_no = StringField(
        "Reference / SO Number",
        validators=[
            Length(max=50),
        ],
    )
    notes = TextAreaField(
        "Reason / Notes",
        validators=[Length(max=255)],
    )
    submit = SubmitField("Record Stock Out")

    def validate_quantity(self, field):
        if self.product_id.data:
            product = db.session.get(Product, self.product_id.data)
            if product:
                if field.data > product.current_stock:
                    raise ValidationError(
                        f"Insufficient inventory! Product '{product.name}' only has "
                        f"{product.current_stock} {product.unit} available (requested: {field.data})."
                    )

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    DecimalField,
    IntegerField,
    SelectField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from app.models.category import Category
from app.models.product import Product


class CategoryForm(FlaskForm):
    """Product category form."""

    name = StringField(
        "Category Name",
        validators=[
            DataRequired(message="Category name is required."),
            Length(min=2, max=80, message="Name must be between 2 and 80 characters."),
        ],
    )
    description = TextAreaField(
        "Description",
        validators=[Length(max=255)],
    )
    submit = SubmitField("Save Category")

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, field):
        name_input = field.data.strip()
        if self.original_name and name_input.lower() == self.original_name.lower():
            return
        existing = Category.query.filter_by(name=name_input).first()
        if existing:
            raise ValidationError(f"Category '{name_input}' already exists.")


class ProductForm(FlaskForm):
    """Product SKU creation and editing form."""

    sku = StringField(
        "SKU (Stock Keeping Unit)",
        validators=[
            DataRequired(message="SKU is required."),
            Length(min=2, max=50, message="SKU must be between 2 and 50 characters."),
        ],
    )
    name = StringField(
        "Product Name",
        validators=[
            DataRequired(message="Product name is required."),
            Length(min=2, max=150, message="Name must be between 2 and 150 characters."),
        ],
    )
    category_id = SelectField(
        "Category",
        coerce=int,
        validators=[DataRequired(message="Please select a category.")],
    )
    warehouse_id = SelectField(
        "Warehouse Location",
        coerce=int,
        validators=[DataRequired(message="Please assign a warehouse.")],
    )
    unit = SelectField(
        "Unit of Measure",
        choices=[
            ("Units", "Units (pcs)"),
            ("Boxes", "Boxes"),
            ("Kg", "Kilograms (kg)"),
            ("Pallets", "Pallets"),
            ("Cartons", "Cartons"),
        ],
        default="Units",
        validators=[DataRequired()],
    )
    cost_price = DecimalField(
        "Unit Cost Price ($)",
        places=2,
        validators=[
            DataRequired(message="Cost price is required."),
            NumberRange(min=0.01, message="Cost price must be greater than 0."),
        ],
    )
    unit_price = DecimalField(
        "Unit Selling Price ($)",
        places=2,
        validators=[
            DataRequired(message="Selling price is required."),
            NumberRange(min=0.01, message="Selling price must be greater than 0."),
        ],
    )
    current_stock = IntegerField(
        "Initial Current Stock",
        default=0,
        validators=[
            NumberRange(min=0, message="Current stock cannot be negative."),
        ],
    )
    min_threshold = IntegerField(
        "Safety Reorder Threshold",
        default=10,
        validators=[
            DataRequired(message="Minimum threshold is required."),
            NumberRange(min=1, message="Threshold must be at least 1 unit."),
        ],
    )
    max_capacity = IntegerField(
        "Max Storage Capacity",
        default=1000,
        validators=[
            DataRequired(message="Max capacity is required."),
            NumberRange(min=1, message="Max capacity must be at least 1 unit."),
        ],
    )
    lead_time_days = IntegerField(
        "Supplier Lead Time (Days)",
        default=7,
        validators=[
            DataRequired(message="Lead time is required."),
            NumberRange(min=1, max=365, message="Lead time must be between 1 and 365 days."),
        ],
    )
    submit = SubmitField("Save Product")

    def __init__(self, original_sku=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_sku = original_sku

    def validate_sku(self, field):
        sku_input = field.data.strip().upper()
        if self.original_sku and sku_input == self.original_sku:
            return
        existing = Product.query.filter_by(sku=sku_input).first()
        if existing:
            raise ValidationError(f"A product with SKU '{sku_input}' already exists.")

    def validate_max_capacity(self, field):
        if self.min_threshold.data and field.data:
            if field.data < self.min_threshold.data:
                raise ValidationError("Max storage capacity cannot be less than safety threshold.")

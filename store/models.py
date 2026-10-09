import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide this product from the shop."
    )

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.pk])

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    @property
    def low_stock(self):
        return 0 < self.stock_quantity <= 5


phone_validator = RegexValidator(
    r"^\+?[0-9\s\-]{7,15}$", "Enter a valid phone number (7-15 digits)."
)
postal_validator = RegexValidator(
    r"^[A-Za-z0-9\s\-]{3,10}$", "Enter a valid postal code."
)


def generate_order_number():
    """Example: S4U-20260115-A1B2C3"""
    return f"S4U-{timezone.localdate():%Y%m%d}-{secrets.token_hex(3).upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        PROCESSING = "Processing", "Processing"
        SHIPPED = "Shipped", "Shipped"
        DELIVERED = "Delivered", "Delivered"
        CANCELLED = "Cancelled", "Cancelled"

    class Payment(models.TextChoices):
        COD = "COD", "Cash on Delivery"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    order_number = models.CharField(
        max_length=30, unique=True, default=generate_order_number, editable=False
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[phone_validator])
    shipping_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, validators=[postal_validator])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=Payment.choices, default=Payment.COD
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def get_absolute_url(self):
        return reverse("order_detail", args=[self.order_number])

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )
    product_name = models.CharField(max_length=200)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    length_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Length in centimeters"
    )
    width_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Width in centimeters"
    )
    height_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Height in centimeters"
    )
    weight_kg = models.DecimalField(
        max_digits=8, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Weight in kilograms"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.length_cm}x{self.width_cm}x{self.height_cm} cm, {self.weight_kg} kg)"

    @property
    def volume_cm3(self):
        return self.length_cm * self.width_cm * self.height_cm

    def sorted_dimensions(self):
        dims = sorted(
            [float(self.length_cm), float(self.width_cm), float(self.height_cm)],
            reverse=True
        )
        return dims


class Box(models.Model):
    name = models.CharField(max_length=100)
    length_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal length in centimeters"
    )
    width_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal width in centimeters"
    )
    height_cm = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Internal height in centimeters"
    )
    max_weight_kg = models.DecimalField(
        max_digits=8, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Maximum weight capacity in kilograms"
    )
    cost = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of the box"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['cost', 'name']
        verbose_name_plural = 'boxes'

    def __str__(self):
        return f"{self.name} ({self.length_cm}x{self.width_cm}x{self.height_cm} cm, max {self.max_weight_kg} kg, ${self.cost})"

    @property
    def volume_cm3(self):
        return self.length_cm * self.width_cm * self.height_cm

    def sorted_dimensions(self):
        dims = sorted(
            [float(self.length_cm), float(self.width_cm), float(self.height_cm)],
            reverse=True
        )
        return dims


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('recommended', 'Box Recommended'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    recommended_box = models.ForeignKey(
        Box, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    @property
    def total_weight_kg(self):
        return sum(
            (item.product.weight_kg * item.quantity for item in self.items.all()),
            Decimal('0')
        )

    @property
    def total_volume_cm3(self):
        return sum(
            (item.product.volume_cm3 * item.quantity for item in self.items.all()),
            Decimal('0')
        )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.order_number})"

    @property
    def line_weight_kg(self):
        return self.product.weight_kg * self.quantity

    @property
    def line_volume_cm3(self):
        return self.product.volume_cm3 * self.quantity
import uuid

from django.db import models

from .allergen import Allergen
from .category import ProductCategory


class Product(models.Model):
    """Satılabilir ürün. Örn: mercimek çorbası."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="SEK")
    allergens = models.ManyToManyField(Allergen, blank=True, related_name="products")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_product"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"
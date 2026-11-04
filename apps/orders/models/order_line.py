import uuid
from decimal import Decimal

from django.db import models

from apps.catalog.models import Product
from apps.recipes.models import RecipeVersion


class OrderLine(models.Model):
    """
    Sipariş satırı. Ürün adı, fiyatı ve onaylı reçete sürümü
    sipariş anında snapshot'lanır.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_lines"
    )
    product_name_snapshot = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    recipe_version_snapshot = models.ForeignKey(
        RecipeVersion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_lines",
        help_text="Sipariş anındaki onaylı reçete sürümü (varsa).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders_order_line"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"], name="uniq_order_product"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order.order_number} — {self.product_name_snapshot} ×{self.quantity}"

    def save(self, *args, **kwargs):
        # line_total her zaman sunucu tarafında hesaplanır
        self.line_total = Decimal(self.quantity) * self.unit_price_snapshot
        super().save(*args, **kwargs)
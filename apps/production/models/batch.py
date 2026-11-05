import uuid
from decimal import Decimal

from django.db import models

from apps.catalog.models import Product
from apps.orders.models import OrderLine
from apps.recipes.models import RecipeVersion

from .plan import ProductionPlan


class ProductionBatchStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ProductionBatch(models.Model):
    """
    Bir üretim partisi. MVP'de 1 parti = 1 sipariş satırı (birebir).
    Parti tamamlandığında rezervasyonlar fiziksel tüketime dönüşür
    (Faz 4 Adım 2). `order_line` opsiyonel: ileride stok için üretim
    eklenirse boş bırakılabilir.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        ProductionPlan, on_delete=models.CASCADE, related_name="batches"
    )
    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_batches",
        help_text="Sipariş kaynaklı üretim ise ilgili satır.",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="production_batches"
    )
    recipe_version_snapshot = models.ForeignKey(
        RecipeVersion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_batches",
        help_text="Üretim anındaki onaylı reçete (varsa).",
    )
    planned_quantity = models.PositiveIntegerField(
        help_text="Planlanan porsiyon/adet sayısı.",
        validators=[],
    )
    actual_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gerçekleşen porsiyon/adet. Tamamlanınca doldurulur.",
    )
    waste_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        help_text="Fire miktarı (birim işletme politikasına göre belirlenecek).",
    )
    status = models.CharField(
        max_length=16,
        choices=ProductionBatchStatus.choices,
        default=ProductionBatchStatus.PLANNED,
    )
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "production_batch"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "order_line"],
                name="uniq_plan_order_line",
                condition=models.Q(order_line__isnull=False),
            ),
            models.CheckConstraint(
                condition=models.Q(planned_quantity__gt=0),
                name="batch_planned_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} × {self.planned_quantity} [{self.status}]"
import uuid
from decimal import Decimal

from django.db import models

from apps.catalog.models import UnitOfMeasure
from apps.inventory.models import InventoryLot

from .batch import ProductionBatch


class BatchIngredient(models.Model):
    """
    Bir üretim partisinde fiilen tüketilen lot/miktar. Parti tamamlanınca
    `services.consume_reservation` tarafından yazılır. Traceability:
    hangi bitmiş ürün hangi malzeme lot'undan üretildi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.CASCADE,
        related_name="ingredients_used",
    )
    lot = models.ForeignKey(
        InventoryLot, on_delete=models.PROTECT, related_name="batch_usages"
    )
    planned_quantity = models.DecimalField(
        max_digits=14, decimal_places=3, default=Decimal("0")
    )
    actual_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="batch_usages"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_batch_ingredient"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "lot"],
                name="uniq_batch_lot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.batch_id} ← {self.lot.internal_lot_code} × {self.actual_quantity}"
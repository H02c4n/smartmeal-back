import uuid

from django.db import models
from django.utils import timezone

from apps.catalog.models import Ingredient
from apps.purchasing.models import Supplier


class QualityStatus(models.TextChoices):
    PENDING = "PENDING", "Pending QC"
    RELEASED = "RELEASED", "Released"
    BLOCKED = "BLOCKED", "Blocked"


class InventoryLot(models.Model):
    """
    Malzeme lotu. Miktar tutmaz — bakiye StockMovement'lardan hesaplanır.
    Tedarikçi lot kodu + malzeme kombinasyonu benzersizdir (her tedarikçi
    aynı lot kodunu farklı malzemeler için kullanabilir).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT, related_name="lots"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="lots"
    )
    supplier_lot_code = models.CharField(max_length=128)
    internal_lot_code = models.CharField(max_length=128, unique=True)
    received_at = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)
    quality_status = models.CharField(
        max_length=16,
        choices=QualityStatus.choices,
        default=QualityStatus.PENDING,
    )
    site_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Tesis kapsamı. Şimdilik opsiyonel (tek tesis varsayımı).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_lot"
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "supplier_lot_code", "ingredient"],
                name="uniq_supplier_lot_per_ingredient",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.internal_lot_code} ({self.ingredient.sku})"
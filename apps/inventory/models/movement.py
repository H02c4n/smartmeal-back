import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .lot import InventoryLot


class MovementType(models.TextChoices):
    RECEIPT = "RECEIPT", "Receipt"
    CONSUMPTION = "CONSUMPTION", "Consumption"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    WASTE = "WASTE", "Waste"
    RETURN = "RETURN", "Return"
    REVERSAL = "REVERSAL", "Reversal"


class StockMovement(models.Model):
    """
    Append-only stok hareket defteri. Geçmiş hareketler güncellenemez veya
    silinemez; düzeltme için ters hareket yazılır.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lot = models.ForeignKey(
        InventoryLot, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=16, choices=MovementType.choices)
    quantity_delta = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Signed. RECEIPT/RETURN pozitif, CONSUMPTION/WASTE negatif.",
    )
    reason = models.CharField(max_length=255, blank=True)
    reference_type = models.CharField(max_length=64, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["lot", "occurred_at"]),
        ]

    def __str__(self) -> str:
        sign = "+" if self.quantity_delta >= 0 else ""
        return f"{self.movement_type} {sign}{self.quantity_delta} [{self.lot.internal_lot_code}]"

    def clean(self):
        """Sign-tutarlılık kontrolü. Admin formu `full_clean()` çağırır."""
        if self.movement_type in (
            MovementType.RECEIPT,
            MovementType.RETURN,
        ) and self.quantity_delta <= 0:
            raise ValidationError(
                f"{self.movement_type} pozitif delta gerektirir."
            )
        if self.movement_type in (
            MovementType.CONSUMPTION,
            MovementType.WASTE,
        ) and self.quantity_delta >= 0:
            raise ValidationError(
                f"{self.movement_type} negatif delta gerektirir."
            )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "StockMovement değiştirilemez. Düzeltme için ters hareket yazın."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "StockMovement silinemez. Düzeltme için ters hareket yazın."
        )
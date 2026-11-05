import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models import InventoryLot
from apps.production.models import ProductionBatch


class QualityCheckType(models.TextChoices):
    TEMPERATURE = "TEMPERATURE", "Temperature"
    WEIGHT = "WEIGHT", "Weight"
    APPEARANCE = "APPEARANCE", "Appearance"
    MICRO = "MICRO", "Microbiological"
    TASTE = "TASTE", "Taste"
    OTHER = "OTHER", "Other"


class QualityCheckResult(models.TextChoices):
    PASS = "PASS", "Pass"
    FAIL = "FAIL", "Fail"


class QualityCheck(models.Model):
    """
    Bir parti veya lot için tek bir ölçüm. Hold/release kararı bu
    ölçümlerin toplamından servis katmanında verilir.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_checks",
    )
    lot = models.ForeignKey(
        InventoryLot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_checks",
    )
    check_type = models.CharField(
        max_length=16, choices=QualityCheckType.choices
    )
    result = models.CharField(max_length=8, choices=QualityCheckResult.choices)
    measurement_value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Ölçüm yoksa (ör. görünüm) boş bırakılabilir.",
    )
    measurement_unit = models.CharField(
        max_length=16,
        blank=True,
        help_text="°C, g, kg... (unit_of_measure tablosunu kullanmıyoruz; "
        "bu bir ölçüm birimi, üretim birimi değil).",
    )
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_checks",
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "quality_check"
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["batch", "checked_at"]),
            models.Index(fields=["lot", "checked_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(batch__isnull=False, lot__isnull=True)
                    | models.Q(batch__isnull=True, lot__isnull=False)
                ),
                name="quality_check_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        target = (
            f"batch={self.batch_id}" if self.batch_id else f"lot={self.lot_id}"
        )
        return f"{self.check_type} [{target}] → {self.result}"

    def clean(self):
        if self.batch_id is None and self.lot_id is None:
            raise ValidationError("batch veya lot zorunlu.")
        if self.batch_id and self.lot_id:
            raise ValidationError("Sadece biri (batch veya lot) set edilebilir.")
        if (
            self.measurement_value is not None
            and not (self.measurement_unit or "").strip()
        ):
            raise ValidationError("Ölçüm değeri varsa unit zorunlu.")
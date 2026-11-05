import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models import InventoryLot
from apps.production.models import ProductionBatch


class QualityIncidentSeverity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class QualityIncidentStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ON_HOLD = "ON_HOLD", "On Hold"
    RELEASED = "RELEASED", "Released"
    CLOSED = "CLOSED", "Closed"


class QualityIncident(models.Model):
    """
    Uygunsuzluk kaydı. `ON_HOLD` durumu, ilgili parti veya lot'un
    paketleme/teslimat akışında kullanılmaması gerektiğini belirtir.
    Release kararı ayrı bir servis çağrısıyla verilir (Faz 5 Adım 2).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ProductionBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_incidents",
    )
    lot = models.ForeignKey(
        InventoryLot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_incidents",
    )
    severity = models.CharField(
        max_length=16, choices=QualityIncidentSeverity.choices
    )
    status = models.CharField(
        max_length=16,
        choices=QualityIncidentStatus.choices,
        default=QualityIncidentStatus.OPEN,
    )
    reason = models.TextField()
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_incidents_reported",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_incidents_resolved",
    )
    resolution_notes = models.TextField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quality_incident"
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["batch", "status"]),
            models.Index(fields=["lot", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(batch__isnull=False, lot__isnull=True)
                    | models.Q(batch__isnull=True, lot__isnull=False)
                ),
                name="quality_incident_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        target = (
            f"batch={self.batch_id}" if self.batch_id else f"lot={self.lot_id}"
        )
        return f"{self.severity} [{self.status}] {target}"

    def clean(self):
        if self.batch_id is None and self.lot_id is None:
            raise ValidationError("batch veya lot zorunlu.")
        if self.batch_id and self.lot_id:
            raise ValidationError("Sadece biri set edilebilir.")
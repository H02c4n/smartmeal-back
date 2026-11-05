import uuid

from django.db import models

from apps.packing.models import Package

from .run import DeliveryRun


class DeliveryStopStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED = "FAILED", "Failed"


class DeliveryStop(models.Model):
    """
    Bir kurye rotasındaki tek durak. Her durak bir paket = bir sipariş.
    Aynı paket birden çok aktif durakta olamaz (unique constraint).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        DeliveryRun, on_delete=models.CASCADE, related_name="stops"
    )
    package = models.ForeignKey(
        Package, on_delete=models.PROTECT, related_name="delivery_stops"
    )
    sequence = models.PositiveIntegerField(
        help_text="Run içindeki sıra (1, 2, 3...)."
    )
    status = models.CharField(
        max_length=16,
        choices=DeliveryStopStatus.choices,
        default=DeliveryStopStatus.PENDING,
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    proof_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Fotoğraf/imza/konum referansı. Saklama politikası Faz 7'de.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_stop"
        ordering = ["run", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "sequence"],
                name="uniq_run_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["package", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.run_id} #{self.sequence} [{self.status}]"
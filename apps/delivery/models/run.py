import uuid

from django.conf import settings
from django.db import models


class DeliveryRunStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class DeliveryRun(models.Model):
    """
    Bir kuryenin belirli bir gündeki teslimat rotası. Birden çok
    DeliveryStop içerir.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_date = models.DateField()
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="delivery_runs",
    )
    status = models.CharField(
        max_length=16,
        choices=DeliveryRunStatus.choices,
        default=DeliveryRunStatus.PLANNED,
    )
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "delivery_run"
        ordering = ["-delivery_date", "-created_at"]
        indexes = [
            models.Index(fields=["delivery_date", "status"]),
            models.Index(fields=["driver", "status"]),
        ]

    def __str__(self) -> str:
        return f"Run {self.delivery_date} [{self.status}]"
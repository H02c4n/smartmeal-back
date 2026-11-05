import uuid

from django.conf import settings
from django.db import models


class ProductionPlanStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    RELEASED = "RELEASED", "Released"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ProductionPlan(models.Model):
    """
    Belirli bir üretim günü için plan. Partiler (ProductionBatch) bu plan
    altında toplanır. Durum geçişleri Faz 4 Adım 2'de servis katmanında
    uygulanacak.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    production_date = models.DateField()
    site_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Tesis kapsamı. Şimdilik opsiyonel (tek tesis varsayımı).",
    )
    status = models.CharField(
        max_length=16,
        choices=ProductionPlanStatus.choices,
        default=ProductionPlanStatus.DRAFT,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="production_plans",
    )
    released_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "production_plan"
        ordering = ["-production_date", "-created_at"]
        indexes = [
            models.Index(fields=["production_date", "status"]),
        ]

    def __str__(self) -> str:
        return f"Plan {self.production_date} [{self.status}]"
import uuid

from django.conf import settings
from django.db import models

from .batch import ProductionBatch


class ProductionTaskType(models.TextChoices):
    PREP = "PREP", "Preparation"
    COOK = "COOK", "Cooking"
    COOL = "COOL", "Cooling"
    PACK = "PACK", "Packing"
    OTHER = "OTHER", "Other"


class ProductionTaskStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    SKIPPED = "SKIPPED", "Skipped"


class ProductionTask(models.Model):
    """
    Bir parti içindeki iş adımı. Sıra (`sequence`) ile partideki iş akışı
    belirlenir. Faz 4 Adım 2+'de operatör mobilinden yönetilecek.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE, related_name="tasks"
    )
    task_type = models.CharField(max_length=16, choices=ProductionTaskType.choices)
    sequence = models.PositiveIntegerField(
        help_text="Parti içindeki sıra (1, 2, 3...)."
    )
    status = models.CharField(
        max_length=16,
        choices=ProductionTaskStatus.choices,
        default=ProductionTaskStatus.PENDING,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_tasks",
    )
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "production_task"
        ordering = ["batch", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "sequence"],
                name="uniq_batch_sequence",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.batch_id} #{self.sequence} {self.task_type} [{self.status}]"
import uuid

from django.db import models

from apps.production.models import ProductionBatch

from .package import Package


class PackageLine(models.Model):
    """
    Paket içindeki ürün miktarı + hangi batch'ten geldiği (izlenebilirlik).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, related_name="lines"
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.PROTECT, related_name="package_lines"
    )
    quantity = models.PositiveIntegerField(
        help_text="Paketlenen porsiyon/adet."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "packing_package_line"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["package", "batch"],
                name="uniq_package_batch",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="package_line_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.package.package_code} ← {self.batch_id} × {self.quantity}"
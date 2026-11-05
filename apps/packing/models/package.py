import uuid

from django.conf import settings
from django.db import models

from apps.orders.models import Order


class PackageStatus(models.TextChoices):
    PACKED = "PACKED", "Packed"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY", "Ready for Delivery"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"


class Package(models.Model):
    """
    Bir siparişin paketlenmiş hali. MVP'de her sipariş için tek Package
    (tüm batch'ler dahil). Faz 6'da delivery ile ilişkilendirilir.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="packages"
    )
    package_code = models.CharField(max_length=32, unique=True)
    status = models.CharField(
        max_length=24,
        choices=PackageStatus.choices,
        default=PackageStatus.PACKED,
    )
    packed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="packed_packages",
    )
    packed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "packing_package"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.package_code} [{self.status}]"
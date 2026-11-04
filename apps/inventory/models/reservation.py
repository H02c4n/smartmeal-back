import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from .lot import InventoryLot


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    RELEASED = "RELEASED", "Released"
    CONSUMED = "CONSUMED", "Consumed"
    EXPIRED = "EXPIRED", "Expired"


def default_expiry():
    return timezone.now() + timedelta(hours=24)


class StockReservation(models.Model):
    """
    Bir lot'tan belirli bir miktar için süreli kilit. `order_id` şimdilik
    nullable UUID; Faz 3'te `orders.Order` FK'sine bağlanacak.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lot = models.ForeignKey(
        InventoryLot, on_delete=models.PROTECT, related_name="reservations"
    )
    order_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Faz 3'te orders.Order.id ile eşleşecek.",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(
        max_length=16,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
    )
    expires_at = models.DateTimeField(default=default_expiry)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="RELEASED/CONSUMED/EXPIRED olduğu an.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_reservations",
    )

    class Meta:
        db_table = "inventory_stock_reservation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lot", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.lot.internal_lot_code} ×{self.quantity} [{self.status}]"

    def clean(self):
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("Rezervasyon miktarı pozitif olmalı.")
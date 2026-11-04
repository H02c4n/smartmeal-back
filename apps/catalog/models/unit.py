import uuid
from decimal import Decimal

from django.db import models


class UnitOfMeasure(models.Model):
    """
    Ölçü birimi. Dönüşüm için base_unit + factor kullanılır.
    Örn: g (base), kg (base=g, factor=1000), mg (base=g, factor=0.001)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=16, unique=True)  # 'g', 'kg', 'ml', 'l', 'adet'
    name = models.CharField(max_length=64)
    base_unit = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="derived_units",
        help_text="Boşsa bu birim kendi başına baz birimdir.",
    )
    factor = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        default=Decimal("1"),
        help_text="1 bu birim = factor × base_unit",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "catalog_unit_of_measure"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"